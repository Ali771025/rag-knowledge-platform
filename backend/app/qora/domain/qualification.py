from __future__ import annotations

from typing import Any, Mapping, Sequence

from app.qora.domain.enums import Section
from app.qora.domain.orchestration_contracts import QualificationQuestion, QualificationStatus, UIOption


def _options(*items: tuple[str, str]) -> list[UIOption]:
    return [UIOption(id=value, label=label, value=value) for value, label in items]


QUESTIONS: dict[Section, tuple[QualificationQuestion, ...]] = {
    Section.EARN: (
        QualificationQuestion(code="ongoing_time", text="برای فعالیت مستمر زمان داری؟", uncertainty_dimension="time", options=_options(("YES", "بله"), ("LIMITED", "محدود"), ("NO", "خیر"))),
        QualificationQuestion(code="initial_capital", text="سرمایه اولیه در اختیار داری؟", uncertainty_dimension="capital", options=_options(("YES", "بله"), ("LIMITED", "محدود"), ("NO", "خیر"))),
        QualificationQuestion(code="audience_network", text="جامعه مخاطب یا شبکه اجتماعی فعال داری؟", uncertainty_dimension="network", options=_options(("YES", "بله"), ("SMALL", "کوچک"), ("NO", "خیر"))),
    ),
    Section.STOCKHOLDERS: (
        QualificationQuestion(code="voting_importance", text="اثرگذاری و حق رأی برایت مهم است؟", uncertainty_dimension="governance", options=_options(("HIGH", "زیاد"), ("MEDIUM", "متوسط"), ("LOW", "کم"))),
        QualificationQuestion(code="growth_interest", text="به مشارکت در رشد بلندمدت علاقه داری؟", uncertainty_dimension="growth", options=_options(("YES", "بله"), ("UNSURE", "مطمئن نیستم"), ("NO", "خیر"))),
        QualificationQuestion(code="time_horizon", text="دیدگاهت بیشتر بلندمدت است؟", uncertainty_dimension="horizon", options=_options(("LONG", "بلندمدت"), ("MEDIUM", "میان‌مدت"), ("SHORT", "کوتاه‌مدت"))),
    ),
    Section.DEVELOPMENT: (
        QualificationQuestion(code="development_role", text="بیشتر به کدام نقش علاقه داری؟", uncertainty_dimension="role", options=_options(("IDEATION", "ایده‌پردازی"), ("DESIGN", "طراحی"), ("CODING", "کدنویسی"), ("COMMUNITY", "مدیریت جامعه"))),
        QualificationQuestion(code="commitment_level", text="چه میزان زمان می‌توانی اختصاص بدهی؟", uncertainty_dimension="commitment", options=_options(("LOW", "کم"), ("MEDIUM", "متوسط"), ("HIGH", "زیاد"))),
    ),
    Section.EDUCATION: (
        QualificationQuestion(code="experience_level", text="سطح فعلی تو چیست؟", uncertainty_dimension="experience", options=_options(("BEGINNER", "مبتدی"), ("INTERMEDIATE", "متوسط"), ("ADVANCED", "حرفه‌ای"))),
        QualificationQuestion(code="learning_goal", text="هدفت یادگیری کوتاه‌مدت است یا مسیر حرفه‌ای؟", uncertainty_dimension="goal", options=_options(("SHORT_TERM", "کوتاه‌مدت"), ("PROFESSIONAL", "مسیر حرفه‌ای"))),
    ),
    Section.INVESTMENT: (
        QualificationQuestion(code="investment_goal", text="هدف اصلی‌ات از بررسی این مسیر چیست؟", uncertainty_dimension="goal", options=_options(("PRESERVATION", "حفظ ارزش"), ("GROWTH", "رشد"), ("LEARNING", "شناخت مسیر"))),
        QualificationQuestion(code="investment_horizon", text="افق زمانی مدنظرت چیست؟", uncertainty_dimension="horizon", options=_options(("SHORT", "کوتاه‌مدت"), ("MEDIUM", "میان‌مدت"), ("LONG", "بلندمدت"))),
        QualificationQuestion(code="risk_tolerance", text="با نوسان و ریسک چه میزان راحت هستی؟", uncertainty_dimension="risk", options=_options(("LOW", "کم"), ("MEDIUM", "متوسط"), ("HIGH", "زیاد"))),
        QualificationQuestion(code="liquidity_need", text="دسترسی سریع به منابع برایت چقدر مهم است؟", uncertainty_dimension="liquidity", options=_options(("HIGH", "زیاد"), ("MEDIUM", "متوسط"), ("LOW", "کم"))),
    ),
}


