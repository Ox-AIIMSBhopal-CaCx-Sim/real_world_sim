import type { CytoParameters } from '../../../types/simulation';
import { NumberField, Section } from '../ParamFields';

export type CytoResourceSelection =
  | { stage: 'reception'; target: 'person' | 'equipment' }
  | { stage: 'processing'; target: 'person' | 'equipment' }
  | { stage: 'reporting'; target: 'person' | 'equipment' }
  | { stage: 'simulation' };

const STAGE_TITLES: Record<CytoResourceSelection['stage'], string> = {
  reception: 'Reception & accessioning',
  processing: 'Slide processing',
  reporting: 'Pathologist reporting',
  simulation: 'Simulation settings',
};

const TARGET_TITLES: Record<'person' | 'equipment', string> = {
  person: 'Staff',
  equipment: 'Equipment',
};

interface CytoResourcePanelProps {
  selection: CytoResourceSelection;
  parameters: CytoParameters;
  onChange: (parameters: CytoParameters) => void;
  onClose: () => void;
  disabled?: boolean;
}

export function CytoResourcePanel({
  selection,
  parameters,
  onChange,
  onClose,
  disabled,
}: CytoResourcePanelProps) {
  const patch = (partial: Partial<CytoParameters>) =>
    onChange({ ...parameters, ...partial });

  const title =
    selection.stage === 'simulation'
      ? STAGE_TITLES.simulation
      : `${STAGE_TITLES[selection.stage]} · ${TARGET_TITLES[selection.target]}`;

  return (
    <aside className="cyto-resource-panel" aria-labelledby="cyto-resource-panel-title">
      <header className="cyto-resource-panel__header">
        <div>
          <p className="cyto-resource-panel__eyebrow">Edit parameters</p>
          <h3 id="cyto-resource-panel-title" className="cyto-resource-panel__title">
            {title}
          </h3>
        </div>
        <button type="button" className="cyto-resource-panel__close" onClick={onClose} aria-label="Close">
          ×
        </button>
      </header>

      <div className="cyto-resource-panel__body">
        {selection.stage === 'simulation' && (
          <Section title="Run configuration">
            <NumberField
              label="Run time (days)"
              value={parameters.simulation.run_time}
              min={1}
              onChange={(v) =>
                patch({ simulation: { ...parameters.simulation, run_time: v } })
              }
              disabled={disabled}
            />
            <NumberField
              label="Experiment no."
              value={parameters.simulation.experiment_no}
              min={1}
              onChange={(v) =>
                patch({ simulation: { ...parameters.simulation, experiment_no: v } })
              }
              disabled={disabled}
            />
          </Section>
        )}

        {selection.stage === 'reception' && selection.target === 'person' && (
          <>
            <Section title="Staffing">
              <NumberField
                label="Reception staff"
                hint="Headcount in simulation"
                value={parameters.cyto_reception.num_staff}
                min={1}
                onChange={(v) =>
                  patch({
                    cyto_reception: { ...parameters.cyto_reception, num_staff: v },
                  })
                }
                disabled={disabled}
              />
            </Section>
            <Section title="Service time (minutes / patient)">
              <NumberField
                label="Accessioning time"
                hint="Constant — minutes to accept & register each patient"
                value={parameters.cyto_reception.accessioning_time.params[0]}
                min={1}
                onChange={(v) =>
                  patch({
                    cyto_reception: {
                      ...parameters.cyto_reception,
                      accessioning_time: {
                        ...parameters.cyto_reception.accessioning_time,
                        params: [v],
                      },
                    },
                  })
                }
                disabled={disabled}
              />
            </Section>
          </>
        )}

        {selection.stage === 'reception' && selection.target === 'equipment' && (
          <>
            <Section title="Patient arrival rates (per day)">
              <NumberField
                label="Pap smear λ"
                hint="Poisson rate"
                value={parameters.pap_per_day.params[0]}
                min={0}
                step={0.5}
                onChange={(v) =>
                  patch({
                    pap_per_day: { ...parameters.pap_per_day, params: [v] },
                  })
                }
                disabled={disabled}
              />
              <NumberField
                label="Non-Pap λ"
                hint="Poisson rate"
                value={parameters.non_pap_per_day.params[0]}
                min={0}
                step={0.5}
                onChange={(v) =>
                  patch({
                    non_pap_per_day: { ...parameters.non_pap_per_day, params: [v] },
                  })
                }
                disabled={disabled}
              />
              <NumberField
                label="Pap slides per patient"
                value={parameters.pap_per_day.slide_pt_ratio}
                min={1}
                onChange={(v) =>
                  patch({
                    pap_per_day: { ...parameters.pap_per_day, slide_pt_ratio: v },
                  })
                }
                disabled={disabled}
              />
            </Section>
            <Section title="Case complexity at intake">
              <NumberField
                label="P(high complexity)"
                value={parameters.case_complexity.p_high}
                min={0}
                max={1}
                step={0.05}
                onChange={(v) => patch({ case_complexity: { p_high: v } })}
                disabled={disabled}
              />
              <NumberField
                label="Slides / patient (high)"
                value={parameters.slide_pt_ratio_by_case_complexity.high}
                min={1}
                onChange={(v) =>
                  patch({
                    slide_pt_ratio_by_case_complexity: {
                      ...parameters.slide_pt_ratio_by_case_complexity,
                      high: v,
                    },
                  })
                }
                disabled={disabled}
              />
              <NumberField
                label="Slides / patient (low)"
                value={parameters.slide_pt_ratio_by_case_complexity.low}
                min={1}
                onChange={(v) =>
                  patch({
                    slide_pt_ratio_by_case_complexity: {
                      ...parameters.slide_pt_ratio_by_case_complexity,
                      low: v,
                    },
                  })
                }
                disabled={disabled}
              />
            </Section>
          </>
        )}

        {selection.stage === 'processing' && selection.target === 'person' && (
          <>
            <Section title="Staffing">
              <NumberField
                label="Cytotechnicians"
                hint="Headcount in simulation"
                value={parameters.cyto_technicians.num_cytotech}
                min={1}
                onChange={(v) =>
                  patch({
                    cyto_technicians: { ...parameters.cyto_technicians, num_cytotech: v },
                  })
                }
                disabled={disabled}
              />
            </Section>
            <Section title="Service times (minutes)">
              <NumberField
                label="Fixation"
                hint="Constant — minutes per slide"
                value={parameters.cyto_fixation_time.params[0]}
                min={1}
                onChange={(v) =>
                  patch({
                    cyto_fixation_time: { ...parameters.cyto_fixation_time, params: [v] },
                  })
                }
                disabled={disabled}
              />
              <NumberField
                label="Staining (per batch)"
                hint="Constant — staining, drying, labelling & mounting"
                value={parameters.cyto_staining_time.params[0]}
                min={1}
                onChange={(v) =>
                  patch({
                    cyto_staining_time: { ...parameters.cyto_staining_time, params: [v] },
                  })
                }
                disabled={disabled}
              />
            </Section>
          </>
        )}

        {selection.stage === 'processing' && selection.target === 'equipment' && (
          <>
            <Section title="Staining station">
              <NumberField
                label="Number of stations"
                value={parameters.cyto_manual_staining_station.num_stations}
                min={1}
                onChange={(v) =>
                  patch({
                    cyto_manual_staining_station: {
                      ...parameters.cyto_manual_staining_station,
                      num_stations: v,
                    },
                  })
                }
                disabled={disabled}
              />
              <NumberField
                label="Batch size (slides)"
                value={parameters.cyto_manual_staining_station.batch_size}
                min={1}
                onChange={(v) =>
                  patch({
                    cyto_manual_staining_station: {
                      ...parameters.cyto_manual_staining_station,
                      batch_size: v,
                    },
                  })
                }
                disabled={disabled}
              />
              <NumberField
                label="Error rate (per batch)"
                value={parameters.cyto_manual_staining_station.error_rate}
                min={0}
                max={1}
                step={0.001}
                onChange={(v) =>
                  patch({
                    cyto_manual_staining_station: {
                      ...parameters.cyto_manual_staining_station,
                      error_rate: v,
                    },
                  })
                }
                disabled={disabled}
              />
            </Section>
            <Section title="Consumables">
              <NumberField
                label="Staining kits"
                value={parameters.cyto_staining_kits.num_kits}
                min={1}
                onChange={(v) =>
                  patch({
                    cyto_staining_kits: { ...parameters.cyto_staining_kits, num_kits: v },
                  })
                }
                disabled={disabled}
              />
              <NumberField
                label="Stain per kit (ml)"
                value={parameters.cyto_staining_kits.stain_per_kit}
                min={1}
                onChange={(v) =>
                  patch({
                    cyto_staining_kits: { ...parameters.cyto_staining_kits, stain_per_kit: v },
                  })
                }
                disabled={disabled}
              />
              <NumberField
                label="Reagent per slide (ml)"
                value={parameters.cyto_staining_kits.reagent_per_slide}
                min={0}
                step={0.01}
                onChange={(v) =>
                  patch({
                    cyto_staining_kits: {
                      ...parameters.cyto_staining_kits,
                      reagent_per_slide: v,
                    },
                  })
                }
                disabled={disabled}
              />
            </Section>
          </>
        )}

        {selection.stage === 'reporting' && selection.target === 'person' && (
          <>
            <Section title="Staffing">
              <NumberField
                label="Cytopathologists"
                hint="Headcount in simulation"
                value={parameters.cyto_pathologists.num_cytopath}
                min={1}
                onChange={(v) =>
                  patch({
                    cyto_pathologists: { ...parameters.cyto_pathologists, num_cytopath: v },
                  })
                }
                disabled={disabled}
              />
            </Section>
            <Section title="Reporting time — high complexity (min, mode, max)">
              <NumberField
                label="Minimum"
                value={parameters.cyto_reporting_time.by_case_complexity.high.params[0]}
                min={1}
                onChange={(v) =>
                  patch({
                    cyto_reporting_time: {
                      by_case_complexity: {
                        ...parameters.cyto_reporting_time.by_case_complexity,
                        high: {
                          ...parameters.cyto_reporting_time.by_case_complexity.high,
                          params: [
                            v,
                            parameters.cyto_reporting_time.by_case_complexity.high.params[1],
                            parameters.cyto_reporting_time.by_case_complexity.high.params[2],
                          ],
                        },
                      },
                    },
                  })
                }
                disabled={disabled}
              />
              <NumberField
                label="Mode"
                value={parameters.cyto_reporting_time.by_case_complexity.high.params[1]}
                min={1}
                onChange={(v) =>
                  patch({
                    cyto_reporting_time: {
                      by_case_complexity: {
                        ...parameters.cyto_reporting_time.by_case_complexity,
                        high: {
                          ...parameters.cyto_reporting_time.by_case_complexity.high,
                          params: [
                            parameters.cyto_reporting_time.by_case_complexity.high.params[0],
                            v,
                            parameters.cyto_reporting_time.by_case_complexity.high.params[2],
                          ],
                        },
                      },
                    },
                  })
                }
                disabled={disabled}
              />
              <NumberField
                label="Maximum"
                value={parameters.cyto_reporting_time.by_case_complexity.high.params[2]}
                min={1}
                onChange={(v) =>
                  patch({
                    cyto_reporting_time: {
                      by_case_complexity: {
                        ...parameters.cyto_reporting_time.by_case_complexity,
                        high: {
                          ...parameters.cyto_reporting_time.by_case_complexity.high,
                          params: [
                            parameters.cyto_reporting_time.by_case_complexity.high.params[0],
                            parameters.cyto_reporting_time.by_case_complexity.high.params[1],
                            v,
                          ],
                        },
                      },
                    },
                  })
                }
                disabled={disabled}
              />
            </Section>
            <Section title="Reporting time — low complexity (min, mode, max)">
              <NumberField
                label="Minimum"
                value={parameters.cyto_reporting_time.by_case_complexity.low.params[0]}
                min={1}
                onChange={(v) =>
                  patch({
                    cyto_reporting_time: {
                      by_case_complexity: {
                        ...parameters.cyto_reporting_time.by_case_complexity,
                        low: {
                          ...parameters.cyto_reporting_time.by_case_complexity.low,
                          params: [
                            v,
                            parameters.cyto_reporting_time.by_case_complexity.low.params[1],
                            parameters.cyto_reporting_time.by_case_complexity.low.params[2],
                          ],
                        },
                      },
                    },
                  })
                }
                disabled={disabled}
              />
              <NumberField
                label="Mode"
                value={parameters.cyto_reporting_time.by_case_complexity.low.params[1]}
                min={1}
                onChange={(v) =>
                  patch({
                    cyto_reporting_time: {
                      by_case_complexity: {
                        ...parameters.cyto_reporting_time.by_case_complexity,
                        low: {
                          ...parameters.cyto_reporting_time.by_case_complexity.low,
                          params: [
                            parameters.cyto_reporting_time.by_case_complexity.low.params[0],
                            v,
                            parameters.cyto_reporting_time.by_case_complexity.low.params[2],
                          ],
                        },
                      },
                    },
                  })
                }
                disabled={disabled}
              />
              <NumberField
                label="Maximum"
                value={parameters.cyto_reporting_time.by_case_complexity.low.params[2]}
                min={1}
                onChange={(v) =>
                  patch({
                    cyto_reporting_time: {
                      by_case_complexity: {
                        ...parameters.cyto_reporting_time.by_case_complexity,
                        low: {
                          ...parameters.cyto_reporting_time.by_case_complexity.low,
                          params: [
                            parameters.cyto_reporting_time.by_case_complexity.low.params[0],
                            parameters.cyto_reporting_time.by_case_complexity.low.params[1],
                            v,
                          ],
                        },
                      },
                    },
                  })
                }
                disabled={disabled}
              />
            </Section>
          </>
        )}

        {selection.stage === 'reporting' && selection.target === 'equipment' && (
          <Section title="Microscope bench">
            <NumberField
              label="Number of stations"
              hint="Microscope workstations"
              value={parameters.cyto_reporting_station.num_stations}
              min={1}
              onChange={(v) =>
                patch({
                  cyto_reporting_station: {
                    ...parameters.cyto_reporting_station,
                    num_stations: v,
                  },
                })
              }
              disabled={disabled}
            />
            <NumberField
              label="Batch size (cases)"
              value={parameters.cyto_reporting_station.batch_size}
              min={1}
              onChange={(v) =>
                patch({
                  cyto_reporting_station: {
                    ...parameters.cyto_reporting_station,
                    batch_size: v,
                  },
                })
              }
              disabled={disabled}
            />
            <NumberField
              label="Error rate"
              hint="Per reporting session"
              value={parameters.cyto_reporting_station.error_rate}
              min={0}
              max={1}
              step={0.001}
              onChange={(v) =>
                patch({
                  cyto_reporting_station: {
                    ...parameters.cyto_reporting_station,
                    error_rate: v,
                  },
                })
              }
              disabled={disabled}
            />
          </Section>
        )}
      </div>

      <p className="cyto-resource-panel__hint">
        Click a professional or piece of equipment in the workflow to edit its parameters.
      </p>
    </aside>
  );
}
