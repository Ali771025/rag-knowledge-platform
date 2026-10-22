"""Background memory-management tasks.

Tasks stay orchestration-focused and integrate with existing conversation-memory
services via thin adapters.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from time import perf_counter
from typing import Any
from uuid import UUID

from app.core.celery_app import CeleryConfigurationError, get_celery_app
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.redis_client import get_redis_client
from app.core.task_base import BaseTaskWithRetry
from app.models.memory_summary import MemorySummary
from app.models.session import Session
from app.services.tasks.task_logging import TaskLogger
from app.services.tasks.task_metrics import TaskMetrics

logger = logging.getLogger(__name__)
task_logger = TaskLogger()
task_metrics = TaskMetrics()

_RAW_MESSAGE_WINDOW = 10
_MAX_MESSAGES = 5000
_MAX_SUMMARY_LENGTH = 4000
_SESSION_EXPIRY_DAYS = 30


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
        logger.warning("celery_not_configured_for_memory_tasks", extra={"error": str(exc)})
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


def _log_task_failure(context: dict[str, Any], started: float, exc: Exception) -> None:
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


def _update_progress(task: Any, *, current: int, total: int, step: str, **extra: Any) -> None:
    meta = {
        "progress": {
            "current": current,
            "total": total,
            "percent": round((current / total) * 100.0, 2) if total > 0 else None,
            "step": step,
        },
        **extra,
    }
    try:
        task.update_state(state="STARTED", meta=meta)
    except Exception:
        logger.debug("memory_task_progress_update_failed", exc_info=True)


def _run_async(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    raise RuntimeError("memory task adapters cannot run async I/O inside an active event loop")


def _validate_session_id(session_id: str) -> UUID:
    try:
        return UUID(str(session_id).strip())
    except Exception as exc:
        raise ValueError("session_id must be a valid UUID string") from exc


def _validate_messages(conversation_messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(conversation_messages, list):
        raise ValueError("conversation_messages must be a list")
    if len(conversation_messages) > _MAX_MESSAGES:
        raise ValueError("conversation_messages exceeds supported limit")

    cleaned: list[dict[str, Any]] = []
    for item in conversation_messages:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).strip().lower()
        content = str(item.get("message", item.get("content", ""))).strip()
        if not role or not content:
            continue
        metadata = dict(item.get("metadata", {}) or {})
        cleaned.append({"role": role, "content": content, "metadata": metadata})
    return cleaned


def _idempotency_key(session_id: UUID, messages: list[dict[str, Any]]) -> str:
    digest_input = "|".join(f"{msg['role']}:{msg['content']}" for msg in messages)
    digest = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()
    return f"{session_id}:{digest}"


def _load_recent_conversation_history(session_id: UUID, provided_messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if provided_messages:
        return _validate_messages(provided_messages)

    from app.conversation_memory.session_manager import ConversationSessionManager

    manager = ConversationSessionManager()
    try:
        session_state = manager.load_session(str(session_id))
    except Exception:
        return []

    turns = list((session_state.metadata or {}).get("turns", []))
    messages: list[dict[str, Any]] = []
    for turn in turns:
        if isinstance(turn, dict):
            role = str(turn.get("role", "")).strip().lower()
            content = str(turn.get("message", turn.get("content", ""))).strip()
            if role and content:
                messages.append({"role": role, "content": content, "metadata": dict(turn.get("metadata", {}) or {})})
    return _validate_messages(messages)


def _extract_key_preferences(messages: list[dict[str, Any]]) -> dict[str, Any]:
    preferences: dict[str, Any] = {"mentions": []}
    mentions: set[str] = set()
    for item in messages:
        metadata = item.get("metadata", {})
        if isinstance(metadata, dict):
            declared = metadata.get("preferences")
            if isinstance(declared, dict):
                preferences.update(declared)
        content = str(item.get("content", "")).lower()
        if "prefer" in content:
            compact = content[:120]
            if compact not in mentions:
                mentions.add(compact)
    preferences["mentions"] = sorted(mentions)[:10]
    return preferences


def _extract_policy_markers(messages: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    milestones: list[dict[str, Any]] = []
    knowledge_progression: list[dict[str, Any]] = []
    for item in messages:
        metadata = item.get("metadata", {})
        if not isinstance(metadata, dict):
            continue
        if metadata.get("onboarding_milestone") is True:
            milestones.append(item)
        if metadata.get("knowledge_progression") is True:
            knowledge_progression.append(item)
    return {
        "onboarding_milestones": milestones,
        "knowledge_progression": knowledge_progression,
    }


def _generate_summary(messages: list[dict[str, Any]]) -> str:
    from app.conversation_memory.memory_policy import summarize_turns
    from app.conversation_memory.models import ConversationRole, ConversationTurn

    turns: list[ConversationTurn] = []
    for item in messages:
        role_text = str(item.get("role", "user")).strip().lower()
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        role = ConversationRole.USER
        if role_text in {"assistant", "system"}:
            role = ConversationRole(role_text)
        turns.append(ConversationTurn(role=role, message=content, metadata=dict(item.get("metadata", {}))))
    summary = summarize_turns(turns)
    if len(summary) > _MAX_SUMMARY_LENGTH:
        return f"{summary[:_MAX_SUMMARY_LENGTH]}..."
    return summary


def _store_compressed_memory(
    *,
    session_id: UUID,
    summary: str,
    raw_tail: list[dict[str, Any]],
    markers: dict[str, list[dict[str, Any]]],
    preferences: dict[str, Any],
    idempotency_key: str,
) -> dict[str, Any]:
    from app.conversation_memory.session_manager import ConversationSessionManager

    manager = ConversationSessionManager()
    try:
        session_state = manager.load_session(str(session_id))
    except Exception:
        session_state = None

    stored_in_redis = False
    if session_state is not None:
        turns_payload = [
            {
                "role": item.get("role", "user"),
                "message": item.get("content", ""),
                "metadata": dict(item.get("metadata", {}) or {}),
            }
            for item in raw_tail
        ]
        metadata = dict(session_state.metadata or {})
        metadata["memory_summary"] = summary
        metadata["turns"] = turns_payload
        metadata["summary_key"] = idempotency_key
        metadata["preferences"] = preferences
        metadata["onboarding_milestones"] = markers["onboarding_milestones"]
        metadata["knowledge_progression"] = markers["knowledge_progression"]

        updated_state = session_state.model_copy(update={"metadata": metadata, "updated_at": datetime.now(timezone.utc)}, deep=True)
        redis_repo = manager.redis_repository
        _run_async(redis_repo.update_session(updated_state, ttl_seconds=manager.default_ttl_seconds))
        stored_in_redis = True

    stored_summary = False
    with SessionLocal() as session:
        exists_stmt = (
            session.query(MemorySummary)
            .filter(MemorySummary.session_id == session_id, MemorySummary.summary == summary)
            .order_by(MemorySummary.created_at.desc())
        )
        if exists_stmt.first() is None:
            record = MemorySummary(session_id=session_id, summary=summary)
            session.add(record)
            session.commit()
            stored_summary = True

        session_row = session.get(Session, session_id)
        if session_row is not None:
            turns_payload = [
                {
                    "role": item.get("role", "user"),
                    "message": item.get("content", ""),
                    "metadata": dict(item.get("metadata", {}) or {}),
                }
                for item in raw_tail
            ]
            state = dict(session_row.state or {})
            state["memory_summary"] = summary
            state["summary_key"] = idempotency_key
            state["preferences"] = preferences
            state["onboarding_milestones"] = markers["onboarding_milestones"]
            state["knowledge_progression"] = markers["knowledge_progression"]
            state["turns"] = turns_payload
            session_row.state = state
            session.add(session_row)
            session.commit()

    return {
        "stored_in_redis": stored_in_redis,
        "stored_summary_row": stored_summary,
        "summary_key": idempotency_key,
    }


def _already_summarized(session_id: UUID, key: str) -> bool:
    with SessionLocal() as session:
        row = session.get(Session, session_id)
        if row is None:
            return False
        state = dict(row.state or {})
        return str(state.get("summary_key", "")).strip() == key


def _apply_retention_policy(session_id: UUID, max_turns: int) -> int:
    from app.conversation_memory.session_manager import ConversationSessionManager

    manager = ConversationSessionManager(max_turns=max_turns)
    try:
        state = manager.load_session(str(session_id))
    except Exception:
        return 0

    updated = manager.memory_policy.apply_memory_policy(state, max_turns=max_turns)
    turns_count = len(list((updated.metadata or {}).get("turns", [])))
    _run_async(manager.redis_repository.update_session(updated, ttl_seconds=manager.default_ttl_seconds))
    return turns_count


def _session_key_pattern() -> str:
    prefix = str(getattr(settings, "redis_key_prefix", "ragai:session"))
    return f"{prefix}:*"


def _parse_session_id_from_key(redis_key: str) -> str | None:
    parts = str(redis_key).split(":")
    if not parts:
        return None
    candidate = parts[-1].strip()
    return candidate or None


def _list_expired_sessions() -> list[str]:
    """Find stale sessions based on last-updated timestamp."""
    stale: list[str] = []
    client = get_redis_client()
    cutoff = datetime.now(timezone.utc) - timedelta(days=_SESSION_EXPIRY_DAYS)
    for redis_key in client.scan_iter(match=_session_key_pattern()):
        raw = client.get(redis_key)
        if not raw:
            continue
        try:
            from app.conversation_memory.serializers import deserialize_session_state

            state = deserialize_session_state(raw)
            updated_at = state.updated_at
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
            if updated_at < cutoff:
                candidate = _parse_session_id_from_key(str(redis_key))
                if candidate:
                    stale.append(candidate)
        except Exception:
            continue
    return stale


def _archive_or_delete_session(session_id: str) -> bool:
    from app.conversation_memory.session_manager import ConversationSessionManager

    manager = ConversationSessionManager()
    try:
        manager.delete_session(session_id)
    except Exception:
        return False
    return True


def _load_context_targets(user_id: str | None, session_id: str | None) -> list[str]:
    if session_id:
        return [session_id]
    if user_id:
        try:
            user_uuid = UUID(user_id)
        except Exception:
            return []
        with SessionLocal() as session:
            rows = session.query(Session.id).filter(Session.user_id == user_uuid).all()
            return [str(row[0]) for row in rows]
    return []


def _rebuild_context_for_target(target_id: str) -> dict[str, Any]:
    from app.conversation_memory.context_manager import build_context
    from app.conversation_memory.session_manager import ConversationSessionManager

    manager = ConversationSessionManager()
    try:
        state = manager.load_session(target_id)
    except Exception:
        return {"target_id": target_id, "rebuilt": False, "reason": "session_missing"}

    turns = list((state.metadata or {}).get("turns", []))
    latest = ""
    if turns and isinstance(turns[-1], dict):
        latest = str(turns[-1].get("message", turns[-1].get("content", "")))
    context = build_context(session_state=state, new_user_message=latest, max_turns=_RAW_MESSAGE_WINDOW)
    metadata = dict(state.metadata or {})
    metadata["context_rebuilt_at"] = datetime.now(timezone.utc).isoformat()
    updated = state.model_copy(update={"metadata": metadata, "updated_at": datetime.now(timezone.utc)}, deep=True)
    _run_async(manager.redis_repository.update_session(updated, ttl_seconds=manager.default_ttl_seconds))
    return {"target_id": target_id, "rebuilt": True, "turns_in_context": len(context.turns)}


@task_app.task(bind=True, base=BaseTaskWithRetry, name="app.tasks.memory.summarize_conversation_memory")
def summarize_conversation_memory(self, session_id: str, conversation_messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize older messages and keep the latest raw window."""
    started = perf_counter()
    context = _request_context(self)
    task_logger.log_task_started(
        task_id=context["task_id"],
        task_name=context["task_name"],
        queue=context["queue"],
        retry_count=context["retry_count"],
    )
    task_metrics.record_task_started(context["task_name"], queue=context["queue"])

    session_uuid = _validate_session_id(session_id)
    history = _load_recent_conversation_history(session_uuid, conversation_messages)
    if not history:
        return {"status": "skipped", "session_id": str(session_uuid), "reason": "missing_session_or_empty_history"}

    dedupe_key = _idempotency_key(session_uuid, history)
    if _already_summarized(session_uuid, dedupe_key):
        duration_seconds = perf_counter() - started
        task_logger.log_task_success(
            task_id=context["task_id"],
            task_name=context["task_name"],
            queue=context["queue"],
            duration_ms=int(duration_seconds * 1000),
            retry_count=context["retry_count"],
        )
        task_metrics.record_task_success(context["task_name"], duration_seconds=duration_seconds, queue=context["queue"])
        return {"status": "skipped", "session_id": str(session_uuid), "reason": "already_summarized", "summary_key": dedupe_key}

    try:
        _update_progress(self, current=1, total=5, step="load_history")
        summary_candidates = history[:-_RAW_MESSAGE_WINDOW] if len(history) > _RAW_MESSAGE_WINDOW else []
        raw_tail = history[-_RAW_MESSAGE_WINDOW:]
        markers = _extract_policy_markers(history)

        _update_progress(self, current=2, total=5, step="extract_preferences")
        preferences = _extract_key_preferences(history)

        _update_progress(self, current=3, total=5, step="generate_summary")
        summary = _generate_summary(summary_candidates) if summary_candidates else "No summary required."

        _update_progress(self, current=4, total=5, step="store_memory")
        storage_result = _store_compressed_memory(
            session_id=session_uuid,
            summary=summary,
            raw_tail=raw_tail,
            markers=markers,
            preferences=preferences,
            idempotency_key=dedupe_key,
        )

        _update_progress(self, current=5, total=5, step="apply_retention")
        retained_raw_count = _apply_retention_policy(session_uuid, _RAW_MESSAGE_WINDOW)

        duration_seconds = perf_counter() - started
        duration_ms = int(duration_seconds * 1000)
        payload = {
            "status": "completed",
            "session_id": str(session_uuid),
            "summary_key": dedupe_key,
            "retained_raw_messages": retained_raw_count,
            "summarized_messages": len(summary_candidates),
            "onboarding_milestones_preserved": len(markers["onboarding_milestones"]),
            "knowledge_progression_preserved": len(markers["knowledge_progression"]),
            "storage_result": storage_result,
        }
        task_logger.log_task_success(
            task_id=context["task_id"],
            task_name=context["task_name"],
            queue=context["queue"],
            duration_ms=duration_ms,
            retry_count=context["retry_count"],
        )
        task_metrics.record_task_success(context["task_name"], duration_seconds=duration_seconds, queue=context["queue"])
        return payload
    except Exception as exc:
        _log_task_failure(context, started, exc)
        raise


