from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.services.session_service import SessionService
from app.services.user_service import UserService

router = APIRouter()


class SessionStartApiRequest(BaseModel):
    user_id: UUID
    title: str | None = None


class SessionStartApiResponse(BaseModel):
    session_id: UUID
    state: str


@router.post("/start", response_model=SessionStartApiResponse, status_code=status.HTTP_201_CREATED)
def start_session(
    payload: SessionStartApiRequest,
    db: Session = Depends(get_db),
) -> SessionStartApiResponse:
    user_service = UserService(UserRepository(db))
    if user_service.get_user(payload.user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    session_service = SessionService(SessionRepository(db))
    session_obj = session_service.create_session(
        user_id=payload.user_id,
        title=payload.title,
        initial_state={"state": "start"},
    )

    state_value = str((session_obj.state or {}).get("state", "start"))
    return SessionStartApiResponse(session_id=session_obj.id, state=state_value)
