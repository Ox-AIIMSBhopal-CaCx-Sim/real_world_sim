"""
Resource Availability Management for Hospital Simulation
This module provides functionality to manage staff schedules and resource availability
based on time constraints (working hours, shifts, days off, etc.)
"""

import simpy
from datetime import datetime, time, timedelta
from typing import List, Tuple, Dict, Optional, Union


class TimeSlot:
    """
    Represents a time slot during which a resource is available.
    """
    
    def __init__(self, start_time: time, end_time: time, days_of_week: Optional[List[int]] = None):
        """
        Initialize a time slot.
        
        Parameters:
        -----------
        start_time : time
            Start time of availability (e.g., time(9, 0) for 9:00 AM)
        end_time : time
            End time of availability (e.g., time(17, 0) for 5:00 PM)
        days_of_week : List[int], optional
            Days of week when this slot is active (0=Monday, 6=Sunday)
            If None, applies to all days
        """
        self.start_time = start_time
        self.end_time = end_time
        self.days_of_week = days_of_week if days_of_week is not None else list(range(7))
    
    def is_available_at(self, dt: datetime) -> bool:
        """
        Check if the resource is available at a given datetime.
        
        Parameters:
        -----------
        dt : datetime
            The datetime to check
        
        Returns:
        --------
        bool : True if available, False otherwise
        """
        # Check day of week (0=Monday, 6=Sunday)
        if dt.weekday() not in self.days_of_week:
            return False
        
        # Check time of day
        current_time = dt.time()
        
        # Handle time slots that cross midnight
        if self.start_time <= self.end_time:
            return self.start_time <= current_time < self.end_time
        else:
            # Time slot crosses midnight (e.g., 22:00 to 06:00)
            return current_time >= self.start_time or current_time < self.end_time
    
    def __repr__(self):
        days_str = ', '.join(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][d] 
                             for d in sorted(self.days_of_week))
        return f"TimeSlot({self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}, {days_str})"


class Schedule:
    """
    Represents a schedule composed of multiple time slots.
    """
    
    def __init__(self, name: str, time_slots: Optional[List[TimeSlot]] = None):
        """
        Initialize a schedule.
        
        Parameters:
        -----------
        name : str
            Name of the schedule (e.g., "Day Shift", "Dr. Smith's Schedule")
        time_slots : List[TimeSlot], optional
            List of time slots when the resource is available
        """
        self.name = name
        self.time_slots = time_slots if time_slots is not None else []
    
    def add_time_slot(self, start_time: time, end_time: time, 
                      days_of_week: Optional[List[int]] = None):
        """
        Add a time slot to the schedule.
        
        Parameters:
        -----------
        start_time : time
            Start time of availability
        end_time : time
            End time of availability
        days_of_week : List[int], optional
            Days of week when this slot is active (0=Monday, 6=Sunday)
        """
        self.time_slots.append(TimeSlot(start_time, end_time, days_of_week))
    
    def is_available_at(self, dt: datetime) -> bool:
        """
        Check if the resource is available at a given datetime.
        
        Parameters:
        -----------
        dt : datetime
            The datetime to check
        
        Returns:
        --------
        bool : True if available in any time slot, False otherwise
        """
        return any(slot.is_available_at(dt) for slot in self.time_slots)
    
    def get_next_available_time(self, current_dt: datetime, max_days_ahead: int = 7) -> Optional[datetime]:
        """
        Find the next time the resource will be available.
        
        Parameters:
        -----------
        current_dt : datetime
            Current datetime
        max_days_ahead : int
            Maximum number of days to search ahead
        
        Returns:
        --------
        datetime or None : Next available datetime, or None if not found
        """
        # Check every minute for the next max_days_ahead days
        check_dt = current_dt
        end_dt = current_dt + timedelta(days=max_days_ahead)
        
        while check_dt < end_dt:
            if self.is_available_at(check_dt):
                return check_dt
            check_dt += timedelta(minutes=1)
        
        return None
    
    def __repr__(self):
        slots_str = '\n  '.join(str(slot) for slot in self.time_slots)
        return f"Schedule('{self.name}')\n  {slots_str}"


