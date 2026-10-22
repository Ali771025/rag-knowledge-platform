from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from app.qora.application.state_service import QoraStateService
from app.qora.infrastructure.persistence.models import UserInteractionEvent


class QoraEventService:
    """Explicit event boundary that delegates transactional writes to QoraStateService."""

    def __init__(self, state_service: QoraStateService) -> None:
        self.state_service = state_service

    def append(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        event_type: str,
        request_id: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        event_id: str | None = None,
        idempotency_key: str | None = None,
        occurred_at: datetime | None = None,
    ) -> UserInteractionEvent:
        return self.state_service.append_event(
            user_id=user_id,
            conversation_id=conversation_id,
            event_type=event_type,
            request_id=request_id,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata,
            event_id=event_id,
            idempotency_key=idempotency_key,
            occurred_at=occurred_at,
        )

    def history(self, *, user_id: UUID, conversation_id: UUID) -> list[UserInteractionEvent]:
        return self.state_service.history(user_id=user_id, conversation_id=conversation_id)

