"""Read-side integration contracts for observability analytics."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.observability.models import AnalyticsSummary


class AnalyticsSummaryReader(Protocol):
    """Loads analytics summaries for a time window."""

    def load_summary(self, window_start: datetime, window_end: datetime) -> AnalyticsSummary:
        """Return an aggregated observability summary for the provided interval."""
