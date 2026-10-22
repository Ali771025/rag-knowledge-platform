"""End-to-end RAG orchestration pipeline with telemetry and fallback policies."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.conversation_memory.models import ConversationContext
from app.core.config import settings
from app.rag.answer_generator import AnswerGenerationInput, AnswerGenerator, GeneratedAnswer
from app.rag.citation_builder import CitationBuildInput, CitationBuilder
from app.rag.constants import REFUSAL_MESSAGE
from app.rag.context_assembler import ContextAssembleInput, ContextAssembler
from app.rag.grounding_checker import GroundingCheckInput, GroundingChecker
from app.rag.models.rag_types import ConfidenceLevel, RetrievalSource
from app.rag.prompt_builder import PromptBuildInput, PromptBuilder
from app.rag.query_analyzer import QueryAnalysis, QueryAnalyzer
from app.rag.reranker import RerankInput, Reranker
from app.rag.retrieval_planner import RetrievalPlanner
from app.rag.retrievers.hybrid_retriever import HybridRetrievalInput, HybridRetriever, HybridRetrieverError
from app.rag.schemas.context import RAGContextBundle
from app.rag.schemas.request import RAGQueryRequest
from app.rag.schemas.response import RAGAnswerResponse

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RAGPolicyConfig:
    """Fallback/degradation policy flags."""

    min_grounding_ratio: float = 0.6
    fallback_on_no_evidence: bool = True
    fallback_on_weak_grounding: bool = False
    warning_on_weak_grounding: bool = True
    allow_graph_degrade: bool = True
    allow_vector_degrade: bool = True
    token_budget: int = 1800
    min_relevance_score: float = 0.15
    min_retrieved_items: int = 1
    relax_filters_on_zero_results: bool = True
    enforce_citation_presence: bool = False
    retry_on_ungrounded_once: bool = False
    refusal_message: str = REFUSAL_MESSAGE


class RAGEvaluationHook(Protocol):
    """Hook points for future offline/online evaluation."""

    def on_stage_complete(self, *, stage: str, trace_id: str, payload: dict[str, Any]) -> None:
        """Called after each deterministic stage boundary."""

    def on_pipeline_complete(self, *, trace_id: str, payload: dict[str, Any]) -> None:
        """Called at final response packaging stage."""


class NoopEvaluationHook:
    """No-op hook implementation."""

    def on_stage_complete(self, *, stage: str, trace_id: str, payload: dict[str, Any]) -> None:
        _ = (stage, trace_id, payload)

    def on_pipeline_complete(self, *, trace_id: str, payload: dict[str, Any]) -> None:
        _ = (trace_id, payload)


class RAGOrchestratorInput(BaseModel):
    """Input payload for orchestrator execution."""

    user_query: str = Field(min_length=1)
    conversation_context: ConversationContext | None = None
    filters: dict[str, Any] | None = None
    retrieval_sources: list[RetrievalSource] | None = None
    top_k: int = Field(default=12, ge=1, le=100)
    strict_grounding: bool = True
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RAGOrchestratorResult(BaseModel):
    """Full orchestrator output including response and telemetry summary."""

    trace_id: str
    response: RAGAnswerResponse
    retrieval_summary: dict[str, Any] = Field(default_factory=dict)
    grounding_status: str
    warnings: list[str] = Field(default_factory=list)
    fallback_reason: str | None = None
    latency_ms: dict[str, int] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class RAGOrchestrator:
    """Deterministic multi-stage RAG orchestration pipeline."""

    _STAGES = [
        "query_analysis",
        "retrieval_planning",
        "hybrid_retrieval",
        "reranking",
        "context_assembly",
        "prompt_build",
        "answer_generation",
        "grounding_check",
        "citation_build",
        "response_packaging",
    ]

    def __init__(
        self,
        *,
        query_analyzer: QueryAnalyzer | None = None,
        retrieval_planner: RetrievalPlanner | None = None,
        hybrid_retriever: HybridRetriever | None = None,
        reranker: Reranker | None = None,
        context_assembler: ContextAssembler | None = None,
        prompt_builder: PromptBuilder | None = None,
        answer_generator: AnswerGenerator | None = None,
        grounding_checker: GroundingChecker | None = None,
        citation_builder: CitationBuilder | None = None,
        policy: RAGPolicyConfig | None = None,
        evaluation_hook: RAGEvaluationHook | None = None,
    ) -> None:
        self.query_analyzer = query_analyzer or QueryAnalyzer()
        self.retrieval_planner = retrieval_planner or RetrievalPlanner()
        self.hybrid_retriever = hybrid_retriever or HybridRetriever()
        self.reranker = reranker or Reranker()
        self.context_assembler = context_assembler or ContextAssembler()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.answer_generator = answer_generator or AnswerGenerator()
        self.grounding_checker = grounding_checker or GroundingChecker()
        self.citation_builder = citation_builder or CitationBuilder()
        self.policy = policy or RAGPolicyConfig(
            min_grounding_ratio=float(getattr(settings, "rag_min_grounding_ratio", 0.6)),
            fallback_on_no_evidence=bool(getattr(settings, "rag_fallback_on_no_evidence", True)),
            fallback_on_weak_grounding=bool(getattr(settings, "rag_fallback_on_weak_grounding", True)),
            warning_on_weak_grounding=bool(getattr(settings, "rag_warning_on_weak_grounding", False)),
            allow_graph_degrade=bool(getattr(settings, "rag_allow_graph_degrade", True)),
            allow_vector_degrade=bool(getattr(settings, "rag_allow_vector_degrade", True)),
            token_budget=int(getattr(settings, "rag_token_budget", 1800)),
            min_relevance_score=float(getattr(settings, "rag_min_relevance_score", 0.15)),
            min_retrieved_items=int(getattr(settings, "rag_min_retrieved_items", 1)),
            relax_filters_on_zero_results=bool(getattr(settings, "rag_relax_filters_on_zero_results", True)),
            enforce_citation_presence=bool(getattr(settings, "rag_enforce_citation_presence", False)),
            retry_on_ungrounded_once=bool(getattr(settings, "rag_retry_on_ungrounded_once", False)),
            refusal_message=str(getattr(settings, "rag_refusal_message", REFUSAL_MESSAGE)),
        )
        self.evaluation_hook = evaluation_hook or NoopEvaluationHook()

    def run(self, payload: RAGOrchestratorInput) -> RAGOrchestratorResult:
        """Execute full RAG flow with robust error handling and telemetry."""
        trace_id = str(uuid4())
        timings: dict[str, int] = {}
        warnings: list[str] = []
        fallback_reason: str | None = None

        pipeline_started = perf_counter()

        request = RAGQueryRequest(
            trace_id=trace_id,
            query=payload.user_query,
            top_k=payload.top_k,
            retrieval_sources=payload.retrieval_sources,
            filters=payload.filters,
            metadata=payload.metadata,
        )

        analysis = self._timed_stage(
            timings,
            "query_analysis",
            lambda: self.query_analyzer.analyze(request),
            trace_id=trace_id,
        )
        plan = self._timed_stage(
            timings,
            "retrieval_planning",
            lambda: self.retrieval_planner.plan(
                request=request,
                analysis=analysis,
                conversation_context=payload.conversation_context,
            ),
            trace_id=trace_id,
        )

        candidate_pool, degraded_sources, retrieval_debug = self._retrieve_with_degradation(
            timings=timings,
            request=request,
            plan=plan,
            trace_id=trace_id,
        )
        warnings.extend([f"degraded_source:{source.value}" for source in degraded_sources])

        if self._is_empty_pool(candidate_pool):
            fallback_reason = "no_evidence"
            return self._finalize_fallback(
                trace_id=trace_id,
                reason=fallback_reason,
                warnings=warnings,
                timings=timings,
                plan=plan,
                candidate_pool=candidate_pool,
                pipeline_started=pipeline_started,
            )

        reranked = self._timed_stage(
            timings,
            "reranking",
            lambda: self.reranker.rerank(
                RerankInput(
                    query=payload.user_query,
                    candidate_pool=candidate_pool,
                    top_n=max(payload.top_k * 4, payload.top_k),
                    conversation_context=payload.conversation_context,
                )
            ),
            trace_id=trace_id,
        )

        assembled_context = self._timed_stage(
            timings,
            "context_assembly",
            lambda: self.context_assembler.assemble(
                ContextAssembleInput(
                    candidate_pool=candidate_pool,
                    reranked_items=reranked.items,
                    token_budget=self.policy.token_budget,
                )
            ),
            trace_id=trace_id,
        )

        if self._is_empty_pool(assembled_context):
            fallback_reason = "empty_context_after_assembly"
            return self._finalize_fallback(
                trace_id=trace_id,
                reason=fallback_reason,
                warnings=warnings,
                timings=timings,
                plan=plan,
                candidate_pool=assembled_context,
                pipeline_started=pipeline_started,
            )

        prompt_payload = self._timed_stage(
            timings,
            "prompt_build",
            lambda: self.prompt_builder.build(
                PromptBuildInput(
                    user_query=payload.user_query,
                    context_bundle=assembled_context,
                    conversation_context=payload.conversation_context,
                    strict_grounding=payload.strict_grounding,
                )
            ),
            trace_id=trace_id,
        )

        generation_started = perf_counter()
        try:
            generated = self.answer_generator.generate(
                AnswerGenerationInput(
                    trace_id=trace_id,
                    prompt_payload=prompt_payload,
                    context_bundle=assembled_context,
                )
            )
        except Exception as exc:
            logger.warning(
                "rag.answer_generation.error trace_id=%s error=%s",
                trace_id,
                type(exc).__name__,
            )
            warnings.append("answer_generation_failed")
            generated = GeneratedAnswer(
                trace_id=trace_id,
                answer=self._build_extractive_answer(assembled_context),
                used_fallback=True,
                metadata={"fallback_reason": "answer_generation_failed"},
            )
        timings["answer_generation"] = int((perf_counter() - generation_started) * 1000)
        self.evaluation_hook.on_stage_complete(
            stage="answer_generation",
            trace_id=trace_id,
            payload={"latency_ms": timings["answer_generation"]},
        )

        answer_text = generated.answer
        if generated.used_fallback and self._has_retrieved_evidence(assembled_context):
            warnings.append("llm_fallback_with_evidence_recovered")
            answer_text = self._build_extractive_answer(assembled_context)

        grounding = self._timed_stage(
            timings,
            "grounding_check",
            lambda: self.grounding_checker.check(
                GroundingCheckInput(
                    answer=answer_text,
                    context_bundle=assembled_context,
                    min_support_ratio=self.policy.min_grounding_ratio,
                )
            ),
            trace_id=trace_id,
        )

        if answer_text.strip() == self.policy.refusal_message and self._has_retrieved_evidence(assembled_context):
            warnings.append("model_refusal_with_evidence_recovered")
            answer_text = self._build_extractive_answer(assembled_context)
            grounding = self._timed_stage(
                timings,
                "grounding_check_recovered",
                lambda: self.grounding_checker.check(
                    GroundingCheckInput(
                        answer=answer_text,
                        context_bundle=assembled_context,
                        min_support_ratio=self.policy.min_grounding_ratio,
                    )
                ),
                trace_id=trace_id,
            )

        if self.grounding_checker.should_warn(grounding) and self.policy.warning_on_weak_grounding:
            warnings.append("weak_grounding")
            answer_text = f"{answer_text}\n\nWarning: Some claims may be weakly grounded in available evidence."

        grounded = bool(grounding.is_grounded and answer_text != self.policy.refusal_message)
        if not grounded and answer_text != self.policy.refusal_message:
            if self.grounding_checker.should_fallback(grounding) and self.policy.fallback_on_weak_grounding:
                fallback_reason = fallback_reason or "weak_grounding"
            else:
                fallback_reason = fallback_reason or "grounding_enforced_refusal"
            answer_text = self.policy.refusal_message

        citations = []
        if answer_text != self.policy.refusal_message:
            citations = self._timed_stage(
                timings,
                "citation_build",
                lambda: self.citation_builder.build(
                    CitationBuildInput(
                        trace_id=trace_id,
                        answer=answer_text,
                        context_bundle=assembled_context,
                        include_uncited=True,
                    )
                ),
                trace_id=trace_id,
            )
            if citations and not self._has_inline_citations(answer_text):
                warnings.append("missing_inline_citations")
                answer_text = self._append_inline_citations(answer_text=answer_text, citations=citations)

        response = self._timed_stage(
            timings,
            "response_packaging",
            lambda: self._package_response(
                trace_id=trace_id,
                answer=answer_text,
                citations=citations,
                grounding=grounding,
                request=request,
                candidate_pool=candidate_pool,
                assembled_context=assembled_context,
                warnings=warnings,
                fallback_reason=fallback_reason,
            ),
            trace_id=trace_id,
        )

        total_ms = int((perf_counter() - pipeline_started) * 1000)
        timings["total"] = total_ms

        self._log_telemetry(
            trace_id=trace_id,
            timings=timings,
            request=request,
            candidate_pool=candidate_pool,
            assembled_context=assembled_context,
            grounding=grounding,
            fallback_reason=fallback_reason,
            retrieval_debug=retrieval_debug,
            prompt_length=len(prompt_payload.system_prompt) + len(prompt_payload.user_prompt),
            context_length=self._estimate_context_length(assembled_context),
            grounded=bool(answer_text != self.policy.refusal_message and grounding.is_grounded),
            citation_count=len(citations),
        )

        retrieval_summary = self._build_retrieval_summary(
            request=request,
            plan=assembled_context.plan,
            candidate_pool=candidate_pool,
            assembled_context=assembled_context,
            degraded_sources=degraded_sources,
        )

        result = RAGOrchestratorResult(
            trace_id=trace_id,
            response=response,
            retrieval_summary=retrieval_summary,
            grounding_status="grounded" if answer_text != self.policy.refusal_message else "insufficient_evidence",
            warnings=warnings,
            fallback_reason=fallback_reason,
            latency_ms=timings,
        )
        self.evaluation_hook.on_pipeline_complete(trace_id=trace_id, payload=result.model_dump(mode="json"))
        return result

    def _retrieve_with_degradation(
        self,
        *,
        timings: dict[str, int],
        request: RAGQueryRequest,
        plan,
        trace_id: str,
    ) -> tuple[RAGContextBundle, list[RetrievalSource], dict[str, Any]]:
        degraded: list[RetrievalSource] = []
        debug: dict[str, Any] = {
            "retrieved_count": 0,
            "post_filter_count": 0,
            "relaxation_applied": False,
            "relaxation_stage_counts": [],
            "top_scores": [],
        }

        try:
            bundle = self._timed_stage(
                timings,
                "hybrid_retrieval",
                lambda: self.hybrid_retriever.retrieve(HybridRetrievalInput(request=request, plan=plan)),
                trace_id=trace_id,
            )
            filtered_bundle = self._apply_relevance_threshold(bundle, self.policy.min_relevance_score)
            debug["retrieved_count"] = self._bundle_count(bundle)
            debug["post_filter_count"] = self._bundle_count(filtered_bundle)
            debug["top_scores"] = self._top_scores(filtered_bundle)

            if self._bundle_count(filtered_bundle) >= self.policy.min_retrieved_items:
                return filtered_bundle, degraded, debug

            if self.policy.relax_filters_on_zero_results:
                relaxed_plans = self._build_relaxed_plans(plan)
                for stage_name, relaxed_plan in relaxed_plans:
                    debug["relaxation_applied"] = True
                    relaxed_bundle = self._timed_stage(
                        timings,
                        "hybrid_retrieval_relaxed",
                        lambda: self.hybrid_retriever.retrieve(HybridRetrievalInput(request=request, plan=relaxed_plan)),
                        trace_id=trace_id,
                    )
                    relaxed_filtered = self._apply_relevance_threshold(relaxed_bundle, self.policy.min_relevance_score)
                    debug["relaxation_stage_counts"].append(
                        {
                            "stage": stage_name,
                            "retrieved_count": self._bundle_count(relaxed_bundle),
                            "post_filter_count": self._bundle_count(relaxed_filtered),
                        }
                    )
                    if self._bundle_count(relaxed_filtered) >= self.policy.min_retrieved_items:
                        debug["post_filter_count"] = self._bundle_count(relaxed_filtered)
                        debug["top_scores"] = self._top_scores(relaxed_filtered)
                        return relaxed_filtered, degraded, debug

            return filtered_bundle, degraded, debug
        except HybridRetrieverError as exc:
            message = str(exc).lower()
            retry_plan = plan

            if "graph" in message and self.policy.allow_graph_degrade and RetrievalSource.GRAPH in retry_plan.sources:
                retry_plan = self._drop_source(retry_plan, RetrievalSource.GRAPH)
                degraded.append(RetrievalSource.GRAPH)
            elif "vector" in message and self.policy.allow_vector_degrade and RetrievalSource.VECTOR in retry_plan.sources:
                retry_plan = self._drop_source(retry_plan, RetrievalSource.VECTOR)
                degraded.append(RetrievalSource.VECTOR)
            else:
                raise

            if not retry_plan.sources:
                if "vector" in message and self.policy.allow_vector_degrade:
                    retry_plan = self._keyword_only_plan(plan, request_top_k=request.top_k)
                else:
                    raise

            try:
                bundle = self._timed_stage(
                    timings,
                    "hybrid_retrieval",
                    lambda: self.hybrid_retriever.retrieve(HybridRetrievalInput(request=request, plan=retry_plan)),
                    trace_id=trace_id,
                )
            except HybridRetrieverError as retry_exc:
                logger.warning(
                    "rag.retrieval.degraded_retry_failed trace_id=%s reason=%s",
                    trace_id,
                    type(retry_exc).__name__,
                )
                empty_bundle = RAGContextBundle(trace_id=request.trace_id, plan=retry_plan)
                debug["retrieved_count"] = 0
                debug["post_filter_count"] = 0
                debug["top_scores"] = []
                return empty_bundle, degraded, debug
            filtered_bundle = self._apply_relevance_threshold(bundle, self.policy.min_relevance_score)
            debug["retrieved_count"] = self._bundle_count(bundle)
            debug["post_filter_count"] = self._bundle_count(filtered_bundle)
            debug["top_scores"] = self._top_scores(filtered_bundle)
            return filtered_bundle, degraded, debug

    def _drop_source(self, plan, source: RetrievalSource):
        sources = [item for item in plan.sources if item != source]
        source_weights = dict(plan.source_weights or {})
        source_weights.pop(source, None)
        top_k = dict(plan.top_k_per_source or {})
        top_k.pop(source, None)

        if source_weights:
            total = sum(max(0.0, value) for value in source_weights.values())
            if total > 0:
                source_weights = {key: round(value / total, 6) for key, value in source_weights.items()}

        return plan.model_copy(
            update={
                "sources": sources,
                "source_weights": source_weights or None,
                "top_k_per_source": top_k or None,
                "include_graph_evidence": plan.include_graph_evidence and (RetrievalSource.GRAPH in sources),
            },
            deep=True,
        )

    def _keyword_only_plan(self, plan, *, request_top_k: int):
        return plan.model_copy(
            update={
                "sources": [RetrievalSource.KEYWORD],
                "source_weights": {RetrievalSource.KEYWORD: 1.0},
                "top_k_per_source": {RetrievalSource.KEYWORD: max(1, request_top_k)},
                "include_graph_evidence": False,
            },
            deep=True,
        )

    def _package_response(
        self,
        *,
        trace_id: str,
        answer: str,
        citations,
        grounding,
        request: RAGQueryRequest,
        candidate_pool: RAGContextBundle,
        assembled_context: RAGContextBundle,
        warnings: list[str],
        fallback_reason: str | None,
    ) -> RAGAnswerResponse:
        grounded = bool(grounding.is_grounded and answer != self.policy.refusal_message)
        confidence = self._confidence_from_grounding(grounding.confidence_level) if grounded else ConfidenceLevel.LOW
        return RAGAnswerResponse(
            trace_id=trace_id,
            answer=answer,
            confidence_level=confidence,
            citations=citations,
            grounding=grounding,
            metadata={
                "query": request.query,
                "grounded": grounded,
                "warnings": warnings,
                "fallback_reason": fallback_reason,
                "candidate_counts": {
                    "chunks": len(candidate_pool.chunks),
                    "facts": len(candidate_pool.facts),
                    "graph_evidence": len(candidate_pool.graph_evidence),
                },
                "assembled_counts": {
                    "chunks": len(assembled_context.chunks),
                    "facts": len(assembled_context.facts),
                    "graph_evidence": len(assembled_context.graph_evidence),
                },
            },
        )

    def _append_inline_citations(self, *, answer_text: str, citations) -> str:
        citation_ids = [item.citation_id for item in citations if getattr(item, "citation_id", None)]
        if not citation_ids:
            return answer_text
        suffix = " ".join(f"[{citation_id}]" for citation_id in citation_ids[:3])
        trimmed = answer_text.rstrip()
        if not trimmed:
            return suffix
        if trimmed.endswith((".", "!", "?")):
            return f"{trimmed} {suffix}"
        return f"{trimmed}. {suffix}"

    def _has_retrieved_evidence(self, bundle: RAGContextBundle) -> bool:
        return bool(bundle.chunks or bundle.facts or bundle.graph_evidence)

    def _build_extractive_answer(self, bundle: RAGContextBundle) -> str:
        if bundle.chunks:
            chunk = bundle.chunks[0]
            metadata = dict(chunk.metadata or {})
            citation_id = str(metadata.get("citation_id") or "C1")
            snippet = self._clip_text(chunk.content, limit=420)
            if snippet:
                return f"{snippet} [{citation_id}]"

        if bundle.facts:
            fact = bundle.facts[0]
            metadata = dict(fact.metadata or {})
            citation_id = str(metadata.get("citation_id") or "C1")
            statement = metadata.get("llm_statement") or f"{fact.subject} --{fact.predicate}--> {fact.obj}"
            return f"{statement} [{citation_id}]"

        if bundle.graph_evidence:
            evidence = bundle.graph_evidence[0]
            metadata = dict(evidence.metadata or {})
            citation_id = str(metadata.get("citation_id") or "C1")
            summary = metadata.get("llm_summary") or evidence.path_summary
            return f"{self._clip_text(str(summary), limit=420)} [{citation_id}]"

        return self.policy.refusal_message

    def _clip_text(self, text: str, *, limit: int) -> str:
        normalized = " ".join(str(text or "").split())
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3] + "..."

    def _finalize_fallback(
        self,
        *,
        trace_id: str,
        reason: str,
        warnings: list[str],
        timings: dict[str, int],
        plan,
        candidate_pool: RAGContextBundle,
        pipeline_started: float,
    ) -> RAGOrchestratorResult:
        answer = self._fallback_answer_for_reason(reason)
        response = RAGAnswerResponse(
            trace_id=trace_id,
            answer=answer,
            confidence_level=ConfidenceLevel.LOW,
            citations=[],
            grounding=None,
            metadata={
                "grounded": False,
                "warnings": [*warnings, reason],
                "fallback_reason": reason,
            },
        )

        timings["total"] = int((perf_counter() - pipeline_started) * 1000)
        self._log_telemetry(
            trace_id=trace_id,
            timings=timings,
            request=RAGQueryRequest(trace_id=trace_id, query="fallback", top_k=1),
            candidate_pool=candidate_pool,
            assembled_context=candidate_pool,
            grounding=None,
            fallback_reason=reason,
            retrieval_debug={
                "retrieved_count": self._bundle_count(candidate_pool),
                "post_filter_count": self._bundle_count(candidate_pool),
                "relaxation_applied": False,
                "relaxation_stage_counts": [],
                "top_scores": self._top_scores(candidate_pool),
            },
            prompt_length=0,
            context_length=self._estimate_context_length(candidate_pool),
            grounded=False,
            citation_count=0,
        )

        retrieval_summary = self._build_retrieval_summary(
            request=RAGQueryRequest(trace_id=trace_id, query="fallback", top_k=1),
            plan=plan,
            candidate_pool=candidate_pool,
            assembled_context=candidate_pool,
            degraded_sources=[],
        )

        result = RAGOrchestratorResult(
            trace_id=trace_id,
            response=response,
            retrieval_summary=retrieval_summary,
            grounding_status="insufficient_evidence",
            warnings=[*warnings, reason],
            fallback_reason=reason,
            latency_ms=timings,
        )
        self.evaluation_hook.on_pipeline_complete(trace_id=trace_id, payload=result.model_dump(mode="json"))
        return result

    def _timed_stage(self, timings: dict[str, int], name: str, func, *, trace_id: str):
        started = perf_counter()
        result = func()
        elapsed_ms = int((perf_counter() - started) * 1000)
        timings[name] = elapsed_ms
        self.evaluation_hook.on_stage_complete(
            stage=name,
            trace_id=trace_id,
            payload={"latency_ms": elapsed_ms},
        )
        return result

    def _is_empty_pool(self, bundle: RAGContextBundle) -> bool:
        return not bundle.chunks and not bundle.facts and not bundle.graph_evidence

    def _fallback_answer_for_reason(self, reason: str) -> str:
        _ = reason
        return self.policy.refusal_message

    def _confidence_from_grounding(self, grounding_confidence: ConfidenceLevel) -> ConfidenceLevel:
        mapping = {
            ConfidenceLevel.VERY_HIGH: ConfidenceLevel.VERY_HIGH,
            ConfidenceLevel.HIGH: ConfidenceLevel.HIGH,
            ConfidenceLevel.MEDIUM: ConfidenceLevel.MEDIUM,
            ConfidenceLevel.LOW: ConfidenceLevel.LOW,
            ConfidenceLevel.VERY_LOW: ConfidenceLevel.LOW,
        }
        return mapping.get(grounding_confidence, ConfidenceLevel.LOW)

    def _build_retrieval_summary(
        self,
        *,
        request: RAGQueryRequest,
        plan,
        candidate_pool: RAGContextBundle,
        assembled_context: RAGContextBundle,
        degraded_sources: list[RetrievalSource],
    ) -> dict[str, Any]:
        return {
            "trace_id": request.trace_id,
            "sources_requested": [source.value for source in (request.retrieval_sources or [])],
            "sources_used": [source.value for source in plan.sources],
            "degraded_sources": [source.value for source in degraded_sources],
            "source_mix_weights": {source.value: weight for source, weight in (plan.source_weights or {}).items()},
            "hit_counts": {
                "raw_chunks": len(candidate_pool.chunks),
                "raw_facts": len(candidate_pool.facts),
                "raw_graph_evidence": len(candidate_pool.graph_evidence),
                "final_chunks": len(assembled_context.chunks),
                "final_facts": len(assembled_context.facts),
                "final_graph_evidence": len(assembled_context.graph_evidence),
            },
        }

    def _log_telemetry(
        self,
        *,
        trace_id: str,
        timings: dict[str, int],
        request: RAGQueryRequest,
        candidate_pool: RAGContextBundle,
        assembled_context: RAGContextBundle,
        grounding,
        fallback_reason: str | None,
        retrieval_debug: dict[str, Any],
        prompt_length: int,
        context_length: int,
        grounded: bool,
        citation_count: int,
    ) -> None:
        logger.info("rag.pipeline.telemetry trace_id=%s latency_ms=%s", trace_id, timings)
        logger.info(
            "rag.query.summary trace_id=%s retrieved_count=%s post_filter_count=%s top_scores=%s "
            "context_length=%s prompt_length=%s grounded=%s citation_count=%s relaxation_applied=%s filter_relaxation=%s",
            trace_id,
            retrieval_debug.get("retrieved_count"),
            retrieval_debug.get("post_filter_count"),
            retrieval_debug.get("top_scores"),
            context_length,
            prompt_length,
            grounded,
            citation_count,
            retrieval_debug.get("relaxation_applied"),
            retrieval_debug.get("relaxation_stage_counts"),
        )
        logger.info(
            "rag.retrieval.summary trace_id=%s source_mix=%s raw_hits=%s final_hits=%s query=%s",
            trace_id,
            [source.value for source in candidate_pool.plan.sources],
            {"chunks": len(candidate_pool.chunks), "facts": len(candidate_pool.facts), "graph_evidence": len(candidate_pool.graph_evidence)},
            {"chunks": len(assembled_context.chunks), "facts": len(assembled_context.facts), "graph_evidence": len(assembled_context.graph_evidence)},
            request.query,
        )
        if grounding is not None:
            logger.info(
                "rag.grounding trace_id=%s grounded=%s confidence=%s unsupported=%s reason=%s unsupported_preview=%s",
                trace_id,
                grounding.is_grounded,
                grounding.confidence_level.value,
                len(grounding.unsupported_claims),
                fallback_reason or "none",
                grounding.unsupported_claims[:2],
            )
        if fallback_reason:
            logger.warning("rag.fallback trace_id=%s reason=%s", trace_id, fallback_reason)

    def _apply_relevance_threshold(self, bundle: RAGContextBundle, min_score: float) -> RAGContextBundle:
        threshold = max(0.0, min(1.0, float(min_score)))
        chunks = [item for item in bundle.chunks if item.score is None or item.score >= threshold]
        facts = [item for item in bundle.facts if item.score is None or item.score >= threshold]
        evidence = [item for item in bundle.graph_evidence if item.score is None or item.score >= threshold]
        return bundle.model_copy(update={"chunks": chunks, "facts": facts, "graph_evidence": evidence}, deep=True)

    def _bundle_count(self, bundle: RAGContextBundle) -> int:
        return len(bundle.chunks) + len(bundle.facts) + len(bundle.graph_evidence)

    def _top_scores(self, bundle: RAGContextBundle) -> list[float]:
        scores = [
            float(item.score)
            for item in [*bundle.chunks, *bundle.facts, *bundle.graph_evidence]
            if getattr(item, "score", None) is not None
        ]
        scores.sort(reverse=True)
        return [round(value, 6) for value in scores[:5]]

    def _build_relaxed_plans(self, plan) -> list[tuple[str, Any]]:
        filters = dict(plan.filters or {})
        if not filters:
            return []

        relaxed: list[tuple[str, Any]] = []

        drop_level = self._with_removed_filter_keys(filters, {"level"})
        if drop_level != filters:
            relaxed.append(("drop_level", plan.model_copy(update={"filters": drop_level or None}, deep=True)))

        base_after_level = drop_level if drop_level != filters else filters
        drop_topic = self._with_removed_filter_keys(base_after_level, {"topic"})
        if drop_topic != base_after_level:
            relaxed.append(("drop_topic", plan.model_copy(update={"filters": drop_topic or None}, deep=True)))

        source_only = self._keep_source_only_filters(drop_topic)
        if source_only != drop_topic:
            relaxed.append(("source_only", plan.model_copy(update={"filters": source_only or None}, deep=True)))

        return relaxed

    def _with_removed_filter_keys(self, filters: dict[str, Any], keys_to_remove: set[str]) -> dict[str, Any]:
        output = dict(filters)
        qdrant = dict(output.get("qdrant") or {})
        must = [item for item in list(qdrant.get("must") or []) if isinstance(item, dict)]

        normalized_remove = {key.strip().lower() for key in keys_to_remove}
        must = [item for item in must if str(item.get("key", "")).strip().lower() not in normalized_remove]

        for key in keys_to_remove:
            output.pop(key, None)

        if must:
            qdrant["must"] = must
            output["qdrant"] = qdrant
        else:
            output.pop("qdrant", None)
        return output

    def _keep_source_only_filters(self, filters: dict[str, Any]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        source_ids = filters.get("source_ids")
        if isinstance(source_ids, list):
            cleaned = [str(item).strip() for item in source_ids if str(item).strip()]
            if cleaned:
                output["source_ids"] = cleaned

        qdrant = dict(filters.get("qdrant") or {})
        must = [item for item in list(qdrant.get("must") or []) if isinstance(item, dict)]
        source_constraints = [item for item in must if str(item.get("key", "")).strip().lower() == "source_id"]
        if source_constraints:
            output["qdrant"] = {"must": source_constraints}
        return output

    def _has_inline_citations(self, answer: str) -> bool:
        return bool(re.search(r"\[(C\d+)\]", answer))

    def _estimate_context_length(self, bundle: RAGContextBundle) -> int:
        return sum(len(chunk.content) for chunk in bundle.chunks) + sum(len(f"{fact.subject} {fact.predicate} {fact.obj}") for fact in bundle.facts) + sum(len(item.path_summary) for item in bundle.graph_evidence)
