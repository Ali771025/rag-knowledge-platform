"""Graph retrieval adapter for query/entity context."""

from __future__ import annotations

import logging
from typing import Any
from uuid import NAMESPACE_DNS, UUID, uuid4, uuid5

from app.core.neo4j_client import Neo4jClientAdapter, Neo4jError
from app.knowledge_graph.graph_repository import GraphRepository
from app.knowledge_graph.query_expander import detect_query_entities
from app.knowledge_graph.schemas import GraphContext, GraphEntity, GraphPath, GraphRelation

logger = logging.getLogger(__name__)

_VALID_ENTITY_TYPES = {"person", "organization", "concept", "technology", "location", "other"}


class GraphRetriever:
    """Read adapter for graph data retrieval."""

    def __init__(
        self,
        neo4j_client: Neo4jClientAdapter | None = None,
        repository: GraphRepository | None = None,
    ) -> None:
        self.repository = repository
        if neo4j_client is not None:
            self.neo4j_client = neo4j_client
        elif repository is not None:
            self.neo4j_client = repository.neo4j_client
        else:
            self.neo4j_client = Neo4jClientAdapter()

        self.max_seed_entities = 12
        self.max_entities = 80
        self.max_relations = 150
        self.max_paths = 40
        self.max_cluster_members = 8

    def get_context_for_query(self, query: str, depth: int = 2) -> GraphContext:
        """Retrieve graph context from a raw user query."""
        query_text = query.strip()
        if not query_text:
            return GraphContext(
                query="empty_query",
                entities=[],
                relations=[],
                paths=[],
                metadata_json={"errors": ["empty_query"], "clusters": []},
            )

        entities = detect_query_entities(query_text)
        if not entities:
            entities = [query_text]

        context = self.get_context_for_entities(entities=entities, depth=depth)
        context.query = query_text
        context.metadata_json["detected_entities"] = entities
        return context

    def get_context_for_entities(self, entities: list[str], depth: int = 2) -> GraphContext:
        """Retrieve graph context for explicit entity list."""
        cleaned_entities = self._dedupe_terms([value for value in entities if value and value.strip()], self.max_seed_entities)
        query_text = ", ".join(cleaned_entities) if cleaned_entities else "entities"
        safe_depth = max(1, min(depth, 3))

        if not cleaned_entities:
            return GraphContext(
                query=query_text,
                entities=[],
                relations=[],
                paths=[],
                metadata_json={"depth": safe_depth, "seed_entities": [], "clusters": []},
            )

        try:
            seed_rows = self._fetch_seed_entities(cleaned_entities, limit=self.max_seed_entities)
            if not seed_rows:
                logger.info("graph_context_no_seed_matches", extra={"entities": cleaned_entities, "depth": safe_depth})
                return GraphContext(
                    query=query_text,
                    entities=[],
                    relations=[],
                    paths=[],
                    metadata_json={"depth": safe_depth, "seed_entities": cleaned_entities, "clusters": []},
                )

            seed_ids = [row["id"] for row in seed_rows if row.get("id")]
            path_rows = self._fetch_path_rows(seed_ids=seed_ids, depth=safe_depth, limit=self.max_paths * 3)
            context = self._build_context(
                query=query_text,
                seed_rows=seed_rows,
                path_rows=path_rows,
                depth=safe_depth,
                requested_entities=cleaned_entities,
            )
            logger.info(
                "graph_context_retrieved",
                extra={
                    "query": query_text,
                    "depth": safe_depth,
                    "seed_count": len(seed_rows),
                    "entity_count": len(context.entities),
                    "relation_count": len(context.relations),
                    "path_count": len(context.paths),
                },
            )
            return context
        except Neo4jError as exc:
            logger.warning(
                "graph_context_neo4j_error",
                extra={"entities": cleaned_entities, "depth": safe_depth, "error": str(exc)},
            )
        except Exception as exc:
            logger.exception("graph_context_unexpected_error", exc_info=exc)

        return GraphContext(
            query=query_text,
            entities=[],
            relations=[],
            paths=[],
            metadata_json={"depth": safe_depth, "seed_entities": cleaned_entities, "clusters": [], "errors": ["graph_lookup_failed"]},
        )

    async def retrieve(self, query: str) -> dict[str, object]:
        """Backward-compatible async wrapper used by earlier skeletons."""
        context = self.get_context_for_query(query=query, depth=2)
        return context.model_dump(mode="json")

    def _fetch_seed_entities(self, entities: list[str], limit: int) -> list[dict[str, Any]]:
        query = """
        UNWIND $terms AS term
        MATCH (n)
        WHERE n.name IS NOT NULL
          AND (
            toLower(n.name) = toLower(term)
            OR toLower(n.name) CONTAINS toLower(term)
            OR toLower(term) CONTAINS toLower(n.name)
            OR any(alias IN coalesce(n.aliases, []) WHERE toLower(alias) = toLower(term))
            OR any(alias IN coalesce(n.aliases, []) WHERE toLower(alias) CONTAINS toLower(term))
          )
        WITH DISTINCT n
        RETURN
          coalesce(n.id, '') AS id,
          coalesce(n.name, '') AS name,
          coalesce(n.entity_type, 'concept') AS entity_type,
          coalesce(toFloat(n.confidence), 0.0) AS confidence,
          coalesce(n.aliases, []) AS aliases,
          labels(n) AS labels
        ORDER BY confidence DESC, name ASC
        LIMIT $limit
        """
        records = self.neo4j_client.execute_read(query, {"terms": entities, "limit": limit})
        return [record for record in records if str(record.get("name", "")).strip()]

    def _fetch_path_rows(self, seed_ids: list[str], depth: int, limit: int) -> list[dict[str, Any]]:
        if not seed_ids:
            return []
        query = f"""
        UNWIND $seed_ids AS seed_id
        MATCH (seed {{id: seed_id}})
        MATCH path=(seed)-[rels*1..{depth}]-(neighbor)
        WHERE neighbor.id IS NOT NULL AND neighbor.name IS NOT NULL
        RETURN
          [n IN nodes(path) | {{
            id: coalesce(n.id, ''),
            name: coalesce(n.name, ''),
            entity_type: coalesce(n.entity_type, 'concept'),
            confidence: coalesce(toFloat(n.confidence), 0.0),
            aliases: coalesce(n.aliases, []),
            labels: labels(n)
          }}] AS path_nodes,
          [r IN relationships(path) | {{
            source_entity_id: coalesce(startNode(r).id, ''),
            target_entity_id: coalesce(endNode(r).id, ''),
            relation_type: type(r),
            confidence: coalesce(toFloat(r.confidence), 0.0),
            evidence: coalesce(r.evidence, ''),
            metadata_json: coalesce(r.metadata_json, {{}})
          }}] AS path_rels,
          length(path) AS hops
        ORDER BY hops ASC
        LIMIT $limit
        """
        return self.neo4j_client.execute_read(query, {"seed_ids": seed_ids, "limit": limit})

    def _build_context(
        self,
        *,
        query: str,
        seed_rows: list[dict[str, Any]],
        path_rows: list[dict[str, Any]],
        depth: int,
        requested_entities: list[str],
    ) -> GraphContext:
        entity_map: dict[str, GraphEntity] = {}
        relation_map: dict[str, GraphRelation] = {}
        relation_uuid_map: dict[str, UUID] = {}
        paths: list[GraphPath] = []
        seen_path_keys: set[str] = set()

        for row in seed_rows:
            entity = self._row_to_entity(row)
            key = str(entity.entity_id)
            entity_map[key] = entity
            if len(entity_map) >= self.max_entities:
                break

        for row in path_rows:
            raw_nodes = row.get("path_nodes") or []
            raw_rels = row.get("path_rels") or []

            path_entity_ids: list[UUID] = []
            path_relation_ids: list[UUID] = []

            for raw_node in raw_nodes:
                entity = self._row_to_entity(raw_node)
                key = str(entity.entity_id)
                if key not in entity_map and len(entity_map) < self.max_entities:
                    entity_map[key] = entity
                path_entity_ids.append(entity.entity_id)

            for raw_rel in raw_rels:
                relation, relation_key = self._row_to_relation(raw_rel)
                if relation_key not in relation_map and len(relation_map) < self.max_relations:
                    relation_map[relation_key] = relation
                    relation_uuid_map[relation_key] = relation.relation_id
                relation_uuid = relation_uuid_map.get(relation_key)
                if relation_uuid is not None:
                    path_relation_ids.append(relation_uuid)

            if path_entity_ids:
                path_key = f"{','.join(str(value) for value in path_entity_ids)}|{','.join(str(value) for value in path_relation_ids)}"
                if path_key not in seen_path_keys and len(paths) < self.max_paths:
                    seen_path_keys.add(path_key)
                    score = 1.0 / max(1, int(row.get("hops", 1)))
                    paths.append(
                        GraphPath(
                            path_id=uuid5(NAMESPACE_DNS, f"path:{path_key}"),
                            entity_ids=path_entity_ids,
                            relation_ids=path_relation_ids,
                            score=score,
                        )
                    )

        clusters = self._build_clusters(paths=paths, entity_map=entity_map)
        metadata_json = {
            "depth": depth,
            "requested_entities": requested_entities,
            "seed_entities": [seed.get("name", "") for seed in seed_rows if seed.get("name")],
            "clusters": clusters,
        }
        return GraphContext(
            query=query,
            entities=list(entity_map.values())[: self.max_entities],
            relations=list(relation_map.values())[: self.max_relations],
            paths=paths[: self.max_paths],
            metadata_json=metadata_json,
        )

    def _row_to_entity(self, row: dict[str, Any]) -> GraphEntity:
        name = str(row.get("name", "")).strip() or "unknown"
        raw_id = str(row.get("id", "")).strip()
        entity_id = self._safe_uuid(raw_id, fallback=f"entity:{name}")
        raw_labels = row.get("labels") if isinstance(row.get("labels"), list) else []
        entity_type = self._normalize_entity_type(row.get("entity_type"), labels=[str(label) for label in raw_labels])
        aliases = row.get("aliases") if isinstance(row.get("aliases"), list) else []
        return GraphEntity(
            entity_id=entity_id,
            name=name,
            entity_type=entity_type,
            confidence=self._clamp_float(row.get("confidence"), minimum=0.0, maximum=1.0),
            aliases=[str(alias).strip() for alias in aliases if str(alias).strip()],
            metadata_json={"labels": [str(label) for label in raw_labels]},
        )

    def _row_to_relation(self, row: dict[str, Any]) -> tuple[GraphRelation, str]:
        source_id = self._safe_uuid(str(row.get("source_entity_id", "")).strip(), fallback=f"src:{row}")
        target_id = self._safe_uuid(str(row.get("target_entity_id", "")).strip(), fallback=f"tgt:{row}")
        relation_type = str(row.get("relation_type", "RELATED_TO")).strip().upper() or "RELATED_TO"
        relation_key = f"{source_id}:{relation_type}:{target_id}"
        relation_id = uuid5(NAMESPACE_DNS, f"relation:{relation_key}")
        metadata_json = row.get("metadata_json") if isinstance(row.get("metadata_json"), dict) else {}
        evidence = str(row.get("evidence", "")).strip() or None
        relation = GraphRelation(
            relation_id=relation_id,
            source_entity_id=source_id,
            target_entity_id=target_id,
            relation_type=relation_type,
            confidence=self._clamp_float(row.get("confidence"), minimum=0.0, maximum=1.0),
            evidence=evidence,
            metadata_json=metadata_json,
        )
        return relation, relation_key

    def _build_clusters(self, paths: list[GraphPath], entity_map: dict[str, GraphEntity]) -> list[dict[str, Any]]:
        cluster_map: dict[str, set[str]] = {}
        for path in paths:
            if len(path.entity_ids) < 2:
                continue
            anchor = str(path.entity_ids[0])
            members = cluster_map.setdefault(anchor, set())
            for entity_id in path.entity_ids[1:]:
                members.add(str(entity_id))

        clusters: list[dict[str, Any]] = []
        for anchor_id, member_ids in cluster_map.items():
            anchor_entity = entity_map.get(anchor_id)
            if anchor_entity is None:
                continue
            member_names: list[str] = []
            for member_id in member_ids:
                entity = entity_map.get(member_id)
                if entity is not None:
                    member_names.append(entity.name)
                if len(member_names) >= self.max_cluster_members:
                    break
            clusters.append({"anchor": anchor_entity.name, "members": member_names, "size": len(member_ids)})

        clusters.sort(key=lambda value: int(value.get("size", 0)), reverse=True)
        return clusters[:10]

    def _normalize_entity_type(self, value: Any, labels: list[str]) -> str:
        raw = str(value or "").strip().lower()
        if raw in _VALID_ENTITY_TYPES:
            return raw
        normalized_labels = {label.strip().lower() for label in labels if label and str(label).strip()}
        if "person" in normalized_labels:
            return "person"
        if "organization" in normalized_labels:
            return "organization"
        if "technology" in normalized_labels:
            return "technology"
        if "location" in normalized_labels:
            return "location"
        return "concept"

    def _safe_uuid(self, raw_value: str, fallback: str) -> UUID:
        if raw_value:
            try:
                return UUID(raw_value)
            except ValueError:
                pass
        return uuid5(NAMESPACE_DNS, fallback)

    def _clamp_float(self, value: Any, minimum: float, maximum: float) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = minimum
        return max(minimum, min(maximum, numeric))

    def _dedupe_terms(self, values: list[str], limit: int) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()
        for value in values:
            normalized = " ".join(value.strip().split())
            if not normalized:
                continue
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(normalized)
            if len(deduped) >= limit:
                break
        return deduped
