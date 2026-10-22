from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

# Prefer PBKDF2 for new passwords and keep bcrypt verification compatibility.
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

SECRET_KEY = str(getattr(settings, "jwt_secret_key", os.getenv("JWT_SECRET_KEY", "change-me-in-production")))
ALGORITHM = str(getattr(settings, "jwt_algorithm", os.getenv("JWT_ALGORITHM", "HS256")))
EXPIRATION: dict[str, int] = {
    "access_minutes": int(
        getattr(settings, "access_token_expire_minutes", os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    ),
    "refresh_days": int(getattr(settings, "refresh_token_expire_days", os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))),
}


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password, scheme="pbkdf2_sha256")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError:
        # Some bcrypt backends can raise ValueError unexpectedly; fallback to direct check.
        if hashed_password.startswith("$2"):
            try:
                import bcrypt

                return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
            except Exception:
                return False
        return False


def _build_token(
    *,
    subject: str,
    token_type: str,
    default_expiry: timedelta,
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    expire_at = datetime.now(timezone.utc) + (expires_delta if expires_delta is not None else default_expiry)
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire_at,
        "iat": datetime.now(timezone.utc),
        "type": token_type,
    }
    if additional_claims:
        payload.update(additional_claims)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    return _build_token(
        subject=subject,
        token_type="access",
        default_expiry=timedelta(minutes=EXPIRATION["access_minutes"]),
        expires_delta=expires_delta,
        additional_claims=additional_claims,
    )


def create_refresh_token(
    subject: str,
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    return _build_token(
        subject=subject,
        token_type="refresh",
        default_expiry=timedelta(days=EXPIRATION["refresh_days"]),
        expires_delta=expires_delta,
        additional_claims=additional_claims,
    )


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def verify_token(token: str, expected_type: str | None = None) -> dict[str, Any]:
    try:
        payload = decode_token(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject is missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_type = payload.get("type")
    if expected_type and token_type != expected_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Expected {expected_type} token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(token, expected_type="access")
    subject = payload.get("sub")
    try:
        user_id = UUID(str(subject))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(required_role: str):
    def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role != required_role:
            raise HTTPException(status_code=403, detail="Access denied")
        return user

    return role_checker


__all__ = [
    "ALGORITHM",
    "EXPIRATION",
    "JWTError",
    "SECRET_KEY",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "get_current_user",
    "get_password_hash",
    "require_role",
    "verify_token",
    "verify_password",
]
