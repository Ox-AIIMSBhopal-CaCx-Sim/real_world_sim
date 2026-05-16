"""Load cyto parameter JSON (shared ground truth)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
SHARED_DEFAULT_JSON = _REPO_ROOT / "shared" / "cyto_parameters.default.json"


def load_default_cyto_parameters() -> dict[str, Any]:
    """Load the canonical default parameter JSON."""
    if not SHARED_DEFAULT_JSON.is_file():
        raise FileNotFoundError(f"Default parameters not found: {SHARED_DEFAULT_JSON}")
    with SHARED_DEFAULT_JSON.open(encoding="utf-8") as f:
        return json.load(f)


def merge_parameters(overrides: dict[str, Any] | None) -> dict[str, Any]:
    """Deep-merge overrides onto defaults (overrides win)."""
    base = load_default_cyto_parameters()
    if not overrides:
        return base
    return _deep_merge(base, overrides)


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in overrides.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
