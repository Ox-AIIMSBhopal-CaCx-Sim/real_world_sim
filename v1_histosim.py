import simpy
import numpy as np
import generic_generator
from generic_entity import Generic_Entity, HistoSample
from generic_generator import Entity_Generator
from manual_generic_process import manual_generic_process
from resource_availability import ScheduledResource, TimeSlot, Schedule

from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional
from pathlib import Path
import yaml
import csv
import calendar

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
    
def get_parameters(parameter_path: Path = Path("histo_parameters.yaml")) -> Dict[str, Any]:
    """Get simulation parameters, reading from YAML file if provided."""
    if parameter_path.exists():
        return read_parameters(parameter_path)
    else:
        raise FileNotFoundError(f"Parameters file not found: {parameter_path}")

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

# Helper function to create schedule from yaml parameters
def create_schedule_from_params(schedule_name: str, schedule_params: Dict[str, Any]) -> Schedule:
    """Creates a Schedule object from YAML-defined time slots."""
    schedule = Schedule(schedule_name)
    for slot_name, slot_data in schedule_params.items():
        days = slot_data['days']
        start_hour, end_hour = slot_data['hours']
        schedule.add_time_slot(
            start_time=time(start_hour, 0),
            end_time=time(end_hour, 0),
            days_of_week=days
        )
    return schedule

# Defining Schedules
histotech_params = params_dict.get('histo_technicians', {}).get('histotech_schedule', {})
histotech_schedule = create_schedule_from_params("Histotech Schedule", histotech_params)

histopath_params = params_dict.get('histo_pathologists', {}).get('histopath_schedule', {})
histopath_schedule = create_schedule_from_params("Histopath Schedule", histopath_params)

# Path residents: YAML key is path_resident (singular). Fall back to technician hours if no schedule.
_path_resident_cfg = params_dict.get("path_resident") or params_dict.get("path_residents") or {}
_resident_sched_params = _path_resident_cfg.get("resident_schedule") or _path_resident_cfg.get(
    "histotech_schedule"
)
if _resident_sched_params:
    path_resident_schedule = create_schedule_from_params(
        "Resident Schedule", _resident_sched_params
    )
else:
    path_resident_schedule = histotech_schedule

# Defining Resources
num_histotech = params_dict.get('histo_technicians', {}).get('num_cytotech', 1)
histotechnician = ScheduledResource(
    env=sim_env,
    capacity=num_histotech,
    schedule=histotech_schedule,
    simulation_start_datetime=SIMULATION_START_DATETIME,
    name="Histotechnicians"
)

num_histopath = params_dict.get('histo_pathologists', {}).get('num_cytopath', 1)
histopathologist = ScheduledResource(
    env=sim_env,
    capacity=num_histopath,
    schedule=histopath_schedule,
    simulation_start_datetime=SIMULATION_START_DATETIME,
    name="Histopathologists"
)

num_path_resident = int(params_dict.get("path_resident", {}).get("num", 5))
path_resident = ScheduledResource(
    env=sim_env,
    capacity=num_path_resident,
    schedule=path_resident_schedule,
    simulation_start_datetime=SIMULATION_START_DATETIME,
    name="PathResidents",
)

