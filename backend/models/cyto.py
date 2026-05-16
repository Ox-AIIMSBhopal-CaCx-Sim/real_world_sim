"""Cytopathology discrete-event model (parameter-driven, JSON config)."""

from __future__ import annotations

import calendar
from datetime import datetime, time, timedelta
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import simpy

from utils.generic_entity import Generic_Entity
from utils.generic_generator import Entity_Generator
from utils.manual_generic_process import manual_generic_process
from utils.resource_availability import ScheduledResource, Schedule

SIMULATION_START_DATETIME = datetime(2026, 5, 1, 8, 0, 0)


def _add_months(dt: datetime, months: int) -> datetime:
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def _create_schedule_from_params(schedule_name: str, schedule_params: Dict[str, Any]) -> Schedule:
    schedule = Schedule(schedule_name)
    for _slot_name, slot_data in schedule_params.items():
        days = slot_data["days"]
        start_hour, end_hour = slot_data["hours"]
        schedule.add_time_slot(
            start_time=time(start_hour, 0),
            end_time=time(end_hour, 0),
            days_of_week=days,
        )
    return schedule


def _to_datetime_str(sim_start: datetime, sim_minutes: Any) -> str:
    if sim_minutes == "N/A" or (isinstance(sim_minutes, float) and np.isnan(sim_minutes)):
        return "N/A"
    dt = sim_start + timedelta(minutes=float(sim_minutes))
    return dt.strftime("%Y-%m-%d %H:%M")


def _wait_minutes(queue_entry: float | None, process_start: float | None) -> float | None:
    if queue_entry is None or process_start is None:
        return None
    return float(process_start) - float(queue_entry)


