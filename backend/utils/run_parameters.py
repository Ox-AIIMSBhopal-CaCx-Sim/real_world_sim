"""Serialize simulation parameters to CSV for experiment reproducibility."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Union

import pandas as pd

PathLike = Union[str, Path]


def _stringify_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    return json.dumps(value, ensure_ascii=True)


def flatten_parameters(
    params: Mapping[str, Any],
    *,
    parent_key: str = "",
) -> List[Dict[str, str]]:
    """Flatten nested parameter dicts into dot-path rows."""
    rows: List[Dict[str, str]] = []
    for key, value in params.items():
        full_key = f"{parent_key}.{key}" if parent_key else str(key)
        if isinstance(value, Mapping):
            rows.extend(flatten_parameters(value, parent_key=full_key))
        else:
            rows.append({"parameter": full_key, "value": _stringify_value(value)})
    return rows


def parameters_to_dataframe(
    params: Mapping[str, Any],
    *,
    run_metadata: Mapping[str, Any] | None = None,
) -> pd.DataFrame:
    """
    Build a two-column parameter table.

    ``run_metadata`` entries (e.g. run_timestamp, seed) are prepended as rows.
    """
    rows: List[Dict[str, str]] = []
    if run_metadata:
        for key, value in run_metadata.items():
            rows.append({"parameter": str(key), "value": _stringify_value(value)})
        rows.append({"parameter": "---", "value": "---"})

    rows.extend(flatten_parameters(params))
    return pd.DataFrame(rows, columns=["parameter", "value"])


def save_run_parameters_csv(
    params: Mapping[str, Any],
    output_path: PathLike,
    *,
    run_metadata: Mapping[str, Any] | None = None,
) -> Path:
    """Write flattened parameters to ``output_path``."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = parameters_to_dataframe(params, run_metadata=run_metadata)
    df.to_csv(output_path, index=False)
    return output_path
