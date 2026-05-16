"""Read/write per-run CSV and other output files."""

from pathlib import Path

import pandas as pd

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = _BACKEND_ROOT / "runs"


class ArtifactStore:
    """Filesystem-backed store for simulation run outputs."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or RUNS_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def ensure_run_dir(self, run_id: str) -> Path:
        run_dir = self.base_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def write_csv(self, run_dir: Path, filename: str, df: pd.DataFrame) -> Path:
        path = run_dir / filename
        df.to_csv(path, index=False)
        return path

    def resolve(self, run_id: str, filename: str) -> Path | None:
        path = self.base_dir / run_id / filename
        return path if path.exists() else None

    def artifact_url(self, run_id: str, filename: str) -> str:
        return f"/api/simulations/{run_id}/artifacts/{filename}"
