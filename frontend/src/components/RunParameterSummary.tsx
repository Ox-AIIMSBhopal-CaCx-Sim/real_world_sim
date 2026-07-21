import type { DisruptionConfig, ParametersDict, SimulationKind } from '../types/simulation';
import { readDisruptions } from './disruptionPresets';
import { formatScheduleDict } from './scheduleUtils';

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
}

function num(value: unknown, fallback = 0): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function constantParam(value: unknown): number | null {
  if (typeof value === 'number') return value;
  const record = asRecord(value);
  const params = record.params;
  if (typeof params === 'number') return params;
  if (Array.isArray(params) && typeof params[0] === 'number') return Number(params[0]);
  return null;
}

function poissonLambda(value: unknown): number | null {
  const record = asRecord(value);
  const params = record.params;
  if (Array.isArray(params) && params.length > 0) return num(params[0]);
  return null;
}

function triangularLabel(value: unknown, complexity: 'high' | 'low'): string | null {
  const byCc = asRecord(asRecord(value).by_case_complexity);
  const entry = asRecord(byCc[complexity]);
  const params = entry.params;
  if (!Array.isArray(params) || params.length < 3) return null;
  return `${params[0]} / ${params[1]} / ${params[2]} min`;
}

function sizeTimeLabel(value: unknown, size: string): string | null {
  const bySize = asRecord(asRecord(value).by_size);
  const t = constantParam(bySize[size]);
  return t == null ? null : `${t} min`;
}

type SummaryRow = { label: string; value: string };
type SummarySection = { title: string; rows: SummaryRow[] };

function row(label: string, value: string | number | null | undefined): SummaryRow | null {
  if (value == null || value === '') return null;
  return { label, value: String(value) };
}

function compact(rows: Array<SummaryRow | null>): SummaryRow[] {
  return rows.filter((r): r is SummaryRow => r != null);
}

function disruptionLabel(d: DisruptionConfig): string {
  const start =
    d.start_datetime != null && d.start_datetime !== ''
      ? `from ${d.start_datetime}`
      : `from day ${d.start_day ?? 0}`;
  return `${d.id}: ${d.resource}, ${start}, ${d.duration_days} day(s), capacity ${d.effective_capacity}`;
}

function buildCytoSections(parameters: ParametersDict): SummarySection[] {
  const pap = asRecord(parameters.pap_per_day);
  const nonPap = asRecord(parameters.non_pap_per_day);
  const slideByCc = asRecord(parameters.slide_pt_ratio_by_case_complexity);
  const techs = asRecord(parameters.cyto_technicians);
  const junior = asRecord(parameters.junior_pathologist);
  const senior = asRecord(parameters.senior_pathologists);
  const stain = asRecord(parameters.cyto_manual_staining_station);

  return [
    {
      title: 'Workload',
      rows: compact([
        row('Pap / day (λ)', poissonLambda(pap)),
        row('Non-Pap / day (λ)', poissonLambda(nonPap)),
        row('Pap slides / patient', pap.slide_pt_ratio != null ? num(pap.slide_pt_ratio) : null),
        row('Non-Pap slides / patient (high)', slideByCc.high != null ? num(slideByCc.high) : null),
        row('Non-Pap slides / patient (low)', slideByCc.low != null ? num(slideByCc.low) : null),
      ]),
    },
    {
      title: 'Lab resources',
      rows: compact([
        row('Cytotechnicians', techs.num_cytotech != null ? num(techs.num_cytotech) : null),
        row('Junior pathologists', junior.num_junior_pathologist != null ? num(junior.num_junior_pathologist) : null),
        row('Senior pathologists', senior.num_senior_pathologist != null ? num(senior.num_senior_pathologist) : null),
        row('Staining stations', stain.num_stations != null ? num(stain.num_stations) : null),
        row('Stain batch size', stain.batch_size != null ? num(stain.batch_size) : null),
        row('Stain error rate', stain.error_rate != null ? num(stain.error_rate) : null),
        row('Repeat stain rate', senior.repeat_stain_rate != null ? num(senior.repeat_stain_rate) : null),
      ]),
    },
    {
      title: 'Schedules',
      rows: compact([
        row('Cytotechnicians', formatScheduleDict(techs.cytotech_schedule)),
        row('Junior pathologists', formatScheduleDict(junior.junior_pathologist_schedule)),
        row('Senior pathologists', formatScheduleDict(senior.senior_pathologist_schedule)),
      ]),
    },
    {
      title: 'Process times',
      rows: compact([
        row('Fixation', constantParam(parameters.cyto_fixation_time) != null ? `${constantParam(parameters.cyto_fixation_time)} min` : null),
        row('Staining', constantParam(parameters.cyto_staining_time) != null ? `${constantParam(parameters.cyto_staining_time)} min` : null),
        row('Screening (high)', triangularLabel(parameters.cyto_slide_screening_time, 'high')),
        row('Screening (low)', triangularLabel(parameters.cyto_slide_screening_time, 'low')),
        row('Reporting (high)', triangularLabel(parameters.cyto_reporting_time, 'high')),
        row('Reporting (low)', triangularLabel(parameters.cyto_reporting_time, 'low')),
      ]),
    },
  ];
}

