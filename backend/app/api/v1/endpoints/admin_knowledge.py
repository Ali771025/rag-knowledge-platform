"""Admin knowledge source management endpoints."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models.user import User
from app.schemas.admin_knowledge import (
    BulkSourceActionRequest,
    BulkSourceActionResponse,
    CreateKnowledgeSourceFromUrlRequest,
    KnowledgeSourceListResponse,
    KnowledgeSourceResponse,
    KnowledgeSourceStatusResponse,
    UpdateKnowledgeLabelRequest,
)
from app.services.admin_knowledge_service import (
    AdminKnowledgeService,
    KnowledgeSourceNotFoundError,
    KnowledgeSourceValidationError,
    parse_tags_form_value,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/knowledge", tags=["admin-knowledge"])


def _normalize_status(value: str) -> str:
    normalized = value.strip().lower()
    if normalized == "running":
        return "in_progress"
    if normalized in {"pending", "in_progress", "completed", "failed"}:
        return normalized
    return "pending"


def _to_source_response(source) -> KnowledgeSourceResponse:
    return KnowledgeSourceResponse(
        id=source.id,
        name=source.name,
        type=source.source_type,
        domain=source.domain,
        label=source.label,
        tags=list(source.tags_json or []),
        created_at=source.created_at,
        updated_at=source.updated_at,
        status=_normalize_status(source.status),
        total_chunks=max(0, int(source.total_chunks or 0)),
        embedded_chunks=max(0, int(source.embedded_chunks or 0)),
        indexing_completed=bool(source.indexing_completed),
        error_message=source.error_message,
    )


@router.post("/upload", response_model=KnowledgeSourceResponse, status_code=status.HTTP_201_CREATED)
def upload_knowledge_source(
    document: UploadFile = File(...),
    domain: str = Form(...),
    label: str = Form(...),
    tags: list[str] = Form(default=[]),
    tags_bracket: list[str] = Form(default=[], alias="tags[]"),
    tags_csv: str | None = Form(default=None),
    _admin_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> KnowledgeSourceResponse:
    service = AdminKnowledgeService(db=db)
    try:
        merged_tags = [*tags, *tags_bracket, *parse_tags_form_value(tags_csv)]
        source = service.upload_source(upload=document, domain=domain, label=label, tags=merged_tags)
        return _to_source_response(source)
    except KnowledgeSourceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("admin_upload_knowledge_source_failed", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to upload knowledge source") from exc


@router.post("/url", response_model=KnowledgeSourceResponse, status_code=status.HTTP_201_CREATED)
def create_knowledge_source_from_url(
    payload: CreateKnowledgeSourceFromUrlRequest,
    _admin_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> KnowledgeSourceResponse:
    service = AdminKnowledgeService(db=db)
    try:
        source = service.create_source_from_url(payload)
        return _to_source_response(source)
    except KnowledgeSourceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("admin_create_knowledge_source_from_url_failed", exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create knowledge source from URL",
        ) from exc


@router.get("/sources", response_model=KnowledgeSourceListResponse, status_code=status.HTTP_200_OK)
def get_knowledge_sources(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    domain: str | None = Query(default=None),
    label: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    type_filter: str | None = Query(default=None, alias="type"),
    search: str | None = Query(default=None),
    _admin_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> KnowledgeSourceListResponse:
    service = AdminKnowledgeService(db=db)
    try:
        return service.list_sources(
            page=page,
            page_size=page_size,
            domain=domain,
            label=label,
            status=status_filter,
            source_type=type_filter,
            search=search,
        )
    except KnowledgeSourceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("admin_get_knowledge_sources_failed", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list knowledge sources") from exc


@router.post("/sources/bulk-delete", response_model=BulkSourceActionResponse, status_code=status.HTTP_200_OK)
def bulk_delete_knowledge_sources(
    payload: BulkSourceActionRequest,
    _admin_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> BulkSourceActionResponse:
    service = AdminKnowledgeService(db=db)
    try:
        return service.bulk_delete_sources(payload.source_ids)
    except Exception as exc:
        logger.exception("admin_bulk_delete_knowledge_sources_failed", exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bulk delete knowledge sources",
        ) from exc


@router.post("/sources/bulk-reprocess", response_model=BulkSourceActionResponse, status_code=status.HTTP_200_OK)
def bulk_reprocess_knowledge_sources(
    payload: BulkSourceActionRequest,
    _admin_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> BulkSourceActionResponse:
    service = AdminKnowledgeService(db=db)
    try:
        return service.bulk_reprocess_sources(payload.source_ids)
    except Exception as exc:
        logger.exception("admin_bulk_reprocess_knowledge_sources_failed", exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bulk reprocess knowledge sources",
        ) from exc


@router.get("/sources/{source_id}", response_model=KnowledgeSourceResponse, status_code=status.HTTP_200_OK)
def get_knowledge_source(
    source_id: UUID,
    _admin_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> KnowledgeSourceResponse:
    service = AdminKnowledgeService(db=db)
    try:
        source = service.get_source(source_id)
        return _to_source_response(source)
    except KnowledgeSourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("admin_get_knowledge_source_failed", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch knowledge source") from exc


@router.get("/sources/{source_id}/status", response_model=KnowledgeSourceStatusResponse, status_code=status.HTTP_200_OK)
def get_knowledge_source_status(
    source_id: UUID,
    _admin_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> KnowledgeSourceStatusResponse:
    service = AdminKnowledgeService(db=db)
    try:
        return service.get_source_status(source_id)
    except KnowledgeSourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("admin_get_knowledge_source_status_failed", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch knowledge source status") from exc


@router.delete(
    "/sources/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_knowledge_source(
    source_id: UUID,
    _admin_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> Response:
    service = AdminKnowledgeService(db=db)
    try:
        service.delete_source(source_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except KnowledgeSourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("admin_delete_knowledge_source_failed", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete knowledge source") from exc


@router.post("/sources/{source_id}/reprocess", response_model=KnowledgeSourceStatusResponse, status_code=status.HTTP_200_OK)
def reprocess_knowledge_source(
    source_id: UUID,
    _admin_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> KnowledgeSourceStatusResponse:
    service = AdminKnowledgeService(db=db)
    try:
        return service.reprocess_source(source_id)
    except KnowledgeSourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except KnowledgeSourceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("admin_reprocess_knowledge_source_failed", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to reprocess knowledge source") from exc


@router.patch("/sources/{source_id}/label", response_model=KnowledgeSourceResponse, status_code=status.HTTP_200_OK)
def update_knowledge_source_label(
    source_id: UUID,
    payload: UpdateKnowledgeLabelRequest,
    _admin_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> KnowledgeSourceResponse:
    service = AdminKnowledgeService(db=db)
    try:
        source = service.update_source_label(source_id, label=payload.label)
        return _to_source_response(source)
    except KnowledgeSourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except KnowledgeSourceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("admin_update_knowledge_source_label_failed", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update source label") from exc
