"""Aggregate KPIs from simulation trace DataFrames."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd

from app.schemas.results import (
    PatientTypeBreakdown,
    ProcessMetric,
    RunArtifacts,
    SimulationRunResult,
    SummaryMetric,
    TurnaroundBucket,
)


def _tat_days(patient_df: pd.DataFrame) -> pd.Series:
    df = patient_df.copy()
    df["Arrival"] = pd.to_datetime(df["Arrival"])
    df["Reporting End"] = pd.to_datetime(df["Reporting End"], errors="coerce")
    completed = df[df["Completed"] == "Yes"].dropna(subset=["Reporting End"])
    if completed.empty:
        return pd.Series(dtype=float)
    delta = completed["Reporting End"] - completed["Arrival"]
    return delta.dt.total_seconds() / (24 * 3600)


def _histogram_buckets(tat_days: pd.Series) -> list[TurnaroundBucket]:
    if tat_days.empty:
        return [
            TurnaroundBucket(range="0–2d", count=0),
            TurnaroundBucket(range="2–5d", count=0),
            TurnaroundBucket(range="5–10d", count=0),
            TurnaroundBucket(range="10–20d", count=0),
            TurnaroundBucket(range=">20d", count=0),
        ]
    bins = [0, 2, 5, 10, 20, np.inf]
    labels = ["0–2d", "2–5d", "5–10d", "10–20d", ">20d"]
    counts = pd.cut(tat_days, bins=bins, labels=labels, right=False).value_counts()
    return [TurnaroundBucket(range=label, count=int(counts.get(label, 0))) for label in labels]


def _process_metrics_from_columns(
    df: pd.DataFrame,
    specs: list[tuple[str, str]],
) -> list[ProcessMetric]:
    metrics: list[ProcessMetric] = []
    for process_name, col in specs:
        if col not in df.columns:
            continue
        waits = df[col].dropna()
        if waits.empty:
            continue
        metrics.append(
            ProcessMetric(
                process=process_name,
                median_wait_min=float(waits.median()),
                p90_wait_min=float(waits.quantile(0.9)),
                n=int(len(waits)),
            )
        )
    return metrics


class KPIAggregator:
    """Compute dashboard metrics from patient/slide timestamp tables."""

    def build_result(
        self,
        run_id: str,
        patient_df: pd.DataFrame,
        slide_df: pd.DataFrame,
        *,
        project_title: str,
        run_time_days: int,
        artifact_urls: dict[str, str],
    ) -> SimulationRunResult:
        tat = _tat_days(patient_df)
        n_patients = len(patient_df)
        n_slides = len(slide_df)
        n_completed = int((patient_df["Completed"] == "Yes").sum()) if n_patients else 0

        median_tat = float(tat.median()) if not tat.empty else 0.0
        p90_tat = float(tat.quantile(0.9)) if not tat.empty else 0.0

        type_labels = {
            "pap_smear": "Pap smear",
            "non_pap_smear": "Non-Pap",
        }
        breakdown: list[PatientTypeBreakdown] = []
        for entity_type, label in type_labels.items():
            subset = patient_df[patient_df["Type"] == entity_type]
            if subset.empty:
                continue
            sub_tat = _tat_days(subset)
            breakdown.append(
                PatientTypeBreakdown(
                    type=label,
                    count=len(subset),
                    medianTatDays=float(sub_tat.median()) if not sub_tat.empty else 0.0,
                )
            )

        process_metrics = _process_metrics_from_columns(
            patient_df,
            [("Reporting", "Reporting Wait (min)")],
        )
        process_metrics.extend(
            _process_metrics_from_columns(
                slide_df,
                [
                    ("Fixation", "Fixation Wait (min)"),
                    ("Manual staining", "Staining Wait (min)"),
                ],
            )
        )

        summary = (
            f"{project_title}: {n_completed} of {n_patients} patients completed reporting "
            f"over {run_time_days} simulated days ({n_slides} slides after warm-up)."
        )

        return SimulationRunResult(
            runId=run_id,
            completedAt=datetime.now(timezone.utc).isoformat(),
            summary=summary,
            metrics=[
                SummaryMetric(label="Patients (post warm-up)", value=str(n_patients)),
                SummaryMetric(
                    label="Completed reporting",
                    value=str(n_completed),
                    detail=f"{100 * n_completed / n_patients:.1f}%"
                    if n_patients
                    else None,
                ),
                SummaryMetric(label="Slides (post warm-up)", value=str(n_slides)),
                SummaryMetric(
                    label="Median turnaround",
                    value=f"{median_tat:.1f} days",
                    detail="Reporting end − arrival",
                ),
                SummaryMetric(label="90th percentile TAT", value=f"{p90_tat:.1f} days"),
            ],
            turnaroundHistogram=_histogram_buckets(tat),
            patientBreakdown=breakdown,
            processMetrics=process_metrics or None,
            artifacts=RunArtifacts(
                patientCsv=artifact_urls["patient_timestamps.csv"],
                slideCsv=artifact_urls["slide_timestamps.csv"],
            ),
            notes=[
                f"Warm-up period excluded from exported patients/slides (first period of run).",
                "Turnaround = Reporting End − Arrival for completed patients.",
            ],
        )
