"""
Resource Availability Management for Hospital Simulation
This module provides functionality to manage staff schedules and resource availability
based on time constraints (working hours, shifts, days off, etc.)
"""

import simpy
from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union


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


class ScheduledResource():
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
        
        # We use a PriorityResource so the shift-monitor can 'jump the line'
        # during off-hours to block items from processing.
        self._resource = simpy.PriorityResource(env, capacity=capacity)
        
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
        return self.simulation_start_datetime + timedelta(minutes=sim_time)
    
    def _monitor_availability(self):
        """
        Background process that monitors and enforces schedule availability.
        Uses a 'Blocking Request' to prevent usage during off-hours.
        """
        blocker_requests = []
        
        while True:
            current_dt = self._sim_time_to_datetime(self.env.now)
            is_open = self.schedule.is_available_at(current_dt)
            
            if not is_open and not blocker_requests:
                # Shift just CLOSED: Request all units to block the resource
                # Priority -1 is higher than the default (0 or 1)
                for _ in range(self._original_capacity):
                    req = self._resource.request(priority=-1)
                    blocker_requests.append(req)
                # Wait for all units to be captured (drains the resource)
                # Note: this might take time if items are currently processing
                
            elif is_open and blocker_requests:
                # Shift just OPENED: Release all blocking units
                for req in blocker_requests:
                    self._resource.release(req)
                blocker_requests = []
            
            # Check for shift changes every minute
            yield self.env.timeout(1)
    
    def request(self, priority: int = 0):
        """
        Request access to the resource. This will automatically wait
        if the resource is not currently available according to its schedule.
        
        Parameters:
        -----------
        priority : int, optional
            Priority for the request (lower number = higher priority)
        
        Returns:
        --------
        simpy.Request : Request object
        """
        return self._resource.request(priority=priority)
    
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


def create_schedule_from_params(schedule_name: str, schedule_params: Dict[str, Any]) -> Schedule:
    """Build a Schedule from YAML-style slot dictionaries."""
    schedule = Schedule(schedule_name)
    for _slot_name, slot_data in schedule_params.items():
        days = slot_data["days"]
        start_hour, end_hour = slot_data["hours"]
        schedule.add_time_slot(
            start_time=time(start_hour, 0),
            end_time=time(end_hour, 0),
            days_of_week=days,
        )
    return schedule


def create_task_schedules_from_params(
    task_windows: Dict[str, Dict[str, Any]],
) -> Dict[str, Schedule]:
    """Build per-task schedules from a YAML ``task_windows`` mapping."""
    return {
        task: create_schedule_from_params(f"{task.title()} Schedule", slots)
        for task, slots in task_windows.items()
    }


def union_schedules(name: str, schedules: Dict[str, Schedule]) -> Schedule:
    """Combine task schedules into one overall on-shift schedule (union of slots)."""
    united = Schedule(name)
    for sched in schedules.values():
        united.time_slots.extend(sched.time_slots)
    return united


