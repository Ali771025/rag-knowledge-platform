"""Internal persona domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

from app.internal.persona.enums import PersonaModifier, PersonaType


@dataclass(frozen=True, slots=True)
class PersonaAnalysisResult:
    """Result object exchanged across internal persona components."""

    session_id: str
    persona_type: PersonaType
    confidence: float
    modifiers: tuple[PersonaModifier, ...] = field(default_factory=tuple)
    signal_scores: Mapping[str, float] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
