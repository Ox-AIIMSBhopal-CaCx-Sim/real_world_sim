import { useEffect, useState } from 'react';
import Papa from 'papaparse';
import type { SimulationRunResult } from '../types/simulation';

interface ResultsPanelProps {
  result: SimulationRunResult | null;
  isRunning: boolean;
  error: string | null;
}

function humanize(key: string): string {
  return key.replace(/_/g, ' ');
}

function CsvTable({ url, title }: { url: string; title: string }) {
  const [rows, setRows] = useState<string[][]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoadError(null);
    setRows([]);
    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load ${title}`);
        return res.text();
      })
      .then((text) => {
        if (cancelled) return;
        const parsed = Papa.parse<string[]>(text, { skipEmptyLines: true });
        setRows((parsed.data as string[][]).slice(0, 51));
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
  return (
    <div className="result-block">
      <div className="result-block__header">
        <h4>{title}</h4>
        <a href={url} target="_blank" rel="noreferrer">
          Download
        </a>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              {header.map((cell) => (
                <th key={cell}>{cell}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {body.map((row, i) => (
              <tr key={`${title}-${i}`}>
                {row.map((cell, j) => (
                  <td key={`${i}-${j}`}>{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function ResultsPanel({ result, isRunning, error }: ResultsPanelProps) {
  if (isRunning) {
    return (
      <div className="results-panel">
        <p className="muted">Simulation running — this may take a minute…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="results-panel">
        <p className="error-text">{error}</p>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="results-panel">
        <p className="muted">
          Results appear here after a run. Tables and plots are loaded from analysis artifact URLs.
        </p>
      </div>
    );
  }

  const { artifacts } = result;
  const tableEntries = Object.entries(artifacts.tables);
  const plotEntries = Object.entries(artifacts.plots);
  const dataEntries = Object.entries(artifacts.data);

  return (
    <div className="results-panel">
      <div className="results-panel__meta">
        <h3>Results · {result.run_id}</h3>
        <p className="muted">
          {result.lab} · status {result.status}
          {result.seed != null ? ` · seed ${result.seed}` : ''}
        </p>
      </div>

      {plotEntries.length > 0 ? (
        <section className="results-section">
          <h3>Plots</h3>
          <div className="plot-grid">
            {plotEntries.map(([key, url]) => (
              <figure key={key} className="plot-card">
                <figcaption>{humanize(key)}</figcaption>
                <a href={url} target="_blank" rel="noreferrer">
                  <img src={url} alt={humanize(key)} />
                </a>
              </figure>
            ))}
          </div>
        </section>
      ) : null}

      {tableEntries.length > 0 ? (
        <section className="results-section">
          <h3>Summary tables</h3>
          {tableEntries.map(([key, url]) => (
            <CsvTable key={key} url={url} title={humanize(key)} />
          ))}
        </section>
      ) : null}

      {dataEntries.length > 0 ? (
        <section className="results-section">
          <h3>Raw data</h3>
          <ul className="download-list">
            {dataEntries.map(([key, url]) => (
              <li key={key}>
                <a href={url} target="_blank" rel="noreferrer">
                  {humanize(key)}
                </a>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
