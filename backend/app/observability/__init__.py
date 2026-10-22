"""Observability and cost monitoring package boundary.

Owns transport-agnostic observability domain contracts for:
- request/session telemetry events
- token and cost accounting models
- dependency health and alerting signals

Must not implement:
- dialogue-policy or response generation decisions (owned by Dialogue Manager)
- retrieval reasoning and ranking logic (owned by `app.rag`)
- prompt composition logic (owned by `app.prompt_orchestration`)
- API routing, auth, or middleware concerns (owned by `app.api` and `app.middleware`)
- provider SDK/http execution paths (owned by LLM transport/service adapters)
"""

from app.observability.enums import (
    AlertSeverity,
    AlertType,
    DependencyType,
    HealthState,
    LogCategory,
    SessionState,
)
from app.observability.exceptions import (
    ObservabilityAlertError,
    ObservabilityAnalyticsError,
    ObservabilityConfigurationError,
    ObservabilityContractError,
    ObservabilityError,
    ObservabilityIntegrationError,
    ObservabilityPersistenceError,
)
from app.observability.cost_models import CostLogEntryResult, CostTotalResult, ProjectedMonthlyCostResult
from app.observability.cost_tracker import CostTracker, ProviderPricingConfig
from app.observability.analytics_models import AnalyticsSummarySnapshot
from app.observability.analytics_summary_service import AnalyticsSummaryService
from app.observability.health_check_service import (
    HealthCheckConfig,
    HealthCheckService,
)
from app.observability.health_models import HealthCheckReport
from app.observability.logging_helpers import LoggingContext, ObservabilityLoggingHelper
from app.observability.logging_models import StructuredLogCategory, StructuredLogEvent, StructuredLogLevel
from app.observability.models import (
    AlertEvent,
    AnalyticsSummary,
    CTAResponseEvent,
    ConversionEvent,
    DependencyHealthResult,
    FunnelOutcomeEvent,
    RequestMetricsEvent,
    SessionRecord,
    TriggerEvent,
)
from app.observability.event_emitter import AsyncEventEmitter
from app.observability.outcome_logger import OutcomeLogger
from app.observability.metrics_collector import MetricsCollector
from app.observability.metrics_registry import (
    ObservabilityMetricsRegistry,
    get_observability_metrics_registry,
)
from app.observability.alerts import (
    AlertCategory,
    AlertCooldownConfig,
    AlertEvent as MonitoringAlertEvent,
    AlertManager,
    AlertSeverity as MonitoringAlertSeverity,
    AlertSink as MonitoringAlertSink,
    AlertThresholds,
    EmailAlertSink,
    LogAlertSink,
    SlackWebhookAlertSink,
)
from app.observability.request_context import (
    attach_request_cost_usd,
    attach_request_state,
    attach_request_tokens,
)
from app.observability.request_trace import (
    RequestTraceRuntime,
    build_trace_context,
    clear_current_trace_context,
    generate_trace_id,
    get_current_trace_context,
    get_request_latency_ms,
    initialize_request_trace,
    set_current_trace_context,
)
from app.observability.structured_logger import RedactionConfig, StructuredLogger, get_structured_logger
from app.observability.protocols import (
    AlertSink,
    AnalyticsSummaryReader,
    ConversationLogRepositoryContract,
    CostRecordSink,
    CostLogRepositoryContract,
    DependencyHealthSink,
    RequestMetricsSink,
    SessionRecordSink,
    SessionLogRepositoryContract,
)
from app.observability.repository_models import CostByPeriodAggregate, CostByStateAggregate, LatencySummaryInputs
from app.observability.value_objects import CostRecord, LatencyRecord, TokenUsageRecord, TraceContext

__all__ = [
    "AlertEvent",
    "AlertSeverity",
    "AlertSink",
    "AlertType",
    "AnalyticsSummary",
    "AnalyticsSummarySnapshot",
    "AnalyticsSummaryService",
    "AnalyticsSummaryReader",
    "AsyncEventEmitter",
    "OutcomeLogger",
    "ConversionEvent",
    "CTAResponseEvent",
    "TriggerEvent",
    "FunnelOutcomeEvent",
    "ConversationLogRepositoryContract",
    "CostLogEntryResult",
    "CostRecord",
    "CostRecordSink",
    "CostByPeriodAggregate",
    "CostByStateAggregate",
    "CostTotalResult",
    "CostLogRepositoryContract",
    "CostTracker",
    "EmailAlertSink",
    "DependencyHealthResult",
    "DependencyHealthSink",
    "DependencyType",
    "HealthState",
    "HealthCheckConfig",
    "HealthCheckReport",
    "HealthCheckService",
    "LatencySummaryInputs",
    "LatencyRecord",
    "LogCategory",
    "LoggingContext",
    "MetricsCollector",
    "MonitoringAlertSeverity",
    "MonitoringAlertSink",
    "ObservabilityLoggingHelper",
    "ObservabilityMetricsRegistry",
    "ObservabilityAlertError",
    "ObservabilityAnalyticsError",
    "ObservabilityConfigurationError",
    "ObservabilityContractError",
    "ObservabilityError",
    "ObservabilityIntegrationError",
    "ObservabilityPersistenceError",
    "ProjectedMonthlyCostResult",
    "ProviderPricingConfig",
    "RedactionConfig",
    "AlertManager",
    "AlertThresholds",
    "AlertCooldownConfig",
    "AlertCategory",
    "MonitoringAlertEvent",
    "SlackWebhookAlertSink",
    "LogAlertSink",
    "RequestMetricsEvent",
    "RequestMetricsSink",
    "RequestTraceRuntime",
    "SessionRecord",
    "SessionRecordSink",
    "SessionLogRepositoryContract",
    "SessionState",
    "StructuredLogCategory",
    "StructuredLogEvent",
    "StructuredLogLevel",
    "StructuredLogger",
    "TokenUsageRecord",
    "TraceContext",
    "attach_request_cost_usd",
    "attach_request_state",
    "attach_request_tokens",
    "build_trace_context",
    "clear_current_trace_context",
    "generate_trace_id",
    "get_current_trace_context",
    "get_observability_metrics_registry",
    "get_request_latency_ms",
    "get_structured_logger",
    "initialize_request_trace",
    "set_current_trace_context",
]
