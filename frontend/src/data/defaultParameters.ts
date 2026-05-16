import type { CytoParameters, HistoParameters } from '../types/simulation';
import defaultCytoJson from '../../../shared/cyto_parameters.default.json';
import defaultHistoJson from '../../../shared/histo_parameters.default.json';

export const defaultCytoParameters = defaultCytoJson as unknown as CytoParameters;
export const defaultHistoParameters = defaultHistoJson as unknown as HistoParameters;

export const CYTO_PIPELINE_STAGES = [
  { id: 'arrival', label: 'Patient arrival', detail: 'Pap & non-Pap (Poisson)' },
  { id: 'accessioning', label: 'Accessioning', detail: 'Split into slides' },
  { id: 'fixation', label: 'Fixation', detail: 'Per slide' },
  { id: 'staining', label: 'Manual staining', detail: 'Batched' },
  { id: 'reporting', label: 'Reporting', detail: 'Cytopathologist' },
] as const;

export const HISTO_PIPELINE_STAGES = [
  { id: 'arrival', label: 'Biopsy arrival', detail: 'Cervical & other (Poisson)' },
  { id: 'fixation', label: 'Fixation', detail: 'By biopsy size' },
  { id: 'grossing', label: 'Grossing', detail: 'Resident + station' },
  { id: 'processing', label: 'Tissue processing', detail: 'Batched' },
  { id: 'embed', label: 'Embedding', detail: 'Per block' },
  { id: 'section', label: 'Sectioning', detail: 'Per block' },
  { id: 'staining', label: 'Staining', detail: 'Batched' },
  { id: 'reporting', label: 'Reporting', detail: 'Histopathologist' },
] as const;

export function defaultParametersForKind(kind: 'cyto' | 'histo'): CytoParameters | HistoParameters {
  return kind === 'cyto'
    ? structuredClone(defaultCytoParameters)
    : structuredClone(defaultHistoParameters);
}
