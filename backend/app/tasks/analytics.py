"""Analytics and cost Celery tasks with thin production-safe integrations."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from time import perf_counter
from typing import Any
from uuid import UUID

from sqlalchemy import func, select

from app.core.celery_app import CeleryConfigurationError, get_celery_app
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.redis_client import get_redis_client
from app.core.task_base import BaseTaskWithRetry
from app.models.conversation_log import ConversationLog
from app.models.cost_log import CostLog
from app.observability.analytics_summary_service import AnalyticsSummaryService
from app.observability.cost_tracker import CostTracker
from app.repositories.conversation_log_repository import ConversationLogRepository
from app.repositories.cost_log_repository import CostLogRepository
from app.repositories.session_log_repository import SessionLogRepository
from app.services.tasks.task_logging import TaskLogger
from app.services.tasks.task_metrics import TaskMetrics

logger = logging.getLogger(__name__)
task_logger = TaskLogger()
task_metrics = TaskMetrics()

_REPORT_LOCK_TTL_SECONDS = 30 * 60
_REPORT_DONE_TTL_SECONDS = 10 * 24 * 60 * 60
_SNAPSHOT_TTL_SECONDS = 14 * 24 * 60 * 60
_JSON_MAX_BYTES = 200_000


class _DummyTaskApp:
    """Fallback task app when Celery is not configured."""

    @staticmethod
    def task(*_args, **_kwargs):
        def decorator(func):
            return func

        return decorator


def _resolve_task_app():
    try:
        return get_celery_app()
    except CeleryConfigurationError as exc:
        logger.warning("celery_not_configured_for_analytics_tasks", extra={"error": str(exc)})
        return _DummyTaskApp()


task_app = _resolve_task_app()


def _request_context(task: Any) -> dict[str, Any]:
    request = getattr(task, "request", None)
    delivery_info = getattr(request, "delivery_info", {}) or {}
    return {
        "task_id": str(getattr(request, "id", "") or ""),
        "task_name": str(getattr(task, "name", "") or ""),
        "queue": delivery_info.get("routing_key") if isinstance(delivery_info, dict) else None,
        "retry_count": int(getattr(request, "retries", 0) or 0),
    }


def _update_progress(task: Any, *, current: int, total: int, step: str, **extra: Any) -> None:
    progress = {
        "current": current,
        "total": total,
        "percent": round((current / total) * 100.0, 2) if total > 0 else None,
        "step": step,
    }
    try:
        task.update_state(state="STARTED", meta={"progress": progress, **extra})
    except Exception:
        logger.debug("analytics_task_progress_update_failed", exc_info=True)


def _report_bucket(report_name: str, anchor: datetime) -> str:
    if report_name == "aggregate_daily_metrics":
        return anchor.strftime("%Y%m%d%H")
    return anchor.strftime("%Y%m%d")


def _period_window(anchor: datetime) -> tuple[datetime, datetime]:
    start = datetime(anchor.year, anchor.month, anchor.day, tzinfo=UTC)
    end = start + timedelta(days=1)
    return start, end


def _redis_key(kind: str, report_name: str, bucket: str) -> str:
    prefix = str(getattr(settings, "redis_key_prefix", "ragai:session"))
    return f"{prefix}:analytics:{report_name}:{bucket}:{kind}"


def _claim_report_run(report_name: str, bucket: str) -> tuple[bool, str]:
    client = get_redis_client()
    done_key = _redis_key("done", report_name, bucket)
    lock_key = _redis_key("lock", report_name, bucket)

    if client.exists(done_key):
        return False, "already_completed"
    acquired = bool(client.set(lock_key, "1", nx=True, ex=_REPORT_LOCK_TTL_SECONDS))
    if not acquired:
        return False, "in_progress"
    return True, "claimed"


def _release_report_lock(report_name: str, bucket: str) -> None:
    client = get_redis_client()
    lock_key = _redis_key("lock", report_name, bucket)
    client.delete(lock_key)


def _persist_report_snapshot(report_name: str, bucket: str, payload: dict[str, Any]) -> bool:
    client = get_redis_client()
    done_key = _redis_key("done", report_name, bucket)
    snapshot_key = _redis_key("snapshot", report_name, bucket)

    snapshot_payload = dict(payload)
    snapshot_payload["report_name"] = report_name
    snapshot_payload["bucket"] = bucket
    snapshot_payload["persisted_at"] = datetime.now(UTC).isoformat()
    encoded = json.dumps(snapshot_payload, default=str, ensure_ascii=False)
    if len(encoded.encode("utf-8")) > _JSON_MAX_BYTES:
        encoded = encoded.encode("utf-8")[:_JSON_MAX_BYTES].decode("utf-8", errors="ignore")

    client.set(done_key, "1", ex=_REPORT_DONE_TTL_SECONDS)
    client.set(snapshot_key, encoded, ex=_SNAPSHOT_TTL_SECONDS)
    return True


def _aggregate_daily_metrics(report_day: datetime) -> dict[str, Any]:
    start_at, end_at = _period_window(report_day)
    with SessionLocal() as db:
        conversation_repo = ConversationLogRepository(db)
        cost_repo = CostLogRepository(db)
        session_repo = SessionLogRepository(db)
        summary_service = AnalyticsSummaryService(
            conversation_logs=conversation_repo,
            cost_logs=cost_repo,
            session_logs=session_repo,
        )
        summary = summary_service.get_today_summary(now=report_day)

        active_users_stmt = select(func.count(func.distinct(ConversationLog.user_id))).where(
            ConversationLog.user_id.is_not(None),
            ConversationLog.created_at >= start_at,
            ConversationLog.created_at < end_at,
        )
        active_users = int(db.scalar(active_users_stmt) or 0)

        conversation_count_stmt = select(func.count(ConversationLog.id)).where(
            ConversationLog.created_at >= start_at,
            ConversationLog.created_at < end_at,
        )
        conversation_count = int(db.scalar(conversation_count_stmt) or 0)

        intents: dict[str, int] = {}
        fallback_count = 0
        hallucination_count = 0
        row_stmt = select(ConversationLog.metadata_json).where(
            ConversationLog.created_at >= start_at,
            ConversationLog.created_at < end_at,
        )
        rows = db.execute(row_stmt).all()
        for (metadata_json,) in rows:
            metadata = dict(metadata_json or {})
            intent = str(metadata.get("detected_intent", "")).strip().lower()
            if intent:
                intents[intent] = intents.get(intent, 0) + 1
            if metadata.get("fallback") is True:
                fallback_count += 1
            if metadata.get("hallucination") is True or metadata.get("hallucination_flag") is True:
                hallucination_count += 1

        total_records = max(conversation_count, 1)
        fallback_rate = round(fallback_count / total_records, 4)
        hallucination_rate = round(hallucination_count / total_records, 4)

        return {
            "active_users": active_users,
            "conversation_count": conversation_count,
            "token_usage": int(summary.total_tokens_today),
            "average_latency_ms": float(summary.avg_latency_ms),
            "p95_latency_ms": float(summary.p95_latency_ms),
            "intent_distribution": intents,
            "state_distribution": dict(summary.state_distribution),
            "fallback_rate": fallback_rate,
            "hallucination_rate": hallucination_rate,
            "currency": summary.currency,
        }


def _calculate_cost_reports(report_day: datetime) -> dict[str, Any]:
    start_at, end_at = _period_window(report_day)
    with SessionLocal() as db:
        repository = CostLogRepository(db)
        tracker = CostTracker(repository)

        total_cost = repository.aggregate_total_cost(start_at=start_at, end_at=end_at, currency="USD")
        total_tokens = repository.aggregate_total_tokens(start_at=start_at, end_at=end_at, currency="USD")
        cost_by_state = repository.aggregate_cost_by_state(start_at=start_at, end_at=end_at, currency="USD")

        cost_per_user_stmt = (
            select(CostLog.user_id, func.coalesce(func.sum(CostLog.total_cost), Decimal("0")))
            .where(
                CostLog.user_id.is_not(None),
                CostLog.created_at >= start_at,
                CostLog.created_at < end_at,
                CostLog.currency == "USD",
            )
            .group_by(CostLog.user_id)
        )
        per_user_rows = db.execute(cost_per_user_stmt).all()
        cost_per_user = {str(row[0]): float(Decimal(str(row[1] or Decimal("0")))) for row in per_user_rows if row[0] is not None}

        projected_monthly = tracker.get_projected_monthly_cost()
        return {
            "currency": "USD",
            "total_cost_usd": float(total_cost),
            "total_tokens": int(total_tokens),
            "cost_per_user": cost_per_user,
            "cost_by_state": {item.state: float(item.total_cost) for item in cost_by_state},
            "projected_monthly_cost_usd": float(projected_monthly.projected_total_cost),
        }


def _generate_usage_insights(aggregates: dict[str, Any], costs: dict[str, Any]) -> dict[str, Any]:
    intent_distribution = dict(aggregates.get("intent_distribution") or {})
    sorted_intents = sorted(intent_distribution.items(), key=lambda item: item[1], reverse=True)
    top_intents = [{"intent": name, "count": count} for name, count in sorted_intents[:5]]

    risk_flags: list[str] = []
    if float(aggregates.get("fallback_rate", 0.0)) > 0.2:
        risk_flags.append("high_fallback_rate")
    if float(aggregates.get("hallucination_rate", 0.0)) > 0.05:
        risk_flags.append("hallucination_risk")
    if float(aggregates.get("average_latency_ms", 0.0)) > 2000:
        risk_flags.append("high_latency")
    if float(costs.get("total_cost_usd", 0.0)) > 100:
        risk_flags.append("daily_cost_spike")

    summary = (
        "Usage stable."
        if not risk_flags
        else f"Attention required: {', '.join(risk_flags)}"
    )
    return {
        "high_level_summary": summary,
        "top_intents": top_intents,
        "state_distribution": dict(aggregates.get("state_distribution") or {}),
        "cost_per_user_count": len(dict(costs.get("cost_per_user") or {})),
        "risk_flags": risk_flags,
    }


def _handle_task_failure(context: dict[str, Any], started: float, exc: Exception) -> None:
    duration_seconds = perf_counter() - started
    task_logger.log_task_failure(
        task_id=context["task_id"],
        task_name=context["task_name"],
        queue=context["queue"],
        duration_ms=int(duration_seconds * 1000),
        retry_count=context["retry_count"],
        error=str(exc),
    )
    task_metrics.record_task_failure(context["task_name"], queue=context["queue"])
    task_metrics.record_task_retry(context["task_name"], retry_count=context["retry_count"], queue=context["queue"])


@task_app.task(bind=True, base=BaseTaskWithRetry, name="app.tasks.analytics.aggregate_daily_metrics")
def aggregate_daily_metrics(self) -> dict[str, Any]:
    """Aggregate daily metrics from observability repositories."""
    started = perf_counter()
    context = _request_context(self)
    task_logger.log_task_started(
        task_id=context["task_id"],
        task_name=context["task_name"],
        queue=context["queue"],
        retry_count=context["retry_count"],
    )
    task_metrics.record_task_started(context["task_name"], queue=context["queue"])

    report_time = datetime.now(UTC)
    report_name = "aggregate_daily_metrics"
    bucket = _report_bucket(report_name, report_time)

    try:
        claimed, reason = _claim_report_run(report_name, bucket)
        if not claimed:
            return {"status": "skipped", "reason": reason, "bucket": bucket}

        _update_progress(self, current=1, total=2, step="aggregate_queries")
        aggregates = _aggregate_daily_metrics(report_time)
        task_logger.log_task_progress(
            task_id=context["task_id"],
            task_name=context["task_name"],
            queue=context["queue"],
            progress={"step": "aggregate_queries", "bucket": bucket},
            retry_count=context["retry_count"],
        )

        _update_progress(self, current=2, total=2, step="persist_snapshot")
        persisted = _persist_report_snapshot(report_name, bucket, {"report_date": report_time.date().isoformat(), "metrics": aggregates})
        duration_seconds = perf_counter() - started
        payload = {
            "status": "completed",
            "bucket": bucket,
            "report_date": report_time.date().isoformat(),
            "metrics": aggregates,
            "persisted": persisted,
        }
        task_logger.log_task_success(
            task_id=context["task_id"],
            task_name=context["task_name"],
            queue=context["queue"],
            duration_ms=int(duration_seconds * 1000),
            retry_count=context["retry_count"],
        )
        task_metrics.record_task_success(context["task_name"], duration_seconds=duration_seconds, queue=context["queue"])
        return payload
    except Exception as exc:
        _handle_task_failure(context, started, exc)
        raise
    finally:
        try:
            _release_report_lock(report_name, bucket)
        except Exception:
            logger.debug("analytics_release_lock_failed", exc_info=True)


@task_app.task(bind=True, base=BaseTaskWithRetry, name="app.tasks.analytics.calculate_cost_reports")
def calculate_cost_reports(self) -> dict[str, Any]:
    """Calculate daily LLM cost reports from existing cost repositories."""
    started = perf_counter()
    context = _request_context(self)
    task_logger.log_task_started(
        task_id=context["task_id"],
        task_name=context["task_name"],
        queue=context["queue"],
        retry_count=context["retry_count"],
    )
    task_metrics.record_task_started(context["task_name"], queue=context["queue"])

    report_time = datetime.now(UTC)
    report_name = "calculate_cost_reports"
    bucket = _report_bucket(report_name, report_time)
    try:
        claimed, reason = _claim_report_run(report_name, bucket)
        if not claimed:
            return {"status": "skipped", "reason": reason, "bucket": bucket}

        _update_progress(self, current=1, total=2, step="calculate_costs")
        costs = _calculate_cost_reports(report_time)
        task_logger.log_task_progress(
            task_id=context["task_id"],
            task_name=context["task_name"],
            queue=context["queue"],
            progress={"step": "calculate_costs", "bucket": bucket},
            retry_count=context["retry_count"],
        )

        _update_progress(self, current=2, total=2, step="persist_snapshot")
        persisted = _persist_report_snapshot(report_name, bucket, {"report_date": report_time.date().isoformat(), "costs": costs})
        duration_seconds = perf_counter() - started
        payload = {
            "status": "completed",
            "bucket": bucket,
            "report_date": report_time.date().isoformat(),
            "costs": costs,
            "persisted": persisted,
        }
        task_logger.log_task_success(
            task_id=context["task_id"],
            task_name=context["task_name"],
            queue=context["queue"],
            duration_ms=int(duration_seconds * 1000),
            retry_count=context["retry_count"],
        )
        task_metrics.record_task_success(context["task_name"], duration_seconds=duration_seconds, queue=context["queue"])
        return payload
    except Exception as exc:
        _handle_task_failure(context, started, exc)
        raise
    finally:
        try:
            _release_report_lock(report_name, bucket)
        except Exception:
            logger.debug("analytics_release_lock_failed", exc_info=True)


@task_app.task(bind=True, base=BaseTaskWithRetry, name="app.tasks.analytics.generate_usage_insights")
def generate_usage_insights(self) -> dict[str, Any]:
    """Generate operational insights from aggregate and cost snapshots."""
    started = perf_counter()
    context = _request_context(self)
    task_logger.log_task_started(
        task_id=context["task_id"],
        task_name=context["task_name"],
        queue=context["queue"],
        retry_count=context["retry_count"],
    )
    task_metrics.record_task_started(context["task_name"], queue=context["queue"])

    report_time = datetime.now(UTC)
    report_name = "generate_usage_insights"
    bucket = _report_bucket(report_name, report_time)
    try:
        claimed, reason = _claim_report_run(report_name, bucket)
        if not claimed:
            return {"status": "skipped", "reason": reason, "bucket": bucket}

        _update_progress(self, current=1, total=3, step="aggregate_metrics")
        aggregates = _aggregate_daily_metrics(report_time)

        _update_progress(self, current=2, total=3, step="calculate_costs")
        costs = _calculate_cost_reports(report_time)

        _update_progress(self, current=3, total=3, step="build_insights")
        insights = _generate_usage_insights(aggregates, costs)
        task_logger.log_task_progress(
            task_id=context["task_id"],
            task_name=context["task_name"],
            queue=context["queue"],
            progress={"step": "build_insights", "bucket": bucket},
            retry_count=context["retry_count"],
        )

        persisted = _persist_report_snapshot(
            report_name,
            bucket,
            {
                "report_date": report_time.date().isoformat(),
                "insights": insights,
                "metrics": aggregates,
                "costs": costs,
            },
        )
        duration_seconds = perf_counter() - started
        payload = {
            "status": "completed",
            "bucket": bucket,
            "report_date": report_time.date().isoformat(),
            "insights": insights,
            "persisted": persisted,
        }
        task_logger.log_task_success(
            task_id=context["task_id"],
            task_name=context["task_name"],
            queue=context["queue"],
            duration_ms=int(duration_seconds * 1000),
            retry_count=context["retry_count"],
        )
        task_metrics.record_task_success(context["task_name"], duration_seconds=duration_seconds, queue=context["queue"])
        return payload
    except Exception as exc:
        _handle_task_failure(context, started, exc)
        raise
    finally:
        try:
            _release_report_lock(report_name, bucket)
        except Exception:
            logger.debug("analytics_release_lock_failed", exc_info=True)


__all__ = ["aggregate_daily_metrics", "calculate_cost_reports", "generate_usage_insights"]
