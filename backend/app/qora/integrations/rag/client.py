from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from pydantic import BaseModel, Field

from app.qora.domain.enums import DepthLevel, PersonaModifier, Section
from app.qora.domain.orchestration_contracts import SourceReference


class QoraRAGRequest(BaseModel):
    product_id: str
    selected_section: Section
    intent: str
    depth_level: DepthLevel
    modifiers: list[PersonaModifier]
    requested_claim_type: str = "PRODUCT_GUIDANCE"
    language: str = "fa"
    content_version: str | None = None


class QoraRAGResult(BaseModel):
    excerpt: str | None = None
    sources: list[SourceReference] = Field(default_factory=list)
    allowed_claims: list[str] = Field(default_factory=list)
    insufficient_context: bool = False
    warnings: list[str] = Field(default_factory=list)


class QoraRAGClient(Protocol):
    def retrieve(self, request: QoraRAGRequest) -> QoraRAGResult: ...


class ExistingRAGAdapter:
    """Strict product-scoped adapter over the repository's existing RAG pipeline."""

    def __init__(self, orchestrator=None) -> None:
        if orchestrator is None:
            from app.rag.rag_orchestrator import RAGOrchestrator, RAGPolicyConfig

            orchestrator = RAGOrchestrator(
                policy=RAGPolicyConfig(
                    fallback_on_no_evidence=True,
                    fallback_on_weak_grounding=True,
                    relax_filters_on_zero_results=False,
                    enforce_citation_presence=True,
                    retry_on_ungrounded_once=False,
                )
            )
        self.orchestrator = orchestrator

    def retrieve(self, request: QoraRAGRequest) -> QoraRAGResult:
        from app.rag.rag_orchestrator import RAGOrchestratorInput

        now = datetime.now(timezone.utc).isoformat()
        query = (
            f"Product: {request.product_id}; section: {request.selected_section.value}; "
            f"intent: {request.intent}; depth: {request.depth_level.value}; "
            f"modifier: {','.join(item.value for item in request.modifiers) or 'NONE'}; "
            f"claim type: {request.requested_claim_type}; language: {request.language}."
        )
        filters = {
            "status": "PUBLISHED",
            "language": request.language,
            "product_id": request.product_id,
            "allowed_depth": request.depth_level.value,
            "valid_from": {"lte": now},
            "valid_to": {"is_null_or_gt": now},
        }
        if request.content_version:
            filters["content_version"] = request.content_version
        try:
            result = self.orchestrator.run(
                RAGOrchestratorInput(
                    user_query=query,
                    filters=filters,
                    top_k={DepthLevel.LOW: 4, DepthLevel.MEDIUM: 8, DepthLevel.HIGH: 12}[request.depth_level],
                    strict_grounding=True,
                    metadata={"qora_product_scope": True, "filters_non_relaxable": True},
                )
            )
        except Exception as exc:
            return QoraRAGResult(
                insufficient_context=True,
                warnings=[f"rag_unavailable:{type(exc).__name__}"],
            )
        sources: list[SourceReference] = []
        allowed_claims: list[str] = []
        for index, citation in enumerate(result.response.citations, start=1):
            metadata = citation.metadata or {}
            chunk_id = metadata.get("chunk_id")
            claim_id = f"claim_{index}"
            sources.append(
                SourceReference(
                    source_id=citation.source_id,
                    chunk_id=str(chunk_id) if chunk_id else None,
                    title=citation.source_title,
                    source_type=str(metadata.get("source_type") or citation.retrieval_source.value),
                    content_version=str(metadata.get("content_version")) if metadata.get("content_version") else None,
                    url=citation.source_uri,
                    claim_ids=[claim_id],
                )
            )
            allowed_claims.append(citation.snippet)
        insufficient = result.grounding_status != "grounded" or not sources
        return QoraRAGResult(
            excerpt=None if insufficient else result.response.answer,
            sources=sources,
            allowed_claims=allowed_claims,
            insufficient_context=insufficient,
            warnings=result.warnings + (["insufficient_context"] if insufficient else []),
        )


class NullRAGClient:
    def retrieve(self, request: QoraRAGRequest) -> QoraRAGResult:
        _ = request
        return QoraRAGResult(insufficient_context=True, warnings=["rag_not_configured"])
