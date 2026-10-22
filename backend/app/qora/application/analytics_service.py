from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from app.qora.infrastructure.persistence.models import UserInteractionEvent


@dataclass(frozen=True, slots=True)
class QoraKPIReport:
    event_counts: dict[str, int]
    time_to_first_cta_ms: float | None
    cta_ctr: float | None
    recommendation_acceptance_rate: float | None
    achievement_completion_rate: float | None
    guardrail_trigger_rate: float | None
    fallback_rate: float | None

    def public_payload(self) -> dict[str, object]:
        # No user id, conversation id, persona, modifier, or raw event metadata leaves this boundary.
        return {
            "event_counts": self.event_counts,
            "time_to_first_cta_ms": self.time_to_first_cta_ms,
            "cta_ctr": self.cta_ctr,
            "recommendation_acceptance_rate": self.recommendation_acceptance_rate,
            "achievement_completion_rate": self.achievement_completion_rate,
            "guardrail_trigger_rate": self.guardrail_trigger_rate,
            "fallback_rate": self.fallback_rate,
        }


class QoraAnalyticsService:
    def aggregate(self, events: Iterable[UserInteractionEvent]) -> QoraKPIReport:
        ordered = sorted(events, key=lambda item: item.occurred_at)
        counts = Counter(item.event_type for item in ordered)
        conversation_started = self._first_time(ordered, "CONVERSATION_STARTED")
        cta_shown = self._first_time(ordered, "CTA_SHOWN") or self._first_time(ordered, "QORA_STAGE_CTA")
        time_to_first_cta = None
        if conversation_started and cta_shown:
            time_to_first_cta = max((cta_shown - conversation_started).total_seconds() * 1000, 0.0)
        cta_denominator = counts["CTA_SHOWN"] + counts["QORA_STAGE_CTA"]
        recommendation_denominator = counts["PRODUCT_RECOMMENDED"]
        achievement_denominator = counts["ACHIEVEMENT_STARTED"]
        total = sum(counts.values())
        return QoraKPIReport(
            event_counts=dict(counts),
            time_to_first_cta_ms=time_to_first_cta,
            cta_ctr=self._ratio(counts["CTA_CLICKED"], cta_denominator),
            recommendation_acceptance_rate=self._ratio(
                counts["FEEDBACK_ACCEPTED"], recommendation_denominator
            ),
            achievement_completion_rate=self._ratio(
                counts["ACHIEVEMENT_COMPLETED"], achievement_denominator
            ),
            guardrail_trigger_rate=self._ratio(counts["GUARDRAIL_TRIGGERED"], total),
            fallback_rate=self._ratio(counts["FALLBACK_USED"], total),
        )

    @staticmethod
    def _first_time(events: list[UserInteractionEvent], event_type: str) -> datetime | None:
        return next((item.occurred_at for item in events if item.event_type == event_type), None)

    @staticmethod
    def _ratio(numerator: int, denominator: int) -> float | None:
        return round(numerator / denominator, 4) if denominator else None
