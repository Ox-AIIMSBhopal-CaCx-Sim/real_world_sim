export type SimulationKind = 'cyto' | 'histo';

export type ParametersDict = Record<string, unknown>;

/** Matches backend Disruption schema / YAML entries. */
export interface DisruptionConfig {
  id: string;
  resource: string;
  duration_days: number;
  effective_capacity: number;
  start_day?: number | null;
  start_datetime?: string | null;
}

export interface ArtifactUrls {
  data: Record<string, string>;
  tables: Record<string, string>;
  plots: Record<string, string>;
}

export interface SimulationRunResult {
  run_id: string;
  lab: SimulationKind;
  status: 'completed' | 'failed';
  seed: number | null;
  project_title: string | null;
  artifacts: ArtifactUrls;
  local_run_dir?: string | null;
  error?: string | null;
}

export interface RunHistoryEntry {
  run_id: string;
  lab: SimulationKind;
  project_title: string;
  seed: number | null;
  completed_at: string;
  result: SimulationRunResult;
}

export interface SimulationRunRequest {
  kind: SimulationKind;
  parameters: ParametersDict;
  seed: number | null;
}
