"""Persona module configuration placeholders."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PersonaEngineConfig(BaseModel):
    """Persona engine configuration placeholder."""

    enabled: bool = True
    policy_name: str = Field(default="default", min_length=1, max_length=128)
    transition_buffer_ttl_seconds: int = Field(default=1800, ge=60, le=86400)
    transition_buffer_size: int = Field(default=3, ge=1, le=10)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
