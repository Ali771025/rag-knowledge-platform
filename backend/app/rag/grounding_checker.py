"""Heuristic grounding validation against retrieved evidence."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.rag.models.rag_types import ConfidenceLevel
from app.rag.schemas.context import RAGContextBundle
from app.rag.schemas.response import GroundingCheckResult
from app.rag.text_normalization import normalize_text, tokenize


class GroundingCheckInput(BaseModel):
    """Input payload for answer grounding validation."""

    answer: str = Field(min_length=1)
    context_bundle: RAGContextBundle
    min_support_ratio: float = Field(default=0.6, ge=0.0, le=1.0)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class GroundingChecker:
    """Checks whether answer claims are sufficiently supported by context."""

    def check(self, payload: GroundingCheckInput) -> GroundingCheckResult:
        """Produce grounding result from answer/context overlap heuristics."""
        claims = self._extract_claims(payload.answer)
        evidence_texts = self._collect_evidence_texts(payload.context_bundle)
        checked_citations = self._collect_citation_ids(payload.context_bundle)

        if not claims:
            return GroundingCheckResult(
                is_grounded=False,
                confidence_level=ConfidenceLevel.LOW,
                checked_citation_ids=checked_citations,
                unsupported_claims=[payload.answer[:160]],
                notes="No analyzable claims detected; fallback_or_warning_recommended=true",
            )

        unsupported: list[str] = []
        supported_count = 0
        for claim in claims:
            if self._is_supported(claim=claim, evidence_texts=evidence_texts):
                supported_count += 1
            else:
                unsupported.append(claim)

        support_ratio = supported_count / len(claims)
        is_grounded = support_ratio >= payload.min_support_ratio and len(unsupported) <= max(1, len(claims) // 3)
        confidence = self._confidence_from_ratio(support_ratio=support_ratio, unsupported_count=len(unsupported), total=len(claims))

        notes = (
            f"support_ratio={support_ratio:.3f}; claims={len(claims)}; "
            f"unsupported={len(unsupported)}; "
            f"fallback_or_warning_recommended={'true' if not is_grounded else 'false'}"
        )

        return GroundingCheckResult(
            is_grounded=is_grounded,
            confidence_level=confidence,
            checked_citation_ids=checked_citations,
            unsupported_claims=unsupported[:12],
            notes=notes,
        )

    def should_fallback(self, result: GroundingCheckResult) -> bool:
        """Indicate whether fallback answer mode should be used."""
        if result.is_grounded:
            return False
        return result.confidence_level in {ConfidenceLevel.VERY_LOW, ConfidenceLevel.LOW}

    def should_warn(self, result: GroundingCheckResult) -> bool:
        """Indicate whether response should include grounding warning."""
        return (not result.is_grounded) or bool(result.unsupported_claims)

    def _extract_claims(self, answer: str) -> list[str]:
        raw_parts = re.split(r"[\n\r]+|(?<=[.!?؟])\s+", answer.strip())
        claims: list[str] = []
        for part in raw_parts:
            text = " ".join(part.split())
            if len(text) < 20:
                continue
            claims.append(text)
        return claims[:40]

    def _collect_evidence_texts(self, bundle: RAGContextBundle) -> list[str]:
        evidence: list[str] = []
        for chunk in bundle.chunks:
            evidence.append(chunk.content)
        for fact in bundle.facts:
            evidence.append(f"{fact.subject} {fact.predicate} {fact.obj}")
        for graph in bundle.graph_evidence:
            evidence.append(graph.path_summary)
        return [item for item in evidence if item.strip()]

    def _collect_citation_ids(self, bundle: RAGContextBundle) -> list[str]:
        citation_ids: set[str] = set()
        for item in [*bundle.chunks, *bundle.facts, *bundle.graph_evidence]:
            metadata = dict(getattr(item, "metadata", None) or {})
            citation = metadata.get("citation_id")
            if citation:
                citation_ids.add(str(citation))
        return sorted(citation_ids)

    def _is_supported(self, *, claim: str, evidence_texts: list[str]) -> bool:
        normalized_claim = self._normalize_text(claim)
        claim_tokens = self._tokenize(claim)
        if not claim_tokens:
            return False

        best_overlap = 0.0
        for evidence in evidence_texts:
            normalized_evidence = self._normalize_text(evidence)
            if normalized_claim and normalized_claim in normalized_evidence:
                return True

            evidence_tokens = self._tokenize(evidence)
            if not evidence_tokens:
                continue

            # Token containment catches paraphrases where Jaccard is too harsh on short claims.
            containment = len(claim_tokens & evidence_tokens) / max(1, len(claim_tokens))
            if containment >= 0.55:
                return True

            overlap = self._jaccard(claim_tokens, evidence_tokens)
            if overlap > best_overlap:
                best_overlap = overlap
            if best_overlap >= 0.32:
                return True

        has_numeric_claim = bool(re.search(r"\b\d+(?:\.\d+)?\b", claim))
        threshold = 0.24 if has_numeric_claim else 0.18
        return best_overlap >= threshold

    def _confidence_from_ratio(self, *, support_ratio: float, unsupported_count: int, total: int) -> ConfidenceLevel:
        if total <= 0:
            return ConfidenceLevel.VERY_LOW
        if support_ratio >= 0.9 and unsupported_count == 0:
            return ConfidenceLevel.VERY_HIGH
        if support_ratio >= 0.75:
            return ConfidenceLevel.HIGH
        if support_ratio >= 0.55:
            return ConfidenceLevel.MEDIUM
        if support_ratio >= 0.35:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.VERY_LOW

    def _tokenize(self, text: str) -> set[str]:
        return set(tokenize(text))

    def _jaccard(self, left: set[str], right: set[str]) -> float:
        if not left or not right:
            return 0.0
        intersection = len(left & right)
        union = len(left | right)
        if union == 0:
            return 0.0
        return intersection / union

    def _normalize_text(self, text: str) -> str:
        return " ".join(tokenize(normalize_text(text)))
