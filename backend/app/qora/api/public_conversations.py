from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any, Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.qora.application.achievement_service import AchievementService
from app.qora.application.errors import DuplicateEventError, StateVersionConflictError
from app.qora.application.orchestrator import (
    ConversationOrchestrator,
    IdempotencyConflictError,
    RequestInProgressError,
)
from app.qora.application.state_service import QoraStateService
from app.qora.domain.orchestration_contracts import InteractionEventInput, PageContext
from app.qora.domain.enums import Section
from app.qora.infrastructure.persistence.models import AgentUserState, ConversationTurn
from app.qora.integrations.rag.client import ExistingRAGAdapter, NullRAGClient


router = APIRouter(prefix="/agent/conversations", tags=["qora-agent"])


class PublicEventType(StrEnum):
    CTA_CLICKED = "CTA_CLICKED"
    CTA_REJECTED = "CTA_REJECTED"
    PRODUCT_ALTERNATIVE_VIEWED = "PRODUCT_ALTERNATIVE_VIEWED"
    QUALIFICATION_ANSWERED = "QUALIFICATION_ANSWERED"
    SOURCE_OPENED = "SOURCE_OPENED"
    ACHIEVEMENT_STARTED = "ACHIEVEMENT_STARTED"
    PAGE_VISIT = "PAGE_VISIT"
    DOCUMENT_VISIT = "DOCUMENT_VISIT"
    DWELL_TIME = "DWELL_TIME"
    MODULE_OPEN = "MODULE_OPEN"
    COMPARISON = "COMPARISON"
    PROGRESS_INTERACTION = "PROGRESS_INTERACTION"


class ConversationCreateRequest(BaseModel):
    conversation_id: UUID | None = None


class ConversationCreateResponse(BaseModel):
    conversation_id: UUID
    created: bool
    progress: dict[str, Any]


class PublicPageContext(BaseModel):
    page: str = Field(default="agent", max_length=128)
    section: Section | None = None
    product_id: str | None = Field(default=None, max_length=64)
    language: str = Field(default="fa", min_length=2, max_length=10)


