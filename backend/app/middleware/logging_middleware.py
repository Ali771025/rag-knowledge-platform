from __future__ import annotations

import logging
import time

from fastapi import Request

from app.core.monitoring import increment_metric, otel_hook

logger = logging.getLogger("app.request")


async def log_request_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    user_id_header = request.headers.get("x-user-id")
    user_id = user_id_header.strip() if user_id_header else "anonymous"
    endpoint = request.url.path
    intent: str | None = None

    response = None
    try:
        if request.method.upper() == "POST":
            try:
                payload = await request.json()
                message = payload.get("message") if isinstance(payload, dict) else None
                if isinstance(message, str):
                    lowered = message.strip().lower()
                    if lowered:
                        intent = lowered.split(maxsplit=1)[0][:64]
            except Exception:
                intent = None

        response = await call_next(request)
        return response
    finally:
        status_code = response.status_code if response is not None else 500

        process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(
            "request_metadata",
            extra={
                "endpoint": endpoint,
                "method": request.method,
                "status_code": status_code,
                "user_id": user_id,
                "latency_ms": process_time_ms,
                "intent": intent,
            },
        )
        increment_metric("request_total")
        otel_hook(
            "request_metadata",
            {
                "endpoint": endpoint,
                "method": request.method,
                "status_code": status_code,
                "latency_ms": process_time_ms,
            },
        )
