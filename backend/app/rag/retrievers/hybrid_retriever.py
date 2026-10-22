"""Hybrid retrieval orchestration across vector, keyword, and graph retrievers.

This component executes source-specific retrievers based on a `RetrievalPlan`,
merges heterogeneous candidates, deduplicates identities, and preserves
per-source provenance for downstream ranking/generation.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.rag.models.rag_types import RetrievalSource
from app.rag.retrievers.graph_retriever import GraphQueryInput, GraphRetriever
from app.rag.retrievers.keyword_retriever import KeywordQueryInput, KeywordRetriever
from app.rag.retrievers.vector_retriever import VectorQueryInput, VectorRetriever
from app.rag.schemas.context import RAGContextBundle
from app.rag.schemas.request import RAGQueryRequest
from app.rag.schemas.retrieval import GraphEvidence, RetrievalPlan, RetrievedChunk, RetrievedFact


class HybridRetrieverError(Exception):
    """Raised when hybrid retrieval orchestration fails."""


class HybridRetrievalInput(BaseModel):
    """Input contract for hybrid retrieval execution."""

    request: RAGQueryRequest
    plan: RetrievalPlan

    model_config = ConfigDict(extra="forbid")


class HybridRetriever:
    """Orchestrates and merges retrieval candidates from multiple sources."""

    def __init__(
        self,
        vector_retriever: VectorRetriever | None = None,
        keyword_retriever: KeywordRetriever | None = None,
        graph_retriever: GraphRetriever | None = None,
    ) -> None:
        self.vector_retriever = vector_retriever or VectorRetriever()
        self.keyword_retriever = keyword_retriever or KeywordRetriever()
        self.graph_retriever = graph_retriever or GraphRetriever()

    def retrieve(self, payload: HybridRetrievalInput) -> RAGContextBundle:
        """Run retrieval plan and return merged raw candidate pool."""
        request = payload.request
        plan = payload.plan

        if plan.trace_id != request.trace_id:
            raise HybridRetrieverError("plan trace_id must match request trace_id")

        source_weights = self._resolve_source_weights(plan)

        vector_chunks: list[RetrievedChunk] = []
        keyword_chunks: list[RetrievedChunk] = []
        graph_facts: list[RetrievedFact] = []
        graph_evidence: list[GraphEvidence] = []

        for source in plan.sources:
            top_k = self._resolve_top_k(plan=plan, source=source, fallback=request.top_k)
            if top_k <= 0:
                continue

            if source == RetrievalSource.VECTOR:
                try:
                    vector_chunks = self._retrieve_vector(
                        trace_id=request.trace_id,
                        query=request.query,
                        filters=plan.filters,
                        top_k=top_k,
                        request_metadata=request.metadata,
                    )
                except Exception as exc:
                    raise HybridRetrieverError(f"vector retrieval failed: {type(exc).__name__}") from exc
            elif source == RetrievalSource.KEYWORD:
                try:
                    keyword_chunks = self._retrieve_keyword(
                        trace_id=request.trace_id,
                        query=request.query,
                        filters=plan.filters,
                        top_k=top_k,
                    )
                except Exception as exc:
                    raise HybridRetrieverError(f"keyword retrieval failed: {type(exc).__name__}") from exc
            elif source == RetrievalSource.GRAPH:
                try:
                    graph_facts, graph_evidence = self._retrieve_graph(
                        trace_id=request.trace_id,
                        query=request.query,
                        top_k=top_k,
                        include_evidence=plan.include_graph_evidence,
                    )
                except Exception as exc:
                    raise HybridRetrieverError(f"graph retrieval failed: {type(exc).__name__}") from exc

        merged_chunks = self._merge_chunks(
            vector_chunks=vector_chunks,
            keyword_chunks=keyword_chunks,
            source_weights=source_weights,
        )
        merged_facts = self._merge_facts(
            facts=graph_facts,
            source_weights=source_weights,
        )
        merged_evidence = self._merge_evidence(
            evidence=graph_evidence,
            source_weights=source_weights,
        )

        notes = self._build_notes(
            plan=plan,
            vector_count=len(vector_chunks),
            keyword_count=len(keyword_chunks),
            fact_count=len(graph_facts),
            evidence_count=len(graph_evidence),
            merged_chunk_count=len(merged_chunks),
            merged_fact_count=len(merged_facts),
            merged_evidence_count=len(merged_evidence),
        )

        return RAGContextBundle(
            trace_id=request.trace_id,
            plan=plan,
            chunks=merged_chunks,
            facts=merged_facts,
            graph_evidence=merged_evidence,
            notes=notes,
        )

    def _retrieve_vector(
        self,
        *,
        trace_id: str,
        query: str,
        filters: dict[str, Any] | None,
        top_k: int,
        request_metadata: dict[str, Any] | None,
    ) -> list[RetrievedChunk]:
        query_vector = self._extract_query_vector(request_metadata)
        payload = VectorQueryInput(
            trace_id=trace_id,
            query_text=None if query_vector else query,
            query_vector=query_vector,
            top_k=top_k,
            filters=filters,
        )
        return self.vector_retriever.retrieve(payload)

    def _retrieve_keyword(
        self,
        *,
        trace_id: str,
        query: str,
        filters: dict[str, Any] | None,
        top_k: int,
    ) -> list[RetrievedChunk]:
        payload = KeywordQueryInput(
            trace_id=trace_id,
            query=query,
            top_k=top_k,
            filters=filters,
        )
        return self.keyword_retriever.retrieve(payload)

    def _retrieve_graph(
        self,
        *,
        trace_id: str,
        query: str,
        top_k: int,
        include_evidence: bool,
    ) -> tuple[list[RetrievedFact], list[GraphEvidence]]:
        payload = GraphQueryInput(
            trace_id=trace_id,
            query=query,
            top_k=top_k,
            include_evidence=include_evidence,
        )
        result = self.graph_retriever.retrieve(payload)
        return result.facts, result.evidence

    def _merge_chunks(
        self,
        *,
        vector_chunks: list[RetrievedChunk],
        keyword_chunks: list[RetrievedChunk],
        source_weights: dict[RetrievalSource, float],
    ) -> list[RetrievedChunk]:
        merged: dict[tuple[str, str, str], RetrievedChunk] = {}

        for source, items in (
            (RetrievalSource.VECTOR, vector_chunks),
            (RetrievalSource.KEYWORD, keyword_chunks),
        ):
            weight = source_weights.get(source, 0.0)
            for item in items:
                key = (item.chunk_id, item.document_id, item.source_id)
                contribution = self._build_contribution(source=source, score=item.score, weight=weight)

                if key not in merged:
                    metadata = dict(item.metadata or {})
                    metadata["provenance"] = [contribution]
                    metadata["blended_score"] = contribution["weighted_score"]
                    merged[key] = item.model_copy(
                        update={
                            "score": contribution["weighted_score"],
                            "metadata": metadata,
                        },
                        deep=True,
                    )
                    continue

                existing = merged[key]
                merged[key] = self._merge_chunk_candidate(existing=existing, incoming=item, contribution=contribution)

        output = list(merged.values())
        output.sort(key=lambda item: (-(item.score or 0.0), item.chunk_id, item.document_id))
        for index, item in enumerate(output, start=1):
            output[index - 1] = item.model_copy(update={"rank": index}, deep=True)
        return output

    def _merge_chunk_candidate(
        self,
        *,
        existing: RetrievedChunk,
        incoming: RetrievedChunk,
        contribution: dict[str, Any],
    ) -> RetrievedChunk:
        metadata = dict(existing.metadata or {})
        provenance = metadata.get("provenance")
        if not isinstance(provenance, list):
            provenance = []
        provenance.append(contribution)

        existing_weighted = float(metadata.get("blended_score", existing.score or 0.0))
        incoming_weighted = float(contribution["weighted_score"])
        blended_score = round(min(1.0, existing_weighted + incoming_weighted), 6)

        if len(incoming.content) > len(existing.content):
            content = incoming.content
        else:
            content = existing.content

        metadata.update(
            {
                "provenance": provenance,
                "blended_score": blended_score,
            }
        )

        source_uri = existing.source_uri or incoming.source_uri
        source_title = existing.source_title or incoming.source_title

        return existing.model_copy(
            update={
                "content": content,
                "score": blended_score,
                "source_uri": source_uri,
                "source_title": source_title,
                "metadata": metadata,
            },
            deep=True,
        )

    def _merge_facts(
        self,
        *,
        facts: list[RetrievedFact],
        source_weights: dict[RetrievalSource, float],
    ) -> list[RetrievedFact]:
        if not facts:
            return []

        weight = source_weights.get(RetrievalSource.GRAPH, 1.0)
        merged: dict[tuple[str, str, str, str], RetrievedFact] = {}

        for fact in facts:
            key = (fact.source_id, fact.subject, fact.predicate, fact.obj)
            contribution = self._build_contribution(source=RetrievalSource.GRAPH, score=fact.score, weight=weight)
            if key not in merged:
                metadata = dict(fact.metadata or {})
                metadata["provenance"] = [contribution]
                metadata["blended_score"] = contribution["weighted_score"]
                merged[key] = fact.model_copy(
                    update={
                        "score": contribution["weighted_score"],
                        "metadata": metadata,
                    },
                    deep=True,
                )
                continue

            existing = merged[key]
            metadata = dict(existing.metadata or {})
            provenance = metadata.get("provenance")
            if not isinstance(provenance, list):
                provenance = []
            provenance.append(contribution)

            score = round(min(1.0, float(metadata.get("blended_score", existing.score or 0.0)) + contribution["weighted_score"]), 6)
            metadata["provenance"] = provenance
            metadata["blended_score"] = score

            merged[key] = existing.model_copy(
                update={
                    "score": score,
                    "metadata": metadata,
                },
                deep=True,
            )

        output = list(merged.values())
        output.sort(key=lambda item: (-(item.score or 0.0), item.fact_id))
        return output

    def _merge_evidence(
        self,
        *,
        evidence: list[GraphEvidence],
        source_weights: dict[RetrievalSource, float],
    ) -> list[GraphEvidence]:
        if not evidence:
            return []

        weight = source_weights.get(RetrievalSource.GRAPH, 1.0)
        merged: dict[tuple[str, str], GraphEvidence] = {}

        for item in evidence:
            key = (item.source_id, item.path_summary)
            contribution = self._build_contribution(source=RetrievalSource.GRAPH, score=item.score, weight=weight)

            if key not in merged:
                metadata = dict(item.metadata or {})
                metadata["provenance"] = [contribution]
                metadata["blended_score"] = contribution["weighted_score"]
                merged[key] = item.model_copy(
                    update={
                        "score": contribution["weighted_score"],
                        "metadata": metadata,
                    },
                    deep=True,
                )
                continue

            existing = merged[key]
            metadata = dict(existing.metadata or {})
            provenance = metadata.get("provenance")
            if not isinstance(provenance, list):
                provenance = []
            provenance.append(contribution)
            score = round(min(1.0, float(metadata.get("blended_score", existing.score or 0.0)) + contribution["weighted_score"]), 6)
            metadata["provenance"] = provenance
            metadata["blended_score"] = score

            edge_ids = list(dict.fromkeys([*(existing.edge_ids or []), *(item.edge_ids or [])]))
            node_ids = list(dict.fromkeys([*existing.node_ids, *item.node_ids]))

            merged[key] = existing.model_copy(
                update={
                    "score": score,
                    "edge_ids": edge_ids or None,
                    "node_ids": node_ids,
                    "metadata": metadata,
                },
                deep=True,
            )

        output = list(merged.values())
        output.sort(key=lambda item: (-(item.score or 0.0), item.evidence_id))
        return output

    def _resolve_source_weights(self, plan: RetrievalPlan) -> dict[RetrievalSource, float]:
        if plan.source_weights:
            return {source: max(0.0, weight) for source, weight in plan.source_weights.items()}

        if not plan.sources:
            return {}
        uniform = round(1.0 / len(plan.sources), 6)
        return {source: uniform for source in plan.sources}

    def _resolve_top_k(self, *, plan: RetrievalPlan, source: RetrievalSource, fallback: int) -> int:
        if plan.top_k_per_source and source in plan.top_k_per_source:
            return max(0, int(plan.top_k_per_source[source]))
        return max(1, int(fallback))

    def _build_contribution(self, *, source: RetrievalSource, score: float | None, weight: float) -> dict[str, Any]:
        safe_score = 0.0 if score is None else max(0.0, min(1.0, float(score)))
        safe_weight = max(0.0, min(1.0, float(weight)))
        weighted_score = round(safe_score * safe_weight, 6)
        return {
            "retrieval_source": source.value,
            "source_weight": safe_weight,
            "source_score": safe_score,
            "weighted_score": weighted_score,
        }

    def _extract_query_vector(self, metadata: dict[str, Any] | None) -> list[float] | None:
        if not metadata:
            return None
        raw = metadata.get("query_vector")
        if not isinstance(raw, list) or not raw:
            return None

        vector: list[float] = []
        for value in raw:
            try:
                vector.append(float(value))
            except (TypeError, ValueError):
                return None
        return vector

    def _build_notes(
        self,
        *,
        plan: RetrievalPlan,
        vector_count: int,
        keyword_count: int,
        fact_count: int,
        evidence_count: int,
        merged_chunk_count: int,
        merged_fact_count: int,
        merged_evidence_count: int,
    ) -> str:
        parts = [
            f"plan_id={plan.plan_id}",
            f"sources={','.join(source.value for source in plan.sources)}",
            f"raw.vector={vector_count}",
            f"raw.keyword={keyword_count}",
            f"raw.facts={fact_count}",
            f"raw.evidence={evidence_count}",
            f"merged.chunks={merged_chunk_count}",
            f"merged.facts={merged_fact_count}",
            f"merged.evidence={merged_evidence_count}",
        ]
        return "; ".join(parts)
