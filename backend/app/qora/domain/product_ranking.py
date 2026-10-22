from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from app.qora.domain.enums import PersonaCore, PersonaModifier, Section
from app.qora.domain.orchestration_contracts import (
    ProductScoreComponents,
    RankedProduct,
    RankingDecision,
)


DEFAULT_PRODUCT_WEIGHTS: dict[str, dict[PersonaCore, float]] = {
    "ETER": {PersonaCore.SAVER: 1, PersonaCore.HUNTER: 1, PersonaCore.ARCHITECT: 1, PersonaCore.PLAYER: 4},
    "Q": {PersonaCore.SAVER: 4, PersonaCore.HUNTER: 3, PersonaCore.ARCHITECT: 5, PersonaCore.PLAYER: 1},
    "STAKING": {PersonaCore.SAVER: 3, PersonaCore.HUNTER: 2, PersonaCore.ARCHITECT: 4, PersonaCore.PLAYER: 5},
    "EID": {PersonaCore.SAVER: 5, PersonaCore.HUNTER: 5, PersonaCore.ARCHITECT: 3, PersonaCore.PLAYER: 3},
    "INSURANCE": {PersonaCore.SAVER: 2, PersonaCore.HUNTER: 4, PersonaCore.ARCHITECT: 2, PersonaCore.PLAYER: 2},
    "EES": {PersonaCore.SAVER: 1, PersonaCore.HUNTER: 1, PersonaCore.ARCHITECT: 2, PersonaCore.PLAYER: 1},
    "ERA": {PersonaCore.SAVER: 2, PersonaCore.HUNTER: 2, PersonaCore.ARCHITECT: 1, PersonaCore.PLAYER: 2},
    "PROPOSAL": {PersonaCore.SAVER: 2, PersonaCore.HUNTER: 2, PersonaCore.ARCHITECT: 1, PersonaCore.PLAYER: 2},
    "ELITE": {PersonaCore.SAVER: 1, PersonaCore.HUNTER: 1, PersonaCore.ARCHITECT: 2, PersonaCore.PLAYER: 1},
    "FAN_COMMUNITY": {persona: 2 for persona in PersonaCore},
    "REFERRAL_INSURANCE": {PersonaCore.SAVER: 1, PersonaCore.HUNTER: 3, PersonaCore.ARCHITECT: 3, PersonaCore.PLAYER: 3},
    "FORECAST": {PersonaCore.SAVER: 3, PersonaCore.HUNTER: 1, PersonaCore.ARCHITECT: 1, PersonaCore.PLAYER: 1},
    "EDGE": {persona: 1 for persona in PersonaCore},
}


@dataclass(frozen=True, slots=True)
class ProductPolicyItem:
    product_id: str
    section: Section
    is_active: bool = True
    rag_ready: bool = True
    compliance_flag: str = "CLEAR"
    restrictions: Mapping[str, Any] = field(default_factory=dict)
    base_risk_penalty: float = 0.0
    base_friction_penalty: float = 0.0
    metadata: Mapping[str, Any] = field(default_factory=dict)


class ProductRankingEngine:
    def rank(
        self,
        *,
        section: Section,
        persona: PersonaCore | None,
        persona_confidence: float,
        products: Sequence[ProductPolicyItem],
        persona_weights: Mapping[str, float],
        weight_table_version: str,
        intent_confidence: float,
        qualification_complete: bool,
        qualification_match: Mapping[str, float] | None,
        readiness_score: float,
        behavior_match: Mapping[str, float] | None,
        modifiers: Sequence[PersonaModifier],
        explicit_product_id: str | None = None,
    ) -> RankingDecision:
        ranked: list[RankedProduct] = []
        explicit = (explicit_product_id or "").upper()
        for product in products:
            exclusion: list[str] = []
            if not product.is_active:
                exclusion.append("PRODUCT_INACTIVE")
            if not product.rag_ready:
                exclusion.append("MISSING_PUBLISHED_RAG_CONTENT")
            if product.compliance_flag != "CLEAR":
                exclusion.append(f"COMPLIANCE_{product.compliance_flag}")
            if bool(product.restrictions.get("blocked", False)):
                exclusion.append("USER_RESTRICTION")
            eligible = not exclusion
            persona_weight = float(persona_weights.get(product.product_id, 0.0)) if persona else 0.0
            intent_match = 1.0 if explicit == product.product_id else float(intent_confidence)
            qualification_score = float((qualification_match or {}).get(product.product_id, 1.0 if qualification_complete else 0.0))
            behavior_score = float((behavior_match or {}).get(product.product_id, 0.0))
            risk_penalty = max(0.0, product.base_risk_penalty)
            friction_penalty = max(0.0, product.base_friction_penalty)
            if PersonaModifier.REGULATION_SENSITIVE in modifiers and product.metadata.get("regulated") is not True:
                risk_penalty += 0.15
            if PersonaModifier.TRUST_LOW in modifiers and product.metadata.get("high_friction") is True:
                friction_penalty += 0.15
            eligibility_score = 1.0 if eligible else 0.0
            final_score = (
                persona_weight + intent_match + qualification_score + eligibility_score
                + readiness_score + behavior_score - risk_penalty - friction_penalty
            )
            reasons = [f"PERSONA_WEIGHT_{persona_weight:g}", f"SECTION_{section.value}"]
            if explicit == product.product_id:
                reasons.append("EXPLICIT_PRODUCT_REQUEST")
            if persona and persona_weight == max(persona_weights.values(), default=0.0):
                reasons.append(f"TOP_{persona.value}_{section.value}_WEIGHT")
            ranked.append(
                RankedProduct(
                    product_id=product.product_id,
                    section=product.section,
                    eligible=eligible,
                    scores=ProductScoreComponents(
                        persona_weight=persona_weight,
                        intent_match=intent_match,
                        qualification_match=qualification_score,
                        eligibility=eligibility_score,
                        readiness_score=readiness_score,
                        behavior_match=behavior_score,
                        risk_penalty=risk_penalty,
                        friction_penalty=friction_penalty,
                        final_score=round(final_score, 6),
                    ),
                    reason_codes=reasons,
                    exclusion_reasons=exclusion,
                )
            )
        ranked.sort(
            key=lambda item: (-item.scores.final_score, -item.scores.persona_weight, item.product_id)
        )
        eligible_ranked = [item for item in ranked if item.eligible]
        confident = persona is not None and persona_confidence >= 0.62 and qualification_complete
        matched = eligible_ranked[0] if confident and eligible_ranked else None
        return RankingDecision(
            weight_table_version=weight_table_version,
            ranked_products=ranked,
            matched_product=matched,
            confidence=persona_confidence if matched else min(persona_confidence, 0.5),
            priority_reason=(matched.reason_codes[-1] if matched else None),
        )
