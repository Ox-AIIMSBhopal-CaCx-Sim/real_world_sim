"""
Cytopathology Laboratory Simulation v2.0
Simulates a cytopathology lab with scheduled slide generation, 
multiple processing stages, and resource consumption tracking.
"""

import simpy
import numpy as np
import pandas as pd
from datetime import datetime, time, timedelta
from resource_availability import (
    Schedule, ScheduledResource, 
    create_standard_weekday_schedule
)


# Simulation constants
SIMULATION_START = datetime(2025, 5, 1, 9, 0, 0)  # May 1, 2025, 9:00 AM (Thursday)
MINUTES_PER_DAY = 1440


def sim_time_to_datetime(sim_time):
    """Convert simulation time (in days) to actual datetime."""
    if sim_time is None:
        return None
    return SIMULATION_START + timedelta(days=sim_time)


def format_datetime(dt):
    """Format datetime as HH:MM DD/MM/YY."""
    if dt is None:
        return None
    return dt.strftime("%H:%M %d/%m/%y")


class PapSmearSlide:
    """Represents a Pap smear slide in the lab."""
    
    def __init__(self, slide_id, arrival_time):
        """
        Initialize a Pap smear slide.
        
        Parameters:
        -----------
        slide_id : int
            Unique identifier for the slide
        arrival_time : float
            Simulation time when slide arrived (in days)
        """
        self.id = slide_id
        self.arrival_time = arrival_time
        self.entry_time = arrival_time
        self.exit_time = None
        
        # Process timestamps
        self.fixation_start = None
        self.fixation_end = None
        self.staining_start = None
        self.staining_end = None
        self.reporting_start = None
        self.reporting_end = None
        
        # Reagent tracking
        self.fixation_reagent_used = 0
        self.stain_reagent_used = 0
    
    def to_dict(self):
        """Convert slide data to dictionary for DataFrame export."""
        return {
            'slide_id': self.id,
            'entry_time': self.entry_time,
            'entry_datetime': format_datetime(sim_time_to_datetime(self.entry_time)),
            'fixation_start': self.fixation_start,
            'fixation_start_datetime': format_datetime(sim_time_to_datetime(self.fixation_start)),
            'fixation_end': self.fixation_end,
            'fixation_end_datetime': format_datetime(sim_time_to_datetime(self.fixation_end)),
            'staining_start': self.staining_start,
            'staining_start_datetime': format_datetime(sim_time_to_datetime(self.staining_start)),
            'staining_end': self.staining_end,
            'staining_end_datetime': format_datetime(sim_time_to_datetime(self.staining_end)),
            'reporting_start': self.reporting_start,
            'reporting_start_datetime': format_datetime(sim_time_to_datetime(self.reporting_start)),
            'reporting_end': self.reporting_end,
            'reporting_end_datetime': format_datetime(sim_time_to_datetime(self.reporting_end)),
            'exit_time': self.exit_time,
            'exit_datetime': format_datetime(sim_time_to_datetime(self.exit_time)),
            'fixation_reagent_used_ml': self.fixation_reagent_used,
            'stain_reagent_used_ml': self.stain_reagent_used,
            'total_time_days': self.exit_time - self.entry_time if self.exit_time else None,
            'total_time_hours': (self.exit_time - self.entry_time) * 24 if self.exit_time else None
        }


class ReagentContainer:
    """Manages reagent inventory with SimPy container."""
    
    def __init__(self, env, name, initial_amount):
        """
        Initialize a reagent container.
        
        Parameters:
        -----------
        env : simpy.Environment
            SimPy environment
        name : str
            Name of the reagent
        initial_amount : float
            Initial amount in ml
        """
        self.env = env
        self.name = name
        self.container = simpy.Container(env, capacity=initial_amount, init=initial_amount)
        self.initial_amount = initial_amount
        self.usage_log = []
    
    def use_reagent(self, amount, slide_id):
        """
        Use a specified amount of reagent.
        
        Parameters:
        -----------
        amount : float
            Amount to use in ml
        slide_id : int
            ID of the slide using the reagent
        
        Returns:
        --------
        simpy.Event : Event that completes when reagent is obtained
        """
        # Log usage
        remaining = self.container.level - amount
        self.usage_log.append({
            'time': self.env.now,
            'datetime': format_datetime(sim_time_to_datetime(self.env.now)),
            'slide_id': slide_id,
            'amount_used': amount,
            'remaining': remaining
        })
        
        # Request reagent from container
        return self.container.get(amount)
    
    @property
    def level(self):
        """Current reagent level in ml."""
        return self.container.level
    
    def get_usage_dataframe(self):
        """Return usage log as pandas DataFrame."""
        return pd.DataFrame(self.usage_log)


