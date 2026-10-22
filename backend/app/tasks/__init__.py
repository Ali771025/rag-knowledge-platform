"""Celery task package namespace.

Phase 1 scaffolding keeps this package lightweight and side-effect free.
Individual task modules can be imported by workers when those modules are
implemented.
"""

__all__: list[str] = []
