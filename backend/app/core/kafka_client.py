"""Kafka client adapter."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


class KafkaError(Exception):
    """Base Kafka adapter exception."""


class KafkaConfigurationError(KafkaError):
    """Raised when Kafka config is missing/invalid."""


class KafkaPublishError(KafkaError):
    """Raised when Kafka publish operation fails."""


class KafkaClientAdapter:
    """Optional Kafka producer wrapper with standardized event publishing."""

    def __init__(
        self,
        bootstrap_servers: str | None = None,
        enabled: bool | None = None,
        strict_mode: bool | None = None,
    ) -> None:
        self.bootstrap_servers = bootstrap_servers or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "")
        env_kafka_enabled = os.getenv("KAFKA_ENABLED")
        env_enable_kafka_events = os.getenv("ENABLE_KAFKA_EVENTS")
        enabled_flag = env_kafka_enabled if env_kafka_enabled is not None else env_enable_kafka_events
        self.enabled = (
            enabled
            if enabled is not None
            else str(enabled_flag or "false").strip().lower() in {"1", "true", "yes"}
        )
        self.strict_mode = (
            strict_mode
            if strict_mode is not None
            else os.getenv("KAFKA_STRICT_MODE", "false").strip().lower() in {"1", "true", "yes"}
        )
        self.topic_prefix = os.getenv("KAFKA_TOPIC_PREFIX", "").strip()
        self._producer: Any | None = None

    def _get_producer(self) -> Any:
        if self._producer is not None:
            return self._producer
        if not self.enabled:
            raise KafkaConfigurationError("Kafka is disabled")
        if not self.bootstrap_servers:
            raise KafkaConfigurationError("KAFKA_BOOTSTRAP_SERVERS is not configured")
        try:
            from kafka import KafkaProducer

            self._producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda value: json.dumps(value).encode("utf-8"),
                linger_ms=int(os.getenv("KAFKA_LINGER_MS", "5")),
                retries=int(os.getenv("KAFKA_RETRIES", "3")),
            )
            return self._producer
        except Exception as exc:
            raise KafkaConfigurationError("failed to initialize Kafka producer") from exc

    def publish(self, topic: str, payload: dict[str, Any]) -> bool:
        """Publish payload to topic.

        Returns True when sent; False when safely skipped in no-op mode.
        """
        if not self.enabled:
            logger.info("kafka_publish_skipped", extra={"topic": topic})
            return False
        producer = self._get_producer()
        try:
            normalized_payload = self._ensure_json_serializable(payload)
            future = producer.send(topic, normalized_payload)
            future.get(timeout=float(os.getenv("KAFKA_SEND_TIMEOUT_SEC", "10")))
            logger.info("kafka_publish_success", extra={"topic": topic})
            return True
        except Exception as exc:
            raise KafkaPublishError("failed to publish Kafka message") from exc

    def publish_event(
        self,
        event_name: str,
        payload: dict[str, Any],
        *,
        correlation_id: str,
        ingestion_job_id: str,
    ) -> bool:
        """Publish a standardized event envelope."""
        topic = self._resolve_topic(event_name)
        payload_with_context = {
            **payload,
            "correlation_id": correlation_id,
            "ingestion_job_id": ingestion_job_id,
        }
        envelope = {
            "event": event_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation_id": correlation_id,
            "ingestion_job_id": ingestion_job_id,
            "payload": payload_with_context,
        }
        return self.publish(topic=topic, payload=envelope)

    def close(self) -> None:
        """Close producer safely."""
        if self._producer is None:
            return
        try:
            self._producer.flush(timeout=float(os.getenv("KAFKA_FLUSH_TIMEOUT_SEC", "10")))
            self._producer.close()
            self._producer = None
        except Exception as exc:
            raise KafkaPublishError("failed to close Kafka producer") from exc

    def _resolve_topic(self, event_name: str) -> str:
        if self.topic_prefix:
            return f"{self.topic_prefix}.{event_name}"
        return event_name

    def _ensure_json_serializable(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return json.loads(json.dumps(payload, default=self._json_default))
        except Exception as exc:
            raise KafkaPublishError("Kafka payload must be JSON serializable") from exc

    def _json_default(self, value: Any) -> Any:
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.isoformat()
        if isinstance(value, set):
            return list(value)
        return str(value)
