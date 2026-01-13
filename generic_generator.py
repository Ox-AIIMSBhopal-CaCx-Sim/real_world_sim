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
                 arrival_rate_per_day=1, arrival_distribution='constant',
                 arrival_params=None, entity_properties=None):
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
        
        # Arrival parameters
        self.arrival_rate_per_day = arrival_rate_per_day
        self.arrival_distribution = arrival_distribution
        self.arrival_params = arrival_params or {}
        
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
        # Add 0.375 (9 hours) to align simulation time 0 with 9 AM on Monday
        adjusted_time = self.env.now + (9/24)
        current_day = int(adjusted_time) % 7
        
        # Calculate current hour of day (0-24)
        current_hour = (adjusted_time % 1) * 24
        
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
        # Add offset to align with 9 AM start
        adjusted_time = self.env.now + (9/24)
        current_day = int(adjusted_time) % 7
        current_hour = (adjusted_time % 1) * 24
        
        start_hour, end_hour = self.working_hours
        
        # If we're in a working day but after hours, go to next working day at start_hour
        if current_day in self.working_days and current_hour >= end_hour:
            # Find next working day
            days_ahead = 1
            next_day = (current_day + days_ahead) % 7
            while next_day not in self.working_days:
                days_ahead += 1
                next_day = (current_day + days_ahead) % 7
            
            hours_until_next = (24 - current_hour) + (days_ahead - 1) * 24 + start_hour
            return hours_until_next / 24
        
        # If we're in a working day but before hours, wait until start_hour today
        if current_day in self.working_days and current_hour < start_hour:
            return (start_hour - current_hour) / 24
        
        # If we're on a non-working day, find the next working day
        if current_day not in self.working_days:
            days_ahead = 1
            next_day = (current_day + days_ahead) % 7
            while next_day not in self.working_days:
                days_ahead += 1
                next_day = (current_day + days_ahead) % 7
            
            hours_until_next = (24 - current_hour) + (days_ahead - 1) * 24 + start_hour
            return hours_until_next / 24
        
        return 0
    
    def get_inter_arrival_time(self):
        """
        Calculate the time between arrivals based on the specified distribution.
        
        Returns:
        --------
        float : Inter-arrival time in days
        """
        if self.arrival_distribution == 'constant':
            # Evenly spaced arrivals throughout the day
            working_hours_per_day = self.working_hours[1] - self.working_hours[0]
            inter_arrival_hours = working_hours_per_day / self.arrival_rate_per_day
            return inter_arrival_hours / 24
        
        elif self.arrival_distribution == 'poisson':
            # Exponential inter-arrival times (Poisson process)
            working_hours_per_day = self.working_hours[1] - self.working_hours[0]
            rate = self.arrival_rate_per_day / (working_hours_per_day / 24)
            inter_arrival_days = np.random.exponential(1.0 / rate)
            return inter_arrival_days
        
        elif self.arrival_distribution == 'uniform':
            # Uniform distribution
            min_time = self.arrival_params.get('min', 0.5 / 24)  # 30 minutes default
            max_time = self.arrival_params.get('max', 2 / 24)  # 2 hours default
            return np.random.uniform(min_time, max_time)
        
        elif self.arrival_distribution == 'exponential':
            # Exponential with custom rate
            rate = self.arrival_params.get('rate', self.arrival_rate_per_day)
            return np.random.exponential(1.0 / rate)
        
        else:
            # Default to constant
            working_hours_per_day = self.working_hours[1] - self.working_hours[0]
            return (working_hours_per_day / self.arrival_rate_per_day) / 24
    
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
            adjusted_time = self.env.now + (9/24)
            current_hour = (adjusted_time % 1) * 24
            end_hour = self.working_hours[1]
            hours_remaining = end_hour - current_hour
            
            if hours_remaining <= 0:
                # We're at or past end of working hours, stop generating for today
                # The next loop will handle waiting until next working time
                yield self.env.timeout(0.01)
            elif inter_arrival_time > (hours_remaining / 24):
                # Next arrival would be past working hours, stop generating for today
                yield self.env.timeout(hours_remaining / 24 + 0.01)
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
    
    # Run simulation for 3 days
    print("Starting simulation...\n")
    env.run(until=3)
    print(f"\nSimulation complete!")
    print(f"Pap slides generated: {pap_generator.entity_count}")
    print(f"Non-Pap slides generated: {non_pap_generator.entity_count}")
