import type { SimulationSession } from '../../types/simulation';
import { SessionTab } from './SessionTab';

interface SidebarProps {
  sessions: SimulationSession[];
  activeSessionId: string;
  onNewSim: () => void;
  onSelectSession: (sessionId: string) => void;
  onRenameSession: (sessionId: string, label: string) => void;
  isRunning: boolean;
}

export function Sidebar({
  sessions,
  activeSessionId,
  onNewSim,
  onSelectSession,
  onRenameSession,
  isRunning,
}: SidebarProps) {
  const active = sessions.find((s) => s.id === activeSessionId);
  const history = [...sessions].reverse();

  return (
    <div className="sidebar">
      <header className="sidebar__brand">
        <span className="sidebar__logo">DES</span>
        <div>
          <h1 className="sidebar__title">Pathology Sim</h1>
          <p className="sidebar__subtitle">Discrete event simulation</p>
        </div>
      </header>

      <button
        type="button"
        className="btn btn--primary btn--block"
        onClick={onNewSim}
        disabled={isRunning}
      >
        New Sim
      </button>

      <section className="sidebar__section sidebar__section--grow">
        <h2 className="sidebar__section-title">Simulations</h2>
        <ul className="session-list" role="tablist" aria-label="Saved simulations">
          {history.map((session) => (
            <li key={session.id}>
              <SessionTab
                session={session}
                isActive={session.id === activeSessionId}
                disabled={isRunning}
                onSelect={() => onSelectSession(session.id)}
                onRename={(label) => onRenameSession(session.id, label)}
              />
            </li>
          ))}
        </ul>
      </section>

      {active && (
        <section className="sidebar__section">
          <h2 className="sidebar__section-title">Current project</h2>
          <p className="sidebar__project-name">{active.parameters.project_title || 'Untitled'}</p>
        </section>
      )}

      <section className="sidebar__section sidebar__section--muted">
        <h2 className="sidebar__section-title">Simulation type</h2>
        <p className="sidebar__badge">Cytopathology</p>
      </section>

      <footer className="sidebar__footer">
        <p>Double-click or use ✎ to rename a simulation. Tabs restore parameters and results.</p>
      </footer>
    </div>
  );
}
