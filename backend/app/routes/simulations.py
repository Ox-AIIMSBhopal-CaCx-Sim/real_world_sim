"""Simulation run and artifact endpoints."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.schemas.parameters import SimulationRunRequest
from app.schemas.results import SimulationRunResult
from app.services.kpi import KPIAggregator
from app.services.runner import SimulationRunner
from app.storage.artifacts import ArtifactStore

router = APIRouter()
_runner = SimulationRunner()
_kpi = KPIAggregator()
_store = ArtifactStore()


@router.post("/run", response_model=SimulationRunResult)
def run_simulation(request: SimulationRunRequest) -> SimulationRunResult:
    """Run a single cytopathology replication and return aggregated KPIs."""
    if request.kind != "cyto":
        raise HTTPException(
            status_code=400,
            detail="Only cytopathology (kind='cyto') is implemented.",
        )

    try:
        output = _runner.run(
            request.kind,
            request.parameters,
            seed=request.seed,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    artifact_urls = {
        "patient_timestamps.csv": _store.artifact_url(
            output.run_id, "patient_timestamps.csv"
        ),
        "slide_timestamps.csv": _store.artifact_url(
            output.run_id, "slide_timestamps.csv"
        ),
    }

    return _kpi.build_result(
        output.run_id,
        output.patient_df,
        output.slide_df,
        project_title=request.parameters.project_title,
        run_time_days=request.parameters.simulation.run_time,
        artifact_urls=artifact_urls,
    )


@router.get("/{run_id}/artifacts/{filename}")
def get_artifact(run_id: str, filename: str) -> FileResponse:
    """Download a per-run CSV or other artifact."""
    path = _store.resolve(run_id, filename)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(path, filename=filename)
