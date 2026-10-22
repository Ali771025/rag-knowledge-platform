from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ChatRequest(BaseModel):
    session_id: UUID
    user_id: UUID
    message: str


class ChatResponse(BaseModel):
    conversation_id: UUID
    session_id: UUID
    role: str
    message: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
