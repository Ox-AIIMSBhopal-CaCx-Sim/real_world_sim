import re
import simpy
import numpy as np
from utils.generic_entity import Generic_Entity
from utils.generic_generator import Entity_Generator
from utils.manual_generic_process import manual_generic_process
from utils.resource_availability import ScheduledResource, TimeSlot, Schedule

from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_PARAMETERS_DIR = _ROOT / "parameters"
_SIM_RESULTS_DIR = _ROOT / "sim_results"
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
    
def get_parameters(parameter_path: Optional[Path] = None) -> Dict[str, Any]:
    """Get simulation parameters, reading from YAML file if provided."""
    path = parameter_path if parameter_path is not None else _PARAMETERS_DIR / "cyto_parameters.yaml"
    if path.exists():
        return read_parameters(path)
    else:
        raise FileNotFoundError(f"Parameters file not found: {path}")

# Load Parameters
params_dict = get_parameters()

# Derive default slide ratios from parameters
PAP_SLIDE_RATIO = params_dict.get('pap_per_day', {}).get('slide_pt_ratio', 1)
SLIDE_PT_RATIO_BY_CC = params_dict.get('slide_pt_ratio_by_case_complexity', {'high': 4, 'low': 1})
NON_PAP_SLIDE_RATIO_DEFAULT = SLIDE_PT_RATIO_BY_CC.get('low', 1)
CASE_COMPLEXITY_P_HIGH = params_dict.get('case_complexity', {}).get('p_high', 0.2)

# Service time parameters (from YAML)
CYTO_REPORTING_TIME = params_dict.get('cyto_reporting_time', {})
CYTO_SLIDE_SCREENING_TIME = params_dict.get('cyto_slide_screening_time', {})
CYTO_STAINING_TIME = params_dict.get('cyto_staining_time', {})
CYTO_FIXATION_TIME = params_dict.get('cyto_fixation_time', {})


def sample_case_complexity() -> str:
    """Return 'high' or 'low' using case_complexity.p_high from parameters."""
    return 'high' if np.random.random() < CASE_COMPLEXITY_P_HIGH else 'low'


def pap_patient_properties() -> Dict[str, Any]:
    cc = sample_case_complexity()
    return {'case_complexity': cc, 'num_slides': PAP_SLIDE_RATIO}


def non_pap_patient_properties() -> Dict[str, Any]:
    cc = sample_case_complexity()
    return {'case_complexity': cc, 'num_slides': int(SLIDE_PT_RATIO_BY_CC.get(cc, NON_PAP_SLIDE_RATIO_DEFAULT))}

# Defining pap smear and non pap smear patient Entities
class PapSmearPatient(Generic_Entity):
    all_pap_smears = []
    
    def __init__(self, id: int, arrival_time: float, num_slides: int = PAP_SLIDE_RATIO, **properties: Any) -> None:
        pap_id = f"Pap-{id:06d}"
        super().__init__(
            id=pap_id,
            entity_type="pap_smear",
            arrival_time=arrival_time,
            **properties,
        )
        self.num_slides = num_slides
        self.slides_completed = 0
        self.entry_timestamp = SIMULATION_START_DATETIME + timedelta(minutes=arrival_time)
        self.entry_timestamp_datetime = self.entry_timestamp
        self.entry_timestamp_days = arrival_time / 1440
        self.entry_timestamp_minutes = arrival_time
        PapSmearPatient.all_pap_smears.append(self)

class notPapSmearPatient(Generic_Entity):
    all_non_pap_smears = []
    
    def __init__(self, id: int, arrival_time: float, num_slides: int = NON_PAP_SLIDE_RATIO_DEFAULT, **properties: Any) -> None:
        non_pap_id = f"NonPap-{id:06d}"
        super().__init__(
            id=non_pap_id,
            entity_type="non_pap_smear",
            arrival_time=arrival_time,
            **properties,
        )
        self.num_slides = num_slides
        self.slides_completed = 0
        self.entry_timestamp = SIMULATION_START_DATETIME + timedelta(minutes=arrival_time)
        self.entry_timestamp_datetime = self.entry_timestamp
        self.entry_timestamp_days = arrival_time / 1440
        self.entry_timestamp_minutes = arrival_time
        notPapSmearPatient.all_non_pap_smears.append(self)

