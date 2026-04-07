"""
Generic entity classes for hospital simulation.
These classes represent different entities that flow through the hospital system.
"""

from datetime import datetime


class Generic_Entity(object):
    """
    A base class representing any entity in the hospital simulation system.
    This can be a slide, sample, patient, or any other object that moves through processes.
    """
    
    def __init__(self, id, entity_type, arrival_time=None, **properties):
        """
        Initialize a hospital entity.
        
        Parameters:
        -----------
        id : int or str
            Unique identifier for this entity
        entity_type : str
            Type of entity (e.g., 'cyto_slide', 'histo_sample', 'patient')
        arrival_time : float, optional
            Simulation time when entity arrived in the system
        **properties : dict
            Additional properties specific to the entity type
        """
        self.id = id
        self.entity_type = entity_type
        self.arrival_time = arrival_time
        
        # Store all additional properties
        for key, value in properties.items():
            setattr(self, key, value)
        
        # Timestamps for different process stages
        self.stage_times = {}
        
        # Entry and exit times
        self.entry_time = arrival_time  # Alias for arrival_time
        self.exit_time = None
    
    def record_stage_start(self, stage_name, time):
        """
        Record the start time of a processing stage.
        
        Parameters:
        -----------
        stage_name : str
            Name o the stage (e.g., 'fixation', 'staining', 'reporting')
        time : float
            Simulation time when the stage started
        """
        self.stage_times[f'{stage_name}_start'] = time
    
    def record_stage_end(self, stage_name, time):
        """
        Record the end time of a processing stage.
        
        Parameters:
        -----------
        stage_name : str
            Name of the stage
        time : float
            Simulation time when the stage ended
        """
        self.stage_times[f'{stage_name}_end'] = time
    
    def get_stage_duration(self, stage_name):
        """
        Calculate the duration of a specific stage.
        
        Parameters:
        -----------
        stage_name : str
            Name of the stage
        
        Returns:
        --------
        float or None : Duration in simulation time units, or None if stage not complete
        """
        start_key = f'{stage_name}_start'
        end_key = f'{stage_name}_end'
        
        if start_key in self.stage_times and end_key in self.stage_times:
            return self.stage_times[end_key] - self.stage_times[start_key]
        return None
    
    def get_waiting_time(self, previous_stage, next_stage):
        """
        Calculate the waiting time between two stages.
        Waiting time = start of next stage - end of previous stage
        
        Parameters:
        -----------
        previous_stage : str
            Name of the previous stage (e.g., 'fixation')
        next_stage : str
            Name of the next stage (e.g., 'staining')
        
        Returns:
        --------
        float or None : Waiting time in simulation time units, or None if stages not complete
        """
        previous_end_key = f'{previous_stage}_end'
        next_start_key = f'{next_stage}_start'
        
        if previous_end_key in self.stage_times and next_start_key in self.stage_times:
            return self.stage_times[next_start_key] - self.stage_times[previous_end_key]
        return None
    
    def get_total_time_in_system(self):
        """
        Calculate total time from entry to exit.
        
        Returns:
        --------
        float or None : Total time in system, or None if not yet exited
        """
        if self.exit_time is not None and self.entry_time is not None:
            return self.exit_time - self.entry_time
        return None
    
    def __repr__(self):
        """String representation of the entity."""
        return f"Hospital_Entity(id={self.id}, type={self.entity_type})"


class CytoSlide(Generic_Entity):
    """
    Represents a cytology slide.
    """
    
    def __init__(self, id, arrival_time=None, is_pap=False, is_positive=False, **kwargs):
        """
        Initialize a cytology slide.
        
        Parameters:
        -----------
        id : int or str
            Unique identifier
        arrival_time : float, optional
            Simulation time of arrival
        is_pap : bool
            Whether this is a Pap smear slide
        is_positive : bool
            Whether the slide is positive (only relevant for Pap smears)
        **kwargs : dict
            Additional properties
        """
        super().__init__(
            id=id,
            entity_type='cyto_slide',
            arrival_time=arrival_time,
            is_pap=is_pap,
            is_positive=is_positive if is_pap else None,
            **kwargs
        )
    
    def __repr__(self):
        if self.is_pap:
            status = 'Positive' if self.is_positive else 'Negative'
            return f"CytoSlide(id={self.id}, Pap={status})"
        return f"CytoSlide(id={self.id}, Non-Pap)"


