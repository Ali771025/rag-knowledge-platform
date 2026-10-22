"""Adapter that exposes profile personalization context to dialogue flows.

This adapter intentionally avoids full prompt generation and only returns
the personalization/adaptation data block required by dialogue components.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.services.user_profile_service import UserProfileService


class DialogueProfileAdapter:
    """Builds dialogue-facing personalization context from profile services."""

    def __init__(self, user_profile_service: UserProfileService | None = None) -> None:
        self.user_profile_service = user_profile_service or UserProfileService()

    def build_dialogue_personalization_context(self, db: Session, user_id: UUID) -> dict[str, Any]:
        """Return personalization context used by dialogue orchestration."""
        profile = self.user_profile_service.get_or_create_profile(db, user_id)
        adaptive_params = self.user_profile_service.get_adaptive_parameters(db, user_id)
        return {
            "knowledge_level": profile.knowledge_level.value,
            "preferred_response_style": profile.preferred_response_style.value,
            "explanation_depth": adaptive_params["explanation_depth"],
            "include_examples": adaptive_params["include_examples"],
            "include_step_by_step": adaptive_params["include_step_by_step"],
            "max_tokens": adaptive_params["max_tokens"],
            "onboarding_progress": profile.onboarding_progress,
            "current_state": profile.last_state,
        }

    def build_prompt_personalization_block(self, profile: Any, adaptive_params: dict[str, Any]) -> str:
        """Render a compact, bounded personalization block for system prompts."""
        knowledge_level = self._get_value(profile, "knowledge_level", "beginner")
        if not isinstance(knowledge_level, str):
            knowledge_level = str(getattr(knowledge_level, "value", "beginner"))

        response_style = self._get_value(profile, "preferred_response_style", "concise")
        if not isinstance(response_style, str):
            response_style = str(getattr(response_style, "value", "concise"))

        onboarding_progress = float(self._get_value(profile, "onboarding_progress", 0.0))
        current_state = str(self._get_value(profile, "last_state", "start"))

        return (
            "Personalization Context:\n"
            f"- knowledge_level: {knowledge_level}\n"
            f"- preferred_response_style: {response_style}\n"
            f"- explanation_depth: {adaptive_params.get('explanation_depth', 'medium')}\n"
            f"- include_examples: {bool(adaptive_params.get('include_examples', True))}\n"
            f"- include_step_by_step: {bool(adaptive_params.get('include_step_by_step', False))}\n"
            f"- max_tokens: {int(adaptive_params.get('max_tokens', 512))}\n"
            f"- onboarding_progress: {onboarding_progress:.1f}\n"
            f"- current_state: {current_state}\n"
        )

    def maybe_update_knowledge_from_query(self, db: Session, user_id: UUID, user_message: str) -> dict[str, Any]:
        """Apply query-based knowledge detection and return update summary."""
        before = self.user_profile_service.get_or_create_profile(db, user_id).knowledge_level
        after_profile = self.user_profile_service.maybe_update_knowledge_from_query(db, user_id, user_message)
        return {
            "before": before.value,
            "after": after_profile.knowledge_level.value,
            "changed": before != after_profile.knowledge_level,
        }

    def _get_value(self, profile: Any, field: str, default: object) -> object:
        if isinstance(profile, dict):
            return profile.get(field, default)
        return getattr(profile, field, default)
