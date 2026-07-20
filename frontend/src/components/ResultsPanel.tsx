import { useEffect, useMemo, useState } from 'react';
import Papa from 'papaparse';
import { resolveArtifactUrl } from '../api/client';
import type { SimulationKind, SimulationRunResult } from '../types/simulation';

interface ResultsPanelProps {
  result: SimulationRunResult | null;
  isRunning: boolean;
  error: string | null;
  /** Narrower layout for side-by-side compare columns. */
  compact?: boolean;
  heading?: string;
}

/** Featured plot keys in display order, per modality. */
const FEATURED_PLOT_KEYS: Record<SimulationKind, string[]> = {
  cyto: [
    'turnaround_patient_pap_smear',
    'turnaround_patient_non_pap_smear',
    'resource_utilisation',
  ],
  histo: [
    'turnaround_patient_cervical_biopsy',
    'turnaround_patient_non_cervical_biopsy',
    'resource_utilisation',
  ],
};

const FEATURED_TITLES: Record<string, string> = {
  turnaround_patient_pap_smear: 'Turnaround time · Pap smear',
  turnaround_patient_non_pap_smear: 'Turnaround time · Non-Pap',
  turnaround_patient_cervical_biopsy: 'Turnaround time · Cervical biopsy',
  turnaround_patient_non_cervical_biopsy: 'Turnaround time · Non-cervical biopsy',
  resource_utilisation: 'Resource utilisation (%)',
};

const DESCRIBE_STAT_ORDER = ['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max'];

const DESCRIBE_STAT_LABELS: Record<string, string> = {
  count: 'count',
  mean: 'mean',
  std: 'std',
  min: 'min',
  '25%': '25%',
  '50%': '50%',
  '75%': '75%',
  max: 'max',
};

type TatSummaryRow = {
  group: string;
  process: string;
  stat: string;
  value: number;
};

function humanize(key: string): string {
  return FEATURED_TITLES[key] ?? key.replace(/_/g, ' ');
}

function groupFromTurnaroundPlotKey(plotKey: string): string | null {
  if (plotKey === 'turnaround_patient') return 'all';
  if (plotKey.startsWith('turnaround_patient_')) {
    return plotKey.slice('turnaround_patient_'.length);
  }
  return null;
}

function formatStatValue(stat: string, value: number): string {
  if (!Number.isFinite(value)) return '—';
  if (stat === 'count') return String(Math.round(value));
  return value.toFixed(3);
}

function PlotFigure({
  plotKey,
  url,
  featured = false,
}: {
  plotKey: string;
  url: string;
  featured?: boolean;
}) {
  const title = humanize(plotKey);
  const resolved = resolveArtifactUrl(url);
  return (
    <figure className={`plot-card${featured ? ' plot-card--featured' : ''}`}>
      <figcaption>{title}</figcaption>
      <a href={resolved} target="_blank" rel="noreferrer">
        <img src={resolved} alt={title} />
      </a>
    </figure>
  );
}

