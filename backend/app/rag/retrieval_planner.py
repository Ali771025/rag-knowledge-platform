"""Deterministic retrieval planning service.

Converts query analysis and optional conversation context into a concrete
`RetrievalPlan` that downstream retrievers can execute.
"""

from __future__ import annotations

import json
from math import floor
from uuid import NAMESPACE_DNS, uuid5

from app.conversation_memory.models import ConversationContext, ConversationState
from app.rag.models.rag_types import RetrievalSource
from app.rag.query_analyzer import QueryAnalysis, QueryType
from app.rag.schemas.request import RAGQueryRequest
from app.rag.schemas.retrieval import RetrievalPlan

_ONBOARDING_TERMS = {
    "onboarding",
    "onboard",
    "orientation",
    "getting started",
    "intro",
    "introduction",
    "join",
    "learning path",
    "curriculum",
    "qna",
}


class RetrievalPlanner:
    """Build deterministic retrieval plans from analysis + context."""

    def plan(
        self,
        *,
        request: RAGQueryRequest,
        analysis: QueryAnalysis,
        conversation_context: ConversationContext | None = None,
    ) -> RetrievalPlan:
        """Compatibility alias for callers that prefer `plan(...)` naming."""
        return self.build_plan(
            request=request,
            analysis=analysis,
            conversation_context=conversation_context,
        )

    def build_plan(
        self,
        *,
        request: RAGQueryRequest,
        analysis: QueryAnalysis,
        conversation_context: ConversationContext | None = None,
    ) -> RetrievalPlan:
        """Create retrieval plan with source weights, top-k split, and constraints."""
        sources = self._select_sources(request=request, analysis=analysis)
        source_weights = self._compute_source_weights(
            sources=sources,
            analysis=analysis,
            request=request,
            conversation_context=conversation_context,
        )
        top_k_per_source = self._allocate_top_k(
            sources=sources,
            source_weights=source_weights,
            total_top_k=request.top_k,
        )

        filters = self._build_filters(request=request, analysis=analysis)
        constraints = self._build_conversation_constraints(
            request=request,
            analysis=analysis,
            conversation_context=conversation_context,
        )

        include_graph = request.include_graph_evidence and (RetrievalSource.GRAPH in sources)
        include_chunks = RetrievalSource.VECTOR in sources or RetrievalSource.KEYWORD in sources
        include_facts = RetrievalSource.GRAPH in sources or analysis.query_type in {
            QueryType.FACTOID,
            QueryType.RELATIONAL,
            QueryType.COMPARATIVE,
        }

        notes = self._build_notes(
            analysis=analysis,
            conversation_context=conversation_context,
            top_k_total=request.top_k,
            selected_sources=sources,
        )

        deterministic_plan_id = self._build_plan_id(
            trace_id=request.trace_id,
            sources=sources,
            source_weights=source_weights,
            top_k_per_source=top_k_per_source,
            filters=filters,
            constraints=constraints,
            include_graph=include_graph,
        )

        return RetrievalPlan(
            plan_id=deterministic_plan_id,
            trace_id=request.trace_id,
            sources=sources,
            source_weights=source_weights,
            top_k_per_source=top_k_per_source,
            include_chunks=include_chunks,
            include_facts=include_facts,
            include_graph_evidence=include_graph,
            filters=filters,
            constraints=constraints,
            notes=notes,
        )

    def _select_sources(self, *, request: RAGQueryRequest, analysis: QueryAnalysis) -> list[RetrievalSource]:
        selected: list[RetrievalSource] = []

        if analysis.needs_semantic_retrieval:
            selected.append(RetrievalSource.VECTOR)
        if analysis.needs_keyword_retrieval:
            selected.append(RetrievalSource.KEYWORD)
        if analysis.needs_graph_retrieval and request.include_graph_evidence:
            selected.append(RetrievalSource.GRAPH)

        if request.retrieval_sources:
            allowlist = list(dict.fromkeys(request.retrieval_sources))
            selected = [source for source in selected if source in allowlist]
            if not selected:
                selected = allowlist

        if not selected:
            selected = [RetrievalSource.VECTOR]

        return list(dict.fromkeys(selected))

    def _compute_source_weights(
        self,
        *,
        sources: list[RetrievalSource],
        analysis: QueryAnalysis,
        request: RAGQueryRequest,
        conversation_context: ConversationContext | None,
    ) -> dict[RetrievalSource, float]:
        weights = {source: 0.0 for source in sources}

        if RetrievalSource.VECTOR in weights and analysis.needs_semantic_retrieval:
            weights[RetrievalSource.VECTOR] += 0.55
        if RetrievalSource.KEYWORD in weights and analysis.needs_keyword_retrieval:
            weights[RetrievalSource.KEYWORD] += 0.35
        if RetrievalSource.GRAPH in weights and analysis.needs_graph_retrieval:
            weights[RetrievalSource.GRAPH] += 0.45

        if analysis.query_type == QueryType.FACTOID:
            if RetrievalSource.KEYWORD in weights:
                weights[RetrievalSource.KEYWORD] += 0.2
            if RetrievalSource.VECTOR in weights:
                weights[RetrievalSource.VECTOR] += 0.1
        elif analysis.query_type == QueryType.PROCEDURAL:
            if RetrievalSource.VECTOR in weights:
                weights[RetrievalSource.VECTOR] += 0.2
            if RetrievalSource.KEYWORD in weights:
                weights[RetrievalSource.KEYWORD] += 0.1
        elif analysis.query_type == QueryType.COMPARATIVE:
            if RetrievalSource.VECTOR in weights:
                weights[RetrievalSource.VECTOR] += 0.12
            if RetrievalSource.GRAPH in weights:
                weights[RetrievalSource.GRAPH] += 0.15
        elif analysis.query_type == QueryType.RELATIONAL:
            if RetrievalSource.GRAPH in weights:
                weights[RetrievalSource.GRAPH] += 0.25

        if analysis.is_ambiguous:
            if RetrievalSource.VECTOR in weights:
                weights[RetrievalSource.VECTOR] += 0.08
            if RetrievalSource.KEYWORD in weights:
                weights[RetrievalSource.KEYWORD] += 0.08

        onboarding_state = self._resolve_onboarding_state(conversation_context)
        onboarding_detected = self._is_onboarding_query(analysis.query)
        if onboarding_state or onboarding_detected:
            if RetrievalSource.KEYWORD in weights:
                weights[RetrievalSource.KEYWORD] += 0.12
            if RetrievalSource.VECTOR in weights:
                weights[RetrievalSource.VECTOR] += 0.08
            if onboarding_state == ConversationState.EDUCATION and RetrievalSource.GRAPH in weights:
                weights[RetrievalSource.GRAPH] += 0.08
            if onboarding_state == ConversationState.JOIN and RetrievalSource.KEYWORD in weights:
                weights[RetrievalSource.KEYWORD] += 0.08

        if not any(value > 0 for value in weights.values()):
            for source in weights:
                weights[source] = 1.0

        return self._normalize_weights(weights)

    def _allocate_top_k(
        self,
        *,
        sources: list[RetrievalSource],
        source_weights: dict[RetrievalSource, float],
        total_top_k: int,
    ) -> dict[RetrievalSource, int]:
        safe_total = max(1, total_top_k)
        if len(sources) == 1:
            return {sources[0]: safe_total}

        # Guarantee a minimal read from each selected source.
        allocation = {source: 1 for source in sources}
        remaining = safe_total - len(sources)
        if remaining <= 0:
            return allocation

        ordered = sorted(sources, key=lambda source: source.value)
        quotas = {}
        for source in ordered:
            weight = source_weights.get(source, 0.0)
            quotas[source] = weight * remaining

        for source in ordered:
            base = floor(quotas[source])
            allocation[source] += base
            remaining -= base

        if remaining <= 0:
            return allocation

        ranked_fractional = sorted(
            ordered,
            key=lambda source: ((quotas[source] - floor(quotas[source])), source.value),
            reverse=True,
        )
        for source in ranked_fractional:
            if remaining <= 0:
                break
            allocation[source] += 1
            remaining -= 1

        return allocation

    def _build_filters(self, *, request: RAGQueryRequest, analysis: QueryAnalysis) -> dict[str, object] | None:
        merged: dict[str, object] = {}
        if request.filters:
            merged.update(request.filters)
        if analysis.retrieval_hints.metadata_filters:
            merged.update(analysis.retrieval_hints.metadata_filters)
        if analysis.retrieval_hints.temporal_hints:
            merged.setdefault("temporal_hints", analysis.retrieval_hints.temporal_hints)
        if not merged:
            return None
        return self._ensure_qdrant_filters(merged)

    def _ensure_qdrant_filters(self, filters: dict[str, object]) -> dict[str, object]:
        output = dict(filters)
        must: list[dict[str, object]] = []

        qdrant_raw = output.get("qdrant")
        if isinstance(qdrant_raw, dict):
            existing_must = qdrant_raw.get("must")
            if isinstance(existing_must, list):
                must.extend([item for item in existing_must if isinstance(item, dict)])

        domain = output.get("domain")
        if isinstance(domain, str):
            normalized_domain = domain.strip().lower()
            if normalized_domain and not self._has_qdrant_key(must, "domain"):
                must.append({"key": "domain", "match": {"value": normalized_domain}})

        source_ids = output.get("source_ids")
        if isinstance(source_ids, list):
            normalized_source_ids = [str(item).strip() for item in source_ids if str(item).strip()]
            if normalized_source_ids and not self._has_qdrant_key(must, "source_id"):
                must.append({"key": "source_id", "match": {"any": normalized_source_ids}})

        labels: list[str] = []
        labels_raw = output.get("labels")
        if isinstance(labels_raw, list):
            labels = [str(item).strip().lower() for item in labels_raw if str(item).strip()]
        elif isinstance(output.get("label"), str):
            single = str(output.get("label")).strip().lower()
            if single:
                labels = [single]

        if labels:
            deduped: list[str] = []
            seen: set[str] = set()
            for label in labels:
                if label in seen:
                    continue
                seen.add(label)
                deduped.append(label)
            labels = deduped
        if labels and not self._has_qdrant_key(must, "label"):
            must.append({"key": "label", "match": {"any": labels}})
            output["labels"] = labels
            output.setdefault("label", labels[0])

        if must:
            output["qdrant"] = {"must": must}
        return output

    @staticmethod
    def _has_qdrant_key(must: list[dict[str, object]], key: str) -> bool:
        return any(item.get("key") == key for item in must)

    def _build_conversation_constraints(
        self,
        *,
        request: RAGQueryRequest,
        analysis: QueryAnalysis,
        conversation_context: ConversationContext | None,
    ) -> dict[str, object] | None:
        constraints: dict[str, object] = {
            "trace_id": request.trace_id,
            "query_type": analysis.query_type.value,
        }

        if analysis.is_ambiguous:
            constraints["diversity_mode"] = True
            constraints["ambiguity_reasons"] = analysis.ambiguity_reasons

        if conversation_context is None:
            return constraints

        constraints["conversation_state"] = conversation_context.state.value

        recent_user_messages = [
            turn.message
            for turn in conversation_context.turns
            if turn.role.value == "user"
        ]
        if recent_user_messages:
            constraints["recent_user_messages"] = recent_user_messages[-3:]

        memory_summary = conversation_context.metadata.get("memory_summary")
        if isinstance(memory_summary, str) and memory_summary.strip():
            constraints["memory_summary_available"] = True

        preferred_language = conversation_context.user_profile.preferences.get("language")
        if isinstance(preferred_language, str) and preferred_language.strip():
            constraints["preferred_language"] = preferred_language.strip().lower()

        if self._is_onboarding_query(analysis.query) or conversation_context.state in {
            ConversationState.START,
            ConversationState.INTRO,
            ConversationState.EDUCATION,
            ConversationState.QNA,
            ConversationState.JOIN,
        }:
            constraints["domain_focus"] = "onboarding"

        return constraints

    def _build_notes(
        self,
        *,
        analysis: QueryAnalysis,
        conversation_context: ConversationContext | None,
        top_k_total: int,
        selected_sources: list[RetrievalSource],
    ) -> str:
        parts = [f"query_type={analysis.query_type.value}", f"top_k_total={top_k_total}"]
        parts.append("sources=" + ",".join(source.value for source in selected_sources))
        if analysis.needs_clarification and analysis.clarification_question:
            parts.append("clarification_needed=true")
        if conversation_context is not None:
            parts.append(f"conversation_state={conversation_context.state.value}")
            if self._is_onboarding_query(analysis.query):
                parts.append("onboarding_pattern=lexical_match")
        return "; ".join(parts)

    def _build_plan_id(
        self,
        *,
        trace_id: str,
        sources: list[RetrievalSource],
        source_weights: dict[RetrievalSource, float],
        top_k_per_source: dict[RetrievalSource, int],
        filters: dict[str, object] | None,
        constraints: dict[str, object] | None,
        include_graph: bool,
    ) -> str:
        payload = {
            "trace_id": trace_id,
            "sources": [source.value for source in sources],
            "source_weights": {source.value: source_weights[source] for source in sorted(source_weights, key=lambda item: item.value)},
            "top_k_per_source": {source.value: top_k_per_source[source] for source in sorted(top_k_per_source, key=lambda item: item.value)},
            "filters": filters or {},
            "constraints": constraints or {},
            "include_graph": include_graph,
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return str(uuid5(NAMESPACE_DNS, serialized))

    def _normalize_weights(self, weights: dict[RetrievalSource, float]) -> dict[RetrievalSource, float]:
        total = sum(value for value in weights.values() if value > 0)
        if total <= 0:
            uniform = round(1.0 / len(weights), 4)
            return {source: uniform for source in weights}

        normalized = {source: value / total for source, value in weights.items()}
        rounded = {source: round(value, 4) for source, value in normalized.items()}

        delta = round(1.0 - sum(rounded.values()), 4)
        if delta != 0:
            # Keep deterministic correction by adjusting lexical-first source.
            first_source = sorted(rounded, key=lambda source: source.value)[0]
            rounded[first_source] = round(rounded[first_source] + delta, 4)

        return rounded

    def _resolve_onboarding_state(self, context: ConversationContext | None) -> ConversationState | None:
        if context is None:
            return None
        if context.state in {
            ConversationState.START,
            ConversationState.INTRO,
            ConversationState.EDUCATION,
            ConversationState.QNA,
            ConversationState.JOIN,
        }:
            return context.state
        return None

    def _is_onboarding_query(self, query: str) -> bool:
        lowered = query.lower()
        return any(term in lowered for term in _ONBOARDING_TERMS)
