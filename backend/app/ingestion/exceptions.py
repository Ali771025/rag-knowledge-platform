"""Custom exceptions for ingestion workflows."""

from __future__ import annotations


class IngestionError(Exception):
    """Base exception for ingestion subsystem."""


class SourceLoadError(IngestionError):
    """Raised when a source cannot be loaded safely."""


class ProcessorError(IngestionError):
    """Raised when a processor stage fails."""


class IndexerError(IngestionError):
    """Raised when an indexing stage fails."""


class IngestionValidationError(IngestionError):
    """Raised when ingestion input validation fails."""
