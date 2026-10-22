"""Observability health API endpoint exposing structured dependency status."""

from __future__ import annotations

import time

from fastapi import APIRouter

from app.core.claude_client import ClaudeClient
from app.core.neo4j_client import Neo4jClientAdapter
from app.core.qdrant_client import QdrantClientAdapter
from app.observability.health_check_service import HealthCheckService

router = APIRouter(prefix="/health", tags=["health"])
_START_TIME = time.monotonic()


def _get_uptime_seconds() -> float:
    return round(time.monotonic() - _START_TIME, 2)


@router.get("")
async def get_health() -> dict[str, object]:
    service = HealthCheckService(
        qdrant_client=QdrantClientAdapter(),
        neo4j_client=Neo4jClientAdapter(),
        llm_client=ClaudeClient(),
    )
    report = await service.check_dependencies()
    services = [
        {
            "name": result.dependency_name,
            "type": result.dependency_type.value,
            "status": result.state.value,
            "latency_ms": result.latency_ms,
            "error": result.error_message,
            "details": dict(result.metadata),
        }
        for result in report.results
    ]

    service_status_by_name = {item["name"]: item["status"] for item in services}
    redis_status = "ok" if service_status_by_name.get("redis") == "healthy" else "down"
    database_status = "ok" if service_status_by_name.get("postgresql") == "healthy" else "down"

    return {
        # Backward-compatible legacy status field; use `overall_status` for dependency truth.
        "status": "ok",
        "overall_status": report.overall_status,
        "timestamp": report.checked_at.isoformat(),
        "uptime": _get_uptime_seconds(),
        "redis": redis_status,
        "database": database_status,
        "services": services,
    }
