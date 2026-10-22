from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import AsyncIterator

from app.core.redis_client import get_redis_client

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _InProcessBroadcaster:
    queues: list[asyncio.Queue[str]] = field(default_factory=list)

    async def subscribe(self) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=2000)
        self.queues.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        if queue in self.queues:
            self.queues.remove(queue)

    def publish(self, payload: dict) -> None:
        data = json.dumps(payload)
        stale: list[asyncio.Queue[str]] = []
        for queue in self.queues:
            try:
                queue.put_nowait(data)
            except Exception:
                stale.append(queue)
        for queue in stale:
            self.unsubscribe(queue)


class TokenUsageRealtimeStreamService:
    def __init__(self, *, channel: str = "ragai:token_usage:events") -> None:
        self.channel = channel
        self._broadcaster = _InProcessBroadcaster()

    async def publish_fallback(self, payload: dict) -> None:
        self._broadcaster.publish(payload)

    async def stream(self) -> AsyncIterator[str]:
        redis_client = None
        pubsub = None
        queue: asyncio.Queue[str] | None = None

        try:
            try:
                redis_client = get_redis_client()
                pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
                pubsub.subscribe(self.channel)
                logger.debug("token_usage.realtime_pubsub_subscribed", extra={"channel": self.channel})
            except Exception:
                pubsub = None

            if pubsub is None:
                queue = await self._broadcaster.subscribe()
                logger.debug("token_usage.realtime_fallback_subscribed")

            while True:
                if pubsub is not None:
                    message = pubsub.get_message(timeout=1.0)
                    if message and message.get("type") == "message":
                        data = message.get("data")
                        if isinstance(data, bytes):
                            data = data.decode("utf-8", errors="ignore")
                        if isinstance(data, str):
                            yield f"event: usage\\ndata: {data}\\n\\n"
                    yield f"event: heartbeat\\ndata: {{\"timestamp\":\"{datetime.now(timezone.utc).isoformat()}\"}}\\n\\n"
                    await asyncio.sleep(5)
                    continue

                if queue is not None:
                    try:
                        data = await asyncio.wait_for(queue.get(), timeout=5)
                        yield f"event: usage\\ndata: {data}\\n\\n"
                    except asyncio.TimeoutError:
                        pass
                    yield f"event: heartbeat\\ndata: {{\"timestamp\":\"{datetime.now(timezone.utc).isoformat()}\"}}\\n\\n"
        finally:
            if pubsub is not None:
                try:
                    pubsub.unsubscribe(self.channel)
                    pubsub.close()
                except Exception:
                    logger.debug("token_usage.realtime_pubsub_cleanup_failed", exc_info=True)
            if queue is not None:
                self._broadcaster.unsubscribe(queue)


token_usage_realtime_stream_service = TokenUsageRealtimeStreamService()
