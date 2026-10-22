"""Repository interfaces for persona persistence contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.internal.persona.enums import PersonaModifier
from app.models.persona_conversion import ModifierHistory, PersonaHistory, PersonaState


class PersonaStateRepository(ABC):
    """Persistence contract for current persona state records."""

    @abstractmethod
    def get_by_session_id(self, session_id: str) -> PersonaState | None:
        """Return the latest persona state for a session."""

    @abstractmethod
    def upsert(self, payload: dict[str, Any]) -> PersonaState:
        """Create or update the persona state for one session."""


class PersonaHistoryRepository(ABC):
    """Persistence contract for persona transition history."""

    @abstractmethod
    def create(self, payload: dict[str, Any]) -> PersonaHistory:
        """Persist one persona history entry."""


class ModifierHistoryRepository(ABC):
    """Persistence contract for modifier application history."""

    @abstractmethod
    def list_by_session_id(self, session_id: str) -> list[ModifierHistory]:
        """Return modifier history ordered by creation time."""

    @abstractmethod
    def create(self, payload: dict[str, Any]) -> ModifierHistory:
        """Persist one modifier history entry."""

    @abstractmethod
    def list_by_modifier(self, modifier: PersonaModifier) -> list[ModifierHistory]:
        """Return modifier history filtered by modifier."""
