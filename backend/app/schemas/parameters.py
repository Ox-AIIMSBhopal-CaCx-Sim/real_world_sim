"""Parameter schemas mirroring shared/*.default.json (current YAML shape)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


SimulationKind = Literal["cyto", "histo"]


class FlexibleModel(BaseModel):
    """Base that allows forward-compatible extra keys from YAML/JSON."""

    model_config = {"extra": "allow"}


class DistributionParams(FlexibleModel):
    distribution: str
    params: list[float] | float


class SimulationMeta(FlexibleModel):
    name: str
    duration_months: int = Field(ge=1, le=60)
    warmup_months: int = Field(ge=0, le=24, default=1)
    experiment_no: int = 1
    no_of_sims: int = 1


class CaseComplexity(FlexibleModel):
    p_high: float = Field(ge=0.0, le=1.0)


class ScheduleSlot(FlexibleModel):
    days: list[int]
    hours: list[int]


class Disruption(FlexibleModel):
    id: str
    resource: str
    duration_days: float | int
    effective_capacity: float | int = 0
    start_day: int | None = None
    start_datetime: str | None = None


class PapPerDay(DistributionParams):
    slide_pt_ratio: int = 1


class CytoTechnicians(FlexibleModel):
    num_cytotech: int
    cytotech_schedule: dict[str, ScheduleSlot]


class JuniorPathologistCyto(FlexibleModel):
    num_junior_pathologist: int
    junior_pathologist_schedule: dict[str, ScheduleSlot]


class SeniorPathologists(FlexibleModel):
    num_senior_pathologist: int
    repeat_stain_rate: float = 0.05
    senior_pathologist_schedule: dict[str, ScheduleSlot]


class CytoManualStainingStation(FlexibleModel):
    num_stations: int = 1
    batch_size: int = 5
    error_rate: float = 0.01
    reagent_per_slide: float | int | None = None


class StainingKits(FlexibleModel):
    num_kits: int
    stain_per_kit: float | int
    reagent_per_slide: float = 0.1


class CytoParameters(FlexibleModel):
    project_title: str
    simulation: SimulationMeta
    pap_per_day: PapPerDay
    non_pap_per_day: DistributionParams
    case_complexity: CaseComplexity
    slide_pt_ratio_by_case_complexity: dict[str, int]
    cyto_fixation_time: dict[str, Any]
    cyto_staining_time: dict[str, Any]
    cyto_slide_screening_time: dict[str, Any]
    cyto_reporting_time: dict[str, Any]
    cyto_technicians: CytoTechnicians
    junior_pathologist: JuniorPathologistCyto
    senior_pathologists: SeniorPathologists
    cyto_manual_staining_station: CytoManualStainingStation
    repeat_staining: dict[str, Any]
    cyto_staining_kits: StainingKits
    disruptions: list[Disruption] = Field(default_factory=list)


class BiopsySizeWeights(FlexibleModel):
    weights: dict[str, float]


class HistoTechnicians(FlexibleModel):
    num_cytotech: int
    histotech_schedule: dict[str, ScheduleSlot]


class JuniorPathologistHisto(FlexibleModel):
    num_junior_pathologist: int
    grossing_cutoff_policy: str | None = None
    task_windows: dict[str, Any] | None = None
    junior_pathologist_schedule: dict[str, ScheduleSlot] | None = None


class StationConfig(FlexibleModel):
    num_stations: int = 1
    batch_size: int = 1


class HistoParameters(FlexibleModel):
    project_title: str
    simulation: SimulationMeta
    cervical_biopsies_per_day: DistributionParams
    other_biopsies_per_day: DistributionParams
    case_complexity: CaseComplexity
    slide_pt_ratio_by_biopsy_size: dict[str, int]
    biopsy_size: BiopsySizeWeights | dict[str, Any]
    histo_fixation_time: dict[str, Any]
    histo_grossing_time: dict[str, Any]
    histo_tissue_processing_time: dict[str, Any]
    histo_embedding_time: dict[str, Any]
    histo_sectioning_time: dict[str, Any]
    histo_staining_time: dict[str, Any]
    histo_slide_screening_time: dict[str, Any]
    histo_reporting_time: dict[str, Any]
    histo_technicians: HistoTechnicians
    junior_pathologist: JuniorPathologistHisto
    senior_pathologists: SeniorPathologists
    histo_grossing_station: StationConfig
    histo_tissue_processor: StationConfig
    histo_embedding_station: StationConfig
    histo_sectioning_station: StationConfig
    histo_staining_station: StationConfig
    repeat_staining: dict[str, Any]
    histo_staining_kits: StainingKits
    disruptions: list[Disruption] = Field(default_factory=list)


class SimulationRunRequest(BaseModel):
    kind: SimulationKind
    parameters: dict[str, Any]
    seed: int | None = 42
    username: str = Field(min_length=3, max_length=32)

    @model_validator(mode="after")
    def validate_parameters_for_kind(self) -> "SimulationRunRequest":
        if self.kind == "cyto":
            CytoParameters.model_validate(self.parameters)
        else:
            HistoParameters.model_validate(self.parameters)
        return self

    def parsed_parameters(self) -> CytoParameters | HistoParameters:
        if self.kind == "cyto":
            return CytoParameters.model_validate(self.parameters)
        return HistoParameters.model_validate(self.parameters)
