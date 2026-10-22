"""Signal models shared by extraction and persona scoring layers."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PersonaSignal(str, Enum):
    """Normalized signal keys emitted by deterministic extraction logic."""

    LEXICAL_ENGAGEMENT = "lexical_engagement"
    HESITATION = "hesitation"
    PROOF_SEEKING = "proof_seeking"
    ROI_SEEKING = "roi_seeking"
    ANALYTICAL_DEPTH = "analytical_depth"
    URGENCY = "urgency"
    GAMIFICATION_AFFINITY = "gamification_affinity"
    ENGAGEMENT_PERSISTENCE = "engagement_persistence"
    METADATA_BEHAVIORAL = "metadata_behavioral"


class ExtractedPersonaSignals(BaseModel):
    """Normalized extraction output suitable for persona scoring."""

    message: str = Field(..., min_length=1, max_length=8000)
    signals: dict[PersonaSignal, float] = Field(default_factory=dict)
    evidence: dict[PersonaSignal, tuple[str, ...]] = Field(default_factory=dict)
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_intensities(self) -> "ExtractedPersonaSignals":
        for signal, value in self.signals.items():
            _ = signal
            if value < 0.0 or value > 1.0:
                raise ValueError("signal intensity must be between 0.0 and 1.0")
        return self

    def normalized_signals(self) -> dict[PersonaSignal, float]:
        """Return all known signals with missing values backfilled to zero."""

        output = {signal: 0.0 for signal in PersonaSignal}
        output.update(self.signals)
        return output
