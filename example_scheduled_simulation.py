"""
Example: Cytopathology Simulation with Scheduled Resources
This demonstrates how to integrate resource_availability with the existing simulation.
"""

import simpy
import yaml
from datetime import datetime, time
from resource_availability import (
    Schedule, ScheduledResource, 
    create_standard_weekday_schedule,
    create_part_time_schedule,
    create_shift_schedule
)

def import_parameters(file_path="parameters.yaml"):
    """Load parameters from YAML file."""
    with open(file_path, 'r') as file:
        parameters = yaml.safe_load(file)
    return parameters


def create_staff_schedules():
    """
    Create example staff schedules for different roles.
    Customize these according to your hospital's actual schedules.
    """
    schedules = {}
    
    # Cytotechnicians - Standard weekday 8 AM to 4 PM
    schedules['cytotechnicians'] = create_standard_weekday_schedule(
        start_hour=8, 
        end_hour=16, 
        name="Cytotechnician Shift"
    )
    
    # Cytopathologists - Standard weekday 9 AM to 5 PM
    schedules['cytopathologists'] = create_standard_weekday_schedule(
        start_hour=9, 
        end_hour=17, 
        name="Cytopathologist Schedule"
    )
    
    # Histopathologists - Extended hours including Saturday morning
    histo_schedule = Schedule("Histopathologist Schedule")
    # Monday-Friday: 8 AM to 6 PM
    histo_schedule.add_time_slot(
        start_time=time(8, 0),
        end_time=time(18, 0),
        days_of_week=[0, 1, 2, 3, 4]
    )
    # Saturday: 8 AM to 1 PM
    histo_schedule.add_time_slot(
        start_time=time(8, 0),
        end_time=time(13, 0),
        days_of_week=[5]
    )
    schedules['histopathologists'] = histo_schedule
    
    # Histotechnicians - Two shifts
    # Morning shift (some staff): 7 AM to 3 PM, Monday-Friday
    schedules['histotech_morning'] = create_shift_schedule(
        start_hour=7,
        end_hour=15,
        days_of_week=[0, 1, 2, 3, 4],
        name="Histotech Morning Shift"
    )
    
    # Afternoon shift (some staff): 11 AM to 7 PM, Monday-Friday
    schedules['histotech_afternoon'] = create_shift_schedule(
        start_hour=11,
        end_hour=19,
        days_of_week=[0, 1, 2, 3, 4],
        name="Histotech Afternoon Shift"
    )
    
    # Part-time staff example: Monday/Wednesday/Friday, 9 AM to 2 PM
    schedules['part_time_tech'] = create_part_time_schedule(
        days_and_hours={
            0: (9, 14),  # Monday
            2: (9, 14),  # Wednesday
            4: (9, 14),  # Friday
        },
        name="Part-time Technician"
    )
    
    return schedules


def setup_simulation_with_schedules(params):
    """
    Set up simulation environment with scheduled resources.
    
    Parameters:
    -----------
    params : dict
        Parameters loaded from YAML file
    
    Returns:
    --------
    tuple : (env, resources_dict, schedules_dict)
    """
    # Create SimPy environment
    env = simpy.Environment()
    
    # Define simulation start datetime
    simulation_start = datetime(2025, 5, 1, 9, 0, 0)  # 1 May 2025, 9:00 AM
    
    # Create staff schedules
    schedules = create_staff_schedules()
    
    # Create scheduled resources
    resources = {}
    
    # Cytotechnicians with schedule
    resources['cytotechnicians'] = ScheduledResource(
        env=env,
        capacity=params['Staff']['num_cytotechnicians'],
        schedule=schedules['cytotechnicians'],
        simulation_start_datetime=simulation_start,
        name="Cytotechnicians"
    )
    
    # Cytopathologists with schedule
    resources['cytopathologists'] = ScheduledResource(
        env=env,
        capacity=params['Staff']['num_cytopathologists'],
        schedule=schedules['cytopathologists'],
        simulation_start_datetime=simulation_start,
        name="Cytopathologists"
    )
    
    # Histopathologists with extended schedule
    resources['histopathologists'] = ScheduledResource(
        env=env,
        capacity=params['Staff']['num_histopathologists'],
        schedule=schedules['histopathologists'],
        simulation_start_datetime=simulation_start,
        name="Histopathologists"
    )
    
    # Histotechnicians - split between morning and afternoon shifts
    num_histotech = params['Staff']['num_histotechnicians']
    morning_staff = num_histotech // 2
    afternoon_staff = num_histotech - morning_staff
    
    resources['histotech_morning'] = ScheduledResource(
        env=env,
        capacity=morning_staff,
        schedule=schedules['histotech_morning'],
        simulation_start_datetime=simulation_start,
        name="Histotech Morning Shift"
    )
    
    resources['histotech_afternoon'] = ScheduledResource(
        env=env,
        capacity=afternoon_staff,
        schedule=schedules['histotech_afternoon'],
        simulation_start_datetime=simulation_start,
        name="Histotech Afternoon Shift"
    )
    
    # Equipment (typically available during all operating hours)
    # Using standard SimPy resources for equipment as they don't have schedule constraints
    resources['staining_stations'] = simpy.Resource(
        env, 
        capacity=params['Stuff']['num_cyto_staining_stations']
    )
    
    resources['microscopes_cyto'] = simpy.Resource(
        env, 
        capacity=params['Stuff']['num_cyto_microscopes']
    )
    
    resources['microscopes_histo'] = simpy.Resource(
        env, 
        capacity=params['Stuff']['num_histo_microscopes']
    )
    
    return env, resources, schedules


