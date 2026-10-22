from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.services.user_profile_service import UserProfileService


@dataclass(frozen=True)
class DashboardCardAction:
    label_key: str
    href: str
    enabled: bool = True


@dataclass(frozen=True)
class DashboardCard:
    id: str
    title_key: str
    summary_key: str
    status: str
    action: DashboardCardAction | None
    icon_key: str | None = None
    progress: int | None = None
    priority: str | None = None


@dataclass(frozen=True)
class DashboardActivation:
    is_activated: bool
    onboarding_progress: float
    initial_interaction_completed: bool
    registration_completed: bool
    first_tasks_received: bool


@dataclass(frozen=True)
class DashboardSnapshot:
    activation: DashboardActivation
    cards: list[DashboardCard]


class DashboardService:
    def __init__(self, profile_service: UserProfileService | None = None) -> None:
        self.profile_service = profile_service or UserProfileService()

    def get_dashboard_snapshot(self, db: Session, user_id: UUID) -> DashboardSnapshot:
        profile = self.profile_service.get_profile(db, user_id)

        progress = float(profile.onboarding_progress)
        progress_int = max(0, min(100, int(round(progress))))
        normalized_state = str(profile.last_state or "").strip().lower()

        initial_interaction_completed = progress >= 20.0
        registration_completed = progress >= 50.0
        first_tasks_received = progress >= 80.0
        is_activated = normalized_state == "join" or progress >= 100.0

        activation = DashboardActivation(
            is_activated=is_activated,
            onboarding_progress=progress,
            initial_interaction_completed=initial_interaction_completed,
            registration_completed=registration_completed,
            first_tasks_received=first_tasks_received,
        )

        overview_status = "complete" if is_activated else "in_progress"
        overview_summary = "activationOverviewActiveSummary" if is_activated else "activationOverviewPendingSummary"
        overview_action = (
            DashboardCardAction(label_key="goToChat", href="/agent", enabled=True)
            if is_activated
            else DashboardCardAction(label_key="openProfile", href="/profile", enabled=True)
        )

        cards = [
            DashboardCard(
                id="activation-overview",
                title_key="activationOverview",
                summary_key=overview_summary,
                status=overview_status,
                action=overview_action,
                icon_key="profile",
                progress=progress_int,
                priority="low" if is_activated else "high",
            ),
            DashboardCard(
                id="conversation-flow",
                title_key="conversationHub",
                summary_key="conversationHubSummary",
                status="idle",
                action=DashboardCardAction(label_key="openChat", href="/agent", enabled=True),
                icon_key="chat",
                priority="medium",
            ),
            DashboardCard(
                id="network-growth",
                title_key="networkGrowth",
                summary_key="networkGrowthSummary",
                status="idle",
                action=DashboardCardAction(label_key="openReferral", href="/referral", enabled=True),
                icon_key="referral",
                priority="low",
            ),
            DashboardCard(
                id="history-review",
                title_key="historyReview",
                summary_key="historyReviewSummary",
                status="idle",
                action=DashboardCardAction(label_key="openHistory", href="/history", enabled=True),
                icon_key="history",
                priority="low",
            ),
        ]

        return DashboardSnapshot(activation=activation, cards=cards)
