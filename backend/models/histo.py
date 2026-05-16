"""Histopathology discrete-event model (parameter-driven, JSON config)."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import simpy

from utils.generic_entity import Generic_Entity, HistoSample
from utils.generic_generator import Entity_Generator
from utils.manual_generic_process import manual_generic_process
from utils.resource_availability import ScheduledResource, Schedule

SIMULATION_START_DATETIME = datetime(2026, 5, 1, 8, 0, 0)

_DEFAULT_SLIDE_PT_RATIO_BY_SIZE = {"small": 1, "medium": 5, "large": 20}
_DEFAULT_HISTO_REPORTING_TIME = {
    "by_case_complexity": {
        "high": {"distribution": "triangular", "params": [20, 30, 100]},
        "low": {"distribution": "triangular", "params": [5, 10, 20]},
    }
}
_DEFAULT_HISTO_FIXATION_TIME = {
    "by_size": {
        "small": {"distribution": "constant", "params": [360]},
        "medium": {"distribution": "constant", "params": [720]},
        "large": {"distribution": "constant", "params": [2880]},
    }
}
_DEFAULT_HISTO_GROSSING_TIME = {
    "by_size": {
        "small": {"distribution": "constant", "params": [10]},
        "medium": {"distribution": "constant", "params": [30]},
        "large": {"distribution": "constant", "params": [120]},
    }
}


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


def run_histo_simulation(
    parameters: dict[str, Any],
    *,
    seed: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run one histopathology replication."""
    if seed is not None:
        np.random.seed(seed)

    params = parameters
    sim_meta = params.get("simulation", {})
    run_time_days = int(sim_meta.get("run_time", 365))
    warmup_days = int(sim_meta.get("warmup_days", 30))
    working_days = sim_meta.get("working_days", [0, 1, 2, 3, 4, 5, 6])
    working_hours = sim_meta.get("working_hours", [9, 17])

    slide_pt_by_size = {
        k: int(v)
        for k, v in params.get(
            "slide_pt_ratio_by_biopsy_size", _DEFAULT_SLIDE_PT_RATIO_BY_SIZE
        ).items()
    }
    num_slides_default = int(slide_pt_by_size.get("small", 1))
    case_complexity_p_high = float(params.get("case_complexity", {}).get("p_high", 0.2))

    def sample_case_complexity() -> str:
        return "high" if np.random.random() < case_complexity_p_high else "low"

    def sample_biopsy_size() -> str:
        weights_cfg = params.get("biopsy_size", {}).get("weights", {})
        sizes = ["small", "medium", "large"]
        if weights_cfg:
            p = np.array([float(weights_cfg.get(s, 0)) for s in sizes], dtype=float)
            if p.sum() <= 0:
                p = np.ones(3) / 3.0
            else:
                p = p / p.sum()
            return str(np.random.choice(sizes, p=p))
        return str(np.random.choice(sizes))

    def biopsy_patient_properties() -> Dict[str, Any]:
        size = sample_biopsy_size()
        cc = sample_case_complexity()
        return {
            "case_complexity": cc,
            "size": size,
            "num_slides": int(slide_pt_by_size.get(size, num_slides_default)),
        }

    sim_start = SIMULATION_START_DATETIME
    sim_end = sim_start + timedelta(days=run_time_days)
    warmup_end = sim_start + timedelta(days=warmup_days)
    sim_duration_min = int((sim_end - sim_start).total_seconds() / 60)
    warmup_duration_min = int((warmup_end - sim_start).total_seconds() / 60)

    env = simpy.Environment()

    class CervicalBiopsyPatient(HistoSample):
        all_cervical: List["CervicalBiopsyPatient"] = []

        def __init__(
            self,
            id: int,
            arrival_time: float,
            num_slides: int = num_slides_default,
            size: str = "small",
            case_complexity: str = "low",
            **properties: Any,
        ) -> None:
            cerv_id = f"Cerv-{id:06d}"
            super().__init__(
                id=cerv_id,
                arrival_time=arrival_time,
                size=size,
                is_cervical=True,
                is_positive=False,
                case_complexity=case_complexity,
                **properties,
            )
            self.entity_type = "cervical_biopsy"
            self.num_slides = num_slides
            self.slides_completed = 0
            self.entry_timestamp = sim_start + timedelta(minutes=arrival_time)
            self.entry_timestamp_datetime = self.entry_timestamp
            CervicalBiopsyPatient.all_cervical.append(self)

    class NonCervicalBiopsyPatient(HistoSample):
        all_non_cervical: List["NonCervicalBiopsyPatient"] = []

        def __init__(
            self,
            id: int,
            arrival_time: float,
            num_slides: int = num_slides_default,
            size: str = "small",
            case_complexity: str = "low",
            **properties: Any,
        ) -> None:
            non_cerv_id = f"NonCerv-{id:06d}"
            super().__init__(
                id=non_cerv_id,
                arrival_time=arrival_time,
                size=size,
                is_cervical=False,
                is_positive=False,
                case_complexity=case_complexity,
                **properties,
            )
            self.entity_type = "non_cervical_biopsy"
            self.num_slides = num_slides
            self.slides_completed = 0
            self.entry_timestamp = sim_start + timedelta(minutes=arrival_time)
            self.entry_timestamp_datetime = self.entry_timestamp
            NonCervicalBiopsyPatient.all_non_cervical.append(self)

    class HistoSlide(Generic_Entity):
        all_slides: List["HistoSlide"] = []

        def __init__(
            self,
            slide_id: str,
            parent_patient: Generic_Entity,
            arrival_time: float,
            **properties: Any,
        ) -> None:
            super().__init__(
                id=slide_id,
                entity_type="histo_slide",
                arrival_time=arrival_time,
                **properties,
            )
            self.parent_patient = parent_patient
            HistoSlide.all_slides.append(self)

    CervicalBiopsyPatient.all_cervical = []
    NonCervicalBiopsyPatient.all_non_cervical = []
    HistoSlide.all_slides = []

    histotech_params = params.get("histo_technicians", {}).get("histotech_schedule", {})
    histopath_params = params.get("histo_pathologists", {}).get("histopath_schedule", {})
    histotech_schedule = _create_schedule_from_params("Histotech Schedule", histotech_params)
    histopath_schedule = _create_schedule_from_params("Histopath Schedule", histopath_params)

    path_resident_cfg = params.get("path_resident") or {}
    resident_sched = path_resident_cfg.get("resident_schedule") or histotech_params
    path_resident_schedule = _create_schedule_from_params("Resident Schedule", resident_sched)

    histotechnician = ScheduledResource(
        env=env,
        capacity=int(params.get("histo_technicians", {}).get("num_cytotech", 1)),
        schedule=histotech_schedule,
        simulation_start_datetime=sim_start,
        name="Histotechnicians",
    )
    histopathologist = ScheduledResource(
        env=env,
        capacity=int(params.get("histo_pathologists", {}).get("num_cytopath", 1)),
        schedule=histopath_schedule,
        simulation_start_datetime=sim_start,
        name="Histopathologists",
    )
    path_resident = ScheduledResource(
        env=env,
        capacity=int(path_resident_cfg.get("num", 5)),
        schedule=path_resident_schedule,
        simulation_start_datetime=sim_start,
        name="PathResidents",
    )

    histo_grossing_station = simpy.Resource(
        env=env,
        capacity=int(params.get("histo_grossing_station", {}).get("num_stations", 1)),
    )
    histo_tissue_processor = simpy.Resource(
        env=env,
        capacity=int(params.get("histo_tissue_processor", {}).get("num_stations", 1)),
    )
    histo_embedding_station = simpy.Resource(
        env=env,
        capacity=int(params.get("histo_embedding_station", {}).get("num_stations", 1)),
    )
    histo_sectioning_station = simpy.Resource(
        env=env,
        capacity=int(params.get("histo_sectioning_station", {}).get("num_stations", 1)),
    )
    histo_staining_station = simpy.Resource(
        env=env,
        capacity=int(params.get("histo_staining_station", {}).get("num_stations", 1)),
    )

    reagent_config = params.get("histo_staining_kits", {})
    total_reagent = reagent_config.get("num_kits", 10) * reagent_config.get("stain_per_kit", 100)
    histo_staining_reagents = simpy.Container(env=env, capacity=total_reagent, init=total_reagent)
    reagent_per_slide = reagent_config.get("reagent_per_slide", 0.1)

    tissue_batch = int(params.get("histo_tissue_processor", {}).get("batch_size", 90))
    staining_batch = int(params.get("histo_staining_station", {}).get("batch_size", 30))

    reporting = manual_generic_process(
        env=env,
        process_name="Reporting",
        resources_requested=[histopathologist],
        service_time_params=params.get("histo_reporting_time", _DEFAULT_HISTO_REPORTING_TIME),
        is_batched=False,
        next_process=None,
    )

    def slide_to_patient_aggregation(slide: HistoSlide) -> None:
        patient = slide.parent_patient
        patient.slides_completed += 1
        if patient.slides_completed == patient.num_slides:
            reporting.add_item(patient)
        return None

    staining = manual_generic_process(
        env=env,
        process_name="Staining",
        resources_requested=[
            histotechnician,
            histo_staining_station,
            (histo_staining_reagents, reagent_per_slide),
        ],
        service_time_params=params.get("histo_staining_time", {}),
        is_batched=True,
        batch_size=staining_batch,
        next_process=slide_to_patient_aggregation,
    )

    sectioning = manual_generic_process(
        env=env,
        process_name="Sectioning",
        resources_requested=[histotechnician, histo_sectioning_station],
        service_time_params=params.get("histo_sectioning_time", {}),
        is_batched=False,
        next_process=staining,
    )

    embedding = manual_generic_process(
        env=env,
        process_name="Embedding",
        resources_requested=[histotechnician, histo_embedding_station],
        service_time_params=params.get("histo_embedding_time", {}),
        is_batched=False,
        next_process=sectioning,
    )

    tissue_processing = manual_generic_process(
        env=env,
        process_name="Tissue Processing",
        resources_requested=[histo_tissue_processor],
        service_time_params=params.get("histo_tissue_processing_time", {}),
        is_batched=True,
        batch_size=tissue_batch,
        next_process=embedding,
    )

    class BlockGenerationGate:
        is_batched = False

        def run_non_batch(self, patient: Generic_Entity):
            for i in range(patient.num_slides):
                slide_id = f"{patient.id}-S{i + 1}"
                slide = HistoSlide(
                    slide_id=slide_id,
                    parent_patient=patient,
                    arrival_time=env.now,
                )
                tissue_processing.add_item(slide)
            yield env.timeout(0)

    block_generation_gate = BlockGenerationGate()

    grossing = manual_generic_process(
        env=env,
        process_name="Grossing",
        resources_requested=[histo_grossing_station, path_resident],
        service_time_params=params.get("histo_grossing_time", _DEFAULT_HISTO_GROSSING_TIME),
        is_batched=False,
        next_process=block_generation_gate,
    )

    fixation = manual_generic_process(
        env=env,
        process_name="Fixation",
        resources_requested=[],
        service_time_params=params.get("histo_fixation_time", _DEFAULT_HISTO_FIXATION_TIME),
        is_batched=False,
        next_process=grossing,
    )

    Entity_Generator(
        env=env,
        entity_class=CervicalBiopsyPatient,
        simulation_start_datetime=sim_start,
        name="Cervical Patient Generator",
        first_stage=fixation,
        working_days=working_days,
        working_hours=working_hours,
        arrival_params=params.get("cervical_biopsies_per_day", {}),
        entity_properties=biopsy_patient_properties,
    )
    Entity_Generator(
        env=env,
        entity_class=NonCervicalBiopsyPatient,
        simulation_start_datetime=sim_start,
        name="Non Cervical Patient Generator",
        first_stage=fixation,
        working_days=working_days,
        working_hours=working_hours,
        arrival_params=params.get("other_biopsies_per_day", {}),
        entity_properties=biopsy_patient_properties,
    )

    env.run(until=sim_duration_min)

    all_patients: List[Generic_Entity] = (
        CervicalBiopsyPatient.all_cervical + NonCervicalBiopsyPatient.all_non_cervical
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
                "Num slides": getattr(p, "num_slides", "N/A"),
                "Biopsy size": getattr(p, "size", "N/A"),
                "Case complexity": getattr(p, "case_complexity", "N/A"),
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
    for s in HistoSlide.all_slides:
        if s.parent_patient.arrival_time < warmup_duration_min:
            continue
        queue_times = getattr(s, "queue_entry_time", {})
        start_times = getattr(s, "process_start_time", {})
        end_times = getattr(s, "process_end_time", {})
        patient_start = getattr(s.parent_patient, "process_start_time", {})
        patient_end = getattr(s.parent_patient, "process_end_time", {})
        slide_rows.append(
            {
                "Slide ID": s.id,
                "Patient ID": s.parent_patient.id,
                "Fixation Start": _to_datetime_str(
                    sim_start, patient_start.get("Fixation", "N/A")
                ),
                "Fixation End": _to_datetime_str(
                    sim_start, patient_end.get("Fixation", "N/A")
                ),
                "Grossing Start": _to_datetime_str(
                    sim_start, patient_start.get("Grossing", "N/A")
                ),
                "Grossing End": _to_datetime_str(
                    sim_start, patient_end.get("Grossing", "N/A")
                ),
                "Tissue Processing Start": _to_datetime_str(
                    sim_start, start_times.get("Tissue Processing", "N/A")
                ),
                "Tissue Processing End": _to_datetime_str(
                    sim_start, end_times.get("Tissue Processing", "N/A")
                ),
                "Staining Start": _to_datetime_str(
                    sim_start, start_times.get("Staining", "N/A")
                ),
                "Staining End": _to_datetime_str(
                    sim_start, end_times.get("Staining", "N/A")
                ),
                "Staining Wait (min)": _wait_minutes(
                    queue_times.get("Staining"), start_times.get("Staining")
                ),
            }
        )

    return pd.DataFrame(patient_rows), pd.DataFrame(slide_rows)
