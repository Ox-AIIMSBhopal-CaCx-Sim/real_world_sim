import type { RunHistoryEntry, SimulationKind } from '../types/simulation';

interface LeftPaneProps {
  kind: SimulationKind;
  onKindChange: (kind: SimulationKind) => void;
  seed: number;
  onSeedChange: (seed: number) => void;
  history: RunHistoryEntry[];
  activeRunId: string | null;
  onSelectRun: (runId: string) => void;
  onRun: () => void;
  isRunning: boolean;
  projectTitle: string;
}

export function LeftPane({
  kind,
  onKindChange,
  seed,
  onSeedChange,
  history,
  activeRunId,
  onSelectRun,
  onRun,
  isRunning,
  projectTitle,
}: LeftPaneProps) {
  return (
    <aside className="left-pane">
      <header className="left-pane__brand">
        <p className="left-pane__eyebrow">Pathology DES</p>
        <h1>Simulation Lab</h1>
        <p className="left-pane__subtitle">{projectTitle || 'Parameter-driven model runs'}</p>
      </header>

      <section className="left-pane__section">
        <h2>Modality</h2>
        <div className="segmented">
          <button
            type="button"
            className={kind === 'cyto' ? 'active' : ''}
            onClick={() => onKindChange('cyto')}
            disabled={isRunning}
          >
            Cytopathology
          </button>
          <button
            type="button"
            className={kind === 'histo' ? 'active' : ''}
            onClick={() => onKindChange('histo')}
            disabled={isRunning}
          >
            Histopathology
          </button>
        </div>
      </section>

      <section className="left-pane__section">
        <h2>Settings</h2>
        <label className="field">
          <span>RNG seed</span>
          <input
            type="number"
            value={seed}
            onChange={(e) => onSeedChange(Number(e.target.value))}
            disabled={isRunning}
          />
        </label>
        <button type="button" className="run-button" onClick={onRun} disabled={isRunning}>
          {isRunning ? 'Running…' : 'Run simulation'}
        </button>
      </section>

      <section className="left-pane__section left-pane__history">
        <h2>Recent runs</h2>
        {history.length === 0 ? (
          <p className="muted">No runs yet. Configure parameters and run.</p>
        ) : (
          <ul className="run-list">
            {history.map((entry) => (
              <li key={entry.run_id}>
                <button
                  type="button"
                  className={entry.run_id === activeRunId ? 'active' : ''}
                  onClick={() => onSelectRun(entry.run_id)}
                >
                  <span className="run-list__id">{entry.run_id}</span>
                  <span className="run-list__meta">
                    {entry.lab} · seed {entry.seed ?? '—'}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </aside>
  );
}
