export type SimulationKind = 'cyto' | 'histo';

export interface DistributionParams {
  distribution: string;
  params: number[];
}

export interface TriangularParams {
  distribution: 'triangular';
  params: [number, number, number];
}

export interface SimulationMeta {
  name: string;
  run_time: number;
  experiment_no: number;
  no_of_sims: number;
  warmup_days?: number;
  working_days?: number[];
  working_hours?: number[];
}

export interface CaseComplexity {
  p_high: number;
}

export interface SlideRatioByComplexity {
  high: number;
  low: number;
}

export interface SlideRatioByBiopsySize {
  small: number;
  medium: number;
  large: number;
}

export interface CytoParameters {
  project_title: string;
  simulation: SimulationMeta;
  pap_per_day: DistributionParams & { slide_pt_ratio: number };
  non_pap_per_day: DistributionParams;
  case_complexity: CaseComplexity;
  slide_pt_ratio_by_case_complexity: SlideRatioByComplexity;
  cyto_fixation_time: DistributionParams;
  cyto_staining_time: DistributionParams;
  cyto_reporting_time: {
    by_case_complexity: {
      high: TriangularParams;
      low: TriangularParams;
    };
  };
  cyto_technicians: {
    num_cytotech: number;
    cytotech_schedule: Record<string, { days: number[]; hours: [number, number] }>;
  };
  cyto_pathologists: {
    num_cytopath: number;
    cytopath_schedule: Record<string, { days: number[]; hours: [number, number] }>;
  };
  cyto_reception: {
    num_staff: number;
    accessioning_time: DistributionParams;
  };
  cyto_manual_staining_station: {
    num_stations: number;
    batch_size: number;
    error_rate: number;
  };
  cyto_reporting_station: {
    num_stations: number;
    batch_size: number;
    error_rate: number;
  };
  cyto_staining_kits: {
    num_kits: number;
    stain_per_kit: number;
    reagent_per_slide: number;
  };
}

export interface HistoTimeBySize {
  by_size: {
    small: DistributionParams;
    medium: DistributionParams;
    large: DistributionParams;
  };
}

export interface HistoStationConfig {
  num_stations: number;
  batch_size: number;
  error_rate: number;
}

export interface HistoParameters {
  project_title: string;
  simulation: SimulationMeta;
  cervical_biopsies_per_day: DistributionParams;
  other_biopsies_per_day: DistributionParams;
  case_complexity: CaseComplexity;
  slide_pt_ratio_by_biopsy_size: SlideRatioByBiopsySize;
  biopsy_size: { weights: Record<string, number> };
  histo_reception: {
    num_staff: number;
    accessioning_time: DistributionParams;
  };
  histo_fixation_time: HistoTimeBySize;
  histo_grossing_time: HistoTimeBySize;
  histo_tissue_processing_time: DistributionParams;
  histo_embedding_time: DistributionParams;
  histo_sectioning_time: DistributionParams;
  histo_staining_time: DistributionParams;
  histo_reporting_time: {
    by_case_complexity: {
      high: TriangularParams;
      low: TriangularParams;
    };
  };
  histo_technicians: {
    num_cytotech: number;
    histotech_schedule: Record<string, { days: number[]; hours: [number, number] }>;
  };
  path_resident: {
    num: number;
    resident_schedule: Record<string, { days: number[]; hours: [number, number] }>;
  };
  histo_pathologists: {
    num_cytopath: number;
    histopath_schedule: Record<string, { days: number[]; hours: [number, number] }>;
  };
  histo_grossing_station: HistoStationConfig;
  histo_tissue_processor: HistoStationConfig;
  histo_embedding_station: HistoStationConfig;
  histo_sectioning_station: HistoStationConfig;
  histo_staining_station: HistoStationConfig;
  histo_reporting_station: HistoStationConfig;
  histo_staining_kits: {
    num_kits: number;
    stain_per_kit: number;
    reagent_per_slide: number;
  };
}

export type SimulationParameters = CytoParameters | HistoParameters;

export interface SimulationRunRequest {
  kind: SimulationKind;
  parameters: SimulationParameters;
  seed?: number;
}

export interface SummaryMetric {
  label: string;
  value: string;
  detail?: string;
}

export interface TurnaroundBucket {
  range: string;
  count: number;
}

export interface PatientTypeBreakdown {
  type: string;
  count: number;
  medianTatDays: number;
}

export interface ProcessMetric {
  process: string;
  median_wait_min: number;
  p90_wait_min: number;
  n: number;
}

export interface RunArtifacts {
  patientCsv: string;
  slideCsv: string;
}

export interface SimulationRunResult {
  runId: string;
  completedAt: string;
  summary: string;
  metrics: SummaryMetric[];
  turnaroundHistogram: TurnaroundBucket[];
  patientBreakdown: PatientTypeBreakdown[];
  processMetrics?: ProcessMetric[];
  artifacts?: RunArtifacts;
  notes: string[];
}

/** A saved simulation workspace tab (parameters + optional results). */
export interface SimulationSession {
  id: string;
  label: string;
  labelIsCustom?: boolean;
  kind: SimulationKind;
  parameters: SimulationParameters;
  /** Preserves parameters and results when toggling modality on the same tab. */
  paramCache?: Partial<
    Record<SimulationKind, { parameters: SimulationParameters; results: SimulationRunResult | null }>
  >;
  results: SimulationRunResult | null;
  createdAt: string;
  updatedAt: string;
}

export interface SimulationWorkspace {
  sessions: SimulationSession[];
  activeSessionId: string;
  isRunning: boolean;
  error: string | null;
}
