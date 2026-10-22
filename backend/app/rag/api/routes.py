"""RAG FastAPI routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.rag_configuration import RAGConfiguration
from app.rag.dependencies import (
    get_context_manager,
    get_rag_orchestrator,
    get_session_manager,
    resolve_conversation_context,
)
from app.rag.models.rag_types import RetrievalSource
from app.rag.prompt_builder import PromptBuildInput, PromptBuilder
from app.rag.rag_orchestrator import RAGOrchestrator, RAGOrchestratorInput
from app.rag.schemas.context import RAGContextBundle
from app.rag.schemas.retrieval import RetrievalPlan, RetrievedChunk
from app.services.llm_service import LLMService

router = APIRouter()


class RAGQueryEndpointRequest(BaseModel):
    """Request body for RAG query endpoint."""

    user_query: str = Field(min_length=1)
    session_id: str | None = None
    filters: dict[str, Any] | None = None
    knowledge_labels: list[str] | None = None
    memory_scope: str | None = Field(default=None, min_length=1, max_length=64)
    retrieval_sources: list[RetrievalSource] | None = None
    top_k: int = Field(default=12, ge=1, le=100)
    strict_grounding: bool = True
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("knowledge_labels")
    @classmethod
    def _normalize_labels(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in value:
            label = " ".join(str(raw or "").strip().split()).lower()
            if not label:
                continue
            if label in seen:
                continue
            seen.add(label)
            normalized.append(label)
        return normalized

    @field_validator("memory_scope")
    @classmethod
    def _normalize_memory_scope(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.strip().split()).lower()
        return normalized or None


class RAGQueryEndpointResponse(BaseModel):
    """Stable response format for RAG endpoint."""

    trace_id: str
    answer: str
    citations: list[dict[str, Any]]
    confidence: str
    grounded: bool
    grounding_status: str
    retrieval_summary: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class RAGGenerateResponse(BaseModel):
    text: str
    mode: str
    prompt_metadata: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid")


@router.post(
    "/query",
    response_model=RAGQueryEndpointResponse,
)
def rag_query(
    payload: RAGQueryEndpointRequest,
    orchestrator: RAGOrchestrator = Depends(get_rag_orchestrator),
    session_manager=Depends(get_session_manager),
    context_manager=Depends(get_context_manager),
    db: Session = Depends(get_db),
) -> RAGQueryEndpointResponse:
    """Execute full RAG query flow via orchestrator."""
    conversation_context = resolve_conversation_context(
        session_id=payload.session_id,
        user_query=payload.user_query,
        session_manager=session_manager,
        context_manager=context_manager,
    )

    effective_labels = _resolve_effective_labels(payload=payload, db=db)
    effective_filters = _build_effective_filters(payload.filters, effective_labels)
    metadata = dict(payload.metadata or {})
    if effective_labels:
        metadata["knowledge_labels"] = list(effective_labels)
    if payload.memory_scope:
        metadata["memory_scope"] = payload.memory_scope

    result = orchestrator.run(
        RAGOrchestratorInput(
            user_query=payload.user_query,
            conversation_context=conversation_context,
            filters=effective_filters,
            retrieval_sources=payload.retrieval_sources,
            top_k=payload.top_k,
            strict_grounding=payload.strict_grounding,
            metadata=metadata or None,
        )
    )

    return RAGQueryEndpointResponse(
        trace_id=result.trace_id,
        answer=result.response.answer,
        citations=[item.model_dump(mode="json") for item in result.response.citations],
        confidence=result.response.confidence_level.value,
        grounded=bool((result.response.metadata or {}).get("grounded", False)),
        grounding_status=result.grounding_status,
        retrieval_summary=result.retrieval_summary,
        warnings=result.warnings,
    )


@router.post("/generate", response_model=RAGGenerateResponse)
def generate_with_llm(payload: dict[str, Any]) -> RAGGenerateResponse:
    """Compatibility generation endpoint.

    Raw contract remains supported:
    - {\"prompt\": \"...\"}

    Structured path:
    - {\"question\": \"...\", \"context\": ...}
    """
    llm_service = LLMService()

    prompt_value = payload.get("prompt")
    if isinstance(prompt_value, str) and prompt_value.strip():
        text = llm_service.send_prompt(payload)
        return RAGGenerateResponse(text=text, mode="raw_prompt")

    question = payload.get("question")
    if not isinstance(question, str) or not question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="payload must include either non-empty 'prompt' or 'question'",
        )
    context_value = payload.get("context")
    if context_value is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="structured generation payload requires 'context'",
        )

    prompt_payload = PromptBuilder().build(
        PromptBuildInput(
            user_query=question.strip(),
            context_bundle=_context_bundle_from_structured_payload(question=question, context=context_value),
            strict_grounding=True,
        )
    )
    generated = llm_service.send_prompt(
        system=prompt_payload.system_prompt,
        messages=[{"role": "user", "content": prompt_payload.user_prompt}],
        context={"request_mode": "structured_question_context"},
        grounded=True,
    )
    return RAGGenerateResponse(
        text=generated,
        mode="question_context",
        prompt_metadata=dict(prompt_payload.metadata),
    )


def _resolve_effective_labels(*, payload: RAGQueryEndpointRequest, db: Session) -> list[str]:
    if payload.knowledge_labels:
        return list(payload.knowledge_labels)

    if isinstance(payload.filters, dict):
        labels_value = payload.filters.get("labels")
        if isinstance(labels_value, list):
            labels = _normalize_labels(labels_value)
            if labels:
                return labels
        label_value = payload.filters.get("label")
        if isinstance(label_value, str):
            label = _normalize_labels([label_value])
            if label:
                return label

    config = db.scalar(select(RAGConfiguration).order_by(RAGConfiguration.created_at.asc()).limit(1))
    if config is None:
        return []
    return _normalize_labels(config.default_labels or [])


def _normalize_labels(value: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in value:
        label = " ".join(str(raw or "").strip().split()).lower()
        if not label:
            continue
        if label in seen:
            continue
        seen.add(label)
        normalized.append(label)
    return normalized


def _build_effective_filters(base_filters: dict[str, Any] | None, labels: list[str]) -> dict[str, Any] | None:
    merged: dict[str, Any] = dict(base_filters or {})
    if not labels:
        return merged or None

    merged["labels"] = list(labels)
    if "label" not in merged and labels:
        merged["label"] = labels[0]

    qdrant_payload = dict(merged.get("qdrant") or {})
    must = list(qdrant_payload.get("must") or [])
    has_label_filter = any(
        isinstance(item, dict) and item.get("key") == "label"
        for item in must
    )
    if not has_label_filter:
        must.append({"key": "label", "match": {"any": list(labels)}})
    qdrant_payload["must"] = must
    merged["qdrant"] = qdrant_payload
    return merged


def _context_bundle_from_structured_payload(*, question: str, context: Any) -> RAGContextBundle:
    snippets: list[str] = []
    if isinstance(context, str):
        text = context.strip()
        if text:
            snippets = [text]
    elif isinstance(context, list):
        snippets = [str(item).strip() for item in context if str(item).strip()]
    elif isinstance(context, dict):
        snippets = [str(value).strip() for value in context.values() if str(value).strip()]
    else:
        text = str(context).strip()
        if text:
            snippets = [text]

    chunks: list[RetrievedChunk] = []
    for index, snippet in enumerate(snippets[:8], start=1):
        citation_id = f"C{index}"
        chunks.append(
            RetrievedChunk(
                chunk_id=f"structured-{index}",
                trace_id="structured-generate",
                retrieval_source=RetrievalSource.VECTOR,
                source_id="structured_input",
                document_id="structured_input",
                content=snippet,
                score=1.0,
                rank=index,
                metadata={"citation_id": citation_id, "source_type": "structured"},
            )
        )

    return RAGContextBundle(
        trace_id="structured-generate",
        plan=RetrievalPlan(trace_id="structured-generate", sources=[RetrievalSource.VECTOR], notes=f"structured_context:{question[:80]}"),
        chunks=chunks,
    )
