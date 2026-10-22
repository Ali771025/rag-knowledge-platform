from __future__ import annotations

from datetime import datetime, timezone
from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.models.invite import Invite
from app.models.referral import ReferralLink, ReferralProgressEvent
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    AdminLoginRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TelegramLoginRequest,
    TokenResponse,
)

router = APIRouter()


def _issue_token_pair(subject: str) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(subject=subject),
        refresh_token=create_refresh_token(subject=subject),
        token_type="bearer",
    )


def _to_utc_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _authenticate_email_password(*, db: Session, email: str, password: str) -> User:
    normalized_email = _normalize_email(email)
    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is None or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    return user


def _telegram_identity_email(telegram_user_id: int) -> str:
    return f"telegram-{telegram_user_id}@telegram.local"


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = _authenticate_email_password(db=db, email=payload.email, password=payload.password)
    return _issue_token_pair(str(user.id))


@router.post("/admin/login", response_model=TokenResponse)
def admin_login(payload: AdminLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = _authenticate_email_password(db=db, email=payload.email, password=payload.password)
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return _issue_token_pair(str(user.id))


@router.post("/telegram/login", response_model=TokenResponse)
def telegram_login(payload: TelegramLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    configured_secret = str(getattr(settings, "telegram_auth_secret", "")).strip()
    if not configured_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram authentication is not configured",
        )
    if payload.auth_secret != configured_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram authentication secret",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email = _telegram_identity_email(payload.telegram_user_id)
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        display_name_parts = [payload.first_name or "", payload.last_name or ""]
        display_name = " ".join(part.strip() for part in display_name_parts if part and part.strip())
        if not display_name:
            username = (payload.username or "").strip()
            display_name = f"@{username}" if username else f"telegram-{payload.telegram_user_id}"
        user = User(
            email=email,
            hashed_password=get_password_hash(token_urlsafe(32)),
            role="user",
            full_name=display_name[:255],
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    return _issue_token_pair(str(user.id))


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(payload: RefreshRequest) -> AccessTokenResponse:
    token_payload = verify_token(payload.refresh_token, expected_type="refresh")
    access_token = create_access_token(subject=str(token_payload["sub"]))
    return AccessTokenResponse(
        access_token=access_token,
        token_type="bearer",
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    normalized_email = _normalize_email(payload.email)
    existing_user = db.scalar(select(User).where(User.email == normalized_email))
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    invite = db.scalar(select(Invite).where(Invite.code == payload.invite_code))
    if invite is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invite code not found",
        )
    if not invite.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invite code is inactive",
        )
    if invite.is_used:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invite code has already been used",
        )
    expires_at = _to_utc_aware(invite.expires_at)
    if expires_at and expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invite code has expired",
        )

    user = User(
        email=normalized_email,
        hashed_password=get_password_hash(payload.password),
        role="user",
        is_active=True,
    )
    db.add(user)
    db.flush()

    invite.is_used = True
    invite.used_at = datetime.now(timezone.utc)
    invite.used_by_user_id = user.id
    db.add(invite)

    referral_link = db.scalar(select(ReferralLink).where(ReferralLink.invite_code == invite.code))
    if referral_link is not None and referral_link.latest_status == "created":
        now = datetime.now(timezone.utc)
        referral_link.latest_status = "invite_opened"
        referral_link.progress_percent = 20
        referral_link.updated_at = now
        db.add(referral_link)
        db.add(
            ReferralProgressEvent(
                referral_link_id=referral_link.id,
                status="invite_opened",
                title="Invited",
                occurred_at=now,
                metadata_json={"source": "invite_registration"},
            )
        )
    db.commit()
    return _issue_token_pair(str(user.id))