function TatDescribeStats({
  rows,
  loading,
  error,
}: {
  rows: TatSummaryRow[];
  loading: boolean;
  error: string | null;
}) {
  if (loading) {
    return <p className="muted tat-describe__status">Loading summary…</p>;
  }
  if (error) {
    return <p className="error-text tat-describe__status">{error}</p>;
  }
  if (rows.length === 0) {
    return <p className="muted tat-describe__status">No summary stats available.</p>;
  }

  const byStat = new Map(rows.map((row) => [row.stat, row.value]));
  const ordered = DESCRIBE_STAT_ORDER.filter((stat) => byStat.has(stat));
  const extras = [...byStat.keys()].filter((stat) => !DESCRIBE_STAT_ORDER.includes(stat));
  const stats = [...ordered, ...extras];

  return (
    <div className="tat-describe">
      <h4>Turnaround summary</h4>
      <p className="muted tat-describe__hint">.describe() · days</p>
      <dl className="tat-describe__list">
        {stats.map((stat) => (
          <div key={stat} className="tat-describe__row">
            <dt>{DESCRIBE_STAT_LABELS[stat] ?? stat}</dt>
            <dd>{formatStatValue(stat, Number(byStat.get(stat)))}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function useTatSummary(url: string | undefined): {
  rows: TatSummaryRow[];
  loading: boolean;
  error: string | null;
} {
  const [rows, setRows] = useState<TatSummaryRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!url) {
      setRows([]);
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    setRows([]);

    fetch(resolveArtifactUrl(url))
      .then((res) => {
        if (!res.ok) throw new Error('Failed to load turnaround summary');
        return res.text();
      })
      .then((text) => {
        if (cancelled) return;
        const parsed = Papa.parse<Record<string, string>>(text, {
          header: true,
          skipEmptyLines: true,
        });
        const next: TatSummaryRow[] = (parsed.data ?? [])
          .filter((row) => row.stat != null && row.stat !== '')
          .map((row) => ({
            group: String(row.group ?? 'all'),
            process: String(row.process ?? 'turnaround'),
            stat: String(row.stat),
            value: Number(row.value),
          }));
        setRows(next);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [url]);

  return { rows, loading, error };
}

const SAMPLE_CHUNK = 10;

type TableSegment =
  | { kind: 'rows'; startIndex: number; rows: string[][] }
  | { kind: 'gap'; omitted: number };

/** For long tables: first 10, middle 10, last 10 data rows (header separate). */
function sampleTableSegments(body: string[][]): TableSegment[] {
  const n = body.length;
  if (n <= SAMPLE_CHUNK * 3) {
    return n === 0 ? [] : [{ kind: 'rows', startIndex: 0, rows: body }];
  }

  const first = body.slice(0, SAMPLE_CHUNK);
  const lastStart = n - SAMPLE_CHUNK;
  const last = body.slice(lastStart);

  let midStart = Math.floor((n - SAMPLE_CHUNK) / 2);
  midStart = Math.max(SAMPLE_CHUNK, Math.min(midStart, lastStart - SAMPLE_CHUNK));
  const middle = body.slice(midStart, midStart + SAMPLE_CHUNK);

  const segments: TableSegment[] = [{ kind: 'rows', startIndex: 0, rows: first }];

  const gapBeforeMid = midStart - SAMPLE_CHUNK;
  if (gapBeforeMid > 0) {
    segments.push({ kind: 'gap', omitted: gapBeforeMid });
  }
  segments.push({ kind: 'rows', startIndex: midStart, rows: middle });

  const midEnd = midStart + SAMPLE_CHUNK;
  const gapBeforeLast = lastStart - midEnd;
  if (gapBeforeLast > 0) {
    segments.push({ kind: 'gap', omitted: gapBeforeLast });
  }
  segments.push({ kind: 'rows', startIndex: lastStart, rows: last });

  return segments;
}

function isTextArtifact(key: string, url: string): boolean {
  const lower = `${key} ${url}`.toLowerCase();
  return (
    lower.includes('.yaml') ||
    lower.includes('.yml') ||
    lower.includes('.json') ||
    key === 'run_manifest'
  );
}

function CsvTable({ url, title }: { url: string; title: string }) {
  const [rows, setRows] = useState<string[][]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoadError(null);
    setRows([]);
    fetch(resolveArtifactUrl(url))
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load ${title}`);
        return res.text();
      })
      .then((text) => {
        if (cancelled) return;
        const parsed = Papa.parse<string[]>(text, { skipEmptyLines: true });
        setRows(parsed.data as string[][]);
      })
      .catch((err: Error) => {
        if (!cancelled) setLoadError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [url, title]);

  if (loadError) {
    return (
      <div className="result-block">
        <h4>{title}</h4>
        <p className="error-text">{loadError}</p>
      </div>
    );
  }

  if (rows.length === 0) {
    return (
      <div className="result-block">
        <h4>{title}</h4>
        <p className="muted">Loading table…</p>
      </div>
    );
  }

  const [header, ...body] = rows;
  const segments = sampleTableSegments(body);
  const sampled = body.length > SAMPLE_CHUNK * 3;
  const colCount = Math.max(header.length, 1);

  return (
    <div className="result-block">
      <div className="result-block__header">
        <h4>{title}</h4>
        <a href={resolveArtifactUrl(url)} target="_blank" rel="noreferrer">
          Download
        </a>
      </div>
      {sampled ? (
        <p className="muted table-sample-hint">
          Showing first {SAMPLE_CHUNK}, middle {SAMPLE_CHUNK}, and last {SAMPLE_CHUNK} of{' '}
          {body.length.toLocaleString()} rows
        </p>
      ) : null}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              {header.map((cell, j) => (
                <th key={`${title}-h-${j}`}>{cell}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {segments.flatMap((segment, sIdx) => {
              if (segment.kind === 'gap') {
                return [
                  <tr key={`${title}-gap-${sIdx}`} className="table-gap-row">
                    <td colSpan={colCount}>
                      … {segment.omitted.toLocaleString()} rows omitted …
                    </td>
                  </tr>,
                ];
              }
              return segment.rows.map((row, i) => (
                <tr key={`${title}-${segment.startIndex + i}`}>
                  {row.map((cell, j) => (
                    <td key={`${segment.startIndex + i}-${j}`}>{cell}</td>
                  ))}
                </tr>
              ));
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RawDataViewer({
  dataKey,
  url,
  title,
}: {
  dataKey: string;
  url: string;
  title: string;
}) {
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState<string[][] | null>(null);
  const [text, setText] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const asText = isTextArtifact(dataKey, url);

  useEffect(() => {
    setOpen(false);
    setRows(null);
    setText(null);
    setLoadError(null);
    setLoading(false);
  }, [url]);

  useEffect(() => {
    if (!open || rows != null || text != null || loadError) return;

    let cancelled = false;
    setLoading(true);
    setLoadError(null);

    fetch(resolveArtifactUrl(url))
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load ${title}`);
        return res.text();
      })
      .then((raw) => {
        if (cancelled) return;
        if (asText) {
          setText(raw);
          return;
        }
        const parsed = Papa.parse<string[]>(raw, { skipEmptyLines: true });
        setRows(parsed.data as string[][]);
      })
      .catch((err: Error) => {
        if (!cancelled) setLoadError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [open, url, title, asText, rows, text, loadError]);

  const header = rows && rows.length > 0 ? rows[0] : [];
  const body = rows && rows.length > 1 ? rows.slice(1) : [];
  const segments = sampleTableSegments(body);
  const sampled = body.length > SAMPLE_CHUNK * 3;
  const colCount = Math.max(header.length, 1);

  return (
    <div className={`raw-data-item${open ? ' raw-data-item--open' : ''}`}>
      <div className="raw-data-item__bar">
        <button
          type="button"
          className="raw-data-item__toggle"
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          <span className="raw-data-item__chevron" aria-hidden>
            {open ? '▾' : '▸'}
          </span>
          <span>{title}</span>
        </button>
        <a href={resolveArtifactUrl(url)} target="_blank" rel="noreferrer" className="raw-data-item__download">
          Download
        </a>
      </div>

      {open ? (
        <div className="raw-data-item__body">
          {loading ? <p className="muted">Loading…</p> : null}
          {loadError ? <p className="error-text">{loadError}</p> : null}
          {text != null ? <pre className="raw-data-pre">{text}</pre> : null}
          {rows != null && rows.length > 0 ? (
            <>
              {sampled ? (
                <p className="muted table-sample-hint">
                  Showing first {SAMPLE_CHUNK}, middle {SAMPLE_CHUNK}, and last {SAMPLE_CHUNK} of{' '}
                  {body.length.toLocaleString()} rows
                </p>
              ) : (
                <p className="muted table-sample-hint">
                  {body.length.toLocaleString()} row{body.length === 1 ? '' : 's'}
                </p>
              )}
              <div className="table-wrap table-wrap--raw">
                <table>
                  <thead>
                    <tr>
                      {header.map((cell, j) => (
                        <th key={`${dataKey}-h-${j}`}>{cell}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {segments.flatMap((segment, sIdx) => {
                      if (segment.kind === 'gap') {
                        return [
                          <tr key={`${dataKey}-gap-${sIdx}`} className="table-gap-row">
                            <td colSpan={colCount}>
                              … {segment.omitted.toLocaleString()} rows omitted …
                            </td>
                          </tr>,
                        ];
                      }
                      return segment.rows.map((row, i) => (
                        <tr key={`${dataKey}-${segment.startIndex + i}`}>
                          {row.map((cell, j) => (
                            <td key={`${segment.startIndex + i}-${j}`}>{cell}</td>
                          ))}
                        </tr>
                      ));
                    })}
                  </tbody>
                </table>
              </div>
            </>
          ) : null}
          {rows != null && rows.length === 0 && !loading && !loadError ? (
            <p className="muted">Empty file.</p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function partitionPlots(
  plots: Record<string, string>,
  lab: SimulationKind,
): { featured: [string, string][]; other: [string, string][] } {
  const preferred = FEATURED_PLOT_KEYS[lab] ?? FEATURED_PLOT_KEYS.cyto;
  const featured: [string, string][] = [];
  const used = new Set<string>();

  for (const key of preferred) {
    if (plots[key]) {
      featured.push([key, plots[key]]);
      used.add(key);
    }
  }

  if (featured.length === 0) {
    for (const [key, url] of Object.entries(plots)) {
      if (key.startsWith('turnaround_patient') && !used.has(key)) {
        featured.push([key, url]);
        used.add(key);
      }
    }
  }

  if (plots.resource_utilisation && !used.has('resource_utilisation')) {
    featured.push(['resource_utilisation', plots.resource_utilisation]);
    used.add('resource_utilisation');
  }

  const other = Object.entries(plots).filter(([key]) => !used.has(key));
  return { featured, other };
}

export function ResultsPanel({
  result,
  isRunning,
  error,
  compact = false,
  heading,
}: ResultsPanelProps) {
  const [showMore, setShowMore] = useState(false);

  useEffect(() => {
    setShowMore(false);
  }, [result?.run_id]);

  const partitioned = useMemo(() => {
    if (!result) return { featured: [] as [string, string][], other: [] as [string, string][] };
    return partitionPlots(result.artifacts.plots, result.lab);
  }, [result]);

  const tatSummaryUrl = result?.artifacts.tables.turnaround_time_patient_summary;
  const {
    rows: tatSummaryRows,
    loading: tatLoading,
    error: tatError,
  } = useTatSummary(tatSummaryUrl);

  const panelClass = `results-panel${compact ? ' results-panel--compact' : ''}`;

  if (isRunning) {
    return (
      <div className={panelClass}>
        <p className="muted">Simulation running — this may take a minute…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className={panelClass}>
        <p className="error-text">{error}</p>
      </div>
    );
  }

  if (!result) {
    return (
      <div className={panelClass}>
        <p className="muted">
          Results appear here after a run. Tables and plots are loaded from analysis artifact URLs.
        </p>
      </div>
    );
  }

  const { artifacts } = result;
  const tableEntries = Object.entries(artifacts.tables).filter(
    ([key]) => key !== 'turnaround_time_patient_summary',
  );
  const dataEntries = Object.entries(artifacts.data);
  const { featured, other } = partitioned;
  const hasMore =
    other.length > 0 || tableEntries.length > 0 || dataEntries.length > 0;

  return (
    <div className={panelClass}>
      <div className="results-panel__meta">
        <h3>
          {heading ?? 'Results'} · {result.run_id}
        </h3>
        <p className="muted">
          {result.lab} · status {result.status}
          {result.seed != null ? ` · seed ${result.seed}` : ''}
        </p>
      </div>

      {featured.length > 0 ? (
        <section className="results-section">
          <h3>Key plots</h3>
          <div className="plot-stack">
            {featured.map(([key, url]) => {
              const group = groupFromTurnaroundPlotKey(key);
              const groupRows =
                group == null
                  ? []
                  : tatSummaryRows.filter(
                      (row) =>
                        row.group === group &&
                        (row.process === 'turnaround' || !row.process),
                    );

              if (group != null) {
                return (
                  <div key={key} className="featured-tat-row">
                    <PlotFigure plotKey={key} url={url} featured />
                    <TatDescribeStats
                      rows={groupRows}
                      loading={tatLoading}
                      error={tatError}
                    />
                  </div>
                );
              }

              return <PlotFigure key={key} plotKey={key} url={url} featured />;
            })}
          </div>
        </section>
      ) : null}

      {hasMore ? (
        <section className="results-section results-section--more">
          <button
            type="button"
            className="results-more-toggle"
            aria-expanded={showMore}
            onClick={() => setShowMore((open) => !open)}
          >
            {showMore ? 'Hide additional results' : 'Show additional plots & tables'}
          </button>

          {showMore ? (
            <div className="results-more">
              {other.length > 0 ? (
                <div className="results-more__block">
                  <h4>Other plots</h4>
                  <div className="plot-grid">
                    {other.map(([key, url]) => (
                      <PlotFigure key={key} plotKey={key} url={url} />
                    ))}
                  </div>
                </div>
              ) : null}

              {tableEntries.length > 0 ? (
                <div className="results-more__block">
                  <h4>Summary tables</h4>
                  {tableEntries.map(([key, url]) => (
                    <CsvTable key={key} url={url} title={humanize(key)} />
                  ))}
                </div>
              ) : null}

              {dataEntries.length > 0 ? (
                <div className="results-more__block">
                  <h4>Raw data</h4>
                  <p className="muted raw-data-hint">
                    Click a dataset to preview inline. Long tables show the first, middle, and last{' '}
                    {SAMPLE_CHUNK} rows.
                  </p>
                  <div className="raw-data-list">
                    {dataEntries.map(([key, url]) => (
                      <RawDataViewer
                        key={key}
                        dataKey={key}
                        url={url}
                        title={humanize(key)}
                      />
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
