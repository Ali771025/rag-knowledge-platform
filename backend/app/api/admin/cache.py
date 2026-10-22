"""Admin cache endpoints for cache stats and invalidation operations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import get_token_payload
from app.core.runtime_services import get_runtime_services
from app.models.cache.contracts import CacheInvalidateResult

router = APIRouter(prefix="/admin/cache", tags=["admin-cache"])


def _admin_auth_hook(token_payload: Annotated[dict[str, Any] | None, Depends(get_token_payload)]) -> dict[str, Any] | None:
    """Placeholder admin auth hook; replace with strict role validation when auth is finalized."""
    return token_payload


class CacheStatsResponse(BaseModel):
    """Typed cache stats response for admin visibility."""

    stats: dict[str, float]
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid")


class CacheInvalidateRequest(BaseModel):
    """Cache invalidation payload for a specific namespace/key."""

    namespace: str = Field(default="semantic", min_length=1, max_length=128)
    cache_key: str = Field(..., min_length=1, max_length=512)
    cache_type: str = Field(default="semantic", pattern="^(semantic|rag|session)$")

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats(_auth: Annotated[dict[str, Any] | None, Depends(_admin_auth_hook)]) -> CacheStatsResponse:
    """Return in-process cache metrics snapshot."""
    services = get_runtime_services()
    return CacheStatsResponse(stats=services.cache_metrics.snapshot())


@router.post("/invalidate", response_model=CacheInvalidateResult)
async def invalidate_cache_entry(
    payload: CacheInvalidateRequest,
    _auth: Annotated[dict[str, Any] | None, Depends(_admin_auth_hook)],
) -> CacheInvalidateResult:
    """Invalidate a cache entry by cache type and key."""
    services = get_runtime_services()
    try:
        if payload.cache_type == "semantic":
            return await services.semantic_cache.invalidate_cache(
                cache_key=payload.cache_key,
                namespace=payload.namespace,
            )
        if payload.cache_type == "rag":
            return await services.rag_cache.invalidate_rag_cache(
                namespace=payload.namespace,
                cache_key=payload.cache_key,
            )
        return await services.session_cache.clear_session_context(
            session_id=payload.cache_key,
            namespace=payload.namespace,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache invalidation failed: {type(exc).__name__}",
        ) from exc


__all__ = ["router", "CacheStatsResponse", "CacheInvalidateRequest"]
