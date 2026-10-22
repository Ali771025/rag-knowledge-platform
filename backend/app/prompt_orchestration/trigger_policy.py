"""YAML-backed typed policy contracts for trigger selection."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from app.internal.conversion.policy_enums import TriggerType
from app.internal.conversion.policy_enums import JourneyStage as FunnelStage
from app.internal.persona.enums import PersonaModifier, PersonaType

try:
    import yaml
except ImportError:  # pragma: no cover - surfaced as TriggerPolicyConfigError at runtime
    yaml = None


_DEFAULT_POLICY_PATH = Path(__file__).with_name("trigger_policy.yaml")
_EXTRA_PERSONA_LABELS = frozenset({"all", "saver", "hunter", "player", "architect", "neutral"})
_VALID_PERSONA_LABELS = frozenset({member.value for member in PersonaType}) | _EXTRA_PERSONA_LABELS


class TriggerPolicyConfigError(RuntimeError):
    """Raised when trigger policy YAML cannot be loaded or validated."""


def _parse_enum_token(token: Any, enum_type: type) -> Any:
    if isinstance(token, enum_type):
        return token
    if not isinstance(token, str):
        raise ValueError(f"Expected string token for {enum_type.__name__}, got: {type(token).__name__}")
    normalized = token.strip()
    if not normalized:
        raise ValueError(f"Blank token is not valid for {enum_type.__name__}")

    by_name = normalized.upper()
    if by_name in enum_type.__members__:
        return enum_type.__members__[by_name]

    by_value = normalized.lower()
    for member in enum_type:
        if member.value == by_value:
            return member

    raise ValueError(f"Invalid {enum_type.__name__}: {token}")


def _normalize_persona_label(raw: str) -> str:
    normalized = raw.strip().lower()
    if not normalized:
        raise ValueError("Persona label cannot be blank")
    if normalized not in _VALID_PERSONA_LABELS:
        raise ValueError(f"Invalid persona label: {raw}")
    return normalized


class TriggerPolicyRule(BaseModel):
    """Per-trigger policy constraints."""

    allowed_stages: list[FunnelStage] = Field(..., min_length=1)
    allowed_personas: list[str] = Field(..., min_length=1)
    required_modifiers: list[PersonaModifier] = Field(default_factory=list)
    min_trust: float = Field(default=0.0, ge=0.0, le=1.0)
    max_per_session: int = Field(default=3, ge=1, le=50)
    requires_real_capacity_limit: bool = False
    softer_fallback: TriggerType | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("allowed_stages", mode="before")
    @classmethod
    def _parse_allowed_stages(cls, value: Any) -> list[FunnelStage]:
        if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
            raise ValueError("allowed_stages must be a list")
        return [_parse_enum_token(item, FunnelStage) for item in value]

    @field_validator("allowed_personas", mode="before")
    @classmethod
    def _parse_allowed_personas(cls, value: Any) -> list[str]:
        if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
            raise ValueError("allowed_personas must be a list")
        return [_normalize_persona_label(str(item)) for item in value]

    @field_validator("required_modifiers", mode="before")
    @classmethod
    def _parse_required_modifiers(cls, value: Any) -> list[PersonaModifier]:
        if value is None:
            return []
        if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
            raise ValueError("required_modifiers must be a list")
        return [_parse_enum_token(item, PersonaModifier) for item in value]

    @field_validator("softer_fallback", mode="before")
    @classmethod
    def _parse_softer_fallback(cls, value: Any) -> TriggerType | None:
        if value is None:
            return None
        return _parse_enum_token(value, TriggerType)

    @model_validator(mode="after")
    def _validate_all_persona_usage(self) -> "TriggerPolicyRule":
        if "all" in self.allowed_personas and len(self.allowed_personas) > 1:
            raise ValueError("allowed_personas cannot combine 'all' with explicit personas")
        return self


class TriggerPolicyConfig(BaseModel):
    """Root trigger-policy config model."""

    max_triggers_per_response: int = Field(default=2, ge=1, le=2)
    scarcity_min_trust: float = Field(default=0.6, ge=0.0, le=1.0)
    resistance_decay: float = Field(default=0.5, gt=0.0, le=1.0)
    trust_low_intensity_factor: float = Field(default=0.7, gt=0.0, le=1.0)
    trigger_policies: dict[TriggerType, TriggerPolicyRule] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")

    @field_validator("trigger_policies", mode="before")
    @classmethod
    def _parse_trigger_policies(cls, value: Any) -> dict[TriggerType, Any]:
        if not isinstance(value, dict):
            raise ValueError("trigger_policies must be an object")
        parsed: dict[TriggerType, Any] = {}
        for raw_key, raw_rule in value.items():
            trigger = _parse_enum_token(raw_key, TriggerType)
            parsed[trigger] = raw_rule
        return parsed


def _read_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise TriggerPolicyConfigError("PyYAML is required to load trigger policy config")

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TriggerPolicyConfigError(f"Unable to read trigger policy file: {path}") from exc

    try:
        loaded = yaml.safe_load(raw)
    except yaml.YAMLError as exc:  # type: ignore[union-attr]
        raise TriggerPolicyConfigError(f"Invalid YAML in trigger policy file: {path}") from exc

    if not isinstance(loaded, dict):
        raise TriggerPolicyConfigError("Trigger policy root must be a YAML object")
    return loaded


def load_trigger_policy(path: str | Path | None = None) -> TriggerPolicyConfig:
    """Load and validate trigger policy YAML."""

    config_path = Path(path) if path is not None else _DEFAULT_POLICY_PATH
    payload = _read_yaml(config_path)
    try:
        return TriggerPolicyConfig.model_validate(payload)
    except ValidationError as exc:
        raise TriggerPolicyConfigError(f"Trigger policy validation failed for {config_path}") from exc


@lru_cache(maxsize=1)
def load_default_trigger_policy() -> TriggerPolicyConfig:
    """Load and memoize the default trigger policy YAML."""

    return load_trigger_policy(_DEFAULT_POLICY_PATH)
