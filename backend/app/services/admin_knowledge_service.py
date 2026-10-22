"""Admin knowledge source management service."""

from __future__ import annotations

import logging
import re
from os import unlink
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ingestion.indexers.vector_indexer import VectorIndexer, VectorIndexerError
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.ingestion_job import IngestionJob
from app.models.knowledge_source import KnowledgeSource
from app.schemas.admin_knowledge import (
    BulkSourceActionResponse,
    CreateKnowledgeSourceFromUrlRequest,
    IngestionStepStatusResponse,
    KnowledgeSourceListResponse,
    KnowledgeSourceResponse,
    KnowledgeSourceStatusResponse,
    PaginatedResultBase,
)
from app.schemas.ingestion import FileIngestionRequest, UrlIngestionRequest
from app.services.ingestion_service import IngestionService

logger = logging.getLogger(__name__)

LABEL_ALLOWED_RE = re.compile(r"[^a-zA-Z0-9 _:/.-]+")
DOMAIN_ALLOWED_RE = re.compile(r"[^a-zA-Z0-9 _:/.-]+")
MAX_LABEL_LENGTH = 128
MAX_DOMAIN_LENGTH = 128
MAX_TAG_LENGTH = 64
SUPPORTED_UPLOAD_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".markdown"}
MAX_LIST_OFFSET = 20_000
DEFAULT_UPLOAD_MAX_BYTES = max(1, int(getattr(settings, "admin_knowledge_upload_max_bytes", 25 * 1024 * 1024)))
INGESTION_SUBMIT_RETRIES = max(0, int(getattr(settings, "admin_knowledge_ingestion_submit_retries", 2)))
MIME_HINTS_BY_EXTENSION = {
    ".pdf": {"application/pdf"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
    },
    ".txt": {"text/plain"},
    ".md": {"text/markdown", "text/plain"},
    ".markdown": {"text/markdown", "text/plain"},
}


class KnowledgeSourceValidationError(ValueError):
    """Raised when request payload does not satisfy business constraints."""


class KnowledgeSourceNotFoundError(LookupError):
    """Raised when knowledge source does not exist."""


def normalize_label(value: str) -> str:
    normalized = " ".join(str(value or "").strip().split())
    normalized = LABEL_ALLOWED_RE.sub("", normalized).strip().lower()
    if not normalized:
        raise KnowledgeSourceValidationError("label is required")
    if len(normalized) > MAX_LABEL_LENGTH:
        raise KnowledgeSourceValidationError(f"label must be at most {MAX_LABEL_LENGTH} characters")
    return normalized


def normalize_domain(value: str) -> str:
    normalized = " ".join(str(value or "").strip().split())
    normalized = DOMAIN_ALLOWED_RE.sub("", normalized).strip().lower()
    if not normalized:
        raise KnowledgeSourceValidationError("domain is required")
    if len(normalized) > MAX_DOMAIN_LENGTH:
        raise KnowledgeSourceValidationError(f"domain must be at most {MAX_DOMAIN_LENGTH} characters")
    return normalized


