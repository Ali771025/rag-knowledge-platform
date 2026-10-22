"""Document endpoints skeleton."""

from __future__ import annotations

import logging
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.metadata import DocumentMetadata
from app.schemas.document import ChunkResponse, DocumentResponse

logger = logging.getLogger(__name__)
router = APIRouter()

SourceType = Literal["web", "discord", "file", "docs"]


class _DocumentQueryRepository:
    """Repository-style query helper for documents/chunks read APIs."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_documents(
        self,
        *,
        limit: int,
        offset: int,
        source_type: SourceType | None,
        topic: str | None,
        language: str | None,
    ) -> list[Document]:
        stmt: Select[tuple[Document]] = select(Document).options(selectinload(Document.chunks)).order_by(Document.created_at.desc())
        stmt = self._apply_document_filters(stmt, source_type=source_type, topic=topic, language=language)
        stmt = stmt.offset(offset).limit(limit)
        return list(self.session.scalars(stmt).all())

    def get_document(self, document_id: UUID) -> Document | None:
        stmt = select(Document).options(selectinload(Document.chunks)).where(Document.id == document_id).limit(1)
        return self.session.scalar(stmt)

    def list_chunks(
        self,
        *,
        limit: int,
        offset: int,
        source_type: SourceType | None,
        topic: str | None,
        language: str | None,
    ) -> list[Chunk]:
        stmt: Select[tuple[Chunk]] = select(Chunk).join(Document, Chunk.document_id == Document.id).order_by(Chunk.created_at.asc())
        if source_type is not None:
            stmt = stmt.where(Document.source_type == source_type)
        if topic:
            topic_text = topic.strip()
            if topic_text:
                stmt = stmt.where(
                    exists(
                        select(1).where(
                            DocumentMetadata.document_id == Document.id,
                            func.lower(DocumentMetadata.topic).contains(topic_text.lower()),
                        )
                    )
                )
        if language:
            normalized_language = language.strip().lower()
            if normalized_language:
                stmt = stmt.where(
                    or_(
                        func.lower(Document.language) == normalized_language,
                        exists(
                            select(1).where(
                                DocumentMetadata.document_id == Document.id,
                                func.lower(DocumentMetadata.language) == normalized_language,
                            )
                        ),
                    )
                )
        stmt = stmt.offset(offset).limit(limit)
        return list(self.session.scalars(stmt).all())

    def get_chunk(self, chunk_id: UUID) -> Chunk | None:
        stmt = select(Chunk).where(Chunk.id == chunk_id).limit(1)
        return self.session.scalar(stmt)

    def _apply_document_filters(
        self,
        stmt: Select[tuple[Document]],
        *,
        source_type: SourceType | None,
        topic: str | None,
        language: str | None,
    ) -> Select[tuple[Document]]:
        if source_type is not None:
            stmt = stmt.where(Document.source_type == source_type)
        if topic:
            topic_text = topic.strip()
            if topic_text:
                stmt = stmt.where(
                    exists(
                        select(1).where(
                            DocumentMetadata.document_id == Document.id,
                            func.lower(DocumentMetadata.topic).contains(topic_text.lower()),
                        )
                    )
                )
        if language:
            normalized_language = language.strip().lower()
            if normalized_language:
                stmt = stmt.where(
                    or_(
                        func.lower(Document.language) == normalized_language,
                        exists(
                            select(1).where(
                                DocumentMetadata.document_id == Document.id,
                                func.lower(DocumentMetadata.language) == normalized_language,
                            )
                        ),
                    )
                )
        return stmt


@router.get("/documents", response_model=list[DocumentResponse], status_code=status.HTTP_200_OK)
def list_documents(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    source_type: SourceType | None = Query(default=None),
    topic: str | None = Query(default=None, min_length=1, max_length=255),
    language: str | None = Query(default=None, min_length=2, max_length=32),
    db: Session = Depends(get_db),
) -> list[DocumentResponse]:
    """List documents with pagination and optional filters."""
    repository = _DocumentQueryRepository(db)
    try:
        return repository.list_documents(
            limit=limit,
            offset=offset,
            source_type=source_type,
            topic=topic,
            language=language,
        )
    except Exception as exc:
        logger.exception("list_documents_endpoint_failed", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list documents") from exc


@router.get("/documents/{document_id}", response_model=DocumentResponse, status_code=status.HTTP_200_OK)
def get_document(document_id: UUID, db: Session = Depends(get_db)) -> DocumentResponse:
    """Fetch one document by id."""
    repository = _DocumentQueryRepository(db)
    try:
        document = repository.get_document(document_id)
    except Exception as exc:
        logger.exception("get_document_endpoint_failed", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch document") from exc

    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.get("/chunks", response_model=list[ChunkResponse], status_code=status.HTTP_200_OK)
def list_chunks(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    source_type: SourceType | None = Query(default=None),
    topic: str | None = Query(default=None, min_length=1, max_length=255),
    language: str | None = Query(default=None, min_length=2, max_length=32),
    db: Session = Depends(get_db),
) -> list[ChunkResponse]:
    """List chunks with pagination and optional document-level filters."""
    repository = _DocumentQueryRepository(db)
    try:
        return repository.list_chunks(
            limit=limit,
            offset=offset,
            source_type=source_type,
            topic=topic,
            language=language,
        )
    except Exception as exc:
        logger.exception("list_chunks_endpoint_failed", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list chunks") from exc


@router.get("/chunks/{chunk_id}", response_model=ChunkResponse, status_code=status.HTTP_200_OK)
def get_chunk(chunk_id: UUID, db: Session = Depends(get_db)) -> ChunkResponse:
    """Fetch one chunk by id."""
    repository = _DocumentQueryRepository(db)
    try:
        chunk = repository.get_chunk(chunk_id)
    except Exception as exc:
        logger.exception("get_chunk_endpoint_failed", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch chunk") from exc

    if chunk is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found")
    return chunk
