from __future__ import annotations

from fastapi import HTTPException, status
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.monitoring import increment_metric, otel_hook
from app.core.redis_client import get_redis_client

RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_KEY_PREFIX = "rate_limit"


def _resolve_user_id(request_user_id: str | None, request_ip: str | None) -> str:
    if request_user_id and request_user_id.strip():
        return request_user_id.strip()
    return request_ip or "anonymous"


def enforce_rate_limit(
    user_id: str,
    redis_client: Redis | None = None,
    *,
    limit_override: int | None = None,
) -> None:
    redis_conn = redis_client or get_redis_client()
    key = f"{RATE_LIMIT_KEY_PREFIX}:{user_id}"
    limit = int(limit_override if limit_override is not None else getattr(settings, "rate_limit", 100))

    try:
        with redis_conn.pipeline() as pipeline:
            pipeline.incr(key)
            pipeline.expire(key, RATE_LIMIT_WINDOW_SECONDS)
            request_count, _ = pipeline.execute()
    except RedisError as exc:
        increment_metric("rate_limit_backend_errors")
        otel_hook("rate_limit_backend_error", {"user_id": user_id})
        if bool(getattr(settings, "rate_limit_fail_open", True)):
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rate limiter is currently unavailable",
        ) from exc

    if int(request_count) > limit:
        increment_metric("rate_limit_exceeded")
        otel_hook("rate_limit_exceeded", {"user_id": user_id, "count": int(request_count), "limit": limit})
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: maximum {limit} requests per minute",
        )

    increment_metric("rate_limit_allowed")