def normalize_tags(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in values:
        normalized = " ".join(str(raw or "").strip().split()).lower()
        if not normalized:
            continue
        if len(normalized) > MAX_TAG_LENGTH:
            raise KnowledgeSourceValidationError(f"each tag must be at most {MAX_TAG_LENGTH} characters")
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def parse_tags_form_value(raw: str | None) -> list[str]:
    if raw is None:
        return []
    text = raw.strip()
    if not text:
        return []
    return [item.strip() for item in text.split(",") if item.strip()]


def _map_ingestion_status(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    if normalized == "running":
        return "in_progress"
    if normalized in {"pending", "completed", "failed", "in_progress"}:
        return normalized
    return "pending"


def _resolve_ingestion_status(value: str | None, *, total_chunks: int, embedded_chunks: int) -> str:
    normalized = str(value or "").strip().lower()
    if normalized == "partial":
        if total_chunks > 0 and embedded_chunks >= total_chunks:
            return "completed"
        return "failed"
    return _map_ingestion_status(normalized)


def _map_source_type_for_ingestion(source_type: str) -> str:
    if source_type == "url":
        return "web"
    return source_type


def _looks_like_pdf(header: bytes) -> bool:
    return header.startswith(b"%PDF-")


def _looks_like_zip(header: bytes) -> bool:
    return header.startswith(b"PK\x03\x04") or header.startswith(b"PK\x05\x06") or header.startswith(b"PK\x07\x08")


def _looks_like_text(header: bytes) -> bool:
    if not header:
        return False
    if b"\x00" in header:
        return False
    try:
        header.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


class AdminKnowledgeService:
    """Coordinates admin knowledge source CRUD and ingestion orchestration."""

    def __init__(
        self,
        *,
        db: Session,
        ingestion_service: IngestionService | None = None,
        vector_indexer: VectorIndexer | None = None,
    ) -> None:
        self.db = db
        self.ingestion_service = ingestion_service or IngestionService()
        self.vector_indexer = vector_indexer or VectorIndexer()

    def upload_source(
        self,
        *,
        upload: UploadFile,
        domain: str,
        label: str,
        tags: list[str],
    ) -> KnowledgeSource:
        validated_domain = normalize_domain(domain)
        validated_label = normalize_label(label)
        validated_tags = normalize_tags(tags)
        file_name = (upload.filename or "uploaded-file").strip() or "uploaded-file"
        file_suffix = Path(file_name).suffix.lower()
        if file_suffix not in SUPPORTED_UPLOAD_EXTENSIONS:
            raise KnowledgeSourceValidationError(
                f"unsupported file extension '{file_suffix or '(none)'}'; supported: {sorted(SUPPORTED_UPLOAD_EXTENSIONS)}"
            )

        tmp_path = self._persist_upload(upload, suffix=file_suffix)
        source = KnowledgeSource(
            name=file_name,
            source_type="file",
            source_uri=tmp_path,
            domain=validated_domain,
            label=validated_label,
            tags_json=validated_tags,
            status="pending",
        )
        self.db.add(source)
        self.db.flush()

        metadata_json = {
            "knowledge_source_id": str(source.id),
            "domain": source.domain,
            "label": source.label,
            "tags": list(source.tags_json or []),
            "uploaded_file_name": file_name,
        }
        logger.info(
            "knowledge_ingestion_started",
            extra={
                "source_id": str(source.id),
                "source_type": "file",
                "domain": source.domain,
                "label": source.label,
            },
        )
        ingestion_response = self._submit_with_retry(
            lambda: self.ingestion_service.submit_file_ingestion(
                FileIngestionRequest(
                    source_type="file",
                    file_path=tmp_path,
                    file_name=file_name,
                    metadata_json=metadata_json,
                )
            ),
            source_id=source.id,
            source_type="file",
        )
        self._apply_ingestion_response(source, ingestion_response.model_dump(mode="python"))
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def create_source_from_url(self, payload: CreateKnowledgeSourceFromUrlRequest) -> KnowledgeSource:
        validated_domain = normalize_domain(payload.domain)
        validated_label = normalize_label(payload.label)
        validated_tags = normalize_tags(payload.tags)
        url_text = str(payload.url)
        source_name = self._build_url_source_name(url_text)

        source = KnowledgeSource(
            name=source_name,
            source_type="url",
            source_uri=url_text,
            domain=validated_domain,
            label=validated_label,
            tags_json=validated_tags,
            status="pending",
        )
        self.db.add(source)
        self.db.flush()

        metadata_json = {
            "knowledge_source_id": str(source.id),
            "domain": source.domain,
            "label": source.label,
            "tags": list(source.tags_json or []),
        }
        logger.info(
            "knowledge_ingestion_started",
            extra={
                "source_id": str(source.id),
                "source_type": "url",
                "domain": source.domain,
                "label": source.label,
            },
        )
        ingestion_response = self._submit_with_retry(
            lambda: self.ingestion_service.submit_url_ingestion(
                UrlIngestionRequest(
                    source_type="web",
                    url=url_text,
                    title=source_name,
                    tags=validated_tags,
                    metadata_json=metadata_json,
                )
            ),
            source_id=source.id,
            source_type="url",
        )
        self._apply_ingestion_response(source, ingestion_response.model_dump(mode="python"))
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def list_sources(
        self,
        *,
        page: int,
        page_size: int,
        domain: str | None,
        label: str | None,
        status: str | None,
        source_type: str | None,
        search: str | None,
    ) -> KnowledgeSourceListResponse:
        if (page - 1) * page_size > MAX_LIST_OFFSET:
            raise KnowledgeSourceValidationError(
                f"pagination offset is too large; max offset is {MAX_LIST_OFFSET}"
            )
        stmt: Select[tuple[KnowledgeSource]] = select(KnowledgeSource)
        filters = []

        if domain:
            filters.append(func.lower(KnowledgeSource.domain) == normalize_domain(domain))
        if label:
            filters.append(func.lower(KnowledgeSource.label) == normalize_label(label))
        if status:
            filters.append(KnowledgeSource.status == _map_ingestion_status(status))
        if source_type:
            normalized_type = source_type.strip().lower()
            if normalized_type in {"file", "url"}:
                filters.append(KnowledgeSource.source_type == normalized_type)
        if search:
            search_text = search.strip().lower()
            if search_text:
                like_value = f"%{search_text}%"
                filters.append(
                    or_(
                        func.lower(KnowledgeSource.name).like(like_value),
                        func.lower(KnowledgeSource.source_uri).like(like_value),
                        func.lower(KnowledgeSource.label).like(like_value),
                        func.lower(KnowledgeSource.domain).like(like_value),
                    )
                )

        if filters:
            stmt = stmt.where(and_(*filters))

        total = int(self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
        offset = (page - 1) * page_size
        items = list(
            self.db.scalars(
                stmt.order_by(KnowledgeSource.created_at.desc(), KnowledgeSource.id.desc()).offset(offset).limit(page_size)
            ).all()
        )

        for item in items:
            self._refresh_source_from_ingestion_job(item)

        self.db.commit()

        return KnowledgeSourceListResponse(
            items=[self._to_source_response(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=PaginatedResultBase.build_total_pages(total, page_size),
        )

    def get_source(self, source_id: UUID) -> KnowledgeSource:
        source = self.db.get(KnowledgeSource, source_id)
        if source is None:
            raise KnowledgeSourceNotFoundError(f"knowledge source not found: {source_id}")
        self._refresh_source_from_ingestion_job(source)
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def delete_source(self, source_id: UUID) -> None:
        source = self.db.get(KnowledgeSource, source_id)
        if source is None:
            raise KnowledgeSourceNotFoundError(f"knowledge source not found: {source_id}")

        related_documents = self._get_related_documents(source)
        document_ids = [item.id for item in related_documents]
        chunk_ids = self._list_chunk_ids(document_ids)
        if chunk_ids:
            try:
                self.vector_indexer.delete_chunks(chunk_ids)
            except VectorIndexerError as exc:
                logger.warning(
                    "knowledge_source_vector_delete_partial_failure",
                    extra={"source_id": str(source.id), "error": str(exc)},
                )

        for document in related_documents:
            self.db.delete(document)
        self.db.delete(source)
        self.db.commit()

    def get_source_status(self, source_id: UUID) -> KnowledgeSourceStatusResponse:
        source = self.db.get(KnowledgeSource, source_id)
        if source is None:
            raise KnowledgeSourceNotFoundError(f"knowledge source not found: {source_id}")

        self._refresh_source_from_ingestion_job(source)
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)

        return KnowledgeSourceStatusResponse(
            source_id=source.id,
            status=_map_ingestion_status(source.status),  # type: ignore[arg-type]
            steps=self._build_step_statuses(source),
            total_chunks=max(0, int(source.total_chunks or 0)),
            embedded_chunks=max(0, int(source.embedded_chunks or 0)),
            indexing_completed=bool(source.indexing_completed),
            last_updated_at=source.updated_at,
        )

    def reprocess_source(self, source_id: UUID) -> KnowledgeSourceStatusResponse:
        source = self.db.get(KnowledgeSource, source_id)
        if source is None:
            raise KnowledgeSourceNotFoundError(f"knowledge source not found: {source_id}")

        metadata_json = {
            "knowledge_source_id": str(source.id),
            "domain": source.domain,
            "label": source.label,
            "tags": list(source.tags_json or []),
            "reprocess": True,
        }
        source.status = "in_progress"
        source.error_message = None
        source.indexing_completed = False
        self.db.add(source)
        self.db.flush()

        logger.info(
            "knowledge_ingestion_started",
            extra={
                "source_id": str(source.id),
                "source_type": source.source_type,
                "domain": source.domain,
                "label": source.label,
                "reprocess": True,
            },
        )

        if source.source_type == "url":
            ingestion_response = self._submit_with_retry(
                lambda: self.ingestion_service.submit_url_ingestion(
                    UrlIngestionRequest(
                        source_type="web",
                        url=source.source_uri,
                        title=source.name,
                        tags=list(source.tags_json or []),
                        metadata_json=metadata_json,
                    )
                ),
                source_id=source.id,
                source_type="url",
            )
        elif source.source_type == "file":
            ingestion_response = self._submit_with_retry(
                lambda: self.ingestion_service.submit_file_ingestion(
                    FileIngestionRequest(
                        source_type="file",
                        file_path=source.source_uri,
                        file_name=source.name,
                        metadata_json=metadata_json,
                    )
                ),
                source_id=source.id,
                source_type="file",
            )
        else:
            raise KnowledgeSourceValidationError(f"unsupported source type for reprocess: {source.source_type}")

        self._apply_ingestion_response(source, ingestion_response.model_dump(mode="python"))
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return self.get_source_status(source.id)

    def update_source_label(self, source_id: UUID, *, label: str) -> KnowledgeSource:
        source = self.db.get(KnowledgeSource, source_id)
        if source is None:
            raise KnowledgeSourceNotFoundError(f"knowledge source not found: {source_id}")
        source.label = normalize_label(label)
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def bulk_delete_sources(self, source_ids: list[UUID]) -> BulkSourceActionResponse:
        processed = 0
        failed_ids: list[UUID] = []
        for source_id in source_ids:
            try:
                self.delete_source(source_id)
                processed += 1
            except Exception:
                logger.exception("bulk_delete_source_failed", extra={"source_id": str(source_id)})
                failed_ids.append(source_id)
        return BulkSourceActionResponse(
            requested=len(source_ids),
            processed=processed,
            failed_source_ids=failed_ids,
        )

    def bulk_reprocess_sources(self, source_ids: list[UUID]) -> BulkSourceActionResponse:
        processed = 0
        failed_ids: list[UUID] = []
        for source_id in source_ids:
            try:
                self.reprocess_source(source_id)
                processed += 1
            except Exception:
                logger.exception("bulk_reprocess_source_failed", extra={"source_id": str(source_id)})
                failed_ids.append(source_id)
        return BulkSourceActionResponse(
            requested=len(source_ids),
            processed=processed,
            failed_source_ids=failed_ids,
        )

    def _refresh_source_from_ingestion_job(self, source: KnowledgeSource) -> None:
        if source.ingestion_job_id is None:
            return

        job = self.db.get(IngestionJob, source.ingestion_job_id)
        if job is None:
            return

        previous_status = _map_ingestion_status(source.status)
        previous_embedded = int(source.embedded_chunks or 0)
        previous_total = int(source.total_chunks or 0)
        previous_indexing_completed = bool(source.indexing_completed)

        source.error_message = job.error_message
        stats_json = dict(job.stats_json or {})
        total_chunks = self._safe_int(stats_json.get("total_chunks"))
        embedded_chunks = self._safe_int(stats_json.get("embedded_chunks"))
        source.total_chunks = max(source.total_chunks, total_chunks)
        source.embedded_chunks = max(source.embedded_chunks, embedded_chunks)

        pipeline_result = stats_json.get("pipeline_result")
        if isinstance(pipeline_result, dict):
            document_id = pipeline_result.get("document_id")
            if isinstance(document_id, str):
                try:
                    source.document_id = UUID(document_id)
                except Exception:
                    pass
            source.total_chunks = max(source.total_chunks, self._safe_int(pipeline_result.get("chunks_total")))
            source.embedded_chunks = max(source.embedded_chunks, self._safe_int(pipeline_result.get("chunks_embedded")))

        source.status = _resolve_ingestion_status(
            job.status,
            total_chunks=max(0, int(source.total_chunks or 0)),
            embedded_chunks=max(0, int(source.embedded_chunks or 0)),
        )
        source.indexing_completed = source.status == "completed" and source.total_chunks > 0 and source.embedded_chunks >= source.total_chunks

        if source.document_id is None:
            related_documents = self._get_related_documents(source)
            if len(related_documents) == 1:
                source.document_id = related_documents[0].id

        if source.document_id is not None and source.total_chunks <= 0:
            source.total_chunks, source.embedded_chunks = self._count_chunks_for_documents([source.document_id])
            source.indexing_completed = source.total_chunks > 0 and source.embedded_chunks >= source.total_chunks

        self._log_processing_milestones(
            source=source,
            previous_status=previous_status,
            previous_total_chunks=previous_total,
            previous_embedded_chunks=previous_embedded,
            previous_indexing_completed=previous_indexing_completed,
        )

    def _apply_ingestion_response(self, source: KnowledgeSource, response_data: dict[str, Any]) -> None:
        job_id = response_data.get("job_id")
        resolved_job_id: UUID | None = None
        if isinstance(job_id, UUID):
            resolved_job_id = job_id
        elif isinstance(job_id, str):
            try:
                resolved_job_id = UUID(job_id)
            except Exception:
                resolved_job_id = None

        if resolved_job_id is not None:
            if self.db.get(IngestionJob, resolved_job_id) is not None:
                source.ingestion_job_id = resolved_job_id
            else:
                logger.warning(
                    "knowledge_ingestion_response_job_not_found",
                    extra={
                        "source_id": str(source.id),
                        "ingestion_job_id": str(resolved_job_id),
                    },
                )
        source.status = _map_ingestion_status(str(response_data.get("status", "pending")))
        self._refresh_source_from_ingestion_job(source)

    def _build_step_statuses(self, source: KnowledgeSource) -> list[IngestionStepStatusResponse]:
        total_chunks = max(0, int(source.total_chunks or 0))
        embedded_chunks = max(0, int(source.embedded_chunks or 0))
        status = _map_ingestion_status(source.status)

        uploaded_status: str = "completed"
        parsing_status: str = "pending"
        chunking_status: str = "pending"
        embedding_status: str = "pending"
        indexing_status: str = "pending"
        completed_status: str = "pending"
        failed_status: str = "pending"
        progress = 0

        if status == "pending":
            parsing_status = "pending"
        elif status == "in_progress":
            parsing_status = "in_progress" if total_chunks == 0 else "completed"
            chunking_status = "pending" if total_chunks == 0 else "completed"
            if total_chunks > 0:
                embedding_status = "in_progress" if embedded_chunks < total_chunks else "completed"
                indexing_status = "pending" if embedded_chunks < total_chunks else "in_progress"
        elif status == "completed":
            parsing_status = "completed"
            chunking_status = "completed"
            embedding_status = "completed"
            indexing_status = "completed"
            completed_status = "completed"
            progress = 100
        elif status == "failed":
            parsing_status = "completed" if total_chunks > 0 else "failed"
            chunking_status = "completed" if total_chunks > 0 else "failed"
            embedding_status = "failed" if embedded_chunks < total_chunks or total_chunks == 0 else "completed"
            indexing_status = "failed" if not source.indexing_completed else "completed"
            failed_status = "completed"

        if total_chunks > 0 and progress == 0:
            progress = min(100, int((embedded_chunks / max(total_chunks, 1)) * 100))

        return [
            IngestionStepStatusResponse(step="uploaded", status=uploaded_status, progress=100),
            IngestionStepStatusResponse(step="parsing", status=parsing_status, progress=100 if parsing_status == "completed" else None),
            IngestionStepStatusResponse(step="chunking", status=chunking_status, progress=100 if chunking_status == "completed" else None),
            IngestionStepStatusResponse(step="embedding", status=embedding_status, progress=progress if embedding_status != "pending" else None),
            IngestionStepStatusResponse(
                step="indexing",
                status=indexing_status,
                progress=100 if source.indexing_completed else (progress if indexing_status != "pending" else None),
            ),
            IngestionStepStatusResponse(step="completed", status=completed_status, progress=100 if completed_status == "completed" else None),
            IngestionStepStatusResponse(step="failed", status=failed_status, message=source.error_message),
        ]

    def _get_related_documents(self, source: KnowledgeSource) -> list[Document]:
        ingestion_source_type = _map_source_type_for_ingestion(source.source_type)
        stmt = select(Document).where(
            Document.source_type == ingestion_source_type,
            Document.source_uri == source.source_uri,
        )
        candidates = list(self.db.scalars(stmt).all())
        source_id = str(source.id)
        return [
            item
            for item in candidates
            if isinstance(item.metadata_json, dict) and str(item.metadata_json.get("knowledge_source_id", "")).strip() == source_id
        ]

    def _list_chunk_ids(self, document_ids: list[UUID]) -> list[str]:
        if not document_ids:
            return []
        stmt = select(Chunk.id).where(Chunk.document_id.in_(document_ids))
        return [str(item) for item in self.db.scalars(stmt).all()]

    def _count_chunks_for_documents(self, document_ids: list[UUID]) -> tuple[int, int]:
        if not document_ids:
            return 0, 0
        total = int(self.db.scalar(select(func.count()).select_from(Chunk).where(Chunk.document_id.in_(document_ids))) or 0)
        embedded = int(
            self.db.scalar(
                select(func.count())
                .select_from(Chunk)
                .where(Chunk.document_id.in_(document_ids), Chunk.embedding_model.is_not(None))
            )
            or 0
        )
        return total, embedded

    def _to_source_response(self, source: KnowledgeSource) -> KnowledgeSourceResponse:
        return KnowledgeSourceResponse(
            id=source.id,
            name=source.name,
            type=source.source_type,  # type: ignore[arg-type]
            domain=source.domain,
            label=source.label,
            tags=list(source.tags_json or []),
            created_at=source.created_at,
            updated_at=source.updated_at,
            status=_map_ingestion_status(source.status),  # type: ignore[arg-type]
            total_chunks=max(0, int(source.total_chunks or 0)),
            embedded_chunks=max(0, int(source.embedded_chunks or 0)),
            indexing_completed=bool(source.indexing_completed),
            error_message=source.error_message,
        )

    def _persist_upload(self, upload: UploadFile, *, suffix: str) -> str:
        total_bytes = 0
        header_bytes = b""
        too_large = False
        with NamedTemporaryFile(prefix="knowledge_upload_", suffix=suffix, delete=False) as tmp_file:
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                tmp_file.write(chunk)
                total_bytes += len(chunk)
                if len(header_bytes) < 8192:
                    header_bytes += chunk[: 8192 - len(header_bytes)]
                if total_bytes > DEFAULT_UPLOAD_MAX_BYTES:
                    too_large = True
                    break

            tmp_path = tmp_file.name

        if too_large:
            try:
                unlink(tmp_path)
            except OSError:
                pass
            raise KnowledgeSourceValidationError(
                f"uploaded file exceeds max size of {DEFAULT_UPLOAD_MAX_BYTES} bytes"
            )

        self._validate_upload_mime(
            file_name=upload.filename or "uploaded-file",
            suffix=suffix,
            content_type=upload.content_type,
            header_bytes=header_bytes,
        )
        return tmp_path

    def _build_url_source_name(self, url: str) -> str:
        parsed = urlparse(url)
        base = (parsed.netloc or url).strip()
        path = parsed.path.strip("/")
        if path:
            return f"{base}/{path[:120]}".strip("/")
        return base

    def _validate_upload_mime(
        self,
        *,
        file_name: str,
        suffix: str,
        content_type: str | None,
        header_bytes: bytes,
    ) -> None:
        expected_mime_hints = MIME_HINTS_BY_EXTENSION.get(suffix, set())
        normalized_content_type = str(content_type or "").split(";", 1)[0].strip().lower()
        if normalized_content_type and normalized_content_type not in expected_mime_hints and normalized_content_type != "application/octet-stream":
            raise KnowledgeSourceValidationError(
                f"unexpected content type for {file_name}: {normalized_content_type or '(missing)'}"
            )

        if suffix == ".pdf" and not _looks_like_pdf(header_bytes):
            raise KnowledgeSourceValidationError("uploaded file is not a valid PDF payload")
        if suffix == ".docx" and not _looks_like_zip(header_bytes):
            raise KnowledgeSourceValidationError("uploaded file is not a valid DOCX payload")
        if suffix in {".txt", ".md", ".markdown"} and not _looks_like_text(header_bytes):
            raise KnowledgeSourceValidationError("uploaded file is not valid text/markdown payload")

    def _submit_with_retry(
        self,
        submitter,
        *,
        source_id: UUID,
        source_type: str,
    ):
        last_error: Exception | None = None
        attempts = max(1, INGESTION_SUBMIT_RETRIES + 1)
        for attempt in range(1, attempts + 1):
            try:
                return submitter()
            except Exception as exc:
                last_error = exc
                if attempt >= attempts or not self._is_transient_ingestion_error(exc):
                    logger.exception(
                        "knowledge_ingestion_submit_failed",
                        extra={
                            "source_id": str(source_id),
                            "source_type": source_type,
                            "attempt": attempt,
                        },
                    )
                    raise
                logger.warning(
                    "knowledge_ingestion_submit_retrying",
                    extra={
                        "source_id": str(source_id),
                        "source_type": source_type,
                        "attempt": attempt,
                        "max_attempts": attempts,
                    },
                )
        if last_error is not None:
            raise last_error
        raise RuntimeError("ingestion submission retry flow reached an impossible state")

    def _is_transient_ingestion_error(self, error: Exception) -> bool:
        if isinstance(error, (TimeoutError, ConnectionError, OSError)):
            return True
        text = str(error).strip().lower()
        transient_markers = (
            "temporar",
            "timeout",
            "timed out",
            "connection",
            "unavailable",
            "rate limit",
            "try again",
            "retry",
        )
        return any(marker in text for marker in transient_markers)

    def _log_processing_milestones(
        self,
        *,
        source: KnowledgeSource,
        previous_status: str,
        previous_total_chunks: int,
        previous_embedded_chunks: int,
        previous_indexing_completed: bool,
    ) -> None:
        current_status = _map_ingestion_status(source.status)
        source_id = str(source.id)
        base_payload = {
            "source_id": source_id,
            "source_type": source.source_type,
            "domain": source.domain,
            "label": source.label,
            "total_chunks": int(source.total_chunks or 0),
            "embedded_chunks": int(source.embedded_chunks or 0),
        }

        if previous_status != "in_progress" and current_status == "in_progress":
            logger.info("knowledge_ingestion_started", extra=base_payload)

        previous_embedding_complete = previous_total_chunks > 0 and previous_embedded_chunks >= previous_total_chunks
        current_embedding_complete = (source.total_chunks or 0) > 0 and (source.embedded_chunks or 0) >= (source.total_chunks or 0)
        if not previous_embedding_complete and current_embedding_complete:
            logger.info("knowledge_embedding_completed", extra=base_payload)

        if not previous_indexing_completed and bool(source.indexing_completed):
            logger.info("knowledge_indexing_completed", extra=base_payload)

        if previous_status != "completed" and current_status == "completed":
            logger.info("knowledge_ingestion_completed", extra=base_payload)

        if previous_status != "failed" and current_status == "failed":
            logger.warning(
                "knowledge_ingestion_failed",
                extra={
                    **base_payload,
                    "error_message": (source.error_message or "")[:512],
                },
            )

    def _safe_int(self, value: Any) -> int:
        try:
            return max(0, int(value))
        except Exception:
            return 0
