"""Deterministic domain restriction checks for Eter ecosystem scope."""

from __future__ import annotations

from app.services.guardrails.constants import (
    ALLOWED_ETER_DOMAIN_KEYWORDS,
    ALLOWED_ETER_FEATURE_KEYWORDS,
    BLOCKED_TOPICS,
    COMPETITOR_KEYWORDS,
    GENERIC_BLOCKCHAIN_KEYWORDS,
    UNSAFE_ACTION_PHRASES,
)
from app.services.guardrails.models import OffTopicResult
from app.services.guardrails.utils import contains_any, normalize_text

_SOFT_OFF_TOPIC_KEYWORDS: set[str] = {
    "weather",
    "sports",
    "movie",
    "music",
    "celebrity",
    "recipe",
    "travel",
    "سرگرمی",
    "آب و هوا",
    "ورزش",
    "فیلم",
    "آشپزی",
}


def is_query_allowed(query: str) -> bool:
    """Return True when the query is in-domain and not clearly blocked."""
    result = detect_off_topic(query)
    return not result.is_off_topic


def detect_off_topic(query: str) -> OffTopicResult:
    """Detect whether a query falls outside Eter scope with confidence scoring.

    Policy:
    - Hard block: blocked topics, competitor promotion, unsafe actions.
    - In-domain: Eter entity mention and/or known Eter feature intent.
    - Generic blockchain without Eter context: off-topic (soft domain mismatch).
    - Uncertain generic requests: prefer soft penalty (low confidence) over hard block.
    """
    normalized_query = normalize_text(query)
    if not normalized_query:
        return OffTopicResult(is_off_topic=True, detected_topic="empty_query", confidence=0.95)

    blocked_matches = _find_matches(normalized_query, BLOCKED_TOPICS)
    if blocked_matches:
        return OffTopicResult(
            is_off_topic=True,
            detected_topic="blocked_topic",
            confidence=0.99,
        )

    unsafe_matches = _find_matches(normalized_query, UNSAFE_ACTION_PHRASES)
    if unsafe_matches:
        return OffTopicResult(
            is_off_topic=True,
            detected_topic="unsafe_action",
            confidence=0.99,
        )

    competitor_matches = _find_matches(normalized_query, COMPETITOR_KEYWORDS)
    if competitor_matches:
        return OffTopicResult(
            is_off_topic=True,
            detected_topic="competitor_promotion",
            confidence=0.94,
        )

    eter_domain_matches = _find_matches(normalized_query, ALLOWED_ETER_DOMAIN_KEYWORDS)
    eter_feature_matches = _find_matches(normalized_query, ALLOWED_ETER_FEATURE_KEYWORDS)
    has_eter_context = bool(eter_domain_matches)

    if has_eter_context and eter_feature_matches:
        return OffTopicResult(
            is_off_topic=False,
            detected_topic="eter_feature",
            confidence=0.93,
        )

    if has_eter_context:
        return OffTopicResult(
            is_off_topic=False,
            detected_topic="eter_general",
            confidence=0.80,
        )

    blockchain_matches = _find_matches(normalized_query, GENERIC_BLOCKCHAIN_KEYWORDS)
    if blockchain_matches:
        return OffTopicResult(
            is_off_topic=True,
            detected_topic="generic_blockchain_no_eter_context",
            confidence=0.82,
        )

    soft_off_topic_matches = _find_matches(normalized_query, _SOFT_OFF_TOPIC_KEYWORDS)
    if soft_off_topic_matches:
        return OffTopicResult(
            is_off_topic=True,
            detected_topic="general_off_topic",
            confidence=0.78,
        )

    # Uncertain queries are marked off-topic with lower confidence for soft handling.
    return OffTopicResult(
        is_off_topic=True,
        detected_topic="low_domain_confidence",
        confidence=0.55,
    )


def _find_matches(text: str, keywords: set[str]) -> list[str]:
    return contains_any(text=text, patterns=list(keywords))

