import type { CytoParameters } from '../types/simulation';
import defaultCytoJson from '../../../shared/cyto_parameters.default.json';

/** Canonical defaults — same file as backend/shared/cyto_parameters.default.json */
export const defaultCytoParameters = defaultCytoJson as unknown as CytoParameters;

export const CYTO_PIPELINE_STAGES = [
  { id: 'arrival', label: 'Patient arrival', detail: 'Pap & non-Pap (Poisson)' },
  { id: 'accessioning', label: 'Accessioning', detail: 'Split into slides' },
  { id: 'fixation', label: 'Fixation', detail: 'Per slide' },
  { id: 'staining', label: 'Manual staining', detail: 'Batched' },
  { id: 'reporting', label: 'Reporting', detail: 'Cytopathologist' },
] as const;
