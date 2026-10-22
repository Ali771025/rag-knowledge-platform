"""Deterministic persona signal extraction from message text and metadata."""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from app.internal.persona.signal_models import ExtractedPersonaSignals, PersonaSignal


def _normalize_text(message: str) -> str:
    return re.sub(r"\s+", " ", message.strip().lower())


def _keyword_hits(text: str, keywords: Sequence[str]) -> tuple[int, list[str]]:
    hits: list[str] = []
    total = 0
    for keyword in keywords:
        pattern = re.compile(rf"\b{re.escape(keyword.lower())}\b")
        count = len(pattern.findall(text))
        if count > 0:
            total += count
            hits.append(keyword)
    return total, hits


def _normalize_count(count: int, cap: int) -> float:
    if cap <= 0:
        return 0.0
    return min(1.0, float(count) / float(cap))


def _metadata_number(metadata: Mapping[str, Any], key: str) -> float:
    value = metadata.get(key)
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def extract_persona_signals(
    message: str,
    metadata: Mapping[str, Any] | None = None,
    *,
    hesitation_terms: Sequence[str],
    proof_terms: Sequence[str],
    roi_terms: Sequence[str],
    analytical_terms: Sequence[str],
    urgency_terms: Sequence[str],
    gamification_terms: Sequence[str],
    lexical_terms: Sequence[str],
    keyword_cap: int = 3,
    metadata_weights: Mapping[str, float] | None = None,
) -> ExtractedPersonaSignals:
    """Extract normalized persona signals from text plus optional metadata cues."""

    normalized = _normalize_text(message)
    safe_metadata = metadata or {}

    lexical_count, lexical_hits = _keyword_hits(normalized, lexical_terms)
    hesitation_count, hesitation_hits = _keyword_hits(normalized, hesitation_terms)
    proof_count, proof_hits = _keyword_hits(normalized, proof_terms)
    roi_count, roi_hits = _keyword_hits(normalized, roi_terms)
    analytical_count, analytical_hits = _keyword_hits(normalized, analytical_terms)
    urgency_count, urgency_hits = _keyword_hits(normalized, urgency_terms)
    gamification_count, gamification_hits = _keyword_hits(normalized, gamification_terms)

    question_bonus = 0.2 if "?" in message else 0.0
    long_message_bonus = 0.15 if len(normalized.split(" ")) >= 15 else 0.0

    weights = dict(metadata_weights or {})
    persistence_value = _metadata_number(safe_metadata, "follow_up_count")
    session_messages = _metadata_number(safe_metadata, "messages_in_session")
    returning_user = _metadata_number(safe_metadata, "returning_user")
    intent_events = _metadata_number(safe_metadata, "intent_events")

    metadata_weight_sum = sum(max(0.0, value) for value in weights.values()) or 1.0
    metadata_signal = (
        max(0.0, weights.get("follow_up_count", 0.5)) * min(1.0, persistence_value / 3.0)
        + max(0.0, weights.get("messages_in_session", 0.3)) * min(1.0, session_messages / 6.0)
        + max(0.0, weights.get("returning_user", 0.1)) * min(1.0, returning_user)
        + max(0.0, weights.get("intent_events", 0.1)) * min(1.0, intent_events / 2.0)
    ) / metadata_weight_sum

    engagement_persistence = min(
        1.0,
        _normalize_count(int(persistence_value), 3)
        + min(0.5, _normalize_count(int(session_messages), 6) * 0.5)
        + long_message_bonus,
    )

    signals = {
        PersonaSignal.LEXICAL_ENGAGEMENT: min(1.0, _normalize_count(lexical_count, keyword_cap) + long_message_bonus),
        PersonaSignal.HESITATION: min(1.0, _normalize_count(hesitation_count, keyword_cap) + question_bonus),
        PersonaSignal.PROOF_SEEKING: min(1.0, _normalize_count(proof_count, keyword_cap) + question_bonus),
        PersonaSignal.ROI_SEEKING: _normalize_count(roi_count, keyword_cap),
        PersonaSignal.ANALYTICAL_DEPTH: min(1.0, _normalize_count(analytical_count, keyword_cap) + question_bonus),
        PersonaSignal.URGENCY: _normalize_count(urgency_count, keyword_cap),
        PersonaSignal.GAMIFICATION_AFFINITY: _normalize_count(gamification_count, keyword_cap),
        PersonaSignal.ENGAGEMENT_PERSISTENCE: engagement_persistence,
        PersonaSignal.METADATA_BEHAVIORAL: min(1.0, max(0.0, metadata_signal)),
    }

    evidence = {
        PersonaSignal.LEXICAL_ENGAGEMENT: tuple(lexical_hits),
        PersonaSignal.HESITATION: tuple(hesitation_hits),
        PersonaSignal.PROOF_SEEKING: tuple(proof_hits),
        PersonaSignal.ROI_SEEKING: tuple(roi_hits),
        PersonaSignal.ANALYTICAL_DEPTH: tuple(analytical_hits),
        PersonaSignal.URGENCY: tuple(urgency_hits),
        PersonaSignal.GAMIFICATION_AFFINITY: tuple(gamification_hits),
        PersonaSignal.ENGAGEMENT_PERSISTENCE: (),
        PersonaSignal.METADATA_BEHAVIORAL: tuple(key for key in safe_metadata.keys() if key in weights),
    }

    return ExtractedPersonaSignals(message=message, signals=signals, evidence=evidence)
