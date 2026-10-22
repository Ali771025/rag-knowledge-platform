from __future__ import annotations

import json
import os
import re
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings

_SAFE_CHARS = re.compile(r"[^a-zA-Z0-9:_-]")
_REDIS_KEY_PREFIX = str(getattr(settings, "redis_key_prefix", os.getenv("REDIS_KEY_PREFIX", "ragai:session")))
_REDIS_URL = str(getattr(settings, "redis_url", os.getenv("REDIS_URL", "redis://localhost:6379/0")))
_REDIS_TTL_SECONDS = int(getattr(settings, "redis_session_ttl", os.getenv("REDIS_SESSION_TTL", "3600")))

_redis_client: Redis | None = None


def _safe_session_key(session_id: str) -> str:
    normalized = _SAFE_CHARS.sub("_", session_id.strip())
    return f"{_REDIS_KEY_PREFIX}:{normalized}"


def get_redis_client() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(
            _REDIS_URL,
            decode_responses=True,
            socket_timeout=2,
            socket_connect_timeout=2,
        )
    return _redis_client


def get_session_state(session_id: str) -> dict[str, Any] | None:
    key = _safe_session_key(session_id)
    try:
        raw = get_redis_client().get(key)
        if not raw:
            return None
        return json.loads(raw)
    except (RedisError, json.JSONDecodeError, TypeError, ValueError):
        return None


def set_session_state(session_id: str, state: dict[str, Any], ttl_seconds: int | None = None) -> bool:
    key = _safe_session_key(session_id)
    ttl = ttl_seconds if ttl_seconds is not None else _REDIS_TTL_SECONDS
    try:
        payload = json.dumps(state)
        return bool(get_redis_client().set(name=key, value=payload, ex=ttl))
    except (RedisError, TypeError, ValueError):
        return False


def delete_session_state(session_id: str) -> bool:
    key = _safe_session_key(session_id)
    try:
        deleted = get_redis_client().delete(key)
        return deleted > 0
    except RedisError:
        return False
