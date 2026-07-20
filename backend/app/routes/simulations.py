"""Simulation run and lookup endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.schemas.parameters import SimulationRunRequest
from app.schemas.results import SimulationRunResult
from app.services.runner import SimulationRunner
from app.services.users import validate_username

router = APIRouter()
_runner = SimulationRunner()


@router.post("/run", response_model=SimulationRunResult)
def run_simulation(request: SimulationRunRequest) -> SimulationRunResult:
    """Run one simulation replication, upload artifacts, return URL map."""
    try:
        username = validate_username(request.username)
        return _runner.run(
            request.kind,
            request.parameters,
            username=username,
            seed=request.seed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — surface sim failures to the client
        raise HTTPException(status_code=500, detail=f"Simulation failed: {exc}") from exc


@router.get("/{run_id}/artifacts/{artifact_path:path}")
def get_artifact(
    run_id: str,
    artifact_path: str,
    username: str = Query(..., min_length=3, max_length=32),
) -> Response:
    """Stream a run artifact via the API (avoids private-bucket CORS)."""
    try:
        username = validate_username(username)
        data, content_type = _runner.read_artifact(
            run_id, artifact_path, username=username
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Artifact fetch failed: {exc}") from exc

    return Response(
        content=data,
        media_type=content_type,
        headers={"Cache-Control": "private, max-age=3600"},
    )


@router.get("/{run_id}", response_model=SimulationRunResult)
def get_simulation(
    run_id: str,
    username: str = Query(..., min_length=3, max_length=32),
) -> SimulationRunResult:
    """Re-fetch artifact URLs for a previous run under a username."""
    try:
        username = validate_username(username)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result = _runner.get_run(run_id, username=username)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return result
