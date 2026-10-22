"""Build stable citation blocks for RAG API responses."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.rag.schemas.context import RAGContextBundle
from app.rag.schemas.response import CitationItem


class CitationBuildInput(BaseModel):
    """Input payload for citation block construction."""

    trace_id: str
    answer: str = Field(min_length=1)
    context_bundle: RAGContextBundle
    include_uncited: bool = False

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CitationBuilder:
    """Maps assembled evidence items into stable citation response entries."""

    def build(self, payload: CitationBuildInput) -> list[CitationItem]:
        """Build citations mapped to answer references and source metadata."""
        evidence_map = self._index_context_evidence(payload.context_bundle)
        cited_ids = self._extract_citation_markers(payload.answer)

        selected_ids: list[str]
        if payload.include_uncited or not cited_ids:
            selected_ids = sorted(evidence_map)
        else:
            selected_ids = [cid for cid in sorted(cited_ids) if cid in evidence_map]

        citations: list[CitationItem] = []
        for citation_id in selected_ids:
            item = evidence_map.get(citation_id)
            if item is None:
                continue
            citations.append(item)

        citations.sort(key=lambda citation: (self._citation_sort_key(citation.citation_id), citation.source_id))
        return citations

    def _index_context_evidence(self, bundle: RAGContextBundle) -> dict[str, CitationItem]:
        output: dict[str, CitationItem] = {}

        for chunk in bundle.chunks:
            metadata = dict(chunk.metadata or {})
            citation_id = self._as_text(metadata.get("citation_id"))
            if not citation_id:
                continue
            source_type = self._as_text(metadata.get("source_type"))
            label = self._as_text(metadata.get("label")) or self._as_text(metadata.get("source_label"))
            output[citation_id] = CitationItem(
                citation_id=citation_id,
                trace_id=bundle.trace_id,
                retrieval_source=chunk.retrieval_source,
                source_id=chunk.source_id,
                snippet=self._clip(chunk.content, limit=280),
                source_uri=chunk.source_uri,
                source_title=chunk.source_title,
                label=label,
                locator=f"chunk:{chunk.chunk_id}",
                score=chunk.score,
                metadata={
                    "evidence_type": "chunk",
                    "document_id": chunk.document_id,
                    "chunk_id": chunk.chunk_id,
                    "title": chunk.source_title,
                    "source_type": source_type,
                    "label": label,
                    "score": chunk.score,
                },
            )

        for fact in bundle.facts:
            metadata = dict(fact.metadata or {})
            citation_id = self._as_text(metadata.get("citation_id"))
            if not citation_id:
                continue
            source_type = self._as_text(metadata.get("source_type"))
            label = self._as_text(metadata.get("label")) or self._as_text(metadata.get("source_label"))
            statement = metadata.get("llm_statement") or f"{fact.subject} --{fact.predicate}--> {fact.obj}"
            output[citation_id] = CitationItem(
                citation_id=citation_id,
                trace_id=bundle.trace_id,
                retrieval_source=fact.retrieval_source,
                source_id=fact.source_id,
                snippet=self._clip(str(statement), limit=280),
                source_uri=fact.source_uri,
                source_title=fact.source_title,
                label=label,
                locator=f"fact:{fact.fact_id}",
                score=fact.score,
                metadata={
                    "evidence_type": "fact",
                    "document_id": metadata.get("document_id"),
                    "chunk_id": None,
                    "title": fact.source_title,
                    "source_type": source_type,
                    "label": label,
                    "score": fact.score,
                },
            )

        for evidence in bundle.graph_evidence:
            metadata = dict(evidence.metadata or {})
            citation_id = self._as_text(metadata.get("citation_id"))
            if not citation_id:
                continue
            source_type = self._as_text(metadata.get("source_type"))
            label = self._as_text(metadata.get("label")) or self._as_text(metadata.get("source_label"))
            summary = metadata.get("llm_summary") or evidence.path_summary
            output[citation_id] = CitationItem(
                citation_id=citation_id,
                trace_id=bundle.trace_id,
                retrieval_source=evidence.retrieval_source,
                source_id=evidence.source_id,
                snippet=self._clip(str(summary), limit=280),
                source_uri=evidence.source_uri,
                source_title=evidence.source_title,
                label=label,
                locator=f"graph:{evidence.evidence_id}",
                score=evidence.score,
                metadata={
                    "evidence_type": "graph_evidence",
                    "document_id": metadata.get("document_id"),
                    "chunk_id": None,
                    "title": evidence.source_title,
                    "source_type": source_type,
                    "label": label,
                    "score": evidence.score,
                },
            )

        return output

    def _extract_citation_markers(self, answer: str) -> set[str]:
        return set(re.findall(r"\[(C\d+)\]", answer))

    def _citation_sort_key(self, citation_id: str) -> tuple[int, str]:
        match = re.fullmatch(r"C(\d+)", citation_id)
        if match:
            return (int(match.group(1)), citation_id)
        return (10**9, citation_id)

    def _as_text(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _clip(self, text: str, *, limit: int) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3] + "..."
