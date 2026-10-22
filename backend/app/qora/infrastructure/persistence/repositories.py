from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import Select, select, update
from sqlalchemy.orm import Session

from app.qora.infrastructure.persistence.models import (
    AgentUserState,
    ConversationTurn,
    DetectedSignal,
    PersonaAssessment,
    RecommendationDecision,
    UserInteractionEvent,
)


class StateRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def load(self, *, user_id: UUID, conversation_id: UUID) -> AgentUserState | None:
        return self.session.scalar(
            select(AgentUserState).where(
                AgentUserState.user_id == user_id,
                AgentUserState.conversation_id == conversation_id,
            )
        )

    def latest_for_user(self, user_id: UUID) -> AgentUserState | None:
        return self.session.scalar(
            select(AgentUserState)
            .where(AgentUserState.user_id == user_id)
            .order_by(AgentUserState.updated_at.desc())
            .limit(1)
        )

    def create(self, state: AgentUserState) -> AgentUserState:
        self.session.add(state)
        self.session.flush()
        return state

    def compare_and_swap(
        self,
        *,
        state_id: UUID,
        expected_version: int,
        values: dict[str, Any],
    ) -> bool:
        statement = (
            update(AgentUserState)
            .where(AgentUserState.id == state_id, AgentUserState.version == expected_version)
            .values(**values, version=expected_version + 1, updated_at=datetime.now(timezone.utc))
        )
        result = self.session.execute(statement)
        return bool(result.rowcount == 1)

    def refresh(self, state: AgentUserState) -> AgentUserState:
        self.session.expire(state)
        self.session.refresh(state)
        return state


class SignalRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def append(self, signal: DetectedSignal) -> DetectedSignal:
        self.session.add(signal)
        self.session.flush()
        return signal

    def rolling(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        turn_limit: int,
        now: datetime | None = None,
    ) -> list[DetectedSignal]:
        effective_now = now or datetime.now(timezone.utc)
        recent_turn_ids = (
            select(ConversationTurn.id)
            .where(
                ConversationTurn.user_id == user_id,
                ConversationTurn.conversation_id == conversation_id,
            )
            .order_by(ConversationTurn.created_at.desc())
            .limit(turn_limit)
        )
        statement = (
            select(DetectedSignal)
            .where(
                DetectedSignal.user_id == user_id,
                DetectedSignal.conversation_id == conversation_id,
                (DetectedSignal.expires_at.is_(None) | (DetectedSignal.expires_at > effective_now)),
                (DetectedSignal.turn_id.is_(None) | DetectedSignal.turn_id.in_(recent_turn_ids)),
            )
            .order_by(DetectedSignal.detected_at.asc())
        )
        return list(self.session.scalars(statement).all())

    def cumulative(
        self,
        *,
        user_id: UUID,
        behavioral_days: int | None = None,
        include_expired: bool = False,
        now: datetime | None = None,
    ) -> list[DetectedSignal]:
        effective_now = now or datetime.now(timezone.utc)
        statement: Select[tuple[DetectedSignal]] = select(DetectedSignal).where(DetectedSignal.user_id == user_id)
        if behavioral_days is not None:
            statement = statement.where(DetectedSignal.detected_at >= effective_now - timedelta(days=behavioral_days))
        if not include_expired:
            statement = statement.where(
                DetectedSignal.expires_at.is_(None) | (DetectedSignal.expires_at > effective_now)
            )
        return list(self.session.scalars(statement.order_by(DetectedSignal.detected_at.asc())).all())


class EventRepository:
    """Append-only event repository; intentionally exposes no update or delete method."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def append(self, event: UserInteractionEvent) -> UserInteractionEvent:
        self.session.add(event)
        self.session.flush()
        return event

    def by_idempotency_key(self, *, user_id: UUID, key: str) -> UserInteractionEvent | None:
        return self.session.scalar(
            select(UserInteractionEvent).where(
                UserInteractionEvent.user_id == user_id,
                UserInteractionEvent.idempotency_key == key,
            )
        )

    def history(self, *, user_id: UUID, conversation_id: UUID) -> list[UserInteractionEvent]:
        return list(
            self.session.scalars(
                select(UserInteractionEvent)
                .where(
                    UserInteractionEvent.user_id == user_id,
                    UserInteractionEvent.conversation_id == conversation_id,
                )
                .order_by(UserInteractionEvent.occurred_at.asc(), UserInteractionEvent.id.asc())
            ).all()
        )


class TurnRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def append(self, turn: ConversationTurn) -> ConversationTurn:
        self.session.add(turn)
        self.session.flush()
        return turn


class AssessmentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def append(self, assessment: PersonaAssessment) -> PersonaAssessment:
        self.session.add(assessment)
        self.session.flush()
        return assessment


class RecommendationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def append(self, decision: RecommendationDecision) -> RecommendationDecision:
        self.session.add(decision)
        self.session.flush()
        return decision

