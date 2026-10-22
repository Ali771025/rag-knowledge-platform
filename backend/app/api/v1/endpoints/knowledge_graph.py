"""Knowledge graph endpoints skeleton."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from app.ingestion.exceptions import IngestionError, IngestionValidationError
from app.schemas.knowledge_graph import (
    GraphContextRequest,
    GraphContextResponse,
    QueryExpansionRequest,
    QueryExpansionResponse,
)
from app.services.knowledge_graph_service import KnowledgeGraphService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kg", tags=["knowledge-graph"])


@router.post("/expand", response_model=QueryExpansionResponse, status_code=status.HTTP_200_OK)
def expand_query(payload: QueryExpansionRequest) -> QueryExpansionResponse:
    """Expand query using knowledge graph context."""
    service = KnowledgeGraphService()
    try:
        return service.expand_query(payload)
    except IngestionValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except IngestionError as exc:
        logger.exception("kg_expand_query_failed", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to expand query") from exc
    except Exception as exc:
        logger.exception("kg_expand_query_unexpected_error", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected knowledge graph error") from exc


@router.post("/context", response_model=GraphContextResponse, status_code=status.HTTP_200_OK)
def get_graph_context(payload: GraphContextRequest) -> GraphContextResponse:
    """Retrieve graph context for a query."""
    service = KnowledgeGraphService()
    try:
        return service.get_graph_context(payload)
    except IngestionValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except IngestionError as exc:
        logger.exception("kg_get_context_failed", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve graph context") from exc
    except Exception as exc:
        logger.exception("kg_get_context_unexpected_error", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected knowledge graph error") from exc
