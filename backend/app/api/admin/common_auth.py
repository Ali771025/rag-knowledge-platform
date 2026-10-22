from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, get_token_payload
from app.models.user import User


async def require_admin_token(
    token_payload: Annotated[dict[str, Any] | None, Depends(get_token_payload)],
    db: Annotated[Session, Depends(get_db_session)],
) -> User:
    if token_payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    subject = token_payload.get("sub")
    try:
        user_id = UUID(str(subject))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject") from exc

    user = db.scalar(select(User).where(User.id == user_id))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authenticated user not found")
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
