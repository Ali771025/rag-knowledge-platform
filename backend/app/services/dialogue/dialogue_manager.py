"""Compatibility bridge to the canonical dialogue manager module."""

from app.services.dialogue_manager import BaseDialogueManager, DialogueManager, SimpleDialogueManager

__all__ = [
    "BaseDialogueManager",
    "DialogueManager",
    "SimpleDialogueManager",
]

