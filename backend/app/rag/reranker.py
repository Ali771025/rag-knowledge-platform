"""Context-aware reranking for heterogeneous retrieval candidates."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.conversation_memory.models import ConversationContext, ConversationState
from app.rag.schemas.context import RAGContextBundle
from app.rag.schemas.retrieval import GraphEvidence, RetrievedChunk, RetrievedFact
from app.rag.text_normalization import normalize_text, unique_tokens


class EvidenceType(str, Enum):
    """Supported evidence candidate kinds."""

    CHUNK = "chunk"
    FACT = "fact"
    GRAPH_EVIDENCE = "graph_evidence"


class RerankedEvidenceItem(BaseModel):
    """Normalized reranked candidate entry."""

    evidence_type: EvidenceType
    evidence_id: str
    source_id: str
    document_id: str | None = None
    content: str
    score: float = Field(ge=0.0, le=1.0)
    rank: int | None = Field(default=None, ge=1)
    components: dict[str, float] = Field(default_factory=dict)
    candidate: RetrievedChunk | RetrievedFact | GraphEvidence

    model_config = ConfigDict(extra="forbid")


class RerankInput(BaseModel):
    """Input payload for reranking."""

    query: str = Field(min_length=1)
    candidate_pool: RAGContextBundle
    top_n: int = Field(default=24, ge=1, le=200)
    conversation_context: ConversationContext | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RerankResult(BaseModel):
    """Reranking result payload."""

    items: list[RerankedEvidenceItem] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class RerankingBackend(Protocol):
    """Pluggable reranking backend interface."""

    def score(
        self,
        *,
        query: str,
        candidates: list[RerankedEvidenceItem],
        conversation_context: ConversationContext | None,
    ) -> list[tuple[float, dict[str, float]]]:
        """Return `(score, components)` for each candidate."""


class HeuristicRerankingBackend:
    """Deterministic heuristic reranking backend."""

    _QUALITY_BY_SOURCE_TYPE = {
        "docs": 0.95,
        "file": 0.9,
        "web": 0.72,
        "discord": 0.58,
    }

    _ONBOARDING_STATE_TERMS = {
        ConversationState.START: {"welcome", "overview", "intro", "onboarding"},
        ConversationState.INTRO: {"introduction", "overview", "goal", "scope", "structure"},
        ConversationState.EDUCATION: {"learn", "step", "tutorial", "explain", "education"},
        ConversationState.QNA: {"question", "answer", "faq", "clarify", "help"},
        ConversationState.JOIN: {"join", "signup", "register", "next", "participate"},
    }

    def score(
        self,
        *,
        query: str,
        candidates: list[RerankedEvidenceItem],
        conversation_context: ConversationContext | None,
    ) -> list[tuple[float, dict[str, float]]]:
        query_terms = self._tokenize(query)
        query_phrase = normalize_text(query)

        output: list[tuple[float, dict[str, float]]] = []
        for candidate in candidates:
            relevance = self._relevance_score(query_terms=query_terms, query_phrase=query_phrase, content=candidate.content)
            recency = self._recency_score(candidate.candidate)
            source_quality = self._source_quality_score(candidate.candidate)
            onboarding = self._onboarding_relevance_score(candidate=candidate, context=conversation_context)

            score = (relevance * 0.55) + (recency * 0.15) + (source_quality * 0.2) + (onboarding * 0.1)
            clipped = round(max(0.0, min(1.0, score)), 6)
            components = {
                "relevance": round(relevance, 6),
                "recency": round(recency, 6),
                "source_quality": round(source_quality, 6),
                "onboarding_relevance": round(onboarding, 6),
            }
            output.append((clipped, components))
        return output

    def _relevance_score(self, *, query_terms: list[str], query_phrase: str, content: str) -> float:
        text = normalize_text(content)
        if not query_terms:
            return 0.0

        hit_count = sum(1 for term in query_terms if term in text)
        coverage = hit_count / len(query_terms)
        phrase_boost = 0.25 if query_phrase and query_phrase in text else 0.0

        density_hits = sum(text.count(term) for term in query_terms)
        density_bonus = min(0.2, density_hits / 60.0)
        return max(0.0, min(1.0, coverage + phrase_boost + density_bonus))

    def _recency_score(self, candidate: RetrievedChunk | RetrievedFact | GraphEvidence) -> float:
        metadata = dict(getattr(candidate, "metadata", None) or {})
        timestamp = self._extract_timestamp(metadata)
        if timestamp is None:
            return 0.5

        now = datetime.now(timezone.utc)
        delta_days = max(0.0, (now - timestamp).total_seconds() / 86_400.0)
        return max(0.0, min(1.0, math.exp(-delta_days / 180.0)))

    def _source_quality_score(self, candidate: RetrievedChunk | RetrievedFact | GraphEvidence) -> float:
        metadata = dict(getattr(candidate, "metadata", None) or {})
        source_type = str(metadata.get("source_type") or "").strip().lower()
        if not source_type:
            source_uri = str(getattr(candidate, "source_uri", "") or "").lower()
            if "docs" in source_uri:
                source_type = "docs"
            elif "discord" in source_uri:
                source_type = "discord"
            elif source_uri.startswith("http"):
                source_type = "web"
        return self._QUALITY_BY_SOURCE_TYPE.get(source_type, 0.7)

    def _onboarding_relevance_score(self, *, candidate: RerankedEvidenceItem, context: ConversationContext | None) -> float:
        if context is None:
            return 0.5

        terms = self._ONBOARDING_STATE_TERMS.get(context.state)
        if not terms:
            return 0.5

        lowered = candidate.content.lower()
        hits = sum(1 for term in terms if term in lowered)
        if hits == 0:
            return 0.35
        return min(1.0, 0.35 + (hits * 0.15))

    def _extract_timestamp(self, metadata: dict[str, Any]) -> datetime | None:
        for key in ("updated_at", "created_at", "timestamp", "ingested_at"):
            value = metadata.get(key)
            if not value:
                continue
            parsed = self._parse_datetime(value)
            if parsed is not None:
                return parsed
        return None

    def _parse_datetime(self, raw: Any) -> datetime | None:
        if isinstance(raw, datetime):
            return raw if raw.tzinfo is not None else raw.replace(tzinfo=timezone.utc)
        if not isinstance(raw, str):
            return None
        value = raw.strip()
        if not value:
            return None
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)

    def _tokenize(self, query: str) -> list[str]:
        return unique_tokens(query, limit=24)


class Reranker:
    """Rerank hybrid candidates contextually."""

    def __init__(self, backend: RerankingBackend | None = None) -> None:
        self.backend = backend or HeuristicRerankingBackend()

    def rerank(self, payload: RerankInput) -> RerankResult:
        """Return top-N reranked evidence items."""
        candidates = self._flatten_candidates(payload.candidate_pool)
        if not candidates:
            return RerankResult(items=[])

        backend_scores = self.backend.score(
            query=payload.query,
            candidates=candidates,
            conversation_context=payload.conversation_context,
        )
        if len(backend_scores) != len(candidates):
            raise ValueError("reranking backend must return one score per candidate")

        scored_items: list[RerankedEvidenceItem] = []
        for candidate, (backend_score, components) in zip(candidates, backend_scores, strict=True):
            base_score = 0.0 if candidate.score is None else candidate.score
            final_score = round(max(0.0, min(1.0, (backend_score * 0.85) + (base_score * 0.15))), 6)
            merged_components = dict(components)
            merged_components["base_score"] = round(base_score, 6)
            merged_components["backend_score"] = round(backend_score, 6)
            scored_items.append(candidate.model_copy(update={"score": final_score, "components": merged_components}, deep=True))

        scored_items.sort(key=lambda item: (-(item.score or 0.0), item.evidence_type.value, item.evidence_id))
        top_items = scored_items[: payload.top_n]

        ranked: list[RerankedEvidenceItem] = []
        for index, item in enumerate(top_items, start=1):
            ranked.append(item.model_copy(update={"rank": index}, deep=True))

        return RerankResult(items=ranked)

    def _flatten_candidates(self, bundle: RAGContextBundle) -> list[RerankedEvidenceItem]:
        items: list[RerankedEvidenceItem] = []

        for chunk in bundle.chunks:
            items.append(
                RerankedEvidenceItem(
                    evidence_type=EvidenceType.CHUNK,
                    evidence_id=chunk.chunk_id,
                    source_id=chunk.source_id,
                    document_id=chunk.document_id,
                    content=chunk.content,
                    score=chunk.score or 0.0,
                    candidate=chunk,
                )
            )

        for fact in bundle.facts:
            content = f"{fact.subject} -[{fact.predicate}]-> {fact.obj}"
            items.append(
                RerankedEvidenceItem(
                    evidence_type=EvidenceType.FACT,
                    evidence_id=fact.fact_id,
                    source_id=fact.source_id,
                    content=content,
                    score=fact.score or 0.0,
                    candidate=fact,
                )
            )

        for evidence in bundle.graph_evidence:
            items.append(
                RerankedEvidenceItem(
                    evidence_type=EvidenceType.GRAPH_EVIDENCE,
                    evidence_id=evidence.evidence_id,
                    source_id=evidence.source_id,
                    content=evidence.path_summary,
                    score=evidence.score or 0.0,
                    candidate=evidence,
                )
            )

        return items
