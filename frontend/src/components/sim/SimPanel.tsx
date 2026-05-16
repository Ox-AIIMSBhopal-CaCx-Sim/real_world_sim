import type {
  CytoParameters,
  HistoParameters,
  SimulationKind,
  SimulationParameters,
} from '../../types/simulation';
import { HistoParameterEditor } from './HistoParameterEditor';
import { ModalityToggle } from './ModalityToggle';
import { ParameterEditor } from './ParameterEditor';
import { PipelineDiagram } from './PipelineDiagram';

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

      <PipelineDiagram kind={kind} />

      {error && (
        <p className="sim-panel__error" role="alert">
          {error}
        </p>
      )}

      <div className="sim-panel__params">
        <h2 className="sim-panel__params-title">Parameters</h2>
        {kind === 'cyto' ? (
          <ParameterEditor
            parameters={parameters as CytoParameters}
            onChange={onParametersChange}
            disabled={isRunning}
          />
        ) : (
          <HistoParameterEditor
            parameters={parameters as HistoParameters}
            onChange={onParametersChange}
            disabled={isRunning}
          />
        )}
      </div>
    </div>
  );
}
