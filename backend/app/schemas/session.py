from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SessionStartRequest(BaseModel):
    user_id: UUID
    title: str | None = None
    initial_state: dict[str, Any] = Field(default_factory=dict)


class SessionState(BaseModel):
    session_id: UUID
    state: dict[str, Any] = Field(default_factory=dict)


class SessionStartResponse(BaseModel):
    session_id: UUID
    user_id: UUID
    title: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
