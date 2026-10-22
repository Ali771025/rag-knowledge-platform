"""Neo4j graph repository."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.core.neo4j_client import Neo4jClientAdapter, Neo4jError
from app.knowledge_graph.schemas import GraphEntity, GraphRelation

logger = logging.getLogger(__name__)

ALLOWED_LABELS = {
    "Concept",
    "Technology",
    "Project",
    "Feature",
    "Service",
    "Organization",
    "Person",
    "Document",
    "Chunk",
}

ALLOWED_RELATIONSHIPS = {
    "USES",
    "DEPENDS_ON",
    "PART_OF",
    "IMPLEMENTS",
    "RELATED_TO",
    "PROVIDES",
    "MENTIONS",
    "CONTAINS",
    "MENTIONED_IN",
}

ENTITY_TYPE_TO_LABEL = {
    "concept": "Concept",
    "technology": "Technology",
    "organization": "Organization",
    "person": "Person",
    "location": "Concept",
    "other": "Concept",
}


class GraphRepositoryError(Exception):
    """Raised when Neo4j graph persistence fails."""


class GraphRepository:
    """Graph persistence adapter backed by Neo4j MERGE semantics."""

    def __init__(self, neo4j_client: Neo4jClientAdapter | None = None) -> None:
        self.neo4j_client = neo4j_client or Neo4jClientAdapter()

    def merge_entity(self, entity: GraphEntity) -> None:
        """Merge one entity node by stable id."""
        label = self._resolve_entity_label(entity)
        safe_label = self._sanitize_cypher_identifier(label, allowed=ALLOWED_LABELS)
        query = f"""
        MERGE (e:{safe_label} {{id: $entity_id}})
        ON CREATE SET e.created_at = datetime()
        SET e.name = $name,
            e.entity_type = $entity_type,
            e.confidence = $confidence,
            e.aliases = $aliases,
            e.metadata_json = $metadata_json,
            e.updated_at = datetime()
        """
        params = {
            "entity_id": str(entity.entity_id),
            "name": entity.name,
            "entity_type": entity.entity_type,
            "confidence": entity.confidence,
            "aliases": list(entity.aliases),
            "metadata_json": dict(entity.metadata_json or {}),
        }
        try:
            self.neo4j_client.execute_write(query, params)
        except Neo4jError as exc:
            logger.exception("merge_entity_failed", exc_info=exc)
            raise GraphRepositoryError(f"failed to merge entity {entity.entity_id}") from exc

    def merge_entities(self, entities: list[GraphEntity]) -> None:
        """Merge multiple entity nodes."""
        errors: list[str] = []
        for entity in entities:
            try:
                self.merge_entity(entity)
            except Exception as exc:
                errors.append(str(entity.entity_id))
                logger.warning("merge_entities_partial_failure", extra={"entity_id": str(entity.entity_id), "error": str(exc)})
        if errors:
            raise GraphRepositoryError(f"failed to merge {len(errors)} entities")

    def merge_relation(self, relation: GraphRelation) -> None:
        """Merge one relationship by source/target/type."""
        rel_type = self._sanitize_relation_type(relation.relation_type)
        query = f"""
        MATCH (source {{id: $source_entity_id}})
        MATCH (target {{id: $target_entity_id}})
        MERGE (source)-[r:{rel_type}]->(target)
        ON CREATE SET r.created_at = datetime()
        SET r.confidence = CASE
                WHEN r.confidence IS NULL OR r.confidence < $confidence THEN $confidence
                ELSE r.confidence
            END,
            r.evidence = CASE
                WHEN $evidence IS NULL OR $evidence = '' THEN r.evidence
                ELSE $evidence
            END,
            r.metadata_json = $metadata_json,
            r.updated_at = datetime()
        """
        params = {
            "source_entity_id": str(relation.source_entity_id),
            "target_entity_id": str(relation.target_entity_id),
            "confidence": float(relation.confidence),
            "evidence": relation.evidence,
            "metadata_json": dict(relation.metadata_json or {}),
        }
        try:
            self.neo4j_client.execute_write(query, params)
        except Neo4jError as exc:
            logger.exception("merge_relation_failed", exc_info=exc)
            raise GraphRepositoryError(
                f"failed to merge relation {relation.source_entity_id}-{relation.relation_type}-{relation.target_entity_id}"
            ) from exc

    def merge_relations(self, relations: list[GraphRelation]) -> None:
        """Merge multiple relationships."""
        errors: list[str] = []
        for relation in relations:
            try:
                self.merge_relation(relation)
            except Exception as exc:
                errors.append(f"{relation.source_entity_id}:{relation.relation_type}:{relation.target_entity_id}")
                logger.warning(
                    "merge_relations_partial_failure",
                    extra={
                        "source_entity_id": str(relation.source_entity_id),
                        "target_entity_id": str(relation.target_entity_id),
                        "relation_type": relation.relation_type,
                        "error": str(exc),
                    },
                )
        if errors:
            raise GraphRepositoryError(f"failed to merge {len(errors)} relations")

    def link_document_to_entities(
        self,
        document_id: str,
        entities: list[GraphEntity],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Link document node to provided entities."""
        entity_ids = [str(entity.entity_id) for entity in entities]
        if not entity_ids:
            return
        contains_rel = self._sanitize_relation_type("CONTAINS")
        mentioned_in_rel = self._sanitize_relation_type("MENTIONED_IN")
        query = f"""
        MERGE (d:Document {{id: $document_id}})
        ON CREATE SET d.created_at = datetime()
        SET d.name = coalesce($title, d.name, $document_id),
            d.title = coalesce($title, d.title),
            d.source_uri = coalesce($source_uri, d.source_uri),
            d.source_type = coalesce($source_type, d.source_type),
            d.language = coalesce($language, d.language),
            d.updated_at = datetime()
        WITH d
        UNWIND $entity_ids AS entity_id
        MATCH (e {{id: entity_id}})
        MERGE (d)-[:{contains_rel}]->(e)
        MERGE (e)-[:{mentioned_in_rel}]->(d)
        """
        try:
            source = dict(metadata or {})
            self.neo4j_client.execute_write(
                query,
                {
                    "document_id": document_id,
                    "entity_ids": entity_ids,
                    "title": source.get("title"),
                    "source_uri": source.get("source_uri"),
                    "source_type": source.get("source_type"),
                    "language": source.get("language"),
                },
            )
        except Neo4jError as exc:
            logger.exception("link_document_to_entities_failed", exc_info=exc)
            raise GraphRepositoryError(f"failed to link document {document_id} to entities") from exc

    def link_chunk_to_entities(
        self,
        chunk_id: str,
        entities: list[GraphEntity],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Link chunk node to provided entities."""
        entity_ids = [str(entity.entity_id) for entity in entities]
        if not entity_ids:
            return
        mentions_rel = self._sanitize_relation_type("MENTIONS")
        mentioned_in_rel = self._sanitize_relation_type("MENTIONED_IN")
        query = f"""
        MERGE (c:Chunk {{id: $chunk_id}})
        ON CREATE SET c.created_at = datetime()
        SET c.name = $chunk_id,
            c.document_id = coalesce($document_id, c.document_id),
            c.text = coalesce($text, c.text),
            c.source_uri = coalesce($source_uri, c.source_uri),
            c.title = coalesce($title, c.title),
            c.position_index = coalesce($position_index, c.position_index),
            c.updated_at = datetime()
        WITH c
        UNWIND $entity_ids AS entity_id
        MATCH (e {{id: entity_id}})
        MERGE (c)-[:{mentions_rel}]->(e)
        MERGE (e)-[:{mentioned_in_rel}]->(c)
        """
        try:
            source = dict(metadata or {})
            self.neo4j_client.execute_write(
                query,
                {
                    "chunk_id": chunk_id,
                    "entity_ids": entity_ids,
                    "document_id": source.get("document_id"),
                    "text": source.get("text"),
                    "source_uri": source.get("source_uri"),
                    "title": source.get("title"),
                    "position_index": source.get("position_index"),
                },
            )
        except Neo4jError as exc:
            logger.exception("link_chunk_to_entities_failed", exc_info=exc)
            raise GraphRepositoryError(f"failed to link chunk {chunk_id} to entities") from exc

    async def save(self, graph_payload: dict[str, object]) -> None:
        """Backward-compatible async save wrapper."""
        _ = graph_payload

    def _resolve_entity_label(self, entity: GraphEntity) -> str:
        metadata = dict(entity.metadata_json or {})
        metadata_label_candidates = [
            metadata.get("neo4j_label"),
            metadata.get("entity_label"),
            metadata.get("llm_type"),
            (metadata.get("properties") or {}).get("type") if isinstance(metadata.get("properties"), dict) else None,
        ]
        for candidate in metadata_label_candidates:
            if not candidate:
                continue
            normalized = self._normalize_label(candidate)
            if normalized in ALLOWED_LABELS:
                return normalized
        return ENTITY_TYPE_TO_LABEL.get(entity.entity_type, "Concept")

    def _normalize_label(self, value: Any) -> str:
        raw = str(value).strip()
        if not raw:
            return ""
        parts = re.split(r"[^A-Za-z0-9]+", raw)
        return "".join(part.capitalize() for part in parts if part)

    def _sanitize_relation_type(self, relation_type: str) -> str:
        rel = relation_type.strip().upper()
        return self._sanitize_cypher_identifier(rel, allowed=ALLOWED_RELATIONSHIPS)

    def _sanitize_cypher_identifier(self, value: str, allowed: set[str]) -> str:
        if value not in allowed:
            raise GraphRepositoryError(f"identifier '{value}' is not in allowlist")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
            raise GraphRepositoryError(f"identifier '{value}' has invalid format")
        return value