class TaskScheduledResource(ScheduledResource):
    """
    Scheduled resource with task-specific time windows on a single capacity pool.

  Each task (e.g. ``grossing``, ``screening``) has its own Schedule. Processes must
    call ``wait_until_can_start`` before requesting so Option A (no new work if
    insufficient time remains in the window) is enforced.
    """

    def __init__(
        self,
        env: simpy.Environment,
        capacity: int,
        task_schedules: Dict[str, Schedule],
        simulation_start_datetime: datetime,
        name: str = "TaskScheduledResource",
    ):
        self.task_schedules = task_schedules
        overall = union_schedules(f"{name} Overall", task_schedules)
        super().__init__(
            env=env,
            capacity=capacity,
            schedule=overall,
            simulation_start_datetime=simulation_start_datetime,
            name=name,
        )

    def _minutes_remaining_in_task_window(self, task: str, dt: datetime) -> float:
        """Minutes until the end of the active task window containing ``dt``."""
        schedule = self.task_schedules[task]
        for slot in schedule.time_slots:
            if slot.is_available_at(dt):
                end_minutes = slot.end_time.hour * 60 + slot.end_time.minute
                current_minutes = dt.hour * 60 + dt.minute + dt.second / 60.0
                return max(0.0, end_minutes - current_minutes)
        return 0.0

    def _minutes_until_can_start(self, task: str, dt: datetime, required_minutes: float) -> float:
        """Minutes from ``dt`` until the task window has at least ``required_minutes`` left."""
        schedule = self.task_schedules[task]
        for day_offset in range(8):
            check_date = dt.date() + timedelta(days=day_offset)
            for slot in schedule.time_slots:
                if check_date.weekday() not in slot.days_of_week:
                    continue
                window_start = datetime.combine(check_date, slot.start_time)
                window_end = datetime.combine(check_date, slot.end_time)
                candidate = max(dt, window_start)
                if candidate >= window_end:
                    continue
                remaining = (window_end - candidate).total_seconds() / 60.0
                if remaining >= required_minutes:
                    return max(0.0, (candidate - dt).total_seconds() / 60.0)
        return 1440.0

    def is_task_available_now(self, task: str) -> bool:
        current_dt = self._sim_time_to_datetime(self.env.now)
        return self.task_schedules[task].is_available_at(current_dt)

    def wait_until_can_start(self, task: str, required_minutes: float):
        """
        Wait until ``task`` is active and at least ``required_minutes`` remain
        in that window (Option A: no new starts near cutoff).
        """
        if task not in self.task_schedules:
            raise KeyError(f"Unknown task {task!r} for {self.name}")

        while True:
            now_dt = self._sim_time_to_datetime(self.env.now)
            schedule = self.task_schedules[task]
            if schedule.is_available_at(now_dt):
                remaining = self._minutes_remaining_in_task_window(task, now_dt)
                if remaining >= required_minutes:
                    return
            wait_minutes = self._minutes_until_can_start(task, now_dt, required_minutes)
            yield self.env.timeout(max(1.0, wait_minutes))


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
    def run_example():
        """
        Integrates manual_generic_process with ScheduledResource to test
        shift-aware batch processing.
        """
        import simpy
        from datetime import datetime, timedelta
        from manual_generic_process import manual_generic_process
        
        # 1. Define a 9:00-17:00 weekday schedule (Mon-Fri)
        weekday_schedule = Schedule("Standard Weekday")
        from datetime import time
        weekday_schedule.add_time_slot(time(9, 0), time(17, 0), days_of_week=[0, 1, 2, 3, 4])
        
        # 2. Simulation starts at 2:00 AM on a Monday
        base_date = datetime(2024, 1, 1, 2, 0)
        
        def to_date_str(sim_time_mins):
            dt = base_date + timedelta(minutes=sim_time_mins)
            return dt.strftime("%d/%m/%y %H:%M")

        env = simpy.Environment()
        
        # 3. Create a Scheduled Resource (2 Technicians)
        technicians = ScheduledResource(
            env=env,
            capacity=2,
            schedule=weekday_schedule,
            simulation_start_datetime=base_date,
            name="Technicians"
        )
        
        # 4. Create the Cutting Process Stage (Batched in pairs)
        cutting_stage = manual_generic_process(
            env=env,
            process_name="cutting",
            resources_requested=[technicians],
            service_time=30,
            service_time_dist="constant",
            service_time_dist_params={},
            is_batched=True,
            batch_size=2
        )
        
        class MockMesh:
            def __init__(self, name):
                self.id = name

        # 5. Meshes arrive outside shift hours (02:00 AM)
        print("\n--- Starting Integrated Shift + Batch Test ---")
        for i in range(4):
            mesh = MockMesh(f"WM-B{i+1}")
            print(f"[{to_date_str(env.now)}] {mesh.id} arrived (Facility Closed).")
            # Items wait for (1) Batch to fill and (2) Shift to open
            env.process(cutting_stage.run_batch(mesh))
            
        env.run(until=1440) # Run for 1 day
        print("\nIntegrated Test Complete!")
    
    run_example()
