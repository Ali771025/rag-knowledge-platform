"""User profile and onboarding milestone ORM models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SqlEnum, Float, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class KnowledgeLevel(str, Enum):
    """Supported user knowledge levels for onboarding personalization."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class PersonalityType(str, Enum):
    """Supported user personality archetypes."""

    ANALYTICAL = "analytical"
    PRACTICAL = "practical"
    CREATIVE = "creative"
    SOCIAL = "social"


class ResponseStyle(str, Enum):
    """Supported response style preferences."""

    CONCISE = "concise"
    DETAILED = "detailed"
    BALANCED = "balanced"


def _enum_values(enum_cls: type[Enum]) -> list[str]:
    return [str(member.value) for member in enum_cls]


class UserProfile(Base):
    """Stores onboarding-oriented profile attributes for a user."""

    __tablename__ = "user_profiles"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(nullable=False, unique=True, index=True)
    knowledge_level: Mapped[KnowledgeLevel] = mapped_column(
        SqlEnum(
            KnowledgeLevel,
            name="knowledge_level",
            native_enum=True,
            values_callable=_enum_values,
        ),
        nullable=False,
        default=KnowledgeLevel.BEGINNER,
    )
    personality_type: Mapped[PersonalityType | None] = mapped_column(
        SqlEnum(
            PersonalityType,
            name="personality_type",
            native_enum=True,
            values_callable=_enum_values,
        ),
        nullable=True,
    )
    preferred_response_style: Mapped[ResponseStyle] = mapped_column(
        SqlEnum(
            ResponseStyle,
            name="response_style",
            native_enum=True,
            values_callable=_enum_values,
        ),
        nullable=False,
        default=ResponseStyle.CONCISE,
    )
    onboarding_progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_state: Mapped[str] = mapped_column(String(100), nullable=False, default="start")
    completed_milestones: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    engagement_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    total_messages: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_sessions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class OnboardingMilestone(Base):
    """Represents a completed onboarding milestone for a user."""

    __tablename__ = "onboarding_milestones"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    milestone_name: Mapped[str] = mapped_column(String(255), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)