class CytoSlide(Generic_Entity):
    """Represents a single slide belonging to a Patient."""
    all_slides = []
    
    def __init__(self, slide_id: str, parent_patient: Generic_Entity, arrival_time: float, **properties: Any) -> None:
        super().__init__(
            id=slide_id,
            entity_type="cyto_slide",
            arrival_time=arrival_time,
            **properties,
        )
        self.parent_patient = parent_patient
        CytoSlide.all_slides.append(self)

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
cytotech_params = params_dict.get('cyto_technicians', {}).get('cytotech_schedule', {})
cytotech_schedule = create_schedule_from_params("Cytotech Schedule", cytotech_params)

junior_pathologist_cfg = params_dict.get('junior_pathologist', {})
junior_pathologist_schedule = create_schedule_from_params(
    "Junior Pathologist Schedule",
    junior_pathologist_cfg.get('junior_pathologist_schedule', {}),
)

senior_pathologist_cfg = params_dict.get('senior_pathologists', {})
senior_pathologist_schedule = create_schedule_from_params(
    "Senior Pathologist Schedule",
    senior_pathologist_cfg.get('senior_pathologist_schedule', {}),
)

# Defining Resources
# Cytotechnicians
num_cytotech = params_dict.get('cyto_technicians', {}).get('num_cytotech', 1)
cytotechnician = ScheduledResource(
    env=sim_env,
    capacity=num_cytotech,
    schedule=cytotech_schedule,
    simulation_start_datetime=SIMULATION_START_DATETIME,
    name="Cytotechnicians"
)
# Junior Cytopathologists
num_junior_pathologist = params_dict.get('junior_pathologist', {}).get('num_junior_pathologist', 1)
junior_pathologist = ScheduledResource(
    env=sim_env,
    capacity=num_junior_pathologist,
    schedule=junior_pathologist_schedule,
    simulation_start_datetime=SIMULATION_START_DATETIME,
    name="Junior Cytopathologists"
)
# Senior Cytopathologists
num_senior_pathologist = params_dict.get('senior_pathologists', {}).get('num_senior_pathologist', 1)
senior_pathologist = ScheduledResource(
    env=sim_env,
    capacity=num_senior_pathologist,
    schedule=senior_pathologist_schedule,
    simulation_start_datetime=SIMULATION_START_DATETIME,
    name="Senior Pathologists"
)

# Non-scheduled Resources
cyto_manual_staining_station = simpy.Resource(
    env=sim_env, 
    capacity=params_dict.get('cyto_manual_staining_station', {}).get('num_stations', 1)
)

reagent_config = params_dict.get('cyto_staining_kits', {})
total_reagent_capacity = reagent_config.get('num_kits', 5) * reagent_config.get('stain_per_kit', 100)
cyto_staining_reagents = simpy.Container(env=sim_env, capacity=total_reagent_capacity, init=total_reagent_capacity)

# Reagent consumption amount per slide
reagent_per_slide = reagent_config.get('reagent_per_slide', 0.1)

# Repeat staining parameters
_staining_station_cfg = params_dict.get('cyto_manual_staining_station', {})
STAINING_ERROR_RATE = float(_staining_station_cfg.get('error_rate', 0.01))
SENIOR_RESTAIN_RATE = float(senior_pathologist_cfg.get('repeat_stain_rate', 0.05))
MAX_RESTAIN_ATTEMPTS = int(params_dict.get('repeat_staining', {}).get('max_attempts', 2))

# Process references filled in after manual_staining / screening are defined
manual_staining = None
screening = None
reporting = None


def base_slide_id(slide_id: str) -> str:
    """Strip prior restain suffixes (e.g. Pap-000001-S1-R1 -> Pap-000001-S1)."""
    return re.sub(r'-R\d+$', '', slide_id)


