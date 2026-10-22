from __future__ import annotations

import logging
from collections import defaultdict
from threading import Lock

logger = logging.getLogger("app.monitoring")

_METRICS_LOCK = Lock()
_METRICS_COUNTERS: dict[str, int] = defaultdict(int)


def increment_metric(name: str, value: int = 1) -> None:
    with _METRICS_LOCK:
        _METRICS_COUNTERS[name] += value


def get_metrics_snapshot() -> dict[str, int]:
    with _METRICS_LOCK:
        return dict(_METRICS_COUNTERS)


def otel_hook(event_name: str, attributes: dict[str, object] | None = None) -> None:
    logger.debug(
        "otel_hook",
        extra={
            "event_name": event_name,
            "attributes": attributes or {},
        },
    )
