import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { SimulationRunResult } from '../../types/simulation';

interface ResultsPanelProps {
  results: SimulationRunResult | null;
  isRunning: boolean;
}

export function ResultsPanel({ results, isRunning }: ResultsPanelProps) {
  if (isRunning) {
    return (
      <div className="results-panel results-panel--empty">
        <div className="results-panel__spinner" aria-hidden="true" />
        <p>Running simulation…</p>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="results-panel results-panel--empty">
        <h2>Results</h2>
        <p>Run a simulation to see turnaround metrics, charts, and breakdown tables here.</p>
      </div>
    );
  }

  return (
    <div className="results-panel">
      <header className="results-panel__header">
        <h2>Results</h2>
        <time className="results-panel__time" dateTime={results.completedAt}>
          {new Date(results.completedAt).toLocaleString()}
        </time>
      </header>

      <p className="results-panel__summary">{results.summary}</p>

      <section className="results-section">
        <h3>Key metrics</h3>
        <div className="metrics-grid">
          {results.metrics.map((m) => (
            <article key={m.label} className="metric-card">
              <span className="metric-card__label">{m.label}</span>
              <span className="metric-card__value">{m.value}</span>
              {m.detail && <span className="metric-card__detail">{m.detail}</span>}
            </article>
          ))}
        </div>
      </section>

      <section className="results-section">
        <h3>Turnaround time distribution</h3>
        <div className="chart-wrap">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart
              data={results.turnaroundHistogram}
              margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="range" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="count" fill="var(--accent)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="results-section">
        <h3>Patient type breakdown</h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>Type</th>
              <th>Count</th>
              <th>Median TAT (days)</th>
            </tr>
          </thead>
          <tbody>
            {results.patientBreakdown.map((row) => (
              <tr key={row.type}>
                <td>{row.type}</td>
                <td>{row.count.toLocaleString()}</td>
                <td>{row.medianTatDays.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {results.notes.length > 0 && (
        <section className="results-section">
          <h3>Notes</h3>
          <ul className="results-notes">
            {results.notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
