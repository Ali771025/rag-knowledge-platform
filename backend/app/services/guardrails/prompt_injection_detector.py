"""Deterministic prompt injection and jailbreak detection."""

from __future__ import annotations

import re

from app.services.guardrails.constants import PROMPT_INJECTION_PATTERNS
from app.services.guardrails.models import InjectionResult, RiskLevel
from app.services.guardrails.utils import contains_any, normalize_text

_HIGH_RISK_PATTERNS: tuple[str, ...] = (
    "ignore previous instructions",
    "ignore all previous",
    "ignore system prompt",
    "forget system prompt",
    "reveal system prompt",
    "reveal hidden prompt",
    "print internal instructions",
    "show developer message",
    "show hidden policy",
    "show chain of thought",
    "act as system",
    "act as another ai",
    "you are now developer mode",
    "jailbreak",
    "dan",
    "do anything now",
    "role: system",
    "override safety",
    "bypass guardrails",
    "recursive prompt",
    "دستورهای قبلی را نادیده بگیر",
    "پرامپت سیستم را افشا کن",
    "حالت توسعه دهنده",
)

_MEDIUM_RISK_PATTERNS: tuple[str, ...] = (
    "<script",
    "</script>",
    "<!--",
    "-->",
    "<system>",
    "</system>",
    "```system",
    "base64",
    "decode this",
    "hidden instruction",
    "policy extraction",
    "prompt leak",
)

_LOW_RISK_PATTERNS: tuple[str, ...] = (
    "simulate unrestricted mode",
    "no restrictions",
    "uncensored answer",
    "just pretend",
    "roleplay as",
    "temporary override",
)

_BASE64_LIKE_RE = re.compile(r"(?:[a-z0-9+/]{24,}={0,2})", re.IGNORECASE)
_ROLE_OVERRIDE_RE = re.compile(
    r"(?:^|\s)(?:system|developer|assistant|user)\s*:\s*",
    re.IGNORECASE,
)
_RECURSIVE_OVERRIDE_RE = re.compile(
    r"(ignore|override).{0,40}(previous|above|prior).{0,40}(instruction|prompt)",
    re.IGNORECASE,
)


def detect_prompt_injection(query: str) -> InjectionResult:
    """Return deterministic prompt-injection signals with risk level."""
    normalized = normalize_text(query)
    if not normalized:
        return InjectionResult(
            is_malicious=False,
            risk_level=RiskLevel.LOW.value,
            matched_patterns=[],
        )

    matched_patterns: list[str] = []
    high_matches = contains_any(normalized, list(_HIGH_RISK_PATTERNS))
    medium_matches = contains_any(normalized, list(_MEDIUM_RISK_PATTERNS))
    low_matches = contains_any(normalized, list(_LOW_RISK_PATTERNS))
    shared_matches = contains_any(normalized, PROMPT_INJECTION_PATTERNS)

    if high_matches:
        matched_patterns.extend(high_matches)
    if medium_matches:
        matched_patterns.extend(medium_matches)
    if low_matches:
        matched_patterns.extend(low_matches)
    if shared_matches:
        matched_patterns.extend(shared_matches)

    regex_medium_hits = _regex_suspicious_hits(normalized)
    if regex_medium_hits:
        matched_patterns.extend(regex_medium_hits)

    deduped = _dedupe(matched_patterns)
    risk_level = _classify_risk(
        normalized=normalized,
        high_matches=high_matches,
        medium_matches=medium_matches + regex_medium_hits,
        low_matches=low_matches,
        shared_matches=shared_matches,
    )

    return InjectionResult(
        is_malicious=bool(deduped),
        risk_level=risk_level,
        matched_patterns=deduped,
    )


def _regex_suspicious_hits(text: str) -> list[str]:
    hits: list[str] = []
    if _BASE64_LIKE_RE.search(text):
        hits.append("base64_like_payload")
    if _ROLE_OVERRIDE_RE.search(text):
        hits.append("role_override_syntax")
    if _RECURSIVE_OVERRIDE_RE.search(text):
        hits.append("recursive_override_phrase")
    return hits


def _classify_risk(
    normalized: str,
    high_matches: list[str],
    medium_matches: list[str],
    low_matches: list[str],
    shared_matches: list[str],
) -> str:
    if high_matches:
        return RiskLevel.HIGH.value

    if medium_matches:
        return RiskLevel.MEDIUM.value

    if shared_matches and (
        "jailbreak" in normalized
        or "developer mode" in normalized
        or "پرامپت سیستم" in normalized
    ):
        return RiskLevel.HIGH.value

    if low_matches or shared_matches:
        return RiskLevel.LOW.value

    return RiskLevel.LOW.value


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output

