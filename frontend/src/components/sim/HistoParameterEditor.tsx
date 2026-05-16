import type { HistoParameters } from '../../types/simulation';
import { NumberField, Section } from './ParamFields';

interface HistoParameterEditorProps {
  parameters: HistoParameters;
  onChange: (parameters: HistoParameters) => void;
  disabled?: boolean;
}

export function HistoParameterEditor({
  parameters,
  onChange,
  disabled,
}: HistoParameterEditorProps) {
  const patch = (partial: Partial<HistoParameters>) =>
    onChange({ ...parameters, ...partial });

  const fixationSmall =
    (parameters.histo_fixation_time as { by_size?: { small?: { params?: number[] } } })
      ?.by_size?.small?.params?.[0] ?? 360;

  return (
    <div className="param-editor">
      <Section title="Simulation">
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
      </Section>

      <Section title="Arrival rates (biopsies / day)">
        <NumberField
          label="Cervical λ"
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
      </Section>

      <Section title="Service times (minutes)">
        <NumberField
          label="Fixation (small biopsy)"
          value={fixationSmall}
          min={1}
          onChange={(v) =>
            patch({
              histo_fixation_time: {
                by_size: {
                  small: { distribution: 'constant', params: [v] },
                  medium: {
                    distribution: 'constant',
                    params: [
                      (parameters.histo_fixation_time as { by_size?: { medium?: { params?: number[] } } })
                        ?.by_size?.medium?.params?.[0] ?? 720,
                    ],
                  },
                  large: {
                    distribution: 'constant',
                    params: [
                      (parameters.histo_fixation_time as { by_size?: { large?: { params?: number[] } } })
                        ?.by_size?.large?.params?.[0] ?? 2880,
                    ],
                  },
                },
              },
            })
          }
          disabled={disabled}
        />
        <NumberField
          label="Tissue processing (batch)"
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
          label="Staining (batch)"
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

      <Section title="Resources">
        <NumberField
          label="Histotechnicians"
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
          value={parameters.path_resident.num}
          min={1}
          onChange={(v) =>
            patch({ path_resident: { ...parameters.path_resident, num: v } })}
          disabled={disabled}
        />
        <NumberField
          label="Histopathologists"
          value={parameters.histo_pathologists.num_cytopath}
          min={1}
          onChange={(v) =>
            patch({
              histo_pathologists: { ...parameters.histo_pathologists, num_cytopath: v },
            })
          }
          disabled={disabled}
        />
        <NumberField
          label="Grossing stations"
          value={parameters.histo_grossing_station.num_stations}
          min={1}
          onChange={(v) =>
            patch({
              histo_grossing_station: {
                ...parameters.histo_grossing_station,
                num_stations: v,
              },
            })
          }
          disabled={disabled}
        />
        <NumberField
          label="Tissue processor batch"
          value={parameters.histo_tissue_processor.batch_size}
          min={1}
          onChange={(v) =>
            patch({
              histo_tissue_processor: {
                ...parameters.histo_tissue_processor,
                batch_size: v,
              },
            })
          }
          disabled={disabled}
        />
        <NumberField
          label="Staining batch size"
          value={parameters.histo_staining_station.batch_size}
          min={1}
          onChange={(v) =>
            patch({
              histo_staining_station: {
                ...parameters.histo_staining_station,
                batch_size: v,
              },
            })
          }
          disabled={disabled}
        />
      </Section>
    </div>
  );
}
