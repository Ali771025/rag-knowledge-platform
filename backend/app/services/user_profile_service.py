"""Orchestration layer for user profile and onboarding domain behaviors."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user_profile import KnowledgeLevel, PersonalityType, ResponseStyle, UserProfile
from app.repositories.user_profile_repository import UserProfileRepository
from app.services.adaptive_engine import AdaptiveEngine
from app.services.engagement_service import EngagementService
from app.services.knowledge_detector import KnowledgeDetector
from app.services.onboarding_tracker import OnboardingTracker

logger = logging.getLogger(__name__)


class UserProfileDomainError(ValueError):
    """Base exception for user profile domain orchestration errors."""


class UserProfileNotFoundError(UserProfileDomainError):
    """Raised when a required user profile does not exist."""


class InvalidOnboardingStateError(UserProfileDomainError):
    """Raised when onboarding state is unsupported."""


class InvalidProfileUpdateError(UserProfileDomainError):
    """Raised when profile update payload includes unsupported values."""


class UserProfileService:
    """Centralizes profile orchestration across repository and domain services."""

    _PATCH_ALLOWED_FIELDS: set[str] = {
        "knowledge_level",
        "personality_type",
        "preferred_response_style",
        "onboarding_progress",
        "last_state",
        "completed_milestones",
        "engagement_score",
        "total_messages",
        "total_sessions",
        "last_active_at",
        "language",
        "timezone",
    }

    def __init__(
        self,
        repository: UserProfileRepository | None = None,
        knowledge_detector: KnowledgeDetector | None = None,
        onboarding_tracker: OnboardingTracker | None = None,
        adaptive_engine: AdaptiveEngine | None = None,
        engagement_service: EngagementService | None = None,
        *,
        auto_create_profile: bool = True,
    ) -> None:
        self.repository = repository or UserProfileRepository()
        self.knowledge_detector = knowledge_detector or KnowledgeDetector()
        self.onboarding_tracker = onboarding_tracker or OnboardingTracker()
        self.adaptive_engine = adaptive_engine or AdaptiveEngine()
        self.engagement_service = engagement_service or EngagementService()
        self.auto_create_profile = auto_create_profile

    def get_or_create_profile(self, db: Session, user_id: UUID) -> UserProfile:
        """Return existing profile or create a default one."""
        existing = self.repository.get_by_user_id(db, user_id)
        if existing is not None:
            return existing

        created = self.repository.create_if_missing(db, user_id)
        logger.info("profile_created", extra={"event": "profile_created", "user_id": str(user_id)})
        return created

    def get_profile(self, db: Session, user_id: UUID) -> UserProfile:
        """Return profile by user id, optionally auto-creating when allowed."""
        profile = self.repository.get_by_user_id(db, user_id)
        if profile is not None:
            return profile
        if self.auto_create_profile:
            created = self.repository.create_if_missing(db, user_id)
            logger.info("profile_created", extra={"event": "profile_created", "user_id": str(user_id)})
            return created
        raise UserProfileNotFoundError("User profile not found")

    def update_profile(self, db: Session, user_id: UUID, update_data: dict[str, Any]) -> UserProfile:
        """Persist partial profile updates via repository."""
        profile = self.get_profile(db, user_id)
        sanitized = self._sanitize_profile_updates(update_data)
        if not sanitized:
            return profile
        updated = self.repository.update_profile(db, profile, sanitized)
        logger.info(
            "profile_updated",
            extra={
                "event": "profile_updated",
                "user_id": str(user_id),
                "updated_fields": sorted(sanitized.keys()),
            },
        )
        return updated

    def submit_assessment(self, db: Session, user_id: UUID, answers: dict[str, Any]) -> UserProfile:
        """Apply assessment-derived profile signals and persist."""
        if not isinstance(answers, Mapping):
            raise UserProfileDomainError("Assessment payload must be a mapping")

        profile = self.get_profile(db, user_id)
        old_level = profile.knowledge_level
        answers_payload = dict(answers)
        detected_level = self.knowledge_detector.detect_from_assessment(answers)

        update_payload: dict[str, Any] = {
            "knowledge_level": detected_level,
            "last_active_at": self._utc_now(),
        }
        if "personality_type" in answers_payload and answers_payload.get("personality_type") is not None:
            update_payload["personality_type"] = self._normalize_personality(answers_payload.get("personality_type"))
        if "preferred_response_style" in answers_payload and answers_payload.get("preferred_response_style") is not None:
            update_payload["preferred_response_style"] = self._normalize_response_style(
                answers_payload.get("preferred_response_style")
            )

        combined = self._snapshot_with_updates(profile, update_payload)
        update_payload["engagement_score"] = self.engagement_service.recalculate_engagement(combined)
        updated = self.repository.update_profile(db, profile, update_payload)

        logger.info(
            "assessment_submitted",
            extra={
                "event": "assessment_submitted",
                "user_id": str(user_id),
                "answer_keys": sorted(str(key) for key in answers_payload.keys()),
            },
        )
        if updated.knowledge_level != old_level:
            logger.info(
                "knowledge_level_changed",
                extra={
                    "event": "knowledge_level_changed",
                    "user_id": str(user_id),
                    "from_level": str(old_level.value),
                    "to_level": str(updated.knowledge_level.value),
                },
            )
        logger.info(
            "engagement_updated",
            extra={
                "event": "engagement_updated",
                "user_id": str(user_id),
                "engagement_score": float(updated.engagement_score),
            },
        )
        return updated

    def update_state(self, db: Session, user_id: UUID, state: str) -> UserProfile:
        """Update onboarding state/progress and conditionally add milestone."""
        profile = self.get_profile(db, user_id)
        try:
            state_updates = self.onboarding_tracker.update_progress(profile, state)
        except ValueError as exc:
            raise InvalidOnboardingStateError(str(exc)) from exc

        milestone = self.onboarding_tracker.maybe_record_milestone(profile, state)
        completed_milestones = list(profile.completed_milestones or [])
        if milestone is not None and milestone not in completed_milestones:
            completed_milestones.append(milestone)

        update_payload: dict[str, Any] = {
            **state_updates,
            "completed_milestones": completed_milestones,
            "last_active_at": self._utc_now(),
        }
        combined = self._snapshot_with_updates(profile, update_payload)
        update_payload["engagement_score"] = self.engagement_service.recalculate_engagement(combined)
        updated = self.repository.update_profile(db, profile, update_payload)
        logger.info(
            "onboarding_state_updated",
            extra={
                "event": "onboarding_state_updated",
                "user_id": str(user_id),
                "state": str(update_payload["last_state"]),
                "progress": float(update_payload["onboarding_progress"]),
            },
        )
        logger.info(
            "engagement_updated",
            extra={
                "event": "engagement_updated",
                "user_id": str(user_id),
                "engagement_score": float(updated.engagement_score),
            },
        )

        if milestone is not None:
            self.repository.add_milestone(
                db,
                user_id=user_id,
                milestone_name=milestone,
                metadata={"state": update_payload["last_state"]},
            )
            logger.info(
                "milestone_recorded",
                extra={
                    "event": "milestone_recorded",
                    "user_id": str(user_id),
                    "milestone_name": milestone,
                },
            )
        return updated

    def register_message_activity(self, db: Session, user_id: UUID) -> UserProfile:
        """Register message activity and persist derived engagement updates."""
        profile = self.get_profile(db, user_id)
        updates = self.engagement_service.register_message(profile)
        updated = self.repository.update_profile(db, profile, updates)
        logger.info(
            "engagement_updated",
            extra={
                "event": "engagement_updated",
                "user_id": str(user_id),
                "engagement_score": float(updated.engagement_score),
                "total_messages": int(updated.total_messages),
            },
        )
        return updated

    def register_session_activity(self, db: Session, user_id: UUID) -> UserProfile:
        """Register session activity and persist derived engagement updates."""
        profile = self.get_profile(db, user_id)
        updates = self.engagement_service.register_session(profile)
        updated = self.repository.update_profile(db, profile, updates)
        logger.info(
            "engagement_updated",
            extra={
                "event": "engagement_updated",
                "user_id": str(user_id),
                "engagement_score": float(updated.engagement_score),
                "total_sessions": int(updated.total_sessions),
            },
        )
        return updated

    def get_adaptive_parameters(self, db: Session, user_id: UUID) -> dict[str, Any]:
        """Return adaptive response parameters derived from user profile."""
        profile = self.get_profile(db, user_id)
        params = self.adaptive_engine.get_response_parameters(profile)
        return {
            "user_id": profile.user_id,
            "knowledge_level": profile.knowledge_level,
            "personality_type": profile.personality_type,
            "preferred_response_style": profile.preferred_response_style,
            "onboarding_progress": profile.onboarding_progress,
            "engagement_score": profile.engagement_score,
            "recommended_state": profile.last_state,
            **params,
        }

    def list_milestones(self, db: Session, user_id: UUID) -> list[dict[str, Any]]:
        """Return user milestones mapped to response-friendly dictionaries."""
        milestones = self.repository.list_milestones(db, user_id)
        return [
            {
                "id": milestone.id,
                "user_id": milestone.user_id,
                "milestone_name": milestone.milestone_name,
                "completed_at": milestone.completed_at,
                "metadata": dict(milestone.metadata_json or {}),
            }
            for milestone in milestones
        ]

    def maybe_update_knowledge_from_query(self, db: Session, user_id: UUID, user_message: str) -> UserProfile:
        """Update knowledge level from a query when heuristic detects a different level."""
        if not isinstance(user_message, str) or not user_message.strip():
            raise UserProfileDomainError("User message must be a non-empty string")

        profile = self.get_profile(db, user_id)
        detected_level = self.knowledge_detector.detect_from_query(user_message)
        if detected_level == profile.knowledge_level:
            return profile

        updates: dict[str, Any] = {
            "knowledge_level": detected_level,
            "last_active_at": self._utc_now(),
        }
        combined = self._snapshot_with_updates(profile, updates)
        updates["engagement_score"] = self.engagement_service.recalculate_engagement(combined)
        updated = self.repository.update_profile(db, profile, updates)
        logger.info(
            "knowledge_level_changed",
            extra={
                "event": "knowledge_level_changed",
                "user_id": str(user_id),
                "from_level": str(profile.knowledge_level.value),
                "to_level": str(detected_level.value),
            },
        )
        logger.info(
            "engagement_updated",
            extra={
                "event": "engagement_updated",
                "user_id": str(user_id),
                "engagement_score": float(updated.engagement_score),
            },
        )
        return updated

    def _snapshot_with_updates(self, profile: UserProfile, updates: dict[str, Any]) -> dict[str, Any]:
        return {
            "total_messages": updates.get("total_messages", profile.total_messages),
            "total_sessions": updates.get("total_sessions", profile.total_sessions),
            "onboarding_progress": updates.get("onboarding_progress", profile.onboarding_progress),
            "last_active_at": updates.get("last_active_at", profile.last_active_at),
        }

    def _sanitize_profile_updates(self, update_data: dict[str, Any]) -> dict[str, Any]:
        unknown_fields = [field for field in update_data if field not in self._PATCH_ALLOWED_FIELDS]
        if unknown_fields:
            raise InvalidProfileUpdateError(
                f"Unsupported profile update fields: {', '.join(sorted(unknown_fields))}"
            )

        sanitized: dict[str, Any] = {}
        for field, value in update_data.items():
            if value is None:
                continue
            if field == "knowledge_level":
                sanitized[field] = self._normalize_knowledge_level(value)
                continue
            if field == "personality_type":
                sanitized[field] = self._normalize_personality(value)
                continue
            if field == "preferred_response_style":
                sanitized[field] = self._normalize_response_style(value)
                continue
            if field == "onboarding_progress":
                progress = float(value)
                if progress < 0.0 or progress > 100.0:
                    raise InvalidProfileUpdateError("onboarding_progress must be between 0 and 100")
                sanitized[field] = progress
                continue
            sanitized[field] = value
        return sanitized

    def _normalize_knowledge_level(self, value: object) -> KnowledgeLevel:
        if isinstance(value, KnowledgeLevel):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized == "expert":
                normalized = KnowledgeLevel.ADVANCED.value
            try:
                return KnowledgeLevel(normalized)
            except ValueError as exc:
                raise InvalidProfileUpdateError(f"Invalid knowledge_level: {value}") from exc
        raise InvalidProfileUpdateError(f"Invalid knowledge_level: {value}")

    def _normalize_personality(self, value: object) -> PersonalityType | None:
        if value is None:
            return None
        if isinstance(value, PersonalityType):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            try:
                return PersonalityType(normalized)
            except ValueError as exc:
                raise InvalidProfileUpdateError(f"Invalid personality_type: {value}") from exc
        raise InvalidProfileUpdateError(f"Invalid personality_type: {value}")

    def _normalize_response_style(self, value: object) -> ResponseStyle:
        if isinstance(value, ResponseStyle):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            try:
                return ResponseStyle(normalized)
            except ValueError as exc:
                raise InvalidProfileUpdateError(f"Invalid preferred_response_style: {value}") from exc
        raise InvalidProfileUpdateError(f"Invalid preferred_response_style: {value}")

    def _utc_now(self):
        from datetime import datetime, timezone

        return datetime.now(timezone.utc)
