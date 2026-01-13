"""
Cytopathology Laboratory Simulation
Combines generic_process, generic_generator, and generic_entity classes
to simulate a complete cytopathology workflow.
"""

import simpy
import numpy as np
import pandas as pd
import yaml
import random
from datetime import datetime, timedelta
from generic_entity import CytoSlide
from generic_process import Lab_Process
from generic_generator import Entity_Generator

# Simulation start date: 1 May 2025, 9:00 AM
SIMULATION_START = datetime(2025, 5, 1, 9, 0, 0)

# Simulation time offset: Start at 9 AM (0.375 days = 9/24)
SIMULATION_TIME_OFFSET = 9 / 24  # 9 AM in fractional days

def sim_time_to_datetime(sim_time):
    """
    Convert simulation time (in days) to actual datetime.
    Simulation starts at time 0 = 9 AM on 1 May 2025
    
    Parameters:
    -----------
    sim_time : float
        Simulation time in days (0 = 9 AM on start date)
    
    Returns:
    --------
    datetime : Actual datetime or None if sim_time is None
    """
    if sim_time is None:
        return None
    # Since sim time 0 = 9 AM, directly add the sim_time to SIMULATION_START
    return SIMULATION_START + timedelta(days=sim_time)

def format_datetime(dt):
    """
    Format datetime as HH:MM DD/MM/YY
    
    Parameters:
    -----------
    dt : datetime
        Datetime object
    
    Returns:
    --------
    str : Formatted datetime string
    """
    if dt is None:
        return None
    return dt.strftime("%H:%M %d/%m/%y")


def import_parameters(file_path="parameters.yaml"):
    """Load parameters from YAML file."""
    with open(file_path, 'r') as file:
        parameters = yaml.safe_load(file)
    return parameters


class Batch_Dependent_Process(Lab_Process):
    """
    Extended Lab_Process that waits for the previous stage to complete
    processing all items before starting.
    
    This is useful for processes that should only start after all items
    from the previous stage are ready (e.g., reporting only after all 
    slides are stained).
    """
    
    def __init__(self, env, name, resource=None, batch_size=1,
                 duration_minutes=0, duration_type='constant',
                 distribution_params=None, wait_for_batch=False,
                 previous_stage=None):
        """
        Initialize a batch-dependent process.
        
        Parameters:
        -----------
        previous_stage : Lab_Process, optional
            The previous stage to monitor. This process will wait until
            the previous stage's queue is empty before processing.
        """
        self.previous_stage = previous_stage
        self.completed_items = []
        
        # Call parent constructor
        super().__init__(
            env=env,
            name=name,
            resource=resource,
            batch_size=batch_size,
            duration_minutes=duration_minutes,
            duration_type=duration_type,
            distribution_params=distribution_params,
            wait_for_batch=wait_for_batch
        )
    
    def run(self):
        """
        Modified run process that waits for previous stage to finish
        before processing its queue.
        """
        while True:
            # Wait if queue is empty
            if len(self.queue) == 0:
                yield self.env.timeout(0.01)
                continue
            
            # Check if previous stage is still processing
            if self.previous_stage is not None:
                # Wait until previous stage has no items in its queue
                if len(self.previous_stage.queue) > 0:
                    yield self.env.timeout(0.01)
                    continue
            
            # If wait_for_batch is True, wait until we have enough items
            if self.wait_for_batch and len(self.queue) < self.batch_size:
                yield self.env.timeout(0.01)
                continue
            
            # Collect a batch of items
            batch = []
            for _ in range(min(self.batch_size, len(self.queue))):
                if len(self.queue) > 0:
                    batch.append(self.queue.pop(0))
            
            if len(batch) == 0:
                continue
            
            # Process with or without resource
            if self.resource:
                with self.resource.request() as request:
                    yield request
                    
                    for item in batch:
                        self._record_start_time(item)
                    
                    print(f"[{self.env.now:.2f}] {self.name}: Started processing batch of {len(batch)} items")
                    
                    duration = self.get_duration()
                    yield self.env.timeout(duration)
                    
                    for item in batch:
                        self._record_end_time(item)
                        # Set exit_time to reporting end time (this is the last stage)
                        item.exit_time = self.env.now
                        self._move_to_next_stage(item)
                        self.completed_items.append(item)
                    
                    print(f"[{self.env.now:.2f}] {self.name}: Completed batch of {len(batch)} items")
            else:
                for item in batch:
                    self._record_start_time(item)
                
                print(f"[{self.env.now:.2f}] {self.name}: Started passive processing of {len(batch)} items")
                
                duration = self.get_duration()
                yield self.env.timeout(duration)
                
                for item in batch:
                    self._record_end_time(item)
                    # Set exit_time to reporting end time (this is the last stage)
                    item.exit_time = self.env.now
                    self._move_to_next_stage(item)
                    self.completed_items.append(item)
                
                print(f"[{self.env.now:.2f}] {self.name}: Completed passive processing of {len(batch)} items")
    
    def _move_to_next_stage(self, item):
        """Override to not move items to next stage, as this is the final stage."""
        # Don't move to next stage - reporting is the final stage
        pass