def spawn_restain_slide(source_slide: 'CytoSlide', reason: str) -> None:
    """Send a new slide entity back to staining with a traceable ID."""
    attempt = getattr(source_slide, 'restain_attempt', 0) + 1
    if attempt > MAX_RESTAIN_ATTEMPTS:
        slide_to_patient_aggregation(source_slide)
        return

    source_slide.superseded = True
    parent = source_slide.parent_patient
    root_id = base_slide_id(source_slide.id)
    new_slide_id = f"{root_id}-R{attempt}"
    tracking_id = f"{parent.id}-R{attempt}"

    new_slide = CytoSlide(
        slide_id=new_slide_id,
        parent_patient=parent,
        arrival_time=sim_env.now,
        case_complexity=getattr(source_slide, 'case_complexity', parent.case_complexity),
        tracking_id=tracking_id,
        original_slide_id=source_slide.id,
        restain_attempt=attempt,
        restain_reason=reason,
    )
    if not hasattr(parent, 'cyto_slides'):
        parent.cyto_slides = []
    parent.cyto_slides.append(new_slide)
    manual_staining.add_item(new_slide)


def route_after_staining(slide):
    """Equipment QC after staining: failed slides are restained instead of aggregating."""
    if np.random.random() < STAINING_ERROR_RATE:
        spawn_restain_slide(slide, 'equipment_error')
        return None
    slide_to_patient_aggregation(slide)
    return None


def route_after_screening(patient):
    """Senior pathologist preference: some slides return to staining before reporting."""
    restain_triggered = False
    for slide in getattr(patient, 'cyto_slides', []):
        if getattr(slide, 'superseded', False):
            continue
        end_times = getattr(slide, 'process_end_time', {})
        if 'manual staining' not in end_times:
            continue
        if np.random.random() < SENIOR_RESTAIN_RATE:
            spawn_restain_slide(slide, 'senior_pathologist')
            patient.slides_completed = max(0, patient.slides_completed - 1)
            restain_triggered = True
    if not restain_triggered:
        reporting.add_item(patient)
    return None


def slide_to_patient_aggregation(slide):
    """Callback to sync slides. Once all slides for a patient are done, start screening."""
    patient = slide.parent_patient
    patient.slides_completed += 1

    target = getattr(patient, 'initial_num_slides', patient.num_slides)
    if patient.slides_completed == target:
        screening.add_item(patient)

    return None

# Defining Processes
reporting = manual_generic_process(
    env=sim_env,
    process_name='Reporting',
    resources_requested=[senior_pathologist],
    service_time_params=params_dict.get('cyto_reporting_time', CYTO_REPORTING_TIME),
    is_batched=False,
    next_process=None,
)

# Slide review by junior pathologist:
screening = manual_generic_process(
    env=sim_env,
    process_name='slide screening',
    resources_requested=[junior_pathologist],
    service_time_params=params_dict.get('cyto_slide_screening_time', CYTO_SLIDE_SCREENING_TIME),
    is_batched=False,
    next_process=route_after_screening,
)

manual_staining = manual_generic_process(
    env=sim_env,
    process_name='manual staining',
    resources_requested=[cytotechnician, cyto_manual_staining_station, (cyto_staining_reagents, reagent_per_slide)],
    service_time_params=params_dict.get('cyto_staining_time', CYTO_STAINING_TIME),
    is_batched=True,
    batch_size=params_dict.get('cyto_manual_staining_station', {}).get('batch_size', 5),
    next_process=slide_to_patient_aggregation,
)

fixation = manual_generic_process(
    env=sim_env,
    process_name = 'fixation',
    resources_requested=[],
    service_time_params=params_dict.get('cyto_fixation_time', CYTO_FIXATION_TIME),
    is_batched = False,
    next_process = manual_staining,
)

# Accessioning Gate: Splits patients into slides
class AccessioningGate:
    def add_item(self, patient):
        """Splits a patient into multiple slides and sends each to fixation."""
        patient.initial_num_slides = patient.num_slides
        patient.slides_completed = 0
        patient.cyto_slides = []
        for i in range(patient.num_slides):
            slide_id = f"{patient.id}-S{i+1}"
            slide = CytoSlide(
                slide_id=slide_id,
                parent_patient=patient,
                arrival_time=sim_env.now,
                case_complexity=patient.case_complexity,
                tracking_id=patient.id,
                restain_attempt=0,
                restain_reason=None,
            )
            patient.cyto_slides.append(slide)
            fixation.add_item(slide)
        return None

