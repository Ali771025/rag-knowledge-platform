"""Qdrant client adapter."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

COLLECTION_NAME = "knowledge_base"
VECTOR_SIZE = 3072


class QdrantError(Exception):
    """Base Qdrant adapter exception."""


class QdrantConfigurationError(QdrantError):
    """Raised when client configuration is invalid."""


class QdrantConnectionError(QdrantError):
    """Raised when client connection/dependency is unavailable."""


class QdrantAPIError(QdrantError):
    """Raised when Qdrant API operations fail."""


class QdrantClientAdapter:
    """Production-safe wrapper for Qdrant operations."""

    def __init__(self, url: str | None = None, api_key: str | None = None, timeout: float | None = None) -> None:
        self.url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self.api_key = api_key if api_key is not None else os.getenv("QDRANT_API_KEY")
        self.timeout = timeout if timeout is not None else float(os.getenv("QDRANT_TIMEOUT", "10"))
        self.collection_name = COLLECTION_NAME
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from qdrant_client import QdrantClient
        except Exception as exc:  # pragma: no cover - optional dependency safety
            raise QdrantConnectionError("qdrant-client dependency is unavailable") from exc
        if not self.url:
            raise QdrantConfigurationError("QDRANT_URL is not configured")
        try:
            self._client = QdrantClient(url=self.url, api_key=self.api_key, timeout=self.timeout)
        except Exception as exc:
            raise QdrantConnectionError("failed to initialize Qdrant client") from exc
        return self._client

    def ensure_collection(self) -> None:
        """Ensure required vector collection exists."""
        client = self._get_client()
        try:
            from qdrant_client.models import Distance, VectorParams
            exists = False
            if hasattr(client, "collection_exists"):
                exists = bool(client.collection_exists(self.collection_name))
            else:
                try:
                    client.get_collection(self.collection_name)
                    exists = True
                except Exception:
                    exists = False
            if not exists:
                client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
                )
            logger.info("qdrant_collection_ready", extra={"collection": self.collection_name})
        except Exception as exc:
            raise QdrantAPIError("failed to ensure Qdrant collection") from exc

    def upsert_vectors(self, items: list[dict[str, Any]]) -> None:
        """Upsert vectors into collection.

        Expected item shape: {"id": str|int, "vector": list[float], "payload": dict|None}
        """
        self.ensure_collection()
        if not items:
            return
        client = self._get_client()
        try:
            from qdrant_client.models import PointStruct
            points = []
            for item in items:
                if "id" not in item or "vector" not in item:
                    raise QdrantAPIError("each item must include 'id' and 'vector'")
                points.append(
                    PointStruct(
                        id=item["id"],
                        vector=item["vector"],
                        payload=item.get("payload"),
                    )
                )
            client.upsert(collection_name=self.collection_name, points=points)
            logger.info("qdrant_upsert_success", extra={"collection": self.collection_name, "count": len(points)})
        except QdrantAPIError:
            raise
        except Exception as exc:
            raise QdrantAPIError("failed to upsert vectors") from exc

    def search(
        self,
        query_vector: list[float],
        top_k: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search vectors in collection."""
        self.ensure_collection()
        client = self._get_client()
        try:
            query_filter = None
            if filters:
                from qdrant_client.models import Filter
                query_filter = Filter(**filters)
            results = client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
                with_vectors=False,
            )
            output: list[dict[str, Any]] = []
            for point in results:
                output.append(
                    {
                        "id": getattr(point, "id", None),
                        "score": getattr(point, "score", None),
                        "payload": getattr(point, "payload", None),
                    }
                )
            return output
        except Exception as exc:
            raise QdrantAPIError("failed to search vectors") from exc

    def delete_vectors(self, ids: list[str | int]) -> None:
        """Delete vectors by ids from collection."""
        if not ids:
            return
        self.ensure_collection()
        client = self._get_client()
        try:
            from qdrant_client.models import PointIdsList
            client.delete(collection_name=self.collection_name, points_selector=PointIdsList(points=ids))
            logger.info("qdrant_delete_success", extra={"collection": self.collection_name, "count": len(ids)})
        except Exception as exc:
            raise QdrantAPIError("failed to delete vectors") from exc
