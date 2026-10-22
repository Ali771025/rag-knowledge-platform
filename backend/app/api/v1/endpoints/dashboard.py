from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.dashboard import (
    DashboardActivationResponse,
    DashboardCardActionResponse,
    DashboardCardResponse,
    DashboardCardsResponse,
)
from app.services.dashboard_service import DashboardService
from app.services.user_profile_service import UserProfileDomainError

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _service() -> DashboardService:
    return DashboardService()


@router.get("/cards", response_model=DashboardCardsResponse)
def get_dashboard_cards(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardCardsResponse:
    service = _service()
    try:
        snapshot = service.get_dashboard_snapshot(db, current_user.id)
    except UserProfileDomainError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ProgrammingError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dashboard storage is not initialized. Apply database migrations.",
        ) from exc

    return DashboardCardsResponse(
        activation=DashboardActivationResponse(
            is_activated=snapshot.activation.is_activated,
            onboarding_progress=snapshot.activation.onboarding_progress,
            initial_interaction_completed=snapshot.activation.initial_interaction_completed,
            registration_completed=snapshot.activation.registration_completed,
            first_tasks_received=snapshot.activation.first_tasks_received,
        ),
        cards=[
            DashboardCardResponse(
                id=card.id,
                title_key=card.title_key,
                summary_key=card.summary_key,
                status=card.status,
                action=(
                    DashboardCardActionResponse(
                        label_key=card.action.label_key,
                        href=card.action.href,
                        enabled=card.action.enabled,
                    )
                    if card.action is not None
                    else None
                ),
                icon_key=card.icon_key,
                progress=card.progress,
                priority=card.priority,
            )
            for card in snapshot.cards
        ],
    )