class CytopathologyLab:
    """Main simulation class for the cytopathology lab."""
    
    def __init__(self, env, num_cytotechnicians, num_cytopathologists, num_microscopes):
        """
        Initialize the lab with resources.
        
        Parameters:
        -----------
        env : simpy.Environment
            SimPy environment
        num_cytotechnicians : int
            Number of cytotechnicians
        num_cytopathologists : int
            Number of cytopathologists
        num_microscopes : int
            Number of microscopes
        """
        self.env = env
        
        # Create schedules for staff (Monday-Friday, 9 AM - 4 PM)
        cytotech_schedule = create_standard_weekday_schedule(9, 16, "Cytotechnician Schedule")
        cytopath_schedule = create_standard_weekday_schedule(9, 16, "Cytopathologist Schedule")
        
        # Create scheduled resources for staff
        self.cytotechnicians = ScheduledResource(
            env=env,
            capacity=num_cytotechnicians,
            schedule=cytotech_schedule,
            simulation_start_datetime=SIMULATION_START,
            name="Cytotechnicians"
        )
        
        self.cytopathologists = ScheduledResource(
            env=env,
            capacity=num_cytopathologists,
            schedule=cytopath_schedule,
            simulation_start_datetime=SIMULATION_START,
            name="Cytopathologists"
        )
        
        # Microscopes are equipment - available anytime (using standard SimPy resource)
        self.microscopes = simpy.Resource(env, capacity=num_microscopes)
        
        # Reagent containers
        self.fixation_reagent = ReagentContainer(env, "Fixation Reagent", 1000)
        self.stain_reagent = ReagentContainer(env, "Pap Stain Reagent", 1000)
        
        # Tracking
        self.slides = []
        self.slide_counter = 0
        
        # Staining batch queue
        self.staining_queue = []
        self.batch_size = 10
    
    def generate_slides(self, mean_slides_per_day=8):
        """
        Generate Pap smear slides using Poisson distribution.
        Only generates slides Monday-Friday, 9 AM to 4 PM.
        
        Parameters:
        -----------
        mean_slides_per_day : float
            Mean number of slides per day (Poisson lambda)
        """
        # Generator schedule: Monday-Friday, 9 AM - 4 PM
        generator_schedule = create_standard_weekday_schedule(9, 16, "Slide Generator")
        
        while True:
            # Check if we're in generation hours
            current_dt = sim_time_to_datetime(self.env.now)
            
            if generator_schedule.is_available_at(current_dt):
                # Generate slides based on Poisson distribution
                # Calculate inter-arrival time
                # For Poisson process: inter-arrival time ~ Exponential(lambda)
                # lambda = mean_slides_per_day slides per 7-hour workday
                # Rate per minute = mean_slides_per_day / (7 * 60)
                workday_hours = 7  # 9 AM to 4 PM
                rate_per_minute = mean_slides_per_day / (workday_hours * 60)
                
                # Generate inter-arrival time in minutes
                inter_arrival_minutes = np.random.exponential(1 / rate_per_minute)
                inter_arrival_days = inter_arrival_minutes / MINUTES_PER_DAY
                
                # Wait for next arrival
                yield self.env.timeout(inter_arrival_days)
                
                # Check again if we're still in generation hours after waiting
                current_dt = sim_time_to_datetime(self.env.now)
                if generator_schedule.is_available_at(current_dt):
                    # Create new slide
                    self.slide_counter += 1
                    slide = PapSmearSlide(self.slide_counter, self.env.now)
                    self.slides.append(slide)
                    
                    print(f"[{self.env.now:.3f} days | {format_datetime(current_dt)}] Slide {slide.id} generated")
                    
                    # Start processing the slide
                    self.env.process(self.process_slide(slide))
            else:
                # Not in generation hours, wait 1 minute and check again
                yield self.env.timeout(1 / MINUTES_PER_DAY)
    
    def fixation_process(self, slide):
        """
        Fixation process - constant 15 minutes, no technician required.
        
        Parameters:
        -----------
        slide : PapSmearSlide
            The slide to process
        """
        # Record start time
        slide.fixation_start = self.env.now
        
        # Use fixation reagent (10 ml)
        reagent_amount = 10
        yield self.fixation_reagent.use_reagent(reagent_amount, slide.id)
        slide.fixation_reagent_used = reagent_amount
        
        print(f"  [{self.env.now:.3f}] Slide {slide.id} - Fixation started "
              f"(Reagent remaining: {self.fixation_reagent.level:.1f} ml)")
        
        # Fixation takes 15 minutes
        fixation_time = 15 / MINUTES_PER_DAY
        yield self.env.timeout(fixation_time)
        
        # Record end time
        slide.fixation_end = self.env.now
        print(f"  [{self.env.now:.3f}] Slide {slide.id} - Fixation completed")
    
    def staining_process(self, slide):
        """
        Staining process - constant 35 minutes, requires cytotechnician, batch size 10.
        
        Parameters:
        -----------
        slide : PapSmearSlide
            The slide to process
        """
        # Add slide to staining queue
        self.staining_queue.append(slide)
        print(f"  [{self.env.now:.3f}] Slide {slide.id} - Added to staining queue "
              f"(Queue size: {len(self.staining_queue)})")
        
        # Wait until we have a full batch or process partial batch
        while len(self.staining_queue) < self.batch_size:
            yield self.env.timeout(1 / MINUTES_PER_DAY)  # Check every minute
            
            # Check if we should process a partial batch
            # (e.g., if no more slides are coming and queue is waiting)
            if len(self.staining_queue) > 0:
                # Calculate time since oldest slide in queue
                oldest_slide = min(self.staining_queue, key=lambda s: s.fixation_end)
                wait_time = self.env.now - oldest_slide.fixation_end
                
                # Process partial batch if waiting > 1 hour (arbitrary threshold)
                if wait_time > 1/24:
                    break
        
        # Process batch if this slide is the last one to complete the batch
        # or if we decided to process a partial batch
        if slide == self.staining_queue[0] or len(self.staining_queue) >= self.batch_size:
            # Get batch to process (up to batch_size slides)
            batch = self.staining_queue[:self.batch_size]
            self.staining_queue = self.staining_queue[self.batch_size:]
            
            # Request cytotechnician
            with self.cytotechnicians.request() as tech_req:
                yield tech_req
                
                # Record start time for all slides in batch
                batch_start = self.env.now
                for s in batch:
                    s.staining_start = batch_start
                
                print(f"  [{self.env.now:.3f}] Staining batch started - "
                      f"{len(batch)} slides (IDs: {[s.id for s in batch]})")
                
                # Use stain reagent for each slide (10 ml per slide)
                for s in batch:
                    reagent_amount = 10
                    yield self.stain_reagent.use_reagent(reagent_amount, s.id)
                    s.stain_reagent_used = reagent_amount
                
                print(f"  [{self.env.now:.3f}] Staining reagent used - "
                      f"Remaining: {self.stain_reagent.level:.1f} ml")
                
                # Staining takes 35 minutes (constant for entire batch)
                staining_time = 35 / MINUTES_PER_DAY
                yield self.env.timeout(staining_time)
                
                # Record end time for all slides in batch
                batch_end = self.env.now
                for s in batch:
                    s.staining_end = batch_end
                
                print(f"  [{self.env.now:.3f}] Staining batch completed - "
                      f"{len(batch)} slides")
                
                # Start reporting for each slide in the batch
                for s in batch:
                    self.env.process(self.reporting_process(s))
    
    def reporting_process(self, slide):
        """
        Reporting process - normal distribution (mean 5 min, sd 2 min),
        requires cytopathologist and microscope.
        
        Parameters:
        -----------
        slide : PapSmearSlide
            The slide to process
        """
        # Request cytopathologist and microscope
        with self.cytopathologists.request() as path_req:
            with self.microscopes.request() as micro_req:
                yield path_req & micro_req
                
                # Record start time
                slide.reporting_start = self.env.now
                print(f"  [{self.env.now:.3f}] Slide {slide.id} - Reporting started")
                
                # Reporting time from normal distribution (mean=5, sd=2 minutes)
                reporting_minutes = max(1, np.random.normal(5, 2))  # Min 1 minute
                reporting_time = reporting_minutes / MINUTES_PER_DAY
                yield self.env.timeout(reporting_time)
                
                # Record end time
                slide.reporting_end = self.env.now
                slide.exit_time = self.env.now
                
                total_time_hours = (slide.exit_time - slide.entry_time) * 24
                print(f"  [{self.env.now:.3f}] Slide {slide.id} - Reporting completed "
                      f"(Total time: {total_time_hours:.2f} hours)")
    
    def process_slide(self, slide):
        """
        Complete processing workflow for a slide.
        
        Parameters:
        -----------
        slide : PapSmearSlide
            The slide to process
        """
        # Stage 1: Fixation
        yield self.env.process(self.fixation_process(slide))
        
        # Stage 2: Staining (batched)
        yield self.env.process(self.staining_process(slide))
        
        # Stage 3: Reporting (started from staining_process after batch completes)
    
    def get_results_dataframe(self):
        """Return all slide data as a pandas DataFrame."""
        data = [slide.to_dict() for slide in self.slides]
        return pd.DataFrame(data)
    
    def print_summary(self):
        """Print simulation summary statistics."""
        print("\n" + "="*80)
        print("SIMULATION SUMMARY")
        print("="*80)
        print(f"Total slides processed: {len(self.slides)}")
        print(f"Fixation reagent remaining: {self.fixation_reagent.level:.1f} ml / {self.fixation_reagent.initial_amount} ml")
        print(f"Stain reagent remaining: {self.stain_reagent.level:.1f} ml / {self.stain_reagent.initial_amount} ml")
        
        # Calculate statistics for completed slides
        completed_slides = [s for s in self.slides if s.exit_time is not None]
        if completed_slides:
            total_times = [(s.exit_time - s.entry_time) * 24 for s in completed_slides]
            print(f"\nCompleted slides: {len(completed_slides)}")
            print(f"Mean processing time: {np.mean(total_times):.2f} hours")
            print(f"Min processing time: {np.min(total_times):.2f} hours")
            print(f"Max processing time: {np.max(total_times):.2f} hours")
            print(f"Std processing time: {np.std(total_times):.2f} hours")
        
        in_progress = len(self.slides) - len(completed_slides)
        if in_progress > 0:
            print(f"\nSlides in progress: {in_progress}")
        print("="*80 + "\n")


