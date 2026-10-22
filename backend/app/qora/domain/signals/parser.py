from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import ValidationError

from app.qora.config import QoraPolicyConfig, load_qora_policy
from app.qora.domain.contracts import SignalCandidate, SignalParserResult
from app.qora.domain.enums import SignalSourceType
from app.qora.domain.signals.taxonomy import SIGNAL_TAXONOMY, known_signal_codes

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SignalInput:
    user_text: str = ""
    source_type: SignalSourceType = SignalSourceType.USER_TEXT
    source_value: str | None = None
    event_type: str | None = None
    metadata: dict[str, Any] | None = None


class SignalLLM(Protocol):
    def send_prompt(
        self,
        system: str | dict[str, Any],
        messages: list[dict[str, str]] | None = None,
        context: dict[str, Any] | None = None,
        grounded: bool = False,
    ) -> str: ...


class RuleBasedSignalParser:
    def parse(self, signal_input: SignalInput) -> SignalParserResult:
        normalized = re.sub(r"\s+", " ", signal_input.user_text.strip().lower())
        event_type = (signal_input.event_type or "").strip().upper()
        signals: list[SignalCandidate] = []
        for definition in SIGNAL_TAXONOMY.values():
            keyword_hits = [keyword for keyword in definition.keywords if keyword.lower() in normalized]
            event_hit = bool(event_type and event_type in definition.event_types)
            if not keyword_hits and not event_hit:
                continue
            base = 0.72 if keyword_hits else 0.78
            strength = min(0.98, base + 0.08 * max(0, len(keyword_hits) - 1) + (0.08 if event_hit else 0.0))
            signals.append(
                SignalCandidate(
                    code=definition.code,
                    category=definition.category,
                    strength=strength,
                    source=signal_input.source_type,
                    evidence=", ".join(keyword_hits) if keyword_hits else event_type,
                    metadata={"parser": "rule", **(signal_input.metadata or {})},
                )
            )
        return SignalParserResult(
            signals=signals,
            ambiguity_score=0.0 if signals else 1.0,
            used_llm=False,
        )


class StructuredLLMSignalExtractor:
    def __init__(self, llm: SignalLLM, policy: QoraPolicyConfig | None = None) -> None:
        self.llm = llm
        self.policy = policy or load_qora_policy()

    def extract(self, signal_input: SignalInput) -> SignalParserResult:
        errors: list[str] = []
        for attempt in range(self.policy.llm.max_retries + 1):
            try:
                raw = self.llm.send_prompt(
                    system=(
                        "Extract only supported QORA signals. Return JSON with keys signals, "
                        "intent_candidates, ambiguity_score. Never infer product facts or persona. "
                        f"Allowed signal codes: {', '.join(known_signal_codes())}."
                    ),
                    messages=[{"role": "user", "content": signal_input.user_text}],
                    context={"event_type": signal_input.event_type, "metadata": signal_input.metadata or {}},
                    grounded=False,
                )
                payload = self._decode_json(raw)
                result = SignalParserResult.model_validate(payload)
                for candidate in result.signals:
                    definition = SIGNAL_TAXONOMY.get(candidate.code)
                    if definition is None:
                        raise ValueError(f"Unknown signal code: {candidate.code}")
                    if candidate.category != definition.category:
                        raise ValueError(f"Invalid category for signal: {candidate.code}")
                return result.model_copy(update={"used_llm": True, "errors": errors})
            except (ValueError, json.JSONDecodeError, ValidationError) as exc:
                errors.append(f"attempt_{attempt + 1}:{type(exc).__name__}")
                logger.warning("qora.signal_extraction_invalid attempt=%s error=%s", attempt + 1, type(exc).__name__)
        return SignalParserResult(used_llm=True, fallback_used=True, ambiguity_score=1.0, errors=errors)

    @staticmethod
    def _decode_json(raw: str) -> dict[str, Any]:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
        payload = json.loads(cleaned)
        if not isinstance(payload, dict):
            raise ValueError("LLM extraction must be a JSON object")
        return payload


class HybridSignalParser:
    def __init__(self, llm: SignalLLM | None = None, policy: QoraPolicyConfig | None = None) -> None:
        self.rule_parser = RuleBasedSignalParser()
        self.llm_parser = StructuredLLMSignalExtractor(llm, policy) if llm is not None else None

    def parse(self, signal_input: SignalInput) -> SignalParserResult:
        rule_result = self.rule_parser.parse(signal_input)
        if self.llm_parser is None or not signal_input.user_text.strip():
            return rule_result
        llm_result = self.llm_parser.extract(signal_input)
        merged: dict[str, SignalCandidate] = {signal.code: signal for signal in rule_result.signals}
        for signal in llm_result.signals:
            llm_signal = signal.model_copy(update={"source": SignalSourceType.LLM_EXTRACTION})
            current = merged.get(signal.code)
            if current is None or llm_signal.strength > current.strength:
                merged[signal.code] = llm_signal
        return SignalParserResult(
            signals=list(merged.values()),
            intent_candidates=list(dict.fromkeys(rule_result.intent_candidates + llm_result.intent_candidates)),
            ambiguity_score=min(rule_result.ambiguity_score, llm_result.ambiguity_score),
            used_llm=True,
            fallback_used=llm_result.fallback_used,
            errors=llm_result.errors,
        )
