import { useMemo, useState } from 'react';
import { setRunDragData } from '../dnd';
import type { WorkspaceTab } from '../hooks/useWorkspace';
import type { RunHistoryEntry, SimulationKind } from '../types/simulation';

interface LeftPaneProps {
  kind: SimulationKind;
  onKindChange: (kind: SimulationKind) => void;
  history: RunHistoryEntry[];
  openTabs: WorkspaceTab[];
  activeTabId: string | null;
  onSelectTab: (tabId: string) => void;
  onCloseTab: (tabId: string) => void;
  onNewSimulation: () => void;
  onCopyParametersFromRun: (runId: string) => void;
  onDeleteRun: (runId: string) => void;
  isRunning: boolean;
  viewingResults: boolean;
  projectTitle: string;
  username: string;
  onLogout: () => void;
}

export function LeftPane({
  kind,
  onKindChange,
  history,
  openTabs,
  activeTabId,
  onSelectTab,
  onCloseTab,
  onNewSimulation,
  onCopyParametersFromRun,
  onDeleteRun,
  isRunning,
  viewingResults,
  projectTitle,
  username,
  onLogout,
}: LeftPaneProps) {
  const lockModality = isRunning || viewingResults;
  const [copyFromId, setCopyFromId] = useState('');

  const drafts = useMemo(
    () => openTabs.filter((tab): tab is Extract<WorkspaceTab, { type: 'draft' }> => tab.type === 'draft'),
    [openTabs],
  );

  const copyableRuns = useMemo(
    () => history.filter((entry) => entry.parameters),
    [history],
  );

  const handleCopy = () => {
    if (!copyFromId) return;
    onCopyParametersFromRun(copyFromId);
  };

  return (
    <aside className="left-pane">
      <header className="left-pane__brand">
        <p className="left-pane__eyebrow">Pathology DES</p>
        <h1>Simulation Lab</h1>
        <p className="left-pane__subtitle">{projectTitle || 'Parameter-driven model runs'}</p>
        <div className="left-pane__user">
          <span className="left-pane__username">{username}</span>
          <button type="button" className="text-button" onClick={onLogout} disabled={isRunning}>
            Log out
          </button>
        </div>
      </header>

      <section className="left-pane__section">
        <h2>Modality</h2>
        <div className="segmented">
          <button
            type="button"
            className={kind === 'cyto' ? 'active' : ''}
            onClick={() => onKindChange('cyto')}
            disabled={lockModality}
          >
            Cytopathology
          </button>
          <button
            type="button"
            className={kind === 'histo' ? 'active' : ''}
            onClick={() => onKindChange('histo')}
            disabled={lockModality}
          >
            Histopathology
          </button>
        </div>
      </section>

      <section className="left-pane__section left-pane__actions">
        <button
          type="button"
          className="run-button run-button--secondary"
          onClick={onNewSimulation}
          disabled={isRunning}
        >
          New simulation
        </button>

        <div className="copy-params">
          <label className="copy-params__label" htmlFor="copy-params-select">
            Copy parameters from run
          </label>
          <div className="copy-params__row">
            <select
              id="copy-params-select"
              value={copyFromId}
              onChange={(e) => setCopyFromId(e.target.value)}
              disabled={isRunning || viewingResults || copyableRuns.length === 0}
            >
              <option value="">
                {copyableRuns.length === 0 ? 'No runs with parameters' : 'Select a run…'}
              </option>
              {copyableRuns.map((entry) => (
                <option key={entry.run_id} value={entry.run_id}>
                  {entry.run_id} · {entry.lab}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="run-button run-button--secondary copy-params__btn"
              onClick={handleCopy}
              disabled={isRunning || viewingResults || !copyFromId}
            >
              Copy
            </button>
          </div>
        </div>
      </section>

      <section className="left-pane__section left-pane__history">
        <h2>Recent runs</h2>
        {history.length > 0 ? (
          <p className="muted left-pane__hint">
            Drag a run onto the main panel to compare side-by-side.
          </p>
        ) : null}
        {drafts.length === 0 && history.length === 0 ? (
          <p className="muted">No runs yet. Configure parameters and run.</p>
        ) : (
          <ul className="run-list">
            {drafts.map((tab) => (
              <li key={tab.id} className="run-list__item">
                <button
                  type="button"
                  className={`run-list__card${tab.id === activeTabId ? ' active' : ''}`}
                  onClick={() => onSelectTab(tab.id)}
                  disabled={isRunning}
                >
                  <span className="run-list__id">New simulation</span>
                  <span className="run-list__meta">{tab.kind} · draft</span>
                </button>
                <button
                  type="button"
                  className="run-list__icon-btn"
                  aria-label="Close draft"
                  title="Close draft"
                  onClick={(e) => {
                    e.stopPropagation();
                    onCloseTab(tab.id);
                  }}
                  disabled={isRunning}
                >
                  ×
                </button>
              </li>
            ))}
            {history.map((entry) => (
              <li key={entry.run_id} className="run-list__item">
                <button
                  type="button"
                  className={`run-list__card${entry.run_id === activeTabId ? ' active' : ''}`}
                  onClick={() => onSelectTab(entry.run_id)}
                  disabled={isRunning}
                  draggable={!isRunning}
                  onDragStart={(e) => {
                    setRunDragData(e.dataTransfer, entry.run_id);
                    e.dataTransfer.setDragImage(e.currentTarget, 40, 20);
                  }}
                  title="Click to open · drag onto main panel to compare"
                >
                  <span className="run-list__id">{entry.run_id}</span>
                  <span className="run-list__meta">
                    {entry.lab} · seed {entry.seed ?? '—'}
                  </span>
                </button>
                <button
                  type="button"
                  className="run-list__icon-btn run-list__icon-btn--danger"
                  aria-label={`Delete run ${entry.run_id}`}
                  title="Delete run"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteRun(entry.run_id);
                  }}
                  disabled={isRunning}
                >
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                    <line x1="10" y1="11" x2="10" y2="17" />
                    <line x1="14" y1="11" x2="14" y2="17" />
                  </svg>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </aside>
  );
}
