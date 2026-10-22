"""Centralized Guardrails configuration values.

Phase 1 intentionally keeps this module simple (module-level settings only)
until runtime config wiring is added in a later phase.
"""

from __future__ import annotations

RETRIEVAL_MIN_SCORE = 0.65
RETRIEVAL_TOP3_AVG_MIN_SCORE = 0.55

CONFIDENCE_MIN_SCORE = 0.60
CONFIDENCE_NORMAL_SCORE = 0.80
CONFIDENCE_REJECT_SCORE = 0.40

GROUNDING_MIN_SCORE = 0.70

ENABLE_OUTPUT_FILTERING = True
ENABLE_PROMPT_INJECTION_PROTECTION = True
ENABLE_GROUNDING_CHECK = True
ENABLE_DOMAIN_GUARD = True

MIN_RELEVANT_DOCS_EDUCATION = 2
MIN_RELEVANT_DOCS_INTRO = 1
