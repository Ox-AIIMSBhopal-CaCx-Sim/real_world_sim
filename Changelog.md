# Changelog

## v3.0 - Resource Scheduling & Container Resources

### 17 February 2026

### Major Features Added

#### 1. Staff Scheduling & Time-Based Availability (`resource_availability.py`)

**Core Classes:**

- **`TimeSlot`**: Defines specific time periods when resources are available
  - Configurable start/end times (e.g., 9:00 AM - 5:00 PM)
  - Day-of-week specification (0=Monday, 6=Sunday)
  - Handles time slots crossing midnight
  - Method: `is_available_at(datetime)` checks availability

- **`Schedule`**: Collection of multiple time slots for complex scheduling
  - Supports multiple shifts per day
  - Different schedules for different days (e.g., weekday vs. weekend)
  - Methods: `add_time_slot()`, `is_available_at()`, `get_next_available_time()`

- **`ScheduledResource`**: SimPy resource with time-based availability
  - Wraps standard `simpy.Resource` with schedule enforcement
  - Automatically sets capacity to 0 outside scheduled hours
  - Background process monitors availability every minute
  - Entities automatically queue when resources unavailable
  - Seamless integration: use `.request()` and `.release()` as normal

- **`ScheduledPriorityResource`**: Priority-based version with scheduling

**Helper Functions:**

- `create_standard_weekday_schedule()`: Monday-Friday, configurable hours
- `create_24_7_schedule()`: Always available
- `create_shift_schedule()`: Custom shifts with specific days
- `create_part_time_schedule()`: Different hours on different days

**Key Benefits:**

- Staff only consume resources during their scheduled working hours
- Realistic modeling of weekday-only operations
- Automatic handling of weekend and after-hours delays
- No code changes needed in existing process logic

#### 2. Container Resources for Consumables (`cyto_sim_v2.0.py`)

**`ReagentContainer` Class:**

- Built on `simpy.Container` for continuous resource tracking
- Tracks initial amount, current level, and usage over time
- Methods:
  - `use_reagent(amount, slide_id)`: Depletes reagent and logs usage
  - `level`: Property returning current reagent level
  - `get_usage_dataframe()`: Exports usage log to pandas DataFrame

**Usage Logging:**

- Records for each reagent use:
  - Simulation time and real datetime
  - Slide ID consuming the reagent
  - Amount used
  - Remaining amount after use
- Enables detailed consumption analysis and restock planning

**Implementation in v2.0 Simulation:**

- Fixation reagent: 1000 ml initial, 10 ml per slide
- Pap stain reagent: 1000 ml initial, 10 ml per slide
- Automatic depletion during processing
- Exported to separate CSV files for analysis

#### 3. Multiple Resources Per Process (`cyto_sim_v2.0.py`)

**Multi-Resource Process Design:**

- **Fixation**: Container resource only (reagent)
  - No staff required (automated process)
  - Uses 10 ml fixation reagent per slide
- **Staining**: Staff + container resources
  - Requires: 1 cytotechnician (scheduled resource)
  - Uses: 10 ml stain reagent per slide (container)
  - Batch size: 10 slides
  - Both resource types managed simultaneously
- **Reporting**: Staff + equipment resources
  - Requires: 1 cytopathologist (scheduled resource) + 1 microscope
  - Uses `with` statement for multiple resources: `with staff.request() as req1: with equipment.request() as req2:`

**Resource Request Patterns:**

```python
# Container resource
yield reagent_container.use_reagent(amount, slide_id)

# Multiple resources simultaneously
with resource1.request() as req1:
    with resource2.request() as req2:
        yield req1 & req2
        # Process here
```



## v2.0 - Generic Classes & Enhanced Pipeline

### Major Architecture Changes

#### Generic Classes Created

- **`Hospital_Entity`** base class in `generic_entity.py`:
  - Flexible base class for any entity type (slides, samples, patients)
  - Automatic timestamp tracking via `stage_times` dictionary
  - Built-in methods: `get_stage_duration()`, `get_waiting_time()`, `get_total_time_in_system()`
  - Pre-built subclasses: `CytoSlide`, `HistoSample`, `Patient`
  - Support for custom properties via `**kwargs`

- **`Lab_Process`** class in `generic_process.py`:
  - Generic SimPy process for any lab stage
  - Configurable batch processing with `wait_for_batch` option
  - Multiple duration distributions: constant, lognormal, uniform, exponential
  - Resource-aware (optional resource requirement)
  - Chainable via `.chain()` method for pipeline construction
  - Automatic stage time recording

- **`Batch_Dependent_Process`** extension:
  - Extends `Lab_Process` for stage dependencies
  - Waits for previous stage queue to empty before processing
  - Used for reporting that waits until all staining is complete

