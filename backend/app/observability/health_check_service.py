"""Health-check service for lightweight dependency visibility."""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.claude_client import ClaudeClient
from app.core.database import SessionLocal
from app.core.neo4j_client import Neo4jClientAdapter
from app.core.qdrant_client import QdrantClientAdapter
from app.core.redis_client import get_redis_client
from app.observability.enums import DependencyType, HealthState
from app.observability.health_models import (
    HealthCheckReport,
    derive_overall_state,
    derive_overall_status,
    now_utc,
)
from app.observability.models import DependencyHealthResult


@dataclass(frozen=True, slots=True)
class HealthCheckConfig:
    """Global health check configuration."""

    default_timeout_seconds: float = 1.5
    llm_timeout_seconds: float = 2.0


class HealthCheckService:
    """Runs lightweight probes for core infrastructure dependencies.

    Dependencies are injectable/optional; missing clients are treated as degraded
    rather than fatal, so health endpoints remain available under partial outages.
    """

    def __init__(
        self,
        *,
        db_session_factory: Callable[[], Session] | None = None,
        redis_client_factory: Callable[[], Any] | None = None,
        qdrant_client: QdrantClientAdapter | None = None,
        neo4j_client: Neo4jClientAdapter | None = None,
        llm_client: ClaudeClient | None = None,
        config: HealthCheckConfig | None = None,
    ) -> None:
        self.db_session_factory = db_session_factory or SessionLocal
        self.redis_client_factory = redis_client_factory or get_redis_client
        self.qdrant_client = qdrant_client
        self.neo4j_client = neo4j_client
        self.llm_client = llm_client
        self.config = config or HealthCheckConfig()

    async def check_dependencies(self) -> HealthCheckReport:
        """Execute all probes concurrently and return structured health report."""

        checked_at = now_utc()

        probes: list[Awaitable[DependencyHealthResult]] = [
            self._run_probe(
                dependency_name="postgresql",
                dependency_type=DependencyType.DATABASE,
                probe=self._probe_postgresql,
            ),
            self._run_probe(
                dependency_name="redis",
                dependency_type=DependencyType.CACHE,
                probe=self._probe_redis,
            ),
            self._run_probe(
                dependency_name="qdrant",
                dependency_type=DependencyType.VECTOR_STORE,
                probe=self._probe_qdrant,
            ),
            self._run_probe(
                dependency_name="neo4j",
                dependency_type=DependencyType.GRAPH_STORE,
                probe=self._probe_neo4j,
            ),
            self._run_probe(
                dependency_name="llm_provider",
                dependency_type=DependencyType.LLM_PROVIDER,
                probe=self._probe_llm_provider,
            ),
        ]

        results = tuple(await asyncio.gather(*probes))
        overall_state = derive_overall_state(results)
        overall_status = derive_overall_status(overall_state)

        return HealthCheckReport(
            checked_at=checked_at,
            overall_status=overall_status,
            overall_state=overall_state,
            results=results,
        )

    async def _run_probe(
        self,
        *,
        dependency_name: str,
        dependency_type: DependencyType,
        probe: Callable[[], Awaitable[dict[str, Any]]],
    ) -> DependencyHealthResult:
        started = time.perf_counter()
        timeout = self.config.default_timeout_seconds

        try:
            metadata = await asyncio.wait_for(probe(), timeout=timeout)
            state = HealthState.HEALTHY
            error_message = None
        except TimeoutError:
            metadata = {}
            state = HealthState.DEGRADED
            error_message = f"probe timeout after {timeout:.2f}s"
        except Exception as exc:
            metadata = {}
            state = HealthState.DEGRADED
            error_message = str(exc)

        latency_ms = (time.perf_counter() - started) * 1000.0
        return DependencyHealthResult(
            dependency_name=dependency_name,
            dependency_type=dependency_type,
            state=state,
            latency_ms=latency_ms,
            error_message=error_message,
            metadata={key: str(value) for key, value in metadata.items()},
        )

    async def _probe_postgresql(self) -> dict[str, Any]:
        def _execute_probe() -> dict[str, Any]:
            db = self.db_session_factory()
            try:
                db.execute(text("SELECT 1"))
                return {"probe": "select_1"}
            finally:
                db.close()

        return await asyncio.to_thread(_execute_probe)

    async def _probe_redis(self) -> dict[str, Any]:
        def _execute_probe() -> dict[str, Any]:
            redis_client = self.redis_client_factory()
            pong = bool(redis_client.ping())
            if not pong:
                raise RuntimeError("redis ping returned false")
            return {"probe": "ping"}

        return await asyncio.to_thread(_execute_probe)

    async def _probe_qdrant(self) -> dict[str, Any]:
        if self.qdrant_client is None:
            # Optional dependency - degrade gracefully when unavailable.
            return {"status": "not_configured"}

        def _execute_probe() -> dict[str, Any]:
            client = self.qdrant_client._get_client()  # noqa: SLF001 - lightweight infra probe
            if hasattr(client, "get_collections"):
                response = client.get_collections()
                count = len(getattr(response, "collections", []) or [])
                return {"collections": count}
            if hasattr(client, "get_collection"):
                client.get_collection(self.qdrant_client.collection_name)
                return {"collection": self.qdrant_client.collection_name}
            return {"status": "ok"}

        return await asyncio.to_thread(_execute_probe)

    async def _probe_neo4j(self) -> dict[str, Any]:
        if self.neo4j_client is None:
            return {"status": "not_configured"}

        def _execute_probe() -> dict[str, Any]:
            self.neo4j_client.execute_read("RETURN 1 AS ok")
            return {"probe": "return_1"}

        return await asyncio.to_thread(_execute_probe)

    async def _probe_llm_provider(self) -> dict[str, Any]:
        if self.llm_client is None:
            return {"status": "not_configured"}

        def _execute_probe() -> dict[str, Any]:
            if not self.llm_client.api_key:
                raise RuntimeError("LLM API key is not configured")

            model = self.llm_client.model
            timeout = float(os.getenv("LLM_HEALTH_TIMEOUT_SECONDS", str(self.config.llm_timeout_seconds)))

            client = self.llm_client._get_client()  # noqa: SLF001 - lightweight infra probe
            if hasattr(client, "models") and hasattr(client.models, "list"):
                client.models.list(timeout=timeout)
                return {"probe": "models_list", "model": model}
            return {"probe": "client_initialized", "model": model}

        return await asyncio.to_thread(_execute_probe)
