from __future__ import annotations

import json
from typing import Any, Protocol

from app.qora.domain.enums import ConversationStage, PersonaCore, PersonaModifier
from app.qora.domain.orchestration_contracts import (
    CTA,
    CompositionContext,
    NextBestAction,
    OrchestratorResponse,
    Progress,
    UIBlock,
    UIOption,
)


class ComposerLLM(Protocol):
    def send_prompt(
        self,
        system: str | dict[str, Any],
        messages: list[dict[str, str]] | None = None,
        context: dict[str, Any] | None = None,
        grounded: bool = False,
    ) -> str: ...


class ResponseComposer:
    def __init__(self, llm: ComposerLLM | None = None) -> None:
        self.llm = llm

    def compose(
        self,
        *,
        request_id: str,
        conversation_id: str,
        context: CompositionContext,
        force_safe: bool = False,
    ) -> OrchestratorResponse:
        message, response_type, ui = self._deterministic_body(context)
        if self.llm is not None and context.rag_excerpt and not force_safe:
            generated = self._compose_with_llm(context)
            if generated:
                message = generated
        primary, secondary = self._cta_policy(context)
        return OrchestratorResponse(
            request_id=request_id,
            conversation_id=conversation_id,
            stage=context.conversation_stage,
            message=message,
            response_type=response_type,
            ui=ui,
            primary_cta=primary,
            secondary_cta=secondary,
            progress=self._progress(context.conversation_stage),
            sources=context.rag_sources,
            warnings=["insufficient_context"] if context.insufficient_context else [],
            next_best_action=context.next_best_action,
        )

    def safe_fallback(self, *, request_id: str, conversation_id: str, stage: ConversationStage) -> OrchestratorResponse:
        return OrchestratorResponse(
            request_id=request_id,
            conversation_id=conversation_id,
            stage=stage,
            message="برای پاسخ دقیق‌تر، اطلاعات معتبر کافی در دسترس نیست. می‌توانیم مسیر را با یک سؤال کوتاه ادامه دهیم.",
            response_type="SAFE_FALLBACK",
            ui=UIBlock(type="TEXT"),
            progress=self._progress(stage),
            warnings=["guardrail_fallback", "insufficient_context"],
            next_best_action=NextBestAction(type="CONTINUE_DISCOVERY"),
        )

    def _deterministic_body(self, context: CompositionContext) -> tuple[str, str, UIBlock]:
        stage = context.conversation_stage
        if stage == ConversationStage.GREETING:
            return (
                "سلام. من QORA هستم؛ برای شناخت مسیرهای اکوسیستم و مقایسه گزینه‌ها کنارت هستم. تصمیم نهایی همیشه با خودت است.",
                "GREETING", UIBlock(type="TEXT"),
            )
        if stage == ConversationStage.WHAT_IS_THIS:
            return (
                "QORA یک راهنمای تصمیم است که مسیرهای سرمایه‌گذاری، کسب درآمد، سهامداری، توسعه و آموزش را بر اساس نیازت بررسی می‌کند؛ نه اینکه به‌جای تو تصمیم بگیرد.",
                "ECOSYSTEM_OVERVIEW", self._section_ui(),
            )
        if context.qualification_question is not None:
            question = context.qualification_question
            return (
                question.text,
                "QUALIFICATION_QUESTION",
                UIBlock(type="QUESTION_OPTIONS", options=question.options),
            )
        if context.matched_product:
            if context.insufficient_context or not context.rag_sources:
                return (
                    "مسیر مناسب مشخص شده، اما برای معرفی دقیق محصول هنوز سند معتبر کافی در دسترس نیست. بهتر است ابتدا سند رسمی را بررسی کنیم.",
                    "INSUFFICIENT_PRODUCT_CONTEXT", UIBlock(type="TEXT"),
                )
            prefix = self._recognize(context.persona_core, context.modifiers)
            explanation = context.rag_excerpt or ""
            message = f"{prefix} {explanation}".strip()
            ui_type = "ACHIEVEMENT" if context.achievement_context else "PRODUCT_GUIDANCE"
            return message, "PRODUCT_GUIDANCE", UIBlock(
                type=ui_type,
                achievement_card=context.achievement_context,
                level_card=context.level_card,
            )
        if stage == ConversationStage.SECTION_DISCOVERY:
            return (
                "کدام مسیر برایت مهم‌تر است: سرمایه‌گذاری، کسب درآمد، سهامداری، توسعه یا آموزش؟",
                "SECTION_DISCOVERY", self._section_ui(),
            )
        return (
            "برای اینکه مسیر مناسب‌تری پیشنهاد بدهم، اطلاعات را مرحله‌به‌مرحله کامل می‌کنیم.",
            "GUIDANCE", UIBlock(type="TEXT"),
        )

    def _compose_with_llm(self, context: CompositionContext) -> str | None:
        system = (
            "Convert the supplied deterministic QORA decision into Persian guidance using Recognize, Frame, Match, "
            "Explain, Guide. Do not select another product, disclose persona, guarantee returns, provide legal certainty, "
            "invent claims, citations, or instructions. Return JSON with only a message field."
        )
        payload = {
            "style": self._style_policy(context.persona_core, context.modifiers),
            "depth": context.depth_level.value,
            "product": context.matched_product,
            "section": context.selected_section.value if context.selected_section else None,
            "priority_reason": context.priority_reason,
            "grounded_excerpt": context.rag_excerpt,
            "allowed_claims": context.allowed_claims,
            "forbidden_claims": context.forbidden_claims,
        }
        try:
            raw = self.llm.send_prompt(
                system=system,
                messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
                context={"structured_output": {"message": "string"}},
                grounded=True,
            )
            parsed = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
            message = parsed.get("message") if isinstance(parsed, dict) else None
            return str(message).strip() if message else None
        except Exception:
            return None

    def _cta_policy(self, context: CompositionContext) -> tuple[CTA | None, CTA | None]:
        if context.conversation_stage not in {
            ConversationStage.CTA, ConversationStage.NEXT_BEST_ACTION, ConversationStage.PRODUCT_INTRODUCTION,
        }:
            return None, None
        if not context.matched_product or context.insufficient_context:
            return CTA(type="VIEW_DOCUMENTS", label="مشاهده اسناد رسمی"), None
        if PersonaModifier.TRUST_LOW in context.modifiers:
            return CTA(type="VIEW_EXPLAINER", label="مشاهده توضیح کوتاه"), CTA(
                type="VIEW_DOCUMENTS", label="دیدن سند رسمی"
            )
        if context.readiness_score < 0.4:
            return CTA(type="VIEW_EXPLAINER", label="مشاهده توضیح کوتاه"), None
        if context.readiness_score >= 0.8:
            return CTA(type="START_GUIDED_FLOW", label="شروع مسیر هدایت‌شده"), CTA(
                type="VIEW_ALTERNATIVES", label="دیدن گزینه‌های دیگر"
            )
        return CTA(type="VIEW_EXPLAINER", label="مشاهده توضیح کوتاه"), CTA(
            type="VIEW_ALTERNATIVES", label="دیدن گزینه‌های دیگر"
        )

    @staticmethod
    def _recognize(persona: PersonaCore | None, modifiers: list[PersonaModifier]) -> str:
        if PersonaModifier.TRUST_LOW in modifiers:
            return "حق داری قبل از هر اقدامی سازوکار و ریسک‌ها را شفاف ببینی."
        if PersonaModifier.REGULATION_SENSITIVE in modifiers:
            return "این توضیح راهنمای عمومی است و دامنه آن را باید با سند رسمی و شرایط معتبر بررسی کرد."
        if PersonaModifier.REGULATION_SENSITIVE in modifiers:
            return "این توضیح راهنمای عمومی است و دامنه آن را باید با سند رسمی و شرایط معتبر بررسی کرد."
        if persona == PersonaCore.HUNTER:
            return "برای مقایسه سریع و روشن، نکات اصلی این مسیر را مرور کنیم."
        if persona == PersonaCore.PLAYER:
            return "این مسیر را می‌توانیم در چند گام مشخص بررسی کنیم."
        if persona == PersonaCore.ARCHITECT:
            return "برای ارزیابی ساختاری، منطق و trade-offهای این مسیر مهم‌اند."
        return "برای تصمیم مطمئن‌تر، سازوکار و محدودیت‌ها را شفاف بررسی کنیم."

    @staticmethod
    def _style_policy(persona: PersonaCore | None, modifiers: list[PersonaModifier]) -> list[str]:
        policies = {
            PersonaCore.SAVER: ["calm", "transparent", "risk-aware", "no pressure"],
            PersonaCore.HUNTER: ["concise", "comparative", "result-oriented", "no guarantees"],
            PersonaCore.PLAYER: ["stepwise", "progress-oriented", "checkpoint-based"],
            PersonaCore.ARCHITECT: ["structured", "analytical", "trade-off-aware", "source-backed"],
        }.get(persona, ["neutral", "discovery-oriented"])
        return [*policies, *(modifier.value for modifier in modifiers)]

    @staticmethod
    def _progress(stage: ConversationStage) -> Progress:
        groups = [
            {ConversationStage.START, ConversationStage.GREETING, ConversationStage.WHAT_IS_THIS},
            {ConversationStage.SIGNAL_CAPTURE, ConversationStage.PERSONA_CLASSIFICATION, ConversationStage.MODIFIER_CLASSIFICATION, ConversationStage.DEPTH_SELECTION},
            {ConversationStage.SECTION_DISCOVERY, ConversationStage.NEED_QUALIFICATION},
            {ConversationStage.WEIGHT_MATCHING, ConversationStage.PRODUCT_PRIORITIZATION, ConversationStage.PRODUCT_INTRODUCTION},
            {ConversationStage.ACHIEVEMENT_OVERLAY, ConversationStage.CTA, ConversationStage.NEXT_BEST_ACTION, ConversationStage.FEEDBACK_OBSERVATION, ConversationStage.PERSONA_REASSESSMENT},
        ]
        step = next((index for index, values in enumerate(groups, start=1) if stage in values), 1)
        return Progress(current_step=step, total_steps=5)

    @staticmethod
    def _section_ui() -> UIBlock:
        labels = {
            "INVESTMENT": "سرمایه‌گذاری",
            "EARN": "کسب درآمد",
            "STOCKHOLDERS": "سهامداری",
            "DEVELOPMENT": "توسعه",
            "EDUCATION": "آموزش",
        }
        return UIBlock(
            type="SECTION_OPTIONS",
            options=[UIOption(id=value, label=label, value=value) for value, label in labels.items()],
        )
