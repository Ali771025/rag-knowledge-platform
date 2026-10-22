"""Shared Celery task base with production-safe retry defaults.

The class in this module is intentionally generic so future task modules can
inherit without coupling to application-specific services.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from celery import Task

logger = logging.getLogger(__name__)

try:
    from kombu.exceptions import OperationalError as KombuOperationalError
except Exception:  # pragma: no cover - defensive import for optional runtime paths
    KombuOperationalError = Exception  # type: ignore[assignment]


TRANSIENT_EXCEPTIONS: tuple[type[BaseException], ...] = (
    TimeoutError,
    ConnectionError,
    KombuOperationalError,
)


class BaseTaskWithRetry(Task):
    """Base Celery Task with bounded retries and lifecycle hook helpers."""

    abstract = True
    autoretry_for = TRANSIENT_EXCEPTIONS
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True
    max_retries = 3

    def is_retryable_error(self, exc: BaseException) -> bool:
        """Return True when an exception belongs to the retryable set."""
        return isinstance(exc, self.autoretry_for)

    def is_non_retryable_error(self, exc: BaseException) -> bool:
        """Return True when an exception should fail immediately."""
        return not self.is_retryable_error(exc)

    def build_lifecycle_metadata(
        self,
        *,
        task_id: str | None,
        status: str,
        args: tuple[Any, ...] | None = None,
        kwargs: dict[str, Any] | None = None,
        exc: BaseException | None = None,
        retval: Any = None,
    ) -> dict[str, Any]:
        """Capture stable lifecycle metadata for future persistence/metrics."""
        request = getattr(self, "request", None)
        delivery_info = getattr(request, "delivery_info", {}) or {}
        queue_name = delivery_info.get("routing_key") if isinstance(delivery_info, dict) else None
        return {
            "task_id": task_id,
            "task_name": self.name,
            "queue_name": queue_name,
            "status": status,
            "retry_count": int(getattr(request, "retries", 0) or 0),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "args_count": len(args or ()),
            "kwargs_keys": sorted((kwargs or {}).keys()),
            "error_type": exc.__class__.__name__ if exc else None,
            "error_message": str(exc) if exc else None,
            "result_type": type(retval).__name__ if retval is not None else None,
        }

    def log_lifecycle_event(self, event: str, metadata: dict[str, Any]) -> None:
        """Best-effort hook for lifecycle logging/observability."""
        try:
            logger.info(event, extra={"task": metadata})
        except Exception:  # pragma: no cover - keep task lifecycle hooks non-fatal
            logger.debug("task_lifecycle_log_failed", exc_info=True)

    def on_failure(
        self,
        exc: BaseException,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        einfo: Any,
    ) -> None:
        """Placeholder failure hook for future persistence integrations."""
        metadata = self.build_lifecycle_metadata(task_id=task_id, status="failed", args=args, kwargs=kwargs, exc=exc)
        self.log_lifecycle_event("task_failed", metadata)
        super().on_failure(exc, task_id, args, kwargs, einfo)

    def on_retry(
        self,
        exc: BaseException,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        einfo: Any,
    ) -> None:
        """Placeholder retry hook for future persistence integrations."""
        metadata = self.build_lifecycle_metadata(task_id=task_id, status="retrying", args=args, kwargs=kwargs, exc=exc)
        self.log_lifecycle_event("task_retrying", metadata)
        super().on_retry(exc, task_id, args, kwargs, einfo)

    def on_success(
        self,
        retval: Any,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> None:
        """Placeholder success hook for future persistence integrations."""
        metadata = self.build_lifecycle_metadata(
            task_id=task_id,
            status="succeeded",
            args=args,
            kwargs=kwargs,
            retval=retval,
        )
        self.log_lifecycle_event("task_succeeded", metadata)
        super().on_success(retval, task_id, args, kwargs)
