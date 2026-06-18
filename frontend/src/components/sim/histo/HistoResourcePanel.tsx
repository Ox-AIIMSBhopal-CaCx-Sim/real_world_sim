import type { HistoParameters, HistoStationConfig } from '../../../types/simulation';
import { NumberField, Section } from '../ParamFields';
import { getTimeBySize, patchTimeBySize } from './histoParamHelpers';

export type HistoResourceSelection =
  | { stage: 'reception'; target: 'person' | 'equipment' }
  | { stage: 'processing'; target: 'person' | 'equipment' }
  | { stage: 'reporting'; target: 'person' | 'equipment' }
  | { stage: 'simulation' };

const STAGE_TITLES: Record<HistoResourceSelection['stage'], string> = {
  reception: 'Reception & accessioning',
  processing: 'Histology processing',
  reporting: 'Pathologist reporting',
  simulation: 'Simulation settings',
};

const TARGET_TITLES: Record<'person' | 'equipment', string> = {
  person: 'Staff',
  equipment: 'Equipment',
};

interface HistoResourcePanelProps {
  selection: HistoResourceSelection;
  parameters: HistoParameters;
  onChange: (parameters: HistoParameters) => void;
  onClose: () => void;
  disabled?: boolean;
}

function StationFields({
  title,
  station,
  onChange,
  disabled,
  batchHint,
}: {
  title: string;
  station: HistoStationConfig;
  onChange: (station: HistoStationConfig) => void;
  disabled?: boolean;
  batchHint?: string;
}) {
  return (
    <Section title={title}>
      <NumberField
        label="Number of stations"
        value={station.num_stations}
        min={1}
        onChange={(v) => onChange({ ...station, num_stations: v })}
        disabled={disabled}
      />
      <NumberField
        label="Batch size"
        hint={batchHint}
        value={station.batch_size}
        min={1}
        onChange={(v) => onChange({ ...station, batch_size: v })}
        disabled={disabled}
      />
      <NumberField
        label="Error rate"
        value={station.error_rate}
        min={0}
        max={1}
        step={0.001}
        onChange={(v) => onChange({ ...station, error_rate: v })}
        disabled={disabled}
      />
    </Section>
  );
}