accessioning_gate = AccessioningGate()

#Defining the generator functions
pap_patient_generator = Entity_Generator(
    env=sim_env,
    entity_class=PapSmearPatient,
    simulation_start_datetime=SIMULATION_START_DATETIME,
    name='Pap Patient Generator',
    first_stage=accessioning_gate, # Start with accessioning to split into slides
    working_days=[0,1,2,3,4,5,6],
    working_hours=[9,17],
    arrival_params={
        'distribution':params_dict.get('pap_per_day', {}).get('distribution', 'poisson'),
        'params':params_dict.get('pap_per_day', {}).get('params', [5])
    },
    entity_properties=pap_patient_properties,
)

non_pap_patient_generator = Entity_Generator(
    env = sim_env,
    entity_class=notPapSmearPatient,
    simulation_start_datetime=SIMULATION_START_DATETIME,
    name='Non Pap Patient Generator',
    first_stage=accessioning_gate,
    working_days=[0,1,2,3,4,5,6],
    working_hours=[9,17],
    arrival_params={
        'distribution':params_dict.get('non_pap_per_day', {}).get('distribution', 'poisson'),
        'params':params_dict.get('non_pap_per_day', {}).get('params', [20])
    },
    entity_properties=non_pap_patient_properties,
)




# Run the Simulation
SIMULATION_END_DATETIME = add_months(SIMULATION_START_DATETIME, 12)
WARMUP_END_DATETIME = add_months(SIMULATION_START_DATETIME, 1)
SIM_DURATION = int((SIMULATION_END_DATETIME - SIMULATION_START_DATETIME).total_seconds() / 60)
WARMUP_DURATION_MINUTES = int((WARMUP_END_DATETIME - SIMULATION_START_DATETIME).total_seconds() / 60)

print(
    f"--- Repeat staining: equipment error rate={STAINING_ERROR_RATE:.3f}, "
    f"senior restain rate={SENIOR_RESTAIN_RATE:.3f}, max attempts={MAX_RESTAIN_ATTEMPTS} ---"
)
print(
    f"--- Starting Cytopathology Simulation ({SIM_DURATION} minutes / 12 months) ---"
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

# Collecting Results
import pandas as pd

all_patients = PapSmearPatient.all_pap_smears + notPapSmearPatient.all_non_pap_smears
all_slides = CytoSlide.all_slides

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
    if s.arrival_time < WARMUP_DURATION_MINUTES:
        continue

    # Safely get timestamp dictionaries
    queue_times = getattr(s, 'queue_entry_time', {})
    start_times = getattr(s, 'process_start_time', {})
    end_times = getattr(s, 'process_end_time', {})
    
    slide_results.append({
        'Slide ID': s.id,
        'Patient ID': s.parent_patient.id,
        'Tracking ID': getattr(s, 'tracking_id', s.parent_patient.id),
        'Original Slide ID': getattr(s, 'original_slide_id', s.id),
        'Restain Attempt': getattr(s, 'restain_attempt', 0),
        'Restain Reason': getattr(s, 'restain_reason', '') or '',
        'Fixation Start': to_datetime_str(start_times.get('fixation', 'N/A')),
        'Fixation End': to_datetime_str(end_times.get('fixation', 'N/A')),
        'Staining Start': to_datetime_str(start_times.get('manual staining', 'N/A')),
        'Staining End': to_datetime_str(end_times.get('manual staining', 'N/A')),
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

# Saving to CSV for further analysis
_SIM_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
_patient_csv = _SIM_RESULTS_DIR / "simulation_patient_timestamps.csv"
_slide_csv = _SIM_RESULTS_DIR / "simulation_slide_timestamps.csv"
df_patients.to_csv(_patient_csv, index=False)
df_slides.to_csv(_slide_csv, index=False)
print(f"\nResults saved to '{_patient_csv}' and '{_slide_csv}'")
