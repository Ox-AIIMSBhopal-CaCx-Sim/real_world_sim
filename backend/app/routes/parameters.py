"""Parameter preset endpoints."""

from typing import Any

from fastapi import APIRouter

from parameters.loader import load_default_cyto_parameters

router = APIRouter()


@router.get("/cyto/default")
def get_default_cyto_parameters() -> dict[str, Any]:
    """Return the canonical default cytopathology parameter JSON."""
    return load_default_cyto_parameters()
