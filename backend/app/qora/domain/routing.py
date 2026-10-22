from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Mapping, Sequence

from app.qora.domain.contracts import SignalCandidate
from app.qora.domain.enums import PersonaCore, Section
from app.qora.domain.orchestration_contracts import IntentDecision, SectionDecision

SECTION_KEYWORDS: dict[Section, tuple[str, ...]] = {
    Section.INVESTMENT: ("investment", "invest", "سرمایه", "ریسک", "بازده", "نقدشوندگی"),
    Section.EARN: ("earn", "income", "درآمد", "کسب", "ارجاع", "فعالیت"),
    Section.STOCKHOLDERS: ("stockholder", "shareholder", "سهامدار", "حق رای", "مالکیت"),
    Section.DEVELOPMENT: ("develop", "code", "proposal", "توسعه", "کدنویسی", "طراحی"),
    Section.EDUCATION: ("education", "learn", "course", "آموزش", "یادگیری", "مبتدی"),
}

PRODUCT_SECTIONS: dict[str, Section] = {
    "ETER": Section.INVESTMENT, "Q": Section.INVESTMENT, "STAKING": Section.INVESTMENT,
    "EID": Section.INVESTMENT, "INSURANCE": Section.INVESTMENT,
    "EES": Section.STOCKHOLDERS, "ERA": Section.STOCKHOLDERS,
    "PROPOSAL": Section.DEVELOPMENT, "ELITE": Section.DEVELOPMENT,
    "FAN_COMMUNITY": Section.EARN, "REFERRAL_INSURANCE": Section.EARN, "FORECAST": Section.EARN,
    "EDGE": Section.EDUCATION,
}


class IntentDetector:
    def detect(self, message: str) -> IntentDecision:
        normalized = re.sub(r"\s+", " ", message.strip().lower())
        matches: list[tuple[Section, list[str]]] = []
        for section, keywords in SECTION_KEYWORDS.items():
            hits = [keyword for keyword in keywords if keyword in normalized]
            if hits:
                matches.append((section, hits))
        if not matches:
            return IntentDecision(name="DISCOVER_ECOSYSTEM", confidence=0.35, evidence=[])
        matches.sort(key=lambda item: (-len(item[1]), item[0].value))
        section, evidence = matches[0]
        confidence = min(0.95, 0.58 + 0.1 * len(evidence))
        if len(matches) > 1 and len(matches[1][1]) == len(evidence):
            confidence = min(confidence, 0.55)
        return IntentDecision(name=f"EXPLORE_{section.value}", confidence=confidence, evidence=evidence)


class SectionRouter:
    """Deterministic priority router: explicit > intent > page > signals > clarification."""

    def resolve(
        self,
        *,
        intent: IntentDecision,
        signals: Sequence[SignalCandidate],
        explicit_section: Section | None,
        explicit_product_id: str | None,
        page_context: Mapping[str, Any] | None,
        interaction_history: Sequence[Mapping[str, Any]],
        persona: PersonaCore | None,
    ) -> SectionDecision:
        _ = persona
        if explicit_section is not None:
            return SectionDecision(
                selected_section=explicit_section, confidence=1.0,
                evidence=["EXPLICIT_SECTION_SELECTION"], requires_qualification=True,
            )
        product_section = PRODUCT_SECTIONS.get((explicit_product_id or "").upper())
        if product_section is not None:
            return SectionDecision(
                selected_section=product_section, confidence=1.0,
                evidence=[f"EXPLICIT_PRODUCT:{explicit_product_id.upper()}"], requires_qualification=True,
            )
        if intent.name.startswith("EXPLORE_") and intent.confidence >= 0.65:
            section_name = intent.name.removeprefix("EXPLORE_")
            return SectionDecision(
                selected_section=Section(section_name), confidence=intent.confidence,
                evidence=["CLEAR_INTENT", *intent.evidence], requires_qualification=True,
            )
        page = str((page_context or {}).get("page") or "").lower()
        for section, keywords in SECTION_KEYWORDS.items():
            if any(keyword in page for keyword in keywords):
                return SectionDecision(
                    selected_section=section, confidence=0.72,
                    evidence=[f"PAGE_CONTEXT:{page}"], requires_qualification=True,
                )
        event_scores: dict[Section, float] = defaultdict(float)
        for event in interaction_history:
            raw_section = event.get("metadata", {}).get("section") if isinstance(event, dict) else None
            try:
                event_scores[Section(str(raw_section))] += 0.2
            except (TypeError, ValueError):
                continue
        signal_codes = {signal.code for signal in signals}
        if signal_codes & {"asks_about_return", "asks_about_risk", "compares_options"}:
            event_scores[Section.INVESTMENT] += 0.45
        if signal_codes & {"asks_about_level", "checks_progress"}:
            event_scores[Section.EDUCATION] += 0.30
        if event_scores:
            section, score = max(event_scores.items(), key=lambda item: (item[1], item[0].value))
            if score >= 0.4:
                return SectionDecision(
                    selected_section=section, confidence=min(0.65, score),
                    evidence=["BEHAVIOR_AND_SIGNALS"], requires_qualification=True,
                )
        return SectionDecision(
            selected_section=None, confidence=0.0,
            evidence=["CLARIFICATION_REQUIRED"], requires_qualification=True,
        )

