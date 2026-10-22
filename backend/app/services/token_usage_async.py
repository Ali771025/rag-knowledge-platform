from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from decimal import Decimal
from queue import Empty, Queue
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select

from app.core.celery_app import CeleryConfigurationError, get_celery_app
from app.core.database import SessionLocal
from app.core.redis_client import get_redis_client
from app.models.token_monitoring import APIKeyMetadata, TokenProvider, TokenUsageLog
from app.repositories.token_monitoring_repository import APIKeyRepository, TokenUsageLogRepository
from app.services.token_budget_service import TokenBudgetService

logger = logging.getLogger(__name__)


class TokenUsageCaptureEvent(BaseModel):
    provider: TokenProvider
    model_name: str = Field(min_length=1, max_length=128)
    api_key_id: UUID | None = None
    api_key_alias: str | None = None
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    cost_usd: Decimal = Field(ge=Decimal("0"))
    latency_ms: int = Field(ge=0)
    cache_hit: bool = False
    endpoint: str | None = None
    session_id: str | None = None
    request_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class TokenUsageAsyncLogger:
    def __init__(self, *, redis_channel: str = "ragai:token_usage:events") -> None:
        self.redis_channel = redis_channel
        self._queue: Queue[TokenUsageCaptureEvent] = Queue(maxsize=20_000)
        self._worker_started = False
        self._worker_lock = threading.Lock()

    def enqueue(self, event: TokenUsageCaptureEvent) -> None:
        payload = self._event_to_payload(event)
        try:
            app = get_celery_app()
            app.send_task("app.tasks.token_usage.persist_token_usage_event", args=[payload])
            logger.debug("token_usage.enqueue_celery", extra={"event": self._safe_event_context(event)})
            return
        except CeleryConfigurationError:
            pass
        except Exception:
            logger.debug("token_usage.celery_dispatch_failed", exc_info=True)

        self._ensure_worker()
        try:
            self._queue.put_nowait(event)
        except Exception:
            logger.warning("token_usage.queue_overflow", extra={"event": self._safe_event_context(event)})

    def flush_once(self, timeout_seconds: float = 0.1) -> bool:
        try:
            event = self._queue.get(timeout=timeout_seconds)
        except Empty:
            return False

        try:
            self._persist_event(event)
            self._publish_realtime(event)
        except Exception:
            logger.exception("token_usage.persistence_failed", extra={"event": self._safe_event_context(event)})
        finally:
            self._queue.task_done()
        return True

    def _ensure_worker(self) -> None:
        if self._worker_started:
            return
        with self._worker_lock:
            if self._worker_started:
                return
            thread = threading.Thread(target=self._run_worker, name="token-usage-logger", daemon=True)
            thread.start()
            self._worker_started = True

    def _run_worker(self) -> None:
        while True:
            self.flush_once(timeout_seconds=0.5)

    def _resolve_api_key_id(self, api_key_alias: str | None) -> UUID | None:
        if not api_key_alias:
            return None
        with SessionLocal() as db:
            stmt = select(APIKeyMetadata.id).where(APIKeyMetadata.key_alias == api_key_alias)
            return db.scalar(stmt)

    def _persist_event(self, event: TokenUsageCaptureEvent) -> None:
        api_key_id = event.api_key_id or self._resolve_api_key_id(event.api_key_alias)

        with SessionLocal() as db:
            usage_repo = TokenUsageLogRepository(db)
            if api_key_id is None:
                placeholder = self._get_or_create_placeholder_key(db=db, provider=event.provider)
                api_key_id = placeholder.id
            event.api_key_id = api_key_id

            usage_repo.create(
                api_key_id=api_key_id,
                provider=event.provider,
                model_name=event.model_name,
                prompt_tokens=event.prompt_tokens,
                completion_tokens=event.completion_tokens,
                total_tokens=event.total_tokens,
                cost_usd=event.cost_usd,
                request_id=event.request_id,
                created_at=event.created_at,
                latency_ms=event.latency_ms,
                cache_hit=event.cache_hit,
                endpoint=event.endpoint,
                session_id=event.session_id,
                metadata_json={
                    **dict(event.metadata or {}),
                    "api_key_alias": event.api_key_alias,
                },
            )
            try:
                TokenBudgetService(db).evaluate_threshold_crossings(api_key_id=api_key_id, at_time=event.created_at)
            except Exception:
                logger.exception(
                    "token_usage.budget_threshold_evaluation_failed",
                    extra={"api_key_id": str(api_key_id), "request_id": event.request_id},
                )
            logger.info(
                "token_usage.persisted",
                extra={
                    "provider": event.provider.value,
                    "model_name": event.model_name,
                    "api_key_id": str(api_key_id),
                    "request_id": event.request_id,
                    "endpoint": event.endpoint,
                    "cache_hit": event.cache_hit,
                },
            )

    def _get_or_create_placeholder_key(self, *, db, provider: TokenProvider) -> APIKeyMetadata:
        repo = APIKeyRepository(db)
        fingerprint = f"system-{provider.value}"
        existing = repo.get_by_fingerprint(fingerprint)
        if existing is not None:
            return existing

        return repo.create(
            provider=provider,
            display_name=f"System {provider.value}",
            key_alias=f"system-{provider.value}",
            key_fingerprint=fingerprint,
            key_hash=f"system-{provider.value}-hash",
            metadata_json={"system_generated": True},
        )

    def _publish_realtime(self, event: TokenUsageCaptureEvent) -> None:
        payload = {
            "timestamp": event.created_at.isoformat(),
            "provider": event.provider.value,
            "model_name": event.model_name,
            "api_key_id": str(event.api_key_id) if event.api_key_id else None,
            "tokens_delta": event.total_tokens,
            "cost_delta": str(event.cost_usd),
            "latency_ms": event.latency_ms,
            "cache_hit": event.cache_hit,
        }
        try:
            get_redis_client().publish(self.redis_channel, json.dumps(payload))
            logger.debug(
                "token_usage.realtime_published",
                extra={
                    "provider": event.provider.value,
                    "model_name": event.model_name,
                    "api_key_id": str(event.api_key_id) if event.api_key_id else None,
                },
            )
        except Exception:
            logger.warning(
                "token_usage.redis_publish_failed",
                extra={
                    "provider": event.provider.value,
                    "model_name": event.model_name,
                    "api_key_id": str(event.api_key_id) if event.api_key_id else None,
                },
                exc_info=True,
            )
            try:
                from app.services.token_usage_stream import token_usage_realtime_stream_service
                import asyncio

                loop = None
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None

                if loop and loop.is_running():
                    loop.create_task(token_usage_realtime_stream_service.publish_fallback(payload))
            except Exception:
                logger.debug("token_usage.fallback_publish_failed", exc_info=True)


    @staticmethod
    def _event_to_payload(event: TokenUsageCaptureEvent) -> dict[str, Any]:
        payload = event.model_dump(mode="json")
        payload["provider"] = event.provider.value
        payload["cost_usd"] = str(event.cost_usd)
        payload["created_at"] = event.created_at.isoformat()
        return payload

    @staticmethod
    def _safe_event_context(event: TokenUsageCaptureEvent) -> dict[str, Any]:
        return {
            "provider": event.provider.value,
            "model_name": event.model_name,
            "request_id": event.request_id,
            "session_id": event.session_id,
            "endpoint": event.endpoint,
        }


token_usage_async_logger = TokenUsageAsyncLogger()
