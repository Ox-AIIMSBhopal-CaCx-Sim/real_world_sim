"""Parameter schemas — mirrors shared/cyto_parameters.default.json."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class DistributionParams(BaseModel):
    distribution: str
    params: list[float] | float

    model_config = {"extra": "allow"}


class PapPerDayParams(DistributionParams):
    slide_pt_ratio: int = 1


class TriangularParams(BaseModel):
    distribution: Literal["triangular"] = "triangular"
    params: list[float]


class SimulationMeta(BaseModel):
    name: str
    run_time: int = Field(description="Simulation horizon in days")
    experiment_no: int = 1
    no_of_sims: int = 1
    warmup_days: int = 30
    working_days: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6])
    working_hours: list[int] = Field(default_factory=lambda: [9, 17])

    model_config = {"extra": "allow"}


class CaseComplexity(BaseModel):
    p_high: float


class SlideRatioByComplexity(BaseModel):
    high: int
    low: int


class ScheduleSlot(BaseModel):
    days: list[int]
    hours: list[int]


class CytoTechnicians(BaseModel):
    num_cytotech: int
    cytotech_schedule: dict[str, ScheduleSlot]


class CytoPathologists(BaseModel):
    num_cytopath: int
    cytopath_schedule: dict[str, ScheduleSlot]


class CytoManualStainingStation(BaseModel):
    num_stations: int
    batch_size: int


class CytoStainingKits(BaseModel):
    num_kits: int
    stain_per_kit: float
    reagent_per_slide: float


class ReportingByComplexity(BaseModel):
    high: TriangularParams
    low: TriangularParams


class CytoReportingTime(BaseModel):
    by_case_complexity: ReportingByComplexity


class CytoParameters(BaseModel):
    """Full cytopathology parameter set (JSON ground truth)."""

    project_title: str
    simulation: SimulationMeta
    pap_per_day: PapPerDayParams
    non_pap_per_day: DistributionParams
    case_complexity: CaseComplexity
    slide_pt_ratio_by_case_complexity: SlideRatioByComplexity
    cyto_fixation_time: DistributionParams
    cyto_staining_time: DistributionParams
    cyto_reporting_time: CytoReportingTime
    cyto_technicians: CytoTechnicians
    cyto_pathologists: CytoPathologists
    cyto_manual_staining_station: CytoManualStainingStation
    cyto_staining_kits: CytoStainingKits

    def to_sim_dict(self) -> dict[str, Any]:
        """Dict passed to models.cyto.run_cyto_simulation."""
        return self.model_dump(mode="python")


SimulationKind = Literal["cyto", "histo"]


class SimulationRunRequest(BaseModel):
    kind: SimulationKind
    parameters: CytoParameters
    seed: int | None = Field(default=None, description="Optional RNG seed")
