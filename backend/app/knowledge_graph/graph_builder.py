"""Knowledge graph builder orchestration."""

from __future__ import annotations

import logging
from typing import Any

from app.ingestion.schemas import DocumentChunk
from app.knowledge_graph.graph_repository import GraphRepository, GraphRepositoryError
from app.knowledge_graph.schemas import GraphEntity, GraphRelation

logger = logging.getLogger(__name__)


class GraphBuilderError(Exception):
    """Raised when graph building orchestration fails."""


class GraphBuilder:
    """Coordinates persistence of entities and relations into Neo4j."""

    def __init__(self, repository: GraphRepository | None = None) -> None:
        self.repository = repository or GraphRepository()

    def build_graph_for_document(
        self,
        document_id: str,
        chunks: list[DocumentChunk],
        entities: list[GraphEntity],
        relations: list[GraphRelation],
    ) -> dict[str, Any]:
        """Persist graph nodes/edges and link document/chunks to entities."""
        try:
            self.repository.merge_entities(entities)
            self.repository.merge_relations(relations)
            document_metadata = self._document_metadata(chunks)
            self.repository.link_document_to_entities(document_id, entities, metadata=document_metadata)
            self.build_graph_for_chunks(chunks, entities, relations)
            summary = {
                "document_id": document_id,
                "entities_merged": len(entities),
                "relations_merged": len(relations),
                "chunks_linked": len(chunks),
                "status": "completed",
            }
            logger.info("build_graph_for_document_completed", extra=summary)
            return summary
        except GraphRepositoryError as exc:
            logger.exception("build_graph_for_document_failed", exc_info=exc)
            raise GraphBuilderError(f"failed to build graph for document {document_id}") from exc

    def build_graph_for_chunks(
        self,
        chunks: list[DocumentChunk],
        entities: list[GraphEntity],
        relations: list[GraphRelation],
    ) -> dict[str, Any]:
        """Persist and link graph data at chunk-level granularity."""
        _ = relations  # currently merged at document level; retained for API consistency.
        failures: list[str] = []
        linked_count = 0
        for chunk in chunks:
            try:
                chunk_entities = self._entities_for_chunk(entities, str(chunk.chunk_id))
                self.repository.link_chunk_to_entities(
                    str(chunk.chunk_id),
                    chunk_entities,
                    metadata={
                        **dict(chunk.metadata_json or {}),
                        "document_id": str(chunk.document_id),
                        "text": chunk.text,
                        "position_index": chunk.chunk_index,
                    },
                )
                linked_count += 1
            except GraphRepositoryError as exc:
                logger.warning(
                    "build_graph_for_chunks_partial_failure",
                    extra={"chunk_id": str(chunk.chunk_id), "error": str(exc)},
                )
                failures.append(str(chunk.chunk_id))

        if failures:
            raise GraphBuilderError(f"failed to link {len(failures)} chunks to entities")

        summary = {"chunks_linked": linked_count, "status": "completed"}
        logger.info("build_graph_for_chunks_completed", extra=summary)
        return summary

    def build(self, entities: list[GraphEntity], relations: list[GraphRelation]) -> dict[str, object]:
        """Backward-compatible payload builder used by prior skeletons."""
        return {"entities": entities, "relations": relations}

    @staticmethod
    def _entities_for_chunk(entities: list[GraphEntity], chunk_id: str) -> list[GraphEntity]:
        scoped = [
            entity
            for entity in entities
            if chunk_id in [str(value) for value in (entity.metadata_json or {}).get("chunk_ids", [])]
        ]
        # Backward compatibility for callers that provide entities without provenance.
        return scoped or [entity for entity in entities if not (entity.metadata_json or {}).get("chunk_ids")]

    @staticmethod
    def _document_metadata(chunks: list[DocumentChunk]) -> dict[str, Any]:
        if not chunks:
            return {}
        first = chunks[0]
        metadata = dict(first.metadata_json or {})
        return {
            "source_uri": metadata.get("source_uri"),
            "title": metadata.get("title"),
            "source_type": metadata.get("source_type"),
            "language": metadata.get("language"),
        }
