"""Query analysis service for retrieval planning.

This service classifies query intent and decides which retrieval modes should be
used before executing the RAG retrieval pipeline.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.rag.models.rag_types import TraceId
from app.rag.schemas.request import RAGQueryRequest
from app.rag.text_normalization import contains_non_latin_letters, normalize_text, unique_tokens

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "do",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "was",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
}

_RELATIONSHIP_CUES = {
    "relationship",
    "related",
    "depends",
    "dependency",
    "connected",
    "connect",
    "between",
    "impact",
    "influence",
    "uses",
    "belongs",
    "part",
    "compare",
    "versus",
    "vs",
}

_KEYWORD_CUES = {
    "exact",
    "quote",
    "quoted",
    "match",
    "verbatim",
    "regex",
    "id",
    "error",
    "stacktrace",
    "code",
}

_AMBIGUOUS_TERMS = {"it", "this", "that", "they", "them", "he", "she", "there", "thing", "stuff"}

_PERSIAN_STOPWORDS = {
    "از", "با", "به", "برای", "در", "را", "که", "این", "آن", "یک", "و", "یا", "است", "هست", "چه",
    "چیست", "چطور", "چگونه", "من", "ما", "شما", "می", "شود", "شده", "دارد", "درباره",
}
_PERSIAN_RELATIONSHIP_CUES = {
    "ارتباط", "رابطه", "وابست", "مرتبط", "تفاوت", "مقایسه", "بین", "تاثیر", "تأثیر", "جزء", "بخش",
}


class QueryType(str, Enum):
    """High-level query intent classification."""

    FACTOID = "factoid"
    PROCEDURAL = "procedural"
    COMPARATIVE = "comparative"
    RELATIONAL = "relational"
    EXPLORATORY = "exploratory"


class RetrievalHints(BaseModel):
    """Parsed hints that can improve retrieval precision and recall."""

    keywords: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    quoted_phrases: list[str] = Field(default_factory=list)
    numeric_constraints: list[str] = Field(default_factory=list)
    temporal_hints: list[str] = Field(default_factory=list)
    metadata_filters: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class QueryAnalysis(BaseModel):
    """Structured analysis result consumed by retrieval planning."""

    trace_id: TraceId
    query: str
    query_type: QueryType
    needs_semantic_retrieval: bool
    needs_keyword_retrieval: bool
    needs_graph_retrieval: bool
    retrieval_hints: RetrievalHints
    is_ambiguous: bool
    ambiguity_reasons: list[str] = Field(default_factory=list)
    needs_clarification: bool
    clarification_question: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class QueryAnalyzer:
    """Service for query intent and retrieval-mode analysis."""

    def analyze(self, request: RAGQueryRequest | str) -> QueryAnalysis:
        """Analyze query text and emit a structured retrieval analysis result."""
        if isinstance(request, RAGQueryRequest):
            trace_id = request.trace_id
            query = request.query
        else:
            trace_id = "no-trace"
            query = request

        normalized_query = " ".join(query.split())
        lowered_query = normalize_text(normalized_query)

        hints = self._extract_hints(normalized_query)
        query_type = self._classify_query_type(lowered_query)

        needs_keyword = self._needs_keyword_retrieval(normalized_query, lowered_query, hints)
        needs_graph = self._needs_graph_retrieval(lowered_query, query_type)
        needs_semantic = self._needs_semantic_retrieval(query_type, needs_keyword, normalized_query)

        is_ambiguous, ambiguity_reasons = self._detect_ambiguity(normalized_query, hints)
        needs_clarification = is_ambiguous and self._should_ask_clarification(ambiguity_reasons)
        clarification_question = self._build_clarification_question(query_type, ambiguity_reasons) if needs_clarification else None

        confidence = self._estimate_confidence(
            query=normalized_query,
            hints=hints,
            is_ambiguous=is_ambiguous,
            query_type=query_type,
        )

        return QueryAnalysis(
            trace_id=trace_id,
            query=normalized_query,
            query_type=query_type,
            needs_semantic_retrieval=needs_semantic,
            needs_keyword_retrieval=needs_keyword,
            needs_graph_retrieval=needs_graph,
            retrieval_hints=hints,
            is_ambiguous=is_ambiguous,
            ambiguity_reasons=ambiguity_reasons,
            needs_clarification=needs_clarification,
            clarification_question=clarification_question,
            confidence=confidence,
        )

    def _classify_query_type(self, lowered_query: str) -> QueryType:
        if any(token in lowered_query for token in ("how to", "steps", "process", "guide", "walkthrough", "چگونه", "چطور", "مراحل", "راهنما")):
            return QueryType.PROCEDURAL
        if any(token in lowered_query for token in ("compare", "difference", "vs", "versus", "better", "مقایسه", "تفاوت", "بهتر")):
            return QueryType.COMPARATIVE
        if any(token in lowered_query for token in (*_RELATIONSHIP_CUES, *_PERSIAN_RELATIONSHIP_CUES)):
            return QueryType.RELATIONAL
        if lowered_query.endswith("?") and any(
            lowered_query.startswith(prefix)
            for prefix in ("what", "who", "when", "where", "which", "define")
        ):
            return QueryType.FACTOID
        if lowered_query.endswith(("?", "؟")) and any(
            lowered_query.startswith(prefix)
            for prefix in ("چه", "چیست", "کی", "کجا", "کدام", "تعریف")
        ):
            return QueryType.FACTOID
        return QueryType.EXPLORATORY

    def _needs_semantic_retrieval(self, query_type: QueryType, needs_keyword: bool, query: str) -> bool:
        if query_type in {QueryType.PROCEDURAL, QueryType.EXPLORATORY, QueryType.RELATIONAL}:
            return True
        token_count = len(query.split())
        if token_count <= 2 and needs_keyword:
            return False
        return True

    def _needs_keyword_retrieval(self, query: str, lowered_query: str, hints: RetrievalHints) -> bool:
        if contains_non_latin_letters(query):
            return True
        if hints.quoted_phrases:
            return True
        if any(cue in lowered_query for cue in _KEYWORD_CUES):
            return True
        if re.search(r"\b[A-Z]{2,}\d*\b", query):
            return True
        if hints.numeric_constraints:
            return True
        return False

    def _needs_graph_retrieval(self, lowered_query: str, query_type: QueryType) -> bool:
        if query_type == QueryType.RELATIONAL:
            return True
        return any(cue in lowered_query for cue in (*_RELATIONSHIP_CUES, *_PERSIAN_RELATIONSHIP_CUES))

    def _extract_hints(self, query: str) -> RetrievalHints:
        quoted_phrases = self._extract_quoted_phrases(query)
        entities = self._extract_entities(query)
        numeric_constraints = re.findall(r"\b\d+(?:\.\d+)?\b", query)

        temporal_hints: list[str] = []
        for token in ("today", "yesterday", "tomorrow", "latest", "recent", "current", "last week", "last month", "last year"):
            if token in query.lower():
                temporal_hints.append(token)

        keywords = self._extract_keywords(query)
        metadata_filters = self._extract_metadata_filters(query)

        return RetrievalHints(
            keywords=keywords,
            entities=entities,
            quoted_phrases=quoted_phrases,
            numeric_constraints=numeric_constraints,
            temporal_hints=temporal_hints,
            metadata_filters=metadata_filters,
        )

    def _extract_keywords(self, query: str) -> list[str]:
        return unique_tokens(query, stopwords=_STOPWORDS | _PERSIAN_STOPWORDS, limit=20)

    def _extract_entities(self, query: str) -> list[str]:
        entities: list[str] = []
        seen: set[str] = set()

        for match in re.findall(r"\b(?:[A-Z][A-Za-z0-9+\-_/]*)(?:\s+[A-Z][A-Za-z0-9+\-_/]*){0,3}\b", query):
            value = " ".join(match.split())
            key = value.lower()
            if key in seen:
                continue
            seen.add(key)
            entities.append(value)

        for match in re.findall(r"\b[A-Z]{2,}[A-Za-z0-9_\-]*\b", query):
            value = match.strip()
            key = value.lower()
            if key in seen:
                continue
            seen.add(key)
            entities.append(value)

        return entities[:12]

    def _extract_quoted_phrases(self, query: str) -> list[str]:
        matches = re.findall(r'"([^"\n]{2,120})"|\'([^\'\n]{2,120})\'', query)
        output: list[str] = []
        seen: set[str] = set()
        for left, right in matches:
            phrase = (left or right).strip()
            key = phrase.lower()
            if not phrase or key in seen:
                continue
            seen.add(key)
            output.append(phrase)
        return output

    def _extract_metadata_filters(self, query: str) -> dict[str, Any] | None:
        lowered = query.lower()
        filters: dict[str, Any] = {}

        language_match = re.search(r"\b(?:in|language)\s+(english|arabic|french|german|spanish)\b", lowered)
        if language_match:
            filters["language"] = language_match.group(1)

        source_match = re.search(r"\b(?:from|source)\s+(docs|documentation|discord|web|file)\b", lowered)
        if source_match:
            source_value = source_match.group(1)
            if source_value == "documentation":
                source_value = "docs"
            filters["source_type"] = source_value

        if "beginner" in lowered:
            filters["difficulty_level"] = "beginner"
        elif "intermediate" in lowered:
            filters["difficulty_level"] = "intermediate"
        elif "advanced" in lowered:
            filters["difficulty_level"] = "advanced"

        if not filters:
            return None
        return filters

    def _detect_ambiguity(self, query: str, hints: RetrievalHints) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        lowered = query.lower()
        token_count = len(query.split())

        if token_count <= 2:
            reasons.append("query_too_short")

        pronouns = {token for token in re.findall(r"\b[a-z]+\b", lowered) if token in _AMBIGUOUS_TERMS}
        if pronouns and not hints.entities and not hints.quoted_phrases:
            reasons.append("unresolved_references")

        if " or " in lowered and len(hints.keywords) <= 4:
            reasons.append("multiple_possible_intents")

        if not hints.keywords:
            reasons.append("insufficient_retrieval_terms")

        return bool(reasons), reasons

    def _should_ask_clarification(self, reasons: list[str]) -> bool:
        high_impact = {"query_too_short", "unresolved_references", "multiple_possible_intents"}
        return any(reason in high_impact for reason in reasons)

    def _build_clarification_question(self, query_type: QueryType, reasons: list[str]) -> str:
        if "unresolved_references" in reasons:
            return "Can you clarify what 'it/this/that' refers to so I can retrieve the right context?"
        if "multiple_possible_intents" in reasons:
            return "Do you want a comparison, an explanation, or a step-by-step answer?"
        if "query_too_short" in reasons:
            return "Can you add a bit more detail about the topic, system, or document you mean?"
        if query_type == QueryType.FACTOID:
            return "Should I prioritize exact facts or a broader semantic explanation?"
        return "Can you provide one more detail so I can target retrieval more accurately?"

    def _estimate_confidence(
        self,
        *,
        query: str,
        hints: RetrievalHints,
        is_ambiguous: bool,
        query_type: QueryType,
    ) -> float:
        score = 0.55
        score += min(len(hints.keywords), 8) * 0.03
        score += min(len(hints.entities), 5) * 0.04
        score += min(len(hints.quoted_phrases), 3) * 0.05

        if query_type in {QueryType.FACTOID, QueryType.PROCEDURAL, QueryType.RELATIONAL}:
            score += 0.08

        if len(query.split()) <= 2:
            score -= 0.25
        if is_ambiguous:
            score -= 0.2

        return max(0.0, min(1.0, round(score, 3)))
