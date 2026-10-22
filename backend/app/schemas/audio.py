from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AudioTranscriptionResponse(BaseModel):
    text: str = Field(default="")
    partial: str | None = Field(default=None)
    final: str | None = Field(default=None)
    language: str | None = Field(default=None)

    model_config = ConfigDict(extra="forbid")


class AudioSpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    language: str | None = Field(default=None, min_length=2, max_length=16)
    voice: str | None = Field(default=None, min_length=1, max_length=32)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AudioSpeechResponse(BaseModel):
    audio_base64: str
    mime_type: str = "audio/mpeg"

    model_config = ConfigDict(extra="forbid")
