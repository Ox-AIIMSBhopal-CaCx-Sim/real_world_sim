"""Orchestrates model execution and artifact persistence."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd

from app.schemas.parameters import CytoParameters, HistoParameters, SimulationKind
from app.storage.artifacts import ArtifactStore
from models.cyto import run_cyto_simulation
from models.histo import run_histo_simulation


@dataclass
class SimulationRunOutput:
    run_id: str
    kind: SimulationKind
    patient_df: pd.DataFrame
    slide_df: pd.DataFrame
    artifact_dir: Path


class SimulationRunner:
    """Build and run DES models; write per-run CSV traces."""

    def __init__(self, store: ArtifactStore | None = None) -> None:
        self._store = store or ArtifactStore()

    def run(
        self,
        kind: SimulationKind,
        parameters: CytoParameters | HistoParameters | dict[str, Any],
        *,
        seed: int | None = None,
    ) -> SimulationRunOutput:
        """Execute one replication and persist trace CSVs."""
        if isinstance(parameters, (CytoParameters, HistoParameters)):
            params_dict = parameters.to_sim_dict()
        else:
            params_dict = parameters

        run_id = str(uuid4())
        artifact_dir = self._store.ensure_run_dir(run_id)

        if kind == "cyto":
            patient_df, slide_df = run_cyto_simulation(params_dict, seed=seed)
        elif kind == "histo":
            patient_df, slide_df = run_histo_simulation(params_dict, seed=seed)
        else:
            raise ValueError(f"Unknown simulation kind: {kind}")

        self._store.write_csv(artifact_dir, "patient_timestamps.csv", patient_df)
        self._store.write_csv(artifact_dir, "slide_timestamps.csv", slide_df)

        return SimulationRunOutput(
            run_id=run_id,
            kind=kind,
            patient_df=patient_df,
            slide_df=slide_df,
            artifact_dir=artifact_dir,
        )
