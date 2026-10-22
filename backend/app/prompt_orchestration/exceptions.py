"""Prompt orchestration domain exceptions.

These exceptions represent module-level failures only.
They intentionally exclude transport-layer, persistence-layer,
and provider-specific HTTP exception semantics.
"""

from __future__ import annotations


class PromptOrchestrationError(Exception):
    """Base exception for prompt orchestration failures."""


class PromptContractError(PromptOrchestrationError):
    """Raised when request/response contract invariants are violated."""


class UpstreamDependencyError(PromptOrchestrationError):
    """Raised when required upstream context providers fail."""


class DownstreamDependencyError(PromptOrchestrationError):
    """Raised when downstream inference gateway integration fails."""


class PromptOrchestrationConfigurationError(PromptOrchestrationError):
    """Raised when module configuration is incomplete or invalid."""


class PromptOrchestrationApplicationError(PromptOrchestrationError):
    """Raised when application-service orchestration flow fails."""


class PromptPlanningError(PromptOrchestrationApplicationError):
    """Raised when deterministic strategy planning fails."""


class ContextAssemblyError(PromptOrchestrationApplicationError):
    """Raised when context normalization/assembly fails."""


class TemplateResolutionError(PromptOrchestrationApplicationError):
    """Raised when a required template cannot be resolved."""


class PromptBuildPipelineError(PromptOrchestrationApplicationError):
    """Raised when prompt build assembly fails."""
