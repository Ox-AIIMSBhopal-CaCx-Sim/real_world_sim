import type { SimulationKind } from "../types/simulation";
import type { ResourceIconKind } from "./ResourceIcons";

export type PipelineStepId =
  | "simulation"
  | "accessioning"
  | "fixation"
  | "staining"
  | "screening"
  | "reporting"
  | "grossing"
  | "tissue_processing"
  | "embedding"
  | "sectioning";

export interface PipelineStep {
  id: PipelineStepId;
  name: string;
  description: string;
  resources: ResourceIconKind[];
}

export const CYTO_PIPELINE_STEPS: PipelineStep[] = [
  {
    id: "accessioning",
    name: "Arrival",
    description: "Samples arrive at the lab and slides are created",
    resources: ["intake"],
  },
  {
    id: "fixation",
    name: "Fixation",
    description: "Preserve specimens before staining",
    resources: ["timer"],
  },
  {
    id: "staining",
    name: "Staining",
    description: "Stain slides with staff and station",
    resources: ["technician", "equipment"],
  },
  {
    id: "screening",
    name: "Screening",
    description: "Junior pathologist reviews each slide",
    resources: ["junior_pathologist"],
  },
  {
    id: "reporting",
    name: "Reporting",
    description: "Senior pathologist issues the diagnosis",
    resources: ["senior_pathologist"],
  },
];

export const HISTO_PIPELINE_STEPS: PipelineStep[] = [
  {
    id: "accessioning",
    name: "Arrival",
    description: "Biopsies arrive and cases are registered",
    resources: ["intake"],
  },
  {
    id: "fixation",
    name: "Fixation",
    description: "Preserve tissue before grossing",
    resources: ["timer"],
  },
  {
    id: "grossing",
    name: "Grossing",
    description: "Junior pathologist samples tissue at station",
    resources: ["junior_pathologist", "equipment"],
  },
  {
    id: "tissue_processing",
    name: "Tissue processing",
    description: "Automated processor prepares blocks",
    resources: ["equipment"],
  },
  {
    id: "embedding",
    name: "Embedding",
    description: "Technician embeds tissue in paraffin",
    resources: ["technician", "equipment"],
  },
  {
    id: "sectioning",
    name: "Sectioning",
    description: "Cut thin sections from paraffin blocks",
    resources: ["technician", "equipment"],
  },
  {
    id: "staining",
    name: "Staining",
    description: "Stain sections with staff and station",
    resources: ["technician", "equipment"],
  },
  {
    id: "screening",
    name: "Screening",
    description: "Junior pathologist reviews each slide",
    resources: ["junior_pathologist"],
  },
  {
    id: "reporting",
    name: "Reporting",
    description: "Senior pathologist issues the diagnosis",
    resources: ["senior_pathologist"],
  },
];

export function getPipelineSteps(kind: SimulationKind): PipelineStep[] {
  return kind === "cyto" ? CYTO_PIPELINE_STEPS : HISTO_PIPELINE_STEPS;
}
