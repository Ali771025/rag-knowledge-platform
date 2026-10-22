"""Stateless engagement scoring and activity metric helpers.

Scoring model (0..100):
- Message volume contributes up to 30 points.
- Session volume contributes up to 25 points.
- Onboarding progress contributes up to 20 points.
- Recency contributes between -15 and +20 points.
- A baseline of 20 keeps new profiles in a neutral zone.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any


class EngagementService:
    """Computes engagement score and activity updates without DB/session ownership."""

    def recalculate_engagement(self, profile: Any) -> float:
        """Recalculate engagement score using transparent weighted factors."""
        total_messages = int(self._get_attr(profile, "total_messages", 0))
        total_sessions = int(self._get_attr(profile, "total_sessions", 0))
        onboarding_progress = float(self._get_attr(profile, "onboarding_progress", 0.0))
        last_active_at = self._get_attr(profile, "last_active_at", None)

        base_score = 20.0
        message_score = min(total_messages * 0.75, 30.0)
        session_score = min(total_sessions * 2.5, 25.0)
        progress_score = min(max(onboarding_progress, 0.0) * 0.2, 20.0)
        recency_score = self._calculate_recency_score(last_active_at)

        total = base_score + message_score + session_score + progress_score + recency_score
        return round(max(0.0, min(100.0, total)), 2)

    def register_message(self, profile: Any) -> dict[str, Any]:
        """Return updates after registering one message activity event."""
        total_messages = int(self._get_attr(profile, "total_messages", 0)) + 1
        total_sessions = int(self._get_attr(profile, "total_sessions", 0))
        onboarding_progress = float(self._get_attr(profile, "onboarding_progress", 0.0))
        now = datetime.now(timezone.utc)

        snapshot = {
            "total_messages": total_messages,
            "total_sessions": total_sessions,
            "onboarding_progress": onboarding_progress,
            "last_active_at": now,
        }
        return {
            "total_messages": total_messages,
            "last_active_at": now,
            "engagement_score": self.recalculate_engagement(snapshot),
        }

    def register_session(self, profile: Any) -> dict[str, Any]:
        """Return updates after registering one session activity event."""
        total_messages = int(self._get_attr(profile, "total_messages", 0))
        total_sessions = int(self._get_attr(profile, "total_sessions", 0)) + 1
        onboarding_progress = float(self._get_attr(profile, "onboarding_progress", 0.0))
        now = datetime.now(timezone.utc)

        snapshot = {
            "total_messages": total_messages,
            "total_sessions": total_sessions,
            "onboarding_progress": onboarding_progress,
            "last_active_at": now,
        }
        return {
            "total_sessions": total_sessions,
            "last_active_at": now,
            "engagement_score": self.recalculate_engagement(snapshot),
        }

    def _calculate_recency_score(self, last_active_at: object) -> float:
        if not isinstance(last_active_at, datetime):
            return -10.0

        if last_active_at.tzinfo is None:
            last_active_at = last_active_at.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        hours_since = max(0.0, (now - last_active_at).total_seconds() / 3600.0)

        if hours_since <= 24:
            return 20.0
        if hours_since <= 72:
            return 12.0
        if hours_since <= 168:
            return 6.0
        if hours_since <= 336:
            return 0.0
        return -15.0

    def _get_attr(self, profile: Any, field: str, default: object) -> object:
        if isinstance(profile, Mapping):
            return profile.get(field, default)
        return getattr(profile, field, default)
