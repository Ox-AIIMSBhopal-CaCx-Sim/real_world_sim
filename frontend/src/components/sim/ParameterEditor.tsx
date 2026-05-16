import type { CytoParameters } from '../../types/simulation';
import { NumberField, Section } from './ParamFields';

interface ParameterEditorProps {
  parameters: CytoParameters;
  onChange: (parameters: CytoParameters) => void;
  disabled?: boolean;
}

export function ParameterEditor({ parameters, onChange, disabled }: ParameterEditorProps) {
  const patch = (partial: Partial<CytoParameters>) =>
    onChange({ ...parameters, ...partial });

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
          label="Experiment no."
          value={parameters.simulation.experiment_no}
          min={1}
          onChange={(v) =>
            patch({ simulation: { ...parameters.simulation, experiment_no: v } })
          }
          disabled={disabled}
        />
      </Section>

      <Section title="Arrival rates (patients / day)">
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

      <Section title="Case complexity">
        <NumberField
          label="P(high complexity)"
          value={parameters.case_complexity.p_high}
          min={0}
          max={1}
          step={0.05}
          onChange={(v) =>
            patch({ case_complexity: { p_high: v } })
          }
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

      <Section title="Service times (minutes)">
        <NumberField
          label="Fixation"
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
          value={parameters.cyto_staining_time.params[0]}
          min={1}
          onChange={(v) =>
            patch({
              cyto_staining_time: { ...parameters.cyto_staining_time, params: [v] },
            })
          }
          disabled={disabled}
        />
        <NumberField
          label="Reporting min (high complexity)"
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
          label="Reporting mode (high)"
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
          label="Reporting max (high)"
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
        <NumberField
          label="Reporting min (low)"
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
          label="Reporting mode (low)"
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
          label="Reporting max (low)"
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

      <Section title="Resources">
        <NumberField
          label="Cytotechnicians"
          value={parameters.cyto_technicians.num_cytotech}
          min={1}
          onChange={(v) =>
            patch({
              cyto_technicians: { ...parameters.cyto_technicians, num_cytotech: v },
            })
          }
          disabled={disabled}
        />
        <NumberField
          label="Cytopathologists"
          value={parameters.cyto_pathologists.num_cytopath}
          min={1}
          onChange={(v) =>
            patch({
              cyto_pathologists: { ...parameters.cyto_pathologists, num_cytopath: v },
            })
          }
          disabled={disabled}
        />
        <NumberField
          label="Staining stations"
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
          label="Staining batch size"
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
      </Section>
    </div>
  );
}