def run_cyto_simulation(params):
    """
    Run the complete cytopathology laboratory simulation.
    
    Parameters:
    -----------
    params : dict
        Parameters loaded from YAML file
    
    Returns:
    --------
    pd.DataFrame : Results with all timestamps
    """
    # Create SimPy environment
    env = simpy.Environment()
    
    # Create resources
    cytotechnicians = simpy.Resource(env, capacity=params['Staff']['num_cytotechnicians'])
    cytopathologists = simpy.Resource(env, capacity=params['Staff']['num_cytopathologists'])
    staining_stations = simpy.Resource(env, capacity=params['Stuff']['num_cyto_staining_stations'])
    
    # Create processing stages
    print("Setting up processing pipeline...\n")
    
    # Stage 1: Fixation (15 mins, batch=1)
    fixation = Lab_Process(
        env=env,
        name='fixation',
        resource=cytotechnicians,
        batch_size=1,
        duration_minutes=15,
        duration_type='constant'
    )
    
    # Stage 2: Staining (20 mins, batch=10, wait_for_batch=True)
    staining = Lab_Process(
        env=env,
        name='staining',
        resource=staining_stations,
        batch_size=10,
        duration_minutes=20,
        duration_type='constant',
        wait_for_batch=True
    )
    
    # Stage 3: Reporting (5 mins exponential, waits for staining to finish)
    reporting = Batch_Dependent_Process(
        env=env,
        name='reporting',
        resource=cytopathologists,
        batch_size=1,
        duration_minutes=5,
        duration_type='exponential',
        distribution_params={'rate': 1.0/5.0},  # Mean = 5 minutes
        previous_stage=staining
    )
    
    # Chain fixation -> staining -> reporting
    fixation.chain(staining).chain(reporting)
    
    # Create generators for Pap and Non-Pap slides
    print("Setting up generators...\n")
    
    # Pap slide generator
    pap_generator = Entity_Generator(
        env=env,
        name='pap_arrivals',
        entity_class=CytoSlide,
        first_stage=fixation,
        working_days=[0, 1, 2, 3, 4, 5],  # Mon-Sat
        working_hours=(9, 16),  # 9 AM - 4 PM
        arrival_rate_per_day=params['simulation']['pap_per_day'],
        arrival_distribution='poisson',
        entity_properties=lambda: {
            'is_pap': True,
            'is_positive': random.random() < 0.05  # 5% positive rate
        }
    )
    
    # Non-Pap slide generator
    non_pap_generator = Entity_Generator(
        env=env,
        name='non_pap_arrivals',
        entity_class=CytoSlide,
        first_stage=fixation,
        working_days=[0, 1, 2, 3, 4, 5],  # Mon-Sat
        working_hours=(9, 16),  # 9 AM - 4 PM
        arrival_rate_per_day=params['simulation']['non_pap_per_day'],
        arrival_distribution='poisson',
        entity_properties={'is_pap': False, 'is_positive': None}
    )
    
    # Run simulation
    run_time = params['simulation']['run_time']
    print(f"{'='*70}")
    print(f"Starting Cytopathology Laboratory Simulation")
    print(f"Run time: {run_time} days (~{run_time/365:.1f} years)")
    print(f"Pap slides per day: {params['simulation']['pap_per_day']}")
    print(f"Non-Pap slides per day: {params['simulation']['non_pap_per_day']}")
    print(f"{'='*70}\n")
    
    env.run(until=run_time)
    
    print(f"\n{'='*70}")
    print(f"Simulation Complete")
    print(f"{'='*70}\n")
    
    # Collect results
    all_slides = reporting.completed_items
    
    print(f"Total slides processed: {len(all_slides)}")
    print(f"Pap slides generated: {pap_generator.entity_count}")
    print(f"Non-Pap slides generated: {non_pap_generator.entity_count}\n")
    
    # Create DataFrame with all timestamps
    results = []
    for slide in all_slides:
        result = {
            'slide_id': slide.id,
            'entity_type': slide.entity_type,
            'is_pap': slide.is_pap,
            'is_positive': slide.is_positive,
            'arrival_time_sim': slide.arrival_time,
            'arrival_time': format_datetime(sim_time_to_datetime(slide.arrival_time)),
            'entry_time': format_datetime(sim_time_to_datetime(slide.entry_time)),
            'exit_time': format_datetime(sim_time_to_datetime(slide.exit_time)),
            'total_time_in_system_days': slide.get_total_time_in_system()
        }
        
        # Add all stage times with formatted dates
        for stage_key, stage_time in slide.stage_times.items():
            result[f'{stage_key}_sim'] = stage_time
            result[stage_key] = format_datetime(sim_time_to_datetime(stage_time))
        
        # Calculate stage durations
        for stage in ['fixation', 'staining', 'reporting']:
            duration = slide.get_stage_duration(stage)
            if duration is not None:
                result[f'{stage}_duration_days'] = duration
        
        # Calculate waiting times between stages
        waiting_times = [
            ('fixation', 'staining', 'waiting_for_staining_days'),
            ('staining', 'reporting', 'waiting_for_reporting_days')
        ]
        
        for prev_stage, next_stage, column_name in waiting_times:
            waiting_time = slide.get_waiting_time(prev_stage, next_stage)
            if waiting_time is not None:
                result[column_name] = waiting_time
        
        results.append(result)
    
    df_results = pd.DataFrame(results)
    
    # Print summary statistics
    if len(results) > 0:
        print("\n" + "="*70)
        print("Summary Statistics")
        print("="*70)
        print(f"\nTotal Time in System (days):")
        print(f"  Mean:   {df_results['total_time_in_system_days'].mean():.4f}")
        print(f"  Median: {df_results['total_time_in_system_days'].median():.4f}")
        print(f"  Min:    {df_results['total_time_in_system_days'].min():.4f}")
        print(f"  Max:    {df_results['total_time_in_system_days'].max():.4f}")
        
        print(f"\nFixation Duration (days):")
        print(f"  Mean:   {df_results['fixation_duration_days'].mean():.4f}")
        
        print(f"\nStaining Duration (days):")
        print(f"  Mean:   {df_results['staining_duration_days'].mean():.4f}")
        
        print(f"\nReporting Duration (days):")
        print(f"  Mean:   {df_results['reporting_duration_days'].mean():.4f}")
        
        print(f"\nWaiting Time for Staining (days):")
        if 'waiting_for_staining_days' in df_results.columns:
            print(f"  Mean:   {df_results['waiting_for_staining_days'].mean():.4f}")
            print(f"  Median: {df_results['waiting_for_staining_days'].median():.4f}")
            print(f"  Max:    {df_results['waiting_for_staining_days'].max():.4f}")
        
        print(f"\nWaiting Time for Reporting (days):")
        if 'waiting_for_reporting_days' in df_results.columns:
            print(f"  Mean:   {df_results['waiting_for_reporting_days'].mean():.4f}")
            print(f"  Median: {df_results['waiting_for_reporting_days'].median():.4f}")
            print(f"  Max:    {df_results['waiting_for_reporting_days'].max():.4f}")
        
        # Breakdown by slide type
        print(f"\nBreakdown by Slide Type:")
        print(f"  Pap slides:     {df_results['is_pap'].sum()}")
        print(f"  Non-Pap slides: {(~df_results['is_pap']).sum()}")
        if df_results['is_pap'].sum() > 0:
            pap_slides = df_results[df_results['is_pap'] == True]
            print(f"  Positive Paps:  {pap_slides['is_positive'].sum()}")
    
    return df_results


if __name__ == "__main__":
    # Load parameters
    print("Loading parameters from parameters.yaml...\n")
    parameters = import_parameters("parameters.yaml")
    
    # Run simulation
    results_df = run_cyto_simulation(parameters)
    
    # Save results
    output_file = "cytology_simulation_results.csv"
    results_df.to_csv(output_file, index=False)
    print(f"\n{'='*70}")
    print(f"Results saved to: {output_file}")
    print(f"{'='*70}\n")
    
    # Display first few rows
    print("First 10 rows of results:")
    print(results_df.head(10).to_string())
    results_df.to_csv("cytology_simulation_results.csv", index=False)