@task_app.task(bind=True, base=BaseTaskWithRetry, name="app.tasks.memory.cleanup_expired_sessions")
def cleanup_expired_sessions(self) -> dict[str, Any]:
    """Delete stale sessions; repeat-safe and idempotent."""
    started = perf_counter()
    context = _request_context(self)
    task_logger.log_task_started(
        task_id=context["task_id"],
        task_name=context["task_name"],
        queue=context["queue"],
        retry_count=context["retry_count"],
    )
    task_metrics.record_task_started(context["task_name"], queue=context["queue"])

    try:
        expired_session_ids = _list_expired_sessions()
        total = len(expired_session_ids)
        cleaned = 0
        failed = 0

        for index, expired_id in enumerate(expired_session_ids, start=1):
            _update_progress(self, current=index, total=max(total, 1), step="cleanup", session_id=expired_id)
            if _archive_or_delete_session(expired_id):
                cleaned += 1
            else:
                failed += 1

        duration_seconds = perf_counter() - started
        duration_ms = int(duration_seconds * 1000)
        payload = {
            "status": "completed",
            "expired_sessions": total,
            "cleaned_sessions": cleaned,
            "failed_sessions": failed,
        }
        task_logger.log_task_success(
            task_id=context["task_id"],
            task_name=context["task_name"],
            queue=context["queue"],
            duration_ms=duration_ms,
            retry_count=context["retry_count"],
        )
        task_metrics.record_task_success(context["task_name"], duration_seconds=duration_seconds, queue=context["queue"])
        return payload
    except Exception as exc:
        _log_task_failure(context, started, exc)
        raise


