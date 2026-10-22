"""Graph evidence retrieval service backed by read-only graph repository.

This service retrieves structured graph facts and synthesizes lightweight
subgraph evidence snippets. It only performs graph reads through the repository.

It does not mutate the graph, run ingestion, or implement entity extraction
pipelines.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any
from uuid import NAMESPACE_DNS, uuid5

from pydantic import BaseModel, ConfigDict, Field

from app.rag.models.rag_types import RetrievalSource, TraceId
from app.rag.repositories.graph_repository import GraphRepository
from app.rag.schemas.retrieval import GraphEvidence, RetrievedFact


class GraphRetrieverError(Exception):
    """Raised when graph retrieval fails."""


class GraphQueryInput(BaseModel):
    """Input contract for graph retrieval."""

    trace_id: TraceId
    query: str = Field(min_length=1)
    top_k: int = Field(default=20, ge=1, le=100)
    include_evidence: bool = True

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class GraphRetrievalResult(BaseModel):
    """Graph retrieval payload containing facts and evidence snippets."""

    facts: list[RetrievedFact] = Field(default_factory=list)
    evidence: list[GraphEvidence] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class GraphRetriever:
    """Read-only graph retriever that returns facts and graph evidence."""

    def __init__(self, repository: GraphRepository | None = None) -> None:
        self.repository = repository or GraphRepository()

    def retrieve(self, query_input: GraphQueryInput) -> GraphRetrievalResult:
        """Retrieve graph facts and optional subgraph snippets relevant to query."""
        query = query_input.query.strip()
        if not query:
            return GraphRetrievalResult()

        try:
            facts = self.repository.retrieve_facts(
                trace_id=query_input.trace_id,
                query=query,
                top_k=query_input.top_k,
            )
        except Exception as exc:
            raise GraphRetrieverError("failed to retrieve graph facts") from exc

        ranked_facts = self._normalize_facts(facts)
        if not query_input.include_evidence:
            return GraphRetrievalResult(facts=ranked_facts, evidence=[])

        evidence = self._build_evidence_snippets(
            trace_id=query_input.trace_id,
            facts=ranked_facts,
            top_k=query_input.top_k,
        )
        return GraphRetrievalResult(facts=ranked_facts, evidence=evidence)

    def _normalize_facts(self, facts: list[RetrievedFact]) -> list[RetrievedFact]:
        if not facts:
            return []

        raw_scores = [fact.score for fact in facts if fact.score is not None]
        if not raw_scores:
            normalized_scores = self._rank_fallback_scores(len(facts))
        else:
            min_score = min(raw_scores)
            max_score = max(raw_scores)
            if min_score == max_score:
                normalized_scores = self._rank_fallback_scores(len(facts))
            else:
                normalized_scores = []
                for fact in facts:
                    if fact.score is None:
                        normalized_scores.append(0.0)
                        continue
                    score = (fact.score - min_score) / (max_score - min_score)
                    normalized_scores.append(round(max(0.0, min(1.0, score)), 6))

        output: list[RetrievedFact] = []
        for rank, (fact, normalized) in enumerate(zip(facts, normalized_scores, strict=True), start=1):
            metadata = dict(fact.metadata or {})
            metadata["raw_score"] = fact.score
            metadata["normalized_score"] = normalized
            metadata["rank"] = rank
            output.append(
                fact.model_copy(
                    update={
                        "score": normalized,
                        "metadata": metadata,
                    },
                    deep=True,
                )
            )
        return output

    def _build_evidence_snippets(self, *, trace_id: str, facts: list[RetrievedFact], top_k: int) -> list[GraphEvidence]:
        if not facts:
            return []

        grouped: dict[str, list[RetrievedFact]] = defaultdict(list)
        for fact in facts:
            grouped[fact.source_id].append(fact)

        evidence_items: list[GraphEvidence] = []
        for source_id in sorted(grouped):
            grouped_facts = grouped[source_id]
            grouped_facts.sort(key=lambda item: (-(item.score or 0.0), item.fact_id))
            selected = grouped_facts[:3]
            node_ids = self._extract_node_ids(selected)
            edge_ids = [fact.fact_id for fact in selected]
            summary = self._build_path_summary(selected)
            if not node_ids or not summary:
                continue

            score = round(sum((fact.score or 0.0) for fact in selected) / len(selected), 6)
            source_uri = next((fact.source_uri for fact in selected if fact.source_uri), None)
            source_title = next((fact.source_title for fact in selected if fact.source_title), None)

            evidence_id = str(
                uuid5(
                    NAMESPACE_DNS,
                    f"{trace_id}:{source_id}:{'|'.join(edge_ids)}",
                )
            )
            evidence_items.append(
                GraphEvidence(
                    evidence_id=evidence_id,
                    trace_id=trace_id,
                    retrieval_source=RetrievalSource.GRAPH,
                    source_id=source_id,
                    node_ids=node_ids,
                    edge_ids=edge_ids,
                    path_summary=summary,
                    score=score,
                    source_uri=source_uri,
                    source_title=source_title,
                    metadata=self._build_evidence_metadata(selected),
                )
            )

        evidence_items.sort(key=lambda item: (-(item.score or 0.0), item.evidence_id))
        return evidence_items[:top_k]

    def _extract_node_ids(self, facts: list[RetrievedFact]) -> list[str]:
        nodes: list[str] = []
        seen: set[str] = set()

        for fact in facts:
            for raw in (fact.subject, fact.obj):
                node = raw.strip()
                key = node.lower()
                if not node or key in seen:
                    continue
                seen.add(key)
                nodes.append(node)

            source_node_id = self._extract_source_node_id(fact)
            if source_node_id and source_node_id not in seen:
                seen.add(source_node_id)
                nodes.append(source_node_id)

        return nodes

    def _extract_source_node_id(self, fact: RetrievedFact) -> str | None:
        metadata = fact.metadata or {}
        source_metadata = metadata.get("source") if isinstance(metadata.get("source"), dict) else None
        if source_metadata:
            for key in ("id", "node_id", "entity_id"):
                value = source_metadata.get(key)
                if value is not None:
                    text = str(value).strip()
                    if text:
                        return text
        return None

    def _build_path_summary(self, facts: list[RetrievedFact]) -> str:
        segments = [f"{fact.subject} -[{fact.predicate}]-> {fact.obj}" for fact in facts]
        return "; ".join(segments)

    def _build_evidence_metadata(self, facts: list[RetrievedFact]) -> dict[str, Any]:
        relation_types = sorted({fact.predicate for fact in facts if fact.predicate})
        metadata: dict[str, Any] = {
            "fact_count": len(facts),
            "relation_types": relation_types,
            "fact_ids": [fact.fact_id for fact in facts],
        }
        for key in ("document_id", "source_type", "label", "source_label"):
            value = next(
                (
                    (fact.metadata or {}).get(key)
                    for fact in facts
                    if (fact.metadata or {}).get(key) is not None
                ),
                None,
            )
            if value is not None:
                metadata[key] = value
        return metadata

    def _rank_fallback_scores(self, total: int) -> list[float]:
        if total <= 0:
            return []
        if total == 1:
            return [1.0]

        output: list[float] = []
        denominator = total - 1
        for index in range(total):
            output.append(round(1.0 - (index / denominator), 6))
        return output
