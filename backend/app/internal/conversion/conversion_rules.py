"""YAML-backed typed contracts for conversion decision policies."""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from app.internal.conversion.policy_enums import EconomicSuggestionStrength
from app.internal.conversion.policy_enums import JourneyStage as FunnelStage
from app.internal.persona.enums import PersonaType

try:
    import yaml
except ImportError:  # pragma: no cover - surfaced via ConversionRulesError
    yaml = None


_DEFAULT_RULES_PATH = Path(__file__).with_name("conversion_rules.yaml")
_EXTRA_PERSONA_LABELS = frozenset({"saver", "hunter", "player", "architect", "neutral"})
_VALID_PERSONAS = frozenset(member.value for member in PersonaType) | _EXTRA_PERSONA_LABELS


class ConversionRulesError(RuntimeError):
    """Raised when conversion rule policy cannot be loaded or validated."""


class ConversionDecisionAction(str, Enum):
    """Supported actions for decision policy rules."""

    BLOCK_ALL = "block_all"
    BLOCK_ECONOMIC = "block_economic"
    ALLOW_MICRO_COMMIT_ONLY = "allow_micro_commit_only"
    ALLOW_ECONOMIC = "allow_economic"
    SOFTEN_ECONOMIC = "soften_economic"


def _parse_stage(value: Any) -> FunnelStage:
    if isinstance(value, FunnelStage):
        return value
    if not isinstance(value, str):
        raise ValueError("stage value must be a string")
    token = value.strip()
    if not token:
        raise ValueError("stage value cannot be blank")
    by_name = token.upper()
    if by_name in FunnelStage.__members__:
        return FunnelStage.__members__[by_name]
    by_value = token.lower()
    for member in FunnelStage:
        if member.value == by_value:
            return member
    raise ValueError(f"Invalid stage value: {value}")


def _parse_persona(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("persona value must be a string")
    token = value.strip().lower()
    if not token:
        raise ValueError("persona value cannot be blank")
    if token not in _VALID_PERSONAS:
        raise ValueError(f"Invalid persona value: {value}")
    return token


def _parse_strength(value: Any) -> EconomicSuggestionStrength:
    if isinstance(value, EconomicSuggestionStrength):
        return value
    if not isinstance(value, str):
        raise ValueError("strength value must be a string")
    token = value.strip()
    if not token:
        raise ValueError("strength value cannot be blank")
    by_name = token.upper()
    if by_name in EconomicSuggestionStrength.__members__:
        return EconomicSuggestionStrength.__members__[by_name]
    by_value = token.lower()
    for member in EconomicSuggestionStrength:
        if member.value == by_value:
            return member
    raise ValueError(f"Invalid strength value: {value}")


class ConversionDecisionThresholds(BaseModel):
    """Configurable baseline thresholds for conversion policy decisions."""

    trust_block_threshold: float = Field(default=0.4, ge=0.0, le=1.0)
    economic_min_trust: float = Field(default=0.6, ge=0.0, le=1.0)
    saver_confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    rejection_softening_threshold: int = Field(default=2, ge=1, le=50)
    default_economic_strength: EconomicSuggestionStrength = EconomicSuggestionStrength.MODERATE
    softened_economic_strength: EconomicSuggestionStrength = EconomicSuggestionStrength.SOFT

    model_config = ConfigDict(extra="forbid")

    @field_validator("default_economic_strength", "softened_economic_strength", mode="before")
    @classmethod
    def _validate_strengths(cls, value: Any) -> EconomicSuggestionStrength:
        return _parse_strength(value)


class ConversionDecisionRuleCondition(BaseModel):
    """Predicate payload for one policy rule."""

    trust_score_lt: float | None = Field(default=None, ge=0.0, le=1.0)
    trust_score_gte: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence_gt: float | None = Field(default=None, ge=0.0, le=1.0)
    stage_lt: FunnelStage | None = None
    stage_gte: FunnelStage | None = None
    persona: str | None = None
    persona_in: list[str] = Field(default_factory=list)
    intent: str | None = Field(default=None, min_length=1, max_length=64)
    rejection_count_gte: int | None = Field(default=None, ge=0, le=100)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("stage_lt", "stage_gte", mode="before")
    @classmethod
    def _validate_stages(cls, value: Any) -> FunnelStage | None:
        if value is None:
            return None
        return _parse_stage(value)

    @field_validator("persona", mode="before")
    @classmethod
    def _validate_persona(cls, value: Any) -> str | None:
        if value is None:
            return None
        return _parse_persona(value)

    @field_validator("persona_in", mode="before")
    @classmethod
    def _validate_persona_in(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("persona_in must be a list")
        return [_parse_persona(item) for item in value]


class ConversionDecisionRule(BaseModel):
    """One conversion policy rule entry."""

    id: str = Field(..., min_length=1, max_length=64)
    priority: int = Field(..., ge=1, le=1000)
    condition: ConversionDecisionRuleCondition
    action: ConversionDecisionAction

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("action", mode="before")
    @classmethod
    def _validate_action(cls, value: Any) -> ConversionDecisionAction:
        if isinstance(value, ConversionDecisionAction):
            return value
        if not isinstance(value, str):
            raise ValueError("action must be a string")
        token = value.strip().lower()
        for member in ConversionDecisionAction:
            if member.value == token:
                return member
        raise ValueError(f"Invalid action: {value}")


class ConversionDecisionPolicyConfig(BaseModel):
    """Versioned root model for conversion decision policies."""

    version: str = Field(..., min_length=1, max_length=16)
    thresholds: ConversionDecisionThresholds = Field(default_factory=ConversionDecisionThresholds)
    rules: list[ConversionDecisionRule] = Field(..., min_length=1)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validate_unique_rule_ids(self) -> "ConversionDecisionPolicyConfig":
        ids = [item.id for item in self.rules]
        if len(ids) != len(set(ids)):
            raise ValueError("rules must have unique ids")
        return self


def _read_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise ConversionRulesError("PyYAML is required to load conversion rules config")
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConversionRulesError(f"Unable to read conversion rules file: {path}") from exc

    try:
        loaded = yaml.safe_load(raw)
    except yaml.YAMLError as exc:  # type: ignore[union-attr]
        raise ConversionRulesError(f"Invalid YAML in conversion rules file: {path}") from exc

    if not isinstance(loaded, dict):
        raise ConversionRulesError("Conversion rules root must be a YAML object")
    return loaded


def load_conversion_decision_policy(path: str | Path | None = None) -> ConversionDecisionPolicyConfig:
    """Load and validate conversion decision policy YAML."""

    config_path = Path(path) if path is not None else _DEFAULT_RULES_PATH
    payload = _read_yaml(config_path)
    try:
        return ConversionDecisionPolicyConfig.model_validate(payload)
    except ValidationError as exc:
        raise ConversionRulesError(f"Conversion rules validation failed for {config_path}") from exc


@lru_cache(maxsize=1)
def load_default_conversion_decision_policy() -> ConversionDecisionPolicyConfig:
    """Load and memoize default conversion decision policy YAML."""

    return load_conversion_decision_policy(_DEFAULT_RULES_PATH)
