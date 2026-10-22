"""Admin RAG configuration and retrieval testing endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models.user import User
from app.schemas.admin_rag import AdminRAGConfig, AdminRAGTestRequest, AdminRAGTestResult
from app.services.admin_rag_service import AdminRAGService, AdminRAGServiceError, AdminRAGUnavailableError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/rag", tags=["admin-rag"])


@router.get("/config", response_model=AdminRAGConfig, status_code=status.HTTP_200_OK)
def get_rag_config(
    _admin_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> AdminRAGConfig:
    service = AdminRAGService(db=db)
    try:
        return service.get_config()
    except Exception as exc:
        logger.exception("admin_get_rag_config_failed", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load RAG config") from exc


@router.put("/config", response_model=AdminRAGConfig, status_code=status.HTTP_200_OK)
def update_rag_config(
    payload: AdminRAGConfig,
    _admin_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> AdminRAGConfig:
    service = AdminRAGService(db=db)
    try:
        return service.update_config(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("admin_update_rag_config_failed", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update RAG config") from exc


@router.post("/test", response_model=AdminRAGTestResult, status_code=status.HTTP_200_OK)
def test_rag_retrieval(
    payload: AdminRAGTestRequest,
    _admin_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> AdminRAGTestResult:
    service = AdminRAGService(db=db)
    try:
        return service.test_retrieval(payload)
    except AdminRAGUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except AdminRAGServiceError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("admin_test_rag_failed", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to run RAG test") from exc
