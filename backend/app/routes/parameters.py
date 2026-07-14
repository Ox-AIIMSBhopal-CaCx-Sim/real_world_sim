"""Parameter default endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.schemas.parameters import SimulationKind
from parameters.loader import load_default_parameters

router = APIRouter()


@router.get("/defaults/{kind}")
def get_defaults(kind: SimulationKind) -> dict[str, Any]:
    """Return shared default parameter JSON for the given lab."""
    try:
        return load_default_parameters(kind)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
