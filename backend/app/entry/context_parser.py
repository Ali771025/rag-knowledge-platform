"""Entry context parser that produces low-confidence bootstrap hints."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.entry.models import EntryContextInput, EntryContextOutput
from app.internal.conversion.policy_enums import EntryProbableIntent, EntryRiskProfileHint


@dataclass(frozen=True, slots=True)
class _Rule:
    when: dict[str, Any]
    set_values: dict[str, Any]


class EntryContextParser:
    """Parse session-entry metadata into weak behavioral hints."""

    def __init__(self, rules_path: str | Path | None = None) -> None:
        if rules_path is None:
            rules_path = Path(__file__).with_name("heuristics.yaml")
        self._rules_path = Path(rules_path)
        self._rules = self._load_rules(self._rules_path)

    def parse(self, payload: EntryContextInput) -> EntryContextOutput:
        values = self._flatten_input(payload)
        output: dict[str, Any] = {
            "referrer_type": "unknown",
            "campaign_type": "unknown",
            "probable_intent": EntryProbableIntent.EXPLORER,
            "risk_profile_hint": EntryRiskProfileHint.LOW,
            "confidence": 0.2,
            "rationale": "default low-confidence entry hint",
            "metadata": {"hint_only": True, "matched_rules": []},
        }

        matched: list[str] = []
        for index, rule in enumerate(self._rules):
            if not self._matches(rule.when, values):
                continue
            for key, value in rule.set_values.items():
                output[key] = value
            matched.append(f"rule_{index + 1}")

        confidence = 0.2 + (0.05 * len(matched))
        output["confidence"] = min(0.4, max(0.2, confidence))
        output["metadata"] = {
            **output["metadata"],
            "matched_rules": matched,
            "source": "entry_context_parser",
        }
        if matched:
            output["rationale"] = "entry hints inferred from referral/campaign metadata"

        # Explicit non-overriding marker for downstream orchestration.
        output["metadata"]["weak_bias_only"] = True

        return EntryContextOutput.model_validate(output)

    @staticmethod
    def _flatten_input(payload: EntryContextInput) -> dict[str, Any]:
        flat = payload.model_dump(mode="python")
        metadata = flat.get("metadata")
        if isinstance(metadata, dict):
            for key, value in metadata.items():
                flat.setdefault(key, value)
        return {key: EntryContextParser._normalize(value) for key, value in flat.items()}

    @staticmethod
    def _normalize(value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @staticmethod
    def _matches(conditions: dict[str, Any], values: dict[str, Any]) -> bool:
        for key, expected in conditions.items():
            actual = values.get(key)
            if isinstance(expected, list):
                expected_tokens = {str(item).strip().lower() for item in expected}
                if str(actual).strip().lower() not in expected_tokens:
                    return False
                continue
            if str(actual).strip().lower() != str(expected).strip().lower():
                return False
        return True

    @staticmethod
    def _load_rules(path: Path) -> list[_Rule]:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        rules_raw = raw.get("rules", [])
        rules: list[_Rule] = []
        for item in rules_raw:
            when = item.get("when", {}) if isinstance(item, dict) else {}
            set_values = item.get("set", {}) if isinstance(item, dict) else {}
            if isinstance(when, dict) and isinstance(set_values, dict):
                rules.append(_Rule(when=when, set_values=set_values))
        return rules


class ContextEnricher:
    """Attach entry context hints into orchestration metadata as weak bias only."""

    @staticmethod
    def enrich(metadata: dict[str, Any], entry_context: EntryContextOutput) -> dict[str, Any]:
        payload = dict(metadata)
        payload["entry_context"] = entry_context.model_dump(mode="json")
        payload["entry_context"]["weak_bias_only"] = True
        return payload
