"""Repository interfaces for conversion persistence contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.internal.conversion.enums import FunnelStage
from app.models.persona_conversion import ConversionEvent, FunnelState


class FunnelStateRepository(ABC):
    """Persistence contract for current funnel state records."""

    @abstractmethod
    def get_by_session_id(self, session_id: str) -> FunnelState | None:
        """Return the latest funnel state for a session."""

    @abstractmethod
    def upsert(self, payload: dict[str, Any]) -> FunnelState:
        """Create or update funnel state for one session."""

    @abstractmethod
    def list_by_stage(self, stage: FunnelStage) -> list[FunnelState]:
        """Return funnel states currently in a stage."""


class ConversionEventRepository(ABC):
    """Persistence contract for conversion event history."""

    @abstractmethod
    def create(self, payload: dict[str, Any]) -> ConversionEvent:
        """Persist one conversion event record."""

    @abstractmethod
    def list_by_session_id(self, session_id: str) -> list[ConversionEvent]:
        """Return conversion events ordered by creation time."""
