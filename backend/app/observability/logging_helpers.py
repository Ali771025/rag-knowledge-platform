"""Common structured logging helpers for observability events."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Mapping
from uuid import UUID

from app.observability.logging_models import StructuredLogCategory, StructuredLogEvent, StructuredLogLevel
from app.observability.structured_logger import StructuredLogger


@dataclass(frozen=True, slots=True)
class LoggingContext:
    """Optional shared context attached to logging helper calls."""

    trace_id: str | None = None
    user_id: UUID | str | None = None
    endpoint: str | None = None
    state: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


class ObservabilityLoggingHelper:
    """Typed helper facade for common observability log events."""

    def __init__(self, logger: StructuredLogger) -> None:
        self.logger = logger

    def user_query(self, query: str, *, context: LoggingContext | None = None) -> None:
        self._emit(
            level=StructuredLogLevel.INFO,
            category=StructuredLogCategory.CONVERSATION,
            message="User query received",
            context=context,
            metadata={"query": query},
        )

    def intent_detected(
        self,
        intent: str,
        confidence: float | None = None,
        *,
        context: LoggingContext | None = None,
    ) -> None:
        metadata: dict[str, Any] = {"intent": intent}
        if confidence is not None:
            metadata["confidence"] = confidence

        self._emit(
            level=StructuredLogLevel.INFO,
            category=StructuredLogCategory.INTENT,
            message="Intent detected",
            context=context,
            metadata=metadata,
        )

    def state_transition(
        self,
        *,
        state_before: str,
        state_after: str,
        context: LoggingContext | None = None,
    ) -> None:
        self._emit(
            level=StructuredLogLevel.INFO,
            category=StructuredLogCategory.SYSTEM,
            message="State transition",
            context=context,
            metadata={
                "state_before": state_before,
                "state_after": state_after,
            },
            state=state_after,
        )

    def rag_docs_count(self, count: int, *, context: LoggingContext | None = None) -> None:
        self._emit(
            level=StructuredLogLevel.INFO,
            category=StructuredLogCategory.REQUEST,
            message="RAG documents counted",
            context=context,
            metadata={"rag_docs_count": count},
        )

    def tokens_used(
        self,
        *,
        input_tokens: int,
        output_tokens: int,
        context: LoggingContext | None = None,
    ) -> None:
        self._emit(
            level=StructuredLogLevel.INFO,
            category=StructuredLogCategory.REQUEST,
            message="Token usage recorded",
            context=context,
            tokens={
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens,
            },
        )

    def cost_usd(self, cost: Decimal | float, *, context: LoggingContext | None = None) -> None:
        self._emit(
            level=StructuredLogLevel.INFO,
            category=StructuredLogCategory.REQUEST,
            message="Cost usage recorded",
            context=context,
            cost_usd=cost,
        )

    def request_completion(
        self,
        *,
        duration_ms: float,
        status: str,
        context: LoggingContext | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        merged_metadata = {
            "status": status,
            **dict(metadata or {}),
        }
        self._emit(
            level=StructuredLogLevel.INFO,
            category=StructuredLogCategory.REQUEST,
            message="Request completed",
            context=context,
            duration_ms=duration_ms,
            metadata=merged_metadata,
        )

    def error(
        self,
        error: BaseException,
        *,
        message: str = "Unhandled exception",
        context: LoggingContext | None = None,
        metadata: Mapping[str, Any] | None = None,
        include_stack_trace: bool = True,
    ) -> None:
        event = self._build_event(
            level=StructuredLogLevel.ERROR,
            category=StructuredLogCategory.ERROR,
            message=message,
            context=context,
            metadata={
                "error_type": type(error).__name__,
                **dict(metadata or {}),
            },
        )

        self.logger.emit(event, exc_info=error if include_stack_trace else None)

    def _emit(
        self,
        *,
        level: StructuredLogLevel,
        category: StructuredLogCategory,
        message: str,
        context: LoggingContext | None,
        metadata: Mapping[str, Any] | None = None,
        duration_ms: float | None = None,
        tokens: int | Mapping[str, int] | None = None,
        cost_usd: Decimal | float | None = None,
        state: str | None = None,
    ) -> None:
        event = self._build_event(
            level=level,
            category=category,
            message=message,
            context=context,
            metadata=metadata,
            duration_ms=duration_ms,
            tokens=tokens,
            cost_usd=cost_usd,
            state=state,
        )
        self.logger.emit(event)

    def _build_event(
        self,
        *,
        level: StructuredLogLevel,
        category: StructuredLogCategory,
        message: str,
        context: LoggingContext | None,
        metadata: Mapping[str, Any] | None = None,
        duration_ms: float | None = None,
        tokens: int | Mapping[str, int] | None = None,
        cost_usd: Decimal | float | None = None,
        state: str | None = None,
    ) -> StructuredLogEvent:
        merged_metadata = dict(context.metadata) if context is not None else {}
        if metadata:
            merged_metadata.update(dict(metadata))

        return StructuredLogEvent(
            level=level,
            category=category,
            message=message,
            service=self.logger.service,
            trace_id=context.trace_id if context is not None else None,
            user_id=context.user_id if context is not None else None,
            endpoint=context.endpoint if context is not None else None,
            state=state or (context.state if context is not None else None),
            duration_ms=duration_ms,
            tokens=tokens,
            cost_usd=cost_usd,
            metadata=merged_metadata,
        )
