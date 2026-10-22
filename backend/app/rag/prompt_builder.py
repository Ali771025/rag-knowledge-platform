"""Grounded prompt construction for answer generation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.conversation_memory.models import ConversationContext
from app.rag.constants import REFUSAL_MESSAGE
from app.rag.schemas.context import RAGContextBundle


class PromptBuildInput(BaseModel):
    """Input payload for grounded prompt construction."""

    user_query: str = Field(min_length=1)
    context_bundle: RAGContextBundle
    conversation_context: ConversationContext | None = None
    strict_grounding: bool = True

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PromptBuildResult(BaseModel):
    """Structured prompt payload for generation backend."""

    system_prompt: str
    user_prompt: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class PromptBuilder:
    """Builds generation prompts with grounding and citation policies."""

    def build(self, payload: PromptBuildInput) -> PromptBuildResult:
        """Construct system + user prompt with context and policies."""
        policy_section = self._policy_block(strict_grounding=payload.strict_grounding)
        profile_section = self._profile_block(payload.conversation_context)
        onboarding_section = self._onboarding_block(payload.conversation_context)

        system_parts = [
            "You are a retrieval-grounded assistant.",
            "Answer in the same language as the user's question unless the user explicitly requests another language.",
            "Synthesize the evidence into a complete explanation; do not merely return search snippets.",
            policy_section,
        ]
        if onboarding_section:
            system_parts.append(onboarding_section)
        if profile_section:
            system_parts.append(profile_section)

        system_prompt = "\n\n".join(part for part in system_parts if part)

        context_text = self._format_context(payload.context_bundle)
        user_prompt = "\n\n".join(
            [
                f"User question:\n{payload.user_query.strip()}",
                "Grounding context:\n" + context_text,
                "Output format:\n"
                "- Answer only with facts supported by the Grounding context.\n"
                "- Combine relevant evidence across document chunks and graph facts, explain relationships, and resolve apparent conflicts.\n"
                "- Preserve important steps, conditions, exceptions, and definitions needed to answer the whole question.\n"
                "- Cite every factual claim with source markers like [C1], [C2].\n"
                f"- If the context does not contain the answer, respond exactly with: {REFUSAL_MESSAGE}",
            ]
        )

        metadata = {
            "trace_id": payload.context_bundle.trace_id,
            "context_notes": payload.context_bundle.notes,
            "chunk_count": len(payload.context_bundle.chunks),
            "fact_count": len(payload.context_bundle.facts),
            "graph_evidence_count": len(payload.context_bundle.graph_evidence),
            "strict_grounding": payload.strict_grounding,
            "conversation_state": payload.conversation_context.state.value if payload.conversation_context else None,
        }

        return PromptBuildResult(system_prompt=system_prompt, user_prompt=user_prompt, metadata=metadata)

    def _policy_block(self, *, strict_grounding: bool) -> str:
        answer_policy = [
            "Answer policy:",
            "1) Be accurate, concise, and directly address the user's question.",
            "2) Do not fabricate facts, sources, or citations.",
            "3) Never use outside knowledge that is not present in the context.",
        ]

        citation_policy = [
            "Citation policy:",
            "1) Cite supporting evidence with citation IDs (e.g., [C1], [C2]).",
            "2) Every non-trivial claim should have at least one supporting citation.",
            "3) If multiple sources support a claim, cite multiple IDs.",
        ]

        fallback_policy = [
            "Fallback policy when evidence is insufficient:",
            f"1) Return exactly: {REFUSAL_MESSAGE}",
            "2) Do not add extra text before or after the refusal sentence.",
        ]

        grounding_line = (
            "Grounding rule: answer only from supplied context."
            if strict_grounding
            else "Grounding rule: prefer supplied context; explicitly mark any general knowledge as unverified."
        )

        return "\n".join([grounding_line, "", *answer_policy, "", *citation_policy, "", *fallback_policy])

    def _profile_block(self, context: ConversationContext | None) -> str:
        if context is None:
            return ""

        profile = context.user_profile
        hints: list[str] = []
        if profile.first_name:
            hints.append(f"user_first_name={profile.first_name}")
        if profile.preferences:
            preferred = profile.preferences.get("language")
            if isinstance(preferred, str) and preferred.strip():
                hints.append(f"preferred_language={preferred.strip()}")

        if not hints:
            return ""

        return "User profile hints:\n- " + "\n- ".join(hints)

    def _onboarding_block(self, context: ConversationContext | None) -> str:
        if context is None:
            return ""

        return (
            "Onboarding phase guidance:\n"
            f"- Current phase: {context.state.value}\n"
            "- Tailor explanation depth and next steps to this phase."
        )

    def _format_context(self, bundle: RAGContextBundle) -> str:
        lines: list[str] = []

        if bundle.chunks:
            lines.append("[Document chunks]")
            for chunk in bundle.chunks:
                metadata = dict(chunk.metadata or {})
                citation = metadata.get("citation_id", "N/A")
                source = chunk.source_title or chunk.source_uri or chunk.source_id
                snippet = self._clip(chunk.content, limit=1200)
                lines.append(f"- [{citation}] source={source} doc={chunk.document_id} text={snippet}")

        if bundle.facts:
            lines.append("[Graph facts]")
            for fact in bundle.facts:
                metadata = dict(fact.metadata or {})
                citation = metadata.get("citation_id", "N/A")
                llm_statement = metadata.get("llm_statement") or f"{fact.subject} --{fact.predicate}--> {fact.obj}"
                lines.append(f"- [{citation}] {llm_statement}")

        if bundle.graph_evidence:
            lines.append("[Graph evidence snippets]")
            for evidence in bundle.graph_evidence:
                metadata = dict(evidence.metadata or {})
                citation = metadata.get("citation_id", "N/A")
                summary = metadata.get("llm_summary") or evidence.path_summary
                lines.append(f"- [{citation}] {self._clip(str(summary), limit=600)}")

        if not lines:
            return "No retrieval evidence available."

        return "\n".join(lines)

    def _clip(self, text: str, *, limit: int) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3] + "..."
