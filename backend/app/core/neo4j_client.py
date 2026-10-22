"""Neo4j client adapter."""

from __future__ import annotations

import logging
import os
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class Neo4jError(Exception):
    """Base Neo4j adapter exception."""


class Neo4jConfigurationError(Neo4jError):
    """Raised when Neo4j config is missing/invalid."""


class Neo4jConnectionError(Neo4jError):
    """Raised when Neo4j driver cannot connect."""


class Neo4jQueryError(Neo4jError):
    """Raised when Neo4j query execution fails."""


class Neo4jClientAdapter:
    """Production-safe wrapper for Neo4j graph operations."""

    def __init__(
        self,
        uri: str | None = None,
        username: str | None = None,
        password: str | None = None,
        database: str | None = None,
    ) -> None:
        self.uri = uri or str(getattr(settings, "neo4j_uri", "")) or os.getenv("NEO4J_URI", "")
        self.username = (
            username
            or str(getattr(settings, "neo4j_user", ""))
            or os.getenv("NEO4J_USERNAME")
            or os.getenv("NEO4J_USER", "")
        )
        self.password = password or str(getattr(settings, "neo4j_password", "")) or os.getenv("NEO4J_PASSWORD", "")
        self.database = (
            database or str(getattr(settings, "neo4j_database", "")) or os.getenv("NEO4J_DATABASE", "neo4j")
        )
        self._driver: Any | None = None

    def _get_driver(self) -> Any:
        if self._driver is not None:
            return self._driver
        if not self.uri or not self.username or not self.password:
            raise Neo4jConfigurationError("NEO4J_URI/NEO4J_USERNAME/NEO4J_PASSWORD must be configured")
        try:
            from neo4j import GraphDatabase
            self._driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
            return self._driver
        except Exception as exc:
            raise Neo4jConnectionError("failed to initialize Neo4j driver") from exc

    def execute_read(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Execute a read query and return records."""
        driver = self._get_driver()
        params = parameters or {}
        try:
            with driver.session(database=self.database) as session:
                result = session.run(query, params)
                return [record.data() for record in result]
        except Exception as exc:
            raise Neo4jQueryError("failed to execute read query") from exc

    def execute_write(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Execute a write query and return records (if any)."""
        driver = self._get_driver()
        params = parameters or {}
        try:
            with driver.session(database=self.database) as session:
                result = session.run(query, params)
                return [record.data() for record in result]
        except Exception as exc:
            raise Neo4jQueryError("failed to execute write query") from exc

    def health_check(self) -> bool:
        """Check Neo4j connectivity."""
        driver = self._get_driver()
        try:
            driver.verify_connectivity()
            return True
        except Exception as exc:
            raise Neo4jConnectionError("Neo4j connectivity check failed") from exc

    def close(self) -> None:
        """Close driver if initialized."""
        if self._driver is None:
            return
        try:
            self._driver.close()
            self._driver = None
        except Exception as exc:
            raise Neo4jConnectionError("failed to close Neo4j driver") from exc
