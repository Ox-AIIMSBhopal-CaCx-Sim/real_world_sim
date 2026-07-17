"""Orchestrate simulation runs and artifact upload."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.schemas.parameters import SimulationKind
from app.schemas.results import ArtifactUrls, SimulationRunResult
from app.services.storage import ArtifactStore, get_artifact_store
from app.services.users import user_exists, validate_username
from models.cyto import run_cyto
from models.histo import run_histo

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_OUTPUT = _BACKEND_ROOT / "sim_results"


class SimulationRunner:
    """Validate-ready parameters → DES model → GCS artifact URLs."""

    def __init__(self, store: ArtifactStore | None = None) -> None:
        self._store = store or get_artifact_store()
        self._output_root = Path(os.getenv("SIM_OUTPUT_ROOT", str(_DEFAULT_OUTPUT)))

    def run(
        self,
        kind: SimulationKind,
        parameters: dict[str, Any],
        *,
        username: str,
        seed: int | None = 42,
    ) -> SimulationRunResult:
        username = validate_username(username)
        if not user_exists(username):
            raise ValueError(f"Unknown username: {username}. Register or log in first.")

        user_root = self._output_root / username
        user_root.mkdir(parents=True, exist_ok=True)

        if kind == "cyto":
            result = run_cyto(
                parameters,
                output_root=user_root,
                seed=seed,
                run_analysis=True,
                quiet=True,
            )
        elif kind == "histo":
            result = run_histo(
                parameters,
                output_root=user_root,
                seed=seed,
                run_analysis=True,
                quiet=True,
            )
        else:
            raise ValueError(f"Unknown simulation kind: {kind}")

        run_id = str(result["run_id"])
        run_dir = Path(result["run_dir"])
        artifact_urls = self._store.upload_run(run_id, run_dir, username=username)

        return SimulationRunResult(
            run_id=run_id,
            lab=kind,
            status="completed",
            seed=seed,
            project_title=parameters.get("project_title"),
            artifacts=ArtifactUrls(**artifact_urls),
            local_run_dir=str(run_dir.resolve()),
        )

    def get_run(self, run_id: str, *, username: str) -> SimulationRunResult | None:
        username = validate_username(username)
        index = self._store.get_run_index(run_id, username=username)
        if index is None:
            local = self._output_root / username / run_id / "artifact_index.json"
            if not local.is_file():
                return None
            index = json.loads(local.read_text(encoding="utf-8"))

        lab: SimulationKind = "histo" if run_id.endswith("_histo") else "cyto"
        artifacts = index.get("artifacts") or {}
        return SimulationRunResult(
            run_id=run_id,
            lab=lab,
            status="completed",
            artifacts=ArtifactUrls(
                data=artifacts.get("data", {}),
                tables=artifacts.get("tables", {}),
                plots=artifacts.get("plots", {}),
            ),
        )
