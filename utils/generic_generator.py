import simpy
import numpy as np
import random
from datetime import datetime, timedelta


class Entity_Generator:
    """
    A flexible generator class for discrete event simulation that creates entities 
    based on configurable working days, hours, arrival rates, and entity properties.
    """
    
    def __init__(self, env, name, entity_class, first_stage=None,
                 working_days=None, working_hours=None,
                 arrival_params=None, entity_properties=None,
                 simulation_start_datetime=None):
        """
        Initialize an entity generator.
        
        Parameters:
        -----------
        env : simpy.Environment
            The SimPy environment
        name : str
            Name of this generator (e.g., 'cytology_arrivals', 'biopsy_arrivals')
        entity_class : class
            The class to instantiate for each generated entity (e.g., CytoSlide, HistoSample)
        first_stage : Lab_Process, optional
            The first processing stage where generated entities will be sent
        working_days : list of int, optional
            Days of the week when generation occurs (0=Monday, 6=Sunday)
            Default: [0, 1, 2, 3, 4, 5] (Monday-Saturday)
        working_hours : tuple of (start_hour, end_hour), optional
            Hours of the day when generation occurs (24-hour format)
            Default: (9, 16) (9 AM to 4 PM)
        arrival_rate_per_day : float
            Average number of entities generated per day
        arrival_distribution : str
            Distribution type for inter-arrival times
            Options: 'constant', 'poisson', 'uniform', 'exponential'
        arrival_params : dict, optional
            Additional parameters for arrival distribution
        entity_properties : dict or callable, optional
            Properties to assign to each generated entity
            Can be a dict of fixed values or a callable that returns properties
        
        Example:
        --------
        # Generate Pap smears Mon-Sat, 9-4, 5 per day, with random positivity
        generator = Entity_Generator(
            env=env,
            name='pap_arrivals',
            entity_class=CytoSlide,
            first_stage=fixation_stage,
            working_days=[0, 1, 2, 3, 4, 5],
            working_hours=(9, 16),
            arrival_rate_per_day=5,
            arrival_distribution='poisson',
            entity_properties=lambda: {
                'is_pap': True,
                'is_positive': random.random() < 0.05
            }
        )
        """
        self.env = env
        self.name = name
        self.entity_class = entity_class
        self.first_stage = first_stage
        
        # Working schedule
        self.working_days = working_days if working_days is not None else [0, 1, 2, 3, 4, 5]
        self.working_hours = working_hours if working_hours is not None else (9, 16)
        
        # Simulation start time for alignment
        self.simulation_start_datetime = simulation_start_datetime
        if self.simulation_start_datetime:
            self.start_minutes_offset = self.simulation_start_datetime.hour * 60 + self.simulation_start_datetime.minute
        else:
            self.start_minutes_offset = 540  # Default to 9 AM
            
        # Arrival parameters (expected: {'distribution': '...', 'params': {...}})
        self.arrival_params = arrival_params or {'distribution': 'constant', 'params': {'rate': 1}}
        
        # Entity properties
        self.entity_properties = entity_properties
        
        # Counter for generated entities
        self.entity_count = 0
        
        # Start the generator process
        self.process = env.process(self.run())
    
    def is_working_time(self):
        """
        Check if current simulation time is within working hours and days.
        
        Returns:
        --------
        bool : True if within working schedule
        """
        # Calculate current day of week (0 = Monday, 6 = Sunday)
        # Apply offset to align simulation time 0 with start datetime
        adjusted_time_minutes = self.env.now + self.start_minutes_offset
        current_day = (int(adjusted_time_minutes) // 1440) % 7
        
        # Calculate current hour of day (0-24)
        current_hour = (adjusted_time_minutes % 1440) / 60
        
        # Check if it's a working day
        is_working_day = current_day in self.working_days
        
        # Check if it's within working hours
        start_hour, end_hour = self.working_hours
        is_working_hour = start_hour <= current_hour < end_hour
        
        return is_working_day and is_working_hour
    
    def get_next_working_time(self):
        """
        Calculate the time (in days) until the next working period begins.
        
        Returns:
        --------
        float : Time to wait in days
        """
        # Apply offset to align simulation time 0
        adjusted_time_minutes = self.env.now + self.start_minutes_offset
        current_day = (int(adjusted_time_minutes) // 1440) % 7
        current_hour = (adjusted_time_minutes % 1440) / 60
        
        start_hour, end_hour = self.working_hours
        
        # If we're in a working day but after hours, go to next working day at start_hour
        if current_day in self.working_days and current_hour >= end_hour:
            # Find next working day
            days_ahead = 1
            next_day = (current_day + days_ahead) % 7
            while next_day not in self.working_days:
                days_ahead += 1
                next_day = (current_day + days_ahead) % 7
            
            minutes_until_next = (24 - current_hour) * 60 + (days_ahead - 1) * 1440 + start_hour * 60
            return minutes_until_next
        
        # If we're in a working day but before hours, wait until start_hour today
        if current_day in self.working_days and current_hour < start_hour:
            return (start_hour - current_hour) * 60
        
        # If we're on a non-working day, find the next working day
        if current_day not in self.working_days:
            days_ahead = 1
            next_day = (current_day + days_ahead) % 7
            while next_day not in self.working_days:
                days_ahead += 1
                next_day = (current_day + days_ahead) % 7
            
            minutes_until_next = (24 - current_hour) * 60 + (days_ahead - 1) * 1440 + start_hour * 60
            return minutes_until_next
        
        return 0
    
    def get_inter_arrival_time(self):
        """
        Calculate the time between arrivals based on the specified distribution.
        
        Returns:
        --------
        float : Inter-arrival time in minutes
        """
        distribution = self.arrival_params.get('distribution', 'constant')
        params = self.arrival_params.get('params', {})
        
        if distribution == 'constant':
            # Evenly spaced arrivals throughout working hours
            working_hours_per_day = self.working_hours[1] - self.working_hours[0]
            rate = params.get('rate', 1) # arrivals per day
            inter_arrival_minutes = (working_hours_per_day * 60) / rate
            return inter_arrival_minutes
        
        elif distribution == 'poisson':
            # Exponential inter-arrival times (Poisson process)
            working_hours_per_day = self.working_hours[1] - self.working_hours[0]
            # rate = arrivals per day / working minutes per day
            if isinstance(params, list):
                rate_per_day = params[0]
            elif isinstance(params, (int, float)):
                rate_per_day = params
            else:
                rate_per_day = params.get('lambda', params.get('rate', 1))
            
            rate_per_minute = rate_per_day / (working_hours_per_day * 60)
            inter_arrival_minutes = np.random.exponential(1.0 / rate_per_minute)
            return inter_arrival_minutes
        
        elif distribution == 'uniform':
            # Uniform distribution
            min_time = params.get('min', 30)  # minutes
            max_time = params.get('max', 120)  # minutes
            return np.random.uniform(min_time, max_time)
        
        elif distribution == 'exponential':
            # Exponential with custom rate (arrivals per minute)
            rate = params.get('rate', 1/60)
            return np.random.exponential(1.0 / rate)
        
        else:
            # Default to constant
            working_hours_per_day = self.working_hours[1] - self.working_hours[0]
            return (working_hours_per_day * 60) / params.get('rate', 1)
    
    def get_entity_properties(self):
        """
        Get properties for the next entity to be generated.
        
        Returns:
        --------
        dict : Properties to assign to the entity
        """
        if callable(self.entity_properties):
            # Call the function to get dynamic properties
            return self.entity_properties()
        elif isinstance(self.entity_properties, dict):
            # Return a copy of the static properties
            return self.entity_properties.copy()
        else:
            # No properties specified
            return {}
    
    def run(self):
        """
        Main generator process that creates entities according to schedule and distribution.
        This runs as a SimPy generator process.
        """
        while True:
            # Check if we're in working hours
            if not self.is_working_time():
                # Wait until next working time
                wait_time = self.get_next_working_time()
                yield self.env.timeout(wait_time)
                continue
            
            # Generate an entity
            self.entity_count += 1
            
            # Get properties for this entity
            properties = self.get_entity_properties()
            
            # Create the entity with its properties
            entity = self.entity_class(
                id=self.entity_count,
                arrival_time=self.env.now,
                **properties
            )
            
            # Log the generation
            print(f"[{self.env.now:.2f}] {self.name}: Generated entity {self.entity_count} with properties {properties}")
            
            # Send to first processing stage if specified
            if self.first_stage:
                self.first_stage.add_item(entity)
            
            # Wait for next arrival
            inter_arrival_time = self.get_inter_arrival_time()
            
            # Make sure we don't go past working hours
            adjusted_time_minutes = self.env.now + self.start_minutes_offset
            current_hour = (adjusted_time_minutes % 1440) / 60
            end_hour = self.working_hours[1]
            hours_remaining = end_hour - current_hour
            
            if hours_remaining <= 0:
                # We're at or past end of working hours, stop generating for today
                # The next loop will handle waiting until next working time
                yield self.env.timeout(1)
            elif inter_arrival_time > (hours_remaining * 60):
                # Next arrival would be past working hours, stop generating for today
                yield self.env.timeout(hours_remaining * 60 + 1)
            else:
                yield self.env.timeout(inter_arrival_time)


# Example usage and testing
if __name__ == "__main__":
    # Define a simple test entity class
    class TestSlide:
        def __init__(self, id, arrival_time, is_pap=False, is_positive=False):
            self.id = id
            self.arrival_time = arrival_time
            self.is_pap = is_pap
            self.is_positive = is_positive
        
        def __repr__(self):
            return f"Slide({self.id}, Pap={self.is_pap}, Pos={self.is_positive})"
    
    # Create simulation environment
    env = simpy.Environment()
    
    # Example 1: Generate Pap smears Mon-Sat, 9-4, 5 per day with Poisson arrivals
    pap_generator = Entity_Generator(
        env=env,
        name='pap_arrivals',
        entity_class=TestSlide,
        working_days=[0, 1, 2, 3, 4, 5],  # Mon-Sat
        working_hours=(9, 16),  # 9 AM - 4 PM
        arrival_rate_per_day=5,
        arrival_distribution='poisson',
        entity_properties=lambda: {
            'is_pap': True,
            'is_positive': random.random() < 0.05  # 5% positive rate
        }
    )
    
    # Example 2: Generate non-Pap slides with constant arrivals
    non_pap_generator = Entity_Generator(
        env=env,
        name='non_pap_arrivals',
        entity_class=TestSlide,
        working_days=[0, 1, 2, 3, 4, 5],
        working_hours=(9, 16),
        arrival_rate_per_day=10,
        arrival_distribution='constant',
        entity_properties={'is_pap': False, 'is_positive': False}
    )
    
    # Run simulation for 3 days (3 * 24 * 60 minutes)
    print("Starting simulation...\n")
    env.run(until=3 * 1440)
    print(f"\nSimulation complete!")
    print(f"Pap slides generated: {pap_generator.entity_count}")
    print(f"Non-Pap slides generated: {non_pap_generator.entity_count}")