class QualificationEngine:
    def evaluate(
        self,
        *,
        section: Section,
        answers: Mapping[str, dict[str, Any]],
        asked_codes: Sequence[str] = (),
        max_questions: int = 4,
    ) -> QualificationStatus:
        questions = QUESTIONS[section]
        answered_codes = {code for code, value in answers.items() if value}
        missing = [question for question in questions if question.code not in answered_codes]
        # Already asked but unanswered questions remain first; answered questions are never repeated.
        asked_set = set(asked_codes)
        missing.sort(key=lambda question: (question.code not in asked_set, list(questions).index(question)))
        completeness = len(answered_codes.intersection({item.code for item in questions})) / len(questions)
        return QualificationStatus(
            complete=not missing,
            completeness=completeness,
            answered=dict(answers),
            next_questions=missing[: max(1, min(4, max_questions))],
        )

    def parse_answer(self, question: QualificationQuestion, message: str) -> tuple[dict[str, Any], float]:
        normalized = " ".join(message.strip().split()).lower()
        for option in question.options:
            if option.value.lower() == normalized or option.label.lower() in normalized:
                return {"value": option.value, "label": option.label}, 1.0
        return {"value": "FREE_TEXT", "text": message.strip()[:500]}, 0.6

    def match_products(
        self,
        *,
        section: Section,
        answers: Mapping[str, dict[str, Any]],
        product_ids: Sequence[str],
    ) -> dict[str, float]:
        scores = {product_id: 0.5 for product_id in product_ids}
        values = {code: str(answer.get("value", "")) for code, answer in answers.items()}
        if section == Section.INVESTMENT:
            if values.get("risk_tolerance") == "LOW":
                self._boost(scores, {"EID": 0.35, "Q": 0.20, "INSURANCE": 0.20})
            elif values.get("risk_tolerance") == "HIGH":
                self._boost(scores, {"STAKING": 0.25, "ETER": 0.20})
            if values.get("liquidity_need") == "HIGH":
                self._boost(scores, {"EID": 0.20, "INSURANCE": 0.15})
            if values.get("investment_goal") == "PRESERVATION":
                self._boost(scores, {"EID": 0.20, "Q": 0.15})
            elif values.get("investment_goal") == "GROWTH":
                self._boost(scores, {"STAKING": 0.20, "ETER": 0.15})
        elif section == Section.EARN:
            if values.get("audience_network") in {"YES", "SMALL"}:
                self._boost(scores, {"FAN_COMMUNITY": 0.30, "REFERRAL_INSURANCE": 0.20})
            if values.get("ongoing_time") == "NO":
                self._boost(scores, {"FORECAST": 0.25})
        elif section == Section.STOCKHOLDERS:
            if values.get("voting_importance") == "HIGH":
                self._boost(scores, {"EES": 0.30})
            if values.get("time_horizon") == "LONG":
                self._boost(scores, {"ERA": 0.25})
        elif section == Section.DEVELOPMENT:
            role = values.get("development_role")
            if role in {"CODING", "DESIGN"}:
                self._boost(scores, {"ELITE": 0.30})
            if role in {"IDEATION", "COMMUNITY"}:
                self._boost(scores, {"PROPOSAL": 0.30})
        elif section == Section.EDUCATION:
            self._boost(scores, {"EDGE": 0.40})
        return {product_id: min(1.0, max(0.0, score)) for product_id, score in scores.items()}

    @staticmethod
    def _boost(scores: dict[str, float], boosts: Mapping[str, float]) -> None:
        for product_id, amount in boosts.items():
            if product_id in scores:
                scores[product_id] += amount
