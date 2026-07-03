import simpy
import numpy as np
from utils.generic_entity import Generic_Entity, HistoSample
from utils.generic_generator import Entity_Generator, DailyScheduleEntityGenerator
from utils.manual_generic_process import manual_generic_process
from utils.resource_availability import (
    ScheduledResource,
    TaskScheduledResource,
    Schedule,
    create_schedule_from_params,
    create_task_schedules_from_params,
)

from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_PARAMETERS_DIR = _ROOT / "parameters"
_SIM_RESULTS_DIR = _ROOT / "sim_results"
import yaml
import csv
import calendar
import integrated_config

# Configuration
SIMULATION_START_DATETIME = datetime(2026, 5, 1, 8, 0, 0)  # Simulation starts on May 1st 2026 at 8am
np.random.seed(42)  # To make the responses deterministic for testing
sim_env = simpy.Environment()


def add_months(dt: datetime, months: int) -> datetime:
    """Return a datetime advanced by a given number of calendar months."""
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)

# Helper Functions
def read_parameters(parameter_path: Path) -> Dict[str, Any]:
    """Read simulation parameters from a YAML file."""
    with parameter_path.open('r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}
    
def get_parameters(parameter_path: Optional[Path] = None) -> Dict[str, Any]:
    """Get simulation parameters, reading from YAML file if provided."""
    path = parameter_path if parameter_path is not None else _PARAMETERS_DIR / "histo_parameters.yaml"
    if path.exists():
        return read_parameters(path)
    else:
        raise FileNotFoundError(f"Parameters file not found: {path}")

# Load Parameters
params_dict = get_parameters()

# Slides per patient by biopsy size (small / medium / large); same for cervical and non-cervical.
_DEFAULT_SLIDE_PT_RATIO_BY_SIZE: Dict[str, int] = {"small": 1, "medium": 5, "large": 20}
if "slide_pt_ratio_by_biopsy_size" in params_dict:
    SLIDE_PT_RATIO_BY_SIZE: Dict[str, int] = {
        k: int(v) for k, v in params_dict["slide_pt_ratio_by_biopsy_size"].items()
    }
else:
    SLIDE_PT_RATIO_BY_SIZE = dict(_DEFAULT_SLIDE_PT_RATIO_BY_SIZE)

CASE_COMPLEXITY_P_HIGH = float(params_dict.get("case_complexity", {}).get("p_high", 0.2))
NUM_SLIDES_DEFAULT = int(SLIDE_PT_RATIO_BY_SIZE.get("small", 1))


def sample_case_complexity() -> str:
    return "high" if np.random.random() < CASE_COMPLEXITY_P_HIGH else "low"


def sample_biopsy_size() -> str:
    weights_cfg = params_dict.get("biopsy_size", {}).get("weights", {})
    sizes = ["small", "medium", "large"]
    if weights_cfg:
        p = np.array([float(weights_cfg.get(s, 0)) for s in sizes], dtype=float)
        if p.sum() <= 0:
            p = np.ones(3) / 3.0
        else:
            p = p / p.sum()
        return str(np.random.choice(sizes, p=p))
    return str(np.random.choice(sizes))


def _biopsy_patient_properties() -> Dict[str, Any]:
    size = sample_biopsy_size()
    cc = sample_case_complexity()
    return {
        "case_complexity": cc,
        "size": size,
        "num_slides": int(SLIDE_PT_RATIO_BY_SIZE.get(size, NUM_SLIDES_DEFAULT)),
    }


# Biopsy patients are HistoSample instances (size, case_complexity) plus simulation-specific fields.
class CervicalBiopsyPatient(HistoSample):
    all_cervical_biopsies: List["CervicalBiopsyPatient"] = []

    def __init__(
        self,
        id: int,
        arrival_time: float,
        num_slides: int = NUM_SLIDES_DEFAULT,
        size: str = "small",
        case_complexity: str = "low",
        is_positive: bool = False,
        **properties: Any,
    ) -> None:
        cerv_id = f"Cerv-{id:06d}"
        super().__init__(
            id=cerv_id,
            arrival_time=arrival_time,
            size=size,
            is_cervical=True,
            is_positive=is_positive,
            case_complexity=case_complexity,
            **properties,
        )
        self.entity_type = "cervical_biopsy"
        self.num_slides = num_slides
        self.slides_completed = 0
        self.entry_timestamp = SIMULATION_START_DATETIME + timedelta(minutes=arrival_time)
        self.entry_timestamp_datetime = self.entry_timestamp
        self.entry_timestamp_days = arrival_time / 1440
        self.entry_timestamp_minutes = arrival_time
        CervicalBiopsyPatient.all_cervical_biopsies.append(self)


class NonCervicalBiopsyPatient(HistoSample):
    all_non_cervical_biopsies: List["NonCervicalBiopsyPatient"] = []

    def __init__(
        self,
        id: int,
        arrival_time: float,
        num_slides: int = NUM_SLIDES_DEFAULT,
        size: str = "small",
        case_complexity: str = "low",
        is_positive: bool = False,
        **properties: Any,
    ) -> None:
        non_cerv_id = f"NonCerv-{id:06d}"
        super().__init__(
            id=non_cerv_id,
            arrival_time=arrival_time,
            size=size,
            is_cervical=False,
            is_positive=is_positive,
            case_complexity=case_complexity,
            **properties,
        )
        self.entity_type = "non_cervical_biopsy"
        self.num_slides = num_slides
        self.slides_completed = 0
        self.entry_timestamp = SIMULATION_START_DATETIME + timedelta(minutes=arrival_time)
        self.entry_timestamp_datetime = self.entry_timestamp
        self.entry_timestamp_days = arrival_time / 1440
        self.entry_timestamp_minutes = arrival_time
        NonCervicalBiopsyPatient.all_non_cervical_biopsies.append(self)

class HistoSlide(Generic_Entity):
    """Represents a single slide belonging to a Patient."""
    all_slides = []
    
    def __init__(self, slide_id: str, parent_patient: Generic_Entity, arrival_time: float, **properties: Any) -> None:
        super().__init__(
            id=slide_id,
            entity_type="histo_slide",
            arrival_time=arrival_time,
            **properties,
        )
        self.parent_patient = parent_patient
        HistoSlide.all_slides.append(self)

# Helper function to create schedule from yaml parameters (re-exported helper)
def _create_schedule_from_params(schedule_name: str, schedule_params: Dict[str, Any]) -> Schedule:
    return create_schedule_from_params(schedule_name, schedule_params)

# Defining Schedules
histotechnician_params = params_dict.get('histo_technicians', {}).get('histotech_schedule', {})
histotechnician_schedule = _create_schedule_from_params("Histotechnician Schedule", histotechnician_params)

senior_pathologist_cfg = params_dict.get('senior_pathologists', {})
senior_pathologist_params = senior_pathologist_cfg.get('senior_pathologist_schedule', {})
senior_pathologist_schedule = _create_schedule_from_params("Senior Pathologist Schedule", senior_pathologist_params)

# Junior pathologists: grossing until 17:00, slide screening from 17:00 onward.
junior_pathologist_cfg = params_dict.get("junior_pathologist") or params_dict.get("path_resident") or {}
junior_task_windows = junior_pathologist_cfg.get("task_windows", {})

# Defining Resources
num_histotech = params_dict.get('histo_technicians', {}).get('num_cytotech', 1)
histotechnician = ScheduledResource(
    env=sim_env,
    capacity=num_histotech,
    schedule=histotechnician_schedule,
    simulation_start_datetime=SIMULATION_START_DATETIME,
    name="Histotechnicians"
)

num_senior_pathologist = params_dict.get('senior_pathologists', {}).get('num_senior_pathologist', 3)
senior_pathologist = ScheduledResource(
    env=sim_env,
    capacity=num_senior_pathologist,
    schedule=senior_pathologist_schedule,
    simulation_start_datetime=SIMULATION_START_DATETIME,
    name="Senior Pathologists"
)

num_junior_pathologist = int(
    junior_pathologist_cfg.get("num_junior_pathologist")
    or junior_pathologist_cfg.get("num", 3)
)
if junior_task_windows:
    junior_pathologist = TaskScheduledResource(
        env=sim_env,
        capacity=num_junior_pathologist,
        task_schedules=create_task_schedules_from_params(junior_task_windows),
        simulation_start_datetime=SIMULATION_START_DATETIME,
        name="Junior Pathologists",
    )
else:
    junior_schedule_params = junior_pathologist_cfg.get("junior_pathologist_schedule", {})
    junior_pathologist = ScheduledResource(
        env=sim_env,
        capacity=num_junior_pathologist,
        schedule=_create_schedule_from_params("Junior Pathologist Schedule", junior_schedule_params),
        simulation_start_datetime=SIMULATION_START_DATETIME,
        name="Junior Pathologists",
    )

# Non-scheduled Resources
histo_grossing_station = simpy.Resource(
    env=sim_env,
    capacity=params_dict.get('histo_grossing_station', {}).get('num_stations', 2)
)

histo_tissue_processor = simpy.Resource(
    env=sim_env,
    capacity=params_dict.get('histo_tissue_processor', {}).get('num_stations', 1)
)

histo_embedding_station = simpy.Resource(
    env=sim_env,
    capacity=params_dict.get('histo_embedding_station', {}).get('num_stations', 1)
)

histo_sectioning_station = simpy.Resource(
    env=sim_env,
    capacity=params_dict.get('histo_sectioning_station', {}).get('num_stations', 1)
)

histo_staining_station = simpy.Resource(
    env=sim_env, 
    capacity=params_dict.get('histo_staining_station', {}).get('num_stations', 1)
)

reagent_config = params_dict.get('histo_staining_kits', {})
total_reagent_capacity = reagent_config.get('num_kits', 10) * reagent_config.get('stain_per_kit', 100)
histo_staining_reagents = simpy.Container(env=sim_env, capacity=total_reagent_capacity, init=total_reagent_capacity)

# Reagent consumption amount per slide
reagent_per_slide = reagent_config.get('reagent_per_slide', 0.1)

# Batch sizes for batched stations (from YAML infrastructure sections)
TISSUE_PROCESSOR_BATCH_SIZE = int(
    params_dict.get("histo_tissue_processor", {}).get("batch_size", 90)
)
STAINING_BATCH_SIZE = int(
    params_dict.get("histo_staining_station", {}).get("batch_size", 30)
)

# Repeat staining parameters (senior pathologist restain only; no equipment error rate)
SENIOR_RESTAIN_RATE = float(senior_pathologist_cfg.get("repeat_stain_rate", 0.30))
MAX_RESTAIN_ATTEMPTS = int(params_dict.get("repeat_staining", {}).get("max_attempts", 2))
RESTAIN_SLIDES_PER_REWORK = int(params_dict.get("repeat_staining", {}).get("slides_per_rework", 5))

# Service time parameters (from YAML)
HISTO_REPORTING_TIME = params_dict.get("histo_reporting_time", {})
HISTO_SLIDE_SCREENING_TIME = params_dict.get("histo_slide_screening_time", {})
HISTO_FIXATION_TIME = params_dict.get("histo_fixation_time", {})
HISTO_GROSSING_TIME = params_dict.get("histo_grossing_time", {})
HISTO_STAINING_TIME = params_dict.get("histo_staining_time", {})
HISTO_SECTIONING_TIME = params_dict.get("histo_sectioning_time", {})
HISTO_EMBEDDING_TIME = params_dict.get("histo_embedding_time", {})
HISTO_TISSUE_PROCESSING_TIME = params_dict.get("histo_tissue_processing_time", {})

# Process references filled in after slide-prep processes are defined
sectioning = None
staining = None
screening = None
reporting = None


def spawn_patient_rework_slides(patient) -> None:
    """Senior pathologist sends the patient back: generate new slides from sectioning."""
    attempt = getattr(patient, "patient_rework_attempt", 0) + 1
    if attempt > MAX_RESTAIN_ATTEMPTS:
        return

    patient.patient_rework_attempt = attempt
    patient.slides_completed = 0
    patient.initial_num_slides = RESTAIN_SLIDES_PER_REWORK

    if not hasattr(patient, "histo_slides"):
        patient.histo_slides = []

    for i in range(RESTAIN_SLIDES_PER_REWORK):
        slide_id = f"{patient.id}-R{attempt}-S{i + 1}"
        slide = HistoSlide(
            slide_id=slide_id,
            parent_patient=patient,
            arrival_time=sim_env.now,
            case_complexity=patient.case_complexity,
            size=patient.size,
            tracking_id=f"{patient.id}-R{attempt}",
            original_slide_id=None,
            restain_attempt=attempt,
            restain_reason="senior_pathologist",
        )
        patient.histo_slides.append(slide)
        sectioning.add_item(slide)


def route_after_reporting(patient):
    """Senior pathologist may send the whole patient back for rework after reporting."""
    attempt = getattr(patient, "patient_rework_attempt", 0)
    if attempt >= MAX_RESTAIN_ATTEMPTS:
        return None
    if np.random.random() < SENIOR_RESTAIN_RATE:
        spawn_patient_rework_slides(patient)
    return None


# Sync Point: Aggregating slides back to patient
def slide_to_patient_aggregation(slide):
    """Callback to sync slides. Once all slides for a patient are done, start screening."""
    patient = slide.parent_patient
    patient.slides_completed += 1

    target = getattr(patient, "initial_num_slides", patient.num_slides)
    if patient.slides_completed == target:
        screening.add_item(patient)

    return None



reporting = manual_generic_process(
    env=sim_env,
    process_name="Reporting",
    resources_requested=[senior_pathologist],
    service_time_params=params_dict.get("histo_reporting_time", HISTO_REPORTING_TIME),
    is_batched=False,
    next_process=route_after_reporting,
)

screening = manual_generic_process(
    env=sim_env,
    process_name="slide screening",
    resources_requested=[(junior_pathologist, "screening")],
    service_time_params=params_dict.get("histo_slide_screening_time", HISTO_SLIDE_SCREENING_TIME),
    is_batched=False,
    next_process=reporting,
)


# 5) Staining and Slide Preparation
staining = manual_generic_process(
    env=sim_env,
    process_name="Staining",
    resources_requested=[histotechnician, histo_staining_station, (histo_staining_reagents, reagent_per_slide)],
    service_time_params=params_dict.get("histo_staining_time", HISTO_STAINING_TIME),
    is_batched=True,
    batch_size=STAINING_BATCH_SIZE,
    next_process=slide_to_patient_aggregation,
)

# 4) Sectioning
sectioning = manual_generic_process(
    env=sim_env,
    process_name="Sectioning",
    resources_requested=[histotechnician, histo_sectioning_station],
    service_time_params=params_dict.get("histo_sectioning_time", HISTO_SECTIONING_TIME),
    is_batched=False,
    next_process=staining,
)

# 3) Embedding
embedding = manual_generic_process(
    env=sim_env,
    process_name="Embedding",
    resources_requested=[histotechnician, histo_embedding_station],
    service_time_params=params_dict.get("histo_embedding_time", HISTO_EMBEDDING_TIME),
    is_batched=False,
    next_process=sectioning,
)

# 2) Tissue Processing
tissue_processing = manual_generic_process(
    env=sim_env,
    process_name="Tissue Processing",
    resources_requested=[histo_tissue_processor],
    service_time_params=params_dict.get("histo_tissue_processing_time", HISTO_TISSUE_PROCESSING_TIME),
    is_batched=True,
    batch_size=TISSUE_PROCESSOR_BATCH_SIZE,
    next_process=embedding,
)

# Block Generation Gate: Splits patients into slides after Grossing
class BlockGenerationGate:
    def __init__(self):
        self.is_batched = False

    def run_non_batch(self, patient):
        """Splits a patient into multiple slides and sends each to tissue processing."""
        patient.initial_num_slides = patient.num_slides
        patient.slides_completed = 0
        patient.patient_rework_attempt = 0
        patient.histo_slides = []
        for i in range(patient.num_slides):
            slide_id = f"{patient.id}-S{i+1}"
            slide = HistoSlide(
                slide_id=slide_id,
                parent_patient=patient,
                arrival_time=sim_env.now,
                case_complexity=patient.case_complexity,
                size=patient.size,
                tracking_id=patient.id,
                restain_attempt=0,
                restain_reason=None,
            )
            patient.histo_slides.append(slide)
            tissue_processing.add_item(slide)
        yield sim_env.timeout(0)

block_generation_gate = BlockGenerationGate()

# 1) Grossing
grossing = manual_generic_process(
    env=sim_env,
    process_name="Grossing",
    resources_requested=[(junior_pathologist, "grossing"), histo_grossing_station],
    service_time_params=params_dict.get("histo_grossing_time", HISTO_GROSSING_TIME),
    is_batched=False,
    next_process=block_generation_gate,
)

# 0) Fixation
fixation = manual_generic_process(
    env=sim_env,
    process_name="Fixation",
    resources_requested=[],
    service_time_params=params_dict.get("histo_fixation_time", HISTO_FIXATION_TIME),
    is_batched=False,
    next_process=grossing,
)

# Cervical arrivals: Poisson by default, or daily schedule from integrated cyto run.
if integrated_config.cervical_daily_schedule is not None:
    cervical_patient_generator = DailyScheduleEntityGenerator(
        env=sim_env,
        entity_class=CervicalBiopsyPatient,
        simulation_start_datetime=SIMULATION_START_DATETIME,
        name='Cervical Patient Generator (from cyto positives)',
        first_stage=fixation,
        working_days=[0, 1, 2, 3, 4, 5, 6],
        working_hours=[9, 17],
        daily_schedule=integrated_config.cervical_daily_schedule,
        entity_properties=_biopsy_patient_properties,
    )
else:
    cervical_patient_generator = Entity_Generator(
        env=sim_env,
        entity_class=CervicalBiopsyPatient,
        simulation_start_datetime=SIMULATION_START_DATETIME,
        name='Cervical Patient Generator',
        first_stage=fixation    , # Start with accessioning to split into slides
        working_days=[0,1,2,3,4,5,6],
        working_hours=[9,17],
        arrival_params={
            'distribution': params_dict.get('cervical_biopsies_per_day', {}).get('distribution', 'poisson'),
            'params': params_dict.get('cervical_biopsies_per_day', {}).get('params', [1])
        },
        entity_properties=_biopsy_patient_properties,
    )

non_cervical_patient_generator = Entity_Generator(
    env=sim_env,
    entity_class=NonCervicalBiopsyPatient,
    simulation_start_datetime=SIMULATION_START_DATETIME,
    name='Non Cervical Patient Generator',
    first_stage=fixation,
    working_days=[0,1,2,3,4,5,6],
    working_hours=[9,17],
    arrival_params={
        'distribution': params_dict.get('other_biopsies_per_day', {}).get('distribution', 'poisson'),
        'params': params_dict.get('other_biopsies_per_day', {}).get('params', [50])
    },
    entity_properties=_biopsy_patient_properties,
)

""" #NOTES
1) MUST ADD SIZE OF TISSUE SIZE (SMALL, MEDIUM LARGE and Case Complexity also is dependent on that)
2) FIXATION TIME WILL DEPEND AND NUMBER OF BLOCKS GENERATED ALSO DEPEND. 
3) Service time for reporting is also dependent on slide size """

SIMULATION_END_DATETIME = add_months(SIMULATION_START_DATETIME, 12)
WARMUP_END_DATETIME = add_months(SIMULATION_START_DATETIME, 1)
SIM_DURATION = int((SIMULATION_END_DATETIME - SIMULATION_START_DATETIME).total_seconds() / 60)
WARMUP_DURATION_MINUTES = int((WARMUP_END_DATETIME - SIMULATION_START_DATETIME).total_seconds() / 60)


def run_simulation() -> None:
    """Run the histopathology simulation."""
    print("=========================================")
    print("  HISTOPATHOLOGY SIMULATION PARAMETERS   ")
    print("=========================================")
    print(yaml.dump(params_dict, default_flow_style=False))
    print("=========================================\n")
    print(
        f"--- Repeat staining: senior restain rate={SENIOR_RESTAIN_RATE:.3f}, "
        f"max attempts={MAX_RESTAIN_ATTEMPTS}, slides per rework={RESTAIN_SLIDES_PER_REWORK} ---"
    )
    if integrated_config.cervical_daily_schedule is not None:
        total_scheduled = sum(integrated_config.cervical_daily_schedule.values())
        print(
            f"--- Cervical biopsies driven by cyto pap-smear positives "
            f"({total_scheduled} scheduled over {len(integrated_config.cervical_daily_schedule)} days) ---"
        )
    print(
        f"--- Starting Histopathology Simulation ({SIM_DURATION} minutes / 12 months) ---"
    )
    print(
        f"--- Warm-up Period: first month until {WARMUP_END_DATETIME.strftime('%Y-%m-%d %H:%M')} (slides not recorded) ---"
    )
    sim_env.run(until=SIM_DURATION)
    print("--- Simulation Complete ---\n")

# Helper to convert simulation minutes to datetime string
def to_datetime_str(sim_minutes):
    if sim_minutes == 'N/A' or (isinstance(sim_minutes, float) and np.isnan(sim_minutes)):
        return 'N/A'
    dt = SIMULATION_START_DATETIME + timedelta(minutes=float(sim_minutes))
    return dt.strftime('%Y-%m-%d %H:%M')


def process_duration_min(start_times, end_times, process_name):
    start = start_times.get(process_name)
    end = end_times.get(process_name)
    if start is None or end is None:
        return 'N/A'
    return round(float(end) - float(start), 2)
    
def collect_and_save_results() -> None:
    """Collect histopathology trace data and write CSVs."""
    import pandas as pd

    all_patients = CervicalBiopsyPatient.all_cervical_biopsies + NonCervicalBiopsyPatient.all_non_cervical_biopsies
    all_slides = HistoSlide.all_slides

    patient_results = []
    for p in all_patients:
        queue_times = getattr(p, 'queue_entry_time', {})
        start_times = getattr(p, 'process_start_time', {})
        end_times = getattr(p, 'process_end_time', {})

        patient_results.append({
            'Patient ID': p.id,
            'Type': p.entity_type,
            'Arrival': f"{p.entry_timestamp_datetime.strftime('%Y-%m-%d %H:%M')}",
            'Num slides': getattr(p, 'num_slides', 'N/A'),
            'Biopsy size': getattr(p, 'size', 'N/A'),
            'Case complexity': getattr(p, 'case_complexity', 'N/A'),
            'Screening Queue': to_datetime_str(queue_times.get('slide screening', 'N/A')),
            'Screening Start': to_datetime_str(start_times.get('slide screening', 'N/A')),
            'Screening End': to_datetime_str(end_times.get('slide screening', 'N/A')),
            'Screening Duration (min)': process_duration_min(start_times, end_times, 'slide screening'),
            'Reporting Queue': to_datetime_str(queue_times.get('Reporting', 'N/A')),
            'Reporting Start': to_datetime_str(start_times.get('Reporting', 'N/A')),
            'Reporting End': to_datetime_str(end_times.get('Reporting', 'N/A')),
            'Completed': 'Yes' if 'Reporting' in end_times else 'No'
        })

    slide_results = []
    for s in all_slides:
        if s.parent_patient.arrival_time < WARMUP_DURATION_MINUTES:
            continue

        queue_times = getattr(s, 'queue_entry_time', {})
        start_times = getattr(s, 'process_start_time', {})
        end_times = getattr(s, 'process_end_time', {})
        patient_start_times = getattr(s.parent_patient, 'process_start_time', {})
        patient_end_times = getattr(s.parent_patient, 'process_end_time', {})

        slide_results.append({
            'Slide ID': s.id,
            'Patient ID': s.parent_patient.id,
            'Tracking ID': getattr(s, 'tracking_id', s.parent_patient.id),
            'Original Slide ID': getattr(s, 'original_slide_id', s.id),
            'Restain Attempt': getattr(s, 'restain_attempt', 0),
            'Restain Reason': getattr(s, 'restain_reason', '') or '',
            'Fixation Start': to_datetime_str(patient_start_times.get('Fixation', 'N/A')),
            'Fixation End': to_datetime_str(patient_end_times.get('Fixation', 'N/A')),
            'Grossing Start': to_datetime_str(patient_start_times.get('Grossing', 'N/A')),
            'Grossing End': to_datetime_str(patient_end_times.get('Grossing', 'N/A')),
            'Tissue Processing Start': to_datetime_str(start_times.get('Tissue Processing', 'N/A')),
            'Tissue Processing End': to_datetime_str(end_times.get('Tissue Processing', 'N/A')),
            'Embedding Start': to_datetime_str(start_times.get('Embedding', 'N/A')),
            'Embedding End': to_datetime_str(end_times.get('Embedding', 'N/A')),
            'Sectioning Start': to_datetime_str(start_times.get('Sectioning', 'N/A')),
            'Sectioning End': to_datetime_str(end_times.get('Sectioning', 'N/A')),
            'Staining Start': to_datetime_str(start_times.get('Staining', 'N/A')),
            'Staining End': to_datetime_str(end_times.get('Staining', 'N/A')),
        })

    df_patients = pd.DataFrame(patient_results)
    df_slides = pd.DataFrame(slide_results)

    print("\n--- Patient Timestamps (First 20) ---")
    print(df_patients.head(20).to_string(index=False))

    print("\n--- Slide Timestamps (First 20) ---")
    print(df_slides.head(20).to_string(index=False))
    print(f"\nRecorded slides after warm-up: {len(df_slides)}")
    restain_slides = sum(1 for s in all_slides if getattr(s, 'restain_attempt', 0) > 0)
    print(f"Restain slides (all attempts): {restain_slides}")

    _SIM_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    _patient_csv = _SIM_RESULTS_DIR / "histo_simulation_patient_timestamps.csv"
    _slide_csv = _SIM_RESULTS_DIR / "histo_simulation_slide_timestamps.csv"
    df_patients.to_csv(_patient_csv, index=False)
    df_slides.to_csv(_slide_csv, index=False)
    print(f"\nResults saved to '{_patient_csv}' and '{_slide_csv}'")


if __name__ == "__main__":
    run_simulation()
    collect_and_save_results()
