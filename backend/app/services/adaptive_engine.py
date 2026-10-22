"""Stateless adaptive engine for response parameter selection.

This module performs deterministic profile-to-parameter transformation only.
No persistence, network calls, or side effects are introduced.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.models.user_profile import KnowledgeLevel, ResponseStyle


class AdaptiveEngine:
    """Computes response parameters from user profile attributes."""

    def get_response_parameters(self, profile: Any) -> dict[str, Any]:
        """Return deterministic response parameters for a profile-like object."""
        knowledge_level = self._get_attr(profile, "knowledge_level", KnowledgeLevel.BEGINNER)
        style = self._get_attr(profile, "preferred_response_style", ResponseStyle.CONCISE)
        progress = float(self._get_attr(profile, "onboarding_progress", 0.0))

        normalized_level = self._normalize_knowledge_level(knowledge_level)
        normalized_style = self._normalize_style(style)

        base = self._base_parameters_for_level(normalized_level)
        style_adjusted = self._apply_style_adjustments(base, normalized_style)
        return self._apply_progress_adjustments(style_adjusted, progress)

    def _base_parameters_for_level(self, level: KnowledgeLevel) -> dict[str, Any]:
        if level == KnowledgeLevel.ADVANCED:
            return {
                "explanation_depth": "high",
                "include_examples": False,
                "include_step_by_step": False,
                "max_tokens": 420,
                "tone": "technical",
                "progressive_disclosure_level": 1,
            }
        if level == KnowledgeLevel.INTERMEDIATE:
            return {
                "explanation_depth": "medium",
                "include_examples": True,
                "include_step_by_step": False,
                "max_tokens": 520,
                "tone": "balanced",
                "progressive_disclosure_level": 2,
            }
        return {
            "explanation_depth": "low",
            "include_examples": True,
            "include_step_by_step": True,
            "max_tokens": 650,
            "tone": "supportive",
            "progressive_disclosure_level": 3,
        }

    def _apply_style_adjustments(
        self,
        params: dict[str, Any],
        style: ResponseStyle,
    ) -> dict[str, Any]:
        adjusted = dict(params)
        if style == ResponseStyle.DETAILED:
            adjusted["max_tokens"] = int(adjusted["max_tokens"] * 1.2)
            adjusted["include_examples"] = True
            adjusted["progressive_disclosure_level"] = min(
                int(adjusted["progressive_disclosure_level"]) + 1,
                4,
            )
        elif style == ResponseStyle.CONCISE:
            adjusted["max_tokens"] = int(adjusted["max_tokens"] * 0.8)
            adjusted["include_step_by_step"] = bool(adjusted["include_step_by_step"]) and (
                adjusted["explanation_depth"] == "low"
            )
        return adjusted

    def _apply_progress_adjustments(
        self,
        params: dict[str, Any],
        onboarding_progress: float,
    ) -> dict[str, Any]:
        adjusted = dict(params)
        if onboarding_progress >= 75.0:
            adjusted["progressive_disclosure_level"] = max(int(adjusted["progressive_disclosure_level"]) - 1, 1)
            adjusted["max_tokens"] = int(adjusted["max_tokens"] * 0.9)
        elif onboarding_progress <= 25.0:
            adjusted["include_examples"] = True
            adjusted["include_step_by_step"] = True
            adjusted["progressive_disclosure_level"] = min(int(adjusted["progressive_disclosure_level"]) + 1, 4)
        return adjusted

    def _normalize_knowledge_level(self, value: object) -> KnowledgeLevel:
        if isinstance(value, KnowledgeLevel):
            return value
        if isinstance(value, str):
            try:
                return KnowledgeLevel(value.lower())
            except ValueError:
                return KnowledgeLevel.BEGINNER
        return KnowledgeLevel.BEGINNER

    def _normalize_style(self, value: object) -> ResponseStyle:
        if isinstance(value, ResponseStyle):
            return value
        if isinstance(value, str):
            try:
                return ResponseStyle(value.lower())
            except ValueError:
                return ResponseStyle.CONCISE
        return ResponseStyle.CONCISE

    def _get_attr(self, profile: Any, field: str, default: object) -> object:
        if isinstance(profile, Mapping):
            return profile.get(field, default)
        return getattr(profile, field, default)
