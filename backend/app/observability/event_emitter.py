"""Fail-safe async event emitter for observability/feedback events."""

from __future__ import annotations

import logging
from typing import Any, Mapping, Sequence

from pydantic import BaseModel


class AsyncEventEmitter:
    """Async event emitter with configurable fail-safe behavior."""

    def __init__(self, *, raise_errors: bool = False, logger_name: str = __name__) -> None:
        self.raise_errors = raise_errors
        self.logger = logging.getLogger(logger_name)

    async def emit(self, event_name: str, payload: BaseModel | Mapping[str, Any]) -> bool:
        """Emit one event payload; return False when emission fails in fail-safe mode."""

        try:
            serialized = self._serialize(payload)
            self.logger.info("observability_event name=%s payload=%s", event_name, serialized)
            return True
        except Exception:
            self.logger.error("observability_event_emit_failed name=%s", event_name, exc_info=True)
            if self.raise_errors:
                raise
            return False

    async def emit_all(
        self,
        events: Sequence[tuple[str, BaseModel | Mapping[str, Any]]],
    ) -> list[bool]:
        """Emit many events in order and return per-event success flags."""

        results: list[bool] = []
        for event_name, payload in events:
            results.append(await self.emit(event_name, payload))
        return results

    @staticmethod
    def _serialize(payload: BaseModel | Mapping[str, Any]) -> dict[str, Any]:
        if isinstance(payload, BaseModel):
            return payload.model_dump(mode="json")
        return dict(payload)
