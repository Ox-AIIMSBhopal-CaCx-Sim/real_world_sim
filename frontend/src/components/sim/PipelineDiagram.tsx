import { CYTO_PIPELINE_STAGES } from '../../data/defaultParameters';

export function PipelineDiagram() {
  return (
    <div className="pipeline">
      <h2 className="pipeline__title">Cytopathology workflow</h2>
      <div
        className="pipeline__track"
        role="img"
        aria-label="Simulation pipeline from patient arrival to reporting"
      >
        {CYTO_PIPELINE_STAGES.map((stage, index) => (
          <div key={stage.id} className="pipeline__stage-wrap">
            <div className="pipeline__stage">
              <span className="pipeline__stage-index">{index + 1}</span>
              <strong>{stage.label}</strong>
              <span className="pipeline__stage-detail">{stage.detail}</span>
            </div>
            {index < CYTO_PIPELINE_STAGES.length - 1 && (
              <span className="pipeline__arrow" aria-hidden="true">
                →
              </span>
            )}
          </div>
        ))}
      </div>
      <p className="pipeline__legend">
        <em>Pap</em> and <em>non-Pap</em> patients arrive via Poisson processes, split into slides at
        accessioning, then flow through fixation and batched staining before pathologist reporting.
      </p>
    </div>
  );
}
