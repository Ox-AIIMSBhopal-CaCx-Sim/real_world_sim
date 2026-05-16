import { CYTO_PIPELINE_STAGES, HISTO_PIPELINE_STAGES } from '../../data/defaultParameters';
import type { SimulationKind } from '../../types/simulation';

interface PipelineDiagramProps {
  kind: SimulationKind;
}

export function PipelineDiagram({ kind }: PipelineDiagramProps) {
  const stages = kind === 'cyto' ? CYTO_PIPELINE_STAGES : HISTO_PIPELINE_STAGES;
  const title = kind === 'cyto' ? 'Cytopathology workflow' : 'Histopathology workflow';
  const legend =
    kind === 'cyto' ? (
      <>
        <em>Pap</em> and <em>non-Pap</em> patients arrive via Poisson processes, split into slides at
        accessioning, then flow through fixation and batched staining before pathologist reporting.
      </>
    ) : (
      <>
        <em>Cervical</em> and <em>other</em> biopsies arrive via Poisson processes; fixation and
        grossing are patient-level, then blocks flow through tissue processing, embedding, sectioning,
        and batched staining before reporting.
      </>
    );

  return (
    <div className="pipeline">
      <h2 className="pipeline__title">{title}</h2>
      <div
        className="pipeline__track"
        role="img"
        aria-label={`${title} from arrival to reporting`}
      >
        {stages.map((stage, index) => (
          <div key={stage.id} className="pipeline__stage-wrap">
            <div className="pipeline__stage">
              <span className="pipeline__stage-index">{index + 1}</span>
              <strong>{stage.label}</strong>
              <span className="pipeline__stage-detail">{stage.detail}</span>
            </div>
            {index < stages.length - 1 && (
              <span className="pipeline__arrow" aria-hidden="true">
                →
              </span>
            )}
          </div>
        ))}
      </div>
      <p className="pipeline__legend">{legend}</p>
    </div>
  );
}
