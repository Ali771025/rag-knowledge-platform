"""Celery worker and queue health monitoring utilities."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from app.core.celery_app import CeleryConfigurationError, get_celery_app
from app.core.database import SessionLocal
from app.core.redis_client import get_redis_client
from app.models.task_log import TaskLog
from app.services.tasks.task_metrics import TaskMetrics

logger = logging.getLogger(__name__)

_KNOWN_QUEUES = {"default", "knowledge_ingestion", "memory_management", "analytics"}
_TASK_FAILURE_WINDOW_MINUTES = 60
_HIGH_FAILURE_THRESHOLD = 20
_HIGH_FAILURE_RATE_THRESHOLD = 0.3


class WorkerMonitor:
    """Defensive monitoring facade for Celery worker status and queue health."""

    def __init__(self) -> None:
        self._task_metrics = TaskMetrics()

    def get_health(self) -> dict[str, Any]:
        app = self._get_celery_app()
        if app is None:
            return {
                "global_status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "celery_unavailable",
                "worker_counts_per_queue": {},
                "queue_sizes": {},
                "missing_workers": [],
                "overloaded_workers": [],
                "recent_failures": self._recent_failure_summary(),
            }

        inspector = app.control.inspect()
        ping_data = self._safe_inspect(inspector.ping)
        stats_data = self._safe_inspect(inspector.stats)
        active_data = self._safe_inspect(inspector.active)
        reserved_data = self._safe_inspect(inspector.reserved)
        active_queues_data = self._safe_inspect(inspector.active_queues)

        expected_queues = self._expected_queues(app)
        worker_counts_per_queue = self._worker_counts_per_queue(active_queues_data, expected_queues)
        queue_sizes = self._queue_sizes(expected_queues)
        overloaded_workers = self._overload_signals(active_data, reserved_data, stats_data)
        missing_workers = [queue for queue, count in worker_counts_per_queue.items() if count <= 0]
        recent_failures = self._recent_failure_summary()

        global_status = "healthy"
        if not ping_data:
            global_status = "unhealthy"
        elif missing_workers or overloaded_workers:
            global_status = "degraded"
        if recent_failures["high_failure_signal"]:
            global_status = "degraded"

        return {
            "global_status": global_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "worker_count": len(ping_data),
            "workers": sorted(ping_data.keys()),
            "worker_counts_per_queue": worker_counts_per_queue,
            "queue_sizes": queue_sizes,
            "missing_workers": missing_workers,
            "overloaded_workers": overloaded_workers,
            "recent_failures": recent_failures,
        }

    def _get_celery_app(self) -> Any | None:
        try:
            return get_celery_app()
        except CeleryConfigurationError as exc:
            logger.info("worker_monitor_celery_unavailable", extra={"error": str(exc)})
        except Exception as exc:
            logger.warning("worker_monitor_celery_lookup_failed", extra={"error": str(exc)})
        return None

    def _safe_inspect(self, fn: Any) -> dict[str, Any]:
        try:
            data = fn()
            return data or {}
        except Exception as exc:
            logger.warning("worker_monitor_inspect_failed", extra={"error": str(exc)})
            return {}

    def _expected_queues(self, app: Any) -> list[str]:
        queues: set[str] = set(_KNOWN_QUEUES)
        try:
            default_queue = str(getattr(app.conf, "task_default_queue", "default") or "default")
            queues.add(default_queue)
            routes = getattr(app.conf, "task_routes", {}) or {}
            for route_config in routes.values():
                if isinstance(route_config, dict):
                    queue_name = route_config.get("queue")
                    if queue_name:
                        queues.add(str(queue_name))
        except Exception:
            pass
        return sorted(queues)

    def _worker_counts_per_queue(self, active_queues_data: dict[str, Any], expected_queues: list[str]) -> dict[str, int]:
        counts = {queue: 0 for queue in expected_queues}
        for _worker_name, queues in (active_queues_data or {}).items():
            for queue_info in queues or []:
                if not isinstance(queue_info, dict):
                    continue
                queue_name = str(queue_info.get("name") or "").strip()
                if not queue_name:
                    continue
                counts[queue_name] = counts.get(queue_name, 0) + 1
        return counts

    def _queue_sizes(self, queue_names: list[str]) -> dict[str, int]:
        sizes: dict[str, int] = {}
        try:
            client = get_redis_client()
        except Exception as exc:
            logger.warning("worker_monitor_queue_sizes_unavailable", extra={"error": str(exc)})
            return {queue: -1 for queue in queue_names}

        for queue_name in queue_names:
            size = -1
            try:
                size = int(client.llen(queue_name))
                self._task_metrics.record_queue_size(queue_name, size)
            except Exception:
                size = -1
            sizes[queue_name] = size
        return sizes

    def _overload_signals(
        self,
        active_data: dict[str, Any],
        reserved_data: dict[str, Any],
        stats_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        overloaded: list[dict[str, Any]] = []
        worker_names = set(active_data.keys()) | set(reserved_data.keys()) | set(stats_data.keys())
        for worker_name in worker_names:
            active_count = len(active_data.get(worker_name, []) or [])
            reserved_count = len(reserved_data.get(worker_name, []) or [])
            total_queued = active_count + reserved_count
            concurrency = self._worker_concurrency(stats_data.get(worker_name, {}))
            overloaded_flag = False
            if concurrency > 0 and total_queued > max(concurrency * 2, 20):
                overloaded_flag = True
            if total_queued > 100:
                overloaded_flag = True
            if overloaded_flag:
                overloaded.append(
                    {
                        "worker": worker_name,
                        "active_tasks": active_count,
                        "reserved_tasks": reserved_count,
                        "concurrency": concurrency,
                    }
                )
        return overloaded

    def _worker_concurrency(self, worker_stats: dict[str, Any]) -> int:
        if not isinstance(worker_stats, dict):
            return 0
        pool = worker_stats.get("pool")
        if isinstance(pool, dict):
            try:
                return int(pool.get("max-concurrency") or 0)
            except Exception:
                return 0
        return 0

    def _recent_failure_summary(self) -> dict[str, Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=_TASK_FAILURE_WINDOW_MINUTES)
        try:
            with SessionLocal() as session:
                failed_stmt = select(TaskLog).where(TaskLog.created_at >= cutoff, TaskLog.status == "failed")
                retry_stmt = select(TaskLog).where(TaskLog.created_at >= cutoff, TaskLog.status == "retrying")
                started_stmt = select(TaskLog).where(TaskLog.created_at >= cutoff)

                failures = len(list(session.scalars(failed_stmt).all()))
                retries = len(list(session.scalars(retry_stmt).all()))
                total = len(list(session.scalars(started_stmt).all()))
        except Exception as exc:
            logger.debug("worker_monitor_failure_summary_unavailable", extra={"error": str(exc)})
            return {
                "window_minutes": _TASK_FAILURE_WINDOW_MINUTES,
                "failures": None,
                "retries": None,
                "total_records": None,
                "high_failure_signal": False,
            }

        failure_rate = (failures / total) if total > 0 else 0.0
        high_failure_signal = failures >= _HIGH_FAILURE_THRESHOLD or failure_rate >= _HIGH_FAILURE_RATE_THRESHOLD
        return {
            "window_minutes": _TASK_FAILURE_WINDOW_MINUTES,
            "failures": failures,
            "retries": retries,
            "total_records": total,
            "failure_rate": round(failure_rate, 4),
            "high_failure_signal": high_failure_signal,
        }

