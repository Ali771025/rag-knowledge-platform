from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ReferralMeResponse(BaseModel):
    code: str = Field(min_length=1, max_length=128)
    invite_link: str | None = Field(default=None, min_length=1, max_length=2048)
    total_referrals: int | None = Field(default=None, ge=0)
    total_rewards: float | None = Field(default=None, ge=0)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
