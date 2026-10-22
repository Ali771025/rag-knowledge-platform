"""Service-layer utilities for tracking and controlling Celery tasks.

This module maps Celery-native task states and payloads into application-friendly
responses without requiring task log records to exist.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal

from sqlalchemy import desc, select

from app.core.celery_app import CeleryConfigurationError, get_celery_app
from app.core.database import SessionLocal
from app.models.task_log import TaskLog

logger = logging.getLogger(__name__)

NormalizedTaskState = Literal["PENDING", "STARTED", "SUCCESS", "FAILURE", "RETRY"]

_ALLOWED_STATES: set[str] = {"PENDING", "STARTED", "SUCCESS", "FAILURE", "RETRY"}
_SENSITIVE_ERROR_MARKERS = ("token", "secret", "password", "api_key", "authorization")
_MAX_ERROR_LENGTH = 512
_MAX_TASK_NAME_LENGTH = 128
_MAX_QUEUE_LENGTH = 64


class TaskTracker:
    """Task status facade backed by Celery AsyncResult with optional DB enrichment."""

    def __init__(self, *, allow_terminate: bool = False) -> None:
        self.allow_terminate = allow_terminate
        self._celery_app: Any | None = None
        self._celery_error: str | None = None
        self._resolve_celery_app()

    def get_task_status(self, task_id: str) -> dict[str, Any]:
        """Return normalized status details for one task identifier."""
        safe_task_id = (task_id or "").strip()
        if not safe_task_id:
            return self._base_status_response(
                task_id=safe_task_id,
                state="PENDING",
                raw_state="PENDING",
                error="missing task id",
            )

        log_record = self._fetch_latest_task_log(safe_task_id)
        async_result = self._get_async_result(safe_task_id)

        if async_result is None:
            response = self._base_status_response(
                task_id=safe_task_id,
                state=self._status_from_log(log_record),
                raw_state=self._celery_error or "UNAVAILABLE",
            )
            return self._enrich_from_log(response, log_record)

        raw_state = str(getattr(async_result, "state", "PENDING") or "PENDING").upper()
        normalized_state = self._normalize_state(raw_state)
        info_payload = getattr(async_result, "info", None)
        result_payload = getattr(async_result, "result", None)
        progress = self._extract_progress(info_payload)
        error_message = self._extract_error_message(normalized_state, info_payload, result_payload)
        started_at, finished_at = self._resolve_timestamps(async_result=async_result, log_record=log_record)

        response = self._base_status_response(
            task_id=safe_task_id,
            state=normalized_state,
            raw_state=raw_state,
            progress=progress,
            error=error_message,
            started_at=started_at,
            finished_at=finished_at,
        )
        response["result_ready"] = bool(getattr(async_result, "ready", lambda: False)())
        response["successful"] = bool(getattr(async_result, "successful", lambda: False)())
        return self._enrich_from_log(response, log_record)

    def cancel_task(self, task_id: str) -> dict[str, Any]:
        """Safely revoke a Celery task without requiring worker termination."""
        safe_task_id = (task_id or "").strip()
        if not safe_task_id:
            return {
                "task_id": safe_task_id,
                "cancelled": False,
                "terminate": False,
                "state": "PENDING",
                "message": "missing task id",
            }

        app = self._get_celery_app()
        if app is None:
            return {
                "task_id": safe_task_id,
                "cancelled": False,
                "terminate": False,
                "state": "PENDING",
                "message": self._celery_error or "celery unavailable",
            }

        terminate = bool(self.allow_terminate)
        try:
            app.control.revoke(safe_task_id, terminate=terminate)
            return {
                "task_id": safe_task_id,
                "cancelled": True,
                "terminate": terminate,
                "state": "FAILURE",
                "message": "task revocation requested",
            }
        except Exception as exc:  # pragma: no cover - defensive service boundary
            logger.warning("task_revoke_failed", extra={"task_id": safe_task_id, "error": str(exc)})
            return {
                "task_id": safe_task_id,
                "cancelled": False,
                "terminate": terminate,
                "state": "FAILURE",
                "message": self._sanitize_error(str(exc)),
            }

    def list_active_tasks(self) -> list[dict[str, Any]]:
        """List currently active tasks reported by Celery workers."""
        app = self._get_celery_app()
        if app is None:
            return []

        try:
            inspector = app.control.inspect()
            active_by_worker = inspector.active() or {}
        except Exception as exc:  # pragma: no cover - broker/runtime protection
            logger.warning("task_inspect_active_failed", extra={"error": str(exc)})
            return []

        active_tasks: list[dict[str, Any]] = []
        for worker_name, worker_tasks in active_by_worker.items():
            for task in worker_tasks or []:
                raw_state = "STARTED"
                active_tasks.append(
                    {
                        "task_id": str(task.get("id") or ""),
                        "task_name": self._normalize_label(task.get("name"), _MAX_TASK_NAME_LENGTH),
                        "queue_name": self._extract_queue_name(task),
                        "state": self._normalize_state(raw_state),
                        "raw_state": raw_state,
                        "worker": self._normalize_label(worker_name, 128),
                        "started_at": self._safe_iso_from_timestamp(task.get("time_start")),
                    }
                )
        return active_tasks

    def _resolve_celery_app(self) -> None:
        app = self._get_celery_app()
        self._celery_app = app

    def _get_celery_app(self) -> Any | None:
        if self._celery_app is not None:
            return self._celery_app
        if self._celery_error is not None:
            return None
        try:
            self._celery_app = get_celery_app()
            return self._celery_app
        except CeleryConfigurationError as exc:
            self._celery_error = str(exc)
            logger.info("task_tracker_celery_unavailable", extra={"error": self._celery_error})
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._celery_error = str(exc)
            logger.warning("task_tracker_celery_unexpected_error", extra={"error": self._celery_error})
        return None

    def _get_async_result(self, task_id: str) -> Any | None:
        app = self._get_celery_app()
        if app is None:
            return None
        try:
            return app.AsyncResult(task_id)
        except Exception as exc:  # pragma: no cover
            logger.warning("task_async_result_lookup_failed", extra={"task_id": task_id, "error": str(exc)})
            return None

    def _fetch_latest_task_log(self, task_id: str) -> TaskLog | None:
        try:
            with SessionLocal() as session:
                stmt = select(TaskLog).where(TaskLog.task_id == task_id).order_by(desc(TaskLog.created_at)).limit(1)
                return session.scalar(stmt)
        except Exception as exc:
            logger.debug("task_log_enrichment_skipped", extra={"task_id": task_id, "error": str(exc)})
            return None

    def _status_from_log(self, log_record: TaskLog | None) -> NormalizedTaskState:
        if log_record is None:
            return "PENDING"
        return self._normalize_state(str(log_record.status or "PENDING").upper())

    def _normalize_state(self, raw_state: str) -> NormalizedTaskState:
        if raw_state in _ALLOWED_STATES:
            return raw_state  # type: ignore[return-value]
        if raw_state in {"RECEIVED"}:
            return "PENDING"
        if raw_state in {"REVOKED"}:
            return "FAILURE"
        return "FAILURE" if raw_state.endswith("FAIL") else "PENDING"

    def _extract_progress(self, payload: Any) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        progress = payload.get("progress")
        if isinstance(progress, dict):
            return {
                "current": progress.get("current"),
                "total": progress.get("total"),
                "percent": progress.get("percent"),
            }
        current = payload.get("current")
        total = payload.get("total")
        if current is None and total is None:
            return None
        percent: float | None = None
        if isinstance(current, (int, float)) and isinstance(total, (int, float)) and total > 0:
            percent = round((float(current) / float(total)) * 100.0, 2)
        return {"current": current, "total": total, "percent": percent}

    def _extract_error_message(self, state: NormalizedTaskState, info_payload: Any, result_payload: Any) -> str | None:
        if state not in {"FAILURE", "RETRY"}:
            return None
        for candidate in (info_payload, result_payload):
            if isinstance(candidate, dict):
                for key in ("error", "error_message", "message", "detail"):
                    value = candidate.get(key)
                    if isinstance(value, str) and value.strip():
                        return self._sanitize_error(value)
            if isinstance(candidate, BaseException):
                return self._sanitize_error(str(candidate))
            if isinstance(candidate, str) and candidate.strip():
                return self._sanitize_error(candidate)
        return "task execution failed" if state == "FAILURE" else "task scheduled for retry"

    def _resolve_timestamps(self, *, async_result: Any, log_record: TaskLog | None) -> tuple[str | None, str | None]:
        started_at = self._to_iso(getattr(log_record, "started_at", None))
        finished_at = self._to_iso(getattr(log_record, "finished_at", None))
        date_done = self._to_iso(getattr(async_result, "date_done", None))
        if finished_at is None:
            finished_at = date_done
        return started_at, finished_at

    def _enrich_from_log(self, response: dict[str, Any], log_record: TaskLog | None) -> dict[str, Any]:
        if log_record is None:
            return response
        response["task_name"] = self._normalize_label(log_record.task_name, _MAX_TASK_NAME_LENGTH)
        response["queue_name"] = self._normalize_label(log_record.queue_name, _MAX_QUEUE_LENGTH)
        response["retry_count"] = int(log_record.retry_count or 0)
        if response.get("started_at") is None:
            response["started_at"] = self._to_iso(log_record.started_at)
        if response.get("finished_at") is None:
            response["finished_at"] = self._to_iso(log_record.finished_at)
        if not response.get("error") and log_record.error_message:
            response["error"] = self._sanitize_error(log_record.error_message)
        return response

    def _base_status_response(
        self,
        *,
        task_id: str,
        state: NormalizedTaskState,
        raw_state: str,
        progress: dict[str, Any] | None = None,
        error: str | None = None,
        started_at: str | None = None,
        finished_at: str | None = None,
    ) -> dict[str, Any]:
        return {
            "task_id": task_id,
            "state": state,
            "raw_state": raw_state,
            "progress": progress,
            "started_at": started_at,
            "finished_at": finished_at,
            "error": error,
            "task_name": None,
            "queue_name": None,
            "retry_count": None,
        }

    def _sanitize_error(self, message: str) -> str:
        value = (message or "").strip()
        lowered = value.lower()
        if any(marker in lowered for marker in _SENSITIVE_ERROR_MARKERS):
            return "error message redacted"
        if len(value) > _MAX_ERROR_LENGTH:
            return f"{value[:_MAX_ERROR_LENGTH]}..."
        return value

    def _extract_queue_name(self, task_data: dict[str, Any]) -> str | None:
        delivery_info = task_data.get("delivery_info") if isinstance(task_data, dict) else None
        if isinstance(delivery_info, dict):
            queue = delivery_info.get("routing_key") or delivery_info.get("exchange")
            return self._normalize_label(queue, _MAX_QUEUE_LENGTH)
        return None

    def _safe_iso_from_timestamp(self, value: Any) -> str | None:
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
            except Exception:
                return None
        return self._to_iso(value)

    def _to_iso(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc).isoformat()
        if isinstance(value, str):
            return value
        return str(value)

    def _normalize_label(self, value: Any, max_len: int) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        return text[:max_len]

