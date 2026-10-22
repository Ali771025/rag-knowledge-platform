"""Deterministic retrieval quality validation before LLM generation."""

from __future__ import annotations

from app.config.guardrails import (
    MIN_RELEVANT_DOCS_EDUCATION,
    MIN_RELEVANT_DOCS_INTRO,
    RETRIEVAL_MIN_SCORE,
    RETRIEVAL_TOP3_AVG_MIN_SCORE,
)
from app.services.guardrails.models import Document, ValidationResult
from app.services.guardrails.utils import keyword_overlap_score, normalize_text, simple_text_similarity

_EDUCATION_STATES = {"education", "qna", "explanation", "learning", "help"}
_INTRO_STATES = {"intro", "greeting", "start", "welcome"}


def validate_retrieval(
    query: str,
    retrieved_docs: list[Document],
    user_state: str | None = None,
) -> ValidationResult:
    """Validate retrieval quality with deterministic thresholds and relevance checks."""
    if not retrieved_docs:
        return ValidationResult(
            is_valid=False,
            confidence_score=0.0,
            reason="no_documents_retrieved",
            fallback_action="no_relevant_context",
        )

    doc_scores = [max(0.0, float(doc.score or 0.0)) for doc in retrieved_docs]
    max_score = max(doc_scores)
    top3_avg_score = _top3_average(doc_scores)

    if max_score < RETRIEVAL_MIN_SCORE:
        return ValidationResult(
            is_valid=False,
            confidence_score=round(max_score, 4),
            reason="max_retrieval_score_below_threshold",
            fallback_action="low_confidence",
        )

    if top3_avg_score < RETRIEVAL_TOP3_AVG_MIN_SCORE:
        return ValidationResult(
            is_valid=False,
            confidence_score=round(top3_avg_score, 4),
            reason="top3_average_score_below_threshold",
            fallback_action="low_confidence",
        )

    relevant_docs = _detect_relevant_docs(query=query, retrieved_docs=retrieved_docs)
    relevant_count = len(relevant_docs)
    required_relevant = _required_relevant_docs(user_state=user_state)
    relevance_ratio = relevant_count / max(1, min(len(retrieved_docs), 3))

    if relevant_count < required_relevant:
        if relevant_count == 0:
            return ValidationResult(
                is_valid=False,
                confidence_score=round(relevance_ratio, 4),
                reason="no_relevant_context",
                fallback_action="no_relevant_context",
            )
        if _is_off_topic_like_mismatch(query=query, retrieved_docs=retrieved_docs, relevant_docs=relevant_docs):
            return ValidationResult(
                is_valid=False,
                confidence_score=round(relevance_ratio, 4),
                reason="off_topic_like_retrieval_mismatch",
                fallback_action="off_topic",
            )
        return ValidationResult(
            is_valid=False,
            confidence_score=round(relevance_ratio, 4),
            reason="insufficient_relevant_documents",
            fallback_action="low_confidence",
        )

    confidence_score = _final_retrieval_confidence(
        max_score=max_score,
        top3_avg_score=top3_avg_score,
        relevant_count=relevant_count,
        required_relevant=required_relevant,
    )
    return ValidationResult(
        is_valid=True,
        confidence_score=confidence_score,
        reason=None,
        fallback_action=None,
    )


def _detect_relevant_docs(query: str, retrieved_docs: list[Document]) -> list[Document]:
    query_norm = normalize_text(query)
    relevant_docs: list[Document] = []

    for doc in retrieved_docs:
        doc_text = doc.content or ""
        sim = simple_text_similarity(query_norm, doc_text)
        overlap = keyword_overlap_score(query_norm, doc_text)
        score = max(0.0, float(doc.score or 0.0))

        proxy_confidence = (score * 0.6) + (sim * 0.25) + (overlap * 0.15)
        is_relevant = (
            (score >= 0.55 and (sim >= 0.18 or overlap >= 0.18))
            or (sim >= 0.30 and overlap >= 0.20)
            or (proxy_confidence >= 0.50 and (sim >= 0.12 or overlap >= 0.12))
        )
        if is_relevant:
            relevant_docs.append(doc)

    return relevant_docs


def _required_relevant_docs(user_state: str | None) -> int:
    if not user_state:
        return max(2, MIN_RELEVANT_DOCS_EDUCATION)

    normalized_state = normalize_text(user_state)
    if normalized_state in _INTRO_STATES:
        return max(1, MIN_RELEVANT_DOCS_INTRO)
    if normalized_state in _EDUCATION_STATES:
        return max(1, MIN_RELEVANT_DOCS_EDUCATION)

    return max(2, MIN_RELEVANT_DOCS_EDUCATION)


def _is_off_topic_like_mismatch(
    query: str,
    retrieved_docs: list[Document],
    relevant_docs: list[Document],
) -> bool:
    if not retrieved_docs:
        return False

    query_norm = normalize_text(query)
    top_docs = sorted(retrieved_docs, key=lambda doc: float(doc.score or 0.0), reverse=True)[:3]
    similarities = [simple_text_similarity(query_norm, doc.content or "") for doc in top_docs]
    overlaps = [keyword_overlap_score(query_norm, doc.content or "") for doc in top_docs]
    top3_scores = [max(0.0, float(doc.score or 0.0)) for doc in top_docs]

    return (
        _top3_average(top3_scores) >= RETRIEVAL_TOP3_AVG_MIN_SCORE
        and max(similarities, default=0.0) < 0.25
        and max(overlaps, default=0.0) < 0.20
        and len(relevant_docs) <= 1
    )


def _final_retrieval_confidence(
    max_score: float,
    top3_avg_score: float,
    relevant_count: int,
    required_relevant: int,
) -> float:
    relevance_factor = min(1.0, relevant_count / max(1, required_relevant))
    confidence = (max_score * 0.35) + (top3_avg_score * 0.40) + (relevance_factor * 0.25)
    return round(max(0.0, min(1.0, confidence)), 4)


def _top3_average(values: list[float]) -> float:
    if not values:
        return 0.0
    top = sorted(values, reverse=True)[:3]
    return sum(top) / len(top)