class PublicInteractionEvent(BaseModel):
    event_id: str = Field(min_length=1, max_length=128)
    event_type: PublicEventType
    entity_type: str | None = Field(default=None, max_length=64)
    entity_id: str | None = Field(default=None, max_length=128)
    metadata: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("metadata")
    @classmethod
    def validate_metadata_size(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(json.dumps(value, ensure_ascii=False, default=str).encode("utf-8")) > 16_384:
            raise ValueError("event metadata exceeds 16 KiB")
        return value

    @field_validator("occurred_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        normalized = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        if normalized > now + timedelta(minutes=5):
            raise ValueError("event timestamp is too far in the future")
        if normalized < now - timedelta(days=30):
            raise ValueError("event timestamp is older than the accepted window")
        return normalized


class ConversationMessageRequest(BaseModel):
    request_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")
    message: str = Field(min_length=1, max_length=10_000)
    page_context: PublicPageContext = Field(default_factory=PublicPageContext)
    interaction_events: list[PublicInteractionEvent] = Field(default_factory=list, max_length=50)


class FeedbackRequest(BaseModel):
    request_id: str = Field(min_length=1, max_length=128)
    feedback: str = Field(pattern=r"^(ACCEPTED|REJECTED|HELPFUL|NOT_HELPFUL)$")
    entity_type: str | None = Field(default=None, max_length=64)
    entity_id: str | None = Field(default=None, max_length=128)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EventBatchRequest(BaseModel):
    request_id: str = Field(min_length=1, max_length=128)
    events: list[PublicInteractionEvent] = Field(min_length=1, max_length=50)


class PublicAgentResponse(BaseModel):
    request_id: str
    conversation_id: str
    message: str
    response_type: str
    ui: dict[str, Any]
    primary_cta: dict[str, Any] | None = None
    secondary_cta: dict[str, Any] | None = None
    progress: dict[str, Any]
    sources: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_best_action: dict[str, Any] | None = None
    can_continue: bool = True

    model_config = ConfigDict(extra="forbid")


DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _active_user(user: User) -> None:
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")


def _owned_state(db: Session, user: User, conversation_id: UUID) -> AgentUserState:
    state_row = db.scalar(
        select(AgentUserState).where(
            AgentUserState.user_id == user.id,
            AgentUserState.conversation_id == conversation_id,
        )
    )
    if state_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return state_row


def _rag_client():
    try:
        return ExistingRAGAdapter()
    except Exception:
        return NullRAGClient()


def _public_payload(payload: dict[str, Any]) -> PublicAgentResponse:
    progress = payload.get("progress") or {}
    return PublicAgentResponse(
        request_id=payload["request_id"],
        conversation_id=payload["conversation_id"],
        message=payload["message"],
        response_type=payload.get("response_type", "GUIDANCE"),
        ui=payload.get("ui") or {"type": "TEXT", "cards": [], "options": []},
        primary_cta=payload.get("primary_cta"),
        secondary_cta=payload.get("secondary_cta"),
        progress={
            "current_stage": payload.get("stage"),
            "step": progress.get("current_step", 1),
            "total_steps": progress.get("total_steps", 5),
        },
        sources=payload.get("sources") or [],
        warnings=payload.get("warnings") or [],
        next_best_action=payload.get("next_best_action"),
        can_continue=payload.get("can_continue", True),
    )


@router.post("", response_model=ConversationCreateResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    body: ConversationCreateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> ConversationCreateResponse:
    _active_user(current_user)
    conversation_id = body.conversation_id or uuid4()
    existing = db.scalar(
        select(AgentUserState).where(AgentUserState.conversation_id == conversation_id)
    )
    if existing is not None and existing.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conversation id is unavailable")
    created = existing is None
    state_row = QoraStateService(db).get_or_create_state(
        user_id=current_user.id,
        conversation_id=conversation_id,
        request_id=f"create:{conversation_id}",
    )
    return ConversationCreateResponse(
        conversation_id=conversation_id,
        created=created,
        progress={"current_stage": state_row.conversation_stage, "step": 1, "total_steps": 5},
    )


@router.get("/{conversation_id}")
def get_conversation(conversation_id: UUID, db: DbSession, current_user: CurrentUser) -> dict[str, Any]:
    _active_user(current_user)
    state_row = _owned_state(db, current_user, conversation_id)
    turns = list(
        db.scalars(
            select(ConversationTurn)
            .where(
                ConversationTurn.user_id == current_user.id,
                ConversationTurn.conversation_id == conversation_id,
            )
            .order_by(ConversationTurn.created_at)
        ).all()
    )
    return {
        "conversation_id": str(conversation_id),
        "progress": {"current_stage": state_row.conversation_stage},
        "messages": [
            {
                "id": str(row.id),
                "role": row.role,
                "message": row.message,
                "created_at": row.created_at,
            }
            for row in turns
        ],
        "updated_at": state_row.updated_at,
    }


@router.post("/{conversation_id}/messages", response_model=PublicAgentResponse)
def post_message(
    conversation_id: UUID,
    body: ConversationMessageRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> PublicAgentResponse:
    _active_user(current_user)
    existing = db.scalar(select(AgentUserState).where(AgentUserState.conversation_id == conversation_id))
    if existing is not None and existing.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    page = PageContext(
        page=body.page_context.page,
        explicit_section=body.page_context.section,
        explicit_product_id=body.page_context.product_id,
        language=body.page_context.language,
    )
    events = [
        InteractionEventInput(
            event_type=item.event_type.value,
            entity_type=item.entity_type,
            entity_id=item.entity_id,
            metadata={**item.metadata, "occurred_at": item.occurred_at.isoformat()},
            idempotency_key=item.idempotency_key or item.event_id,
        )
        for item in body.interaction_events
    ]
    try:
        payload = ConversationOrchestrator(
            state_service=QoraStateService(db),
            rag_client=_rag_client(),
        ).process_turn(
            request_id=body.request_id,
            user_id=current_user.id,
            conversation_id=conversation_id,
            message=body.message,
            interaction_events=events,
            page_context=page,
        )
    except (IdempotencyConflictError, RequestInProgressError, StateVersionConflictError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _public_payload(payload)


@router.post("/{conversation_id}/events", status_code=status.HTTP_202_ACCEPTED)
def post_events(
    conversation_id: UUID,
    body: EventBatchRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, Any]:
    _active_user(current_user)
    _owned_state(db, current_user, conversation_id)
    service = QoraStateService(db)
    accepted = 0
    duplicates = 0
    for item in body.events:
        try:
            service.append_event(
                user_id=current_user.id,
                conversation_id=conversation_id,
                event_type=item.event_type.value,
                entity_type=item.entity_type,
                entity_id=item.entity_id,
                metadata=item.metadata,
                event_id=item.event_id,
                idempotency_key=item.idempotency_key or item.event_id,
                occurred_at=item.occurred_at,
                request_id=body.request_id,
            )
            accepted += 1
        except DuplicateEventError:
            duplicates += 1
    return {"accepted": accepted, "duplicates": duplicates}


@router.post("/{conversation_id}/feedback", status_code=status.HTTP_202_ACCEPTED)
def post_feedback(
    conversation_id: UUID,
    body: FeedbackRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, bool]:
    _active_user(current_user)
    _owned_state(db, current_user, conversation_id)
    QoraStateService(db).append_event(
        user_id=current_user.id,
        conversation_id=conversation_id,
        event_type=f"FEEDBACK_{body.feedback}",
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        metadata=body.metadata,
        request_id=body.request_id,
        idempotency_key=f"feedback:{conversation_id}:{body.request_id}",
    )
    return {"accepted": True}


@router.get("/{conversation_id}/progress")
def get_progress(conversation_id: UUID, db: DbSession, current_user: CurrentUser) -> dict[str, Any]:
    _active_user(current_user)
    state_row = _owned_state(db, current_user, conversation_id)
    achievement_service = AchievementService(db)
    decision = achievement_service.get_next_best_achievement(state_row)
    level_card = achievement_service.level_card(
        state_row, decision.context if decision.eligible else None
    )
    return {
        "conversation_id": str(conversation_id),
        "current_stage": state_row.conversation_stage,
        "level_card": level_card.model_dump(mode="json"),
        "achievement": decision.context.model_dump(mode="json") if decision.eligible and decision.context else None,
    }


@router.post("/{conversation_id}/achievements/{achievement_id}/start", status_code=status.HTTP_202_ACCEPTED)
def start_achievement(
    conversation_id: UUID,
    achievement_id: UUID,
    request_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, Any]:
    _active_user(current_user)
    state_row = _owned_state(db, current_user, conversation_id)
    service = AchievementService(db)
    decision = service.get_next_best_achievement(state_row)
    if not decision.eligible or decision.context is None or decision.context.achievement_id != str(achievement_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Achievement is not currently eligible")
    row = service.start_achievement(
        user_id=current_user.id,
        achievement_id=achievement_id,
        conversation_id=conversation_id,
        request_id=request_id,
        idempotency_key=f"{conversation_id}:{request_id}",
    )
    return {"achievement_id": str(row.achievement_id), "status": row.status}
