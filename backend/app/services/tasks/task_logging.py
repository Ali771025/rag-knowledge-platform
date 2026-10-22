"""Structured task logging adapter for Celery-oriented service workflows.

This logger never raises to callers so task execution is not disrupted by
observability failures.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_SENSITIVE_KEYS = {"password", "secret", "token", "api_key", "authorization"}
_MAX_TEXT_LENGTH = 512
_MAX_COLLECTION_ITEMS = 20


class TaskLogger:
    """Best-effort task lifecycle logger with structured/fallback sinks."""

    def __init__(self) -> None:
        self._structured_logger: Any | None = None
        try:
            from app.observability.structured_logger import get_structured_logger

            self._structured_logger = get_structured_logger(logger_name="app.tasks")
        except Exception:
            self._structured_logger = None

    def log_task_started(
        self,
        *,
        task_id: str,
        task_name: str,
        queue: str | None = None,
        retry_count: int = 0,
    ) -> None:
        self._emit(
            level="info",
            event="task_started",
            payload=self._build_payload(
                task_id=task_id,
                task_name=task_name,
                queue=queue,
                status="STARTED",
                retry_count=retry_count,
            ),
        )

    def log_task_progress(
        self,
        *,
        task_id: str,
        task_name: str,
        queue: str | None = None,
        progress: dict[str, Any] | None = None,
        retry_count: int = 0,
    ) -> None:
        payload = self._build_payload(
            task_id=task_id,
            task_name=task_name,
            queue=queue,
            status="STARTED",
            retry_count=retry_count,
        )
        payload["progress"] = self._sanitize(progress or {})
        self._emit(level="info", event="task_progress", payload=payload)

    def log_task_success(
        self,
        *,
        task_id: str,
        task_name: str,
        queue: str | None = None,
        duration_ms: int | None = None,
        retry_count: int = 0,
    ) -> None:
        self._emit(
            level="info",
            event="task_success",
            payload=self._build_payload(
                task_id=task_id,
                task_name=task_name,
                queue=queue,
                status="SUCCESS",
                duration_ms=duration_ms,
                retry_count=retry_count,
            ),
        )

    def log_task_retry(
        self,
        *,
        task_id: str,
        task_name: str,
        queue: str | None = None,
        retry_count: int,
        error: str | None = None,
    ) -> None:
        self._emit(
            level="warning",
            event="task_retry",
            payload=self._build_payload(
                task_id=task_id,
                task_name=task_name,
                queue=queue,
                status="RETRY",
                retry_count=retry_count,
                error=error,
            ),
        )

    def log_task_failure(
        self,
        *,
        task_id: str,
        task_name: str,
        queue: str | None = None,
        duration_ms: int | None = None,
        retry_count: int = 0,
        error: str | None = None,
    ) -> None:
        self._emit(
            level="error",
            event="task_failure",
            payload=self._build_payload(
                task_id=task_id,
                task_name=task_name,
                queue=queue,
                status="FAILURE",
                duration_ms=duration_ms,
                retry_count=retry_count,
                error=error,
            ),
        )

    def _build_payload(
        self,
        *,
        task_id: str,
        task_name: str,
        queue: str | None,
        status: str,
        duration_ms: int | None = None,
        retry_count: int | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "task_id": self._truncate(task_id),
            "task_name": self._truncate(task_name, max_len=128),
            "queue": self._truncate(queue, max_len=64),
            "status": status,
            "duration_ms": int(duration_ms) if duration_ms is not None else None,
            "retry_count": int(retry_count or 0),
            "error": self._truncate(error) if error else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return self._sanitize(payload)

    def _emit(self, *, level: str, event: str, payload: dict[str, Any]) -> None:
        try:
            if self._structured_logger is not None:
                message = f"celery_{event}"
                state = str(payload.get("status") or "").lower() or None
                if level == "error":
                    self._structured_logger.error(message, state=state, metadata=payload)
                elif level == "warning":
                    self._structured_logger.warning(message, state=state, metadata=payload)
                else:
                    self._structured_logger.info(message, state=state, metadata=payload)
                return

            fallback_payload = {"event": event, "task": payload}
            if level == "error":
                logger.error("task_lifecycle_event", extra=fallback_payload)
            elif level == "warning":
                logger.warning("task_lifecycle_event", extra=fallback_payload)
            else:
                logger.info("task_lifecycle_event", extra=fallback_payload)
        except Exception:  # pragma: no cover - logging adapter must not fail tasks
            logger.debug("task_logging_emit_failed", exc_info=True)

    def _sanitize(self, value: Any) -> Any:
        if isinstance(value, dict):
            sanitized: dict[str, Any] = {}
            for key, item in list(value.items())[:_MAX_COLLECTION_ITEMS]:
                key_text = self._truncate(str(key), max_len=64) or ""
                if key_text.lower() in _SENSITIVE_KEYS:
                    sanitized[key_text] = "[REDACTED]"
                    continue
                sanitized[key_text] = self._sanitize(item)
            return sanitized
        if isinstance(value, (list, tuple, set)):
            return [self._sanitize(item) for item in list(value)[:_MAX_COLLECTION_ITEMS]]
        if isinstance(value, str):
            lowered = value.lower()
            if any(marker in lowered for marker in _SENSITIVE_KEYS):
                return "[REDACTED]"
            return self._truncate(value)
        return value

    def _truncate(self, value: Any, *, max_len: int = _MAX_TEXT_LENGTH) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        if len(text) <= max_len:
            return text
        return f"{text[:max_len]}..."

