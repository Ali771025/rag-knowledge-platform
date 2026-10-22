from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation


class ConversationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_message(
        self,
        *,
        session_id: UUID,
        role: str,
        message: str,
        user_id: UUID | None = None,
    ) -> Conversation:
        conversation = Conversation(
            session_id=session_id,
            user_id=user_id,
            role=role,
            message=message,
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def list_by_session(self, session_id: UUID) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .where(Conversation.session_id == session_id)
            .order_by(Conversation.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())
