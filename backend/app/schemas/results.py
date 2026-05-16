"""API response models aligned with frontend SimulationRunResult."""

from pydantic import BaseModel, Field


class SummaryMetric(BaseModel):
    label: str
    value: str
    detail: str | None = None


class TurnaroundBucket(BaseModel):
    range: str
    count: int


class PatientTypeBreakdown(BaseModel):
    type: str
    count: int
    median_tat_days: float = Field(alias="medianTatDays")

    model_config = {"populate_by_name": True}


class ProcessMetric(BaseModel):
    process: str
    median_wait_min: float
    p90_wait_min: float
    n: int


class RunArtifacts(BaseModel):
    patient_csv: str = Field(alias="patientCsv")
    slide_csv: str = Field(alias="slideCsv")

    model_config = {"populate_by_name": True}


class SimulationRunResult(BaseModel):
    run_id: str = Field(alias="runId")
    completed_at: str = Field(alias="completedAt")
    summary: str
    metrics: list[SummaryMetric]
    turnaround_histogram: list[TurnaroundBucket] = Field(alias="turnaroundHistogram")
    patient_breakdown: list[PatientTypeBreakdown] = Field(alias="patientBreakdown")
    process_metrics: list[ProcessMetric] | None = Field(default=None, alias="processMetrics")
    artifacts: RunArtifacts | None = None
    notes: list[str]

    model_config = {"populate_by_name": True}
