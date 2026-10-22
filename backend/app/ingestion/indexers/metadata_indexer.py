"""PostgreSQL metadata indexer."""

from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.ingestion.exceptions import IndexerError
from app.ingestion.schemas import IngestionChunk
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.ingestion_job import IngestionJob
from app.models.metadata import DocumentMetadata

logger = logging.getLogger(__name__)


class MetadataIndexerError(IndexerError):
    """Raised when metadata indexer operations fail."""


class MetadataIndexer:
    """Repository-style metadata indexer for ingestion persistence."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    @contextmanager
    def _session_scope(self) -> Iterator[Session]:
        """Provide transactional session scope."""
        if self._session is not None:
            try:
                yield self._session
                self._session.commit()
            except Exception:
                self._session.rollback()
                raise
            return

        session = SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_ingestion_job(
        self,
        *,
        source_type: str,
        source_uri: str,
        status: str = "pending",
        error_message: str | None = None,
        stats_json: dict[str, Any] | None = None,
    ) -> IngestionJob:
        """Create a new ingestion job record."""
        try:
            with self._session_scope() as session:
                job = IngestionJob(
                    source_type=source_type,
                    source_uri=source_uri,
                    status=status,
                    error_message=error_message,
                    stats_json=stats_json or {},
                )
                session.add(job)
                session.flush()
                session.refresh(job)
                logger.info("ingestion_job_created", extra={"job_id": str(job.id), "status": job.status})
                return job
        except Exception as exc:
            logger.exception("create_ingestion_job_failed", exc_info=exc)
            raise MetadataIndexerError("failed to create ingestion job") from exc

    def update_ingestion_job(
        self,
        job_id: UUID,
        *,
        status: str | None = None,
        error_message: str | None = None,
        stats_json: dict[str, Any] | None = None,
        completed_at: datetime | None = None,
    ) -> IngestionJob | None:
        """Update ingestion job fields by ID."""
        try:
            with self._session_scope() as session:
                job = session.get(IngestionJob, job_id)
                if job is None:
                    return None
                if status is not None:
                    job.status = status
                if error_message is not None:
                    job.error_message = error_message
                if stats_json is not None:
                    merged_stats = dict(job.stats_json or {})
                    merged_stats.update(stats_json)
                    job.stats_json = merged_stats
                if completed_at is not None:
                    job.completed_at = completed_at
                elif status in {"completed", "failed", "partial"} and job.completed_at is None:
                    job.completed_at = datetime.now(timezone.utc)
                session.add(job)
                session.flush()
                session.refresh(job)
                logger.info("ingestion_job_updated", extra={"job_id": str(job.id), "status": job.status})
                return job
        except Exception as exc:
            logger.exception("update_ingestion_job_failed", exc_info=exc)
            raise MetadataIndexerError("failed to update ingestion job") from exc

    def store_document(
        self,
        *,
        source_type: str,
        source_uri: str,
        title: str | None = None,
        raw_content: str | None = None,
        cleaned_text: str | None = None,
        language: str | None = None,
        summary: str | None = None,
        content_hash: str | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> Document:
        """Store or update document using idempotent matching rules."""
        try:
            with self._session_scope() as session:
                document = self._find_existing_document(session, source_uri=source_uri, content_hash=content_hash)
                if document is None:
                    document = Document(
                        source_type=source_type,
                        source_uri=source_uri,
                        title=title,
                        raw_content=raw_content,
                        cleaned_text=cleaned_text,
                        language=language,
                        summary=summary,
                        content_hash=content_hash,
                        metadata_json=metadata_json or {},
                    )
                else:
                    document.source_type = source_type
                    document.source_uri = source_uri
                    document.title = title or document.title
                    document.raw_content = raw_content if raw_content is not None else document.raw_content
                    document.cleaned_text = cleaned_text if cleaned_text is not None else document.cleaned_text
                    document.language = language or document.language
                    document.summary = summary if summary is not None else document.summary
                    document.content_hash = content_hash or document.content_hash
                    merged_metadata = dict(document.metadata_json or {})
                    merged_metadata.update(metadata_json or {})
                    document.metadata_json = merged_metadata

                session.add(document)
                session.flush()
                session.refresh(document)
                logger.info("document_stored", extra={"document_id": str(document.id), "source_uri": source_uri})
                return document
        except Exception as exc:
            logger.exception("store_document_failed", exc_info=exc)
            raise MetadataIndexerError("failed to store document") from exc

    def store_chunks(self, document_id: UUID, chunks: list[IngestionChunk]) -> list[Chunk]:
        """Store or update chunks for a document."""
        try:
            with self._session_scope() as session:
                persisted: list[Chunk] = []
                for item in chunks:
                    chunk_index = self._resolve_chunk_index(item)
                    existing = session.scalar(
                        select(Chunk).where(Chunk.document_id == document_id, Chunk.chunk_index == chunk_index)
                    )
                    payload_metadata = dict(getattr(item, "metadata", {}) or {})
                    if existing is None:
                        chunk = Chunk(
                            document_id=document_id,
                            chunk_index=chunk_index,
                            text=item.content,
                            token_count=payload_metadata.get("token_count"),
                            embedding_model=payload_metadata.get("embedding_model"),
                            content_hash=payload_metadata.get("content_hash"),
                            metadata_json=payload_metadata,
                        )
                    else:
                        chunk = existing
                        chunk.text = item.content
                        chunk.token_count = payload_metadata.get("token_count", chunk.token_count)
                        chunk.embedding_model = payload_metadata.get("embedding_model", chunk.embedding_model)
                        chunk.content_hash = payload_metadata.get("content_hash", chunk.content_hash)
                        merged_metadata = dict(chunk.metadata_json or {})
                        merged_metadata.update(payload_metadata)
                        chunk.metadata_json = merged_metadata
                    session.add(chunk)
                    session.flush()
                    persisted.append(chunk)
                logger.info("chunks_stored", extra={"document_id": str(document_id), "count": len(persisted)})
                return persisted
        except Exception as exc:
            logger.exception("store_chunks_failed", exc_info=exc)
            raise MetadataIndexerError("failed to store chunks") from exc

    def store_metadata(self, document_id: UUID, metadata: dict[str, Any]) -> DocumentMetadata:
        """Store extracted metadata for a document."""
        try:
            with self._session_scope() as session:
                existing = session.scalar(
                    select(DocumentMetadata)
                    .where(DocumentMetadata.document_id == document_id)
                    .order_by(DocumentMetadata.created_at.desc())
                    .limit(1)
                )

                tags = metadata.get("tags")
                related_topics = metadata.get("related_topics")
                tags_text = json.dumps(tags) if isinstance(tags, list) else (str(tags) if tags is not None else None)
                related_topics_text = (
                    json.dumps(related_topics)
                    if isinstance(related_topics, list)
                    else (str(related_topics) if related_topics is not None else None)
                )

                if existing is None:
                    record = DocumentMetadata(
                        document_id=document_id,
                        topic=self._to_nullable_str(metadata.get("topic")),
                        category=self._to_nullable_str(metadata.get("category")),
                        subcategory=self._to_nullable_str(metadata.get("subcategory")),
                        difficulty_level=self._to_nullable_str(metadata.get("difficulty_level")),
                        tags=tags_text,
                        section_type=self._to_nullable_str(metadata.get("section_type")),
                        parent_topic=self._to_nullable_str(metadata.get("parent_topic")),
                        related_topics=related_topics_text,
                        language=self._to_nullable_str(metadata.get("language")),
                        word_count=self._to_nullable_int(metadata.get("word_count")),
                    )
                else:
                    record = existing
                    record.topic = self._coalesce_str(metadata.get("topic"), record.topic)
                    record.category = self._coalesce_str(metadata.get("category"), record.category)
                    record.subcategory = self._coalesce_str(metadata.get("subcategory"), record.subcategory)
                    record.difficulty_level = self._coalesce_str(metadata.get("difficulty_level"), record.difficulty_level)
                    record.tags = tags_text or record.tags
                    record.section_type = self._coalesce_str(metadata.get("section_type"), record.section_type)
                    record.parent_topic = self._coalesce_str(metadata.get("parent_topic"), record.parent_topic)
                    record.related_topics = related_topics_text or record.related_topics
                    record.language = self._coalesce_str(metadata.get("language"), record.language)
                    record.word_count = self._to_nullable_int(metadata.get("word_count")) or record.word_count

                session.add(record)
                session.flush()
                session.refresh(record)
                logger.info("document_metadata_stored", extra={"document_id": str(document_id), "metadata_id": str(record.id)})
                return record
        except Exception as exc:
            logger.exception("store_metadata_failed", exc_info=exc)
            raise MetadataIndexerError("failed to store document metadata") from exc

    def get_document(self, document_id: UUID) -> Document | None:
        """Fetch one document by ID."""
        try:
            with self._session_scope() as session:
                return session.get(Document, document_id)
        except Exception as exc:
            logger.exception("get_document_failed", exc_info=exc)
            raise MetadataIndexerError("failed to fetch document") from exc

    def list_documents(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        source_type: str | None = None,
    ) -> list[Document]:
        """List persisted documents with pagination."""
        try:
            with self._session_scope() as session:
                stmt: Select[tuple[Document]] = select(Document).order_by(Document.created_at.desc())
                if source_type:
                    stmt = stmt.where(Document.source_type == source_type)
                stmt = stmt.offset(max(0, offset)).limit(max(1, min(limit, 1000)))
                return list(session.scalars(stmt).all())
        except Exception as exc:
            logger.exception("list_documents_failed", exc_info=exc)
            raise MetadataIndexerError("failed to list documents") from exc

    def get_chunk(self, chunk_id: UUID) -> Chunk | None:
        """Fetch one chunk by ID."""
        try:
            with self._session_scope() as session:
                return session.get(Chunk, chunk_id)
        except Exception as exc:
            logger.exception("get_chunk_failed", exc_info=exc)
            raise MetadataIndexerError("failed to fetch chunk") from exc

    def list_chunks(
        self,
        *,
        document_id: UUID | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[Chunk]:
        """List chunks with optional document filter and pagination."""
        try:
            with self._session_scope() as session:
                stmt: Select[tuple[Chunk]] = select(Chunk).order_by(Chunk.created_at.asc())
                if document_id is not None:
                    stmt = stmt.where(Chunk.document_id == document_id)
                stmt = stmt.offset(max(0, offset)).limit(max(1, min(limit, 2000)))
                return list(session.scalars(stmt).all())
        except Exception as exc:
            logger.exception("list_chunks_failed", exc_info=exc)
            raise MetadataIndexerError("failed to list chunks") from exc

    async def index(self, chunks: list[IngestionChunk]) -> int:
        """Backward-compatible index method for earlier skeleton usage."""
        logger.info("metadata_index_invoked", extra={"chunk_count": len(chunks)})
        return len(chunks)

    def _find_existing_document(
        self,
        session: Session,
        *,
        source_uri: str,
        content_hash: str | None,
    ) -> Document | None:
        if content_hash:
            by_hash = session.scalar(select(Document).where(Document.content_hash == content_hash).limit(1))
            if by_hash is not None:
                return by_hash
        return session.scalar(select(Document).where(Document.source_uri == source_uri).limit(1))

    def _resolve_chunk_index(self, chunk: IngestionChunk) -> int:
        sequence = getattr(chunk, "sequence", 0)
        try:
            index = int(sequence)
        except Exception:
            index = 0
        return max(0, index)

    def _to_nullable_str(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text if text else None

    def _coalesce_str(self, value: Any, current: str | None) -> str | None:
        incoming = self._to_nullable_str(value)
        return incoming if incoming is not None else current

    def _to_nullable_int(self, value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except Exception:
            return None
