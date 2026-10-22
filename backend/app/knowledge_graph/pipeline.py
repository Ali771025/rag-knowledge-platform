"""Knowledge graph pipeline orchestration."""

from __future__ import annotations

import logging
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from app.core.kafka_client import KafkaClientAdapter, KafkaError
from app.ingestion.exceptions import IngestionError
from app.ingestion.schemas import DocumentChunk
from app.knowledge_graph.entity_extractor import EntityExtractor
from app.knowledge_graph.graph_builder import GraphBuilder, GraphBuilderError
from app.knowledge_graph.relation_extractor import RelationExtractor
from app.knowledge_graph.schemas import GraphBuildRequest, GraphBuildResult, GraphEntity, GraphRelation

logger = logging.getLogger(__name__)

ZERO_UUID = UUID("00000000-0000-0000-0000-000000000000")


class KnowledgeGraphPipeline:
    """Coordinates extraction, deduplication, and Neo4j graph persistence."""

    def __init__(
        self,
        entity_extractor: EntityExtractor | None = None,
        relation_extractor: RelationExtractor | None = None,
        graph_builder: GraphBuilder | None = None,
        kafka_client: KafkaClientAdapter | None = None,
    ) -> None:
        self.entity_extractor = entity_extractor or EntityExtractor()
        self.relation_extractor = relation_extractor or RelationExtractor()
        self.graph_builder = graph_builder or GraphBuilder()
        self.kafka_client = kafka_client or KafkaClientAdapter()

    def build_for_document(
        self,
        document_id: str,
        chunks: list[DocumentChunk],
        *,
        correlation_id: str | None = None,
        ingestion_job_id: str | None = None,
    ) -> dict[str, Any]:
        """Build graph for a document using provided chunks."""
        errors: list[str] = []
        resolved_correlation_id = correlation_id or str(document_id)
        resolved_ingestion_job_id = ingestion_job_id or str(document_id)
        entities, relations = self._extract_entities_relations(
            chunks,
            errors,
            correlation_id=resolved_correlation_id,
            ingestion_job_id=resolved_ingestion_job_id,
        )

        try:
            self.graph_builder.build_graph_for_document(
                document_id=document_id,
                chunks=chunks,
                entities=entities,
                relations=relations,
            )
            self._publish_event(
                "kg.graph.updated",
                {
                    "document_id": document_id,
                    "chunk_count": len(chunks),
                    "entity_count": len(entities),
                    "relation_count": len(relations),
                },
                correlation_id=resolved_correlation_id,
                ingestion_job_id=resolved_ingestion_job_id,
            )
        except GraphBuilderError as exc:
            logger.warning("kg_graph_builder_document_failed", extra={"document_id": document_id, "error": str(exc)})
            errors.append(f"graph_builder:{exc}")

        status = self._derive_status(errors=errors, entity_count=len(entities), relation_count=len(relations))
        summary = {
            "document_id": document_id,
            "entity_count": len(entities),
            "relation_count": len(relations),
            "status": status,
            "errors": errors,
        }
        logger.info("kg_pipeline_document_completed", extra=summary)
        return summary

    def build_for_chunks(
        self,
        chunks: list[DocumentChunk],
        *,
        correlation_id: str | None = None,
        ingestion_job_id: str | None = None,
    ) -> dict[str, Any]:
        """Build graph from chunks and infer document id from first chunk."""
        document_id = str(chunks[0].document_id) if chunks else str(ZERO_UUID)
        errors: list[str] = []
        resolved_correlation_id = correlation_id or document_id
        resolved_ingestion_job_id = ingestion_job_id or document_id
        entities, relations = self._extract_entities_relations(
            chunks,
            errors,
            correlation_id=resolved_correlation_id,
            ingestion_job_id=resolved_ingestion_job_id,
        )

        try:
            self.graph_builder.build_graph_for_chunks(
                chunks=chunks,
                entities=entities,
                relations=relations,
            )
            self._publish_event(
                "kg.graph.updated",
                {
                    "document_id": document_id,
                    "chunk_count": len(chunks),
                    "entity_count": len(entities),
                    "relation_count": len(relations),
                },
                correlation_id=resolved_correlation_id,
                ingestion_job_id=resolved_ingestion_job_id,
            )
        except GraphBuilderError as exc:
            logger.warning("kg_graph_builder_chunks_failed", extra={"document_id": document_id, "error": str(exc)})
            errors.append(f"graph_builder:{exc}")

        status = self._derive_status(errors=errors, entity_count=len(entities), relation_count=len(relations))
        summary = {
            "document_id": document_id,
            "entity_count": len(entities),
            "relation_count": len(relations),
            "status": status,
            "errors": errors,
        }
        logger.info("kg_pipeline_chunks_completed", extra=summary)
        return summary

    async def run(self, request: GraphBuildRequest) -> GraphBuildResult:
        """Backward-compatible async run wrapper."""
        logger.info("knowledge_graph_pipeline_run_called", extra={"document_id": str(request.document_id)})
        return GraphBuildResult(document_id=request.document_id, entities=0, relations=0, status="pending")

    def _extract_entities_relations(
        self,
        chunks: list[DocumentChunk],
        errors: list[str],
        *,
        correlation_id: str,
        ingestion_job_id: str,
    ) -> tuple[list[GraphEntity], list[GraphRelation]]:
        entity_map: dict[str, GraphEntity] = {}
        relation_map: dict[str, GraphRelation] = {}

        for chunk in chunks:
            try:
                extracted_entities = self.entity_extractor.extract_entities(chunk.text, metadata=dict(chunk.metadata_json or {}))
                extracted_entities = [self._canonicalize_entity(entity, chunk) for entity in extracted_entities]
                self._publish_event(
                    "kg.entities.extracted",
                    {
                        "document_id": str(chunk.document_id),
                        "chunk_id": str(chunk.chunk_id),
                        "entity_count": len(extracted_entities),
                    },
                    correlation_id=correlation_id,
                    ingestion_job_id=ingestion_job_id,
                )
                deduped_entities = self._merge_entities(entity_map, extracted_entities)
                # Build relations against current full entity context.
                extracted_relations = self.relation_extractor.extract_relations(chunk.text, deduped_entities)
                self._publish_event(
                    "kg.relations.extracted",
                    {
                        "document_id": str(chunk.document_id),
                        "chunk_id": str(chunk.chunk_id),
                        "relation_count": len(extracted_relations),
                    },
                    correlation_id=correlation_id,
                    ingestion_job_id=ingestion_job_id,
                )
                self._merge_relations(relation_map, extracted_relations)
            except IngestionError:
                raise
            except Exception as exc:
                logger.warning("kg_pipeline_chunk_processing_failed", extra={"chunk_id": str(chunk.chunk_id), "error": str(exc)})
                errors.append(f"chunk:{chunk.chunk_id}:{exc}")
                continue

        return list(entity_map.values()), list(relation_map.values())

    def _merge_entities(self, entity_map: dict[str, GraphEntity], items: list[GraphEntity]) -> list[GraphEntity]:
        for entity in items:
            key = self._normalize_entity_name(entity.name)
            if not key:
                continue
            existing = entity_map.get(key)
            if existing is None:
                entity_map[key] = entity
                continue

            merged_metadata = self._merge_entity_metadata(existing.metadata_json, entity.metadata_json)
            merged_aliases = list(existing.aliases)
            for alias in [*entity.aliases, entity.name]:
                if alias.casefold() != existing.name.casefold() and alias not in merged_aliases:
                    merged_aliases.append(alias)

            if entity.confidence > existing.confidence:
                entity_map[key] = entity.model_copy(
                    update={
                        "entity_id": existing.entity_id,
                        "aliases": merged_aliases,
                        "metadata_json": merged_metadata,
                    },
                    deep=True,
                )
            else:
                entity_map[key] = existing.model_copy(
                    update={"aliases": merged_aliases, "metadata_json": merged_metadata},
                    deep=True,
                )
        return list(entity_map.values())

    def _canonicalize_entity(self, entity: GraphEntity, chunk: DocumentChunk) -> GraphEntity:
        normalized_name = self._normalize_entity_name(entity.name)
        canonical_id = uuid5(NAMESPACE_URL, f"qora-entity:{normalized_name}")
        metadata = dict(entity.metadata_json or {})
        metadata["document_ids"] = self._merge_string_lists(metadata.get("document_ids"), [str(chunk.document_id)])
        metadata["chunk_ids"] = self._merge_string_lists(metadata.get("chunk_ids"), [str(chunk.chunk_id)])
        source_uri = chunk.metadata_json.get("source_uri") if isinstance(chunk.metadata_json, dict) else None
        source_title = chunk.metadata_json.get("title") if isinstance(chunk.metadata_json, dict) else None
        if source_uri:
            metadata["source_uris"] = self._merge_string_lists(metadata.get("source_uris"), [str(source_uri)])
        if source_title:
            metadata["source_titles"] = self._merge_string_lists(metadata.get("source_titles"), [str(source_title)])
        return entity.model_copy(update={"entity_id": canonical_id, "metadata_json": metadata}, deep=True)

    def _merge_entity_metadata(self, left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
        merged = {**dict(left or {}), **dict(right or {})}
        for key in ("document_ids", "chunk_ids", "source_uris", "source_titles"):
            merged[key] = self._merge_string_lists(left.get(key), right.get(key))
            if not merged[key]:
                merged.pop(key, None)
        return merged

    @staticmethod
    def _merge_string_lists(left: Any, right: Any) -> list[str]:
        output: list[str] = []
        for raw in (left, right):
            values = raw if isinstance(raw, list) else ([raw] if raw else [])
            for value in values:
                text = str(value).strip()
                if text and text not in output:
                    output.append(text)
        return output

    def _merge_relations(self, relation_map: dict[str, GraphRelation], items: list[GraphRelation]) -> None:
        for relation in items:
            key = f"{relation.source_entity_id}:{relation.relation_type}:{relation.target_entity_id}"
            existing = relation_map.get(key)
            if existing is None or relation.confidence > existing.confidence:
                relation_map[key] = relation

    def _normalize_entity_name(self, name: str) -> str:
        return " ".join(name.strip().lower().split())

    def _derive_status(self, errors: list[str], entity_count: int, relation_count: int) -> str:
        if not errors:
            return "completed"
        if entity_count > 0 or relation_count > 0:
            return "partial"
        return "failed"

    def _publish_event(
        self,
        event_name: str,
        payload: dict[str, Any],
        *,
        correlation_id: str,
        ingestion_job_id: str,
    ) -> None:
        try:
            self.kafka_client.publish_event(
                event_name=event_name,
                payload=payload,
                correlation_id=correlation_id,
                ingestion_job_id=ingestion_job_id,
            )
        except KafkaError as exc:
            logger.warning(
                "kafka_event_publish_failed",
                extra={
                    "event_name": event_name,
                    "correlation_id": correlation_id,
                    "ingestion_job_id": ingestion_job_id,
                    "error": str(exc),
                },
            )
            if self.kafka_client.strict_mode:
                raise IngestionError(f"kafka_event_publish_failed:{event_name}") from exc
