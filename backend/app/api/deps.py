from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.redis_client import get_redis_client
from app.core.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_db_session(db: Annotated[Session, Depends(get_db)]) -> Session:
    return db


def get_redis_dependency():
    return get_redis_client()


def get_token_payload(token: Annotated[str | None, Depends(oauth2_scheme)]) -> dict[str, Any] | None:
    if not token:
        return None
    try:
        return decode_token(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