class ScheduledResource:
    """
    A SimPy resource that is only available during specified time slots.
    This wraps a standard SimPy Resource and adds schedule-based availability.
    """
    
    def __init__(self, env: simpy.Environment, capacity: int, schedule: Schedule,
                 simulation_start_datetime: datetime, name: str = "ScheduledResource"):
        """
        Initialize a scheduled resource.
        
        Parameters:
        -----------
        env : simpy.Environment
            The SimPy environment
        capacity : int
            Number of resources (e.g., number of staff members)
        schedule : Schedule
            The schedule defining when the resource is available
        simulation_start_datetime : datetime
            The real-world datetime corresponding to simulation time 0
        name : str
            Name of the resource for logging/debugging
        """
        self.env = env
        self.capacity = capacity
        self.schedule = schedule
        self.simulation_start_datetime = simulation_start_datetime
        self.name = name
        
        # Create the underlying SimPy resource
        self._resource = simpy.Resource(env, capacity=capacity)
        
        # Track original capacity for restore
        self._original_capacity = capacity
        
        # Start the availability monitoring process
        self.env.process(self._monitor_availability())
    
    def _sim_time_to_datetime(self, sim_time: float) -> datetime:
        """
        Convert simulation time (in days) to real datetime.
        
        Parameters:
        -----------
        sim_time : float
            Simulation time in days
        
        Returns:
        --------
        datetime : Corresponding real-world datetime
        """
        return self.simulation_start_datetime + timedelta(days=sim_time)
    
    def _monitor_availability(self):
        """
        Background process that monitors and enforces schedule availability.
        This runs continuously throughout the simulation.
        """
        while True:
            current_dt = self._sim_time_to_datetime(self.env.now)
            
            if self.schedule.is_available_at(current_dt):
                # Resource should be available - ensure capacity is set
                if self._resource.capacity != self._original_capacity:
                    self._resource._capacity = self._original_capacity
            else:
                # Resource should be unavailable - set capacity to 0
                if self._resource.capacity != 0:
                    self._resource._capacity = 0
            
            # Check availability status every minute (1/1440 days)
            yield self.env.timeout(1/1440)
    
    def request(self, priority: Optional[int] = None):
        """
        Request access to the resource. This will automatically wait
        if the resource is not currently available according to its schedule.
        
        Parameters:
        -----------
        priority : int, optional
            Priority for the request (not used with standard Resource)
        
        Returns:
        --------
        simpy.Request : Request object
        """
        return self._resource.request()
    
    def release(self, request):
        """
        Release a previously acquired resource.
        
        Parameters:
        -----------
        request : simpy.Request
            The request object obtained from request()
        """
        return self._resource.release(request)
    
    @property
    def count(self):
        """Number of resources currently in use."""
        return self._resource.count
    
    @property
    def queue(self):
        """Queue of pending requests."""
        return self._resource.queue
    
    def is_available_now(self) -> bool:
        """
        Check if the resource is available at the current simulation time.
        
        Returns:
        --------
        bool : True if available, False otherwise
        """
        current_dt = self._sim_time_to_datetime(self.env.now)
        return self.schedule.is_available_at(current_dt)
    
    def __repr__(self):
        return f"ScheduledResource('{self.name}', capacity={self.capacity}, available={self.is_available_now()})"


class ScheduledPriorityResource(ScheduledResource):
    """
    A SimPy PriorityResource that is only available during specified time slots.
    """
    
    def __init__(self, env: simpy.Environment, capacity: int, schedule: Schedule,
                 simulation_start_datetime: datetime, name: str = "ScheduledPriorityResource"):
        """Initialize a scheduled priority resource."""
        # Don't call super().__init__ to avoid creating standard Resource
        self.env = env
        self.capacity = capacity
        self.schedule = schedule
        self.simulation_start_datetime = simulation_start_datetime
        self.name = name
        
        # Create PriorityResource instead of standard Resource
        self._resource = simpy.PriorityResource(env, capacity=capacity)
        self._original_capacity = capacity
        
        # Start monitoring
        self.env.process(self._monitor_availability())
    
    def request(self, priority: int = 0):
        """
        Request access to the resource with a given priority.
        
        Parameters:
        -----------
        priority : int
            Priority for the request (lower values = higher priority)
        
        Returns:
        --------
        simpy.PriorityRequest : Request object
        """
        return self._resource.request(priority=priority)


# Predefined common schedules
def create_standard_weekday_schedule(start_hour: int = 9, end_hour: int = 17, 
                                     name: str = "Weekday 9-5") -> Schedule:
    """
    Create a standard Monday-Friday schedule.
    
    Parameters:
    -----------
    start_hour : int
        Starting hour (24-hour format)
    end_hour : int
        Ending hour (24-hour format)
    name : str
        Name for the schedule
    
    Returns:
    --------
    Schedule : A schedule for Monday-Friday
    """
    schedule = Schedule(name)
    schedule.add_time_slot(
        start_time=time(start_hour, 0),
        end_time=time(end_hour, 0),
        days_of_week=[0, 1, 2, 3, 4]  # Monday-Friday
    )
    return schedule


