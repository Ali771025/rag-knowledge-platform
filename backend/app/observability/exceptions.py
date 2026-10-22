"""Observability and cost monitoring domain exceptions.

These exceptions represent failures inside the observability layer only.
They intentionally exclude transport/framework exception semantics.
"""

from __future__ import annotations


class ObservabilityError(Exception):
    """Base exception for observability-layer failures."""


class ObservabilityContractError(ObservabilityError):
    """Raised when observability domain contract invariants are violated."""


class ObservabilityConfigurationError(ObservabilityError):
    """Raised when observability configuration is invalid or incomplete."""


class ObservabilityIntegrationError(ObservabilityError):
    """Raised when an observability dependency boundary fails."""


class ObservabilityPersistenceError(ObservabilityError):
    """Raised when observability records cannot be persisted or loaded."""


class ObservabilityAnalyticsError(ObservabilityError):
    """Raised when analytics aggregation contracts cannot be satisfied."""


class ObservabilityAlertError(ObservabilityError):
    """Raised when alert evaluation or dispatch contracts fail."""
