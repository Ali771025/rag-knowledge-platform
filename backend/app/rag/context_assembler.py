"""Assemble final grounded context payload for generation."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.rag.reranker import EvidenceType, RerankedEvidenceItem
from app.rag.schemas.context import RAGContextBundle
from app.rag.schemas.retrieval import GraphEvidence, RetrievedChunk, RetrievedFact


class ContextAssembleInput(BaseModel):
    """Input payload for context assembly."""

    candidate_pool: RAGContextBundle
    reranked_items: list[RerankedEvidenceItem]
    token_budget: int = Field(default=1800, ge=200, le=12000)
    max_chunks: int = Field(default=18, ge=1, le=100)
    max_facts: int = Field(default=20, ge=1, le=120)
    max_graph_evidence: int = Field(default=12, ge=1, le=80)

    model_config = ConfigDict(extra="forbid")


class ContextAssembler:
    """Build a compact, citation-preserving context bundle."""

    def assemble(self, payload: ContextAssembleInput) -> RAGContextBundle:
        """Assemble final context under token budget constraints."""
        if not payload.reranked_items:
            return RAGContextBundle(
                trace_id=payload.candidate_pool.trace_id,
                plan=payload.candidate_pool.plan,
                chunks=[],
                facts=[],
                graph_evidence=[],
                notes="assembled_empty_context",
            )

        selected_chunks: list[RetrievedChunk] = []
        selected_facts: list[RetrievedFact] = []
        selected_graph: list[GraphEvidence] = []

        remaining_tokens = payload.token_budget
        seen_chunk_keys: set[tuple[str, str, str]] = set()
        seen_fact_keys: set[tuple[str, str, str, str]] = set()
        seen_graph_keys: set[tuple[str, str]] = set()
        chunk_signatures: list[set[str]] = []
        citation_index = 1

        for item in payload.reranked_items:
            if remaining_tokens <= 0:
                break

            if item.evidence_type == EvidenceType.CHUNK:
                if len(selected_chunks) >= payload.max_chunks:
                    continue
                chunk = self._as_chunk(item)
                key = (chunk.chunk_id, chunk.document_id, chunk.source_id)
                if key in seen_chunk_keys:
                    continue
                if self._is_redundant_chunk(chunk.content, chunk_signatures):
                    continue

                token_cost = self._estimate_tokens(chunk.content)
                if token_cost > remaining_tokens:
                    continue

                chunk_with_citation = self._with_chunk_citation(chunk, citation_index)
                citation_index += 1
                selected_chunks.append(chunk_with_citation)
                seen_chunk_keys.add(key)
                chunk_signatures.append(self._text_signature(chunk.content))
                remaining_tokens -= token_cost
                continue

            if item.evidence_type == EvidenceType.FACT:
                if len(selected_facts) >= payload.max_facts:
                    continue
                fact = self._as_fact(item)
                key = (fact.source_id, fact.subject, fact.predicate, fact.obj)
                if key in seen_fact_keys:
                    continue

                llm_fact = f"{fact.subject} -> {fact.predicate} -> {fact.obj}"
                token_cost = self._estimate_tokens(llm_fact)
                if token_cost > remaining_tokens:
                    continue

                fact_with_citation = self._with_fact_citation(fact, citation_index)
                citation_index += 1
                selected_facts.append(fact_with_citation)
                seen_fact_keys.add(key)
                remaining_tokens -= token_cost
                continue

            if item.evidence_type == EvidenceType.GRAPH_EVIDENCE:
                if len(selected_graph) >= payload.max_graph_evidence:
                    continue
                graph_item = self._as_graph_evidence(item)
                key = (graph_item.source_id, graph_item.path_summary)
                if key in seen_graph_keys:
                    continue

                token_cost = self._estimate_tokens(graph_item.path_summary)
                if token_cost > remaining_tokens:
                    continue

                graph_with_citation = self._with_graph_citation(graph_item, citation_index)
                citation_index += 1
                selected_graph.append(graph_with_citation)
                seen_graph_keys.add(key)
                remaining_tokens -= token_cost

        grouped_summary = self._group_summary(selected_chunks=selected_chunks, selected_facts=selected_facts, selected_graph=selected_graph)

        notes = "; ".join(
            [
                f"token_budget={payload.token_budget}",
                f"token_remaining={remaining_tokens}",
                f"selected_chunks={len(selected_chunks)}",
                f"selected_facts={len(selected_facts)}",
                f"selected_graph_evidence={len(selected_graph)}",
                f"groups={grouped_summary}",
            ]
        )

        return RAGContextBundle(
            trace_id=payload.candidate_pool.trace_id,
            plan=payload.candidate_pool.plan,
            chunks=selected_chunks,
            facts=selected_facts,
            graph_evidence=selected_graph,
            notes=notes,
        )

    def _as_chunk(self, item: RerankedEvidenceItem) -> RetrievedChunk:
        if not isinstance(item.candidate, RetrievedChunk):
            raise TypeError("expected RetrievedChunk candidate")
        return item.candidate

    def _as_fact(self, item: RerankedEvidenceItem) -> RetrievedFact:
        if not isinstance(item.candidate, RetrievedFact):
            raise TypeError("expected RetrievedFact candidate")
        return item.candidate

    def _as_graph_evidence(self, item: RerankedEvidenceItem) -> GraphEvidence:
        if not isinstance(item.candidate, GraphEvidence):
            raise TypeError("expected GraphEvidence candidate")
        return item.candidate

    def _with_chunk_citation(self, chunk: RetrievedChunk, citation_index: int) -> RetrievedChunk:
        metadata = dict(chunk.metadata or {})
        metadata["citation_id"] = f"C{citation_index}"
        metadata["document_group"] = f"{chunk.source_id}:{chunk.document_id}"
        return chunk.model_copy(update={"metadata": metadata}, deep=True)

    def _with_fact_citation(self, fact: RetrievedFact, citation_index: int) -> RetrievedFact:
        metadata = dict(fact.metadata or {})
        metadata["citation_id"] = f"C{citation_index}"
        metadata["llm_statement"] = f"{fact.subject} --{fact.predicate}--> {fact.obj}"
        return fact.model_copy(update={"metadata": metadata}, deep=True)

    def _with_graph_citation(self, evidence: GraphEvidence, citation_index: int) -> GraphEvidence:
        metadata = dict(evidence.metadata or {})
        metadata["citation_id"] = f"C{citation_index}"
        metadata["llm_summary"] = evidence.path_summary
        return evidence.model_copy(update={"metadata": metadata}, deep=True)

    def _group_summary(
        self,
        *,
        selected_chunks: list[RetrievedChunk],
        selected_facts: list[RetrievedFact],
        selected_graph: list[GraphEvidence],
    ) -> str:
        groups: dict[str, int] = defaultdict(int)

        for chunk in selected_chunks:
            groups[f"chunk:{chunk.source_id}:{chunk.document_id}"] += 1
        for fact in selected_facts:
            groups[f"fact:{fact.source_id}"] += 1
        for evidence in selected_graph:
            groups[f"graph:{evidence.source_id}"] += 1

        if not groups:
            return "none"
        parts = [f"{key}={groups[key]}" for key in sorted(groups)]
        return ",".join(parts)

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        return max(1, len(text) // 4)

    def _text_signature(self, text: str) -> set[str]:
        tokens = [token.lower() for token in text.split() if token.strip()]
        normalized: set[str] = set()
        for token in tokens:
            cleaned = "".join(ch for ch in token if ch.isalnum())
            if len(cleaned) < 3:
                continue
            normalized.add(cleaned)
            if len(normalized) >= 100:
                break
        return normalized

    def _is_redundant_chunk(self, text: str, signatures: list[set[str]]) -> bool:
        current = self._text_signature(text)
        if not current:
            return False

        for other in signatures:
            intersection = len(current & other)
            union = len(current | other)
            if union == 0:
                continue
            jaccard = intersection / union
            if jaccard >= 0.78:
                return True
        return False
