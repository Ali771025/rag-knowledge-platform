from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class SignalWindowConfig(BaseModel):
    short_term_turns: int = Field(ge=10, le=20)
    behavioral_days: int = Field(ge=1, le=365)
    stable_signal_categories: list[str]
    default_ttl_hours: int = Field(ge=1)


class ScoringConfig(BaseModel):
    decay: float = Field(ge=0.0, le=1.0)
    textual_weight: float = Field(ge=0.0)
    behavioral_weight: float = Field(ge=0.0)
    consistency_bonus: float = Field(ge=0.0)
    contradiction_penalty: float = Field(ge=0.0)
    confidence_threshold: float = Field(ge=0.0, le=1.0)
    top_margin_threshold: float = Field(ge=0.0, le=1.0)
    minimum_transition_evidence: int = Field(ge=2)
    transition_score_ratio: float = Field(ge=1.0)


class ModifierRuleConfig(BaseModel):
    activation_threshold: float = Field(ge=0.0, le=1.0)
    deactivation_threshold: float = Field(ge=0.0, le=1.0)
    minimum_duration_turns: int = Field(ge=1)
    effect: str


class LLMExtractionConfig(BaseModel):
    max_retries: int = Field(ge=0, le=3)
    timeout_seconds: float = Field(gt=0.0, le=30.0)


class AchievementPolicyConfig(BaseModel):
    readiness_threshold: float = Field(ge=0.0, le=1.0)
    referral_rule_version: str = Field(min_length=1, max_length=32)
    completion_event_types: list[str] = Field(min_length=1)
    level_threshold_semantics: str = Field(min_length=1, max_length=64)


class QoraPolicyConfig(BaseModel):
    signal_windows: SignalWindowConfig
    scoring: ScoringConfig
    confidence_weights: dict[str, float]
    signal_weights: dict[str, float]
    modifier_rules: dict[str, ModifierRuleConfig]
    llm: LLMExtractionConfig
    achievement: AchievementPolicyConfig

    model_config = ConfigDict(extra="forbid")


@lru_cache(maxsize=4)
def load_qora_policy(path: str | None = None) -> QoraPolicyConfig:
    configured = path or os.getenv("QORA_POLICY_PATH")
    policy_path = Path(configured) if configured else Path(__file__).with_name("default_policy.json")
    return QoraPolicyConfig.model_validate(json.loads(policy_path.read_text(encoding="utf-8")))
