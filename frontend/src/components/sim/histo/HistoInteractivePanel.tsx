import { useMemo, useState } from 'react';
import type { HistoParameters } from '../../../types/simulation';
import { normalizeHistoParameters } from '../../../data/defaultParameters';
import {
  HistoProcessingEquipment,
  HistoProcessingProfessional,
  HistoReceptionEquipment,
  HistoReceptionProfessional,
  HistoReportingEquipment,
  HistoReportingProfessional,
} from './HistoCartoons';
import { HistoResourcePanel, type HistoResourceSelection } from './HistoResourcePanel';

interface HistoInteractivePanelProps {
  parameters: HistoParameters;
  onChange: (parameters: HistoParameters) => void;
  disabled?: boolean;
}

type StageId = 'reception' | 'processing' | 'reporting';

const STAGES: { id: StageId; title: string; detail: string }[] = [
  {
    id: 'reception',
    title: 'Reception',
    detail: 'Accept biopsies & accession specimens',
  },
  {
    id: 'processing',
    title: 'Processing',
    detail: 'Fixation, grossing, embedding & staining',
  },
  {
    id: 'reporting',
    title: 'Reporting',
    detail: 'Microscopy & sign-out',
  },
];

function isSameSelection(a: HistoResourceSelection | null, b: HistoResourceSelection) {
  if (!a) return false;
  if (a.stage !== b.stage) return false;
  if (a.stage === 'simulation' || b.stage === 'simulation') return a.stage === b.stage;
  return a.target === b.target;
}

export function HistoInteractivePanel({ parameters, onChange, disabled }: HistoInteractivePanelProps) {
  const normalized = useMemo(() => normalizeHistoParameters(parameters), [parameters]);
  const [selection, setSelection] = useState<HistoResourceSelection | null>(null);

  const select = (next: HistoResourceSelection) => {
    setSelection((current) => (isSameSelection(current, next) ? null : next));
  };

  const patch = (next: HistoParameters) => onChange(normalizeHistoParameters(next));

  const personSelected = (stage: StageId) =>
    selection?.stage === stage && selection.target === 'person';

  const equipmentSelected = (stage: StageId) =>
    selection?.stage === stage && selection.target === 'equipment';

  return (
    <div className="cyto-interactive">
      <div className="cyto-interactive__main">
        <div className="cyto-interactive__header">
          <div>
            <h2 className="cyto-interactive__title">Histopathology workflow</h2>
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

        <div className="cyto-interactive__track" role="group" aria-label="Histopathology workflow stations">
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
                      <HistoReceptionProfessional
                        selected={personSelected('reception')}
                        onClick={() => select({ stage: 'reception', target: 'person' })}
                      />
                      <HistoReceptionEquipment
                        selected={equipmentSelected('reception')}
                        onClick={() => select({ stage: 'reception', target: 'equipment' })}
                      />
                    </>
                  )}
                  {stage.id === 'processing' && (
                    <>
                      <HistoProcessingProfessional
                        selected={personSelected('processing')}
                        onClick={() => select({ stage: 'processing', target: 'person' })}
                      />
                      <HistoProcessingEquipment
                        selected={equipmentSelected('processing')}
                        onClick={() => select({ stage: 'processing', target: 'equipment' })}
                      />
                    </>
                  )}
                  {stage.id === 'reporting' && (
                    <>
                      <HistoReportingProfessional
                        selected={personSelected('reporting')}
                        onClick={() => select({ stage: 'reporting', target: 'person' })}
                      />
                      <HistoReportingEquipment
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
                  <span className="cyto-interactive__flow-label">Biopsies</span>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {selection && (
        <HistoResourcePanel
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
