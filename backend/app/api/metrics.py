"""Prometheus scrape endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.observability.metrics_registry import get_observability_metrics_registry

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def get_metrics() -> Response:
    """Expose Prometheus-compatible metrics from the shared registry."""

    registry = get_observability_metrics_registry().registry
    payload = generate_latest(registry)
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)
