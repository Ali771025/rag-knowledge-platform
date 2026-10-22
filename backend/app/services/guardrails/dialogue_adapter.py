"""Thin adapter for Dialogue Manager integration with guardrails contracts."""

from __future__ import annotations

import re

from app.services.guardrails.constants import FALLBACK_MESSAGES
from app.services.guardrails.models import (
    Document,
    PreSafetyResult,
    SafetyOrchestratorResult,
    ValidationResult,
)
from app.services.guardrails.retrieval_validator import validate_retrieval
from app.services.guardrails.safety_orchestrator import (
    post_check_generated_response,
    pre_check_user_query,
)

_PERSIAN_CHAR_RE = re.compile(r"[\u0600-\u06ff]")


class GuardrailsDialogueAdapter:
    """Bridges dialogue flow inputs/outputs to guardrails pre/post checks."""

    def run_pre_generation_safety(
        self,
        *,
        user_query: str,
        user_state: str | None = None,
        trace_id: str | None = None,
    ) -> PreSafetyResult:
        return pre_check_user_query(
            user_query=user_query,
            user_state=user_state,
            trace_id=trace_id,
        )

    def run_post_generation_safety(
        self,
        *,
        user_query: str,
        retrieved_docs: list[Document],
        llm_response: str,
        user_state: str | None = None,
        intent_score: float | None = None,
        trace_id: str | None = None,
    ) -> SafetyOrchestratorResult:
        return post_check_generated_response(
            user_query=user_query,
            retrieved_docs=retrieved_docs,
            llm_response=llm_response,
            user_state=user_state,
            intent_score=intent_score,
            trace_id=trace_id,
        )

    def run_retrieval_validation(
        self,
        *,
        user_query: str,
        retrieved_docs: list[Document],
        user_state: str | None = None,
    ) -> ValidationResult:
        return validate_retrieval(
            query=user_query,
            retrieved_docs=retrieved_docs,
            user_state=user_state,
        )

    def resolve_fallback_message(self, *, fallback_key: str, user_query: str) -> str:
        language = "fa" if _PERSIAN_CHAR_RE.search(user_query) else "en"
        selected = FALLBACK_MESSAGES.get(fallback_key) or FALLBACK_MESSAGES["low_confidence"]
        return selected.get(language, selected.get("en", ""))