class HistoSample(Generic_Entity):
    """
    Represents a histology sample/biopsy.
    """
    
    def __init__(self, id, arrival_time=None, size='small', is_cervical=False, 
                 is_positive=False, **kwargs):
        """
        Initialize a histology sample.
        
        Parameters:
        -----------
        id : int or str
            Unique identifier
        arrival_time : float, optional
            Simulation time of arrival
        size : str
            Size of the biopsy ('small', 'medium', 'large')
        is_cervical : bool
            Whether this is a cervical biopsy
        is_positive : bool
            Whether the sample is positive for disease
        **kwargs : dict
            Additional properties
        """
        super().__init__(
            id=id,
            entity_type='histo_sample',
            arrival_time=arrival_time,
            size=size,
            is_cervical=is_cervical,
            is_positive=is_positive,
            **kwargs
        )
    
    def __repr__(self):
        tissue = 'Cervical' if self.is_cervical else 'Non-Cervical'
        status = 'Positive' if self.is_positive else 'Negative'
        return f"HistoSample(id={self.id}, {tissue}, {self.size}, {status})"


class Patient(Generic_Entity):
    """
    Represents a patient in the hospital system.
    """
    
    def __init__(self, id, arrival_time=None, age=None, diagnosis=None, **kwargs):
        """
        Initialize a patient entity.
        
        Parameters:
        -----------
        id : int or str
            Unique patient identifier
        arrival_time : float, optional
            Simulation time of arrival
        age : int, optional
            Patient age
        diagnosis : str, optional
            Initial diagnosis or reason for visit
        **kwargs : dict
            Additional properties
        """
        super().__init__(
            id=id,
            entity_type='patient',
            arrival_time=arrival_time,
            age=age,
            diagnosis=diagnosis,
            **kwargs
        )
    
    def __repr__(self):
        return f"Patient(id={self.id}, age={self.age}, diagnosis={self.diagnosis})"


# Example usage and testing
if __name__ == "__main__":
    print("Testing Hospital_Entity classes\n")
    
    # Example 1: Create a Pap smear slide
    pap_slide = CytoSlide(
        id=1,
        arrival_time=0.5,
        is_pap=True,
        is_positive=True
    )
    print(f"Created: {pap_slide}")
    
    # Record some stage times
    pap_slide.record_stage_start('fixation', 0.5)
    pap_slide.record_stage_end('fixation', 0.52)
    pap_slide.record_stage_start('staining', 0.52)
    pap_slide.record_stage_end('staining', 0.56)
    pap_slide.record_stage_start('reporting', 0.56)
    pap_slide.record_stage_end('reporting', 0.58)
    pap_slide.exit_time = 0.58
    
    print(f"Fixation duration: {pap_slide.get_stage_duration('fixation'):.4f} days")
    print(f"Total time in system: {pap_slide.get_total_time_in_system():.4f} days")
    print(f"Stage times: {pap_slide.stage_times}\n")
    
    # Example 2: Create a histology sample
    histo_sample = HistoSample(
        id=101,
        arrival_time=1.0,
        size='medium',
        is_cervical=True,
        is_positive=False
    )
    print(f"Created: {histo_sample}")
    
    # Record some stages
    histo_sample.record_stage_start('grossing', 1.0)
    histo_sample.record_stage_end('grossing', 1.02)
    histo_sample.record_stage_start('fixation', 1.02)
    histo_sample.record_stage_end('fixation', 2.02)
    
    print(f"Grossing duration: {histo_sample.get_stage_duration('grossing'):.4f} days")
    print(f"Fixation duration: {histo_sample.get_stage_duration('fixation'):.4f} days\n")
    
    # Example 3: Create a patient
    patient = Patient(
        id='P001',
        arrival_time=0.3,
        age=35,
        diagnosis='Screening',
        risk_level='low'
    )
    print(f"Created: {patient}")
    print(f"Patient age: {patient.age}")
    print(f"Risk level: {patient.risk_level}")
    print(f"Arrival time: {patient.arrival_time}\n")
    
    # Example 4: Create a custom entity with arbitrary properties
    custom_entity = Generic_Entity(
        id='CUSTOM-1',
        entity_type='blood_sample',
        arrival_time=2.5,
        test_type='CBC',
        priority='urgent',
        collection_site='ER'
    )
    print(f"Created: {custom_entity}")
    print(f"Test type: {custom_entity.test_type}")
    print(f"Priority: {custom_entity.priority}")
    print(f"Collection site: {custom_entity.collection_site}\n")
    
    # Example 5: Create 10 cytoslides
    print("Creating 10 CytoSlides:")
    slides = []
    for i in range(10):
        slide = CytoSlide(
            id=i + 1,
            arrival_time=0.1 * i,
            is_pap=True,
            is_positive=(i % 5 == 0)  # Every 5th slide is positive
        )
        slides.append(slide)
        print(f"  {slide}")
    
    print(f"\nTotal slides created: {len(slides)}")
