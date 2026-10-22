"""Main application service for prompt orchestration flow."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Mapping

from app.prompt_orchestration.context_assembler import AssembledContext, ContextAssembler
from app.prompt_orchestration.config import PromptOrchestrationConfig
from app.prompt_orchestration.context_models import PromptContextEnvelope
from app.prompt_orchestration.exceptions import (
    ContextAssemblyError,
    PromptBuildPipelineError,
    PromptContractError,
    PromptOrchestrationApplicationError,
    PromptPlanningError,
    TemplateResolutionError,
)
from app.prompt_orchestration.grounding_policy_engine import (
    GroundingPolicyEngine,
    GroundingPolicyMode,
    GroundingPromptConstraints,
    GroundingPolicyRequest,
    InsufficientContextPolicy,
)
from app.prompt_orchestration.models import (
    GroundingMode,
    GroundingPolicy,
    OutputContract,
    OutputFormat,
    PromptBuildResult,
    PromptOrchestrationRequest,
)
from app.prompt_orchestration.output_contract_engine import (
    OutputContractEngine,
    OutputContractRequest,
    OutputPromptConstraints,
    OutputResponseFormat,
    OutputStyleProfile,
)
from app.prompt_orchestration.planner import PromptPlanner
from app.prompt_orchestration.prompt_builder import PromptBuildDraft, PromptBuilder, PromptBuilderInput
from app.prompt_orchestration.observability import (
    LoggingPromptAuditSink,
    LoggingPromptOrchestrationMetrics,
    NoOpPromptAuditSink,
    NoOpPromptOrchestrationMetrics,
    PromptAuditRecordFactory,
    PromptAuditSink,
    PromptOrchestrationMetrics,
    PromptTraceMetadata,
)
from app.prompt_orchestration.strategies import StrategySelectionRequest
from app.prompt_orchestration.strategies import PromptStrategyType
from app.prompt_orchestration.template_registry import (
    build_representative_templates,
    PromptTemplateRegistry,
    TemplateEnvironment,
    TemplateLookupRequest,
    TemplateLookupResult,
)
from app.prompt_orchestration.validation import (
    PromptBuildRequestValidator,
    PromptBuildValidationRequest,
)


@dataclass(frozen=True, slots=True)
class PromptOrchestrationRequestEnvelope:
    """Application-level request envelope for orchestration execution."""

    request: PromptOrchestrationRequest
    context: PromptContextEnvelope = field(default_factory=PromptContextEnvelope)
    template_variables: Mapping[str, Any] = field(default_factory=dict)
    trace_metadata: PromptTraceMetadata = field(default_factory=PromptTraceMetadata)


class PromptOrchestrationService:
    """Application service that orchestrates prompt planning and building."""

    def __init__(
        self,
        *,
        planner: PromptPlanner,
        context_assembler: ContextAssembler,
        grounding_policy_engine: GroundingPolicyEngine,
        output_contract_engine: OutputContractEngine,
        template_registry: PromptTemplateRegistry,
        prompt_builder: PromptBuilder,
        validator: PromptBuildRequestValidator | None = None,
        metrics: PromptOrchestrationMetrics | None = None,
        audit_sink: PromptAuditSink | None = None,
        audit_factory: PromptAuditRecordFactory | None = None,
        config: PromptOrchestrationConfig | None = None,
    ) -> None:
        resolved_config = config or PromptOrchestrationConfig()
        self._planner = planner
        self._context_assembler = context_assembler
        self._grounding_policy_engine = grounding_policy_engine
        self._output_contract_engine = output_contract_engine
        self._template_registry = template_registry
        self._prompt_builder = prompt_builder
        self._validator = validator or PromptBuildRequestValidator.default(limits=context_assembler.limits)
        self._metrics = metrics or NoOpPromptOrchestrationMetrics()
        self._audit_sink = audit_sink or NoOpPromptAuditSink()
        self._audit_factory = audit_factory or PromptAuditRecordFactory()
        self._config = resolved_config

    @classmethod
    def default(cls, *, config: PromptOrchestrationConfig | None = None) -> PromptOrchestrationService:
        """Construct service with deterministic default dependencies."""
        resolved_config = config or PromptOrchestrationConfig.from_env()
        context_assembler = ContextAssembler(limits=resolved_config.context_budgets.to_limits())
        metrics: PromptOrchestrationMetrics
        if resolved_config.observability.metrics_enabled:
            metrics = LoggingPromptOrchestrationMetrics(logger_name=resolved_config.observability.metrics_logger_name)
        else:
            metrics = NoOpPromptOrchestrationMetrics()

        audit_sink: PromptAuditSink
        if resolved_config.observability.audit_enabled:
            audit_sink = LoggingPromptAuditSink(logger_name=resolved_config.observability.audit_logger_name)
        else:
            audit_sink = NoOpPromptAuditSink()

        return cls(
            planner=PromptPlanner(),
            context_assembler=context_assembler,
            grounding_policy_engine=GroundingPolicyEngine(),
            output_contract_engine=OutputContractEngine(),
            template_registry=PromptTemplateRegistry(
                templates=build_representative_templates(),
                default_language=resolved_config.templates.default_language,
            ),
            prompt_builder=PromptBuilder(),
            metrics=metrics,
            audit_sink=audit_sink,
            audit_factory=PromptAuditRecordFactory(preview_chars=resolved_config.observability.audit_preview_chars),
            config=resolved_config,
        )

    def orchestrate(self, envelope: PromptOrchestrationRequestEnvelope) -> PromptBuildResult:
        """Execute full prompt orchestration flow and return PromptBuildResult."""
        request = envelope.request
        request_id_for_observability = request.request_id.strip() if request.request_id else "missing-request-id"
        trace_metadata = self._resolve_trace_metadata(envelope)
        request_id = self._validated_request_id(request)
        start = perf_counter()
        metric_tags = self._metric_tags(request=request, trace=trace_metadata)
        self._metrics.prompt_build_count(tags=metric_tags)

        try:
            self._validator.validate(
                PromptBuildValidationRequest(
                    request=request,
                    context=envelope.context,
                    template_variables=envelope.template_variables,
                )
            )
            assembled_context = self._assemble_context(envelope.context)
            planning_result = self._planner.plan(
                StrategySelectionRequest(
                    request_id=request_id,
                    user_input=request.user_input,
                    conversation_history=tuple(item.message for item in assembled_context.conversational_messages),
                    context_snippets=tuple(chunk.content for chunk in assembled_context.authoritative_chunks),
                    metadata=request.metadata,
                )
            )
            template_lookup = self._resolve_template(request.metadata, planning_result.selected_strategy)
            grounding_constraints, grounding_policy = self._derive_grounding_constraints(request.metadata, assembled_context)
            output_constraints, output_contract = self._derive_output_constraints(request.metadata)

            draft = self._prompt_builder.build(
                PromptBuilderInput(
                    request_id=request_id,
                    user_input=request.user_input,
                    template_lookup=template_lookup,
                    planning=planning_result,
                    assembled_context=assembled_context,
                    grounding_constraints=grounding_constraints,
                    output_constraints=output_constraints,
                    output_contract=output_contract,
                    grounding_policy=grounding_policy,
                    template_variables=envelope.template_variables,
                    metadata=request.metadata,
                )
            )
            result = self._materialize_result(draft)
            elapsed_ms = (perf_counter() - start) * 1000
            self._metrics.prompt_build_latency(latency_ms=elapsed_ms, tags=metric_tags)
            self._metrics.template_usage(
                template_id=result.template_ref.template_id,
                version=result.template_ref.version,
                tags=metric_tags,
            )
            self._metrics.grounding_mode_usage(grounding_mode=result.grounding_policy.mode.value, tags=metric_tags)
            self._metrics.output_contract_usage(output_format=result.output_contract.format.value, tags=metric_tags)
            self._audit_sink.record(
                self._audit_factory.build_success(
                    result=result,
                    trace=trace_metadata,
                    metadata=self._audit_metadata(request.metadata),
                )
            )
            return result
        except PromptOrchestrationApplicationError as exc:
            elapsed_ms = (perf_counter() - start) * 1000
            self._metrics.prompt_build_latency(latency_ms=elapsed_ms, tags=metric_tags)
            self._metrics.prompt_failures(error_type=type(exc).__name__, tags=metric_tags)
            self._audit_sink.record(
                self._audit_factory.build_failure(
                    request_id=request_id_for_observability,
                    trace=trace_metadata,
                    failure_type=type(exc).__name__,
                    failure_message=str(exc),
                    metadata=self._audit_metadata(request.metadata),
                )
            )
            raise
        except PromptContractError as exc:
            elapsed_ms = (perf_counter() - start) * 1000
            self._metrics.prompt_build_latency(latency_ms=elapsed_ms, tags=metric_tags)
            self._metrics.prompt_failures(error_type=type(exc).__name__, tags=metric_tags)
            self._audit_sink.record(
                self._audit_factory.build_failure(
                    request_id=request_id_for_observability,
                    trace=trace_metadata,
                    failure_type=type(exc).__name__,
                    failure_message=str(exc),
                    metadata=self._audit_metadata(request.metadata),
                )
            )
            raise PromptOrchestrationApplicationError(
                f"Prompt orchestration failed for request `{request_id}`: {exc}"
            ) from exc

    def _validated_request_id(self, request: PromptOrchestrationRequest) -> str:
        if not request.request_id:
            raise PromptContractError("`request_id` is required for prompt orchestration.")
        return request.request_id

    def _assemble_context(self, context: PromptContextEnvelope) -> AssembledContext:
        try:
            return self._context_assembler.assemble(context)
        except PromptContractError as exc:
            raise ContextAssemblyError(f"Context assembly failed: {exc}") from exc

    def _resolve_template(self, metadata: Mapping[str, Any], strategy: PromptStrategyType) -> TemplateLookupResult:
        language = str(
            metadata.get(
                "language",
                self._config.language.default_language,
            )
        ).strip().lower()
        version = metadata.get("template_version", self._config.templates.default_versions.get(strategy))
        environment = str(metadata.get("environment", TemplateEnvironment.DEFAULT)).strip().lower()
        try:
            return self._template_registry.lookup(
                TemplateLookupRequest(
                    strategy=strategy,
                    language=language,
                    version=None if version is None else str(version),
                    environment=environment,
                )
            )
        except PromptContractError as exc:
            raise TemplateResolutionError(f"Template lookup failed: {exc}") from exc

    def _derive_grounding_constraints(
        self, metadata: Mapping[str, Any], assembled_context: AssembledContext
    ) -> tuple[GroundingPromptConstraints, GroundingPolicy]:
        try:
            mode = GroundingPolicyMode(
                str(metadata.get("grounding_mode", self._config.grounding.default_mode)).strip().lower()
            )
        except ValueError as exc:
            supported = ", ".join(item.value for item in GroundingPolicyMode)
            raise PromptPlanningError(
                f"Unsupported grounding_mode `{metadata.get('grounding_mode')}`. Supported values: {supported}."
            ) from exc

        try:
            insufficient = InsufficientContextPolicy(
                str(
                    metadata.get(
                        "insufficient_context_policy",
                        self._config.grounding.default_insufficient_context_policy,
                    )
                )
                .strip()
                .lower()
            )
        except ValueError as exc:
            supported = ", ".join(item.value for item in InsufficientContextPolicy)
            raise PromptPlanningError(
                "Unsupported insufficient_context_policy "
                f"`{metadata.get('insufficient_context_policy')}`. Supported values: {supported}."
            ) from exc

        constraints = self._grounding_policy_engine.build_constraints(
            GroundingPolicyRequest(
                mode=mode,
                insufficient_context_policy=insufficient,
                has_authoritative_context=bool(assembled_context.authoritative_chunks),
                authoritative_context_count=len(assembled_context.authoritative_chunks),
            )
        )

        if mode is GroundingPolicyMode.STRICT_GROUNDED:
            policy = GroundingPolicy(
                mode=GroundingMode.REQUIRED,
                require_citations=True,
                min_citations=1,
                allow_unverified_claims=False,
            )
        elif mode is GroundingPolicyMode.GROUNDED_PREFERRED:
            policy = GroundingPolicy(
                mode=GroundingMode.PREFERRED,
                require_citations=False,
                min_citations=0,
                allow_unverified_claims=False,
            )
        else:
            policy = GroundingPolicy(
                mode=GroundingMode.DISABLED,
                require_citations=False,
                min_citations=0,
                allow_unverified_claims=False,
            )
        return constraints, policy

    def _derive_output_constraints(self, metadata: Mapping[str, Any]) -> tuple[OutputPromptConstraints, OutputContract]:
        output_format_raw = str(metadata.get("output_format", OutputResponseFormat.PLAIN_TEXT)).strip().lower()
        try:
            output_format = OutputResponseFormat(output_format_raw)
        except ValueError as exc:
            supported = ", ".join(item.value for item in OutputResponseFormat)
            raise PromptPlanningError(f"Unsupported output_format `{output_format_raw}`. Supported values: {supported}.") from exc

        style_profile = OutputStyleProfile(
            style=metadata.get("style"),
            tone=metadata.get("tone"),
            language=str(metadata.get("language", self._config.language.default_language)),
            compliance_constraints=tuple(metadata.get("compliance_constraints", ())),
            max_response_chars=metadata.get("max_response_chars"),
        )

        request = OutputContractRequest(
            format=output_format,
            style_profile=style_profile,
            json_required_fields=tuple(metadata.get("json_required_fields", ())),
            json_schema=metadata.get("json_schema"),
        )
        constraints = self._output_contract_engine.build_constraints(request)

        if output_format in {OutputResponseFormat.PLAIN_TEXT, OutputResponseFormat.MARKDOWN}:
            contract = OutputContract(format=OutputFormat.TEXT)
        elif output_format is OutputResponseFormat.JSON:
            contract = OutputContract(format=OutputFormat.JSON_OBJECT)
        else:
            contract = OutputContract(format=OutputFormat.JSON_SCHEMA, json_schema=request.json_schema)

        return constraints, contract

    def _materialize_result(self, draft: PromptBuildDraft) -> PromptBuildResult:
        try:
            return draft.to_prompt_build_result()
        except PromptContractError as exc:
            raise PromptBuildPipelineError(f"Prompt build materialization failed: {exc}") from exc

    def _resolve_trace_metadata(self, envelope: PromptOrchestrationRequestEnvelope) -> PromptTraceMetadata:
        trace = envelope.trace_metadata
        metadata = envelope.request.metadata
        return PromptTraceMetadata(
            trace_id=trace.trace_id or self._normalized_optional_str(metadata.get("trace_id")),
            correlation_id=trace.correlation_id or self._normalized_optional_str(metadata.get("correlation_id")),
            span_id=trace.span_id or self._normalized_optional_str(metadata.get("span_id")),
            source_service=trace.source_service or self._normalized_optional_str(metadata.get("source_service")),
            tags={**dict(trace.tags), **self._trace_tags_from_metadata(metadata)},
        )

    def _trace_tags_from_metadata(self, metadata: Mapping[str, Any]) -> Mapping[str, str]:
        value = metadata.get("trace_tags")
        if not isinstance(value, Mapping):
            return {}
        tags: dict[str, str] = {}
        for key, item in value.items():
            key_text = self._normalized_optional_str(key)
            item_text = self._normalized_optional_str(item)
            if key_text and item_text:
                tags[key_text] = item_text
        return tags

    def _metric_tags(self, *, request: PromptOrchestrationRequest, trace: PromptTraceMetadata) -> Mapping[str, str]:
        tags: dict[str, str] = {}
        if trace.trace_id:
            tags["trace_id"] = trace.trace_id
        if trace.correlation_id:
            tags["correlation_id"] = trace.correlation_id
        if trace.source_service:
            tags["source_service"] = trace.source_service

        interaction = self._normalized_optional_str(request.metadata.get("interaction_type"))
        if interaction:
            tags["interaction_type"] = interaction
        return tags

    def _audit_metadata(self, metadata: Mapping[str, Any]) -> Mapping[str, Any]:
        keys_to_capture = (
            "interaction_type",
            "intent",
            "language",
            "environment",
            "output_format",
            "grounding_mode",
        )
        return {key: metadata[key] for key in keys_to_capture if key in metadata}

    def _normalized_optional_str(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip()
            return normalized if normalized else None
        normalized = str(value).strip()
        return normalized if normalized else None
