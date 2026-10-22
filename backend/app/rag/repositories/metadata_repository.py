"""Read-only SQL metadata repository for retrieved chunks.

This adapter only fetches existing metadata rows needed for retrieval grounding.
It must not create/update rows or run schema management operations.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.document import Document
from app.models.metadata import DocumentMetadata


class MetadataRepository:
    """Read-only adapter for chunk/document metadata lookups."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def fetch_chunks_metadata(self, chunk_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Fetch metadata for chunk ids keyed by chunk id text.

        Returns a dictionary with source traceability fields (`source_id`, `source_uri`,
        and `source_title`) and chunk/document descriptors.
        """
        normalized_ids = [value.strip() for value in chunk_ids if value and value.strip()]
        if not normalized_ids:
            return {}
        parsed_ids: list[UUID] = []
        for value in normalized_ids:
            try:
                parsed_ids.append(UUID(value))
            except ValueError:
                continue
        if not parsed_ids:
            return {}

        stmt = (
            select(
                Chunk.id.label("chunk_id"),
                Chunk.chunk_index,
                Chunk.token_count,
                Chunk.embedding_model,
                Chunk.metadata_json.label("chunk_metadata_json"),
                Document.id.label("document_id"),
                Document.source_type,
                Document.source_uri,
                Document.title,
                Document.language.label("document_language"),
                DocumentMetadata.topic,
                DocumentMetadata.category,
                DocumentMetadata.subcategory,
                DocumentMetadata.difficulty_level,
                DocumentMetadata.tags,
                DocumentMetadata.section_type,
                DocumentMetadata.parent_topic,
                DocumentMetadata.related_topics,
            )
            .join(Document, Chunk.document_id == Document.id)
            .outerjoin(DocumentMetadata, DocumentMetadata.document_id == Document.id)
            .where(Chunk.id.in_(parsed_ids))
        )

        rows = self.db.execute(stmt).all()

        output: dict[str, dict[str, Any]] = {}
        for row in rows:
            chunk_id = str(row.chunk_id)
            if chunk_id not in output:
                output[chunk_id] = {
                    "chunk_id": chunk_id,
                    "document_id": str(row.document_id),
                    "source_id": f"document:{row.document_id}",
                    "source_type": row.source_type,
                    "source_uri": row.source_uri,
                    "source_title": row.title,
                    "chunk_index": row.chunk_index,
                    "token_count": row.token_count,
                    "embedding_model": row.embedding_model,
                    "document_language": row.document_language,
                    "chunk_metadata": row.chunk_metadata_json if isinstance(row.chunk_metadata_json, dict) else {},
                    "document_topics": [],
                    "document_categories": [],
                    "document_tags": [],
                }

            if row.topic:
                output[chunk_id]["document_topics"].append(row.topic)
            if row.category:
                output[chunk_id]["document_categories"].append(row.category)
            if row.tags:
                output[chunk_id]["document_tags"].append(row.tags)

            # Preserve one representative structured metadata block for downstream use.
            details = output[chunk_id].setdefault("document_metadata", {})
            if row.subcategory and "subcategory" not in details:
                details["subcategory"] = row.subcategory
            if row.difficulty_level and "difficulty_level" not in details:
                details["difficulty_level"] = row.difficulty_level
            if row.section_type and "section_type" not in details:
                details["section_type"] = row.section_type
            if row.parent_topic and "parent_topic" not in details:
                details["parent_topic"] = row.parent_topic
            if row.related_topics and "related_topics" not in details:
                details["related_topics"] = row.related_topics

        for metadata in output.values():
            metadata["document_topics"] = sorted(set(metadata["document_topics"]))
            metadata["document_categories"] = sorted(set(metadata["document_categories"]))
            metadata["document_tags"] = sorted(set(metadata["document_tags"]))

        return output
