"""Async Redis client infrastructure for cache services."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import RedisError

from app.core.config import settings

_JSON_KEY_SEGMENT_PATTERN = re.compile(r"[^a-zA-Z0-9:_-]")


class RedisSerializationError(ValueError):
    """Raised when JSON payload serialization or deserialization fails."""


class RedisOperationError(RuntimeError):
    """Raised when Redis command execution fails."""


@dataclass(slots=True)
class RedisClientConfig:
    """Connection and key configuration for the async Redis client."""

    url: str = settings.redis_url
    key_prefix: str = settings.redis_key_prefix
    default_ttl_seconds: int = settings.redis_session_ttl
    socket_timeout_seconds: float = 2.0
    socket_connect_timeout_seconds: float = 2.0
    decode_responses: bool = True


class AsyncRedisClient:
    """Reusable async Redis wrapper with JSON convenience helpers."""

    def __init__(self, config: RedisClientConfig | None = None) -> None:
        self.config = config or RedisClientConfig()
        self._pool: ConnectionPool | None = None
        self._client: Redis | None = None

    async def connect(self) -> Redis:
        """Create and reuse a Redis client backed by a connection pool."""
        if self._client is None:
            self._pool = ConnectionPool.from_url(
                self.config.url,
                decode_responses=self.config.decode_responses,
                socket_timeout=self.config.socket_timeout_seconds,
                socket_connect_timeout=self.config.socket_connect_timeout_seconds,
            )
            self._client = Redis(connection_pool=self._pool)
        return self._client

    async def close(self) -> None:
        """Close the Redis client and release all pool connections."""
        if self._client is not None:
            await self._client.close()
            self._client = None

        if self._pool is not None:
            await self._pool.disconnect()
            self._pool = None

    async def get_json(self, key: str) -> dict[str, Any] | list[Any] | str | int | float | bool | None:
        """Read and deserialize a JSON payload stored at the given key."""
        client = await self.connect()
        try:
            raw_value = await client.get(key)
        except RedisError as exc:
            raise RedisOperationError(f"Failed to get Redis key '{key}'.") from exc

        if raw_value is None:
            return None

        try:
            return json.loads(raw_value)
        except json.JSONDecodeError as exc:
            raise RedisSerializationError(f"Invalid JSON payload at Redis key '{key}'.") from exc

    async def set_json(
        self,
        key: str,
        value: dict[str, Any] | list[Any] | str | int | float | bool | None,
        ttl_seconds: int | None = None,
    ) -> bool:
        """Serialize and write a JSON payload with optional TTL."""
        try:
            payload = json.dumps(value)
        except (TypeError, ValueError) as exc:
            raise RedisSerializationError("Failed to serialize payload for Redis storage.") from exc

        ttl = self.config.default_ttl_seconds if ttl_seconds is None else ttl_seconds
        if ttl <= 0:
            raise ValueError("ttl_seconds must be greater than zero.")

        client = await self.connect()
        try:
            return bool(await client.set(name=key, value=payload, ex=ttl))
        except RedisError as exc:
            raise RedisOperationError(f"Failed to set Redis key '{key}'.") from exc

    async def delete(self, key: str) -> int:
        """Delete the provided key and return the count of deleted entries."""
        client = await self.connect()
        try:
            return int(await client.delete(key))
        except RedisError as exc:
            raise RedisOperationError(f"Failed to delete Redis key '{key}'.") from exc

    async def exists(self, key: str) -> bool:
        """Return True when the key exists in Redis."""
        client = await self.connect()
        try:
            return bool(await client.exists(key))
        except RedisError as exc:
            raise RedisOperationError(f"Failed to inspect Redis key '{key}'.") from exc

    def build_key(self, namespace: str, *parts: object) -> str:
        """Build a consistent namespaced key: <prefix>:<namespace>:<part1>:..."""
        clean_segments = [self._sanitize_segment(self.config.key_prefix), self._sanitize_segment(namespace)]
        clean_segments.extend(self._sanitize_segment(part) for part in parts)
        return ":".join(segment for segment in clean_segments if segment)

    @staticmethod
    def _sanitize_segment(value: object) -> str:
        text = str(value).strip()
        if not text:
            return ""
        return _JSON_KEY_SEGMENT_PATTERN.sub("_", text)
