"""Admin knowledge graph exploration endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError

from app.core.security import require_role
from app.models.user import User
from app.schemas.admin_knowledge_graph import (
    KnowledgeGraphEntityListResponse,
    KnowledgeGraphEntityResponse,
    KnowledgeGraphQueryFilters,
    KnowledgeGraphRelationshipListResponse,
    KnowledgeGraphVisualizationFilters,
    KnowledgeGraphVisualizationResponse,
)
from app.services.admin_knowledge_graph_service import (
    AdminKnowledgeGraphNotFoundError,
    AdminKnowledgeGraphService,
    AdminKnowledgeGraphServiceError,
    AdminKnowledgeGraphUnavailableError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/knowledge-graph", tags=["admin-knowledge-graph"])


@router.get("/entities", response_model=KnowledgeGraphEntityListResponse, status_code=status.HTTP_200_OK)
def get_graph_entities(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    label: str | None = Query(default=None),
    entity_type: str | None = Query(default=None, alias="type"),
    search: str | None = Query(default=None),
    _admin_user: User = Depends(require_role("admin")),
) -> KnowledgeGraphEntityListResponse:
    service = AdminKnowledgeGraphService()
    try:
        filters = KnowledgeGraphQueryFilters(
            page=page,
            page_size=page_size,
            label=label,
            entity_type=entity_type,
            search=search,
        )
        return service.list_entities(filters)
    except AdminKnowledgeGraphUnavailableError as exc:
        logger.warning("admin_get_graph_entities_fallback_empty", extra={"error": str(exc)})
        return KnowledgeGraphEntityListResponse(
            items=[],
            total=0,
            page=page,
            page_size=page_size,
            total_pages=0,
        )
    except AdminKnowledgeGraphServiceError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("admin_get_graph_entities_failed", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list graph entities") from exc


@router.get("/entities/{entity_id}", response_model=KnowledgeGraphEntityResponse, status_code=status.HTTP_200_OK)
def get_graph_entity_by_id(
    entity_id: str,
    _admin_user: User = Depends(require_role("admin")),
) -> KnowledgeGraphEntityResponse:
    service = AdminKnowledgeGraphService()
    try:
        return service.get_entity(entity_id)
    except AdminKnowledgeGraphNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AdminKnowledgeGraphUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except AdminKnowledgeGraphServiceError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("admin_get_graph_entity_by_id_failed", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch graph entity") from exc


@router.get("/relationships", response_model=KnowledgeGraphRelationshipListResponse, status_code=status.HTTP_200_OK)
def get_graph_relationships(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    label: str | None = Query(default=None),
    entity_type: str | None = Query(default=None, alias="type"),
    relationship_type: str | None = Query(default=None),
    search: str | None = Query(default=None),
    _admin_user: User = Depends(require_role("admin")),
) -> KnowledgeGraphRelationshipListResponse:
    service = AdminKnowledgeGraphService()
    try:
        filters = KnowledgeGraphQueryFilters(
            page=page,
            page_size=page_size,
            label=label,
            entity_type=entity_type,
            relationship_type=relationship_type,
            search=search,
        )
        return service.list_relationships(filters)
    except AdminKnowledgeGraphUnavailableError as exc:
        logger.warning("admin_get_graph_relationships_fallback_empty", extra={"error": str(exc)})
        return KnowledgeGraphRelationshipListResponse(
            items=[],
            total=0,
            page=page,
            page_size=page_size,
            total_pages=0,
        )
    except AdminKnowledgeGraphServiceError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("admin_get_graph_relationships_failed", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list graph relationships") from exc


@router.get("/visualize", response_model=KnowledgeGraphVisualizationResponse, status_code=status.HTTP_200_OK)
def visualize_graph(
    label: str | None = Query(default=None),
    entity_type: str | None = Query(default=None, alias="type"),
    search: str | None = Query(default=None),
    relationship_type: str | None = Query(default=None),
    center_entity_id: str | None = Query(default=None),
    depth: int = Query(default=2, ge=1, le=3),
    limit: int = Query(default=150, ge=1, le=500),
    _admin_user: User = Depends(require_role("admin")),
) -> KnowledgeGraphVisualizationResponse:
    service = AdminKnowledgeGraphService()
    try:
        filters = KnowledgeGraphVisualizationFilters(
            label=label,
            entity_type=entity_type,
            search=search,
            relationship_type=relationship_type,
            center_entity_id=center_entity_id,
            depth=depth,
            limit=limit,
        )
        return service.visualize(filters)
    except AdminKnowledgeGraphUnavailableError as exc:
        logger.warning("admin_visualize_graph_fallback_empty", extra={"error": str(exc)})
        return KnowledgeGraphVisualizationResponse(
            nodes=[],
            edges=[],
            metadata_json={
                "graph_backend_available": False,
                "graph_backend_status": "unavailable",
                "graph_backend_reason": str(exc),
                "fallback_mode": "empty_visualization",
            },
        )
    except AdminKnowledgeGraphServiceError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("admin_visualize_graph_failed", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to visualize graph") from exc
