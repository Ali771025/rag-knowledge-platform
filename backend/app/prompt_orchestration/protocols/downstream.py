"""Downstream integration contracts for prompt orchestration.

These protocols define where this module sends finalized inference payloads.
Concrete provider transports should be implemented outside this module.
"""

from __future__ import annotations

from typing import Protocol

from app.prompt_orchestration.models import LLMInferenceRequest, LLMInferenceResponse


class InferenceGateway(Protocol):
    """Executes inference requests against a model-serving boundary."""

    def generate(self, request: LLMInferenceRequest) -> LLMInferenceResponse:
        """Return model output for a prepared inference request."""
