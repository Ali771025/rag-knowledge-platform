"""RAG-specific exception placeholders.

Owns RAG-domain failure types only.
Must not duplicate global transport/error-mapping logic.
"""


class RAGError(Exception):
    """Base exception for RAG module failures."""
