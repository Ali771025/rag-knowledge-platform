"""API endpoints for user onboarding profile management."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.user_profile import (
    AdaptiveParametersResponse,
    AssessmentSubmission,
    MilestoneResponse,
    StateUpdateRequest,
    UserProfileResponse,
    UserProfileUpdate,
)
from app.services.user_profile_service import (
    InvalidOnboardingStateError,
    InvalidProfileUpdateError,
    UserProfileDomainError,
    UserProfileNotFoundError,
    UserProfileService,
)

router = APIRouter(prefix="/users", tags=["user-onboarding"])


def _service() -> UserProfileService:
    return UserProfileService()


@router.get("/profile", response_model=UserProfileResponse)
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    service = _service()
    try:
        profile = service.get_profile(db, current_user.id)
    except UserProfileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ProgrammingError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Profile storage is not initialized. Apply database migrations.",
        ) from exc
    return UserProfileResponse.model_validate(profile, from_attributes=True)


@router.patch("/profile", response_model=UserProfileResponse)
def patch_profile(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    service = _service()
    updates = payload.model_dump(exclude_unset=True)
    try:
        profile = service.update_profile(db, current_user.id, updates)
    except UserProfileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidProfileUpdateError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except UserProfileDomainError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ProgrammingError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Profile storage is not initialized. Apply database migrations.",
        ) from exc
    return UserProfileResponse.model_validate(profile, from_attributes=True)


@router.post("/assessment", response_model=UserProfileResponse)
def submit_assessment(
    payload: AssessmentSubmission,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    service = _service()
    if payload.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assessment user_id must match the authenticated user",
        )

    answers: dict[str, Any] = dict(payload.responses)
    if payload.knowledge_level is not None:
        answers["knowledge_level"] = payload.knowledge_level
    if payload.personality_type is not None:
        answers["personality_type"] = payload.personality_type
    if payload.preferred_response_style is not None:
        answers["preferred_response_style"] = payload.preferred_response_style

    try:
        profile = service.submit_assessment(db, current_user.id, answers)
    except InvalidProfileUpdateError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except UserProfileDomainError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ProgrammingError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Profile storage is not initialized. Apply database migrations.",
        ) from exc
    return UserProfileResponse.model_validate(profile, from_attributes=True)


@router.post("/state/update", response_model=UserProfileResponse)
def update_state(
    payload: StateUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    service = _service()
    if payload.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State update user_id must match the authenticated user",
        )

    try:
        profile = service.update_state(db, current_user.id, payload.last_state)
    except InvalidOnboardingStateError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except UserProfileDomainError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ProgrammingError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Profile storage is not initialized. Apply database migrations.",
        ) from exc
    return UserProfileResponse.model_validate(profile, from_attributes=True)


@router.get("/adaptive-parameters", response_model=AdaptiveParametersResponse)
def get_adaptive_parameters(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AdaptiveParametersResponse:
    service = _service()
    try:
        result = service.get_adaptive_parameters(db, current_user.id)
    except UserProfileDomainError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ProgrammingError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Profile storage is not initialized. Apply database migrations.",
        ) from exc
    return AdaptiveParametersResponse.model_validate(result)


@router.get("/milestones", response_model=list[MilestoneResponse])
def list_milestones(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MilestoneResponse]:
    service = _service()
    try:
        rows = service.list_milestones(db, current_user.id)
    except UserProfileDomainError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ProgrammingError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Profile storage is not initialized. Apply database migrations.",
        ) from exc
    return [MilestoneResponse.model_validate(row) for row in rows]
