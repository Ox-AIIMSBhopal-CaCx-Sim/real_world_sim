import type { ParametersDict, SimulationKind } from '../types/simulation';
import { PipelineSteps } from './PipelineSteps';

interface ParameterEditorProps {
  kind: SimulationKind;
  parameters: ParametersDict | null;
  loading: boolean;
  onChange: (path: string[], value: unknown) => void;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
}

function NumberField({
  label,
  value,
  onChange,
  step = 1,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        type="number"
        step={step}
        value={Number.isFinite(value) ? value : 0}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </label>
  );
}

export function ParameterEditor({ kind, parameters, loading, onChange }: ParameterEditorProps) {
  if (loading || !parameters) {
    return (
      <div className="param-panel">
        <p className="muted">Loading default parameters…</p>
      </div>
    );
  }

  const sim = asRecord(parameters.simulation);
  const caseComplexity = asRecord(parameters.case_complexity);

  return (
    <div className="param-panel">
      <PipelineSteps kind={kind} />

      <div className="param-grid">
        <section>
          <h3>Simulation</h3>
          <NumberField
            label="Duration (months)"
            value={Number(sim.duration_months ?? 12)}
            onChange={(v) => onChange(['simulation', 'duration_months'], v)}
          />
          <NumberField
            label="Warm-up (months)"
            value={Number(sim.warmup_months ?? 1)}
            onChange={(v) => onChange(['simulation', 'warmup_months'], v)}
          />
          <NumberField
            label="P(high complexity)"
            value={Number(caseComplexity.p_high ?? 0.2)}
            step={0.01}
            onChange={(v) => onChange(['case_complexity', 'p_high'], v)}
          />
        </section>

        {kind === 'cyto' ? (
          <CytoFields parameters={parameters} onChange={onChange} />
        ) : (
          <HistoFields parameters={parameters} onChange={onChange} />
        )}
      </div>
    </div>
  );
}

function CytoFields({
  parameters,
  onChange,
}: {
  parameters: ParametersDict;
  onChange: (path: string[], value: unknown) => void;
}) {
  const pap = asRecord(parameters.pap_per_day);
  const nonPap = asRecord(parameters.non_pap_per_day);
  const techs = asRecord(parameters.cyto_technicians);
  const junior = asRecord(parameters.junior_pathologist);
  const senior = asRecord(parameters.senior_pathologists);
  const stain = asRecord(parameters.cyto_manual_staining_station);
  const papParams = Array.isArray(pap.params) ? pap.params : [0];
  const nonPapParams = Array.isArray(nonPap.params) ? nonPap.params : [0];

  return (
    <>
      <section>
        <h3>Workload</h3>
        <NumberField
          label="Pap per day (λ)"
          value={Number(papParams[0] ?? 0)}
          onChange={(v) => onChange(['pap_per_day', 'params'], [v])}
        />
        <NumberField
          label="Non-Pap per day (λ)"
          value={Number(nonPapParams[0] ?? 0)}
          onChange={(v) => onChange(['non_pap_per_day', 'params'], [v])}
        />
        <NumberField
          label="Pap slides / patient"
          value={Number(pap.slide_pt_ratio ?? 1)}
          onChange={(v) => onChange(['pap_per_day', 'slide_pt_ratio'], v)}
        />
      </section>
      <section>
        <h3>Resources</h3>
        <NumberField
          label="Cytotechnicians"
          value={Number(techs.num_cytotech ?? 1)}
          onChange={(v) => onChange(['cyto_technicians', 'num_cytotech'], v)}
        />
        <NumberField
          label="Junior pathologists"
          value={Number(junior.num_junior_pathologist ?? 1)}
          onChange={(v) => onChange(['junior_pathologist', 'num_junior_pathologist'], v)}
        />
        <NumberField
          label="Senior pathologists"
          value={Number(senior.num_senior_pathologist ?? 1)}
          onChange={(v) => onChange(['senior_pathologists', 'num_senior_pathologist'], v)}
        />
        <NumberField
          label="Staining stations"
          value={Number(stain.num_stations ?? 1)}
          onChange={(v) => onChange(['cyto_manual_staining_station', 'num_stations'], v)}
        />
        <NumberField
          label="Stain batch size"
          value={Number(stain.batch_size ?? 5)}
          onChange={(v) => onChange(['cyto_manual_staining_station', 'batch_size'], v)}
        />
      </section>
    </>
  );
}

function HistoFields({
  parameters,
  onChange,
}: {
  parameters: ParametersDict;
  onChange: (path: string[], value: unknown) => void;
}) {
  const cervical = asRecord(parameters.cervical_biopsies_per_day);
  const other = asRecord(parameters.other_biopsies_per_day);
  const techs = asRecord(parameters.histo_technicians);
  const junior = asRecord(parameters.junior_pathologist);
  const senior = asRecord(parameters.senior_pathologists);
  const tissue = asRecord(parameters.histo_tissue_processor);
  const cervicalParams = Array.isArray(cervical.params) ? cervical.params : [0];
  const otherParams = Array.isArray(other.params) ? other.params : [0];

  return (
    <>
      <section>
        <h3>Workload</h3>
        <NumberField
          label="Cervical biopsies / day (λ)"
          value={Number(cervicalParams[0] ?? 0)}
          onChange={(v) => onChange(['cervical_biopsies_per_day', 'params'], [v])}
        />
        <NumberField
          label="Other biopsies / day (λ)"
          value={Number(otherParams[0] ?? 0)}
          onChange={(v) => onChange(['other_biopsies_per_day', 'params'], [v])}
        />
      </section>
      <section>
        <h3>Resources</h3>
        <NumberField
          label="Histotechnicians"
          value={Number(techs.num_cytotech ?? 1)}
          onChange={(v) => onChange(['histo_technicians', 'num_cytotech'], v)}
        />
        <NumberField
          label="Junior pathologists"
          value={Number(junior.num_junior_pathologist ?? 1)}
          onChange={(v) => onChange(['junior_pathologist', 'num_junior_pathologist'], v)}
        />
        <NumberField
          label="Senior pathologists"
          value={Number(senior.num_senior_pathologist ?? 1)}
          onChange={(v) => onChange(['senior_pathologists', 'num_senior_pathologist'], v)}
        />
        <NumberField
          label="Tissue processor capacity"
          value={Number(tissue.num_stations ?? 1)}
          onChange={(v) => onChange(['histo_tissue_processor', 'num_stations'], v)}
        />
        <NumberField
          label="Tissue processor batch"
          value={Number(tissue.batch_size ?? 90)}
          onChange={(v) => onChange(['histo_tissue_processor', 'batch_size'], v)}
        />
      </section>
    </>
  );
}
