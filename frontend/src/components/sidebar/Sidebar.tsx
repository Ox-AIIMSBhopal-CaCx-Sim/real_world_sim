interface SidebarProps {
  onNewSim: () => void;
  projectTitle: string;
  isRunning: boolean;
}

export function Sidebar({ onNewSim, projectTitle, isRunning }: SidebarProps) {
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

      <section className="sidebar__section">
        <h2 className="sidebar__section-title">Current project</h2>
        <p className="sidebar__project-name">{projectTitle || 'Untitled'}</p>
      </section>

      <section className="sidebar__section sidebar__section--muted">
        <h2 className="sidebar__section-title">Simulation type</h2>
        <p className="sidebar__badge">Cytopathology</p>
        <p className="sidebar__hint">Histopathology will be added when the backend supports it.</p>
      </section>

      <footer className="sidebar__footer">
        <p>Configure parameters in the centre panel, then run to view results.</p>
      </footer>
    </div>
  );
}
