"""Deterministic output filtering before returning responses to users."""

from __future__ import annotations

import re

from app.services.guardrails.constants import (
    ALLOWED_ETER_DOMAIN_KEYWORDS,
    ALLOWED_ETER_FEATURE_KEYWORDS,
    COMPETITOR_KEYWORDS,
    FABRICATION_UNCERTAINTY_PHRASES,
    FALLBACK_MESSAGES,
    FORBIDDEN_OUTPUT_ACTION_PHRASES,
    GENERIC_BLOCKCHAIN_KEYWORDS,
    PROMPT_INJECTION_PATTERNS,
    UNSAFE_ACTION_PHRASES,
    UNSAFE_OUTPUT_PATTERNS,
)
from app.services.guardrails.models import Document, OutputValidationResult
from app.services.guardrails.utils import (
    contains_any,
    extract_numbers,
    normalize_text,
    simple_text_similarity,
    split_into_claims,
)

_PERSIAN_CHAR_RE = re.compile(r"[\u0600-\u06ff]")
_DATE_RE = re.compile(r"\b(?:19|20)\d{2}\b")
_FEATURE_EXISTENCE_MARKERS = {
    "has",
    "have",
    "supports",
    "support",
    "available",
    "exists",
    "can do",
    "includes",
    "است",
    "هست",
    "دارد",
    "وجود دارد",
    "در دسترس",
}


def validate_output(
    user_query: str,
    llm_response: str,
    retrieved_context: list[Document],
) -> OutputValidationResult:
    """Validate and filter LLM output using deterministic guardrail checks."""
    response_norm = normalize_text(llm_response)
    violations: list[str] = []

    domain_violations = _check_domain_violations(response_norm=response_norm)
    if domain_violations:
        violations.extend(domain_violations)

    fabrication_violations = _check_fabrication_violations(
        response_text=response_norm,
        retrieved_context=retrieved_context,
    )
    if fabrication_violations:
        violations.extend(fabrication_violations)

    forbidden_action_violations = _check_forbidden_action_violations(response_norm=response_norm)
    if forbidden_action_violations:
        violations.extend(forbidden_action_violations)

    unsafe_violations = _check_unsafe_output_violations(response_norm=response_norm)
    if unsafe_violations:
        violations.extend(unsafe_violations)

    deduped_violations = _dedupe(violations)
    if deduped_violations:
        language = _detect_language(user_query=user_query, response=llm_response)
        fallback = FALLBACK_MESSAGES["unsafe_output"][language]
        return OutputValidationResult(
            is_safe=False,
            confidence_score=_confidence_from_violations(deduped_violations),
            violations=deduped_violations,
            filtered_response=fallback,
        )

    return OutputValidationResult(
        is_safe=True,
        confidence_score=1.0,
        violations=[],
        filtered_response=llm_response,
    )


def _check_domain_violations(response_norm: str) -> list[str]:
    violations: list[str] = []
    competitor_matches = contains_any(response_norm, list(COMPETITOR_KEYWORDS))
    if competitor_matches:
        violations.append("domain_competitor_focused_response")

    has_eter = bool(contains_any(response_norm, list(ALLOWED_ETER_DOMAIN_KEYWORDS)))
    has_blockchain = bool(contains_any(response_norm, list(GENERIC_BLOCKCHAIN_KEYWORDS)))
    if has_blockchain and not has_eter:
        violations.append("domain_generic_blockchain_without_eter_context")

    # If the response clearly drifts from platform and feature space, mark domain drift.
    has_eter_feature = bool(contains_any(response_norm, list(ALLOWED_ETER_FEATURE_KEYWORDS)))
    if not has_eter and not has_eter_feature and has_blockchain:
        violations.append("domain_drift_outside_eter")

    return violations


def _check_fabrication_violations(
    response_text: str,
    retrieved_context: list[Document],
) -> list[str]:
    violations: list[str] = []
    context_blob = normalize_text(" ".join(doc.content or "" for doc in retrieved_context))
    context_numbers = set(extract_numbers(context_blob))
    context_dates = set(_DATE_RE.findall(context_blob))

    uncertainty_hits = contains_any(response_text, list(FABRICATION_UNCERTAINTY_PHRASES))
    if uncertainty_hits:
        violations.append("fabrication_uncertainty_phrase")

    response_numbers = extract_numbers(response_text)
    if response_numbers:
        unsupported_numbers = [number for number in response_numbers if number not in context_numbers]
        if unsupported_numbers:
            violations.append("fabrication_unsupported_numbers")

    response_dates = _DATE_RE.findall(response_text)
    if response_dates:
        unsupported_dates = [date for date in response_dates if date not in context_dates]
        if unsupported_dates:
            violations.append("fabrication_unsupported_dates")

    claims = split_into_claims(response_text)
    for claim in claims:
        if _is_feature_existence_claim(claim) and not _claim_supported_by_context(claim, retrieved_context):
            violations.append("fabrication_unsupported_feature_claim")
            break

    return violations


def _check_forbidden_action_violations(response_norm: str) -> list[str]:
    violations: list[str] = []
    if contains_any(response_norm, list(FORBIDDEN_OUTPUT_ACTION_PHRASES)):
        violations.append("forbidden_phase1_action_claim")
    return violations


def _check_unsafe_output_violations(response_norm: str) -> list[str]:
    violations: list[str] = []
    if contains_any(response_norm, list(UNSAFE_OUTPUT_PATTERNS)):
        violations.append("unsafe_prompt_or_policy_leakage")
    if contains_any(response_norm, PROMPT_INJECTION_PATTERNS):
        violations.append("unsafe_jailbreak_echo")
    if contains_any(response_norm, list(UNSAFE_ACTION_PHRASES)):
        violations.append("unsafe_operational_claim")
    return violations


def _is_feature_existence_claim(claim: str) -> bool:
    has_feature_keyword = bool(contains_any(claim, list(ALLOWED_ETER_FEATURE_KEYWORDS)))
    has_existence_marker = bool(contains_any(claim, list(_FEATURE_EXISTENCE_MARKERS)))
    return has_feature_keyword and has_existence_marker


def _claim_supported_by_context(claim: str, retrieved_context: list[Document]) -> bool:
    if not retrieved_context:
        return False
    max_similarity = 0.0
    for doc in retrieved_context:
        max_similarity = max(max_similarity, simple_text_similarity(claim, doc.content or ""))
    return max_similarity >= 0.28


def _detect_language(user_query: str, response: str) -> str:
    combined = f"{user_query} {response}"
    if _PERSIAN_CHAR_RE.search(combined):
        return "fa"
    return "en"


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def _confidence_from_violations(violations: list[str]) -> float:
    if not violations:
        return 1.0
    confidence = 1.0 - min(0.9, len(violations) * 0.2)
    return round(max(0.0, confidence), 4)
