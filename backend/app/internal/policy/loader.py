"""Config loader for persona and conversion policy files."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any

from app.internal.policy.config_models import PersonaConversionPolicyConfig

_DEFAULT_CONFIG_PATH = Path(__file__).with_name("defaults.json")


class PolicyConfigError(RuntimeError):
    """Raised when policy configuration cannot be loaded."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PolicyConfigError(f"Unable to read policy config file: {path}") from exc

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PolicyConfigError(f"Invalid JSON in policy config file: {path}") from exc

    if not isinstance(parsed, dict):
        raise PolicyConfigError("Policy config root must be a JSON object.")

    return parsed


def load_policy_config(path: str | Path | None = None) -> PersonaConversionPolicyConfig:
    """Load and validate persona/conversion policy configuration from JSON."""

    config_path = Path(path) if path is not None else _DEFAULT_CONFIG_PATH
    payload = _read_json(config_path)

    try:
        return PersonaConversionPolicyConfig.model_validate(payload)
    except Exception as exc:  # pragma: no cover - pydantic error details are surfaced by tests
        raise PolicyConfigError(f"Policy config validation failed for {config_path}") from exc


@lru_cache(maxsize=1)
def load_default_policy_config() -> PersonaConversionPolicyConfig:
    """Load and memoize the default policy configuration."""

    return load_policy_config(_DEFAULT_CONFIG_PATH)
