"""Knowledge graph query expansion utilities."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.core.neo4j_client import Neo4jClientAdapter, Neo4jError
from app.knowledge_graph.graph_repository import GraphRepository
from app.rag.text_normalization import unique_tokens

logger = logging.getLogger(__name__)

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


class QueryExpander:
    """Expand user queries with neighboring graph context from Neo4j."""

    def __init__(
        self,
        neo4j_client: Neo4jClientAdapter | None = None,
        graph_repository: GraphRepository | None = None,
    ) -> None:
        self.graph_repository = graph_repository
        if neo4j_client is not None:
            self.neo4j_client = neo4j_client
        elif graph_repository is not None:
            self.neo4j_client = graph_repository.neo4j_client
        else:
            self.neo4j_client = Neo4jClientAdapter()

    def expand_query(self, query: str, max_expansions: int = 5) -> dict[str, Any]:
        """Return graph-aware query variants for retrieval."""
        query_text = query.strip()
        if not query_text:
            return {
                "original_query": query,
                "expanded_queries": [],
                "related_entities": [],
                "graph_hints": {"detected_entities": [], "depth": 2, "errors": ["empty_query"]},
            }

        safe_max_expansions = max(1, min(max_expansions, 50))
        detected_entities = self.detect_query_entities(query_text)
        related_terms, relation_hints = self._get_related_terms_with_hints(detected_entities, depth=2)
        expanded_queries = self._build_expansions(
            query=query_text,
            detected_entities=detected_entities,
            related_terms=related_terms,
            max_expansions=safe_max_expansions,
        )
        logger.info(
            "query_expansion_completed",
            extra={
                "query": query_text,
                "detected_entities": len(detected_entities),
                "related_terms": len(related_terms),
                "expansions": len(expanded_queries),
            },
        )
        return {
            "original_query": query_text,
            "expanded_queries": expanded_queries,
            "related_entities": related_terms,
            "graph_hints": {
                "detected_entities": detected_entities,
                "depth": 2,
                "matches": relation_hints,
            },
        }

    def detect_query_entities(self, query: str) -> list[str]:
        """Extract candidate entities/concepts from raw user query text."""
        query_text = query.strip()
        if not query_text:
            return []

        candidates: list[str] = []
        # Quoted phrases usually indicate meaningful entity names.
        for quoted in re.findall(r'"([^"]{2,80})"|\'([^\']{2,80})\'', query_text):
            phrase = (quoted[0] or quoted[1]).strip()
            if phrase:
                candidates.append(phrase)

        # Keep title-cased phrases (e.g., "OpenAI API", "Vector Database").
        for phrase in re.findall(r"\b(?:[A-Z][A-Za-z0-9+\-_/]*)(?:\s+[A-Z][A-Za-z0-9+\-_/]*){0,3}\b", query_text):
            cleaned = phrase.strip()
            if len(cleaned) >= 2:
                candidates.append(cleaned)

        # Fall back to meaningful non-stopword tokens to catch lowercase concepts.
        for token in unique_tokens(query_text, stopwords=_STOPWORDS, limit=24):
            lowered = token.lower()
            if lowered not in _STOPWORDS:
                candidates.append(token)

        return self._dedupe_preserve_order(candidates, limit=12)

    def get_related_terms(self, entities: list[str], depth: int = 2) -> list[str]:
        """Retrieve neighboring graph terms for detected entities."""
        terms, _ = self._get_related_terms_with_hints(entities, depth=depth)
        return terms

    def _get_related_terms_with_hints(self, entities: list[str], depth: int = 2) -> tuple[list[str], list[dict[str, Any]]]:
        cleaned_entities = self._dedupe_preserve_order([value.strip() for value in entities if value and value.strip()], limit=12)
        if not cleaned_entities:
            return [], []

        safe_depth = max(1, min(depth, 3))
        limit = max(50, len(cleaned_entities) * 20)
        query = f"""
        UNWIND $entities AS term
        MATCH (seed)
        WHERE seed.name IS NOT NULL
          AND (
            toLower(seed.name) = toLower(term)
            OR toLower(seed.name) CONTAINS toLower(term)
            OR toLower(term) CONTAINS toLower(seed.name)
            OR any(alias IN coalesce(seed.aliases, []) WHERE toLower(alias) = toLower(term))
            OR any(alias IN coalesce(seed.aliases, []) WHERE toLower(alias) CONTAINS toLower(term))
          )
        WITH DISTINCT seed, term
        MATCH path=(seed)-[*1..{safe_depth}]-(neighbor)
        WHERE neighbor.name IS NOT NULL AND seed <> neighbor
        WITH term, seed, neighbor, min(length(path)) AS hops
        RETURN term AS matched_term, seed.name AS seed_name, neighbor.name AS related_name, hops
        ORDER BY hops ASC, related_name ASC
        LIMIT $limit
        """
        try:
            records = self.neo4j_client.execute_read(query, {"entities": cleaned_entities, "limit": limit})
        except Neo4jError as exc:
            logger.warning(
                "query_expansion_graph_lookup_failed",
                extra={"entities": cleaned_entities, "depth": safe_depth, "error": str(exc)},
            )
            return [], []
        except Exception as exc:
            logger.exception("query_expansion_unexpected_graph_error", exc_info=exc)
            return [], []

        related_terms: list[str] = []
        hints: list[dict[str, Any]] = []
        for row in records:
            related_name = str(row.get("related_name", "")).strip()
            seed_name = str(row.get("seed_name", "")).strip()
            if not related_name:
                continue
            related_terms.append(related_name)
            hints.append(
                {
                    "matched_term": str(row.get("matched_term", "")).strip(),
                    "seed_entity": seed_name,
                    "related_entity": related_name,
                    "hops": int(row.get("hops", safe_depth)),
                }
            )

        return self._dedupe_preserve_order(related_terms, limit=60), hints

    def _build_expansions(
        self,
        *,
        query: str,
        detected_entities: list[str],
        related_terms: list[str],
        max_expansions: int,
    ) -> list[str]:
        variants: list[str] = []
        seen: set[str] = set()

        def add_variant(value: str) -> None:
            normalized = " ".join(value.split())
            key = normalized.lower()
            if not normalized or key == query.lower() or key in seen:
                return
            seen.add(key)
            variants.append(normalized)

        top_entities = detected_entities[:4]
        top_related = related_terms[:8]

        for entity in top_entities:
            add_variant(f"{query} {entity}")
        for term in top_related:
            add_variant(f"{query} {term}")
        if top_related:
            add_variant(f"{query} {' '.join(top_related[:2])}")
        for entity in top_entities[:2]:
            for term in top_related[:4]:
                if entity.lower() == term.lower():
                    continue
                add_variant(f"{query} {entity} {term}")

        return variants[:max_expansions]

    def _dedupe_preserve_order(self, values: list[str], limit: int) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()
        for value in values:
            normalized = " ".join(value.strip().split())
            if not normalized:
                continue
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(normalized)
            if len(deduped) >= limit:
                break
        return deduped


_DEFAULT_EXPANDER = QueryExpander()


def expand_query(query: str, max_expansions: int = 5) -> dict[str, Any]:
    """Expand a user query using graph-aware terms."""
    return _DEFAULT_EXPANDER.expand_query(query=query, max_expansions=max_expansions)


def detect_query_entities(query: str) -> list[str]:
    """Detect candidate entities/concepts from a user query."""
    return _DEFAULT_EXPANDER.detect_query_entities(query)


def get_related_terms(entities: list[str], depth: int = 2) -> list[str]:
    """Retrieve graph-neighbor terms for the provided entities."""
    return _DEFAULT_EXPANDER.get_related_terms(entities=entities, depth=depth)
