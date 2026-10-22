"""Helpers for attaching deferred observability fields to request state."""

from __future__ import annotations

from fastapi import Request


def attach_request_state(request: Request, state: str) -> None:
    """Attach workflow state for downstream middleware metrics/log labeling."""

    request.state.state = state


def attach_request_tokens(request: Request, *, input_tokens: int, output_tokens: int) -> None:
    """Attach token usage for middleware-level deferred metrics recording."""

    request.state.observability_tokens = {
        "input": max(0, int(input_tokens)),
        "output": max(0, int(output_tokens)),
    }


def attach_request_cost_usd(request: Request, *, cost_usd: float) -> None:
    """Attach normalized cost for middleware-level deferred metrics recording."""

    request.state.observability_cost_usd = max(0.0, float(cost_usd))
