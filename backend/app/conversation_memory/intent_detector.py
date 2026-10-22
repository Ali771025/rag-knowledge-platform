"""Intent detector abstraction and baseline rule-based implementation."""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from typing import Final

from app.conversation_memory.exceptions import IntentDetectionError
from app.conversation_memory.models import SessionState

logger = logging.getLogger(__name__)

IntentLabel = str

SUPPORTED_INTENTS: Final[set[IntentLabel]] = {
    "greeting",
    "learn_more",
    "tell_me_about",
    "start_learning",
    "explain",
    "ask_question",
    "clarify",
    "join",
    "participate",
    "ready",
    "unknown",
}

_AFFIRMATIVE_TOKENS: Final[tuple[str, ...]] = (
    "yes",
    "yeah",
    "yep",
    "ok",
    "okay",
    "sure",
    "continue",
    "next",
    "bale",
    "بله",
    "باشه",
    "حتما",
)

_INTENT_PATTERNS: Final[list[tuple[IntentLabel, tuple[str, ...]]]] = [
    ("ready", ("i'm ready", "im ready", "ready to join", "ready", "آماده‌ام", "آماده ام", "آمادم", "آماده")),
    (
        "participate",
        ("participate", "take part", "count me in", "میخوام شرکت کنم", "می‌خوام شرکت کنم", "شرکت کنم", "مشارکت کنم"),
    ),
    ("join", ("join", "sign up", "register", "enroll", "apply", "عضو", "ثبت نام", "ثبت‌نام", "پیوستن", "ملحق")),
    ("ask_question", ("?", "question", "ask", "what", "how", "why", "can you", "میشه", "می‌شود", "چطور", "چگونه", "سوال", "سؤال")),
    ("clarify", ("clarify", "more detail", "elaborate", "not clear", "clearer", "توضیح بیشتر", "شفاف", "واضح نیست", "دقیق‌تر")),
    ("start_learning", ("start learning", "begin learning", "learn now", "let's start", "شروع یادگیری", "شروع کنیم", "شروع آموزش")),
    ("explain", ("explain", "walk me through", "overview", "describe", "explanation", "توضیح بده", "توضیح", "شرح بده")),
    (
        "tell_me_about",
        (
            "tell me about",
            "about the program",
            "about this",
            "help me build onboarding plan",
            "build onboarding plan",
            "onboarding plan",
            "درباره",
            "در مورد",
            "راجب",
            "راجع",
        ),
    ),
    (
        "learn_more",
        (
            "learn more",
            "more info",
            "more information",
            "details please",
            "tell more",
            "tell me more",
            "more details",
            "اطلاعات بیشتر",
            "بیشتر بدونم",
            "بیشتر بدانم",
        ),
    ),
    ("greeting", ("hello", "hi", "hey", "helo", "heloo", "salam", "سلام", "درود")),
]


class BaseIntentDetector(ABC):
    """Abstract interface for intent detector implementations."""

    @abstractmethod
    def detect_intent(self, message: str, session_state: SessionState | None = None) -> IntentLabel:
        """Detect intent label from the user message."""


class RuleBasedIntentDetector(BaseIntentDetector):
    """Deterministic keyword/pattern-based intent detector."""

    _patterns: list[tuple[IntentLabel, tuple[str, ...]]]

    def __init__(self) -> None:
        self._patterns = list(_INTENT_PATTERNS)

    def detect_intent(self, message: str, session_state: SessionState | None = None) -> IntentLabel:
        """Detect intent via case-insensitive keyword matching."""
        try:
            normalized = self._normalize_message(message)
            if not normalized:
                return "unknown"

            contextual_affirmative_intent = self._resolve_contextual_affirmative_intent(
                normalized=normalized,
                session_state=session_state,
            )
            if contextual_affirmative_intent is not None:
                return contextual_affirmative_intent

            for intent, phrases in self._patterns:
                if self._matches(normalized, phrases):
                    logger.debug("Intent matched intent=%s message=%s", intent, normalized[:120])
                    return intent

            logger.debug("No intent rule matched; returning unknown.")
            return "unknown"
        except IntentDetectionError:
            raise
        except Exception as exc:  # pragma: no cover - defensive safety net
            logger.exception("Intent detection failed unexpectedly.")
            raise IntentDetectionError("Failed to detect intent.") from exc

    def _normalize_message(self, message: str) -> str:
        if not isinstance(message, str):
            raise IntentDetectionError("Message must be a string.")
        text = message.casefold().strip()
        text = re.sub(r"\s+", " ", text)
        return text

    @staticmethod
    def _matches(message: str, phrases: tuple[str, ...]) -> bool:
        for phrase in phrases:
            normalized_phrase = phrase.casefold().strip()
            if not normalized_phrase:
                continue

            if re.fullmatch(r"[a-z0-9]+", normalized_phrase):
                pattern = rf"(?<![a-z0-9]){re.escape(normalized_phrase)}(?![a-z0-9])"
                if re.search(pattern, message):
                    return True
                continue

            if normalized_phrase in message:
                return True

        return False

    @staticmethod
    def _resolve_contextual_affirmative_intent(
        *,
        normalized: str,
        session_state: SessionState | None,
    ) -> IntentLabel | None:
        if not any(RuleBasedIntentDetector._matches(normalized, (token,)) for token in _AFFIRMATIVE_TOKENS):
            return None

        if session_state is None:
            return "learn_more"

        state_to_intent: dict[str, IntentLabel] = {
            "start": "learn_more",
            "intro": "start_learning",
            "education": "ask_question",
            "qna": "join",
            "join": "ready",
        }
        return state_to_intent.get(session_state.state.value, "learn_more")


class IntentDetector:
    """Backward-compatible adapter for existing Phase 1 imports."""

    def __init__(self, detector: BaseIntentDetector | None = None) -> None:
        self.detector = detector or RuleBasedIntentDetector()

    def detect(self, message: str) -> IntentLabel:
        """Return detected intent label for a message."""
        return self.detector.detect_intent(message=message, session_state=None)

    def detect_intent(self, message: str, session_state: SessionState | None = None) -> IntentLabel:
        """Detect intent using the configured detector implementation."""
        return self.detector.detect_intent(message=message, session_state=session_state)
