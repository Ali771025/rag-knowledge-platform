"""Typed enums for persona intelligence."""

from __future__ import annotations

from enum import Enum


class PersonaType(str, Enum):
    """Coarse user persona classifications used by downstream policies."""

    EXPLORER = "explorer"
    ANALYST = "analyst"
    PRAGMATIST = "pragmatist"
    EXECUTOR = "executor"


class PersonaModifier(str, Enum):
    """Context modifiers that tune persona interpretation and messaging."""

    HIGH_INTENT = "high_intent"
    BUDGET_SENSITIVE = "budget_sensitive"
    RISK_AVERSE = "risk_averse"
    TIME_CONSTRAINED = "time_constrained"
    TRUST_LOW = "trust_low"
    AUTHORITY_DRIVEN = "authority_driven"
    COMMUNITY_DRIVEN = "community_driven"
    INDIVIDUAL_DRIVEN = "individual_driven"
    REGULATION_SENSITIVE = "regulation_sensitive"
