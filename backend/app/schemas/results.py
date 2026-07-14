"""API response models for simulation runs and artifact URLs."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.parameters import SimulationKind


class ArtifactUrls(BaseModel):
    """HTTP URLs for data CSVs, analysis tables, and plot PNGs."""

    data: dict[str, str] = Field(default_factory=dict)
    tables: dict[str, str] = Field(default_factory=dict)
    plots: dict[str, str] = Field(default_factory=dict)


class SimulationRunResult(BaseModel):
    run_id: str
    lab: SimulationKind
    status: Literal["completed", "failed"] = "completed"
    seed: int | None = None
    project_title: str | None = None
    artifacts: ArtifactUrls
    local_run_dir: str | None = None
    error: str | None = None


class RunIndexEntry(BaseModel):
    run_id: str
    lab: SimulationKind
    status: str
    created_at: str | None = None
    artifacts: ArtifactUrls | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
