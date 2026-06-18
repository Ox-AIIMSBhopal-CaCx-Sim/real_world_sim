import type {
  CytoParameters,
  HistoParameters,
  SimulationKind,
  SimulationParameters,
} from '../../types/simulation';
import { CytoInteractivePanel } from './cyto/CytoInteractivePanel';
import { HistoInteractivePanel } from './histo/HistoInteractivePanel';
import { ModalityToggle } from './ModalityToggle';

interface SimPanelProps {
  kind: SimulationKind;
  parameters: SimulationParameters;
  onKindChange: (kind: SimulationKind) => void;
  onParametersChange: (p: SimulationParameters) => void;
  onRun: () => void;
  isRunning: boolean;
  error: string | null;
}

export function SimPanel({
  kind,
  parameters,
  onKindChange,
  onParametersChange,
  onRun,
  isRunning,
  error,
}: SimPanelProps) {
  return (
    <div className="sim-panel">
      <header className="sim-panel__header">
        <div>
          <h2 className="sim-panel__title">Simulation panel</h2>
          <p className="sim-panel__subtitle">{parameters.project_title}</p>
        </div>
        <button
          type="button"
          className="btn btn--run"
          onClick={onRun}
          disabled={isRunning}
        >
          {isRunning ? 'Running…' : 'Run Simulation'}
        </button>
      </header>

      <ModalityToggle kind={kind} onChange={onKindChange} disabled={isRunning} />

      {error && (
        <p className="sim-panel__error" role="alert">
          {error}
        </p>
      )}

      {kind === 'cyto' ? (
        <CytoInteractivePanel
          parameters={parameters as CytoParameters}
          onChange={onParametersChange}
          disabled={isRunning}
        />
      ) : (
        <HistoInteractivePanel
          parameters={parameters as HistoParameters}
          onChange={onParametersChange}
          disabled={isRunning}
        />
      )}
    </div>
  );
}
