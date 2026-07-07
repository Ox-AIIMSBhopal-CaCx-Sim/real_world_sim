"""
Integrated cytopathology → histopathology simulation.

Phase 1: Run cytosim and count daily pap smear arrivals.
Phase 2: Apply pap-smear positivity (default 10%) and schedule cervical biopsies
         for the following simulation day in histosim.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Dict

import numpy as np

import integrated_config

_ROOT = Path(__file__).resolve().parent
_SIM_RESULTS_DIR = _ROOT / "sim_results"


def _load_module(module_name: str, file_path: Path):
    """Load a script module whose filename is not a valid Python identifier."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def build_cervical_schedule_from_pap_counts(
    daily_pap_counts: Dict[int, int],
    positivity_rate: float,
    *,
    seed: int = 42,
) -> Dict[int, int]:
    """
    Convert daily pap-smear counts into next-day cervical biopsy demand.

    Each pap smear on day D has ``positivity_rate`` probability of being positive;
    the number of positives becomes the biopsy count on day D + 1.
    """
    rng = np.random.default_rng(seed)
    cervical_schedule: Dict[int, int] = {}

    for day, pap_count in sorted(daily_pap_counts.items()):
        positives = sum(1 for _ in range(pap_count) if rng.random() < positivity_rate)
        if positives > 0:
            cervical_schedule[day + 1] = cervical_schedule.get(day + 1, 0) + positives

    return cervical_schedule


def _print_schedule_summary(
    daily_pap_counts: Dict[int, int],
    cervical_schedule: Dict[int, int],
    positivity_rate: float,
) -> None:
    total_pap = sum(daily_pap_counts.values())
    total_biopsies = sum(cervical_schedule.values())
    print("=========================================")
    print("  INTEGRATED SIMULATION: CYTO → HISTO    ")
    print("=========================================")
    print(f"Pap smear positivity rate: {positivity_rate:.0%}")
    print(f"Total pap smears (cyto): {total_pap}")
    print(f"Total scheduled cervical biopsies (histo): {total_biopsies}")
    print(f"Effective positivity: {total_biopsies / total_pap:.1%}" if total_pap else "No pap smears")
    print("Sample daily linkage (pap day → biopsies next day):")
    for day in sorted(daily_pap_counts)[:5]:
        pap_count = daily_pap_counts[day]
        biopsy_count = cervical_schedule.get(day + 1, 0)
        print(f"  Day {day}: {pap_count} pap smears → Day {day + 1}: {biopsy_count} biopsies")
    print("=========================================\n")


def run_integrated_simulation(
    *,
    positivity_rate: float | None = None,
    seed: int = 42,
) -> None:
    """Run cytosim first, then histosim with cyto-driven cervical biopsy demand."""
    np.random.seed(seed)
    rate = positivity_rate if positivity_rate is not None else integrated_config.PAP_POSITIVITY_RATE

    print("=== Phase 1: Cytopathology simulation ===\n")
    cyto = _load_module("v4_cytosim", _ROOT / "v4.0_cytosim.py")
    cyto.run_simulation()

    daily_pap_counts = cyto.count_daily_pap_arrivals()
    cervical_schedule = build_cervical_schedule_from_pap_counts(
        daily_pap_counts,
        rate,
        seed=seed,
    )
    _print_schedule_summary(daily_pap_counts, cervical_schedule, rate)

    integrated_config.cervical_daily_schedule = cervical_schedule

    print("=== Phase 2: Histopathology simulation ===\n")
    histo = _load_module("v2_histosim", _ROOT / "v2_histosim.py")
    histo.run_simulation()

    cyto.collect_and_save_results(tags="integrated")
    histo.collect_and_save_results(tags="integrated")

    _save_schedule_csv(daily_pap_counts, cervical_schedule, rate)


def _save_schedule_csv(
    daily_pap_counts: Dict[int, int],
    cervical_schedule: Dict[int, int],
    positivity_rate: float,
) -> None:
    import pandas as pd

    rows = []
    all_days = sorted(set(daily_pap_counts) | {d - 1 for d in cervical_schedule})
    for day in all_days:
        rows.append({
            "Simulation day": day,
            "Pap smears": daily_pap_counts.get(day, 0),
            "Cervical biopsies (next day)": cervical_schedule.get(day + 1, 0),
        })

    df = pd.DataFrame(rows)
    _SIM_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _SIM_RESULTS_DIR / "integrated_cyto_histo_schedule.csv"
    df.to_csv(out_path, index=False)
    print(f"\nCyto→histo daily schedule saved to '{out_path}'")


if __name__ == "__main__":
    run_integrated_simulation()