# Non-scheduled Resources
histo_grossing_station = simpy.Resource(
    env=sim_env,
    capacity=params_dict.get('histo_grossing_station', {}).get('num_stations', 1)
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

# Sync Point: Aggregating slides back to patient
def slide_to_patient_aggregation(slide):
    """Callback to sync slides. Once all slides for a patient are done, start reporting."""
    patient = slide.parent_patient
    patient.slides_completed += 1
    
    if patient.slides_completed == patient.num_slides:
        # All slides are ready, patient enters reporting
        reporting.add_item(patient)
    
    return None # Slide entity ends its lifecycle here


# 6) Reporting

_DEFAULT_HISTO_REPORTING_TIME = {
    "by_case_complexity": {
        "high": {"distribution": "triangular", "params": [20, 30, 100]},
        "low": {"distribution": "triangular", "params": [5, 10, 20]},
    }
}

_DEFAULT_HISTO_FIXATION_TIME = {
    "by_size": {
        "small": {"distribution": "constant", "params": 360},
        "medium": {"distribution": "constant", "params": 720},
        "large": {"distribution": "constant", "params": 2880},
    }
}

_DEFAULT_HISTO_GROSSING_TIME = {
    "by_size": {
        "small": {"distribution": "constant", "params": 10},
        "medium": {"distribution": "constant", "params": 30},
        "large": {"distribution": "constant", "params": 120},
    }
}

reporting = manual_generic_process(
    env=sim_env,
    process_name="Reporting",
    resources_requested=[histopathologist],
    service_time_params=params_dict.get(
        "histo_reporting_time", _DEFAULT_HISTO_REPORTING_TIME
    ),
    is_batched=False,
    next_process=None,
)


# 5) Staining and Slide Preparation
staining = manual_generic_process(
    env=sim_env,
    process_name="Staining",
    resources_requested=[histotechnician, histo_staining_station, (histo_staining_reagents, reagent_per_slide)],
    service_time_params={
        'distribution': params_dict.get('histo_staining_time', {}).get('distribution', 'constant'),
        'params': params_dict.get('histo_staining_time', {}).get('params', [35])
    },
    is_batched=True,
    batch_size=STAINING_BATCH_SIZE,
    next_process=slide_to_patient_aggregation,
)

# 4) Sectioning
sectioning = manual_generic_process(
    env=sim_env,
    process_name="Sectioning",
    resources_requested=[histotechnician, histo_sectioning_station],
    service_time_params={
        'distribution': params_dict.get('histo_sectioning_time', {}).get('distribution', 'constant'),
        'params': params_dict.get('histo_sectioning_time', {}).get('params', [1])
    },
    is_batched=False,
    next_process=staining,
)

# 3) Embedding
embedding = manual_generic_process(
    env=sim_env,
    process_name="Embedding",
    resources_requested=[histotechnician, histo_embedding_station],
    service_time_params={
        'distribution': params_dict.get('histo_embedding_time', {}).get('distribution', 'constant'),
        'params': params_dict.get('histo_embedding_time', {}).get('params', [1])
    },
    is_batched=False,
    next_process=sectioning,
)

# 2) Tissue Processing
tissue_processing = manual_generic_process(
    env=sim_env,
    process_name="Tissue Processing",
    resources_requested=[histo_tissue_processor],
    service_time_params={
        'distribution': params_dict.get('histo_tissue_processing_time', {}).get('distribution', 'constant'),
        'params': params_dict.get('histo_tissue_processing_time', {}).get('params', [1320])
    },
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
        for i in range(patient.num_slides):
            slide_id = f"{patient.id}-S{i+1}"
            slide = HistoSlide(slide_id=slide_id, parent_patient=patient, arrival_time=sim_env.now)
            # Send slide to tissue processing
            tissue_processing.add_item(slide)
        yield sim_env.timeout(0)

block_generation_gate = BlockGenerationGate()

# 1) Grossing
grossing = manual_generic_process(
    env=sim_env,
    process_name="Grossing",
    resources_requested=[histo_grossing_station, path_resident],
    service_time_params=params_dict.get(
        "histo_grossing_time", _DEFAULT_HISTO_GROSSING_TIME
    ),
    is_batched=False,
    next_process=block_generation_gate,
)

# 0) Fixation
fixation = manual_generic_process(
    env=sim_env,
    process_name="Fixation",
    resources_requested=[],
    service_time_params=params_dict.get(
        "histo_fixation_time", _DEFAULT_HISTO_FIXATION_TIME
    ),
    is_batched=False,
    next_process=grossing,
)

# Defining the generator functions
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

# --- Print Summary of Parameters Used ---
print("=========================================")
print("  HISTOPATHOLOGY SIMULATION PARAMETERS   ")
print("=========================================")
print(yaml.dump(params_dict, default_flow_style=False))
print("=========================================\n")

# Run the Simulation
SIMULATION_END_DATETIME = add_months(SIMULATION_START_DATETIME, 12)
WARMUP_END_DATETIME = add_months(SIMULATION_START_DATETIME, 1)
SIM_DURATION = int((SIMULATION_END_DATETIME - SIMULATION_START_DATETIME).total_seconds() / 60)
WARMUP_DURATION_MINUTES = int((WARMUP_END_DATETIME - SIMULATION_START_DATETIME).total_seconds() / 60)

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
    
# Collecting Results
import pandas as pd

all_patients = CervicalBiopsyPatient.all_cervical_biopsies + NonCervicalBiopsyPatient.all_non_cervical_biopsies
all_slides = HistoSlide.all_slides

patient_results = []
for p in all_patients:
    # Safely get timestamp dictionaries
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
        'Reporting Queue': to_datetime_str(queue_times.get('Reporting', 'N/A')),
        'Reporting Start': to_datetime_str(start_times.get('Reporting', 'N/A')),
        'Reporting End': to_datetime_str(end_times.get('Reporting', 'N/A')),
        'Completed': 'Yes' if 'Reporting' in end_times else 'No'
    })

slide_results = []
for s in all_slides:
    if s.parent_patient.arrival_time < WARMUP_DURATION_MINUTES:
        continue

    # Safely get timestamp dictionaries for slide
    queue_times = getattr(s, 'queue_entry_time', {})
    start_times = getattr(s, 'process_start_time', {})
    end_times = getattr(s, 'process_end_time', {})
    
    # Safely get timestamp dictionaries for parent patient (for pre-slide processes)
    patient_start_times = getattr(s.parent_patient, 'process_start_time', {})
    patient_end_times = getattr(s.parent_patient, 'process_end_time', {})
    
    slide_results.append({
        'Slide ID': s.id,
        'Patient ID': s.parent_patient.id,
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

# Saving to CSV for further analysis
df_patients.to_csv("histo_simulation_patient_timestamps.csv", index=False)
df_slides.to_csv("histo_simulation_slide_timestamps.csv", index=False)
print("\nResults saved to 'histo_simulation_patient_timestamps.csv' and 'histo_simulation_slide_timestamps.csv'")


# MAchine resource utilisation percentage
# HR utilisation percentage
# Additional processes which can be bottlenecks
# Model limitations are adverse events - Strikes, machine not working, 
# Model should also need to identify when the machine needs to be serviced because if the machine is not 
# Incident register - which machine breaks down by what frequency
# Contingency plans cannot run forever
# After how many days after breakdown does the queues explode
# TAT will increase expoenntially, we will stop the billing after 8th day. 
# Can also work on Sundays
# Nice implementations of the model. 
# Predictive Daily modelling - how do I distribute resources today
# 

# What features about UI
# Tell me all the assumptions - tweak all the parameters
# All the Graphs/numbers and Tables
# Details of a report - Input parameters
# KPI Graph and Table 
# KPI that we are measuring 