- **`Entity_Generator`** class in `generic_generator.py`:
  - Configurable working days (Mon-Sat default)
  - Configurable working hours (9 AM - 4 PM default)
  - Multiple arrival distributions: constant, Poisson, uniform, exponential
  - Dynamic entity properties via callable functions
  - Automatic time offset handling (9 AM = simulation time 0)
  - Prevents infinite loops at end of working hours

#### Enhanced Pipeline Configuration

- **3-stage cytology pipeline**:
  - Fixation: 15 min constant, batch=1
  - Staining: 20 min constant, batch=10, wait_for_batch=True
  - Reporting: 5 min exponential, batch=1, waits for staining completion

#### Timestamp & Datetime Formatting

- **Simulation start**: 1 May 2025, 9:00 AM
- **Time alignment**: Simulation time 0 = 9 AM on start date
- **Formatted timestamps**: All times displayed as `HH:MM DD/MM/YY`
- **Dual time columns**: Both simulation time (numeric) and formatted datetime in output

#### Enhanced Metrics & Analysis

- **Duration tracking**:
  - Per-stage durations: fixation, staining, reporting
  - Total time in system (turnaround time)
- **Waiting time calculation**:
  - `waiting_for_staining_days`: Time between fixation end and staining start
  - `waiting_for_reporting_days`: Time between staining end and reporting start
  - Formula: `start_of_next_stage - end_of_previous_stage`

- **Output improvements**:
  - All numeric values rounded to 3 decimal places
  - Comprehensive CSV with all timestamps and calculated metrics
  - Summary statistics for durations and waiting times
  - Jupyter notebook (`plotting.ipynb`) with visualization cells

#### Key Behavioral Changes from v1.0

- **Arrivals**: Now spread throughout the day with Poisson distribution (not batched once per day)
- **Working hours enforcement**: Proper time offset ensures arrivals start at 9 AM, not 6 PM
- **Reporting timing**: Waits for all staining to complete before starting (no fixed 5 PM rule)
- **Exit time**: Now properly set to reporting end time (final stage)
- **Batch processing**: Staining waits for batch of 10 slides before processing
- **Stage dependencies**: Reporting stage monitors staining queue completion

#### File Structure

- `generic_entity.py`: Entity class definitions
- `generic_process.py`: Lab process classes
- `generic_generator.py`: Entity generator class
- `cyto_sim.py`: Main simulation combining all generic classes
- `plotting.ipynb`: Visualization and analysis notebook
- `processing_pipeline.json`: JSON configuration for pipelines (created but not yet used in v2.0)

## v1.0 - Initial Cytology Department Simulation

### Overview

This is the baseline cytology-only simulation that models the complete workflow from sample arrival through processing to final reporting.

### Key Features

#### Scope & Flow

- **Cytology only**: defines `CytoSlide` and `HistoSample` classes, but only cytology is simulated.
- **Three processes**: sample generation → processing → reporting, coordinated via FIFO queues.

#### Arrivals

- **Working hours constraint**: arrivals happen only Mon–Sat, 9:00–16:00, enforced by `is_working_hours()` + `get_next_working_time()`.
- **Daily generation**: once per simulated day, generates:
  - Pap slides: count from `simulation.pap_per_day`; positivity by `pap_positive_rate`.
  - Non-Pap slides: count from `simulation.non_pap_per_day`.
- Each slide records `arrival_time` and is logged to the console.

#### Resources

- `cytotechnicians` and `cytopathologists` capacities from `Staff` in `parameters.yaml`.
- Processing and reporting each require the respective resource (SimPy resources, FIFO access).

#### Processing

- Constant processing time per slide from `processing.cyto_slides` (minutes → days).
- Sets `start_processing_time`, moves slides to reporting queue on completion.

#### Reporting

- Lognormal reporting time using `reporting.cyto_slide_distribution` (`mean`, `sd`) → minutes → days.
- Sets `start_reporting_time` and `exit_time`.
- Computes and stores `turnaround_time = exit_time - arrival_time`.

#### Results & Outputs

- Collects per-slide records: `slide_id`, `slide_type` (Pap/Non-Pap), `is_positive`, timestamps, and `turnaround_time`.
- Prints run header, per-step logs, and summary stats (avg/median/min/max TAT).
- Returns a `pandas` DataFrame and saves to `cytology_simulation_results.csv`.

#### Timekeeping Assumptions

- Working-hours constraint applies to arrivals only; processing and reporting run continuously (24/7) subject to resource availability.
- Arrivals are batched once per day (not spread within 9–16 window).

#### Parameters Used

- From `parameters.yaml`: `simulation.run_time`, `simulation.pap_per_day`, `simulation.non_pap_per_day`, `pap_positive_rate`, `processing.cyto_slides`, and `reporting.cyto_slide_distribution`.

---
