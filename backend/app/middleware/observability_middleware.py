"""Observability middleware with trace context and low-overhead hooks."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.datastructures import MutableHeaders

from app.observability.logging_helpers import LoggingContext, ObservabilityLoggingHelper
from app.observability.metrics_collector import MetricsCollector
from app.observability.request_trace import (
    clear_current_trace_context,
    get_request_latency_ms,
    initialize_request_trace,
)
from app.observability.structured_logger import StructuredLogger, get_structured_logger


class ObservabilityMiddleware:
    """Thin composable middleware for request trace/metrics/logging concerns.

    Notes:
    - This middleware is intentionally low-overhead and synchronous in its bookkeeping.
    - Any unavailable token/cost data can be attached later via `request.state` by handlers.
    """

    def __init__(
        self,
        app: Callable[..., Any],
        *,
        metrics_collector: MetricsCollector | None = None,
        structured_logger: StructuredLogger | None = None,
    ) -> None:
        self.app = app
        self.metrics_collector = metrics_collector or MetricsCollector()
        self.logger = structured_logger or get_structured_logger(logger_name="app.observability.middleware")
        self.log_helper = ObservabilityLoggingHelper(self.logger)
        self._excluded_paths = {"/api/v1/metrics"}

    async def __call__(self, scope: dict[str, Any], receive: Callable[..., Any], send: Callable[..., Any]) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        runtime = initialize_request_trace(request)
        should_observe = request.url.path not in self._excluded_paths

        scope.setdefault("state", {})
        scope["state"]["trace_id"] = runtime.trace_id
        scope["state"]["request_id"] = runtime.request_id
        scope["state"]["request_started_at"] = runtime.started_at

        context = LoggingContext(
            trace_id=runtime.trace_id,
            user_id=self._extract_user_id(request),
            endpoint=request.url.path,
            state=self._extract_state(request),
        )

        response_status = 500
        completed = False

        async def send_wrapper(message: dict[str, Any]) -> None:
            nonlocal response_status, completed

            if message.get("type") == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.append("x-trace-id", runtime.trace_id)
                response_status = int(message.get("status", 500))

            if message.get("type") == "http.response.body" and not message.get("more_body", False):
                completed = True
                if should_observe:
                    try:
                        await self._on_response(request=request, context=context, status_code=response_status)
                    except Exception:
                        # Observability hooks must not break response delivery.
                        pass

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
            if should_observe and not completed:
                # Fallback for edge-cases where response body hooks are skipped.
                try:
                    await self._on_response(request=request, context=context, status_code=response_status)
                except Exception:
                    pass
        except Exception as exc:
            if should_observe:
                try:
                    await self._on_exception(request=request, context=context, exc=exc)
                except Exception:
                    pass
            error_response = self._standard_error_response(trace_id=runtime.trace_id)
            await error_response(scope, receive, send)
        finally:
            clear_current_trace_context()

    async def _on_response(self, *, request: Request, context: LoggingContext, status_code: int) -> None:
        latency_ms = get_request_latency_ms(request)
        endpoint = request.url.path
        state = self._extract_state(request)

        self.metrics_collector.record_request(endpoint=endpoint, user_id=None, state=state)
        if latency_ms is not None:
            self.metrics_collector.record_latency(endpoint=endpoint, duration_ms=latency_ms, state=state)

        tokens_payload = getattr(request.state, "observability_tokens", None)
        if isinstance(tokens_payload, dict):
            input_tokens = int(tokens_payload.get("input", 0) or 0)
            output_tokens = int(tokens_payload.get("output", 0) or 0)
            self.metrics_collector.record_tokens(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                user_id=None,
                state=state,
            )

        cost_usd = getattr(request.state, "observability_cost_usd", None)
        if cost_usd is not None:
            try:
                self.metrics_collector.record_cost(cost_usd=float(cost_usd), user_id=None, state=state)
            except (TypeError, ValueError):
                pass

        self.log_helper.request_completion(
            duration_ms=float(latency_ms or 0.0),
            status=str(status_code),
            context=LoggingContext(
                trace_id=context.trace_id,
                user_id=context.user_id,
                endpoint=context.endpoint,
                state=state,
            ),
            metadata={
                "status_code": status_code,
                "started_at": getattr(request.state, "request_started_at", datetime.now(UTC)).isoformat(),
            },
        )

    async def _on_exception(self, *, request: Request, context: LoggingContext, exc: Exception) -> None:
        endpoint = request.url.path
        state = self._extract_state(request)

        self.metrics_collector.record_error(endpoint=endpoint, error_type=type(exc).__name__, state=state)

        self.log_helper.error(
            exc,
            message="Request processing failed",
            context=LoggingContext(
                trace_id=context.trace_id,
                user_id=context.user_id,
                endpoint=context.endpoint,
                state=state,
            ),
            metadata={
                "method": request.method,
            },
            include_stack_trace=True,
        )

    def _extract_user_id(self, request: Request) -> str | None:
        user_id_header = request.headers.get("x-user-id")
        if user_id_header is None:
            return None
        normalized = user_id_header.strip()
        return normalized or None

    def _extract_state(self, request: Request) -> str:
        value = getattr(request.state, "state", None)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return "unknown"

    def _standard_error_response(self, *, trace_id: str) -> Response:
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error": {
                    "code": "internal_server_error",
                    "trace_id": trace_id,
                },
            },
            headers={"x-trace-id": trace_id},
        )
