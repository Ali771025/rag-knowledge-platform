"""Discord source loader implementation."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from app.ingestion.exceptions import IngestionValidationError, SourceLoadError
from app.ingestion.schemas import RawDocument, SourceConfig
from app.ingestion.sources.base import BaseSourceLoader

logger = logging.getLogger(__name__)

DEFAULT_LIMIT_PER_CHANNEL = int(os.getenv("DISCORD_DEFAULT_LIMIT_PER_CHANNEL", "200"))
MAX_LIMIT_PER_CHANNEL = int(os.getenv("DISCORD_MAX_LIMIT_PER_CHANNEL", "1000"))


@dataclass(slots=True)
class DiscordChannelRef:
    """Channel descriptor used by the ingestion adapter."""

    channel_id: str
    channel_name: str | None = None
    channel_type: str | None = None


@dataclass(slots=True)
class DiscordMessagePayload:
    """Normalized message payload produced by an adapter."""

    message_id: str
    content: str
    author_id: str
    author_name: str | None
    timestamp: datetime | str
    channel_id: str
    channel_name: str | None = None
    thread_id: str | None = None
    thread_name: str | None = None
    attachments: list[dict[str, Any]] | None = None


class DiscordAPIAdapter(Protocol):
    """Protocol for Discord data access, enabling test doubles."""

    async def fetch_messages(
        self,
        *,
        token: str,
        channel_id: str,
        limit: int,
        timeout_seconds: int,
    ) -> list[DiscordMessagePayload]:
        """Fetch normalized messages for a channel."""


class DiscordHTTPAdapter:
    """HTTP-based Discord API adapter.

    Uses Discord REST API and keeps external calls isolated for testability.
    """

    async def fetch_messages(
        self,
        *,
        token: str,
        channel_id: str,
        limit: int,
        timeout_seconds: int,
    ) -> list[DiscordMessagePayload]:
        try:
            import httpx
        except Exception as exc:  # pragma: no cover - optional dependency safety
            raise SourceLoadError("httpx is required for Discord scraping") from exc

        headers = {"Authorization": f"Bot {token}"}
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        params = {"limit": max(1, min(limit, 100))}
        timeout = httpx.Timeout(timeout_seconds)

        async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
            response = await client.get(url, params=params)
            if response.status_code in {401, 403}:
                raise SourceLoadError("Discord API authentication/authorization failed")
            response.raise_for_status()
            payload = response.json()

        messages: list[DiscordMessagePayload] = []
        for item in payload:
            content = str(item.get("content") or "").strip()
            attachments_raw = item.get("attachments") or []
            attachments = [
                {
                    "id": attachment.get("id"),
                    "filename": attachment.get("filename"),
                    "content_type": attachment.get("content_type"),
                    "size": attachment.get("size"),
                    "url": attachment.get("url"),
                }
                for attachment in attachments_raw
            ]
            if not content and not attachments:
                continue
            messages.append(
                DiscordMessagePayload(
                    message_id=str(item.get("id", "")),
                    content=content or "[attachment-only-message]",
                    author_id=str((item.get("author") or {}).get("id", "")),
                    author_name=(item.get("author") or {}).get("username"),
                    timestamp=item.get("timestamp") or "",
                    channel_id=channel_id,
                    channel_name=None,
                    thread_id=str((item.get("thread") or {}).get("id")) if item.get("thread") else None,
                    thread_name=(item.get("thread") or {}).get("name") if item.get("thread") else None,
                    attachments=attachments,
                )
            )
        return messages


class DiscordScraperSource(BaseSourceLoader):
    """Loads Discord messages from configured channels as raw documents."""

    def __init__(self, adapter: DiscordAPIAdapter | None = None) -> None:
        self.adapter = adapter or DiscordHTTPAdapter()

    async def load(self, config: SourceConfig) -> list[RawDocument]:
        """Load and normalize messages from Discord channels."""
        self.validate_source(config)
        if config.source_type != "discord":
            raise IngestionValidationError("DiscordScraperSource requires source_type='discord'")

        token = self._resolve_token(config)
        channels = self._resolve_channels(config)
        limit_per_channel = self._resolve_limit(config)

        documents: list[RawDocument] = []
        for channel in channels:
            try:
                messages = await self.adapter.fetch_messages(
                    token=token,
                    channel_id=channel.channel_id,
                    limit=limit_per_channel,
                    timeout_seconds=config.timeout_seconds,
                )
            except Exception as exc:
                logger.warning(
                    "discord_channel_fetch_failed",
                    extra={"channel_id": channel.channel_id, "error": str(exc)},
                )
                continue

            for message in messages:
                if len(documents) >= config.max_items:
                    break
                raw_content = message.content.strip()
                if not raw_content:
                    continue
                title = self._build_title(channel, message)
                documents.append(
                    self.build_raw_document(
                        config=config,
                        raw_content=raw_content,
                        title=title,
                        metadata={
                            "message_id": message.message_id,
                            "author_id": message.author_id,
                            "author_name": message.author_name,
                            "timestamp": str(message.timestamp),
                            "channel_id": message.channel_id,
                            "channel_name": channel.channel_name or message.channel_name,
                            "channel_type": channel.channel_type,
                            "thread_id": message.thread_id,
                            "thread_name": message.thread_name,
                            "attachments": message.attachments or [],
                            "source_channel_kind": self._classify_channel_kind(channel),
                        },
                    )
                )
            if len(documents) >= config.max_items:
                break

        logger.info(
            "discord_scraper_completed",
            extra={
                "channels_requested": len(channels),
                "documents_collected": len(documents),
                "source_uri": config.source_uri,
            },
        )
        return documents

    def _resolve_token(self, config: SourceConfig) -> str:
        """Resolve Discord bot token from config options/environment."""
        token = str(config.options.get("bot_token") or os.getenv("DISCORD_BOT_TOKEN", "")).strip()
        if not token:
            raise IngestionValidationError("DISCORD_BOT_TOKEN is missing and no bot_token provided in options")
        return token

    def _resolve_channels(self, config: SourceConfig) -> list[DiscordChannelRef]:
        """Resolve channels from SourceConfig options."""
        channels_raw = config.options.get("channels")
        if not channels_raw:
            channel_ids_raw = config.options.get("channel_ids") or []
            channels_raw = [{"channel_id": str(item)} for item in channel_ids_raw]

        channels: list[DiscordChannelRef] = []
        for item in channels_raw or []:
            if not isinstance(item, dict):
                continue
            channel_id = str(item.get("channel_id") or item.get("id") or "").strip()
            if not channel_id:
                continue
            channels.append(
                DiscordChannelRef(
                    channel_id=channel_id,
                    channel_name=(str(item.get("channel_name")).strip() if item.get("channel_name") else None),
                    channel_type=(str(item.get("channel_type")).strip() if item.get("channel_type") else None),
                )
            )
        if not channels:
            raise IngestionValidationError(
                "No Discord channels configured. Provide options.channels or options.channel_ids."
            )
        return channels

    def _resolve_limit(self, config: SourceConfig) -> int:
        """Resolve and clamp message limit per channel."""
        limit = int(config.options.get("limit_per_channel", DEFAULT_LIMIT_PER_CHANNEL))
        if limit <= 0:
            raise IngestionValidationError("limit_per_channel must be greater than zero")
        return max(1, min(limit, MAX_LIMIT_PER_CHANNEL))

    def _build_title(self, channel: DiscordChannelRef, message: DiscordMessagePayload) -> str:
        """Build deterministic title for extracted Discord message."""
        channel_name = channel.channel_name or message.channel_name or channel.channel_id
        author_name = message.author_name or message.author_id
        return f"Discord message in #{channel_name} by {author_name}"

    def _classify_channel_kind(self, channel: DiscordChannelRef) -> str:
        """Classify channel for FAQ/announcement support metadata."""
        name = (channel.channel_name or "").lower()
        declared = (channel.channel_type or "").lower()
        if declared in {"faq", "announcement"}:
            return declared
        if "faq" in name:
            return "faq"
        if "announce" in name or "announcement" in name or "news" in name:
            return "announcement"
        return "general"
