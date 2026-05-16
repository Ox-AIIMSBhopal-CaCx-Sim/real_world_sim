import type { SimulationKind } from '../../types/simulation';

interface ModalityToggleProps {
  kind: SimulationKind;
  onChange: (kind: SimulationKind) => void;
  disabled?: boolean;
}

export function ModalityToggle({ kind, onChange, disabled }: ModalityToggleProps) {
  return (
    <div className="modality-toggle" role="group" aria-label="Simulation modality">
      <button
        type="button"
        className={`modality-toggle__btn${kind === 'cyto' ? ' modality-toggle__btn--active' : ''}`}
        aria-pressed={kind === 'cyto'}
        disabled={disabled}
        onClick={() => onChange('cyto')}
      >
        Cytopathology
      </button>
      <button
        type="button"
        className={`modality-toggle__btn${kind === 'histo' ? ' modality-toggle__btn--active' : ''}`}
        aria-pressed={kind === 'histo'}
        disabled={disabled}
        onClick={() => onChange('histo')}
      >
        Histopathology
      </button>
    </div>
  );
}