function sampleSizeRows(parameters: ParametersDict): SummaryRow[] {
  const weights = asRecord(asRecord(parameters.biopsy_size).weights);
  const sizes: Array<[string, string]> = [
    ['small', 'Sample size (small)'],
    ['medium', 'Sample size (medium)'],
    ['large', 'Sample size (large)'],
  ];
  const values = sizes.map(([key]) => Math.max(0, num(weights[key], 0)));
  const total = values.reduce((sum, v) => sum + v, 0);
  if (total <= 0) return [];
  return compact(
    sizes.map(([, label], i) => row(label, `${((values[i] / total) * 100).toFixed(0)}%`)),
  );
}

function buildHistoSections(parameters: ParametersDict): SummarySection[] {
  const cervical = asRecord(parameters.cervical_biopsies_per_day);
  const other = asRecord(parameters.other_biopsies_per_day);
  const slideBySize = asRecord(parameters.slide_pt_ratio_by_biopsy_size);
  const techs = asRecord(parameters.histo_technicians);
  const junior = asRecord(parameters.junior_pathologist);
  const senior = asRecord(parameters.senior_pathologists);
  const grossing = asRecord(parameters.histo_grossing_station);
  const tissue = asRecord(parameters.histo_tissue_processor);
  const embedding = asRecord(parameters.histo_embedding_station);
  const sectioning = asRecord(parameters.histo_sectioning_station);
  const staining = asRecord(parameters.histo_staining_station);

  return [
    {
      title: 'Workload',
      rows: compact([
        row('Cervical biopsies / day (λ)', poissonLambda(cervical)),
        row('Other biopsies / day (λ)', poissonLambda(other)),
        row('Slides / patient (small)', slideBySize.small != null ? num(slideBySize.small) : null),
        row('Slides / patient (medium)', slideBySize.medium != null ? num(slideBySize.medium) : null),
        row('Slides / patient (large)', slideBySize.large != null ? num(slideBySize.large) : null),
        ...sampleSizeRows(parameters),
      ]),
    },
    {
      title: 'Lab resources',
      rows: compact([
        row('Histotechnicians', techs.num_cytotech != null ? num(techs.num_cytotech) : null),
        row('Junior pathologists', junior.num_junior_pathologist != null ? num(junior.num_junior_pathologist) : null),
        row('Senior pathologists', senior.num_senior_pathologist != null ? num(senior.num_senior_pathologist) : null),
        row('Grossing stations', grossing.num_stations != null ? num(grossing.num_stations) : null),
        row('Tissue processors', tissue.num_stations != null ? num(tissue.num_stations) : null),
        row('Processor batch size', tissue.batch_size != null ? num(tissue.batch_size) : null),
        row('Embedding stations', embedding.num_stations != null ? num(embedding.num_stations) : null),
        row('Sectioning stations', sectioning.num_stations != null ? num(sectioning.num_stations) : null),
        row('Staining stations', staining.num_stations != null ? num(staining.num_stations) : null),
        row('Stain batch size', staining.batch_size != null ? num(staining.batch_size) : null),
        row('Repeat stain rate', senior.repeat_stain_rate != null ? num(senior.repeat_stain_rate) : null),
      ]),
    },
    {
      title: 'Schedules',
      rows: compact([
        row('Histotechnicians', formatScheduleDict(techs.histotech_schedule)),
        row(
          'Junior · grossing',
          formatScheduleDict(asRecord(junior.task_windows).grossing),
        ),
        row(
          'Junior · screening',
          formatScheduleDict(asRecord(junior.task_windows).screening),
        ),
        row('Senior pathologists', formatScheduleDict(senior.senior_pathologist_schedule)),
      ]),
    },
    {
      title: 'Process times',
      rows: compact([
        row('Fixation (small)', sizeTimeLabel(parameters.histo_fixation_time, 'small')),
        row('Fixation (medium)', sizeTimeLabel(parameters.histo_fixation_time, 'medium')),
        row('Fixation (large)', sizeTimeLabel(parameters.histo_fixation_time, 'large')),
        row('Grossing (small)', sizeTimeLabel(parameters.histo_grossing_time, 'small')),
        row('Grossing (medium)', sizeTimeLabel(parameters.histo_grossing_time, 'medium')),
        row('Grossing (large)', sizeTimeLabel(parameters.histo_grossing_time, 'large')),
        row(
          'Tissue processing',
          constantParam(parameters.histo_tissue_processing_time) != null
            ? `${constantParam(parameters.histo_tissue_processing_time)} min`
            : null,
        ),
        row(
          'Embedding',
          constantParam(parameters.histo_embedding_time) != null
            ? `${constantParam(parameters.histo_embedding_time)} min`
            : null,
        ),
        row(
          'Sectioning',
          constantParam(parameters.histo_sectioning_time) != null
            ? `${constantParam(parameters.histo_sectioning_time)} min`
            : null,
        ),
        row(
          'Staining',
          constantParam(parameters.histo_staining_time) != null
            ? `${constantParam(parameters.histo_staining_time)} min`
            : null,
        ),
        row('Screening (high)', triangularLabel(parameters.histo_slide_screening_time, 'high')),
        row('Screening (low)', triangularLabel(parameters.histo_slide_screening_time, 'low')),
        row('Reporting (high)', triangularLabel(parameters.histo_reporting_time, 'high')),
        row('Reporting (low)', triangularLabel(parameters.histo_reporting_time, 'low')),
      ]),
    },
  ];
}

