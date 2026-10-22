from __future__ import annotations

import json
import logging
import os
from typing import Any, Protocol

from app.core.config import settings
from app.rag.constants import REFUSAL_MESSAGE

logger = logging.getLogger(__name__)

_MIN_TEMPERATURE = 0.0
_MAX_TEMPERATURE = 0.3


class _LLMProvider(Protocol):
    """Provider abstraction for text generation."""

    provider_name: str
    model_name: str

    def generate(
        self,
        *,
        system_prompt: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Generate text from provider API."""


class _OpenAIProvider:
    provider_name = "openai"

    def __init__(self, *, api_key: str, model_name: str, timeout_seconds: float, max_retries: int) -> None:
        from openai import OpenAI

        self._client = OpenAI(
            api_key=api_key,
            timeout=max(1.0, float(timeout_seconds)),
            max_retries=max(0, int(max_retries)),
        )
        self.model_name = model_name

    def generate(
        self,
        *,
        system_prompt: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> str:
        provider_messages: list[dict[str, str]] = []
        if system_prompt.strip():
            provider_messages.append({"role": "system", "content": system_prompt.strip()})
        provider_messages.extend(messages)

        response = self._client.chat.completions.create(
            model=self.model_name,
            messages=provider_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        choices = getattr(response, "choices", None) or []
        if not choices:
            return ""
        message = getattr(choices[0], "message", None)
        if message is None:
            return ""

        content = getattr(message, "content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "text" and isinstance(item.get("text"), str):
                    parts.append(item["text"])
            return "\n".join(parts)
        return str(content or "")


class _AnthropicProvider:
    provider_name = "anthropic"

    def __init__(self, *, api_key: str, model_name: str) -> None:
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)
        self.model_name = model_name

    def generate(
        self,
        *,
        system_prompt: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> str:
        response = self._client.messages.create(
            model=self.model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=messages,
        )
        content = getattr(response, "content", None)
        if content and len(content) > 0:
            first = content[0]
            text = getattr(first, "text", None)
            if text:
                return str(text)
        return ""


class LLMService:
    def __init__(self) -> None:
        self.llm_provider = str(getattr(settings, "llm_provider", os.getenv("LLM_PROVIDER", "openai"))).strip().lower() or "openai"
        self.openai_api_key = str(getattr(settings, "openai_api_key", os.getenv("OPENAI_API_KEY", "")))
        self.anthropic_api_key = str(getattr(settings, "anthropic_api_key", os.getenv("ANTHROPIC_API_KEY", "")))
        self.max_tokens = max(1, int(getattr(settings, "max_tokens", os.getenv("MAX_TOKENS", "512"))))
        self.temperature = self._clamp_temperature(float(getattr(settings, "temperature", os.getenv("TEMPERATURE", "0.2"))))

        self._provider: _LLMProvider | None = None
        self._client_error: str | None = None

        self.default_model = self._resolve_default_model()
        self._provider = self._build_provider()

    def send_prompt(
        self,
        system: str | dict[str, Any],
        messages: list[dict[str, str]] | None = None,
        context: dict[str, Any] | None = None,
        grounded: bool = False,
    ) -> str:
        if isinstance(system, dict) and messages is None:
            return self._send_from_request_payload(system)

        if not isinstance(system, str):
            return self._fallback_response(reason="Invalid system prompt payload")

        outbound_messages = self._sanitize_messages(messages or [])
        if grounded and not self._looks_grounded(system=system, messages=outbound_messages, context=context):
            logger.warning("llm.send_prompt_bare_question_without_context")
            return REFUSAL_MESSAGE

        final_system = system.strip()
        if context:
            final_system = f"{final_system}\n\nOperational context:\n{self._stringify_context(context)}"

        if self._provider is None:
            return self._fallback_response(reason=self._client_error)

        try:
            response_text = self._provider.generate(
                system_prompt=final_system,
                messages=outbound_messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            cleaned = self._clean_response(response_text)
            if cleaned:
                return cleaned
            return self._fallback_response(reason="Empty LLM response")
        except Exception as exc:
            status_code = getattr(exc, "status_code", None)
            body = getattr(exc, "body", None)
            response_payload = getattr(exc, "response", None)
            logger.exception(
                "llm.generation_failed provider=%s model=%s status=%s error=%s body=%s response=%s",
                self.llm_provider,
                self.default_model,
                status_code,
                type(exc).__name__,
                body,
                response_payload,
            )
            return self._fallback_response(reason=str(exc))

    def _send_from_request_payload(self, request_payload: dict[str, Any]) -> str:
        prompt_value = request_payload.get("prompt")
        if isinstance(prompt_value, str) and prompt_value.strip():
            prompt = prompt_value.strip()
            if "Grounding context:" not in prompt:
                logger.warning("llm.generate_bare_prompt_without_context")
            return self.send_prompt(
                system="You are a helpful assistant.",
                messages=[{"role": "user", "content": prompt}],
                context={"request_mode": "raw_prompt"},
                grounded=False,
            )

        question = request_payload.get("question")
        context_value = request_payload.get("context")
        if isinstance(question, str) and question.strip() and context_value is not None:
            question_text = question.strip()
            context_text = self._context_to_text(context_value)
            prompt = self._build_question_context_prompt(question=question_text, context_text=context_text)
            return self.send_prompt(
                system="You are a retrieval-grounded assistant.",
                messages=[{"role": "user", "content": prompt}],
                context={"request_mode": "question_context"},
                grounded=True,
            )

        return self._fallback_response(reason="Request must include prompt or {question, context}")

    def _build_provider(self) -> _LLMProvider | None:
        try:
            if self.llm_provider == "openai":
                if not self.openai_api_key:
                    self._client_error = "OPENAI_API_KEY is not configured"
                    return None
                return _OpenAIProvider(
                    api_key=self.openai_api_key,
                    model_name=self.default_model,
                    timeout_seconds=float(getattr(settings, "openai_generation_timeout_sec", 8.0)),
                    max_retries=int(getattr(settings, "openai_generation_max_retries", 0)),
                )

            if self.llm_provider == "anthropic":
                if not self.anthropic_api_key:
                    self._client_error = "ANTHROPIC_API_KEY is not configured"
                    return None
                return _AnthropicProvider(api_key=self.anthropic_api_key, model_name=self.default_model)

            self._client_error = f"Unsupported llm provider: {self.llm_provider}"
            return None
        except Exception as exc:
            self._client_error = str(exc)
            logger.exception("llm.provider_bootstrap_failed provider=%s", self.llm_provider)
            return None

    def _resolve_default_model(self) -> str:
        configured_default = str(getattr(settings, "default_model", os.getenv("DEFAULT_MODEL", ""))).strip()
        if configured_default:
            if self.llm_provider == "openai" and configured_default.startswith("claude"):
                return str(getattr(settings, "openai_generation_model", "gpt-4o-mini"))
            if self.llm_provider == "anthropic" and configured_default.startswith("gpt-"):
                return str(getattr(settings, "anthropic_generation_model", "claude-3-5-haiku-latest"))
            return configured_default

        if self.llm_provider == "anthropic":
            return str(getattr(settings, "anthropic_generation_model", "claude-3-5-haiku-latest"))
        return str(getattr(settings, "openai_generation_model", "gpt-4o-mini"))

    def _sanitize_messages(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        cleaned: list[dict[str, str]] = []

        for raw in messages:
            if not isinstance(raw, dict):
                continue
            role = str(raw.get("role", "")).strip().lower()
            if role not in {"user", "assistant", "system"}:
                continue
            content = str(raw.get("content", "") or "").strip()
            if not content:
                continue
            cleaned.append({"role": role, "content": content})

        if not cleaned:
            return [{"role": "user", "content": "Please answer the user question using the provided context."}]

        # Anthropic-style chat requires alternating user/assistant turns.
        output: list[dict[str, str]] = []
        for item in cleaned:
            role = item["role"]
            if role == "system":
                # System content is moved into the system prompt and removed from turn list.
                continue
            if output and output[-1]["role"] == role:
                output[-1]["content"] = f"{output[-1]['content']}\n\n{item['content']}"
                continue
            output.append(item)

        if not output:
            return [{"role": "user", "content": cleaned[-1]["content"]}]

        if output[0]["role"] != "user":
            output[0]["role"] = "user"

        return output

    def _looks_grounded(
        self,
        *,
        system: str,
        messages: list[dict[str, str]],
        context: dict[str, Any] | None,
    ) -> bool:
        if "Grounding context:" in system:
            return True
        for item in messages:
            if "Grounding context:" in item.get("content", ""):
                return True
        if isinstance(context, dict):
            summary = json.dumps(context, ensure_ascii=True).lower()
            if "retrieval_summary" in summary or "context_bundle" in summary:
                return True
        return False

    @staticmethod
    def _stringify_context(context: dict[str, Any]) -> str:
        try:
            return json.dumps(context, ensure_ascii=True, default=str)
        except Exception:
            return str(context)

    @staticmethod
    def _context_to_text(value: Any) -> str:
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, list):
            parts = [str(item).strip() for item in value if str(item).strip()]
            return "\n".join(parts)
        if isinstance(value, dict):
            return json.dumps(value, ensure_ascii=True, default=str)
        return str(value).strip()

    @staticmethod
    def _build_question_context_prompt(*, question: str, context_text: str) -> str:
        return "\n\n".join(
            [
                f"User question:\n{question}",
                f"Grounding context:\n{context_text or 'No context provided.'}",
                f"If the context does not contain the answer, respond exactly with: {REFUSAL_MESSAGE}",
            ]
        )

    @staticmethod
    def _clamp_temperature(value: float) -> float:
        if value < _MIN_TEMPERATURE:
            return _MIN_TEMPERATURE
        if value > _MAX_TEMPERATURE:
            return _MAX_TEMPERATURE
        return value

    @staticmethod
    def _clean_response(text: str) -> str:
        return " ".join(str(text or "").split())

    @staticmethod
    def _fallback_response(reason: str | None = None) -> str:
        base = "[DEV FALLBACK] LLM is unavailable. Continuing with deterministic guidance."
        if reason:
            return f"{base} ({reason})"
        return base
