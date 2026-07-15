import type { SimulationKind } from '../types/simulation';
import { getPipelineSteps, type PipelineStepId } from './pipelineConfig';
import { ResourceIcon } from './ResourceIcons';

interface PipelineStepsProps {
  kind: SimulationKind;
  selectedStepId: PipelineStepId | null;
  onSelectStep: (stepId: PipelineStepId) => void;
}

export function PipelineSteps({ kind, selectedStepId, onSelectStep }: PipelineStepsProps) {
  const steps = getPipelineSteps(kind);

  return (
    <div className="pipeline">
      <div className="pipeline__header">
        <h3>Process pipeline</h3>
        <p className="muted">Click a step to edit its parameters</p>
      </div>
      <ol className="pipeline__cards">
        {steps.map((step, index) => {
          const selected = step.id === selectedStepId;
          return (
            <li key={step.id}>
              <button
                type="button"
                className={`pipeline-card${selected ? ' pipeline-card--selected' : ''}`}
                onClick={() => onSelectStep(step.id)}
                aria-pressed={selected}
              >
                <span className="pipeline-card__index">{index + 1}</span>
                <span className="pipeline-card__name">{step.name}</span>
                <span className="pipeline-card__desc">{step.description}</span>
                <span className="pipeline-card__resources" aria-label="Resources involved">
                  {step.resources.map((resource) => (
                    <ResourceIcon key={resource} kind={resource} />
                  ))}
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
