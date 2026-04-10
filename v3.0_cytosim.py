import simpy
import numpy as np
import generic_generator
from generic_entity import Generic_Entity
from generic_generator import Entity_Generator
from manual_generic_process import manual_generic_process
from resource_availability import ScheduledResource, TimeSlot, Schedule

from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional
from pathlib import Path
import yaml
import csv

# Configuration
SIMULATION_START_DATETIME = datetime(2026, 5, 1, 8, 0, 0)  # Simulation starts on May 1st 2026 at 8am
np.random.seed(42)  # To make the responses deterministic for testing
sim_env = simpy.Environment()

# Helper Functions
def read_parameters(parameter_path: Path) -> Dict[str, Any]:
    """Read simulation parameters from a YAML file."""
    with parameter_path.open('r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}
    
def get_parameters(parameter_path: Path = Path("cyto_parameters.yaml")) -> Dict[str, Any]:
    """Get simulation parameters, reading from YAML file if provided."""
    if parameter_path.exists():
        return read_parameters(parameter_path)
    else:
        raise FileNotFoundError(f"Parameters file not found: {parameter_path}")

# Load Parameters
params_dict = get_parameters()

# Derive default slide ratios from parameters
PAP_SLIDE_RATIO = params_dict.get('pap_per_day', {}).get('slide_pt_ratio', 1)
NON_PAP_SLIDE_RATIO = params_dict.get('non_pap_per_day', {}).get('slide_pt_ratio', 3)

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
    
    def __init__(self, id: int, arrival_time: float, num_slides: int = NON_PAP_SLIDE_RATIO, **properties: Any) -> None:
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

cytopath_params = params_dict.get('cyto_pathologists', {}).get('cytopath_schedule', {})
cytopath_schedule = create_schedule_from_params("Cytopath Schedule", cytopath_params)

# Defining Resources
num_cytotech = params_dict.get('cyto_technicians', {}).get('num_cytotech', 1)
cytotechnician = ScheduledResource(
    env=sim_env,
    capacity=num_cytotech,
    schedule=cytotech_schedule,
    simulation_start_datetime=SIMULATION_START_DATETIME,
    name="Cytotechnicians"
)

num_cytopath = params_dict.get('cyto_pathologists', {}).get('num_cytopath', 1)
cytopathologist = ScheduledResource(
    env=sim_env,
    capacity=num_cytopath,
    schedule=cytopath_schedule,
    simulation_start_datetime=SIMULATION_START_DATETIME,
    name="Cytopathologists"
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

# Sync Point: Aggregating slides back to patient
def slide_to_patient_aggregation(slide):
    """Callback to sync slides. Once all slides for a patient are done, start reporting."""
    patient = slide.parent_patient
    patient.slides_completed += 1
    
    if patient.slides_completed == patient.num_slides:
        # All slides are ready, patient enters reporting
        reporting.add_item(patient)
    
    return None # Slide entity ends its lifecycle here

# Defining Processes
reporting = manual_generic_process(
    env=sim_env,
    process_name='Reporting',
    resources_requested=[cytopathologist],
    service_time_params={
        'distribution': 'triangular',
        'params': params_dict.get('cyto_reporting_time', {}).get('params', [2, 10, 100])
    },
    is_batched = False,
    next_process = None,
)

manual_staining = manual_generic_process(
    env=sim_env,
    process_name='manual staining',
    resources_requested=[cytotechnician, cyto_manual_staining_station, (cyto_staining_reagents, reagent_per_slide)],
    service_time_params={
        'distribution': 'constant',
        'params': params_dict.get('cyto_staining_time', {}).get('params', {'value': 35})
    },
    is_batched = True,
    batch_size = params_dict.get('cyto_manual_staining_station', {}).get('batch_size', 5),
    next_process = slide_to_patient_aggregation,
)

fixation = manual_generic_process(
    env=sim_env,
    process_name = 'fixation',
    resources_requested=[],
    service_time_params={
        'distribution': 'constant',
        'params': params_dict.get('cyto_fixation_time', {}).get('params', {'value': 20})
    },
    is_batched = False,
    next_process = manual_staining,
)

# Accessioning Gate: Splits patients into slides
class AccessioningGate:
    def add_item(self, patient):
        """Splits a patient into multiple slides and sends each to fixation."""
        for i in range(patient.num_slides):
            slide_id = f"{patient.id}-S{i+1}"
            slide = CytoSlide(slide_id=slide_id, parent_patient=patient, arrival_time=sim_env.now)
            # Send slide to fixation
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
    }
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
    }
)




# Run the Simulation
SIM_DURATION = 5 * 1440 # 5 days in minutes
print(f"--- Starting Cytopathology Simulation ({SIM_DURATION} minutes / 5 days) ---")
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
        'Reporting Queue': to_datetime_str(queue_times.get('Reporting', 'N/A')),
        'Reporting Start': to_datetime_str(start_times.get('Reporting', 'N/A')),
        'Reporting End': to_datetime_str(end_times.get('Reporting', 'N/A')),
        'Completed': 'Yes' if 'Reporting' in end_times else 'No'
    })

slide_results = []
for s in all_slides:
    # Safely get timestamp dictionaries
    queue_times = getattr(s, 'queue_entry_time', {})
    start_times = getattr(s, 'process_start_time', {})
    end_times = getattr(s, 'process_end_time', {})
    
    slide_results.append({
        'Slide ID': s.id,
        'Patient ID': s.parent_patient.id,
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

# Saving to CSV for further analysis
df_patients.to_csv("simulation_patient_timestamps.csv", index=False)
df_slides.to_csv("simulation_slide_timestamps.csv", index=False)
print("\nResults saved to 'simulation_patient_timestamps.csv' and 'simulation_slide_timestamps.csv'")
