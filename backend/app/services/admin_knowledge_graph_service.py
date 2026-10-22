"""Admin knowledge graph exploration service."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from app.core.neo4j_client import (
    Neo4jClientAdapter,
    Neo4jConfigurationError,
    Neo4jConnectionError,
    Neo4jError,
    Neo4jQueryError,
)
from app.schemas.admin_knowledge_graph import (
    KnowledgeGraphEdgeResponse,
    KnowledgeGraphEntityListResponse,
    KnowledgeGraphEntityResponse,
    KnowledgeGraphNodeResponse,
    KnowledgeGraphQueryFilters,
    KnowledgeGraphRelationshipListResponse,
    KnowledgeGraphRelationshipResponse,
    KnowledgeGraphVisualizationFilters,
    KnowledgeGraphVisualizationResponse,
)

logger = logging.getLogger(__name__)

_VALID_ENTITY_TYPES = {"person", "organization", "concept", "technology", "location", "other"}


class AdminKnowledgeGraphServiceError(RuntimeError):
    """Raised when admin knowledge graph operations fail."""


class AdminKnowledgeGraphUnavailableError(AdminKnowledgeGraphServiceError):
    """Raised when graph backend is unavailable or not configured."""


class AdminKnowledgeGraphNotFoundError(AdminKnowledgeGraphServiceError):
    """Raised when a graph entity does not exist."""


class AdminKnowledgeGraphService:
    """Read-only service for admin graph exploration endpoints."""

    def __init__(self, *, neo4j_client: Neo4jClientAdapter | None = None) -> None:
        self.neo4j_client = neo4j_client or Neo4jClientAdapter()

    def list_entities(self, filters: KnowledgeGraphQueryFilters) -> KnowledgeGraphEntityListResponse:
        params = self._build_filter_params(filters)
        where_clause = self._entity_where_clause()
        try:
            total_rows = self.neo4j_client.execute_read(
                f"""
                MATCH (n)
                WHERE {where_clause}
                RETURN count(DISTINCT n) AS total
                """,
                params,
            )
            total = int((total_rows[0].get("total") if total_rows else 0) or 0)

            rows = self.neo4j_client.execute_read(
                f"""
                MATCH (n)
                WHERE {where_clause}
                RETURN
                  coalesce(toString(n.id), '') AS id,
                  coalesce(n.name, '') AS name,
                  coalesce(n.entity_type, 'other') AS entity_type,
                  coalesce(n.label, n.source_label, n.metadata_json.label, '') AS source_label,
                  coalesce(n.domain, n.metadata_json.domain, '') AS domain,
                  coalesce(n.description, n.metadata_json.description, '') AS description,
                  coalesce(n.aliases, []) AS aliases,
                  n.confidence AS confidence,
                  coalesce(n.source_ids, n.metadata_json.source_ids, []) AS source_ids,
                  coalesce(n.metadata_json, {{}}) AS metadata_json,
                  n.created_at AS created_at,
                  n.updated_at AS updated_at,
                  labels(n) AS neo4j_labels
                ORDER BY toLower(coalesce(n.name, '')) ASC
                SKIP $offset
                LIMIT $limit
                """,
                params,
            )
        except (Neo4jConfigurationError, Neo4jConnectionError) as exc:
            raise AdminKnowledgeGraphUnavailableError(
                "Knowledge graph backend is unavailable. Verify Neo4j configuration and connectivity."
            ) from exc
        except Neo4jQueryError as exc:
            raise AdminKnowledgeGraphUnavailableError(
                "Knowledge graph backend is unavailable or returned an invalid response."
            ) from exc
        except Neo4jError as exc:
            raise AdminKnowledgeGraphServiceError("Failed to list graph entities") from exc

        items = [self._map_entity_row(row) for row in rows if str(row.get("id", "")).strip() and str(row.get("name", "")).strip()]
        return KnowledgeGraphEntityListResponse(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            total_pages=KnowledgeGraphEntityListResponse.build_total_pages(total=total, page_size=filters.page_size),
        )

    def get_entity(self, entity_id: str) -> KnowledgeGraphEntityResponse:
        safe_id = entity_id.strip()
        if not safe_id:
            raise AdminKnowledgeGraphNotFoundError("Entity not found")

        try:
            rows = self.neo4j_client.execute_read(
                """
                MATCH (n {id: $entity_id})
                OPTIONAL MATCH (n)-[r]-()
                RETURN
                  coalesce(toString(n.id), '') AS id,
                  coalesce(n.name, '') AS name,
                  coalesce(n.entity_type, 'other') AS entity_type,
                  coalesce(n.label, n.source_label, n.metadata_json.label, '') AS source_label,
                  coalesce(n.domain, n.metadata_json.domain, '') AS domain,
                  coalesce(n.description, n.metadata_json.description, '') AS description,
                  coalesce(n.aliases, []) AS aliases,
                  n.confidence AS confidence,
                  coalesce(n.source_ids, n.metadata_json.source_ids, []) AS source_ids,
                  coalesce(n.metadata_json, {}) AS metadata_json,
                  n.created_at AS created_at,
                  n.updated_at AS updated_at,
                  labels(n) AS neo4j_labels,
                  count(r) AS relationship_count
                """,
                {"entity_id": safe_id},
            )
        except (Neo4jConfigurationError, Neo4jConnectionError) as exc:
            raise AdminKnowledgeGraphUnavailableError(
                "Knowledge graph backend is unavailable. Verify Neo4j configuration and connectivity."
            ) from exc
        except Neo4jQueryError as exc:
            raise AdminKnowledgeGraphUnavailableError(
                "Knowledge graph backend is unavailable or returned an invalid response."
            ) from exc
        except Neo4jError as exc:
            raise AdminKnowledgeGraphServiceError("Failed to fetch graph entity") from exc

        if not rows:
            raise AdminKnowledgeGraphNotFoundError("Entity not found")

        row = rows[0]
        if not str(row.get("id", "")).strip() or not str(row.get("name", "")).strip():
            raise AdminKnowledgeGraphNotFoundError("Entity not found")

        entity = self._map_entity_row(row)
        entity.metadata_json = dict(entity.metadata_json or {})
        entity.metadata_json["relationship_count"] = int(row.get("relationship_count") or 0)
        return entity

    def list_relationships(self, filters: KnowledgeGraphQueryFilters) -> KnowledgeGraphRelationshipListResponse:
        params = self._build_filter_params(filters)
        where_clause = self._relationship_where_clause()
        try:
            total_rows = self.neo4j_client.execute_read(
                f"""
                MATCH (source)-[r]->(target)
                WHERE {where_clause}
                RETURN count(r) AS total
                """,
                params,
            )
            total = int((total_rows[0].get("total") if total_rows else 0) or 0)

            rows = self.neo4j_client.execute_read(
                f"""
                MATCH (source)-[r]->(target)
                WHERE {where_clause}
                RETURN
                  coalesce(toString(r.id), toString(source.id) + ':' + type(r) + ':' + toString(target.id)) AS id,
                  coalesce(toString(source.id), '') AS source_entity_id,
                  coalesce(toString(target.id), '') AS target_entity_id,
                  type(r) AS relationship_type,
                  coalesce(r.label, r.metadata_json.label, source.label, source.source_label, source.metadata_json.label, '') AS source_label,
                  r.confidence AS confidence,
                  coalesce(r.metadata_json, {{}}) AS metadata_json
                ORDER BY toUpper(type(r)) ASC, id ASC
                SKIP $offset
                LIMIT $limit
                """,
                params,
            )
        except (Neo4jConfigurationError, Neo4jConnectionError) as exc:
            raise AdminKnowledgeGraphUnavailableError(
                "Knowledge graph backend is unavailable. Verify Neo4j configuration and connectivity."
            ) from exc
        except Neo4jQueryError as exc:
            raise AdminKnowledgeGraphUnavailableError(
                "Knowledge graph backend is unavailable or returned an invalid response."
            ) from exc
        except Neo4jError as exc:
            raise AdminKnowledgeGraphServiceError("Failed to list graph relationships") from exc

        items = [
            self._map_relationship_row(row)
            for row in rows
            if str(row.get("source_entity_id", "")).strip() and str(row.get("target_entity_id", "")).strip()
        ]
        return KnowledgeGraphRelationshipListResponse(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            total_pages=KnowledgeGraphRelationshipListResponse.build_total_pages(total=total, page_size=filters.page_size),
        )

    def visualize(self, filters: KnowledgeGraphVisualizationFilters) -> KnowledgeGraphVisualizationResponse:
        params = {
            "search": filters.search.strip().lower() if filters.search else None,
            "entity_type": filters.entity_type,
            "source_label": filters.label.strip().lower() if filters.label else None,
            "relationship_type": filters.relationship_type.upper() if filters.relationship_type else None,
            "limit": filters.limit,
            "path_limit": min(max(filters.limit * 4, 50), 1500),
            "center_entity_id": filters.center_entity_id,
        }
        where_clause = self._visualization_where_clause()

        if filters.center_entity_id:
            query = f"""
            MATCH (center {{id: $center_entity_id}})
            MATCH path=(center)-[rels*1..{filters.depth}]-(neighbor)
            WITH path
            LIMIT $path_limit
            UNWIND relationships(path) AS rel
            WITH DISTINCT rel, startNode(rel) AS source, endNode(rel) AS target
            WHERE {where_clause}
            RETURN
              coalesce(toString(rel.id), toString(source.id) + ':' + type(rel) + ':' + toString(target.id)) AS edge_id,
              type(rel) AS relation,
              rel.confidence AS confidence,
              coalesce(rel.metadata_json, {{}}) AS rel_metadata,
              coalesce(toString(source.id), '') AS source_id,
              coalesce(source.name, '') AS source_name,
              coalesce(source.entity_type, 'other') AS source_type,
              coalesce(source.domain, source.metadata_json.domain, '') AS source_domain,
              coalesce(source.label, source.source_label, source.metadata_json.label, '') AS source_label,
              coalesce(source.metadata_json, {{}}) AS source_metadata,
              labels(source) AS source_neo4j_labels,
              coalesce(toString(target.id), '') AS target_id,
              coalesce(target.name, '') AS target_name,
              coalesce(target.entity_type, 'other') AS target_type,
              coalesce(target.domain, target.metadata_json.domain, '') AS target_domain,
              coalesce(target.label, target.source_label, target.metadata_json.label, '') AS target_label,
              coalesce(target.metadata_json, {{}}) AS target_metadata,
              labels(target) AS target_neo4j_labels
            ORDER BY relation ASC, edge_id ASC
            LIMIT $limit
            """
        else:
            query = f"""
            MATCH (source)-[rel]->(target)
            WHERE {where_clause}
            RETURN
              coalesce(toString(rel.id), toString(source.id) + ':' + type(rel) + ':' + toString(target.id)) AS edge_id,
              type(rel) AS relation,
              rel.confidence AS confidence,
              coalesce(rel.metadata_json, {{}}) AS rel_metadata,
              coalesce(toString(source.id), '') AS source_id,
              coalesce(source.name, '') AS source_name,
              coalesce(source.entity_type, 'other') AS source_type,
              coalesce(source.domain, source.metadata_json.domain, '') AS source_domain,
              coalesce(source.label, source.source_label, source.metadata_json.label, '') AS source_label,
              coalesce(source.metadata_json, {{}}) AS source_metadata,
              labels(source) AS source_neo4j_labels,
              coalesce(toString(target.id), '') AS target_id,
              coalesce(target.name, '') AS target_name,
              coalesce(target.entity_type, 'other') AS target_type,
              coalesce(target.domain, target.metadata_json.domain, '') AS target_domain,
              coalesce(target.label, target.source_label, target.metadata_json.label, '') AS target_label,
              coalesce(target.metadata_json, {{}}) AS target_metadata,
              labels(target) AS target_neo4j_labels
            ORDER BY relation ASC, edge_id ASC
            LIMIT $limit
            """

        try:
            rows = self.neo4j_client.execute_read(query, params)
        except (Neo4jConfigurationError, Neo4jConnectionError) as exc:
            raise AdminKnowledgeGraphUnavailableError(
                "Knowledge graph backend is unavailable. Verify Neo4j configuration and connectivity."
            ) from exc
        except Neo4jQueryError as exc:
            raise AdminKnowledgeGraphUnavailableError(
                "Knowledge graph backend is unavailable or returned an invalid response."
            ) from exc
        except Neo4jError as exc:
            raise AdminKnowledgeGraphServiceError("Failed to visualize knowledge graph") from exc

        node_map: dict[str, KnowledgeGraphNodeResponse] = {}
        edges: list[KnowledgeGraphEdgeResponse] = []

        for row in rows:
            source_id = str(row.get("source_id", "")).strip()
            target_id = str(row.get("target_id", "")).strip()
            if not source_id or not target_id:
                continue

            source_node = self._map_node(
                node_id=source_id,
                name=row.get("source_name"),
                entity_type=row.get("source_type"),
                domain=row.get("source_domain"),
                source_label=row.get("source_label"),
                metadata=row.get("source_metadata"),
                neo4j_labels=row.get("source_neo4j_labels"),
            )
            target_node = self._map_node(
                node_id=target_id,
                name=row.get("target_name"),
                entity_type=row.get("target_type"),
                domain=row.get("target_domain"),
                source_label=row.get("target_label"),
                metadata=row.get("target_metadata"),
                neo4j_labels=row.get("target_neo4j_labels"),
            )
            node_map[source_node.id] = source_node
            node_map[target_node.id] = target_node

            edge = KnowledgeGraphEdgeResponse(
                id=str(row.get("edge_id") or f"{source_id}:{row.get('relation')}:{target_id}"),
                source=source_id,
                target=target_id,
                relation=str(row.get("relation") or "RELATED_TO").upper(),
                weight=self._normalize_confidence(row.get("confidence")),
                source_label=self._normalize_optional_text(row.get("source_label")),
                metadata_json=self._normalize_metadata(row.get("rel_metadata")),
            )
            edges.append(edge)

        return KnowledgeGraphVisualizationResponse(
            nodes=list(node_map.values()),
            edges=edges,
            metadata_json={
                "graph_backend_available": True,
                "center_entity_id": filters.center_entity_id,
                "depth": filters.depth,
                "limit": filters.limit,
                "returned_nodes": len(node_map),
                "returned_edges": len(edges),
            },
        )

    def _build_filter_params(self, filters: KnowledgeGraphQueryFilters) -> dict[str, Any]:
        offset = (filters.page - 1) * filters.page_size
        return {
            "search": filters.search.strip().lower() if filters.search else None,
            "entity_type": filters.entity_type,
            "source_label": filters.label.strip().lower() if filters.label else None,
            "relationship_type": filters.relationship_type.upper() if filters.relationship_type else None,
            "offset": offset,
            "limit": filters.page_size,
        }

    def _entity_where_clause(self) -> str:
        return """
        n.name IS NOT NULL
        AND ($search IS NULL
             OR toLower(coalesce(n.name, '')) CONTAINS $search
             OR toLower(coalesce(n.description, n.metadata_json.description, '')) CONTAINS $search
             OR any(alias IN coalesce(n.aliases, []) WHERE toLower(alias) CONTAINS $search))
        AND ($entity_type IS NULL OR toLower(coalesce(n.entity_type, '')) = $entity_type)
        AND ($source_label IS NULL OR toLower(coalesce(n.label, n.source_label, n.metadata_json.label, '')) = $source_label)
        """

    def _relationship_where_clause(self) -> str:
        return """
        source.name IS NOT NULL
        AND target.name IS NOT NULL
        AND ($search IS NULL
             OR toLower(coalesce(source.name, '')) CONTAINS $search
             OR toLower(coalesce(target.name, '')) CONTAINS $search
             OR toUpper(type(r)) CONTAINS toUpper($search))
        AND ($entity_type IS NULL
             OR toLower(coalesce(source.entity_type, '')) = $entity_type
             OR toLower(coalesce(target.entity_type, '')) = $entity_type)
        AND ($relationship_type IS NULL OR toUpper(type(r)) = $relationship_type)
        AND ($source_label IS NULL
             OR toLower(coalesce(source.label, source.source_label, source.metadata_json.label, target.label, target.source_label, target.metadata_json.label, r.label, r.metadata_json.label, '')) = $source_label)
        """

    def _visualization_where_clause(self) -> str:
        return """
        source.name IS NOT NULL
        AND target.name IS NOT NULL
        AND ($search IS NULL
             OR toLower(coalesce(source.name, '')) CONTAINS $search
             OR toLower(coalesce(target.name, '')) CONTAINS $search
             OR toUpper(type(rel)) CONTAINS toUpper($search))
        AND ($entity_type IS NULL
             OR toLower(coalesce(source.entity_type, '')) = $entity_type
             OR toLower(coalesce(target.entity_type, '')) = $entity_type)
        AND ($relationship_type IS NULL OR toUpper(type(rel)) = $relationship_type)
        AND ($source_label IS NULL
             OR toLower(coalesce(source.label, source.source_label, source.metadata_json.label, target.label, target.source_label, target.metadata_json.label, rel.label, rel.metadata_json.label, '')) = $source_label)
        """

    def _map_entity_row(self, row: dict[str, Any]) -> KnowledgeGraphEntityResponse:
        entity_type = self._normalize_entity_type(row.get("entity_type"))
        source_ids_raw = row.get("source_ids") if isinstance(row.get("source_ids"), list) else []
        aliases_raw = row.get("aliases") if isinstance(row.get("aliases"), list) else []
        metadata = self._normalize_metadata(row.get("metadata_json"))
        metadata["neo4j_labels"] = [str(label) for label in (row.get("neo4j_labels") or []) if str(label).strip()]

        return KnowledgeGraphEntityResponse(
            id=str(row.get("id")),
            name=str(row.get("name")),
            type=entity_type,
            label=self._normalize_optional_text(row.get("source_label")),
            domain=self._normalize_optional_text(row.get("domain")),
            description=self._normalize_optional_text(row.get("description")),
            aliases=[str(alias).strip() for alias in aliases_raw if str(alias).strip()],
            confidence=self._normalize_confidence(row.get("confidence")),
            source_ids=[str(source_id).strip() for source_id in source_ids_raw if str(source_id).strip()],
            metadata_json=metadata,
            created_at=self._normalize_datetime(row.get("created_at")),
            updated_at=self._normalize_datetime(row.get("updated_at")),
        )

    def _map_relationship_row(self, row: dict[str, Any]) -> KnowledgeGraphRelationshipResponse:
        return KnowledgeGraphRelationshipResponse(
            id=str(row.get("id")),
            source_entity_id=str(row.get("source_entity_id")),
            target_entity_id=str(row.get("target_entity_id")),
            relationship_type=str(row.get("relationship_type") or "RELATED_TO").upper(),
            label=self._normalize_optional_text(row.get("source_label")),
            confidence=self._normalize_confidence(row.get("confidence")),
            metadata_json=self._normalize_metadata(row.get("metadata_json")),
        )

    def _map_node(
        self,
        *,
        node_id: str,
        name: Any,
        entity_type: Any,
        domain: Any,
        source_label: Any,
        metadata: Any,
        neo4j_labels: Any,
    ) -> KnowledgeGraphNodeResponse:
        node_metadata = self._normalize_metadata(metadata)
        node_metadata["neo4j_labels"] = [str(label) for label in (neo4j_labels or []) if str(label).strip()]
        return KnowledgeGraphNodeResponse(
            id=node_id,
            label=self._normalize_optional_text(name) or "Unnamed",
            type=self._normalize_entity_type(entity_type),
            domain=self._normalize_optional_text(domain),
            source_label=self._normalize_optional_text(source_label),
            metadata_json=node_metadata,
        )

    def _normalize_entity_type(self, value: Any) -> str:
        normalized = str(value or "other").strip().lower()
        if normalized in _VALID_ENTITY_TYPES:
            return normalized
        return "other"

    def _normalize_confidence(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        if numeric < 0:
            return 0.0
        if numeric > 1:
            return 1.0
        return numeric

    def _normalize_optional_text(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _normalize_metadata(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return dict(value)
        return {}

    def _normalize_datetime(self, value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        return None
