"""Minimal analytics read service for internal reporting endpoints."""

from __future__ import annotations

from app.analytics.repositories import ConversionAnalyticsRepository, TriggerEffectivenessRepository


class AnalyticsInsightsService:
    """Thin service layer for internal analytics reads."""

    def __init__(
        self,
        conversion_repo: ConversionAnalyticsRepository,
        trigger_repo: TriggerEffectivenessRepository,
    ) -> None:
        self.conversion_repo = conversion_repo
        self.trigger_repo = trigger_repo

    def conversion_rate_by_persona(self) -> dict[str, float]:
        return self.conversion_repo.conversion_rate_by_persona()

    def trigger_performance_by_stage(self, stage: str) -> list[dict[str, object]]:
        rows = self.trigger_repo.trigger_performance_by_stage(stage)
        return [
            {
                "trigger_primary": row.trigger_primary,
                "trigger_secondary": row.trigger_secondary,
                "persona": row.persona,
                "stage": row.stage,
                "success_rate": row.success_rate,
                "sample_size": row.sample_size,
                "last_updated": row.last_updated.isoformat(),
            }
            for row in rows
        ]

    def funnel_dropout_by_stage(self) -> dict[str, int]:
        return self.conversion_repo.funnel_dropout_by_stage()
