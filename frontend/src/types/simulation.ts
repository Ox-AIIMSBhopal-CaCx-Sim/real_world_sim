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
}

export interface CaseComplexity {
  p_high: number;
}

export interface SlideRatioByComplexity {
  high: number;
  low: number;
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
  cyto_manual_staining_station: {
    num_stations: number;
    batch_size: number;
  };
  cyto_staining_kits: {
    num_kits: number;
    stain_per_kit: number;
    reagent_per_slide: number;
  };
}

export interface SimulationRunRequest {
  kind: SimulationKind;
  parameters: CytoParameters;
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

export interface SimulationRunResult {
  runId: string;
  completedAt: string;
  summary: string;
  metrics: SummaryMetric[];
  turnaroundHistogram: TurnaroundBucket[];
  patientBreakdown: PatientTypeBreakdown[];
  notes: string[];
}

export interface SimulationState {
  kind: SimulationKind;
  parameters: CytoParameters;
  results: SimulationRunResult | null;
  isRunning: boolean;
  error: string | null;
}