def run_simulation(simulation_days=10, 
                   mean_slides_per_day=8,
                   num_cytotechnicians=1,
                   num_cytopathologists=1,
                   num_microscopes=1):
    """
    Run the cytopathology simulation.
    
    Parameters:
    -----------
    simulation_days : int
        Number of days to run the simulation
    mean_slides_per_day : float
        Mean number of slides generated per day (Poisson)
    num_cytotechnicians : int
        Number of cytotechnicians
    num_cytopathologists : int
        Number of cytopathologists
    num_microscopes : int
        Number of microscopes
    
    Returns:
    --------
    tuple : (lab, results_df, fixation_usage_df, stain_usage_df)
    """
    print("="*80)
    print("CYTOPATHOLOGY LAB SIMULATION v2.0")
    print("="*80)
    print(f"Simulation start: {SIMULATION_START.strftime('%A, %B %d, %Y at %I:%M %p')}")
    print(f"Duration: {simulation_days} days")
    print(f"Mean slides per day: {mean_slides_per_day}")
    print(f"Cytotechnicians: {num_cytotechnicians}")
    print(f"Cytopathologists: {num_cytopathologists}")
    print(f"Microscopes: {num_microscopes}")
    print(f"Initial fixation reagent: 1000 ml")
    print(f"Initial stain reagent: 1000 ml")
    print("="*80 + "\n")
    
    # Create environment
    env = simpy.Environment()
    
    # Create lab
    lab = CytopathologyLab(
        env=env,
        num_cytotechnicians=num_cytotechnicians,
        num_cytopathologists=num_cytopathologists,
        num_microscopes=num_microscopes
    )
    
    # Start slide generation
    env.process(lab.generate_slides(mean_slides_per_day))
    
    # Run simulation
    env.run(until=simulation_days)
    
    # Print summary
    lab.print_summary()
    
    # Get results
    results_df = lab.get_results_dataframe()
    fixation_usage_df = lab.fixation_reagent.get_usage_dataframe()
    stain_usage_df = lab.stain_reagent.get_usage_dataframe()
    
    return lab, results_df, fixation_usage_df, stain_usage_df


