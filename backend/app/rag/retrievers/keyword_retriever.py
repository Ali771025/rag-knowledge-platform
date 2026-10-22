"""Keyword/lexical retrieval over existing metadata/content storage.

This retriever performs read-only lexical lookup against already indexed content
(`chunks`, `documents`, `document_metadata`) and returns `RetrievedChunk` items.

It does not create indexes, mutate storage, or run ingestion logic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import SessionLocal
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.metadata import DocumentMetadata
from app.rag.models.rag_types import RetrievalSource, TraceId
from app.rag.schemas.retrieval import RetrievedChunk
from app.rag.text_normalization import normalize_text, unique_tokens

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
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
    "that",
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
_STOPWORDS.update({"از", "با", "به", "برای", "در", "را", "که", "این", "آن", "یک", "و", "یا", "است", "هست", "چه", "چیست", "چطور", "چگونه", "درباره"})


class KeywordRetrieverError(Exception):
    """Raised when lexical retrieval fails."""


class KeywordQueryInput(BaseModel):
    """Input contract for lexical retrieval."""

    trace_id: TraceId
    query: str = Field(min_length=1)
    top_k: int = Field(default=20, ge=1, le=100)
    filters: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


@dataclass(slots=True)
class _CandidateRow:
    chunk_id: str
    document_id: str
    content: str
    source_uri: str | None
    source_title: str | None
    source_type: str | None
    chunk_metadata: dict[str, Any]
    topic: str | None
    category: str | None
    tags: str | None
    difficulty_level: str | None
    language: str | None


class KeywordContentStore(Protocol):
    """Interface for lexical candidate lookup from existing content store."""

    def search_candidates(self, *, query: str, filters: dict[str, Any] | None, limit: int) -> list[_CandidateRow]:
        """Return lexical candidates from metadata/content store."""


class SQLKeywordContentStore:
    """SQLAlchemy-backed lexical candidate lookup over existing content tables."""

    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self.session_factory = session_factory or SessionLocal

    def search_candidates(self, *, query: str, filters: dict[str, Any] | None, limit: int) -> list[_CandidateRow]:
        terms = _tokenize_query(query)
        if not terms:
            return []

        query_patterns = [f"%{term}%" for term in terms[:8]]
        safe_limit = max(1, min(limit, 500))

        with self.session_factory() as session:
            stmt: Select = (
                select(
                    Chunk.id.label("chunk_id"),
                    Chunk.document_id.label("document_id"),
                    Chunk.text.label("content"),
                    Chunk.metadata_json.label("chunk_metadata_json"),
                    Document.source_uri,
                    Document.title.label("source_title"),
                    Document.source_type,
                    DocumentMetadata.topic,
                    DocumentMetadata.category,
                    DocumentMetadata.tags,
                    DocumentMetadata.difficulty_level,
                    DocumentMetadata.language,
                )
                .join(Document, Chunk.document_id == Document.id)
                .outerjoin(DocumentMetadata, DocumentMetadata.document_id == Document.id)
            )

            lexical_conditions = []
            for pattern in query_patterns:
                lexical_conditions.extend(
                    [
                        Chunk.text.ilike(pattern),
                        Document.title.ilike(pattern),
                        Document.summary.ilike(pattern),
                        DocumentMetadata.topic.ilike(pattern),
                        DocumentMetadata.category.ilike(pattern),
                        DocumentMetadata.tags.ilike(pattern),
                    ]
                )
            stmt = stmt.where(or_(*lexical_conditions))
            stmt = self._apply_filters(stmt, filters)
            stmt = stmt.order_by(Chunk.created_at.desc()).limit(safe_limit)

            rows = session.execute(stmt).all()

        output: list[_CandidateRow] = []
        for row in rows:
            chunk_id = str(row.chunk_id)
            content = row.content or ""
            if not chunk_id or not content.strip():
                continue
            output.append(
                _CandidateRow(
                    chunk_id=chunk_id,
                    document_id=str(row.document_id),
                    content=content,
                    source_uri=row.source_uri,
                    source_title=row.source_title,
                    source_type=row.source_type,
                    chunk_metadata=row.chunk_metadata_json if isinstance(row.chunk_metadata_json, dict) else {},
                    topic=row.topic,
                    category=row.category,
                    tags=row.tags,
                    difficulty_level=row.difficulty_level,
                    language=row.language,
                )
            )
        return output

    def _apply_filters(self, stmt: Select, filters: dict[str, Any] | None) -> Select:
        if not filters:
            return stmt

        language = _as_text(filters.get("language"))
        if language:
            stmt = stmt.where(DocumentMetadata.language == language)

        source_type = _as_text(filters.get("source_type"))
        if source_type:
            stmt = stmt.where(Document.source_type == source_type)

        difficulty = _as_text(filters.get("difficulty_level"))
        if difficulty:
            stmt = stmt.where(DocumentMetadata.difficulty_level == difficulty)

        topic = _as_text(filters.get("topic"))
        if topic:
            stmt = stmt.where(DocumentMetadata.topic.ilike(f"%{topic}%"))

        category = _as_text(filters.get("category"))
        if category:
            stmt = stmt.where(DocumentMetadata.category.ilike(f"%{category}%"))

        domain = _as_text(filters.get("domain"))
        if domain:
            stmt = stmt.where(Chunk.metadata_json["domain"].as_string() == domain)

        labels = filters.get("labels")
        if isinstance(labels, list):
            normalized_labels = [str(item).strip().lower() for item in labels if str(item).strip()]
            if normalized_labels:
                stmt = stmt.where(Chunk.metadata_json["label"].as_string().in_(normalized_labels))
        else:
            label = _as_text(filters.get("label"))
            if label:
                stmt = stmt.where(Chunk.metadata_json["label"].as_string() == label)

        source_ids = filters.get("source_ids")
        if isinstance(source_ids, list):
            normalized_source_ids = [str(item).strip() for item in source_ids if str(item).strip()]
            if normalized_source_ids:
                stmt = stmt.where(Chunk.metadata_json["source_id"].as_string().in_(normalized_source_ids))

        return stmt


class KeywordRetriever:
    """Read-only lexical retriever over existing metadata/content store."""

    def __init__(self, content_store: KeywordContentStore | None = None) -> None:
        self.content_store = content_store or SQLKeywordContentStore()

    def retrieve(self, query_input: KeywordQueryInput) -> list[RetrievedChunk]:
        """Retrieve lexical matches and return normalized `RetrievedChunk` results."""
        query = query_input.query.strip()
        if not query:
            return []

        candidate_limit = max(query_input.top_k * 8, query_input.top_k)
        candidates = self.content_store.search_candidates(
            query=query,
            filters=query_input.filters,
            limit=candidate_limit,
        )
        if not candidates:
            return []

        scored = self._score_candidates(candidates=candidates, query=query)
        ranked = sorted(scored, key=lambda item: (-item[1], item[0].chunk_id))[: query_input.top_k]

        normalized_scores = self._normalize_scores([item[1] for item in ranked])

        output: list[RetrievedChunk] = []
        for rank, ((candidate, raw_score), normalized) in enumerate(zip(ranked, normalized_scores, strict=True), start=1):
            metadata = dict(candidate.chunk_metadata)
            metadata.update(
                {
                    "lexical_raw_score": round(raw_score, 6),
                    "lexical_normalized_score": normalized,
                    "lexical_topic": candidate.topic,
                    "lexical_category": candidate.category,
                    "lexical_tags": candidate.tags,
                    "lexical_difficulty_level": candidate.difficulty_level,
                    "lexical_language": candidate.language,
                    "source_type": candidate.source_type,
                }
            )

            output.append(
                RetrievedChunk(
                    chunk_id=candidate.chunk_id,
                    trace_id=query_input.trace_id,
                    retrieval_source=RetrievalSource.KEYWORD,
                    source_id=f"document:{candidate.document_id}",
                    document_id=candidate.document_id,
                    content=candidate.content,
                    score=normalized,
                    rank=rank,
                    source_uri=candidate.source_uri,
                    source_title=candidate.source_title,
                    start_char=self._find_span_start(candidate.content, query),
                    end_char=self._find_span_end(candidate.content, query),
                    metadata=metadata,
                )
            )
        return output

    def _score_candidates(self, *, candidates: list[_CandidateRow], query: str) -> list[tuple[_CandidateRow, float]]:
        terms = _tokenize_query(query)
        query_phrase = normalize_text(query)

        deduped: dict[str, tuple[_CandidateRow, float]] = {}
        for candidate in candidates:
            score = self._score_one(candidate, terms=terms, query_phrase=query_phrase)
            existing = deduped.get(candidate.chunk_id)
            if existing is None or score > existing[1]:
                deduped[candidate.chunk_id] = (candidate, score)

        return list(deduped.values())

    def _score_one(self, candidate: _CandidateRow, *, terms: list[str], query_phrase: str) -> float:
        content = normalize_text(candidate.content)
        title = normalize_text(candidate.source_title or "")
        topic = normalize_text(candidate.topic or "")
        category = normalize_text(candidate.category or "")
        tags = normalize_text(candidate.tags or "")

        if not terms:
            return 0.0

        text_hits = sum(1 for term in terms if term in content)
        title_hits = sum(1 for term in terms if term in title)
        metadata_hits = sum(1 for term in terms if term in topic or term in category or term in tags)

        coverage_text = text_hits / len(terms)
        coverage_title = title_hits / len(terms)
        coverage_meta = metadata_hits / len(terms)

        exact_phrase_boost = 0.0
        if query_phrase and query_phrase in content:
            exact_phrase_boost = 0.25
        elif query_phrase and query_phrase in title:
            exact_phrase_boost = 0.2

        # Mild bonus for denser keyword usage while capping outliers.
        density = sum(content.count(term) for term in terms)
        density_bonus = min(density, 12) / 60.0

        return (coverage_text * 0.55) + (coverage_title * 0.2) + (coverage_meta * 0.2) + exact_phrase_boost + density_bonus

    def _normalize_scores(self, scores: list[float]) -> list[float]:
        if not scores:
            return []

        min_score = min(scores)
        max_score = max(scores)
        if max_score == min_score:
            return self._rank_fallback_scores(len(scores))

        normalized: list[float] = []
        for score in scores:
            value = (score - min_score) / (max_score - min_score)
            normalized.append(round(max(0.0, min(1.0, value)), 6))
        return normalized

    def _rank_fallback_scores(self, total: int) -> list[float]:
        if total <= 0:
            return []
        if total == 1:
            return [1.0]

        scores: list[float] = []
        denominator = total - 1
        for index in range(total):
            scores.append(round(1.0 - (index / denominator), 6))
        return scores

    def _find_span_start(self, content: str, query: str) -> int | None:
        lowered_content = content.lower()
        lowered_query = query.lower().strip()
        if not lowered_query:
            return None
        start = lowered_content.find(lowered_query)
        if start >= 0:
            return start

        terms = _tokenize_query(query)
        for term in terms:
            hit = lowered_content.find(term)
            if hit >= 0:
                return hit
        return None

    def _find_span_end(self, content: str, query: str) -> int | None:
        start = self._find_span_start(content, query)
        if start is None:
            return None

        lowered_content = content.lower()
        lowered_query = query.lower().strip()
        if lowered_query and lowered_content[start : start + len(lowered_query)] == lowered_query:
            return start + len(lowered_query)

        terms = _tokenize_query(query)
        if not terms:
            return None
        first_term = terms[0]
        return start + len(first_term)


def _tokenize_query(query: str) -> list[str]:
    return unique_tokens(query, stopwords=_STOPWORDS, limit=24)


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None
