"""Admin RAG config management and retrieval test service."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.embedding_client import EmbeddingClientAPIError, EmbeddingClientConfigurationError
from app.core.qdrant_client import QdrantClientAdapter
from app.core.qdrant_client import QdrantConnectionError
from app.models.rag_configuration import RAGConfiguration
from app.rag.answer_generator import AnswerGenerationInput, AnswerGenerator
from app.rag.citation_builder import CitationBuildInput, CitationBuilder
from app.rag.context_assembler import ContextAssembleInput, ContextAssembler
from app.rag.prompt_builder import PromptBuildInput, PromptBuilder, PromptBuildResult
from app.rag.repositories.graph_repository import GraphRepositoryError
from app.rag.repositories.qdrant_repository import QdrantRepositoryError
from app.rag.query_analyzer import QueryAnalyzer
from app.rag.reranker import EvidenceType, RerankInput, RerankedEvidenceItem, Reranker
from app.rag.repositories.qdrant_repository import QdrantRepository
from app.rag.retrievers.graph_retriever import GraphRetrieverError
from app.rag.retrieval_planner import RetrievalPlanner
from app.rag.retrievers.hybrid_retriever import HybridRetrievalInput, HybridRetriever, HybridRetrieverError
from app.rag.retrievers.keyword_retriever import KeywordRetriever
from app.rag.retrievers.vector_retriever import VectorRetriever, VectorRetrieverError
from app.rag.schemas.request import RAGQueryRequest
from app.schemas.admin_rag import (
    AdminRAGCitation,
    AdminRAGConfig,
    AdminRAGDiagnostics,
    AdminRAGRetrievedChunk,
    AdminRAGTestRequest,
    AdminRAGTestResult,
)

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = AdminRAGConfig()


class AdminRAGServiceError(RuntimeError):
    """Raised when admin RAG operations fail."""


class AdminRAGUnavailableError(AdminRAGServiceError):
    """Raised when RAG pipeline dependencies are unavailable."""


class AdminRAGService:
    """Service for persisted RAG config and retrieval testing."""

    def __init__(self, *, db: Session) -> None:
        self.db = db

    def get_config(self) -> AdminRAGConfig:
        model = self._get_or_create_model()
        return self._to_schema(model)

    def update_config(self, payload: AdminRAGConfig) -> AdminRAGConfig:
        model = self._get_or_create_model()
        model.chunk_size = payload.chunk_size
        model.chunk_overlap = payload.chunk_overlap
        model.top_k = payload.top_k
        model.similarity_threshold = payload.similarity_threshold
        model.reranker_enabled = payload.reranker_enabled
        model.hybrid_search_enabled = payload.hybrid_search_enabled
        model.graph_enhanced_retrieval_enabled = payload.graph_enhanced_retrieval_enabled
        model.embedding_model = payload.embedding_model
        model.reranker_model = payload.reranker_model
        model.vector_collection_name = payload.vector_collection_name
        model.default_labels = list(payload.default_labels)
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        logger.info(
            "admin_rag_config_updated",
            extra={
                "chunk_size": model.chunk_size,
                "chunk_overlap": model.chunk_overlap,
                "top_k": model.top_k,
                "similarity_threshold": model.similarity_threshold,
                "reranker_enabled": model.reranker_enabled,
                "hybrid_search_enabled": model.hybrid_search_enabled,
                "graph_enhanced_retrieval_enabled": model.graph_enhanced_retrieval_enabled,
                "embedding_model": model.embedding_model,
                "vector_collection_name": model.vector_collection_name,
                "default_labels_count": len(model.default_labels or []),
            },
        )
        return self._to_schema(model)

    def test_retrieval(self, payload: AdminRAGTestRequest) -> AdminRAGTestResult:
        config = self.get_config()
        effective_labels = payload.labels if payload.labels else list(config.default_labels)
        effective_top_k = payload.top_k if payload.top_k is not None else config.top_k
        effective_reranker = payload.reranker_enabled if payload.reranker_enabled is not None else config.reranker_enabled
        effective_hybrid = payload.hybrid_search_enabled if payload.hybrid_search_enabled is not None else config.hybrid_search_enabled
        effective_graph = (
            payload.graph_enhanced_retrieval_enabled
            if payload.graph_enhanced_retrieval_enabled is not None
            else config.graph_enhanced_retrieval_enabled
        )
        include_graph = bool(payload.include_graph_context and effective_graph)

        config_used = config.model_copy(
            update={
                "top_k": effective_top_k,
                "reranker_enabled": effective_reranker,
                "hybrid_search_enabled": effective_hybrid,
                "graph_enhanced_retrieval_enabled": effective_graph,
                "similarity_threshold": payload.similarity_threshold
                if payload.similarity_threshold is not None
                else config.similarity_threshold,
                "default_labels": effective_labels,
            },
            deep=True,
        )

        trace_id = str(uuid4())
        timings_ms: dict[str, int] = {}
        warnings: list[str] = []
        started = perf_counter()

        try:
            filters = self._build_filters(
                domain=payload.domain,
                labels=effective_labels,
                source_ids=payload.source_ids,
            )
            request = RAGQueryRequest(
                trace_id=trace_id,
                query=payload.query,
                top_k=effective_top_k,
                retrieval_sources=self._build_retrieval_sources(
                    hybrid_enabled=effective_hybrid,
                    graph_enabled=include_graph,
                ),
                include_graph_evidence=include_graph,
                filters=filters,
            )

            analyzer = QueryAnalyzer()
            planner = RetrievalPlanner()
            hybrid_retriever = self._build_hybrid_retriever(config_used.vector_collection_name)
            reranker = Reranker()
            context_assembler = ContextAssembler()
            prompt_builder = PromptBuilder()
            answer_generator = AnswerGenerator()
            citation_builder = CitationBuilder()

            t0 = perf_counter()
            analysis = analyzer.analyze(request)
            timings_ms["query_analysis"] = int((perf_counter() - t0) * 1000)

            t0 = perf_counter()
            if hasattr(planner, "build_plan"):
                plan = planner.build_plan(request=request, analysis=analysis, conversation_context=None)
            else:
                plan = planner.plan(request=request, analysis=analysis, conversation_context=None)
            timings_ms["retrieval_plan"] = int((perf_counter() - t0) * 1000)

            if not effective_hybrid:
                plan = plan.model_copy(
                    update={
                        "sources": [source for source in plan.sources if source.value != "keyword"] or plan.sources,
                    },
                    deep=True,
                )
            if not include_graph:
                plan = plan.model_copy(
                    update={
                        "sources": [source for source in plan.sources if source.value != "graph"] or plan.sources,
                        "include_graph_evidence": False,
                    },
                    deep=True,
                )

            graph_fallback_used = False
            t0 = perf_counter()
            try:
                candidate_pool = hybrid_retriever.retrieve(HybridRetrievalInput(request=request, plan=plan))
            except Exception as exc:
                if include_graph and self._is_graph_dependency_error(exc):
                    warnings.append("graph_backend_unavailable_fallback_without_graph")
                    graph_fallback_used = True
                    fallback_sources = [source for source in plan.sources if source.value != "graph"]
                    if not fallback_sources:
                        fallback_sources = self._build_retrieval_sources(
                            hybrid_enabled=effective_hybrid,
                            graph_enabled=False,
                        )
                    plan_update: dict[str, Any] = {
                        "sources": fallback_sources,
                        "include_graph_evidence": False,
                    }
                    source_weights = getattr(plan, "source_weights", None)
                    if isinstance(source_weights, dict):
                        filtered_weights = {key: value for key, value in source_weights.items() if key in fallback_sources}
                        plan_update["source_weights"] = filtered_weights or None
                    top_k_per_source = getattr(plan, "top_k_per_source", None)
                    if isinstance(top_k_per_source, dict):
                        filtered_top_k = {key: value for key, value in top_k_per_source.items() if key in fallback_sources}
                        plan_update["top_k_per_source"] = filtered_top_k or None
                    plan = plan.model_copy(update=plan_update, deep=True)
                    fallback_request = request.model_copy(
                        update={
                            "retrieval_sources": fallback_sources,
                            "include_graph_evidence": False,
                        },
                        deep=True,
                    )
                    if hasattr(fallback_request, "retrieval_sources") and fallback_request.retrieval_sources:
                        fallback_request.retrieval_sources = [
                            source for source in fallback_request.retrieval_sources if source.value != "graph"
                        ]
                    candidate_pool = hybrid_retriever.retrieve(HybridRetrievalInput(request=fallback_request, plan=plan))
                else:
                    raise
            timings_ms["retrieval"] = int((perf_counter() - t0) * 1000)

            # Safety net: enforce label/domain filters again at application layer.
            candidate_pool = self._post_filter_candidate_pool(
                candidate_pool=candidate_pool,
                labels=effective_labels,
                domain=payload.domain,
                source_ids=payload.source_ids,
                similarity_threshold=config_used.similarity_threshold,
            )

            if effective_reranker:
                t0 = perf_counter()
                reranked = reranker.rerank(
                    RerankInput(
                        query=payload.query,
                        candidate_pool=candidate_pool,
                        top_n=max(effective_top_k * 2, effective_top_k),
                        conversation_context=None,
                    )
                )
                timings_ms["rerank"] = int((perf_counter() - t0) * 1000)
                reranked_items = reranked.items
            else:
                reranked_items = self._fallback_reranked_items(candidate_pool, top_n=max(effective_top_k * 2, effective_top_k))
                timings_ms["rerank"] = 0
                warnings.append("reranker_disabled")

            t0 = perf_counter()
            assembled_context = context_assembler.assemble(
                ContextAssembleInput(
                    candidate_pool=candidate_pool,
                    reranked_items=reranked_items,
                    token_budget=1800,
                    max_chunks=max(4, effective_top_k),
                    max_facts=max(6, effective_top_k),
                    max_graph_evidence=max(4, effective_top_k // 2),
                )
            )
            timings_ms["context_assembly"] = int((perf_counter() - t0) * 1000)

            t0 = perf_counter()
            prompt = prompt_builder.build(
                PromptBuildInput(
                    user_query=payload.query,
                    context_bundle=assembled_context,
                    conversation_context=None,
                    strict_grounding=True,
                )
            )
            prompt_payload = self._normalize_prompt_payload(prompt)
            generated = answer_generator.generate(
                AnswerGenerationInput(
                    trace_id=trace_id,
                    prompt_payload=prompt_payload,
                    context_bundle=assembled_context,
                )
            )
            timings_ms["answer_generation"] = int((perf_counter() - t0) * 1000)

            t0 = perf_counter()
            citations = citation_builder.build(
                CitationBuildInput(
                    trace_id=trace_id,
                    answer=generated.answer,
                    context_bundle=assembled_context,
                    include_uncited=True,
                )
            )
            timings_ms["citation_build"] = int((perf_counter() - t0) * 1000)

            raw_chunks = candidate_pool.chunks[:effective_top_k]
            retrieved_chunks = [self._to_retrieved_chunk(item, rerank_lookup=None) for item in raw_chunks]
            rerank_lookup = self._build_rerank_lookup(reranked_items)
            reranked_chunks = [
                self._to_retrieved_chunk(item, rerank_lookup=rerank_lookup)
                for item in assembled_context.chunks[:effective_top_k]
            ]

            chunk_label_lookup = self._build_chunk_label_lookup(raw_chunks, assembled_context.chunks)
            final_citations = [
                self._to_citation(item, rerank_lookup=rerank_lookup, chunk_label_lookup=chunk_label_lookup)
                for item in citations
            ]
            total_latency = int((perf_counter() - started) * 1000)
            timings_ms["total"] = total_latency

            diagnostics = AdminRAGDiagnostics(
                timings_ms=timings_ms,
                flags={
                    "hybrid_search_enabled": effective_hybrid,
                    "reranker_enabled": effective_reranker,
                    "graph_enhanced_retrieval_enabled": effective_graph,
                    "include_graph_context": include_graph,
                    "graph_fallback_used": graph_fallback_used,
                    "llm_fallback_used": generated.used_fallback,
                },
                retrieval_summary={
                    "trace_id": trace_id,
                    "sources": [source.value for source in plan.sources],
                    "retrieved_chunk_count": len(candidate_pool.chunks),
                    "retrieved_fact_count": len(candidate_pool.facts),
                    "retrieved_graph_evidence_count": len(candidate_pool.graph_evidence),
                    "assembled_chunk_count": len(assembled_context.chunks),
                    "assembled_fact_count": len(assembled_context.facts),
                    "assembled_graph_evidence_count": len(assembled_context.graph_evidence),
                },
                warnings=warnings,
            )

            logger.info(
                "admin_rag_test_executed",
                extra={
                    "trace_id": trace_id,
                    "query_length": len(payload.query),
                    "labels_count": len(effective_labels),
                    "top_k": effective_top_k,
                    "retrieved_chunk_count": len(candidate_pool.chunks),
                    "reranked_chunk_count": len(assembled_context.chunks[:effective_top_k]),
                    "latency_ms": total_latency,
                    "hybrid_search_enabled": effective_hybrid,
                    "reranker_enabled": effective_reranker,
                    "graph_enhanced_retrieval_enabled": effective_graph,
                    "include_graph_context": include_graph,
                },
            )

            return AdminRAGTestResult(
                query=payload.query,
                config_used=config_used,
                retrieved_chunks=retrieved_chunks,
                reranked_chunks=reranked_chunks,
                final_answer=generated.answer,
                citations=final_citations,
                diagnostics=diagnostics,
                latency_ms=total_latency,
            )
        except AdminRAGUnavailableError:
            raise
        except Exception as exc:
            logger.exception("admin_rag_test_failed", exc_info=exc)
            if self._is_dependency_unavailable_error(exc):
                raise AdminRAGUnavailableError(
                    "RAG retrieval pipeline is unavailable. Verify OPENAI_API_KEY and vector store/indexing dependencies."
                ) from exc
            raise AdminRAGServiceError("Failed to execute RAG retrieval test") from exc

    def _build_hybrid_retriever(self, vector_collection_name: str) -> HybridRetriever:
        qdrant_adapter = QdrantClientAdapter()
        qdrant_adapter.collection_name = vector_collection_name
        vector_repo = QdrantRepository(qdrant_client=qdrant_adapter)
        vector_retriever = VectorRetriever(repository=vector_repo)
        keyword_retriever = KeywordRetriever()
        return HybridRetriever(vector_retriever=vector_retriever, keyword_retriever=keyword_retriever)

    def _build_filters(
        self,
        *,
        domain: str | None,
        labels: list[str],
        source_ids: list[str] | None,
    ) -> dict[str, Any] | None:
        app_filters: dict[str, Any] = {}
        if domain:
            app_filters["domain"] = domain.strip().lower()
        if labels:
            app_filters["labels"] = labels
        if source_ids:
            app_filters["source_ids"] = [item.strip() for item in source_ids if item.strip()]

        qdrant_must: list[dict[str, Any]] = []
        if domain:
            qdrant_must.append({"key": "domain", "match": {"value": domain.strip().lower()}})
        if labels:
            qdrant_must.append({"key": "label", "match": {"any": labels}})
        if source_ids:
            qdrant_must.append({"key": "source_id", "match": {"any": [item.strip() for item in source_ids if item.strip()]}})
        if qdrant_must:
            app_filters["qdrant"] = {"must": qdrant_must}

        return app_filters or None

    def _build_retrieval_sources(self, *, hybrid_enabled: bool, graph_enabled: bool):
        from app.rag.models.rag_types import RetrievalSource

        if hybrid_enabled:
            sources = [RetrievalSource.VECTOR, RetrievalSource.KEYWORD]
        else:
            sources = [RetrievalSource.VECTOR]
        if graph_enabled:
            sources.append(RetrievalSource.GRAPH)
        return sources

    def _post_filter_candidate_pool(
        self,
        *,
        candidate_pool,
        labels: list[str],
        domain: str | None,
        source_ids: list[str] | None,
        similarity_threshold: float,
    ):
        normalized_labels = {item.lower() for item in labels}
        normalized_domain = domain.strip().lower() if domain else None
        normalized_source_ids = {item.strip() for item in source_ids or [] if item.strip()}
        safe_threshold = max(0.0, min(1.0, float(similarity_threshold)))

        filtered_chunks = []
        for item in candidate_pool.chunks:
            metadata = dict(item.metadata or {})
            label = str(metadata.get("label") or "").strip().lower()
            domain_value = str(metadata.get("domain") or "").strip().lower()
            score = item.score if item.score is not None else 0.0
            if normalized_labels and label not in normalized_labels:
                continue
            if normalized_domain and domain_value != normalized_domain:
                continue
            if normalized_source_ids and item.source_id not in normalized_source_ids:
                continue
            if score < safe_threshold:
                continue
            filtered_chunks.append(item)

        return candidate_pool.model_copy(update={"chunks": filtered_chunks}, deep=True)

    def _fallback_reranked_items(self, candidate_pool, *, top_n: int) -> list[RerankedEvidenceItem]:
        items: list[RerankedEvidenceItem] = []
        for chunk in candidate_pool.chunks:
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
        for fact in candidate_pool.facts:
            items.append(
                RerankedEvidenceItem(
                    evidence_type=EvidenceType.FACT,
                    evidence_id=fact.fact_id,
                    source_id=fact.source_id,
                    content=f"{fact.subject} -[{fact.predicate}]-> {fact.obj}",
                    score=fact.score or 0.0,
                    candidate=fact,
                )
            )
        items.sort(key=lambda item: (-(item.score or 0.0), item.evidence_id))
        top_items = items[:top_n]
        ranked: list[RerankedEvidenceItem] = []
        for index, item in enumerate(top_items, start=1):
            ranked.append(item.model_copy(update={"rank": index}, deep=True))
        return ranked

    def _build_rerank_lookup(self, reranked_items: list[RerankedEvidenceItem]) -> dict[str, float]:
        lookup: dict[str, float] = {}
        for item in reranked_items:
            if item.evidence_type != EvidenceType.CHUNK:
                continue
            lookup[item.evidence_id] = item.score
        return lookup

    def _to_retrieved_chunk(self, item, *, rerank_lookup: dict[str, float] | None) -> AdminRAGRetrievedChunk:
        metadata = dict(item.metadata or {})
        label = str(metadata.get("label") or "").strip() or None
        rerank_score = rerank_lookup.get(item.chunk_id) if rerank_lookup else None
        return AdminRAGRetrievedChunk(
            chunk_id=item.chunk_id,
            source_id=item.source_id,
            source_title=item.source_title,
            label=label,
            content=item.content,
            score=item.score,
            rerank_score=rerank_score,
            metadata=metadata,
        )

    def _to_citation(
        self,
        item,
        *,
        rerank_lookup: dict[str, float],
        chunk_label_lookup: dict[str, str],
    ) -> AdminRAGCitation:
        metadata = dict(item.metadata or {})
        chunk_id = metadata.get("chunk_id")
        label = metadata.get("label") or metadata.get("chunk_label")
        if not label and isinstance(chunk_id, str):
            label = chunk_label_lookup.get(chunk_id)
        return AdminRAGCitation(
            source_id=item.source_id,
            source_title=item.source_title,
            label=str(label).strip() if label is not None else None,
            chunk_id=str(chunk_id) if chunk_id is not None else None,
            locator=item.locator,
            score=item.score,
            snippet=item.snippet,
        )

    def _build_chunk_label_lookup(self, *chunk_groups) -> dict[str, str]:
        lookup: dict[str, str] = {}
        for chunks in chunk_groups:
            for chunk in chunks:
                metadata = dict(chunk.metadata or {})
                raw_label = metadata.get("label")
                if raw_label is None:
                    continue
                label = str(raw_label).strip()
                if not label:
                    continue
                lookup[chunk.chunk_id] = label
        return lookup

    def _get_or_create_model(self) -> RAGConfiguration:
        model = self.db.scalar(select(RAGConfiguration).order_by(RAGConfiguration.created_at.asc()).limit(1))
        if model is not None:
            return model

        model = RAGConfiguration(
            chunk_size=DEFAULT_CONFIG.chunk_size,
            chunk_overlap=DEFAULT_CONFIG.chunk_overlap,
            top_k=DEFAULT_CONFIG.top_k,
            similarity_threshold=DEFAULT_CONFIG.similarity_threshold,
            reranker_enabled=DEFAULT_CONFIG.reranker_enabled,
            hybrid_search_enabled=DEFAULT_CONFIG.hybrid_search_enabled,
            graph_enhanced_retrieval_enabled=DEFAULT_CONFIG.graph_enhanced_retrieval_enabled,
            embedding_model=DEFAULT_CONFIG.embedding_model,
            reranker_model=DEFAULT_CONFIG.reranker_model,
            vector_collection_name=DEFAULT_CONFIG.vector_collection_name,
            default_labels=list(DEFAULT_CONFIG.default_labels),
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model

    def _to_schema(self, model: RAGConfiguration) -> AdminRAGConfig:
        return AdminRAGConfig(
            chunk_size=model.chunk_size,
            chunk_overlap=model.chunk_overlap,
            top_k=model.top_k,
            similarity_threshold=model.similarity_threshold,
            reranker_enabled=model.reranker_enabled,
            hybrid_search_enabled=model.hybrid_search_enabled,
            graph_enhanced_retrieval_enabled=model.graph_enhanced_retrieval_enabled,
            embedding_model=model.embedding_model,  # type: ignore[arg-type]
            reranker_model=model.reranker_model,
            vector_collection_name=model.vector_collection_name,
            default_labels=list(model.default_labels or []),
            updated_at=model.updated_at,
        )

    def _is_dependency_unavailable_error(self, error: Exception) -> bool:
        dependency_error_types = (
            EmbeddingClientConfigurationError,
            EmbeddingClientAPIError,
            QdrantConnectionError,
            QdrantRepositoryError,
            GraphRepositoryError,
            VectorRetrieverError,
            GraphRetrieverError,
            HybridRetrieverError,
        )
        dependency_keywords = (
            "openai_api_key",
            "embedding",
            "qdrant",
            "neo4j",
            "vector",
            "retriev",
            "unavailable",
        )

        for exc in self._iter_error_chain(error):
            if isinstance(exc, dependency_error_types):
                return True
            message = str(exc).strip().lower()
            if message and any(keyword in message for keyword in dependency_keywords):
                return True
        return False

    def _is_graph_dependency_error(self, error: Exception) -> bool:
        graph_error_types = (
            GraphRepositoryError,
            GraphRetrieverError,
            HybridRetrieverError,
        )
        graph_keywords = (
            "neo4j",
            "graph",
            "relationship",
            "entity",
        )

        for exc in self._iter_error_chain(error):
            if isinstance(exc, graph_error_types):
                return True
            message = str(exc).strip().lower()
            if message and any(keyword in message for keyword in graph_keywords):
                return True
        return False

    def _iter_error_chain(self, error: Exception):
        seen: set[int] = set()
        current: BaseException | None = error
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            if isinstance(current, Exception):
                yield current
            if current.__cause__ is not None:
                current = current.__cause__
                continue
            current = current.__context__

    def _normalize_prompt_payload(self, payload: Any) -> PromptBuildResult:
        if isinstance(payload, PromptBuildResult):
            return payload
        if isinstance(payload, dict):
            return PromptBuildResult.model_validate(payload)
        return PromptBuildResult(
            system_prompt=str(getattr(payload, "system_prompt", "") or ""),
            user_prompt=str(getattr(payload, "user_prompt", "") or ""),
            metadata=dict(getattr(payload, "metadata", {}) or {}),
        )
