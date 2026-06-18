import { useMemo, useState } from 'react';
import type { CytoParameters } from '../../../types/simulation';
import { normalizeCytoParameters } from '../../../data/defaultParameters';
import {
  ProcessingEquipment,
  ProcessingProfessional,
  ReceptionEquipment,
  ReceptionProfessional,
  ReportingEquipment,
  ReportingProfessional,
} from './CytoCartoons';
import { CytoResourcePanel, type CytoResourceSelection } from './CytoResourcePanel';

interface CytoInteractivePanelProps {
  parameters: CytoParameters;
  onChange: (parameters: CytoParameters) => void;
  disabled?: boolean;
}

type StageId = 'reception' | 'processing' | 'reporting';

const STAGES: { id: StageId; title: string; detail: string }[] = [
  {
    id: 'reception',
    title: 'Reception',
    detail: 'Accept samples & accession patients',
  },
  {
    id: 'processing',
    title: 'Processing',
    detail: 'Fixation & batched staining',
  },
  {
    id: 'reporting',
    title: 'Reporting',
    detail: 'Microscopy & sign-out',
  },
];

function isSameSelection(a: CytoResourceSelection | null, b: CytoResourceSelection) {
  if (!a) return false;
  if (a.stage !== b.stage) return false;
  if (a.stage === 'simulation' || b.stage === 'simulation') return a.stage === b.stage;
  return a.target === b.target;
}

export function CytoInteractivePanel({ parameters, onChange, disabled }: CytoInteractivePanelProps) {
  const normalized = useMemo(() => normalizeCytoParameters(parameters), [parameters]);
  const [selection, setSelection] = useState<CytoResourceSelection | null>(null);

  const select = (next: CytoResourceSelection) => {
    setSelection((current) => (isSameSelection(current, next) ? null : next));
  };

  const patch = (next: CytoParameters) => onChange(normalizeCytoParameters(next));

  const personSelected = (stage: StageId) =>
    selection?.stage === stage && selection.target === 'person';

  const equipmentSelected = (stage: StageId) =>
    selection?.stage === stage && selection.target === 'equipment';

  return (
    <div className="cyto-interactive">
      <div className="cyto-interactive__main">
        <div className="cyto-interactive__header">
          <div>
            <h2 className="cyto-interactive__title">Cytopathology workflow</h2>
            <p className="cyto-interactive__subtitle">
              Click a <strong>professional</strong> to edit staffing &amp; service times, or{' '}
              <strong>equipment</strong> for stations, batch sizes &amp; error rates.
            </p>
          </div>
          <button
            type="button"
            className={`cyto-interactive__settings ${selection?.stage === 'simulation' ? 'cyto-interactive__settings--active' : ''}`}
            onClick={() => select({ stage: 'simulation' })}
            disabled={disabled}
          >
            Simulation settings
          </button>
        </div>

        <div className="cyto-interactive__track" role="group" aria-label="Cytopathology workflow stations">
          {STAGES.map((stage, index) => (
            <div key={stage.id} className="cyto-interactive__stage-wrap">
              <article className="cyto-interactive__stage">
                <header className="cyto-interactive__stage-header">
                  <span className="cyto-interactive__stage-index">{index + 1}</span>
                  <div>
                    <h3 className="cyto-interactive__stage-title">{stage.title}</h3>
                    <p className="cyto-interactive__stage-detail">{stage.detail}</p>
                  </div>
                </header>

                <div className="cyto-interactive__figures">
                  {stage.id === 'reception' && (
                    <>
                      <ReceptionProfessional
                        selected={personSelected('reception')}
                        onClick={() => select({ stage: 'reception', target: 'person' })}
                      />
                      <ReceptionEquipment
                        selected={equipmentSelected('reception')}
                        onClick={() => select({ stage: 'reception', target: 'equipment' })}
                      />
                    </>
                  )}
                  {stage.id === 'processing' && (
                    <>
                      <ProcessingProfessional
                        selected={personSelected('processing')}
                        onClick={() => select({ stage: 'processing', target: 'person' })}
                      />
                      <ProcessingEquipment
                        selected={equipmentSelected('processing')}
                        onClick={() => select({ stage: 'processing', target: 'equipment' })}
                      />
                    </>
                  )}
                  {stage.id === 'reporting' && (
                    <>
                      <ReportingProfessional
                        selected={personSelected('reporting')}
                        onClick={() => select({ stage: 'reporting', target: 'person' })}
                      />
                      <ReportingEquipment
                        selected={equipmentSelected('reporting')}
                        onClick={() => select({ stage: 'reporting', target: 'equipment' })}
                      />
                    </>
                  )}
                </div>
              </article>

              {index < STAGES.length - 1 && (
                <div className="cyto-interactive__flow" aria-hidden="true">
                  <span className="cyto-interactive__arrow">→</span>
                  <span className="cyto-interactive__flow-label">Samples</span>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {selection && (
        <CytoResourcePanel
          selection={selection}
          parameters={normalized}
          onChange={patch}
          onClose={() => setSelection(null)}
          disabled={disabled}
        />
      )}
    </div>
  );
}
