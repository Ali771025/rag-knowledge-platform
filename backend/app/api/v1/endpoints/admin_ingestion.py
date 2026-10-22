"""Admin ingestion endpoints skeleton."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.ingestion.exceptions import IngestionError, IngestionValidationError
from app.schemas.ingestion import DiscordIngestionRequest, FileIngestionRequest, IngestionResponse, UrlIngestionRequest
from app.services.ingestion_service import IngestionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/ingest", tags=["admin-ingestion"])


@router.post("/url", response_model=IngestionResponse, status_code=status.HTTP_202_ACCEPTED)
def submit_url_ingestion(payload: UrlIngestionRequest) -> IngestionResponse:
    """Submit URL ingestion job."""
    service = IngestionService()
    try:
        return service.submit_url_ingestion(payload)
    except IngestionValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except IngestionError as exc:
        logger.exception("admin_submit_url_ingestion_failed", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to submit URL ingestion") from exc
    except Exception as exc:
        logger.exception("admin_submit_url_ingestion_unexpected_error", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected ingestion error") from exc


@router.post("/discord", response_model=IngestionResponse, status_code=status.HTTP_202_ACCEPTED)
def submit_discord_ingestion(payload: DiscordIngestionRequest) -> IngestionResponse:
    """Submit Discord ingestion job."""
    service = IngestionService()
    try:
        return service.submit_discord_ingestion(payload)
    except IngestionValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except IngestionError as exc:
        logger.exception("admin_submit_discord_ingestion_failed", exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit Discord ingestion",
        ) from exc
    except Exception as exc:
        logger.exception("admin_submit_discord_ingestion_unexpected_error", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected ingestion error") from exc


@router.post("/file", response_model=IngestionResponse, status_code=status.HTTP_202_ACCEPTED)
def submit_file_ingestion(payload: FileIngestionRequest) -> IngestionResponse:
    """Submit file ingestion job."""
    service = IngestionService()
    try:
        return service.submit_file_ingestion(payload)
    except IngestionValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except IngestionError as exc:
        logger.exception("admin_submit_file_ingestion_failed", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to submit file ingestion") from exc
    except Exception as exc:
        logger.exception("admin_submit_file_ingestion_unexpected_error", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected ingestion error") from exc


@router.get("/jobs/{job_id}", response_model=IngestionResponse, status_code=status.HTTP_200_OK)
def get_ingestion_job_status(job_id: UUID) -> IngestionResponse:
    """Get ingestion job status."""
    service = IngestionService()
    try:
        return service.get_ingestion_status(job_id)
    except IngestionValidationError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except IngestionError as exc:
        logger.exception("admin_get_ingestion_job_status_failed", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get ingestion job status") from exc
    except Exception as exc:
        logger.exception("admin_get_ingestion_job_status_unexpected_error", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected ingestion error") from exc