def example_process_with_scheduled_staff(env, item_id, resources):
    """
    Example process that uses scheduled staff resources.
    
    This demonstrates how to use ScheduledResource in your existing processes.
    """
    print(f"[{env.now:.2f}] Item {item_id} arrives for processing")
    
    # Step 1: Staining (requires cytotechnician and staining station)
    print(f"[{env.now:.2f}] Item {item_id} waiting for cytotechnician and staining station")
    
    with resources['cytotechnicians'].request() as staff_req:
        with resources['staining_stations'].request() as station_req:
            yield staff_req & station_req
            
            staining_start = env.now
            print(f"[{staining_start:.2f}] Item {item_id} starting staining")
            
            # Staining takes 60 minutes = 60/1440 days
            yield env.timeout(60/1440)
            
            print(f"[{env.now:.2f}] Item {item_id} staining complete")
    
    # Step 2: Screening (requires cytotechnician and microscope)
    print(f"[{env.now:.2f}] Item {item_id} waiting for screening")
    
    with resources['cytotechnicians'].request() as staff_req:
        with resources['microscopes_cyto'].request() as micro_req:
            yield staff_req & micro_req
            
            screening_start = env.now
            print(f"[{screening_start:.2f}] Item {item_id} starting screening")
            
            # Screening takes 20 minutes
            yield env.timeout(20/1440)
            
            print(f"[{env.now:.2f}] Item {item_id} screening complete")
    
    # Step 3: Reporting (requires cytopathologist)
    print(f"[{env.now:.2f}] Item {item_id} waiting for cytopathologist")
    
    with resources['cytopathologists'].request() as path_req:
        yield path_req
        
        reporting_start = env.now
        print(f"[{reporting_start:.2f}] Item {item_id} starting reporting")
        
        # Reporting takes 10 minutes
        yield env.timeout(10/1440)
        
        print(f"[{env.now:.2f}] Item {item_id} COMPLETE")


def run_example_simulation():
    """Run a simple example simulation with scheduled resources."""
    
    # Load parameters
    params = import_parameters()
    
    # Set up simulation
    env, resources, schedules = setup_simulation_with_schedules(params)
    
    # Print schedules
    print("=" * 60)
    print("STAFF SCHEDULES")
    print("=" * 60)
    for name, schedule in schedules.items():
        print(f"\n{schedule}")
    print("\n" + "=" * 60)
    print("SIMULATION START")
    print("=" * 60 + "\n")
    
    # Generate some test items at different times
    # Item 0: Arrives at simulation start (Thursday 9:00 AM)
    env.process(example_process_with_scheduled_staff(env, 0, resources))
    
    # Item 1: Arrives 2 hours later (Thursday 11:00 AM)
    env.process(example_process_with_scheduled_staff(env, 1, resources))
    env.run(until=2/24)  # Run to 11:00 AM
    
    # Item 2: Arrives on Friday afternoon
    env.run(until=1 + 6/24)  # Friday 3:00 PM
    env.process(example_process_with_scheduled_staff(env, 2, resources))
    
    # Item 3: Arrives on Saturday (most staff off)
    env.run(until=2 + 2/24)  # Saturday 11:00 AM
    env.process(example_process_with_scheduled_staff(env, 3, resources))
    
    # Run for 5 days total
    env.run(until=5)
    
    print("\n" + "=" * 60)
    print("SIMULATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_example_simulation()
