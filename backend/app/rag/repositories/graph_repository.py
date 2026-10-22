"""Read-only Neo4j repository for retrieving graph facts.

This adapter only executes graph read queries for RAG evidence.
It must not merge nodes/relationships or perform schema operations.
"""

from __future__ import annotations

from typing import Any
from uuid import NAMESPACE_DNS, uuid5

from app.core.neo4j_client import Neo4jClientAdapter, Neo4jError
from app.rag.models.rag_types import RetrievalSource, TraceId
from app.rag.schemas.retrieval import RetrievedFact
from app.rag.text_normalization import unique_tokens


class GraphRepositoryError(Exception):
    """Raised when graph fact retrieval fails."""


class GraphRepository:
    """Read-only adapter for graph fact retrieval from Neo4j."""

    def __init__(self, neo4j_client: Neo4jClientAdapter | None = None) -> None:
        self.neo4j_client = neo4j_client or Neo4jClientAdapter()

    def retrieve_facts(self, *, trace_id: TraceId, query: str, top_k: int = 20) -> list[RetrievedFact]:
        """Retrieve graph facts related to query text."""
        query_text = query.strip()
        if not query_text:
            return []

        terms = self._tokenize(query_text)
        safe_top_k = max(1, min(top_k, 100))

        cypher = """
        MATCH (source)-[rel]->(target)
        WHERE source.name IS NOT NULL
          AND target.name IS NOT NULL
          AND NOT type(rel) IN ['CONTAINS', 'MENTIONS', 'MENTIONED_IN']
          AND (
            size($terms) = 0
            OR any(term IN $terms WHERE toLower(source.name) CONTAINS term)
            OR any(term IN $terms WHERE toLower(target.name) CONTAINS term)
            OR any(term IN $terms WHERE toLower(type(rel)) CONTAINS term)
          )
        OPTIONAL MATCH (document:Document)-[:CONTAINS]->(source)
        OPTIONAL MATCH (target_document:Document)-[:CONTAINS]->(target)
        WITH source, rel, target, coalesce(document, target_document) AS evidence_document
        RETURN
          coalesce(source.id, source.name) AS source_node_id,
          coalesce(source.name, '') AS source_name,
          coalesce(target.name, '') AS target_name,
          coalesce(type(rel), 'RELATED_TO') AS relation_type,
          coalesce(toFloat(rel.confidence), 0.0) AS score,
          coalesce(evidence_document.id, '') AS document_id,
          coalesce(evidence_document.source_uri, source.source_uri, '') AS source_uri,
          coalesce(evidence_document.title, source.title, '') AS source_title,
          coalesce(evidence_document.source_type, '') AS source_type,
          coalesce(source.metadata_json, {}) AS source_metadata,
          coalesce(rel.metadata_json, {}) AS relation_metadata
        ORDER BY score DESC, source_name ASC, target_name ASC
        LIMIT $limit
        """

        try:
            rows = self.neo4j_client.execute_read(cypher, {"terms": terms, "limit": safe_top_k})
        except Neo4jError as exc:
            raise GraphRepositoryError("Neo4j is unavailable for fact retrieval") from exc
        except Exception as exc:
            raise GraphRepositoryError("failed to retrieve graph facts") from exc

        facts: list[RetrievedFact] = []
        for row in rows:
            subject = self._to_text(row.get("source_name"))
            predicate = self._to_text(row.get("relation_type"))
            obj = self._to_text(row.get("target_name"))
            source_node_id = self._to_text(row.get("source_node_id")) or "unknown"
            document_id = self._to_text(row.get("document_id"))
            if not subject or not predicate or not obj:
                continue

            fact_id = str(uuid5(NAMESPACE_DNS, f"{source_node_id}:{predicate}:{obj}"))
            metadata = self._merge_metadata(
                source_metadata=row.get("source_metadata"),
                relation_metadata=row.get("relation_metadata"),
            )
            metadata = dict(metadata or {})
            if document_id:
                metadata["document_id"] = document_id
            source_type = self._to_text(row.get("source_type"))
            if source_type:
                metadata["source_type"] = source_type
            facts.append(
                RetrievedFact(
                    fact_id=fact_id,
                    trace_id=trace_id,
                    retrieval_source=RetrievalSource.GRAPH,
                    source_id=f"document:{document_id}" if document_id else f"graph:{source_node_id}",
                    subject=subject,
                    predicate=predicate,
                    obj=obj,
                    score=self._safe_float(row.get("score")),
                    source_uri=self._to_text(row.get("source_uri")),
                    source_title=self._to_text(row.get("source_title")),
                    metadata=metadata or None,
                )
            )

        return facts

    def _tokenize(self, query: str) -> list[str]:
        return unique_tokens(query, limit=24)

    def _merge_metadata(self, *, source_metadata: Any, relation_metadata: Any) -> dict[str, Any] | None:
        merged: dict[str, Any] = {}
        if isinstance(source_metadata, dict):
            merged["source"] = source_metadata
        if isinstance(relation_metadata, dict):
            merged["relation"] = relation_metadata
        return merged or None

    def _to_text(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _safe_float(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
