import type { SimulationKind } from '../types/simulation';

const CYTO_STEPS = [
  'Accessioning',
  'Fixation',
  'Staining',
  'Screening',
  'Reporting',
];

const HISTO_STEPS = [
  'Fixation',
  'Grossing',
  'Tissue processing',
  'Embedding',
  'Sectioning',
  'Staining',
  'Screening',
  'Reporting',
];

export function PipelineSteps({ kind }: { kind: SimulationKind }) {
  const steps = kind === 'cyto' ? CYTO_STEPS : HISTO_STEPS;
  return (
    <div className="pipeline">
      <h3>Process pipeline</h3>
      <ol className="pipeline__steps">
        {steps.map((step, index) => (
          <li key={step}>
            <span className="pipeline__index">{index + 1}</span>
            <span>{step}</span>
            {index < steps.length - 1 ? <span className="pipeline__arrow" aria-hidden>→</span> : null}
          </li>
        ))}
      </ol>
    </div>
  );
}
