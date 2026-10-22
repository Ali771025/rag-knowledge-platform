from __future__ import annotations

from dataclasses import dataclass

from app.qora.domain.enums import PersonaCore, PersonaModifier, SignalSourceType


@dataclass(frozen=True, slots=True)
class SignalDefinition:
    code: str
    category: str
    persona: PersonaCore | None = None
    modifier: PersonaModifier | None = None
    keywords: tuple[str, ...] = ()
    event_types: tuple[str, ...] = ()
    allowed_sources: tuple[SignalSourceType, ...] = tuple(SignalSourceType)


def _definition(
    code: str,
    category: str,
    *,
    persona: PersonaCore | None = None,
    modifier: PersonaModifier | None = None,
    keywords: tuple[str, ...] = (),
    events: tuple[str, ...] = (),
) -> SignalDefinition:
    return SignalDefinition(code, category, persona, modifier, keywords, events)


SIGNAL_TAXONOMY: dict[str, SignalDefinition] = {
    item.code: item
    for item in (
        _definition("asks_how_it_works", "TRUST", persona=PersonaCore.SAVER, keywords=("how does it work", "چطور کار می", "چگونه کار می")),
        _definition("asks_about_scam", "TRUST", persona=PersonaCore.SAVER, modifier=PersonaModifier.TRUST_LOW, keywords=("scam", "fraud", "کلاهبرداری", "اسکم", "قابل اعتماد")),
        _definition("requests_terms", "TERMS", persona=PersonaCore.SAVER, modifier=PersonaModifier.REGULATION_SENSITIVE, keywords=("terms", "شرایط", "قوانین"), events=("TERMS_OPENED",)),
        _definition("requests_economic_logic", "ECONOMICS", persona=PersonaCore.SAVER, keywords=("economic logic", "منطق اقتصادی", "مدل درآمد")),
        _definition("delays_action", "BEHAVIOR", persona=PersonaCore.SAVER, events=("CTA_DELAYED", "CTA_DISMISSED")),
        _definition("views_docs_without_action", "BEHAVIOR", persona=PersonaCore.SAVER, events=("DOCS_VIEWED_NO_ACTION",)),
        _definition("asks_about_risk", "RISK", persona=PersonaCore.SAVER, modifier=PersonaModifier.TRUST_LOW, keywords=("risk", "ریسک", "ضرر", "از دست")),
        _definition("asks_about_fairness", "TRUST", persona=PersonaCore.SAVER, keywords=("fair", "fairness", "منصفانه", "عدالت")),
        _definition("asks_about_return", "RETURN", persona=PersonaCore.HUNTER, keywords=("return", "roi", "بازده", "سود")),
        _definition("asks_about_speed", "SPEED", persona=PersonaCore.HUNTER, keywords=("fast", "quick", "سریع", "چقدر طول")),
        _definition("asks_about_advantage", "ADVANTAGE", persona=PersonaCore.HUNTER, keywords=("advantage", "مزیت", "برتری")),
        _definition("compares_options", "COMPARISON", persona=PersonaCore.HUNTER, keywords=("compare", "versus", " vs ", "مقایسه", "بهتره"), events=("PRODUCTS_COMPARED",)),
        _definition("seeks_shortcut", "SPEED", persona=PersonaCore.HUNTER, keywords=("shortcut", "راه میانبر", "سریع ترین")),
        _definition("switches_paths_quickly", "BEHAVIOR", persona=PersonaCore.HUNTER, events=("PATH_SWITCHED_QUICKLY",)),
        _definition("asks_about_upgrade", "UPGRADE", persona=PersonaCore.HUNTER, keywords=("upgrade", "ارتقا")),
        _definition("asks_best_option", "COMPARISON", persona=PersonaCore.HUNTER, keywords=("best option", "بهترین گزینه", "کدام بهتر")),
        _definition("asks_about_level", "PROGRESS", persona=PersonaCore.PLAYER, keywords=("level", "سطح")),
        _definition("asks_about_badge", "PROGRESS", persona=PersonaCore.PLAYER, keywords=("badge", "نشان", "مدال")),
        _definition("asks_about_unlock", "PROGRESS", persona=PersonaCore.PLAYER, keywords=("unlock", "باز میشه", "باز کردن")),
        _definition("checks_progress", "PROGRESS", persona=PersonaCore.PLAYER, keywords=("progress", "پیشرفت"), events=("PROGRESS_VIEWED",)),
        _definition("performs_small_repeated_actions", "BEHAVIOR", persona=PersonaCore.PLAYER, events=("REPEATED_SMALL_ACTIONS",)),
        _definition("daily_engagement", "BEHAVIOR", persona=PersonaCore.PLAYER, events=("DAILY_ENGAGEMENT",)),
        _definition("asks_whats_next", "PROGRESS", persona=PersonaCore.PLAYER, keywords=("what next", "what's next", "بعدش چی", "مرحله بعد")),
        _definition("asks_design_reason", "DESIGN", persona=PersonaCore.ARCHITECT, keywords=("why designed", "design reason", "چرا طراحی", "دلیل طراحی")),
        _definition("asks_sustainability", "DESIGN", persona=PersonaCore.ARCHITECT, keywords=("sustainability", "sustainable", "پایداری", "پایدار")),
        _definition("asks_game_theory", "DESIGN", persona=PersonaCore.ARCHITECT, keywords=("game theory", "نظریه بازی")),
        _definition("asks_incentive_structure", "DESIGN", persona=PersonaCore.ARCHITECT, keywords=("incentive", "مشوق", "انگیزشی")),
        _definition("checks_attack_vectors", "SECURITY", persona=PersonaCore.ARCHITECT, keywords=("attack vector", "حمله", "آسیب پذیری")),
        _definition("finds_contradictions", "DESIGN", persona=PersonaCore.ARCHITECT, keywords=("contradiction", "تناقض", "ناسازگار")),
        _definition("reads_lightpaper", "DESIGN", persona=PersonaCore.ARCHITECT, keywords=("lightpaper", "لایت پیپر"), events=("LIGHTPAPER_VIEWED",)),
        _definition("compares_scenarios", "DESIGN", persona=PersonaCore.ARCHITECT, keywords=("scenario", "سناریو"), events=("SCENARIOS_COMPARED",)),
        _definition("suggests_design_change", "DESIGN", persona=PersonaCore.ARCHITECT, keywords=("should redesign", "تغییر طراحی", "بهتر است طراحی")),
        _definition("doubts_claims", "TRUST", modifier=PersonaModifier.TRUST_LOW, keywords=("don't trust", "اعتماد ندار", "مدرک")),
        _definition("seeks_authority", "AUTHORITY", modifier=PersonaModifier.AUTHORITY_DRIVEN, keywords=("official", "expert", "منبع رسمی", "کارشناس", "تایید شده"), events=("OFFICIAL_DOC_VIEWED",)),
        _definition("seeks_community", "COMMUNITY", modifier=PersonaModifier.COMMUNITY_DRIVEN, keywords=("community", "others", "جامعه", "بقیه", "کاربران"), events=("COMMUNITY_OPENED",)),
        _definition("seeks_personal_control", "AUTONOMY", modifier=PersonaModifier.INDIVIDUAL_DRIVEN, keywords=("my choice", "my control", "انتخاب خودم", "کنترل شخصی")),
        _definition("seeks_regulatory_clarity", "REGULATION", modifier=PersonaModifier.REGULATION_SENSITIVE, keywords=("regulation", "compliance", "license", "رگولاتوری", "مجوز", "قانونی"), events=("REGULATION_DOC_VIEWED",)),
    )
}


def known_signal_codes() -> tuple[str, ...]:
    return tuple(SIGNAL_TAXONOMY)

