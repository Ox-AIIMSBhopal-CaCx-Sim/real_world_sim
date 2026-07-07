"""
Run the cytopathology simulation multiple times and record summary statistics only.

Each replication reloads a fresh copy of ``v4.0_cytosim`` (no per-run CSV folders).
After every run, waiting-time ``.describe()`` stats and resource utilisation
percentages are appended to a single summary CSV.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from utils.analysis import calc_res_util_pct, list_processes, load_waiting_times

_ROOT = Path(__file__).resolve().parent
_CYTO_PATH = _ROOT / "v4.0_cytosim.py"
_OUTPUT_DIR = _ROOT / "sim_results"

NUM_RUNS = 50
BASE_SEED = 42


def _load_cyto_module(module_name: str):
    """Load a fresh cytopathology simulation module (isolated global state)."""
    spec = importlib.util.spec_from_file_location(module_name, _CYTO_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {_CYTO_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _waiting_time_summary_rows(
    *,
    run_index: int,
    seed: int,
    df: pd.DataFrame,
    dataset: str,
    group_col: str | None = "Type",
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if df.empty:
        return rows

    if group_col and group_col in df.columns:
        groups = [(str(name), group_df) for name, group_df in df.groupby(group_col, dropna=False)]
    else:
        groups = [("all", df)]

    for group_name, group_df in groups:
        wait_df = load_waiting_times(df=group_df)
        for process in list_processes(wait_df):
            series = wait_df[f"waiting_for_{process}_days"]
            for stat_name, value in series.describe().items():
                rows.append(
                    {
                        "run_index": run_index,
                        "seed": seed,
                        "summary_type": "waiting_time",
                        "dataset": dataset,
                        "group": group_name,
                        "process": process,
                        "resource": "",
                        "statistic": stat_name,
                        "value": value,
                    }
                )
    return rows


def _resource_util_summary_rows(
    *,
    run_index: int,
    seed: int,
    busy_df: pd.DataFrame,
    metadata_df: pd.DataFrame,
) -> List[Dict[str, Any]]:
    util_df = calc_res_util_pct(busy_df, metadata_df)
    return [
        {
            "run_index": run_index,
            "seed": seed,
            "summary_type": "resource_utilisation",
            "dataset": "",
            "group": "",
            "process": "",
            "resource": row["utilisation_key"],
            "statistic": "utilisation_pct",
            "value": row["utilisation_pct"],
        }
        for _, row in util_df.iterrows()
    ]


def extract_run_summary(
    *,
    run_index: int,
    seed: int,
    frames: Dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Build long-format summary rows for one simulation replication."""
    rows: List[Dict[str, Any]] = []
    rows.extend(
        _waiting_time_summary_rows(
            run_index=run_index,
            seed=seed,
            df=frames["patient_timestamps"],
            dataset="patient",
            group_col="Type",
        )
    )
    rows.extend(
        _waiting_time_summary_rows(
            run_index=run_index,
            seed=seed,
            df=frames["slide_timestamps"],
            dataset="slide",
            group_col=None,
        )
    )
    rows.extend(
        _resource_util_summary_rows(
            run_index=run_index,
            seed=seed,
            busy_df=frames["resource_busy_intervals"],
            metadata_df=frames["resource_metadata"],
        )
    )
    return pd.DataFrame(rows)


def run_multi_cyto_simulation(
    *,
    num_runs: int = NUM_RUNS,
    base_seed: int = BASE_SEED,
    output_dir: Path | str | None = None,
) -> Path:
    """Run cytopathology sim ``num_runs`` times and write one summary CSV."""
    output_dir = Path(output_dir or _OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    batch_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_path = output_dir / f"{batch_timestamp}_cyto_multi_run_summary.csv"

    print(f"Running {num_runs} cytopathology replications → '{summary_path}'")

    for run_index in range(num_runs):
        seed = base_seed + run_index
        module_name = f"v4_cytosim_run_{run_index}"
        if module_name in sys.modules:
            del sys.modules[module_name]

        print(f"\n=== Run {run_index + 1}/{num_runs} (seed={seed}) ===")
        cyto = _load_cyto_module(module_name)
        cyto.np.random.seed(seed)
        cyto.run_simulation()
        frames = cyto.collect_result_dataframes()
        run_summary = extract_run_summary(run_index=run_index, seed=seed, frames=frames)

        write_header = not summary_path.exists()
        run_summary.to_csv(summary_path, mode="a", index=False, header=write_header)
        print(f"  Appended {len(run_summary)} summary rows")

        del sys.modules[module_name]

    print(f"\nMulti-run summary saved to '{summary_path}'")
    return summary_path


if __name__ == "__main__":
    run_multi_cyto_simulation()
