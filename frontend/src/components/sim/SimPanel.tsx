import type { CytoParameters } from '../../types/simulation';
import { ParameterEditor } from './ParameterEditor';
import { PipelineDiagram } from './PipelineDiagram';

interface SimPanelProps {
  parameters: CytoParameters;
  onParametersChange: (p: CytoParameters) => void;
  onRun: () => void;
  isRunning: boolean;
  error: string | null;
}

export function SimPanel({
  parameters,
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

      <PipelineDiagram />

      {error && <p className="sim-panel__error" role="alert">{error}</p>}

      <div className="sim-panel__params">
        <h2 className="sim-panel__params-title">Parameters</h2>
        <ParameterEditor
          parameters={parameters}
          onChange={onParametersChange}
          disabled={isRunning}
        />
      </div>
    </div>
  );
}
