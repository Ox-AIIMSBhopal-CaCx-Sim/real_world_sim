# Changelog

## v2.0 - 








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
