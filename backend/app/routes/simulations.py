"""Simulation run and lookup endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

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
