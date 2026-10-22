"""Deterministic grounding verification against retrieved context."""

from __future__ import annotations

from app.config.guardrails import GROUNDING_MIN_SCORE
from app.services.guardrails.constants import ALLOWED_ETER_FEATURE_KEYWORDS
from app.services.guardrails.models import Document, GroundingResult
from app.services.guardrails.utils import (
    extract_numbers,
    keyword_overlap_score,
    normalize_text,
    simple_text_similarity,
    split_into_claims,
    tokenize_text,
)

_SAFE_SHORT_PATTERNS = {
    "سلام",
    "hello",
    "hi",
    "how can i help",
    "چطور می توانم کمک کنم",
    "لطفا سوال",
    "please clarify",
}
_EXISTENCE_CLAIM_MARKERS = {
    "has",
    "have",
    "supports",
    "support",
    "available",
    "exists",
    "can do",
    "includes",
    "قابلیت",
    "امکان",
    "پشتیبانی",
    "وجود دارد",
    "در دسترس",
}


def verify_grounding(response: str, retrieved_docs: list[Document]) -> GroundingResult:
    """Verify whether response claims are supported by retrieved documents."""
    claims = split_into_claims(response)
    if not claims:
        return GroundingResult(is_grounded=True, unsupported_claims=[], grounding_score=1.0)

    if _is_safe_non_factual_response(response=response, claims=claims):
        return GroundingResult(is_grounded=True, unsupported_claims=[], grounding_score=1.0)

    docs_text = [normalize_text(doc.content or "") for doc in retrieved_docs]
    docs_blob = " ".join(docs_text).strip()
    docs_numbers = set(extract_numbers(docs_blob))

    if not docs_text:
        factual_claims = [claim for claim in claims if _is_factual_claim(claim)]
        if factual_claims:
            return GroundingResult(
                is_grounded=False,
                unsupported_claims=factual_claims,
                grounding_score=0.0,
            )
        return GroundingResult(is_grounded=True, unsupported_claims=[], grounding_score=1.0)

    unsupported_claims: list[str] = []
    claim_scores: list[float] = []
    unsupported_number_count = 0

    for claim in claims:
        max_similarity = max(simple_text_similarity(claim, doc_text) for doc_text in docs_text)
        max_overlap = max(keyword_overlap_score(claim, doc_text) for doc_text in docs_text)
        support_score = (max_similarity * 0.65) + (max_overlap * 0.35)

        claim_numbers = extract_numbers(claim)
        has_unsupported_number = any(number not in docs_numbers for number in claim_numbers)
        unsupported_feature_claim = _is_unsupported_feature_claim(claim, max_similarity, max_overlap)

        if has_unsupported_number:
            unsupported_number_count += 1
            support_score = min(support_score, 0.10)

        if unsupported_feature_claim:
            support_score = min(support_score, 0.20)

        is_supported = (
            support_score >= 0.38
            and not has_unsupported_number
            and not unsupported_feature_claim
        )
        if not is_supported and _is_factual_claim(claim):
            unsupported_claims.append(claim)

        claim_scores.append(support_score)

    if not claim_scores:
        grounding_score = 1.0
    else:
        grounding_score = sum(claim_scores) / len(claim_scores)
        if unsupported_number_count:
            grounding_score -= min(0.45, unsupported_number_count * 0.18)

    grounding_score = round(max(0.0, min(1.0, grounding_score)), 4)
    return GroundingResult(
        is_grounded=grounding_score >= GROUNDING_MIN_SCORE,
        unsupported_claims=unsupported_claims,
        grounding_score=grounding_score,
    )


def _is_safe_non_factual_response(response: str, claims: list[str]) -> bool:
    normalized_response = normalize_text(response)
    if len(tokenize_text(normalized_response)) > 12:
        return False
    if any(marker in normalized_response for marker in _SAFE_SHORT_PATTERNS):
        return True
    return all(not _is_factual_claim(claim) for claim in claims)


def _is_factual_claim(claim: str) -> bool:
    normalized_claim = normalize_text(claim)
    if not normalized_claim:
        return False
    if extract_numbers(normalized_claim):
        return True
    tokens = tokenize_text(normalized_claim)
    if len(tokens) <= 2:
        return False
    factual_markers = {"is", "are", "has", "have", "will", "can", "است", "هست", "دارد", "می تواند"}
    return any(marker in tokens for marker in factual_markers)


def _is_unsupported_feature_claim(claim: str, max_similarity: float, max_overlap: float) -> bool:
    normalized_claim = normalize_text(claim)
    has_feature_keyword = any(keyword in normalized_claim for keyword in ALLOWED_ETER_FEATURE_KEYWORDS)
    has_existence_marker = any(marker in normalized_claim for marker in _EXISTENCE_CLAIM_MARKERS)
    return has_feature_keyword and has_existence_marker and (
        max_similarity < 0.26 or max_overlap < 0.20
    )