def run_cyto_simulation(
    parameters: dict[str, Any],
    *,
    seed: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Run one cytopathology replication.

    Args:
        parameters: Full cyto parameter object (same shape as shared/cyto_parameters.default.json).
        seed: Optional RNG seed for reproducibility.

    Returns:
        (patient_timestamps_df, slide_timestamps_df)
    """
    if seed is not None:
        np.random.seed(seed)

    params = parameters
    sim_meta = params.get("simulation", {})
    run_time_days = int(sim_meta.get("run_time", 365))
    warmup_days = int(sim_meta.get("warmup_days", 30))
    working_days = sim_meta.get("working_days", [0, 1, 2, 3, 4, 5, 6])
    working_hours = sim_meta.get("working_hours", [9, 17])

    pap_slide_ratio = params.get("pap_per_day", {}).get("slide_pt_ratio", 1)
    slide_pt_by_cc = params.get("slide_pt_ratio_by_case_complexity", {"high": 4, "low": 1})
    non_pap_slide_default = slide_pt_by_cc.get("low", 1)
    case_complexity_p_high = params.get("case_complexity", {}).get("p_high", 0.2)

    def sample_case_complexity() -> str:
        return "high" if np.random.random() < case_complexity_p_high else "low"

    def pap_patient_properties() -> Dict[str, Any]:
        cc = sample_case_complexity()
        return {"case_complexity": cc, "num_slides": pap_slide_ratio}

    def non_pap_patient_properties() -> Dict[str, Any]:
        cc = sample_case_complexity()
        return {
            "case_complexity": cc,
            "num_slides": int(slide_pt_by_cc.get(cc, non_pap_slide_default)),
        }

    sim_start = SIMULATION_START_DATETIME
    sim_end = sim_start + timedelta(days=run_time_days)
    warmup_end = sim_start + timedelta(days=warmup_days)
    sim_duration_min = int((sim_end - sim_start).total_seconds() / 60)
    warmup_duration_min = int((warmup_end - sim_start).total_seconds() / 60)

    env = simpy.Environment()

    # --- Entity classes (reset class-level registries each run) ---
    class PapSmearPatient(Generic_Entity):
        all_pap_smears: List["PapSmearPatient"] = []

        def __init__(
            self,
            id: int,
            arrival_time: float,
            num_slides: int = pap_slide_ratio,
            **properties: Any,
        ) -> None:
            pap_id = f"Pap-{id:06d}"
            super().__init__(
                id=pap_id,
                entity_type="pap_smear",
                arrival_time=arrival_time,
                **properties,
            )
            self.num_slides = num_slides
            self.slides_completed = 0
            self.entry_timestamp = sim_start + timedelta(minutes=arrival_time)
            self.entry_timestamp_datetime = self.entry_timestamp
            PapSmearPatient.all_pap_smears.append(self)

    class NotPapSmearPatient(Generic_Entity):
        all_non_pap_smears: List["NotPapSmearPatient"] = []

        def __init__(
            self,
            id: int,
            arrival_time: float,
            num_slides: int = non_pap_slide_default,
            **properties: Any,
        ) -> None:
            non_pap_id = f"NonPap-{id:06d}"
            super().__init__(
                id=non_pap_id,
                entity_type="non_pap_smear",
                arrival_time=arrival_time,
                **properties,
            )
            self.num_slides = num_slides
            self.slides_completed = 0
            self.entry_timestamp = sim_start + timedelta(minutes=arrival_time)
            self.entry_timestamp_datetime = self.entry_timestamp
            NotPapSmearPatient.all_non_pap_smears.append(self)

    class CytoSlide(Generic_Entity):
        all_slides: List["CytoSlide"] = []

        def __init__(
            self,
            slide_id: str,
            parent_patient: Generic_Entity,
            arrival_time: float,
            **properties: Any,
        ) -> None:
            super().__init__(
                id=slide_id,
                entity_type="cyto_slide",
                arrival_time=arrival_time,
                **properties,
            )
            self.parent_patient = parent_patient
            CytoSlide.all_slides.append(self)

    PapSmearPatient.all_pap_smears = []
    NotPapSmearPatient.all_non_pap_smears = []
    CytoSlide.all_slides = []

    # --- Resources ---
    cytotech_params = params.get("cyto_technicians", {}).get("cytotech_schedule", {})
    cytopath_params = params.get("cyto_pathologists", {}).get("cytopath_schedule", {})

    cytotech_schedule = _create_schedule_from_params("Cytotech Schedule", cytotech_params)
    cytopath_schedule = _create_schedule_from_params("Cytopath Schedule", cytopath_params)

    cytotechnician = ScheduledResource(
        env=env,
        capacity=params.get("cyto_technicians", {}).get("num_cytotech", 1),
        schedule=cytotech_schedule,
        simulation_start_datetime=sim_start,
        name="Cytotechnicians",
    )
    cytopathologist = ScheduledResource(
        env=env,
        capacity=params.get("cyto_pathologists", {}).get("num_cytopath", 1),
        schedule=cytopath_schedule,
        simulation_start_datetime=sim_start,
        name="Cytopathologists",
    )
    cyto_manual_staining_station = simpy.Resource(
        env=env,
        capacity=params.get("cyto_manual_staining_station", {}).get("num_stations", 1),
    )
    reagent_config = params.get("cyto_staining_kits", {})
    total_reagent_capacity = reagent_config.get("num_kits", 5) * reagent_config.get(
        "stain_per_kit", 100
    )
    cyto_staining_reagents = simpy.Container(
        env=env, capacity=total_reagent_capacity, init=total_reagent_capacity
    )
    reagent_per_slide = reagent_config.get("reagent_per_slide", 0.1)

    reporting = manual_generic_process(
        env=env,
        process_name="Reporting",
        resources_requested=[cytopathologist],
        service_time_params=params.get("cyto_reporting_time", {}),
        is_batched=False,
        next_process=None,
    )

    def slide_to_patient_aggregation(slide: CytoSlide) -> None:
        patient = slide.parent_patient
        patient.slides_completed += 1
        if patient.slides_completed == patient.num_slides:
            reporting.add_item(patient)
        return None

    manual_staining = manual_generic_process(
        env=env,
        process_name="manual staining",
        resources_requested=[
            cytotechnician,
            cyto_manual_staining_station,
            (cyto_staining_reagents, reagent_per_slide),
        ],
        service_time_params=params.get("cyto_staining_time", {}),
        is_batched=True,
        batch_size=params.get("cyto_manual_staining_station", {}).get("batch_size", 5),
        next_process=slide_to_patient_aggregation,
    )

    fixation = manual_generic_process(
        env=env,
        process_name="fixation",
        resources_requested=[],
        service_time_params=params.get("cyto_fixation_time", {}),
        is_batched=False,
        next_process=manual_staining,
    )

    class AccessioningGate:
        def add_item(self, patient: Generic_Entity) -> None:
            for i in range(patient.num_slides):
                slide_id = f"{patient.id}-S{i + 1}"
                slide = CytoSlide(
                    slide_id=slide_id,
                    parent_patient=patient,
                    arrival_time=env.now,
                )
                fixation.add_item(slide)

    accessioning_gate = AccessioningGate()

    Entity_Generator(
        env=env,
        entity_class=PapSmearPatient,
        simulation_start_datetime=sim_start,
        name="Pap Patient Generator",
        first_stage=accessioning_gate,
        working_days=working_days,
        working_hours=working_hours,
        arrival_params=params.get("pap_per_day", {}),
        entity_properties=pap_patient_properties,
    )
    Entity_Generator(
        env=env,
        entity_class=NotPapSmearPatient,
        simulation_start_datetime=sim_start,
        name="Non Pap Patient Generator",
        first_stage=accessioning_gate,
        working_days=working_days,
        working_hours=working_hours,
        arrival_params=params.get("non_pap_per_day", {}),
        entity_properties=non_pap_patient_properties,
    )

    env.run(until=sim_duration_min)

    all_patients: List[Generic_Entity] = (
        PapSmearPatient.all_pap_smears + NotPapSmearPatient.all_non_pap_smears
    )

    patient_rows: List[dict[str, Any]] = []
    for p in all_patients:
        if p.arrival_time < warmup_duration_min:
            continue
        queue_times = getattr(p, "queue_entry_time", {})
        start_times = getattr(p, "process_start_time", {})
        end_times = getattr(p, "process_end_time", {})
        patient_rows.append(
            {
                "Patient ID": p.id,
                "Type": p.entity_type,
                "Arrival": p.entry_timestamp_datetime.strftime("%Y-%m-%d %H:%M"),
                "Reporting Queue": _to_datetime_str(
                    sim_start, queue_times.get("Reporting", "N/A")
                ),
                "Reporting Start": _to_datetime_str(
                    sim_start, start_times.get("Reporting", "N/A")
                ),
                "Reporting End": _to_datetime_str(
                    sim_start, end_times.get("Reporting", "N/A")
                ),
                "Reporting Wait (min)": _wait_minutes(
                    queue_times.get("Reporting"), start_times.get("Reporting")
                ),
                "Completed": "Yes" if "Reporting" in end_times else "No",
            }
        )

    slide_rows: List[dict[str, Any]] = []
    for s in CytoSlide.all_slides:
        if s.arrival_time < warmup_duration_min:
            continue
        queue_times = getattr(s, "queue_entry_time", {})
        start_times = getattr(s, "process_start_time", {})
        end_times = getattr(s, "process_end_time", {})
        slide_rows.append(
            {
                "Slide ID": s.id,
                "Patient ID": s.parent_patient.id,
                "Fixation Queue": _to_datetime_str(
                    sim_start, queue_times.get("fixation", "N/A")
                ),
                "Fixation Start": _to_datetime_str(
                    sim_start, start_times.get("fixation", "N/A")
                ),
                "Fixation End": _to_datetime_str(
                    sim_start, end_times.get("fixation", "N/A")
                ),
                "Fixation Wait (min)": _wait_minutes(
                    queue_times.get("fixation"), start_times.get("fixation")
                ),
                "Staining Queue": _to_datetime_str(
                    sim_start, queue_times.get("manual staining", "N/A")
                ),
                "Staining Start": _to_datetime_str(
                    sim_start, start_times.get("manual staining", "N/A")
                ),
                "Staining End": _to_datetime_str(
                    sim_start, end_times.get("manual staining", "N/A")
                ),
                "Staining Wait (min)": _wait_minutes(
                    queue_times.get("manual staining"),
                    start_times.get("manual staining"),
                ),
            }
        )

    return pd.DataFrame(patient_rows), pd.DataFrame(slide_rows)
