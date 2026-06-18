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
  const params =
    kind === 'cyto'
      ? structuredClone(defaultCytoParameters)
      : structuredClone(defaultHistoParameters);
  return kind === 'cyto'
    ? normalizeCytoParameters(params as CytoParameters)
    : normalizeHistoParameters(params as HistoParameters);
}

function normalizeHistoStation(
  station: Partial<HistoParameters['histo_grossing_station']> | undefined,
  defaults: HistoParameters['histo_grossing_station'],
): HistoParameters['histo_grossing_station'] {
  return {
    ...defaults,
    ...station,
    error_rate: station?.error_rate ?? defaults.error_rate,
  };
}

/** Fill in frontend-only histo fields when loading older saved sessions. */
export function normalizeHistoParameters(parameters: HistoParameters): HistoParameters {
  const defaults = defaultHistoParameters;
  return {
    ...parameters,
    histo_reception: parameters.histo_reception ?? structuredClone(defaults.histo_reception),
    histo_grossing_station: normalizeHistoStation(
      parameters.histo_grossing_station,
      defaults.histo_grossing_station,
    ),
    histo_tissue_processor: normalizeHistoStation(
      parameters.histo_tissue_processor,
      defaults.histo_tissue_processor,
    ),
    histo_embedding_station: normalizeHistoStation(
      parameters.histo_embedding_station,
      defaults.histo_embedding_station,
    ),
    histo_sectioning_station: normalizeHistoStation(
      parameters.histo_sectioning_station,
      defaults.histo_sectioning_station,
    ),
    histo_staining_station: normalizeHistoStation(
      parameters.histo_staining_station,
      defaults.histo_staining_station,
    ),
    histo_reporting_station:
      parameters.histo_reporting_station ?? structuredClone(defaults.histo_reporting_station),
  };
}

/** Fill in frontend-only cyto fields when loading older saved sessions. */
export function normalizeCytoParameters(parameters: CytoParameters): CytoParameters {
  const defaults = defaultCytoParameters;
  return {
    ...parameters,
    cyto_reception: parameters.cyto_reception ?? structuredClone(defaults.cyto_reception),
    cyto_manual_staining_station: {
      ...defaults.cyto_manual_staining_station,
      ...parameters.cyto_manual_staining_station,
      error_rate:
        parameters.cyto_manual_staining_station?.error_rate ??
        defaults.cyto_manual_staining_station.error_rate,
    },
    cyto_reporting_station:
      parameters.cyto_reporting_station ?? structuredClone(defaults.cyto_reporting_station),
  };
}
