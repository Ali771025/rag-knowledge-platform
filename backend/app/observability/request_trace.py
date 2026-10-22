"""Request-scoped trace context helpers for ASGI/FastAPI workflows."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from uuid import UUID, uuid4

from fastapi import Request

from app.observability.value_objects import TraceContext

_TRACE_CONTEXT: ContextVar[TraceContext | None] = ContextVar("observability_trace_context", default=None)


@dataclass(frozen=True, slots=True)
class RequestTraceRuntime:
    """Runtime timing/trace attributes attached to request state."""

    trace_id: str
    request_id: str
    started_at: datetime
    started_perf_counter: float


def generate_trace_id() -> str:
    """Generate a UUID4 trace identifier string."""

    return str(uuid4())


def build_trace_context(
    *,
    trace_id: str,
    request_id: str | None = None,
    session_id: UUID | None = None,
    user_id: UUID | None = None,
) -> TraceContext:
    """Build a domain trace context object for this request."""

    return TraceContext(
        trace_id=trace_id,
        request_id=request_id,
        session_id=session_id,
        user_id=user_id,
    )


def set_current_trace_context(trace_context: TraceContext) -> None:
    """Set context-local trace metadata for the current execution context."""

    _TRACE_CONTEXT.set(trace_context)


def get_current_trace_context() -> TraceContext | None:
    """Get context-local trace metadata for the current execution context."""

    return _TRACE_CONTEXT.get()


def clear_current_trace_context() -> None:
    """Clear context-local trace metadata."""

    _TRACE_CONTEXT.set(None)


def initialize_request_trace(request: Request) -> RequestTraceRuntime:
    """Create and attach request-scoped trace metadata to request state/context."""

    incoming_trace = request.headers.get("x-trace-id")
    trace_id = incoming_trace.strip() if incoming_trace and incoming_trace.strip() else generate_trace_id()
    request_id = trace_id
    started_at = datetime.now(UTC)
    started_perf_counter = perf_counter()

    runtime = RequestTraceRuntime(
        trace_id=trace_id,
        request_id=request_id,
        started_at=started_at,
        started_perf_counter=started_perf_counter,
    )

    request.state.trace_id = trace_id
    request.state.request_id = request_id
    request.state.request_started_at = started_at
    request.state.request_started_perf_counter = started_perf_counter

    set_current_trace_context(build_trace_context(trace_id=trace_id, request_id=request_id))
    return runtime


def get_request_latency_ms(request: Request) -> float | None:
    """Compute elapsed request latency in milliseconds from request state."""

    started_perf_counter = getattr(request.state, "request_started_perf_counter", None)
    if started_perf_counter is None:
        return None
    return max(0.0, (perf_counter() - float(started_perf_counter)) * 1000.0)
