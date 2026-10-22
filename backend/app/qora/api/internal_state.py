from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models.user import User
from app.qora.application.errors import StateNotFoundError, StateVersionConflictError
from app.qora.application.state_service import QoraStateService
from app.qora.infrastructure.persistence.models import AgentUserState, UserInteractionEvent

router = APIRouter(prefix="/internal/agent", tags=["internal-agent"], include_in_schema=False)


def _state_payload(state: AgentUserState) -> dict[str, Any]:
    return {
        "id": str(state.id),
        "user_id": str(state.user_id),
        "conversation_id": str(state.conversation_id),
        "persona_core": state.persona_core,
        "persona_scores": state.persona_scores,
        "persona_modifiers": state.persona_modifiers,
        "depth_level": state.depth_level,
        "persona_confidence": state.persona_confidence,
        "selected_section": state.selected_section,
        "current_intent": state.current_intent,
        "intent_confidence": state.intent_confidence,
        "conversation_stage": state.conversation_stage,
        "matched_product": state.matched_product,
        "product_priority_reason": state.product_priority_reason,
        "next_best_action": state.next_best_action,
        "current_points": state.current_points,
        "current_level": state.current_level,
        "readiness_score": state.readiness_score,
        "reward_sensitivity": state.reward_sensitivity,
        "version": state.version,
        "created_at": state.created_at.isoformat(),
        "updated_at": state.updated_at.isoformat(),
    }


def _event_payload(event: UserInteractionEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        "metadata": event.metadata_json,
        "occurred_at": event.occurred_at.isoformat(),
        "request_id": event.request_id,
    }


@router.get("/state/{user_id}")
def get_state(
    user_id: UUID,
    conversation_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
) -> dict[str, Any]:
    service = QoraStateService(db)
    try:
        state = (
            service.load_state(user_id=user_id, conversation_id=conversation_id)
            if conversation_id
            else service.states.latest_for_user(user_id)
        )
    except StateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if state is None:
        raise HTTPException(status_code=404, detail="QORA state not found")
    return _state_payload(state)


@router.get("/state/{user_id}/history")
def get_history(
    user_id: UUID,
    conversation_id: UUID = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
) -> dict[str, Any]:
    events = QoraStateService(db).history(user_id=user_id, conversation_id=conversation_id)
    return {"user_id": str(user_id), "conversation_id": str(conversation_id), "events": [_event_payload(e) for e in events]}


@router.post("/state/{user_id}/rebuild")
def rebuild_state(
    user_id: UUID,
    conversation_id: UUID = Query(...),
    request_id: str | None = Header(default=None, alias="X-Request-ID"),
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
) -> dict[str, Any]:
    try:
        state = QoraStateService(db).rebuild_state(
            user_id=user_id,
            conversation_id=conversation_id,
            request_id=request_id or f"req_{uuid4().hex}",
        )
    except StateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StateVersionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _state_payload(state)
