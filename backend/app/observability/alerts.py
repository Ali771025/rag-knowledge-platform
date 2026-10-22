"""Pluggable alerting primitives for observability events."""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Any, Protocol

logger = logging.getLogger("app.observability.alerts")


class AlertCategory(StrEnum):
    """Supported monitoring alert categories."""

    HIGH_LATENCY = "high_latency"
    HIGH_ERROR_RATE = "high_error_rate"
    DAILY_COST_THRESHOLD_EXCEEDED = "daily_cost_threshold_exceeded"
    LLM_FAILURE = "llm_failure"


class AlertSeverity(StrEnum):
    """Relative alert severity."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class AlertEvent:
    """Portable alert payload passed to alert sinks."""

    category: AlertCategory
    title: str
    message: str
    severity: AlertSeverity = AlertSeverity.WARNING
    trace_id: str | None = None
    state: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class AlertSink(Protocol):
    """Abstract sink interface for alert delivery."""

    async def send_alert(self, event: AlertEvent) -> None:
        """Deliver an alert event to the sink destination."""


@dataclass(frozen=True, slots=True)
class AlertThresholds:
    """Threshold values for alert evaluation helpers."""

    high_latency_ms: float = 2_000.0
    high_error_rate: float = 0.1
    daily_cost_usd_threshold: Decimal = Decimal("250")


@dataclass(frozen=True, slots=True)
class AlertCooldownConfig:
    """Cooldown windows to reduce repeated alert storms by category."""

    high_latency: timedelta = timedelta(minutes=5)
    high_error_rate: timedelta = timedelta(minutes=5)
    daily_cost_threshold_exceeded: timedelta = timedelta(minutes=30)
    llm_failure: timedelta = timedelta(minutes=5)

    def for_category(self, category: AlertCategory) -> timedelta:
        if category is AlertCategory.HIGH_LATENCY:
            return self.high_latency
        if category is AlertCategory.HIGH_ERROR_RATE:
            return self.high_error_rate
        if category is AlertCategory.DAILY_COST_THRESHOLD_EXCEEDED:
            return self.daily_cost_threshold_exceeded
        return self.llm_failure


class LogAlertSink:
    """Simple log-based alert sink."""

    def __init__(self, *, logger_name: str = "app.observability.alert_sink") -> None:
        self._logger = logging.getLogger(logger_name)

    async def send_alert(self, event: AlertEvent) -> None:
        self._logger.warning(
            "observability_alert",
            extra={
                "category": event.category.value,
                "severity": event.severity.value,
                "title": event.title,
                "message": event.message,
                "trace_id": event.trace_id,
                "state": event.state,
                "metadata": event.metadata,
            },
        )


class SlackWebhookAlertSink:
    """Slack webhook alert sink.

    This is intentionally a lightweight implementation/stub suitable for production wiring
    via dependency injection without coupling the alert manager to one provider.
    """

    def __init__(self, webhook_url: str | None = None, *, timeout_seconds: float = 2.0) -> None:
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        self.timeout_seconds = timeout_seconds

    async def send_alert(self, event: AlertEvent) -> None:
        if not self.webhook_url:
            return

        try:
            import httpx

            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                await client.post(
                    self.webhook_url,
                    json={
                        "text": f"[{event.severity.value.upper()}] {event.title}",
                        "blocks": [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"*{event.category.value}*\\n{event.message}",
                                },
                            }
                        ],
                    },
                )
        except Exception as exc:
            logger.warning("slack_alert_send_failed", extra={"error": str(exc)})


class EmailAlertSink:
    """Email alert sink interface/stub.

    Replace this with provider-specific implementation (SES/SMTP/etc.) in production.
    """

    async def send_alert(self, event: AlertEvent) -> None:
        logger.info(
            "email_alert_stub",
            extra={
                "category": event.category.value,
                "severity": event.severity.value,
                "title": event.title,
            },
        )


class AlertManager:
    """Evaluates thresholds and dispatches alerts to pluggable sinks.

    Delivery is non-blocking and bounded by sink-local timeouts/failure handling.
    Cooldowns are applied per category to leave room for anti-storm behavior.
    """

    def __init__(
        self,
        *,
        sinks: list[AlertSink] | None = None,
        thresholds: AlertThresholds | None = None,
        cooldowns: AlertCooldownConfig | None = None,
    ) -> None:
        self.sinks = sinks or [LogAlertSink()]
        self.thresholds = thresholds or AlertThresholds()
        self.cooldowns = cooldowns or AlertCooldownConfig()
        self._last_sent_at: dict[AlertCategory, datetime] = {}

    async def maybe_alert_high_latency(
        self,
        *,
        latency_ms: float,
        endpoint: str,
        trace_id: str | None = None,
        state: str | None = None,
    ) -> bool:
        if latency_ms < self.thresholds.high_latency_ms:
            return False

        event = AlertEvent(
            category=AlertCategory.HIGH_LATENCY,
            severity=AlertSeverity.WARNING,
            title="High latency detected",
            message=f"Latency {latency_ms:.2f}ms exceeded threshold on {endpoint}",
            trace_id=trace_id,
            state=state,
            metadata={"latency_ms": latency_ms, "endpoint": endpoint},
        )
        return await self._dispatch_with_cooldown(event)

    async def maybe_alert_high_error_rate(
        self,
        *,
        error_rate: float,
        window_label: str,
        trace_id: str | None = None,
    ) -> bool:
        if error_rate < self.thresholds.high_error_rate:
            return False

        event = AlertEvent(
            category=AlertCategory.HIGH_ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            title="High error rate detected",
            message=f"Error rate {error_rate:.2%} exceeded threshold in {window_label}",
            trace_id=trace_id,
            metadata={"error_rate": error_rate, "window": window_label},
        )
        return await self._dispatch_with_cooldown(event)

    async def maybe_alert_daily_cost_threshold(
        self,
        *,
        total_cost_usd: Decimal,
        period_label: str,
        trace_id: str | None = None,
    ) -> bool:
        if total_cost_usd < self.thresholds.daily_cost_usd_threshold:
            return False

        event = AlertEvent(
            category=AlertCategory.DAILY_COST_THRESHOLD_EXCEEDED,
            severity=AlertSeverity.WARNING,
            title="Daily cost threshold exceeded",
            message=(
                f"Daily cost ${total_cost_usd} exceeded threshold ${self.thresholds.daily_cost_usd_threshold}"
            ),
            trace_id=trace_id,
            metadata={"total_cost_usd": str(total_cost_usd), "period": period_label},
        )
        return await self._dispatch_with_cooldown(event)

    async def maybe_alert_llm_failure(
        self,
        *,
        provider: str,
        error_message: str,
        trace_id: str | None = None,
        state: str | None = None,
    ) -> bool:
        if not error_message.strip():
            return False

        event = AlertEvent(
            category=AlertCategory.LLM_FAILURE,
            severity=AlertSeverity.CRITICAL,
            title="LLM provider failure",
            message=f"LLM provider `{provider}` failure: {error_message}",
            trace_id=trace_id,
            state=state,
            metadata={"provider": provider},
        )
        return await self._dispatch_with_cooldown(event)

    async def emit(self, event: AlertEvent) -> bool:
        """Emit a pre-built event while honoring cooldowns."""

        return await self._dispatch_with_cooldown(event)

    async def _dispatch_with_cooldown(self, event: AlertEvent) -> bool:
        now = datetime.now(UTC)
        last_sent = self._last_sent_at.get(event.category)
        cooldown = self.cooldowns.for_category(event.category)

        if last_sent is not None and (now - last_sent) < cooldown:
            return False

        self._last_sent_at[event.category] = now

        tasks = [asyncio.create_task(self._safe_send(sink, event)) for sink in self.sinks]
        if tasks:
            await asyncio.gather(*tasks)
        return True

    async def _safe_send(self, sink: AlertSink, event: AlertEvent) -> None:
        try:
            await sink.send_alert(event)
        except Exception as exc:
            logger.warning(
                "alert_sink_failed",
                extra={"sink": sink.__class__.__name__, "error": str(exc), "category": event.category.value},
            )