if __name__ == "__main__":
    # Run simulation
    lab, results_df, fixation_usage_df, stain_usage_df = run_simulation(
        simulation_days=10,
        mean_slides_per_day=8,
        num_cytotechnicians=1,
        num_cytopathologists=1,
        num_microscopes=1
    )
    
    # Save results to CSV files
    results_df.to_csv('cyto_simulation_results_v2.csv', index=False)
    fixation_usage_df.to_csv('fixation_reagent_usage.csv', index=False)
    stain_usage_df.to_csv('stain_reagent_usage.csv', index=False)
    
    print("\nResults saved to:")
    print("  - cyto_simulation_results_v2.csv")
    print("  - fixation_reagent_usage.csv")
    print("  - stain_reagent_usage.csv")
    
    # Display first few rows
    print("\n" + "="*80)
    print("SAMPLE RESULTS (first 5 slides)")
    print("="*80)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    print(results_df.head())
    
    print("\n" + "="*80)
    print("REAGENT USAGE SUMMARY")
    print("="*80)
    print(f"\nFixation Reagent:")
    print(f"  Total used: {fixation_usage_df['amount_used'].sum():.1f} ml")
    print(f"  Final remaining: {fixation_usage_df['remaining'].iloc[-1]:.1f} ml")
    
    print(f"\nStain Reagent:")
    print(f"  Total used: {stain_usage_df['amount_used'].sum():.1f} ml")
    print(f"  Final remaining: {stain_usage_df['remaining'].iloc[-1]:.1f} ml")
