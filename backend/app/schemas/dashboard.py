from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


DashboardCardStatus = Literal["idle", "in_progress", "complete", "blocked"]
DashboardCardPriority = Literal["low", "medium", "high"]
DashboardCardTitleKey = Literal["activationOverview", "conversationHub", "networkGrowth", "historyReview"]
DashboardCardSummaryKey = Literal[
    "activationOverviewActiveSummary",
    "activationOverviewPendingSummary",
    "conversationHubSummary",
    "networkGrowthSummary",
    "historyReviewSummary",
]
DashboardCardActionLabelKey = Literal["goToChat", "openProfile", "openChat", "openReferral", "openHistory"]
DashboardCardIconKey = Literal["chat", "profile", "referral", "history"]


class DashboardCardActionResponse(BaseModel):
    label_key: DashboardCardActionLabelKey
    href: str = Field(min_length=1, max_length=255)
    enabled: bool = True

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DashboardCardResponse(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    title_key: DashboardCardTitleKey
    summary_key: DashboardCardSummaryKey
    status: DashboardCardStatus
    action: DashboardCardActionResponse | None = None
    icon_key: DashboardCardIconKey | None = None
    progress: int | None = Field(default=None, ge=0, le=100)
    priority: DashboardCardPriority | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DashboardActivationResponse(BaseModel):
    is_activated: bool
    onboarding_progress: float = Field(ge=0.0, le=100.0)
    initial_interaction_completed: bool
    registration_completed: bool
    first_tasks_received: bool

    model_config = ConfigDict(extra="forbid")


class DashboardCardsResponse(BaseModel):
    activation: DashboardActivationResponse
    cards: list[DashboardCardResponse] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")
