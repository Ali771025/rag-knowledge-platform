from __future__ import annotations

import re
from typing import Sequence

from app.qora.domain.enums import ConversationStage, DepthLevel, PersonaModifier
from app.qora.domain.orchestration_contracts import CompositionContext, GuardrailResult, OrchestratorResponse
from app.services.guardrails.prompt_injection_detector import detect_prompt_injection

_PERSONA_DISCLOSURE = re.compile(
    r"\b(?:SAVER|HUNTER|PLAYER|ARCHITECT)\b|پرسونای\s+(?:شما|تو)|شخصیت\s+(?:شما|تو)",
    re.IGNORECASE,
)
_FINANCIAL_GUARANTEE = re.compile(r"(?:سود|بازده).{0,20}(?:تضمینی|قطعی)|guaranteed (?:return|profit)", re.IGNORECASE)
_LEGAL_CERTAINTY = re.compile(r"(?:کاملاً قانونی|تضمین قانونی|قطعاً قانونی)|legally guaranteed", re.IGNORECASE)
_PROMPT_LEAKAGE = re.compile(r"system prompt|developer message|internal instruction|پرامپت سیستم|دستور داخلی", re.IGNORECASE)
_AGGRESSIVE = re.compile(r"همین حالا|فوراً|فرصت را از دست نده|buy now|act now", re.IGNORECASE)


class QoraGuardrailValidator:
    def validate(
        self,
        *,
        response: OrchestratorResponse,
        context: CompositionContext,
        user_message: str,
        known_product_ids: Sequence[str],
    ) -> GuardrailResult:
        reasons: list[str] = []
        injection = detect_prompt_injection(user_message)
        if injection.is_malicious:
            reasons.append("PROMPT_INJECTION")
        if _PERSONA_DISCLOSURE.search(response.message):
            reasons.append("PERSONA_DISCLOSURE")
        if _FINANCIAL_GUARANTEE.search(response.message):
            reasons.append("FINANCIAL_GUARANTEE")
        if _LEGAL_CERTAINTY.search(response.message):
            reasons.append("LEGAL_CERTAINTY")
        if _PROMPT_LEAKAGE.search(response.message):
            reasons.append("PROMPT_LEAKAGE")
        if any(claim.lower() in response.message.lower() for claim in context.forbidden_claims):
            reasons.append("FORBIDDEN_CLAIM")
        mentioned_products = [product for product in known_product_ids if re.search(rf"\b{re.escape(product)}\b", response.message, re.IGNORECASE)]
        if any(product != context.matched_product for product in mentioned_products):
            reasons.append("HALLUCINATED_PRODUCT")
        if response.response_type == "PRODUCT_GUIDANCE":
            if context.conversation_stage.value not in {
                ConversationStage.PRODUCT_INTRODUCTION.value,
                ConversationStage.ACHIEVEMENT_OVERLAY.value,
                ConversationStage.CTA.value,
                ConversationStage.NEXT_BEST_ACTION.value,
            } or not context.matched_product:
                reasons.append("PREMATURE_PRODUCT_INTRODUCTION")
            if not response.sources:
                reasons.append("MISSING_CITATION")
            elif any(
                not all((source.source_id, source.chunk_id, source.title, source.source_type, source.content_version))
                for source in response.sources
            ):
                reasons.append("INCOMPLETE_SOURCE")
        if PersonaModifier.TRUST_LOW in context.modifiers:
            if response.primary_cta and response.primary_cta.type in {"BUY", "CONNECT_WALLET", "START_NOW"}:
                reasons.append("AGGRESSIVE_CTA")
            if _AGGRESSIVE.search(response.message):
                reasons.append("AGGRESSIVE_CTA")
        allowed_ctas = {
            "VIEW_DOCUMENTS", "VIEW_EXPLAINER", "VIEW_ALTERNATIVES", "START_GUIDED_FLOW"
        }
        for cta in (response.primary_cta, response.secondary_cta):
            if cta and cta.type not in allowed_ctas:
                reasons.append("UNSAFE_EXTERNAL_ACTION")
        words = len(response.message.split())
        if context.depth_level == DepthLevel.LOW and words > 130:
            reasons.append("DEPTH_MISMATCH")
        if context.depth_level == DepthLevel.HIGH and response.response_type == "PRODUCT_GUIDANCE" and words < 12:
            reasons.append("DEPTH_MISMATCH")
        if context.insufficient_context and response.response_type == "PRODUCT_GUIDANCE":
            reasons.append("UNSUPPORTED_CLAIM")
        return GuardrailResult(
            valid=not reasons,
            reason_codes=list(dict.fromkeys(reasons)),
            severity="BLOCK" if reasons else "NONE",
        )
