"""Central Celery application bootstrap and queue routing configuration.

This module is intentionally import-safe:
- If Celery is not installed, imports still work.
- If queue settings are incomplete, imports still work.

Callers that actually need a working Celery instance should use
``get_celery_app()`` which raises a clear configuration error when needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.core.celery_schedule import get_celery_beat_schedule

try:
    from celery import Celery
except Exception:  # pragma: no cover - optional dependency safety
    Celery = None  # type: ignore[assignment]


DEFAULT_TIMEZONE = "UTC"
DEFAULT_SOFT_TIME_LIMIT_SECONDS = 300
DEFAULT_TIME_LIMIT_SECONDS = 360
DEFAULT_WORKER_PREFETCH_MULTIPLIER = 1
DEFAULT_WORKER_MAX_TASKS_PER_CHILD = 100
DEFAULT_QUEUE_NAME = "default"


@dataclass(frozen=True)
class CeleryRuntimeConfig:
    """Normalized runtime config for Celery."""

    broker_url: str
    result_backend: str
    timezone: str
    task_soft_time_limit: int
    task_time_limit: int
    worker_prefetch_multiplier: int
    worker_max_tasks_per_child: int
    task_default_queue: str
    task_routes: dict[str, dict[str, str]]
    beat_schedule: dict[str, dict[str, Any]]
    task_modules: list[str]


class CeleryConfigurationError(Exception):
    """Raised when Celery dependency/configuration is unavailable."""


def _setting(name: str, default: Any) -> Any:
    """Read optional settings fields safely with a default fallback."""
    value = getattr(settings, name, default)
    return default if value is None else value


def _build_runtime_config() -> CeleryRuntimeConfig:
    """Build Celery configuration using settings with safe defaults."""
    redis_url = str(_setting("redis_url", "redis://localhost:6379/0"))
    return CeleryRuntimeConfig(
        broker_url=redis_url,
        result_backend=redis_url,
        timezone=str(_setting("celery_timezone", DEFAULT_TIMEZONE)),
        task_soft_time_limit=int(_setting("celery_task_soft_time_limit", DEFAULT_SOFT_TIME_LIMIT_SECONDS)),
        task_time_limit=int(_setting("celery_task_time_limit", DEFAULT_TIME_LIMIT_SECONDS)),
        worker_prefetch_multiplier=int(
            _setting("celery_worker_prefetch_multiplier", DEFAULT_WORKER_PREFETCH_MULTIPLIER)
        ),
        worker_max_tasks_per_child=int(
            _setting("celery_worker_max_tasks_per_child", DEFAULT_WORKER_MAX_TASKS_PER_CHILD)
        ),
        task_default_queue=str(_setting("celery_default_queue", DEFAULT_QUEUE_NAME)),
        task_routes={
            "app.tasks.knowledge.*": {"queue": "knowledge_ingestion"},
            "app.tasks.memory.*": {"queue": "memory_management"},
            "app.tasks.analytics.*": {"queue": "analytics"},
            "app.tasks.token_usage.*": {"queue": "analytics"},
        },
        beat_schedule=get_celery_beat_schedule(),
        task_modules=[
            "app.tasks.knowledge",
            "app.tasks.memory",
            "app.tasks.analytics",
            "app.tasks.token_usage",
        ],
    )


def _create_celery_app(config: CeleryRuntimeConfig) -> Any:
    """Create and configure a Celery app instance from runtime config."""
    if Celery is None:
        raise CeleryConfigurationError("celery dependency is not installed")
    if not config.broker_url:
        raise CeleryConfigurationError("settings.redis_url must be configured")

    app = Celery("ragai", broker=config.broker_url, backend=config.result_backend)
    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone=config.timezone,
        enable_utc=True,
        task_track_started=True,
        task_soft_time_limit=config.task_soft_time_limit,
        task_time_limit=config.task_time_limit,
        worker_prefetch_multiplier=config.worker_prefetch_multiplier,
        worker_max_tasks_per_child=config.worker_max_tasks_per_child,
        task_default_queue=config.task_default_queue,
        task_routes=config.task_routes,
        beat_schedule=config.beat_schedule,
        imports=config.task_modules,
    )
    return app


def _bootstrap_celery_app() -> tuple[Any | None, str | None]:
    """Create a Celery app once at import time, while staying import-safe."""
    try:
        app = _create_celery_app(_build_runtime_config())
    except Exception as exc:
        return None, str(exc)
    return app, None


celery_app, _celery_app_error = _bootstrap_celery_app()


def get_celery_app() -> Any:
    """Return the configured Celery app, or raise a clear setup error."""
    if celery_app is None:
        raise CeleryConfigurationError(_celery_app_error or "celery app is not configured")
    return celery_app


__all__ = ["CeleryConfigurationError", "celery_app", "get_celery_app"]
