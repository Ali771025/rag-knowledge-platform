"""Repository methods for user profiles and onboarding milestones."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user_profile import (
    KnowledgeLevel,
    OnboardingMilestone,
    ResponseStyle,
    UserProfile,
)


class UserProfileRepository:
    """Persistence-only operations for user profile and milestone records."""

    def get_by_user_id(self, db: Session, user_id: UUID) -> UserProfile | None:
        """Return the user profile by `user_id`, or `None` when missing."""
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        return db.scalar(stmt)

    def create_profile(self, db: Session, profile_data: dict[str, object]) -> UserProfile:
        """Create and persist a user profile from a plain data mapping."""
        profile = UserProfile(**profile_data)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    def update_profile(
        self,
        db: Session,
        profile: UserProfile,
        update_data: dict[str, object],
    ) -> UserProfile:
        """Apply non-`None` updates to a profile and persist the result."""
        for field, value in update_data.items():
            if value is not None and hasattr(profile, field):
                setattr(profile, field, value)

        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    def create_if_missing(
        self,
        db: Session,
        user_id: UUID,
        defaults: dict[str, object] | None = None,
    ) -> UserProfile:
        """Fetch existing profile or create a default one for `user_id`."""
        existing = self.get_by_user_id(db, user_id)
        if existing is not None:
            return existing

        payload: dict[str, object] = {
            "user_id": user_id,
            "knowledge_level": KnowledgeLevel.BEGINNER,
            "preferred_response_style": ResponseStyle.CONCISE,
            "onboarding_progress": 0.0,
            "last_state": "start",
            "completed_milestones": [],
            "engagement_score": 50.0,
            "total_messages": 0,
            "total_sessions": 0,
            "language": "en",
            "timezone": "UTC",
        }
        if defaults:
            payload.update(defaults)
        return self.create_profile(db, payload)

    def add_milestone(
        self,
        db: Session,
        user_id: UUID,
        milestone_name: str,
        metadata: dict[str, object] | None = None,
    ) -> OnboardingMilestone:
        """Insert a completed milestone entry for a user."""
        milestone = OnboardingMilestone(
            user_id=user_id,
            milestone_name=milestone_name,
            metadata_json=metadata or {},
        )
        db.add(milestone)
        db.commit()
        db.refresh(milestone)
        return milestone

    def list_milestones(self, db: Session, user_id: UUID) -> list[OnboardingMilestone]:
        """Return all milestones for `user_id` ordered by completion time."""
        stmt = (
            select(OnboardingMilestone)
            .where(OnboardingMilestone.user_id == user_id)
            .order_by(OnboardingMilestone.completed_at.asc())
        )
        return list(db.scalars(stmt).all())

    def increment_message_count(self, db: Session, profile: UserProfile) -> UserProfile:
        """Increase message counter by one and persist."""
        profile.total_messages += 1
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    def increment_session_count(self, db: Session, profile: UserProfile) -> UserProfile:
        """Increase session counter by one and persist."""
        profile.total_sessions += 1
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    def touch_last_active(self, db: Session, profile: UserProfile) -> UserProfile:
        """Set `last_active_at` to current UTC time and persist."""
        profile.last_active_at = datetime.now(timezone.utc)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile
