"""Pydantic schemas for user onboarding profile flows."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.user_profile import KnowledgeLevel, PersonalityType, ResponseStyle


class UserProfileBase(BaseModel):
    """Shared user profile fields for create/update operations."""

    knowledge_level: KnowledgeLevel | None = Field(
        default=None,
        description="Declared knowledge level used for personalization.",
    )
    personality_type: PersonalityType | None = Field(
        default=None,
        description="Optional personality archetype inferred or selected by the user.",
    )
    preferred_response_style: ResponseStyle | None = Field(
        default=None,
        description="Preferred assistant response style.",
    )
    onboarding_progress: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Onboarding completion percentage between 0 and 100.",
    )
    last_state: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Most recent onboarding state key.",
    )
    completed_milestones: list[str] | None = Field(
        default=None,
        description="Ordered list of completed onboarding milestone names.",
    )
    engagement_score: float | None = Field(
        default=None,
        description="Current engagement score used for pacing and follow-up.",
    )
    language: str | None = Field(
        default=None,
        min_length=2,
        max_length=16,
        description="Language code or locale preference, for example 'en' or 'en-US'.",
    )
    timezone: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        description="IANA timezone string or equivalent user timezone preference.",
    )

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class UserProfileCreate(UserProfileBase):
    """Payload for creating a user onboarding profile."""

    user_id: UUID = Field(description="User identifier associated with the profile.")


class UserProfileUpdate(UserProfileBase):
    """Payload for partially updating a user onboarding profile."""

    total_messages: int | None = Field(
        default=None,
        ge=0,
        description="Optional override for cumulative message count.",
    )
    total_sessions: int | None = Field(
        default=None,
        ge=0,
        description="Optional override for cumulative session count.",
    )
    last_active_at: datetime | None = Field(
        default=None,
        description="Last known activity timestamp.",
    )


class UserProfileResponse(BaseModel):
    """Response schema representing a persisted user profile."""

    id: UUID
    user_id: UUID
    knowledge_level: KnowledgeLevel
    personality_type: PersonalityType | None = None
    preferred_response_style: ResponseStyle
    onboarding_progress: float = Field(ge=0.0, le=100.0)
    last_state: str
    completed_milestones: list[str] = Field(default_factory=list)
    engagement_score: float
    total_messages: int
    total_sessions: int
    last_active_at: datetime | None = None
    language: str
    timezone: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class AssessmentSubmission(BaseModel):
    """Payload submitted after onboarding assessment."""

    user_id: UUID = Field(description="User identifier for this assessment submission.")
    knowledge_level: KnowledgeLevel | None = Field(
        default=None,
        description="Optionally declared knowledge level from assessment.",
    )
    personality_type: PersonalityType | None = Field(
        default=None,
        description="Optional personality classification outcome.",
    )
    preferred_response_style: ResponseStyle | None = Field(
        default=None,
        description="Optional preferred response style inferred from answers.",
    )
    responses: dict[str, Any] = Field(
        default_factory=dict,
        description="Raw assessment responses keyed by question identifiers.",
    )

    model_config = ConfigDict(extra="forbid")


class StateUpdateRequest(BaseModel):
    """Payload to update onboarding state and progress."""

    user_id: UUID = Field(description="User identifier whose onboarding state changes.")
    last_state: str = Field(
        min_length=1,
        max_length=100,
        description="New onboarding state key.",
    )
    onboarding_progress: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Optional updated onboarding completion percentage.",
    )

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class MilestoneResponse(BaseModel):
    """Response schema for an onboarding milestone entry."""

    id: UUID
    user_id: UUID
    milestone_name: str
    completed_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class AdaptiveParametersResponse(BaseModel):
    """Response schema with adaptive parameters derived from profile state."""

    user_id: UUID
    knowledge_level: KnowledgeLevel
    personality_type: PersonalityType | None = None
    preferred_response_style: ResponseStyle
    onboarding_progress: float = Field(ge=0.0, le=100.0)
    engagement_score: float
    recommended_state: str | None = Field(
        default=None,
        description="Optional state hint from adaptive planning layer.",
    )
    explanation_depth: str = Field(description="Target conceptual detail level for responses.")
    include_examples: bool = Field(description="Whether examples should be included by default.")
    include_step_by_step: bool = Field(description="Whether step-by-step structure should be included.")
    max_tokens: int = Field(description="Recommended max response token budget.")
    tone: str = Field(description="Recommended response tone.")
    progressive_disclosure_level: int = Field(
        description="How strongly to gate complexity behind incremental explanations."
    )

    model_config = ConfigDict(extra="forbid")