@task_app.task(bind=True, base=BaseTaskWithRetry, name="app.tasks.memory.rebuild_user_context")
def rebuild_user_context(self, user_id: str | None = None, session_id: str | None = None) -> dict[str, Any]:
    """Rebuild long-term context for one session or all sessions for a user."""
    started = perf_counter()
    context = _request_context(self)
    task_logger.log_task_started(
        task_id=context["task_id"],
        task_name=context["task_name"],
        queue=context["queue"],
        retry_count=context["retry_count"],
    )
    task_metrics.record_task_started(context["task_name"], queue=context["queue"])

    resolved_user_id = str(user_id or "").strip() or None
    resolved_session_id = str(session_id or "").strip() or None
    if resolved_user_id is None and resolved_session_id is None:
        raise ValueError("either user_id or session_id must be provided")

    try:
        targets = _load_context_targets(resolved_user_id, resolved_session_id)
        rebuilt: list[dict[str, Any]] = []
        for index, target_id in enumerate(targets, start=1):
            _update_progress(self, current=index, total=max(len(targets), 1), step="rebuild_context", target=target_id)
            rebuilt.append(_rebuild_context_for_target(target_id))

        duration_seconds = perf_counter() - started
        duration_ms = int(duration_seconds * 1000)
        payload = {
            "status": "completed",
            "user_id": resolved_user_id,
            "session_id": resolved_session_id,
            "targets": len(targets),
            "rebuilt": rebuilt,
        }
        task_logger.log_task_success(
            task_id=context["task_id"],
            task_name=context["task_name"],
            queue=context["queue"],
            duration_ms=duration_ms,
            retry_count=context["retry_count"],
        )
        task_metrics.record_task_success(context["task_name"], duration_seconds=duration_seconds, queue=context["queue"])
        return payload
    except Exception as exc:
        _log_task_failure(context, started, exc)
        raise


__all__ = ["summarize_conversation_memory", "cleanup_expired_sessions", "rebuild_user_context"]
