"""Dialogue service namespace with lazy exports to avoid import-time cycles."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "BaseDialogueManager",
    "DialogueManager",
    "SimpleDialogueManager",
    "DialogueIntelligenceHooks",
    "DialogueOrchestrationServices",
    "DialoguePolicySnapshot",
    "LoggingEventEmitter",
    "PersonaServiceHook",
    "ConversionServiceHook",
    "build_dialogue_orchestration_services",
    "load_dialogue_policy_snapshot",
]

_EXPORTS: dict[str, tuple[str, str]] = {
    "BaseDialogueManager": ("app.services.dialogue.dialogue_manager", "BaseDialogueManager"),
    "DialogueManager": ("app.services.dialogue.dialogue_manager", "DialogueManager"),
    "SimpleDialogueManager": ("app.services.dialogue.dialogue_manager", "SimpleDialogueManager"),
    "DialogueIntelligenceHooks": ("app.services.dialogue.service", "DialogueIntelligenceHooks"),
    "DialogueOrchestrationServices": ("app.services.dialogue.service", "DialogueOrchestrationServices"),
    "DialoguePolicySnapshot": ("app.services.dialogue.service", "DialoguePolicySnapshot"),
    "LoggingEventEmitter": ("app.services.dialogue.service", "LoggingEventEmitter"),
    "PersonaServiceHook": ("app.services.dialogue.service", "PersonaServiceHook"),
    "ConversionServiceHook": ("app.services.dialogue.service", "ConversionServiceHook"),
    "build_dialogue_orchestration_services": ("app.services.dialogue.service", "build_dialogue_orchestration_services"),
    "load_dialogue_policy_snapshot": ("app.services.dialogue.service", "load_dialogue_policy_snapshot"),
}


def __getattr__(name: str) -> Any:
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = target
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
