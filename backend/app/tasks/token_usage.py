from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.celery_app import CeleryConfigurationError, get_celery_app
from app.core.redis_client import get_redis_client
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.token_monitoring import APIKeyMetadata, TokenProvider
from app.repositories.token_monitoring_repository import APIKeyRepository, TokenUsageLogRepository
from app.services.token_budget_service import TokenBudgetService
from app.services.token_optimization_service import TokenOptimizationService

logger = logging.getLogger(__name__)


class _DummyTaskApp:
    @staticmethod
    def task(*_args, **_kwargs):
        def decorator(func):
            return func

        return decorator


def _resolve_task_app():
    try:
        return get_celery_app()
    except CeleryConfigurationError:
        return _DummyTaskApp()


task_app = _resolve_task_app()


def _resolve_api_key_id(db, api_key_alias: str | None) -> UUID | None:
    if not api_key_alias:
        return None
    stmt = select(APIKeyMetadata.id).where(APIKeyMetadata.key_alias == api_key_alias)
    return db.scalar(stmt)


def _get_or_create_placeholder_key(repo: APIKeyRepository, provider: TokenProvider) -> APIKeyMetadata:
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


def _publish_realtime(payload: dict[str, Any]) -> None:
    event = {
        "timestamp": str(payload.get("created_at")),
        "provider": str(payload.get("provider", "openai")),
        "model_name": str(payload.get("model_name", "unknown")),
        "api_key_id": str(payload.get("api_key_id")) if payload.get("api_key_id") else None,
        "tokens_delta": int(payload.get("total_tokens", 0) or 0),
        "cost_delta": str(payload.get("cost_usd", "0")),
        "latency_ms": int(payload.get("latency_ms", 0) or 0),
        "cache_hit": bool(payload.get("cache_hit", False)),
    }
    try:
        get_redis_client().publish("ragai:token_usage:events", json.dumps(event))
        logger.debug(
            "token_usage.task_realtime_published",
            extra={
                "provider": event["provider"],
                "model_name": event["model_name"],
                "api_key_id": event["api_key_id"],
            },
        )
    except Exception:
        logger.warning(
            "token_usage.task_realtime_publish_failed",
            extra={
                "provider": event["provider"],
                "model_name": event["model_name"],
                "api_key_id": event["api_key_id"],
            },
            exc_info=True,
        )
        try:
            from app.services.token_usage_stream import token_usage_realtime_stream_service

            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                loop.create_task(token_usage_realtime_stream_service.publish_fallback(event))
        except Exception:
            pass


@task_app.task(name="app.tasks.token_usage.persist_token_usage_event")
def persist_token_usage_event(payload: dict[str, Any]) -> dict[str, Any]:
    provider = TokenProvider(str(payload.get("provider", "openai")))
    api_key_id = UUID(str(payload["api_key_id"])) if payload.get("api_key_id") else None

    with SessionLocal() as db:
        api_key_repo = APIKeyRepository(db)
        usage_repo = TokenUsageLogRepository(db)

        if api_key_id is None:
            api_key_id = _resolve_api_key_id(db, str(payload.get("api_key_alias", "")).strip() or None)
        if api_key_id is None:
            api_key_id = _get_or_create_placeholder_key(api_key_repo, provider).id

        created_at = datetime.fromisoformat(str(payload.get("created_at"))) if payload.get("created_at") else datetime.now(timezone.utc)
        usage_repo.create(
            api_key_id=api_key_id,
            provider=provider,
            model_name=str(payload.get("model_name", "unknown")),
            prompt_tokens=max(int(payload.get("prompt_tokens", 0)), 0),
            completion_tokens=max(int(payload.get("completion_tokens", 0)), 0),
            total_tokens=max(int(payload.get("total_tokens", 0)), 0),
            cost_usd=Decimal(str(payload.get("cost_usd", "0"))),
            request_id=(str(payload.get("request_id")) if payload.get("request_id") else None),
            latency_ms=max(int(payload.get("latency_ms", 0)), 0),
            cache_hit=bool(payload.get("cache_hit", False)),
            endpoint=(str(payload.get("endpoint")) if payload.get("endpoint") else None),
            session_id=(str(payload.get("session_id")) if payload.get("session_id") else None),
            metadata_json=dict(payload.get("metadata") or {}),
            created_at=created_at,
        )
        TokenBudgetService(db).evaluate_threshold_crossings(api_key_id=api_key_id, at_time=created_at)
        logger.info(
            "token_usage.task_persisted",
            extra={
                "provider": provider.value,
                "model_name": str(payload.get("model_name", "unknown")),
                "api_key_id": str(api_key_id),
                "request_id": payload.get("request_id"),
                "endpoint": payload.get("endpoint"),
            },
        )
        payload["api_key_id"] = str(api_key_id)
        payload["created_at"] = created_at.isoformat()
        _publish_realtime(payload)

    return {"status": "persisted"}


@task_app.task(name="app.tasks.token_usage.generate_optimization_recommendations")
def generate_optimization_recommendations() -> dict[str, Any]:
    with SessionLocal() as db:
        service = TokenOptimizationService(db)
        generated = service.generate_recommendations()
    logger.info("token_usage.optimization_generated", extra={"created_count": len(generated)})
    return {"status": "ok", "created": len(generated)}
