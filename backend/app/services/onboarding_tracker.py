"""Stateless onboarding progress and milestone logic."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class OnboardingTracker:
    """Handles deterministic onboarding state-to-progress transformation."""

    _STATE_ORDER: tuple[str, ...] = ("start", "intro", "education", "qna", "join")
    _STATE_PROGRESS: dict[str, float] = {
        "start": 0.0,
        "intro": 20.0,
        "education": 50.0,
        "qna": 80.0,
        "join": 100.0,
    }
    _STATE_MILESTONES: dict[str, str] = {
        "intro": "milestone_intro_completed",
        "education": "milestone_education_completed",
        "qna": "milestone_qna_completed",
        "join": "milestone_join_completed",
    }

    def calculate_progress_from_state(self, state: str) -> float:
        """Map a supported onboarding state to its canonical progress value."""
        normalized = self._normalize_state(state)
        return self._STATE_PROGRESS[normalized]

    def update_progress(
        self,
        profile: Any,
        new_state: str,
        *,
        allow_decrease: bool = False,
    ) -> dict[str, Any]:
        """Return updated state/progress payload without DB side effects.

        By default progress is monotonic and does not decrease.
        """
        normalized_state = self._normalize_state(new_state)
        target_progress = self.calculate_progress_from_state(normalized_state)
        current_progress = float(self._get_attr(profile, "onboarding_progress", 0.0))

        next_progress = target_progress if allow_decrease else max(current_progress, target_progress)
        return {
            "last_state": normalized_state,
            "onboarding_progress": next_progress,
        }

    def maybe_record_milestone(self, profile: Any, new_state: str) -> str | None:
        """Return standardized milestone name if state transition yields a new one."""
        normalized_state = self._normalize_state(new_state)
        milestone_name = self._STATE_MILESTONES.get(normalized_state)
        if milestone_name is None:
            return None

        completed = self._completed_milestones(profile)
        if milestone_name in completed:
            return None
        return milestone_name

    def _normalize_state(self, state: str) -> str:
        normalized = state.strip().lower()
        if normalized not in self._STATE_ORDER:
            valid_states = ", ".join(self._STATE_ORDER)
            raise ValueError(f"Unsupported onboarding state '{state}'. Valid states: {valid_states}")
        return normalized

    def _completed_milestones(self, profile: Any) -> set[str]:
        values = self._get_attr(profile, "completed_milestones", [])
        if not isinstance(values, list):
            return set()
        return {str(value) for value in values}

    def _get_attr(self, profile: Any, field: str, default: object) -> object:
        if isinstance(profile, Mapping):
            return profile.get(field, default)
        return getattr(profile, field, default)
