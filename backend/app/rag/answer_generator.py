"""Answer generation wrapper over the existing LLM service abstraction."""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.rag.prompt_builder import PromptBuildResult
from app.rag.schemas.context import RAGContextBundle
from app.services.llm_service import LLMService


class LLMInferenceAdapter(Protocol):
    """Provider-agnostic LLM interface used by the answer generator."""

    def send_prompt(
        self,
        system: str,
        messages: list[dict[str, str]],
        context: dict[str, Any] | None = None,
        grounded: bool = False,
    ) -> str:
        """Send a prompt to the underlying inference layer and return text."""


class AnswerGenerationInput(BaseModel):
    """Input payload for answer generation."""

    trace_id: str
    prompt_payload: PromptBuildResult
    context_bundle: RAGContextBundle | None = None

    model_config = ConfigDict(extra="forbid")


class GeneratedAnswer(BaseModel):
    """Structured answer object returned by generator wrapper."""

    trace_id: str
    answer: str = Field(min_length=1)
    model_name: str | None = None
    used_fallback: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AnswerGenerator:
    """Wrapper that delegates answer generation to existing LLM abstraction."""

    def __init__(self, llm_service: LLMInferenceAdapter | None = None) -> None:
        self.llm_service = llm_service or LLMService()

    def generate(self, payload: AnswerGenerationInput) -> GeneratedAnswer:
        """Generate answer text using the configured LLM service interface."""
        messages = [
            {
                "role": "user",
                "content": payload.prompt_payload.user_prompt,
            }
        ]

        context: dict[str, Any] = {
            "trace_id": payload.trace_id,
            "prompt_metadata": payload.prompt_payload.metadata,
        }
        if payload.context_bundle is not None:
            context["retrieval_summary"] = {
                "chunks": len(payload.context_bundle.chunks),
                "facts": len(payload.context_bundle.facts),
                "graph_evidence": len(payload.context_bundle.graph_evidence),
                "notes": payload.context_bundle.notes,
            }

        answer_text = self.llm_service.send_prompt(
            system=payload.prompt_payload.system_prompt,
            messages=messages,
            context=context,
            grounded=True,
        )
        cleaned = self._normalize_answer(answer_text)

        used_fallback = cleaned.startswith("[DEV FALLBACK]")
        model_name = getattr(self.llm_service, "default_model", None)

        return GeneratedAnswer(
            trace_id=payload.trace_id,
            answer=cleaned,
            model_name=str(model_name) if model_name else None,
            used_fallback=used_fallback,
            metadata={
                "message_count": len(messages),
                "used_context": payload.context_bundle is not None,
                "prompt_metadata": payload.prompt_payload.metadata,
            },
        )

    def _normalize_answer(self, answer: str) -> str:
        lines = [" ".join(line.split()) for line in str(answer).splitlines()]
        cleaned_lines: list[str] = []
        previous_blank = False
        for line in lines:
            if not line:
                if cleaned_lines and not previous_blank:
                    cleaned_lines.append("")
                previous_blank = True
                continue
            cleaned_lines.append(line)
            previous_blank = False
        cleaned = "\n".join(cleaned_lines).strip()
        if cleaned:
            return cleaned
        return "Evidence is currently insufficient to provide a grounded answer."
