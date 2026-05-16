"""Histopathology discrete-event model.

TODO: Extract build + run logic from backend/v1_histosim.py into this module.
"""

from typing import Any

import pandas as pd


def run_histo_simulation(
    parameters: dict[str, Any],
    *,
    seed: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Run one histopathology replication.

    Returns:
        (patient_timestamps_df, slide_timestamps_df)
    """
    raise NotImplementedError(
        "Histo model not yet extracted from v1_histosim.py — implement in a follow-up step."
    )
