import type { DisruptionConfig, SimulationKind } from '../types/simulation';

export interface DisruptionPreset {
  key: string;
  title: string;
  description: string;
  defaults: DisruptionConfig;
}

export interface DisruptionResourceOption {
  value: string;
  label: string;
}

export function getDisruptionResources(kind: SimulationKind): DisruptionResourceOption[] {
  if (kind === 'cyto') {
    return [
      { value: 'cytotechnician', label: 'Cytotechnician' },
      { value: 'junior_pathologist', label: 'Junior pathologist' },
      { value: 'senior_pathologist', label: 'Senior pathologist' },
      { value: 'cyto_manual_staining_station', label: 'Manual staining station' },
    ];
  }

  return [
    { value: 'histotechnician', label: 'Histotechnician' },
    { value: 'junior_pathologist', label: 'Junior pathologist' },
    { value: 'senior_pathologist', label: 'Senior pathologist' },
    { value: 'histo_grossing_station', label: 'Grossing station' },
    { value: 'histo_tissue_processor', label: 'Tissue processor' },
    { value: 'histo_embedding_station', label: 'Embedding station' },
    { value: 'histo_sectioning_station', label: 'Sectioning station' },
    { value: 'histo_staining_station', label: 'Staining station' },
  ];
}

export function getDisruptionPresets(kind: SimulationKind): DisruptionPreset[] {
  const equipmentResource =
    kind === 'cyto' ? 'cyto_manual_staining_station' : 'histo_tissue_processor';

  return [
    {
      key: 'junior_doctor_strike',
      title: 'Junior doctor strike',
      description: 'Junior pathologists unavailable for several days.',
      defaults: {
        id: 'junior_doctor_strike',
        resource: 'junior_pathologist',
        start_day: 84,
        start_datetime: null,
        duration_days: 5,
        effective_capacity: 0,
      },
    },
    {
      key: 'equipment_breakdown',
      title: 'Equipment breakdown',
      description: 'Key lab equipment offline with zero capacity.',
      defaults: {
        id: 'equipment_breakdown',
        resource: equipmentResource,
        start_day: 30,
        start_datetime: null,
        duration_days: 14,
        effective_capacity: 0,
      },
    },
  ];
}

export function isDisruptionConfig(value: unknown): value is DisruptionConfig {
  if (!value || typeof value !== 'object') return false;
  const d = value as Record<string, unknown>;
  return typeof d.id === 'string' && typeof d.resource === 'string';
}

export function readDisruptions(value: unknown): DisruptionConfig[] {
  if (!Array.isArray(value)) return [];
  return value.filter(isDisruptionConfig).map((d) => ({
    id: d.id,
    resource: d.resource,
    duration_days: Number(d.duration_days ?? 1),
    effective_capacity: Number(d.effective_capacity ?? 0),
    start_day: d.start_day == null ? null : Number(d.start_day),
    start_datetime: d.start_datetime == null ? null : String(d.start_datetime),
  }));
}

/** Serialize for the backend: exactly one of start_day / start_datetime. */
export function toApiDisruption(d: DisruptionConfig): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    id: d.id,
    resource: d.resource,
    duration_days: d.duration_days,
    effective_capacity: d.effective_capacity,
  };
  if (d.start_datetime) {
    payload.start_datetime = d.start_datetime;
  } else {
    payload.start_day = d.start_day ?? 0;
  }
  return payload;
}
