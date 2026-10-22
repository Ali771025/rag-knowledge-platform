"""Conversion module configuration placeholders."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ConversionEngineConfig(BaseModel):
    """Conversion engine configuration placeholder."""

    enabled: bool = True
    policy_name: str = Field(default="default", min_length=1, max_length=128)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