function buildSections(
  kind: SimulationKind,
  parameters: ParametersDict,
  seed?: number | null,
): SummarySection[] {
  const sim = asRecord(parameters.simulation);
  const caseComplexity = asRecord(parameters.case_complexity);
  const disruptions = readDisruptions(parameters.disruptions);

  return [
    {
      title: 'Simulation',
      rows: compact([
        row('Modality', kind === 'cyto' ? 'Cytopathology' : 'Histopathology'),
        row('Duration (months)', sim.duration_months != null ? num(sim.duration_months) : null),
        row('Warm-up (months)', sim.warmup_months != null ? num(sim.warmup_months) : null),
        row(
          'P(high complexity)',
          caseComplexity.p_high != null ? num(caseComplexity.p_high) : null,
        ),
        row('RNG seed', seed != null ? seed : null),
      ]),
    },
    ...(kind === 'cyto' ? buildCytoSections(parameters) : buildHistoSections(parameters)),
    {
      title: 'Disruptions',
      rows:
        disruptions.length === 0
          ? [{ label: 'Active disruptions', value: 'None' }]
          : disruptions.map((d, i) => ({
              label: `Disruption ${i + 1}`,
              value: disruptionLabel(d),
            })),
    },
  ].filter((section) => section.rows.length > 0);
}

function SummarySections({
  sections,
  keyPrefix,
}: {
  sections: SummarySection[];
  keyPrefix: string;
}) {
  return (
    <>
      {sections.map((section) => (
        <section key={`${keyPrefix}-${section.title}`} className="run-summary__section">
          <h4>{section.title}</h4>
          <dl className="run-summary__list">
            {section.rows.map((item) => (
              <div key={`${keyPrefix}-${section.title}-${item.label}`} className="run-summary__row">
                <dt>{item.label}</dt>
                <dd>{item.value}</dd>
              </div>
            ))}
          </dl>
        </section>
      ))}
    </>
  );
}

export interface CompareSummaryRun {
  runId: string;
  kind: SimulationKind;
  parameters?: ParametersDict | null;
  seed?: number | null;
}

interface RunParameterSummaryProps {
  kind: SimulationKind;
  parameters: ParametersDict;
  seed?: number | null;
  runId?: string | null;
  compare?: CompareSummaryRun | null;
  onClearCompare?: () => void;
}

export function RunParameterSummary({
  kind,
  parameters,
  seed,
  runId,
  compare,
  onClearCompare,
}: RunParameterSummaryProps) {
  const primarySections = buildSections(kind, parameters, seed);
  const compareSections =
    compare?.parameters != null
      ? buildSections(compare.kind, compare.parameters, compare.seed)
      : null;

  if (compare) {
    return (
      <div className="run-summary run-summary--compare">
        <div className="run-summary__compare-toolbar">
          <h3>Run configurations</h3>
          {onClearCompare ? (
            <button type="button" className="text-button" onClick={onClearCompare}>
              Exit comparison
            </button>
          ) : null}
        </div>
        <div className="run-summary__split">
          <div className="run-summary__col">
            <div className="run-summary__col-header">
              <span className="run-summary__run-label">A</span>
              <div>
                <p className="run-summary__col-title">Run A</p>
                <p className="run-summary__run-id">{runId ?? 'Current'}</p>
              </div>
            </div>
            <div className="run-summary__grid">
              <SummarySections sections={primarySections} keyPrefix="a" />
            </div>
          </div>
          <div className="run-summary__col">
            <div className="run-summary__col-header">
              <span className="run-summary__run-label run-summary__run-label--b">B</span>
              <div>
                <p className="run-summary__col-title">Run B</p>
                <p className="run-summary__run-id">{compare.runId}</p>
              </div>
            </div>
            {compareSections ? (
              <div className="run-summary__grid">
                <SummarySections sections={compareSections} keyPrefix="b" />
              </div>
            ) : (
              <p className="muted run-summary__missing">
                No saved parameters for this run.
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="run-summary">
      <div className="run-summary__header">
        <h3>Run configuration</h3>
        <p className="muted">
          Parameters used for this simulation. Click <strong>New simulation</strong> to
          configure another run.
        </p>
      </div>
      <div className="run-summary__grid">
        <SummarySections sections={primarySections} keyPrefix="a" />
      </div>
    </div>
  );
}
