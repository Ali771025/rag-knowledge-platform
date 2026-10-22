"""Config-driven resolver for safe trigger template fragments."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.internal.conversion.policy_enums import TriggerType
from app.prompt_orchestration.models import PromptOrchestrationMeta, TriggerIntensityLevel

try:
    import yaml
except ImportError:  # pragma: no cover - surfaced via TriggerTemplateError
    yaml = None


_DEFAULT_TEMPLATES_PATH = Path(__file__).with_name("trigger_templates.yaml")
_DISALLOWED_PHRASES = (
    "buy now",
    "last chance",
    "hurry",
    "act immediately",
    "limited time only",
    "do it now",
)


class TriggerTemplateError(RuntimeError):
    """Raised when trigger template config cannot be loaded/resolved."""


def _parse_trigger(token: Any) -> TriggerType:
    if isinstance(token, TriggerType):
        return token
    if not isinstance(token, str):
        raise ValueError("trigger key must be a string")
    normalized = token.strip()
    if not normalized:
        raise ValueError("trigger key cannot be blank")
    by_name = normalized.upper()
    if by_name in TriggerType.__members__:
        return TriggerType.__members__[by_name]
    by_value = normalized.lower()
    for member in TriggerType:
        if member.value == by_value:
            return member
    raise ValueError(f"Invalid trigger: {token}")


class TriggerTemplateFragment(BaseModel):
    """Safe template fragment payload for one intensity level."""

    tone: str = Field(..., min_length=1, max_length=64)
    proof_style: str = Field(..., min_length=1, max_length=64)
    cta_style: str = Field(..., min_length=1, max_length=64)
    fragment: str = Field(..., min_length=1, max_length=240)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("fragment")
    @classmethod
    def _validate_safe_fragment(cls, value: str) -> str:
        lowered = value.lower()
        if any(phrase in lowered for phrase in _DISALLOWED_PHRASES):
            raise ValueError("fragment contains disallowed aggressive urgency language")
        return value


class TriggerTemplateRule(BaseModel):
    """Per-trigger intensity templates and guardrails."""

    allow_high: bool = False
    requires_capacity_flag: bool = False
    soft: TriggerTemplateFragment
    medium: TriggerTemplateFragment
    high: TriggerTemplateFragment | None = None

    model_config = ConfigDict(extra="forbid")


class TriggerTemplatesConfig(BaseModel):
    """Root YAML model for trigger template fragment resolution."""

    version: str = Field(..., min_length=1, max_length=16)
    high_intensity_threshold: float = Field(default=0.85, ge=0.5, le=1.0)
    templates: dict[TriggerType, TriggerTemplateRule] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")

    @field_validator("templates", mode="before")
    @classmethod
    def _parse_templates(cls, value: Any) -> dict[TriggerType, Any]:
        if not isinstance(value, dict):
            raise ValueError("templates must be a mapping")
        parsed: dict[TriggerType, Any] = {}
        for raw_key, raw_rule in value.items():
            parsed[_parse_trigger(raw_key)] = raw_rule
        return parsed


def _read_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise TriggerTemplateError("PyYAML is required to load trigger templates")

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TriggerTemplateError(f"Unable to read trigger templates file: {path}") from exc

    try:
        loaded = yaml.safe_load(raw)
    except yaml.YAMLError as exc:  # type: ignore[union-attr]
        raise TriggerTemplateError(f"Invalid YAML in trigger templates file: {path}") from exc
    if not isinstance(loaded, dict):
        raise TriggerTemplateError("Trigger templates root must be a YAML object")
    return loaded


def load_trigger_templates(path: str | Path | None = None) -> TriggerTemplatesConfig:
    """Load and validate trigger template YAML config."""

    config_path = Path(path) if path is not None else _DEFAULT_TEMPLATES_PATH
    payload = _read_yaml(config_path)
    try:
        return TriggerTemplatesConfig.model_validate(payload)
    except ValidationError as exc:
        raise TriggerTemplateError(f"Trigger template validation failed for {config_path}") from exc


@lru_cache(maxsize=1)
def load_default_trigger_templates() -> TriggerTemplatesConfig:
    """Load and memoize default trigger template config."""

    return load_trigger_templates(_DEFAULT_TEMPLATES_PATH)


class TriggerTemplateResolver:
    """Resolve selected triggers into non-aggressive prompt orchestration metadata."""

    def __init__(self, config: TriggerTemplatesConfig | None = None) -> None:
        self.config = config or load_default_trigger_templates()

    def resolve(
        self,
        *,
        triggers: list[TriggerType],
        intensity: float,
        capacity_flags: dict[TriggerType, bool] | None = None,
    ) -> PromptOrchestrationMeta:
        """Map trigger list + intensity into safe metadata fragments."""

        if not triggers:
            raise TriggerTemplateError("At least one trigger is required for template resolution")
        if intensity < 0.0 or intensity > 1.0:
            raise TriggerTemplateError("intensity must be between 0.0 and 1.0")

        flags = capacity_flags or {}
        level = self._intensity_level(intensity)

        resolved_triggers: list[TriggerType] = []
        resolved_fragments: list[TriggerTemplateFragment] = []
        dropped_triggers: list[str] = []
        for trigger in triggers[:2]:
            rule = self.config.templates.get(trigger)
            if rule is None:
                dropped_triggers.append(trigger.value)
                continue

            if trigger is TriggerType.SCARCITY and rule.requires_capacity_flag and not flags.get(trigger, False):
                dropped_triggers.append(trigger.value)
                continue

            fragment = self._fragment_for_level(rule=rule, level=level)
            resolved_triggers.append(trigger)
            resolved_fragments.append(fragment)

        if not resolved_triggers:
            fallback_trigger = TriggerType.TRANSPARENCY
            fallback_rule = self.config.templates.get(fallback_trigger)
            if fallback_rule is None:
                raise TriggerTemplateError("Fallback trigger template is not configured")
            resolved_triggers = [fallback_trigger]
            resolved_fragments = [self._fragment_for_level(rule=fallback_rule, level=TriggerIntensityLevel.SOFT)]
            dropped_triggers.append("all_input_triggers_filtered")

        primary = resolved_fragments[0]
        return PromptOrchestrationMeta(
            triggers=resolved_triggers,
            intensity=round(float(intensity), 4),
            intensity_level=level,
            tone=primary.tone,
            proof_style=primary.proof_style,
            cta_style=primary.cta_style,
            trigger_fragments=[fragment.fragment for fragment in resolved_fragments],
            metadata={
                "dropped_triggers": dropped_triggers,
                "capacity_checked": sorted([item.value for item in flags.keys()]),
            },
        )

    def _intensity_level(self, intensity: float) -> TriggerIntensityLevel:
        if intensity < 0.5:
            return TriggerIntensityLevel.SOFT
        if intensity < self.config.high_intensity_threshold:
            return TriggerIntensityLevel.MEDIUM
        return TriggerIntensityLevel.HIGH

    @staticmethod
    def _fragment_for_level(*, rule: TriggerTemplateRule, level: TriggerIntensityLevel) -> TriggerTemplateFragment:
        if level is TriggerIntensityLevel.SOFT:
            return rule.soft
        if level is TriggerIntensityLevel.MEDIUM:
            return rule.medium
        if not rule.allow_high or rule.high is None:
            return rule.medium
        return rule.high
