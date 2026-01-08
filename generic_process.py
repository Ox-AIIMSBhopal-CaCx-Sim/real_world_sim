import simpy
import numpy as np
import random


class Lab_Process:
    """
    A generic laboratory process stage that can be chained together to create a pipeline.
    Each instance represents a single stage in the processing workflow.
    """
    
    def __init__(self, env, name, resource=None, batch_size=1, 
                 duration_minutes=0, duration_type='constant', 
                 distribution_params=None, wait_for_batch=False):
        """
        Initialize a lab process stage.
        Parameters:
        -----------
        env : simpy.Environment
            The SimPy environment
        name : str
            Name of this process stage (e.g., 'fixation', 'staining', 'reporting')
        resource : simpy.Resource, optional
            The resource required for this process (e.g., technician, equipment)
        batch_size : int
            Maximum number of items to process together in a batch
        duration_minutes : float
            Base processing duration in minutes
        duration_type : str
            Type of duration distribution ('constant', 'lognormal', 'uniform', 'exponential')
        distribution_params : dict, optional
            Parameters for the duration distribution (e.g., {'mean': 3.4, 'sd': 0.4})
        wait_for_batch : bool
            If True, wait until batch_size items are available before processing
        """
        self.env = env
        self.name = name
        self.resource = resource
        self.batch_size = batch_size
        self.duration_minutes = duration_minutes
        self.duration_type = duration_type
        self.distribution_params = distribution_params or {}
        self.wait_for_batch = wait_for_batch
        
        # Queue for items waiting to be processed at this stage
        self.queue = []
        
        # Next stage in the pipeline (set via chain method)
        self.next_stage = None
        
        # Start the process automatically
        self.process = env.process(self.run())
    
    def get_duration(self):
        """
        Calculate processing duration based on the specified distribution type.
        
        Returns:
        --------
        float : Duration in days
        """
        if self.duration_type == 'constant':
            minutes = self.duration_minutes
        
        elif self.duration_type == 'lognormal':
            mean = self.distribution_params.get('mean', 0)
            sd = self.distribution_params.get('sd', 1)
            minutes = np.random.lognormal(mean, sd)
        
        elif self.duration_type == 'uniform':
            min_val = self.distribution_params.get('min', self.duration_minutes)
            max_val = self.distribution_params.get('max', self.duration_minutes)
            minutes = np.random.uniform(min_val, max_val)
        
        elif self.duration_type == 'exponential':
            rate = self.distribution_params.get('rate', 1.0)
            minutes = np.random.exponential(1.0 / rate)
        
        else:
            minutes = self.duration_minutes
        
        # Convert minutes to days for SimPy
        return minutes / (60 * 24)
    
    def run(self):
        """
        Main SimPy process that continuously processes items from the queue.
        This method runs as a generator and is automatically started.
        """
        while True:
            # Wait if queue is empty
            if len(self.queue) == 0:
                yield self.env.timeout(0.01)  # Small delay to avoid busy waiting
                continue
            
            # If wait_for_batch is True, wait until we have enough items
            if self.wait_for_batch and len(self.queue) < self.batch_size:
                yield self.env.timeout(0.01)
                continue
            
            # Collect a batch of items (up to batch_size)
            batch = []
            for _ in range(min(self.batch_size, len(self.queue))):
                if len(self.queue) > 0:
                    batch.append(self.queue.pop(0))
            
            if len(batch) == 0:
                continue
            
            # Process with or without resource
            if self.resource:
                # Request the resource
                with self.resource.request() as request:
                    yield request
                    
                    # Record start time for each item in batch
                    for item in batch:
                        self._record_start_time(item)
                    
                    print(f"[{self.env.now:.2f}] {self.name}: Started processing batch of {len(batch)} items")
                    
                    # Process for the specified duration
                    duration = self.get_duration()
                    yield self.env.timeout(duration)
                    
                    # Record end time and move to next stage
                    for item in batch:
                        self._record_end_time(item)
                        self._move_to_next_stage(item)
                    
                    print(f"[{self.env.now:.2f}] {self.name}: Completed batch of {len(batch)} items")
            
            else:
                # No resource required (e.g., passive waiting like fixation time)
                for item in batch:
                    self._record_start_time(item)
                
                print(f"[{self.env.now:.2f}] {self.name}: Started passive processing of {len(batch)} items")
                
                duration = self.get_duration()
                yield self.env.timeout(duration)
                
                for item in batch:
                    self._record_end_time(item)
                    self._move_to_next_stage(item)
                
                print(f"[{self.env.now:.2f}] {self.name}: Completed passive processing of {len(batch)} items")
    
    def _record_start_time(self, item):
        """Record the start time of processing for an item."""
        if not hasattr(item, 'stage_times'):
            item.stage_times = {}
        item.stage_times[f'{self.name}_start'] = self.env.now
    
    def _record_end_time(self, item):
        """Record the end time of processing for an item."""
        item.stage_times[f'{self.name}_end'] = self.env.now
    
    def _move_to_next_stage(self, item):
        """Move an item to the next stage in the pipeline."""
        if self.next_stage:
            self.next_stage.queue.append(item)
        else:
            # This is the final stage - mark item as complete
            if not hasattr(item, 'exit_time'):
                item.exit_time = self.env.now
    
    def chain(self, next_stage):
        """
        Chain this process to the next stage in the pipeline.
        
        Parameters:
        -----------
        next_stage : Lab_Process
            The next process stage in the pipeline
        
        Returns:
        --------
        Lab_Process : The next_stage (for method chaining)
        
        Example:
        --------
        stage1.chain(stage2).chain(stage3)
        """
        self.next_stage = next_stage
        return next_stage
    
    def add_item(self, item):
        """
        Add an item to this process stage's queue.
        
        Parameters:
        -----------
        item : object
            The item to process (e.g., a CytoSlide or HistoSample)
        """
        self.queue.append(item)


# Example usage and testing
if __name__ == "__main__":
    # Create a simple test environment
    env = simpy.Environment()
    
    # Create some resources
    technician = simpy.Resource(env, capacity=2)
    staining_machine = simpy.Resource(env, capacity=1)
    pathologist = simpy.Resource(env, capacity=1)
    
    # Define a simple test item class
    class TestSlide:
        def __init__(self, id):
            self.id = id
            self.stage_times = {}
    
    # Create a pipeline: fixation → staining → reporting
    fixation = Lab_Process(
        env=env,
        name='fixation',
        resource=technician,
        batch_size=1,
        duration_minutes=30,
        duration_type='constant'
    )
    
    staining = Lab_Process(
        env=env,
        name='staining',
        resource=staining_machine,
        batch_size=5,
        duration_minutes=60,
        duration_type='constant',
        wait_for_batch=False
    )
    
    reporting = Lab_Process(
        env=env,
        name='reporting',
        resource=pathologist,
        batch_size=1,
        duration_minutes=30,
        duration_type='lognormal',
        distribution_params={'mean': 3.4, 'sd': 0.4}
    )
    
    # Chain the stages together
    fixation.chain(staining).chain(reporting)
    
    # Sample generator
    def generate_samples(env, first_stage):
        for i in range(10):
            slide = TestSlide(id=i+1)
            first_stage.add_item(slide)
            print(f"[{env.now:.2f}] Generated slide {slide.id}")
            yield env.timeout(0.1)  # Arrival rate
    
    # Start the generator
    env.process(generate_samples(env, fixation))
    
    # Run simulation
    print("Starting simulation...\n")
    env.run(until=10)
    print("\nSimulation complete!")
