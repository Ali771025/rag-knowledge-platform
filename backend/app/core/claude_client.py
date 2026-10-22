"""Claude client adapter."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class ClaudeClientError(Exception):
    """Base Claude client exception."""


class ClaudeClientConfigurationError(ClaudeClientError):
    """Raised when Claude configuration is missing."""


class ClaudeClientAPIError(ClaudeClientError):
    """Raised when Claude API call fails."""


class ClaudeClient:
    """Wrapper for Anthropic Claude interactions."""

    def __init__(self, api_key: str | None = None, model: str | None = None, max_tokens: int | None = None) -> None:
        self.api_key = api_key or settings.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.model = model or settings.default_model or os.getenv("DEFAULT_MODEL", "claude-3-5-haiku-latest")
        self.max_tokens = max_tokens if max_tokens is not None else int(settings.max_tokens or os.getenv("MAX_TOKENS", "1024"))
        self.temperature = float(settings.temperature if settings.temperature is not None else os.getenv("TEMPERATURE", "0.2"))
        self.request_timeout_sec = max(1.0, float(settings.claude_request_timeout_sec or 8.0))
        self.max_retries = max(0, int(settings.claude_max_retries or 0))
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise ClaudeClientConfigurationError("ANTHROPIC_API_KEY is not configured")
        try:
            from anthropic import Anthropic
            self._client = Anthropic(
                api_key=self.api_key,
                timeout=self.request_timeout_sec,
                max_retries=self.max_retries,
            )
            return self._client
        except Exception as exc:
            raise ClaudeClientAPIError("failed to initialize Claude client") from exc

    def generate_text(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate text completion from Claude."""
        client = self._get_client()
        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt or "",
                messages=[{"role": "user", "content": prompt}],
            )
            content = getattr(response, "content", [])
            if not content:
                return ""
            text = getattr(content[0], "text", "")
            return str(text)
        except Exception as exc:
            raise ClaudeClientAPIError("failed to generate text from Claude") from exc

    def generate_json(self, prompt: str, system_prompt: str | None = None) -> dict | list:
        """Generate JSON output from Claude text response."""
        text = self.generate_text(prompt=prompt, system_prompt=system_prompt)
        try:
            parsed = json.loads(text)
        except Exception as exc:
            raise ClaudeClientAPIError("Claude response is not valid JSON") from exc
        if not isinstance(parsed, (dict, list)):
            raise ClaudeClientAPIError("Claude JSON response must be object or array")
        return parsed
