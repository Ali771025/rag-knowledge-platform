from __future__ import annotations

import base64
import io
import logging
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)

_SUPPORTED_LANGUAGES = {"en", "fa", "ar"}
_DEFAULT_STT_MODEL = "whisper-1"
_DEFAULT_TTS_MODEL = "gpt-4o-mini-tts"
_DEFAULT_TTS_VOICE = "alloy"


class VoiceServiceError(RuntimeError):
    """Raised when voice processing fails."""


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: str | None = None


@dataclass(frozen=True)
class SpeechResult:
    audio_base64: str
    mime_type: str = "audio/mpeg"


def _normalize_language(language: str | None) -> str | None:
    if not language:
        return None
    normalized = language.strip().lower()
    base = normalized.split("-", 1)[0]
    if base in _SUPPORTED_LANGUAGES:
        return base
    return None


class VoiceService:
    def __init__(self) -> None:
        self._openai_api_key = str(getattr(settings, "openai_api_key", "") or "").strip()
        self._timeout = max(1.0, float(getattr(settings, "openai_request_timeout_sec", 20.0)))
        self._max_retries = max(0, int(getattr(settings, "openai_max_retries", 1)))
        self._stt_model = str(getattr(settings, "openai_stt_model", _DEFAULT_STT_MODEL) or _DEFAULT_STT_MODEL)
        self._tts_model = str(getattr(settings, "openai_tts_model", _DEFAULT_TTS_MODEL) or _DEFAULT_TTS_MODEL)
        self._tts_voice = str(getattr(settings, "openai_tts_voice", _DEFAULT_TTS_VOICE) or _DEFAULT_TTS_VOICE)

    def transcribe_audio(self, *, audio_bytes: bytes, filename: str, language: str | None = None) -> TranscriptionResult:
        if not audio_bytes:
            raise VoiceServiceError("Audio payload is empty.")

        normalized_language = _normalize_language(language)
        if not self._openai_api_key:
            logger.warning("voice.transcribe_missing_openai_key")
            return TranscriptionResult(text="", language=normalized_language)

        try:
            from openai import OpenAI
        except Exception as exc:
            raise VoiceServiceError("OpenAI client is not available.") from exc

        client = OpenAI(api_key=self._openai_api_key, timeout=self._timeout, max_retries=self._max_retries)
        buffer = io.BytesIO(audio_bytes)
        safe_name = filename.strip() or "voice-input.webm"
        buffer.name = safe_name  # type: ignore[attr-defined]

        try:
            response = client.audio.transcriptions.create(
                model=self._stt_model,
                file=buffer,
                language=normalized_language,
                response_format="json",
            )
        except Exception as exc:
            logger.exception("voice.transcribe_failed")
            raise VoiceServiceError("Speech-to-text transcription failed.") from exc

        text = str(getattr(response, "text", "") or "").strip()
        return TranscriptionResult(text=text, language=normalized_language)

    def synthesize_speech(self, *, text: str, language: str | None = None, voice: str | None = None) -> SpeechResult:
        normalized_text = text.strip()
        if not normalized_text:
            raise VoiceServiceError("Text payload is empty.")

        normalized_language = _normalize_language(language) or "en"
        selected_voice = (voice or self._tts_voice).strip() or self._tts_voice

        if not self._openai_api_key:
            logger.warning("voice.speech_missing_openai_key")
            return SpeechResult(audio_base64="", mime_type="audio/mpeg")

        try:
            from openai import OpenAI
        except Exception as exc:
            raise VoiceServiceError("OpenAI client is not available.") from exc

        client = OpenAI(api_key=self._openai_api_key, timeout=self._timeout, max_retries=self._max_retries)
        prompt = normalized_text
        if normalized_language in {"fa", "ar"}:
            prompt = f"[language={normalized_language}] {normalized_text}"

        try:
            response = client.audio.speech.create(
                model=self._tts_model,
                voice=selected_voice,
                input=prompt,
                format="mp3",
            )
            audio_bytes = response.read()
        except Exception as exc:
            logger.exception("voice.speech_failed")
            raise VoiceServiceError("Text-to-speech generation failed.") from exc

        encoded = base64.b64encode(audio_bytes).decode("ascii")
        return SpeechResult(audio_base64=encoded, mime_type="audio/mpeg")