def create_24_7_schedule(name: str = "24/7") -> Schedule:
    """
    Create a 24/7 schedule (always available).
    
    Parameters:
    -----------
    name : str
        Name for the schedule
    
    Returns:
    --------
    Schedule : A schedule that is always available
    """
    schedule = Schedule(name)
    schedule.add_time_slot(
        start_time=time(0, 0),
        end_time=time(23, 59),
        days_of_week=list(range(7))
    )
    return schedule


def create_shift_schedule(start_hour: int, end_hour: int, 
                         days_of_week: List[int],
                         name: str = "Shift") -> Schedule:
    """
    Create a custom shift schedule.
    
    Parameters:
    -----------
    start_hour : int
        Starting hour (24-hour format)
    end_hour : int
        Ending hour (24-hour format)
    days_of_week : List[int]
        Days of week (0=Monday, 6=Sunday)
    name : str
        Name for the schedule
    
    Returns:
    --------
    Schedule : A custom shift schedule
    """
    schedule = Schedule(name)
    schedule.add_time_slot(
        start_time=time(start_hour, 0),
        end_time=time(end_hour, 0),
        days_of_week=days_of_week
    )
    return schedule


def create_part_time_schedule(days_and_hours: Dict[int, Tuple[int, int]],
                              name: str = "Part-time") -> Schedule:
    """
    Create a part-time schedule with different hours on different days.
    
    Parameters:
    -----------
    days_and_hours : Dict[int, Tuple[int, int]]
        Dictionary mapping day of week to (start_hour, end_hour)
        Example: {0: (9, 13), 2: (9, 13), 4: (9, 13)} for Mon/Wed/Fri mornings
    name : str
        Name for the schedule
    
    Returns:
    --------
    Schedule : A part-time schedule
    """
    schedule = Schedule(name)
    for day, (start_hour, end_hour) in days_and_hours.items():
        schedule.add_time_slot(
            start_time=time(start_hour, 0),
            end_time=time(end_hour, 0),
            days_of_week=[day]
        )
    return schedule


# Example usage
if __name__ == "__main__":
    # Example 1: Create a standard weekday schedule
    weekday_schedule = create_standard_weekday_schedule(9, 17, "Standard Weekday")
    print(weekday_schedule)
    print()
    
    # Example 2: Create a part-time schedule
    part_time = create_part_time_schedule(
        {0: (9, 13), 2: (9, 13), 4: (9, 13)},  # Mon/Wed/Fri mornings
        "Part-time Staff"
    )
    print(part_time)
    print()
    
    # Example 3: Test availability
    test_dt = datetime(2025, 5, 5, 10, 30)  # Monday at 10:30 AM
    print(f"Testing {test_dt.strftime('%A %H:%M')}")
    print(f"Available on weekday schedule: {weekday_schedule.is_available_at(test_dt)}")
    print(f"Available on part-time schedule: {part_time.is_available_at(test_dt)}")
    print()
    
    # Example 4: Test with SimPy
    print("Running SimPy simulation example...")
    env = simpy.Environment()
    sim_start = datetime(2025, 5, 1, 9, 0)
    
    # Create a scheduled resource
    scheduled_staff = ScheduledResource(
        env=env,
        capacity=2,
        schedule=weekday_schedule,
        simulation_start_datetime=sim_start,
        name="Cytotechnicians"
    )
    
    def process_item(env, item_id, resource):
        arrival_time = env.now
        print(f"Item {item_id} arrives at sim time {arrival_time:.2f}")
        
        with resource.request() as req:
            yield req
            start_time = env.now
            wait_time = start_time - arrival_time
            print(f"  Item {item_id} starts processing at {start_time:.2f} (waited {wait_time:.2f} days)")
            
            # Process for 30 minutes (0.0208 days)
            yield env.timeout(30/1440)
            
            print(f"  Item {item_id} completes at {env.now:.2f}")
    
    # Generate some test items
    for i in range(5):
        env.process(process_item(env, i, scheduled_staff))
    
    # Run simulation for 2 days
    env.run(until=2)
    print("\nSimulation complete!")