export function HistoResourcePanel({
  selection,
  parameters,
  onChange,
  onClose,
  disabled,
}: HistoResourcePanelProps) {
  const patch = (partial: Partial<HistoParameters>) =>
    onChange({ ...parameters, ...partial });

  const title =
    selection.stage === 'simulation'
      ? STAGE_TITLES.simulation
      : `${STAGE_TITLES[selection.stage]} · ${TARGET_TITLES[selection.target]}`;

  const fixation = parameters.histo_fixation_time;
  const grossing = parameters.histo_grossing_time;

  return (
    <aside className="cyto-resource-panel" aria-labelledby="histo-resource-panel-title">
      <header className="cyto-resource-panel__header">
        <div>
          <p className="cyto-resource-panel__eyebrow">Edit parameters</p>
          <h3 id="histo-resource-panel-title" className="cyto-resource-panel__title">
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
              label="Warm-up (days)"
              value={parameters.simulation.warmup_days ?? 30}
              min={0}
              onChange={(v) =>
                patch({ simulation: { ...parameters.simulation, warmup_days: v } })
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
                value={parameters.histo_reception.num_staff}
                min={1}
                onChange={(v) =>
                  patch({
                    histo_reception: { ...parameters.histo_reception, num_staff: v },
                  })
                }
                disabled={disabled}
              />
            </Section>
            <Section title="Service time (minutes / biopsy)">
              <NumberField
                label="Accessioning time"
                hint="Constant — minutes to accept & register each biopsy"
                value={parameters.histo_reception.accessioning_time.params[0]}
                min={1}
                onChange={(v) =>
                  patch({
                    histo_reception: {
                      ...parameters.histo_reception,
                      accessioning_time: {
                        ...parameters.histo_reception.accessioning_time,
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
            <Section title="Biopsy arrival rates (per day)">
              <NumberField
                label="Cervical biopsy λ"
                hint="Poisson rate"
                value={parameters.cervical_biopsies_per_day.params[0]}
                min={0}
                step={0.5}
                onChange={(v) =>
                  patch({
                    cervical_biopsies_per_day: {
                      ...parameters.cervical_biopsies_per_day,
                      params: [v],
                    },
                  })
                }
                disabled={disabled}
              />
              <NumberField
                label="Other biopsies λ"
                hint="Poisson rate"
                value={parameters.other_biopsies_per_day.params[0]}
                min={0}
                step={0.5}
                onChange={(v) =>
                  patch({
                    other_biopsies_per_day: {
                      ...parameters.other_biopsies_per_day,
                      params: [v],
                    },
                  })
                }
                disabled={disabled}
              />
            </Section>
            <Section title="Case complexity & biopsy size">
              <NumberField
                label="P(high complexity)"
                value={parameters.case_complexity.p_high}
                min={0}
                max={1}
                step={0.01}
                onChange={(v) => patch({ case_complexity: { p_high: v } })}
                disabled={disabled}
              />
              <NumberField
                label="Slides (small biopsy)"
                value={parameters.slide_pt_ratio_by_biopsy_size.small}
                min={1}
                onChange={(v) =>
                  patch({
                    slide_pt_ratio_by_biopsy_size: {
                      ...parameters.slide_pt_ratio_by_biopsy_size,
                      small: v,
                    },
                  })
                }
                disabled={disabled}
              />
              <NumberField
                label="Slides (medium biopsy)"
                value={parameters.slide_pt_ratio_by_biopsy_size.medium}
                min={1}
                onChange={(v) =>
                  patch({
                    slide_pt_ratio_by_biopsy_size: {
                      ...parameters.slide_pt_ratio_by_biopsy_size,
                      medium: v,
                    },
                  })
                }
                disabled={disabled}
              />
              <NumberField
                label="Slides (large biopsy)"
                value={parameters.slide_pt_ratio_by_biopsy_size.large}
                min={1}
                onChange={(v) =>
                  patch({
                    slide_pt_ratio_by_biopsy_size: {
                      ...parameters.slide_pt_ratio_by_biopsy_size,
                      large: v,
                    },
                  })
                }
                disabled={disabled}
              />
              <NumberField
                label="P(small biopsy)"
                value={parameters.biopsy_size.weights.small ?? 0.9}
                min={0}
                max={1}
                step={0.01}
                onChange={(v) =>
                  patch({
                    biopsy_size: {
                      weights: { ...parameters.biopsy_size.weights, small: v },
                    },
                  })
                }
                disabled={disabled}
              />
              <NumberField
                label="P(medium biopsy)"
                value={parameters.biopsy_size.weights.medium ?? 0.09}
                min={0}
                max={1}
                step={0.01}
                onChange={(v) =>
                  patch({
                    biopsy_size: {
                      weights: { ...parameters.biopsy_size.weights, medium: v },
                    },
                  })
                }
                disabled={disabled}
              />
              <NumberField
                label="P(large biopsy)"
                value={parameters.biopsy_size.weights.large ?? 0.01}
                min={0}
                max={1}
                step={0.01}
                onChange={(v) =>
                  patch({
                    biopsy_size: {
                      weights: { ...parameters.biopsy_size.weights, large: v },
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
                label="Histotechnicians"
                hint="Headcount in simulation"
                value={parameters.histo_technicians.num_cytotech}
                min={1}
                onChange={(v) =>
                  patch({
                    histo_technicians: { ...parameters.histo_technicians, num_cytotech: v },
                  })
                }
                disabled={disabled}
              />
              <NumberField
                label="Pathology residents"
                hint="Grossing staff"
                value={parameters.path_resident.num}
                min={1}
                onChange={(v) =>
                  patch({ path_resident: { ...parameters.path_resident, num: v } })}
                disabled={disabled}
              />
            </Section>
            <Section title="Fixation (minutes, by biopsy size)">
              <NumberField
                label="Small biopsy"
                value={getTimeBySize(fixation, 'small', 360)}
                min={1}
                onChange={(v) =>
                  patch({ histo_fixation_time: patchTimeBySize(fixation, 'small', v) })
                }
                disabled={disabled}
              />
              <NumberField
                label="Medium biopsy"
                value={getTimeBySize(fixation, 'medium', 720)}
                min={1}
                onChange={(v) =>
                  patch({ histo_fixation_time: patchTimeBySize(fixation, 'medium', v) })
                }
                disabled={disabled}
              />
              <NumberField
                label="Large biopsy"
                value={getTimeBySize(fixation, 'large', 2880)}
                min={1}
                onChange={(v) =>
                  patch({ histo_fixation_time: patchTimeBySize(fixation, 'large', v) })
                }
                disabled={disabled}
              />
            </Section>
            <Section title="Grossing (minutes, by biopsy size)">
              <NumberField
                label="Small biopsy"
                value={getTimeBySize(grossing, 'small', 10)}
                min={1}
                onChange={(v) =>
                  patch({ histo_grossing_time: patchTimeBySize(grossing, 'small', v) })
                }
                disabled={disabled}
              />
              <NumberField
                label="Medium biopsy"
                value={getTimeBySize(grossing, 'medium', 30)}
                min={1}
                onChange={(v) =>
                  patch({ histo_grossing_time: patchTimeBySize(grossing, 'medium', v) })
                }
                disabled={disabled}
              />
              <NumberField
                label="Large biopsy"
                value={getTimeBySize(grossing, 'large', 120)}
                min={1}
                onChange={(v) =>
                  patch({ histo_grossing_time: patchTimeBySize(grossing, 'large', v) })
                }
                disabled={disabled}
              />
            </Section>
            <Section title="Other service times (minutes)">
              <NumberField
                label="Tissue processing (per batch)"
                value={parameters.histo_tissue_processing_time.params[0]}
                min={1}
                onChange={(v) =>
                  patch({
                    histo_tissue_processing_time: {
                      ...parameters.histo_tissue_processing_time,
                      params: [v],
                    },
                  })
                }
                disabled={disabled}
              />
              <NumberField
                label="Embedding (per block)"
                value={parameters.histo_embedding_time.params[0]}
                min={1}
                onChange={(v) =>
                  patch({
                    histo_embedding_time: { ...parameters.histo_embedding_time, params: [v] },
                  })
                }
                disabled={disabled}
              />
              <NumberField
                label="Sectioning (per block)"
                value={parameters.histo_sectioning_time.params[0]}
                min={1}
                onChange={(v) =>
                  patch({
                    histo_sectioning_time: { ...parameters.histo_sectioning_time, params: [v] },
                  })
                }
                disabled={disabled}
              />
              <NumberField
                label="Staining (per batch)"
                value={parameters.histo_staining_time.params[0]}
                min={1}
                onChange={(v) =>
                  patch({
                    histo_staining_time: { ...parameters.histo_staining_time, params: [v] },
                  })
                }
                disabled={disabled}
              />
            </Section>
          </>
        )}

        {selection.stage === 'processing' && selection.target === 'equipment' && (
          <>
            <StationFields
              title="Grossing station"
              station={parameters.histo_grossing_station}
              onChange={(station) => patch({ histo_grossing_station: station })}
              disabled={disabled}
              batchHint="Samples per batch"
            />
            <StationFields
              title="Tissue processor"
              station={parameters.histo_tissue_processor}
              onChange={(station) => patch({ histo_tissue_processor: station })}
              disabled={disabled}
              batchHint="Cassettes per batch"
            />
            <StationFields
              title="Embedding station"
              station={parameters.histo_embedding_station}
              onChange={(station) => patch({ histo_embedding_station: station })}
              disabled={disabled}
              batchHint="Blocks per batch"
            />
            <StationFields
              title="Sectioning station"
              station={parameters.histo_sectioning_station}
              onChange={(station) => patch({ histo_sectioning_station: station })}
              disabled={disabled}
              batchHint="Blocks per batch"
            />
            <StationFields
              title="Staining station"
              station={parameters.histo_staining_station}
              onChange={(station) => patch({ histo_staining_station: station })}
              disabled={disabled}
              batchHint="Slides per batch"
            />
            <Section title="Consumables">
              <NumberField
                label="Staining kits"
                value={parameters.histo_staining_kits.num_kits}
                min={1}
                onChange={(v) =>
                  patch({
                    histo_staining_kits: { ...parameters.histo_staining_kits, num_kits: v },
                  })
                }
                disabled={disabled}
              />
              <NumberField
                label="Stain per kit (ml)"
                value={parameters.histo_staining_kits.stain_per_kit}
                min={1}
                onChange={(v) =>
                  patch({
                    histo_staining_kits: { ...parameters.histo_staining_kits, stain_per_kit: v },
                  })
                }
                disabled={disabled}
              />
              <NumberField
                label="Reagent per slide (ml)"
                value={parameters.histo_staining_kits.reagent_per_slide}
                min={0}
                step={0.01}
                onChange={(v) =>
                  patch({
                    histo_staining_kits: {
                      ...parameters.histo_staining_kits,
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
                label="Histopathologists"
                hint="Headcount in simulation"
                value={parameters.histo_pathologists.num_cytopath}
                min={1}
                onChange={(v) =>
                  patch({
                    histo_pathologists: { ...parameters.histo_pathologists, num_cytopath: v },
                  })
                }
                disabled={disabled}
              />
            </Section>
            <Section title="Reporting time — high complexity (min, mode, max)">
              <NumberField
                label="Minimum"
                value={parameters.histo_reporting_time.by_case_complexity.high.params[0]}
                min={1}
                onChange={(v) =>
                  patch({
                    histo_reporting_time: {
                      by_case_complexity: {
                        ...parameters.histo_reporting_time.by_case_complexity,
                        high: {
                          ...parameters.histo_reporting_time.by_case_complexity.high,
                          params: [
                            v,
                            parameters.histo_reporting_time.by_case_complexity.high.params[1],
                            parameters.histo_reporting_time.by_case_complexity.high.params[2],
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
                value={parameters.histo_reporting_time.by_case_complexity.high.params[1]}
                min={1}
                onChange={(v) =>
                  patch({
                    histo_reporting_time: {
                      by_case_complexity: {
                        ...parameters.histo_reporting_time.by_case_complexity,
                        high: {
                          ...parameters.histo_reporting_time.by_case_complexity.high,
                          params: [
                            parameters.histo_reporting_time.by_case_complexity.high.params[0],
                            v,
                            parameters.histo_reporting_time.by_case_complexity.high.params[2],
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
                value={parameters.histo_reporting_time.by_case_complexity.high.params[2]}
                min={1}
                onChange={(v) =>
                  patch({
                    histo_reporting_time: {
                      by_case_complexity: {
                        ...parameters.histo_reporting_time.by_case_complexity,
                        high: {
                          ...parameters.histo_reporting_time.by_case_complexity.high,
                          params: [
                            parameters.histo_reporting_time.by_case_complexity.high.params[0],
                            parameters.histo_reporting_time.by_case_complexity.high.params[1],
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
                value={parameters.histo_reporting_time.by_case_complexity.low.params[0]}
                min={1}
                onChange={(v) =>
                  patch({
                    histo_reporting_time: {
                      by_case_complexity: {
                        ...parameters.histo_reporting_time.by_case_complexity,
                        low: {
                          ...parameters.histo_reporting_time.by_case_complexity.low,
                          params: [
                            v,
                            parameters.histo_reporting_time.by_case_complexity.low.params[1],
                            parameters.histo_reporting_time.by_case_complexity.low.params[2],
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
                value={parameters.histo_reporting_time.by_case_complexity.low.params[1]}
                min={1}
                onChange={(v) =>
                  patch({
                    histo_reporting_time: {
                      by_case_complexity: {
                        ...parameters.histo_reporting_time.by_case_complexity,
                        low: {
                          ...parameters.histo_reporting_time.by_case_complexity.low,
                          params: [
                            parameters.histo_reporting_time.by_case_complexity.low.params[0],
                            v,
                            parameters.histo_reporting_time.by_case_complexity.low.params[2],
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
                value={parameters.histo_reporting_time.by_case_complexity.low.params[2]}
                min={1}
                onChange={(v) =>
                  patch({
                    histo_reporting_time: {
                      by_case_complexity: {
                        ...parameters.histo_reporting_time.by_case_complexity,
                        low: {
                          ...parameters.histo_reporting_time.by_case_complexity.low,
                          params: [
                            parameters.histo_reporting_time.by_case_complexity.low.params[0],
                            parameters.histo_reporting_time.by_case_complexity.low.params[1],
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
          <StationFields
            title="Microscope bench"
            station={parameters.histo_reporting_station}
            onChange={(station) => patch({ histo_reporting_station: station })}
            disabled={disabled}
            batchHint="Cases per session"
          />
        )}
      </div>

      <p className="cyto-resource-panel__hint">
        Click a professional or piece of equipment in the workflow to edit its parameters.
      </p>
    </aside>
  );
}
