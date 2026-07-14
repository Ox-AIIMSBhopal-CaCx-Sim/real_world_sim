"""Simulation run and lookup endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.parameters import SimulationRunRequest
from app.schemas.results import SimulationRunResult
from app.services.runner import SimulationRunner

router = APIRouter()
_runner = SimulationRunner()


@router.post("/run", response_model=SimulationRunResult)
def run_simulation(request: SimulationRunRequest) -> SimulationRunResult:
    """Run one simulation replication, upload artifacts, return URL map."""
    try:
        return _runner.run(request.kind, request.parameters, seed=request.seed)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — surface sim failures to the client
        raise HTTPException(status_code=500, detail=f"Simulation failed: {exc}") from exc


@router.get("/{run_id}", response_model=SimulationRunResult)
def get_simulation(run_id: str) -> SimulationRunResult:
    """Re-fetch artifact URLs for a previous run."""
    result = _runner.get_run(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return result
