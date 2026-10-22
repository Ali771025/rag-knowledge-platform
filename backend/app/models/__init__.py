"""Model package exports with resilient optional-import guards."""

from __future__ import annotations

from importlib import import_module
from typing import Iterable

__all__ = [
    "User",
    "Session",
    "SessionLog",
    "Conversation",
    "ConversationLog",
    "CostLog",
    "Document",
    "DocumentProcessingJob",
    "Chunk",
    "DocumentMetadata",
    "KnowledgeGraphRecord",
    "IngestionJob",
    "KnowledgeSource",
    "RAGConfiguration",
    "MemorySummary",
    "SemanticCacheLog",
    "LLMUsageLog",
    "RoutingDecisionLog",
    "TaskLog",
    "Invite",
    "PersonaState",
    "PersonaHistory",
    "ModifierHistory",
    "FunnelState",
    "ConversionEvent",
    "TriggerEffectiveness",
    "APIKeyMetadata",
    "TokenUsageLog",
    "DailyAggregate",
    "OptimizationRecommendation",
    "BudgetAlert",
    "APIKeyBudgetConfig",
    "BudgetChangeAuditLog",
    "ReferralLink",
    "ReferralProgressEvent",
    "ReferralChatThread",
    "ReferralChatMessage",
    "AgentUserState",
    "DetectedSignal",
    "ConversationTurn",
    "UserInteractionEvent",
    "PersonaAssessment",
    "RecommendationDecision",
    "OrchestratorExecution",
    "QualificationAnswer",
    "ProductWeightTableVersion",
    "ProductCatalogItem",
    "ProductPersonaWeight",
]

_SYMBOL_MODULE_MAP = {
    "User": "app.models.user",
    "Session": "app.models.session",
    "SessionLog": "app.models.session_log",
    "Conversation": "app.models.conversation",
    "ConversationLog": "app.models.conversation_log",
    "CostLog": "app.models.cost_log",
    "Document": "app.models.document",
    "DocumentProcessingJob": "app.models.document_job",
    "Chunk": "app.models.chunk",
    "DocumentMetadata": "app.models.metadata",
    "KnowledgeGraphRecord": "app.models.knowledge_graph",
    "IngestionJob": "app.models.ingestion_job",
    "KnowledgeSource": "app.models.knowledge_source",
    "RAGConfiguration": "app.models.rag_configuration",
    "MemorySummary": "app.models.memory_summary",
    "SemanticCacheLog": "app.models.cache.logs",
    "LLMUsageLog": "app.models.llm.logs",
    "RoutingDecisionLog": "app.models.llm.logs",
    "TaskLog": "app.models.task_log",
    "Invite": "app.models.invite",
    "PersonaState": "app.models.persona_conversion",
    "PersonaHistory": "app.models.persona_conversion",
    "ModifierHistory": "app.models.persona_conversion",
    "FunnelState": "app.models.persona_conversion",
    "ConversionEvent": "app.models.persona_conversion",
    "TriggerEffectiveness": "app.models.persona_conversion",
    "APIKeyMetadata": "app.models.token_monitoring",
    "TokenUsageLog": "app.models.token_monitoring",
    "DailyAggregate": "app.models.token_monitoring",
    "OptimizationRecommendation": "app.models.token_monitoring",
    "BudgetAlert": "app.models.token_monitoring",
    "APIKeyBudgetConfig": "app.models.token_monitoring",
    "BudgetChangeAuditLog": "app.models.token_monitoring",
    "ReferralLink": "app.models.referral",
    "ReferralProgressEvent": "app.models.referral",
    "ReferralChatThread": "app.models.referral",
    "ReferralChatMessage": "app.models.referral",
    "AgentUserState": "app.qora.infrastructure.persistence.models",
    "DetectedSignal": "app.qora.infrastructure.persistence.models",
    "ConversationTurn": "app.qora.infrastructure.persistence.models",
    "UserInteractionEvent": "app.qora.infrastructure.persistence.models",
    "PersonaAssessment": "app.qora.infrastructure.persistence.models",
    "RecommendationDecision": "app.qora.infrastructure.persistence.models",
    "OrchestratorExecution": "app.qora.infrastructure.persistence.models",
    "QualificationAnswer": "app.qora.infrastructure.persistence.models",
    "ProductWeightTableVersion": "app.qora.infrastructure.persistence.models",
    "ProductCatalogItem": "app.qora.infrastructure.persistence.models",
    "ProductPersonaWeight": "app.qora.infrastructure.persistence.models",
}


def _try_import(module_path: str, symbols: Iterable[str]) -> None:
    """Import symbols without breaking all model exports on one failure."""
    try:
        module = import_module(module_path)
    except Exception:
        # Optional import guard allows lightweight contract-only imports in envs
        # where ORM dependencies are not installed.
        return

    for symbol in symbols:
        value = getattr(module, symbol, None)
        if value is not None:
            globals()[symbol] = value


def _safe_import() -> None:
    _try_import("app.models.chunk", ("Chunk",))
    _try_import("app.models.conversation", ("Conversation",))
    _try_import("app.models.conversation_log", ("ConversationLog",))
    _try_import("app.models.cost_log", ("CostLog",))
    _try_import("app.models.document", ("Document",))
    _try_import("app.models.document_job", ("DocumentProcessingJob",))
    _try_import("app.models.ingestion_job", ("IngestionJob",))
    _try_import("app.models.invite", ("Invite",))
    _try_import("app.models.knowledge_source", ("KnowledgeSource",))
    _try_import("app.models.knowledge_graph", ("KnowledgeGraphRecord",))
    _try_import("app.models.rag_configuration", ("RAGConfiguration",))
    _try_import("app.models.memory_summary", ("MemorySummary",))
    _try_import("app.models.metadata", ("DocumentMetadata",))
    _try_import("app.models.session", ("Session",))
    _try_import("app.models.session_log", ("SessionLog",))
    _try_import("app.models.task_log", ("TaskLog",))
    _try_import("app.models.user", ("User",))
    _try_import("app.models.cache.logs", ("SemanticCacheLog",))
    _try_import("app.models.llm.logs", ("LLMUsageLog", "RoutingDecisionLog"))
    _try_import(
        "app.models.persona_conversion",
        (
            "ConversionEvent",
            "FunnelState",
            "ModifierHistory",
            "PersonaHistory",
            "PersonaState",
            "TriggerEffectiveness",
        ),
    )
    _try_import(
        "app.models.token_monitoring",
        (
            "APIKeyMetadata",
            "TokenUsageLog",
            "DailyAggregate",
            "OptimizationRecommendation",
            "BudgetAlert",
            "APIKeyBudgetConfig",
            "BudgetChangeAuditLog",
        ),
    )
    _try_import(
        "app.models.referral",
        (
            "ReferralLink",
            "ReferralProgressEvent",
            "ReferralChatThread",
            "ReferralChatMessage",
        ),
    )
    _try_import(
        "app.qora.infrastructure.persistence.models",
        (
            "AgentUserState",
            "DetectedSignal",
            "ConversationTurn",
            "UserInteractionEvent",
            "PersonaAssessment",
            "RecommendationDecision",
            "OrchestratorExecution",
            "QualificationAnswer",
            "ProductWeightTableVersion",
            "ProductCatalogItem",
            "ProductPersonaWeight",
        ),
    )


def __getattr__(name: str):
    module_path = _SYMBOL_MODULE_MAP.get(name)
    if not module_path:
        raise AttributeError(name)
    _try_import(module_path, (name,))
    value = globals().get(name)
    if value is None:
        raise AttributeError(name)
    return value


_safe_import()
