from __future__ import annotations

from typing import Any

from app.qora.domain.orchestration_contracts import OrchestratorResponse


class FrontendResponseMapper:
    """Public mapper whose schema contains no persona, modifier, score, or internal policy fields."""

    def map(self, response: OrchestratorResponse) -> dict[str, Any]:
        return response.model_dump(mode="json", exclude_none=True)
