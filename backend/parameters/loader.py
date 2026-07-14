"""Load cyto/histo parameter JSON (shared ground truth)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

_REPO_ROOT = Path(__file__).resolve().parents[2]
CYTO_DEFAULT_JSON = _REPO_ROOT / "shared" / "cyto_parameters.default.json"
HISTO_DEFAULT_JSON = _REPO_ROOT / "shared" / "histo_parameters.default.json"

LabKind = Literal["cyto", "histo"]


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Default parameters not found: {path}")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_default_cyto_parameters() -> dict[str, Any]:
    """Load the canonical default cytopathology parameter JSON."""
    return _load_json(CYTO_DEFAULT_JSON)


def load_default_histo_parameters() -> dict[str, Any]:
    """Load the canonical default histopathology parameter JSON."""
    return _load_json(HISTO_DEFAULT_JSON)


def load_default_parameters(kind: LabKind) -> dict[str, Any]:
    """Load default parameters for the given lab kind."""
    if kind == "cyto":
        return load_default_cyto_parameters()
    if kind == "histo":
        return load_default_histo_parameters()
    raise ValueError(f"Unknown lab kind: {kind}")


def merge_parameters(
    overrides: dict[str, Any] | None,
    *,
    kind: LabKind = "cyto",
) -> dict[str, Any]:
    """Deep-merge overrides onto defaults for the given lab (overrides win)."""
    base = load_default_parameters(kind)
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
