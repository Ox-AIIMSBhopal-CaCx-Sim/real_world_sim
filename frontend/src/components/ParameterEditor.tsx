import { useEffect, useState } from "react";
import type { ParametersDict, SimulationKind } from "../types/simulation";
import { DisruptionsPanel } from "./DisruptionsPanel";
import { PipelineSteps } from "./PipelineSteps";
import { getPipelineSteps, type PipelineStepId } from "./pipelineConfig";

interface ParameterEditorProps {
  kind: SimulationKind;
  parameters: ParametersDict | null;
  loading: boolean;
  onChange: (path: string[], value: unknown) => void;
  onRun: () => void;
  isRunning: boolean;
  resetKey?: number;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object"
    ? (value as Record<string, unknown>)
    : {};
}

function NumberField({
  label,
  value,
  onChange,
  step = 1,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        type="number"
        step={step}
        value={Number.isFinite(value) ? value : 0}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </label>
  );
}

function constantParam(value: unknown): number {
  if (typeof value === "number") return value;
  const record = asRecord(value);
  const params = record.params;
  if (typeof params === "number") return params;
  if (Array.isArray(params) && typeof params[0] === "number") return params[0];
  return 0;
}

function triangularParams(
  value: unknown,
  complexity: "high" | "low",
  fallback: [number, number, number],
): [number, number, number] {
  const byComplexity = asRecord(asRecord(value).by_case_complexity);
  const entry = asRecord(byComplexity[complexity]);
  const params = entry.params;
  if (Array.isArray(params) && params.length >= 3) {
    return [
      Number(params[0] ?? fallback[0]),
      Number(params[1] ?? fallback[1]),
      Number(params[2] ?? fallback[2]),
    ];
  }
  return fallback;
}

function ComplexityTimeFields({
  label,
  value,
  onChange,
  highFallback,
  lowFallback,
}: {
  label: string;
  value: unknown;
  onChange: (next: unknown) => void;
  highFallback: [number, number, number];
  lowFallback: [number, number, number];
}) {
  const high = triangularParams(value, "high", highFallback);
  const low = triangularParams(value, "low", lowFallback);

  const setTriangular = (
    complexity: "high" | "low",
    index: 0 | 1 | 2,
    nextValue: number,
  ) => {
    const current = complexity === "high" ? [...high] : [...low];
    current[index] = nextValue;
    const other = complexity === "high" ? low : high;
    onChange({
      by_case_complexity: {
        high: {
          distribution: "triangular",
          params: complexity === "high" ? current : other,
        },
        low: {
          distribution: "triangular",
          params: complexity === "low" ? current : other,
        },
      },
    });
  };

  return (
    <section>
      <h3>{label}</h3>
      <p className="muted complexity-time__hint">
        Triangular times in minutes (min / mode / max)
      </p>
      <div className="complexity-time">
        <div>
          <h4>High complexity</h4>
          <NumberField
            label="Min"
            value={high[0]}
            onChange={(v) => setTriangular("high", 0, v)}
          />
          <NumberField
            label="Mode"
            value={high[1]}
            onChange={(v) => setTriangular("high", 1, v)}
          />
          <NumberField
            label="Max"
            value={high[2]}
            onChange={(v) => setTriangular("high", 2, v)}
          />
        </div>
        <div>
          <h4>Low complexity</h4>
          <NumberField
            label="Min"
            value={low[0]}
            onChange={(v) => setTriangular("low", 0, v)}
          />
          <NumberField
            label="Mode"
            value={low[1]}
            onChange={(v) => setTriangular("low", 1, v)}
          />
          <NumberField
            label="Max"
            value={low[2]}
            onChange={(v) => setTriangular("low", 2, v)}
          />
        </div>
      </div>
    </section>
  );
}

function sizeConstantParam(
  value: unknown,
  size: "small" | "medium" | "large",
  fallback: number,
): number {
  const bySize = asRecord(asRecord(value).by_size);
  return constantParam(bySize[size] ?? fallback);
}

function SizeTimeFields({
  label,
  value,
  onChange,
  fallbacks,
}: {
  label: string;
  value: unknown;
  onChange: (next: unknown) => void;
  fallbacks: { small: number; medium: number; large: number };
}) {
  const sizes = ["small", "medium", "large"] as const;

  const setSize = (size: (typeof sizes)[number], nextValue: number) => {
    const nextBySize: Record<string, unknown> = {};
    for (const s of sizes) {
      nextBySize[s] = {
        distribution: "constant",
        params: s === size ? nextValue : sizeConstantParam(value, s, fallbacks[s]),
      };
    }
    onChange({ by_size: nextBySize });
  };

  return (
    <section>
      <h3>{label}</h3>
      <p className="muted complexity-time__hint">
        Times in minutes by biopsy size
      </p>
      <div className="complexity-time complexity-time--three">
        {sizes.map((size) => (
          <div key={size}>
            <h4>{size}</h4>
            <NumberField
              label="Time (min)"
              value={sizeConstantParam(value, size, fallbacks[size])}
              onChange={(v) => setSize(size, v)}
            />
          </div>
        ))}
      </div>
    </section>
  );
}

export function ParameterEditor({
  kind,
  parameters,
  loading,
  onChange,
  onRun,
  isRunning,
  resetKey = 0,
}: ParameterEditorProps) {
  const [selectedStepId, setSelectedStepId] = useState<PipelineStepId | null>(
    null,
  );

  useEffect(() => {
    setSelectedStepId(null);
  }, [kind, resetKey]);

  if (loading || !parameters) {
    return (
      <div className="param-panel">
        <p className="muted">Loading default parameters…</p>
      </div>
    );
  }

  const selectedStep =
    getPipelineSteps(kind).find((step) => step.id === selectedStepId) ?? null;

  return (
    <div className="param-panel param-panel--trio">
      <aside className="side-card simulation-panel">
        <div className="side-card__header">
          <h3>Simulation parameters</h3>
          <p className="muted">
            Global run settings applied to every scenario.
          </p>
        </div>
        <SimulationFields parameters={parameters} onChange={onChange} />
      </aside>

      <div className="param-panel__center">
        <PipelineSteps
          kind={kind}
          selectedStepId={selectedStepId}
          onSelectStep={(id) =>
            setSelectedStepId((current) => (current === id ? null : id))
          }
        />

        {selectedStep ? (
          <div
            className="step-editor"
            role="region"
            aria-label={`${selectedStep.name} parameters`}
          >
            <div className="step-editor__header">
              <div>
                <p className="step-editor__eyebrow">Editing step</p>
                <h3>{selectedStep.name}</h3>
                <p className="muted">{selectedStep.description}</p>
              </div>
              <button
                type="button"
                className="step-editor__close"
                onClick={() => setSelectedStepId(null)}
              >
                Close
              </button>
            </div>

            <div className="param-grid">
              {kind === "cyto" ? (
                <CytoStepFields
                  stepId={selectedStep.id}
                  parameters={parameters}
                  onChange={onChange}
                />
              ) : (
                <HistoStepFields
                  stepId={selectedStep.id}
                  parameters={parameters}
                  onChange={onChange}
                />
              )}
            </div>
          </div>
        ) : (
          <p className="pipeline__hint muted">
            Select a pipeline step above to edit its parameters.
          </p>
        )}

        <div className="pipeline__actions">
          <button
            type="button"
            className="run-button"
            onClick={onRun}
            disabled={isRunning}
          >
            {isRunning ? "Running…" : "Run simulation"}
          </button>
        </div>
      </div>

      <DisruptionsPanel
        kind={kind}
        parameters={parameters}
        onChange={onChange}
      />
    </div>
  );
}

function SimulationFields({
  parameters,
  onChange,
}: {
  parameters: ParametersDict;
  onChange: (path: string[], value: unknown) => void;
}) {
  const sim = asRecord(parameters.simulation);
  const caseComplexity = asRecord(parameters.case_complexity);

  return (
    <div className="side-card__fields">
      <NumberField
        label="Duration (months)"
        value={Number(sim.duration_months ?? 12)}
        onChange={(v) => onChange(["simulation", "duration_months"], v)}
      />
      <NumberField
        label="Warm-up (months)"
        value={Number(sim.warmup_months ?? 1)}
        onChange={(v) => onChange(["simulation", "warmup_months"], v)}
      />
      <NumberField
        label="Proportion of complex cases"
        value={Number(caseComplexity.p_high ?? 0.2)}
        step={0.01}
        onChange={(v) => onChange(["case_complexity", "p_high"], v)}
      />
    </div>
  );
}

function HistoStepFields({
  stepId,
  parameters,
  onChange,
}: {
  stepId: PipelineStepId;
  parameters: ParametersDict;
  onChange: (path: string[], value: unknown) => void;
}) {
  const cervical = asRecord(parameters.cervical_biopsies_per_day);
  const other = asRecord(parameters.other_biopsies_per_day);
  const techs = asRecord(parameters.histo_technicians);
  const junior = asRecord(parameters.junior_pathologist);
  const senior = asRecord(parameters.senior_pathologists);
  const grossing = asRecord(parameters.histo_grossing_station);
  const tissue = asRecord(parameters.histo_tissue_processor);
  const embedding = asRecord(parameters.histo_embedding_station);
  const sectioning = asRecord(parameters.histo_sectioning_station);
  const staining = asRecord(parameters.histo_staining_station);
  const slideBySize = asRecord(parameters.slide_pt_ratio_by_biopsy_size);
  const cervicalParams = Array.isArray(cervical.params) ? cervical.params : [0];
  const otherParams = Array.isArray(other.params) ? other.params : [0];

  switch (stepId) {
    case "accessioning":
      return (
        <section>
          <h3>Workload</h3>
          <NumberField
            label="Cervical biopsies / day (λ)"
            value={Number(cervicalParams[0] ?? 0)}
            onChange={(v) => onChange(["cervical_biopsies_per_day", "params"], [v])}
          />
          <NumberField
            label="Other biopsies / day (λ)"
            value={Number(otherParams[0] ?? 0)}
            onChange={(v) => onChange(["other_biopsies_per_day", "params"], [v])}
          />
          <NumberField
            label="Slides / patient (small)"
            value={Number(slideBySize.small ?? 1)}
            onChange={(v) => onChange(["slide_pt_ratio_by_biopsy_size", "small"], v)}
          />
          <NumberField
            label="Slides / patient (medium)"
            value={Number(slideBySize.medium ?? 10)}
            onChange={(v) => onChange(["slide_pt_ratio_by_biopsy_size", "medium"], v)}
          />
          <NumberField
            label="Slides / patient (large)"
            value={Number(slideBySize.large ?? 20)}
            onChange={(v) => onChange(["slide_pt_ratio_by_biopsy_size", "large"], v)}
          />
        </section>
      );

    case "fixation":
      return (
        <SizeTimeFields
          label="Process time"
          value={parameters.histo_fixation_time}
          fallbacks={{ small: 360, medium: 720, large: 2880 }}
          onChange={(next) => onChange(["histo_fixation_time"], next)}
        />
      );

    case "grossing":
      return (
        <>
          <section>
            <h3>Resources</h3>
            <NumberField
              label="Junior pathologists"
              value={Number(junior.num_junior_pathologist ?? 1)}
              onChange={(v) =>
                onChange(["junior_pathologist", "num_junior_pathologist"], v)
              }
            />
            <NumberField
              label="Grossing stations"
              value={Number(grossing.num_stations ?? 1)}
              onChange={(v) => onChange(["histo_grossing_station", "num_stations"], v)}
            />
          </section>
          <SizeTimeFields
            label="Process time"
            value={parameters.histo_grossing_time}
            fallbacks={{ small: 10, medium: 30, large: 120 }}
            onChange={(next) => onChange(["histo_grossing_time"], next)}
          />
        </>
      );

    case "tissue_processing":
      return (
        <>
          <section>
            <h3>Resources</h3>
            <NumberField
              label="Tissue processors"
              value={Number(tissue.num_stations ?? 1)}
              onChange={(v) => onChange(["histo_tissue_processor", "num_stations"], v)}
            />
            <NumberField
              label="Processor batch size"
              value={Number(tissue.batch_size ?? 90)}
              onChange={(v) => onChange(["histo_tissue_processor", "batch_size"], v)}
            />
          </section>
          <section>
            <h3>Process time</h3>
            <NumberField
              label="Tissue processing time (min)"
              value={constantParam(parameters.histo_tissue_processing_time)}
              onChange={(v) =>
                onChange(["histo_tissue_processing_time"], {
                  distribution: "constant",
                  params: v,
                })
              }
            />
          </section>
        </>
      );

    case "embedding":
      return (
        <>
          <section>
            <h3>Resources</h3>
            <NumberField
              label="Histotechnicians"
              value={Number(techs.num_cytotech ?? 1)}
              onChange={(v) => onChange(["histo_technicians", "num_cytotech"], v)}
            />
            <NumberField
              label="Embedding stations"
              value={Number(embedding.num_stations ?? 1)}
              onChange={(v) => onChange(["histo_embedding_station", "num_stations"], v)}
            />
          </section>
          <section>
            <h3>Process time</h3>
            <NumberField
              label="Embedding time (min)"
              value={constantParam(parameters.histo_embedding_time)}
              onChange={(v) =>
                onChange(["histo_embedding_time"], {
                  distribution: "constant",
                  params: v,
                })
              }
            />
          </section>
        </>
      );

    case "sectioning":
      return (
        <>
          <section>
            <h3>Resources</h3>
            <NumberField
              label="Histotechnicians"
              value={Number(techs.num_cytotech ?? 1)}
              onChange={(v) => onChange(["histo_technicians", "num_cytotech"], v)}
            />
            <NumberField
              label="Sectioning stations"
              value={Number(sectioning.num_stations ?? 1)}
              onChange={(v) => onChange(["histo_sectioning_station", "num_stations"], v)}
            />
          </section>
          <section>
            <h3>Process time</h3>
            <NumberField
              label="Sectioning time (min)"
              value={constantParam(parameters.histo_sectioning_time)}
              onChange={(v) =>
                onChange(["histo_sectioning_time"], {
                  distribution: "constant",
                  params: v,
                })
              }
            />
          </section>
        </>
      );

    case "staining":
      return (
        <>
          <section>
            <h3>Resources</h3>
            <NumberField
              label="Histotechnicians"
              value={Number(techs.num_cytotech ?? 1)}
              onChange={(v) => onChange(["histo_technicians", "num_cytotech"], v)}
            />
            <NumberField
              label="Staining stations"
              value={Number(staining.num_stations ?? 1)}
              onChange={(v) => onChange(["histo_staining_station", "num_stations"], v)}
            />
            <NumberField
              label="Stain batch size"
              value={Number(staining.batch_size ?? 25)}
              onChange={(v) => onChange(["histo_staining_station", "batch_size"], v)}
            />
          </section>
          <section>
            <h3>Process time</h3>
            <NumberField
              label="Staining time (min)"
              value={constantParam(parameters.histo_staining_time)}
              onChange={(v) =>
                onChange(["histo_staining_time"], {
                  distribution: "constant",
                  params: v,
                })
              }
            />
          </section>
        </>
      );

    case "screening":
      return (
        <>
          <section>
            <h3>Resources</h3>
            <NumberField
              label="Junior pathologists"
              value={Number(junior.num_junior_pathologist ?? 1)}
              onChange={(v) =>
                onChange(["junior_pathologist", "num_junior_pathologist"], v)
              }
            />
          </section>
          <ComplexityTimeFields
            label="Process time"
            value={parameters.histo_slide_screening_time}
            highFallback={[20, 30, 40]}
            lowFallback={[10, 20, 30]}
            onChange={(next) => onChange(["histo_slide_screening_time"], next)}
          />
        </>
      );

    case "reporting":
      return (
        <>
          <section>
            <h3>Resources</h3>
            <NumberField
              label="Senior pathologists"
              value={Number(senior.num_senior_pathologist ?? 1)}
              onChange={(v) =>
                onChange(["senior_pathologists", "num_senior_pathologist"], v)
              }
            />
            <NumberField
              label="Repeat stain rate"
              value={Number(senior.repeat_stain_rate ?? 0.05)}
              step={0.01}
              onChange={(v) =>
                onChange(["senior_pathologists", "repeat_stain_rate"], v)
              }
            />
          </section>
          <ComplexityTimeFields
            label="Process time"
            value={parameters.histo_reporting_time}
            highFallback={[20, 30, 100]}
            lowFallback={[5, 10, 20]}
            onChange={(next) => onChange(["histo_reporting_time"], next)}
          />
        </>
      );

    default:
      return (
        <section>
          <p className="muted">No editable parameters for this step yet.</p>
        </section>
      );
  }
}

function CytoStepFields({
  stepId,
  parameters,
  onChange,
}: {
  stepId: PipelineStepId;
  parameters: ParametersDict;
  onChange: (path: string[], value: unknown) => void;
}) {
  const pap = asRecord(parameters.pap_per_day);
  const nonPap = asRecord(parameters.non_pap_per_day);
  const techs = asRecord(parameters.cyto_technicians);
  const junior = asRecord(parameters.junior_pathologist);
  const senior = asRecord(parameters.senior_pathologists);
  const stain = asRecord(parameters.cyto_manual_staining_station);
  const papParams = Array.isArray(pap.params) ? pap.params : [0];
  const nonPapParams = Array.isArray(nonPap.params) ? nonPap.params : [0];

  switch (stepId) {
    case "accessioning":
      {
        const slideByCc = asRecord(parameters.slide_pt_ratio_by_case_complexity);
        return (
          <section>
            <h3>Workload</h3>
            <NumberField
              label="Pap per day (λ)"
              value={Number(papParams[0] ?? 0)}
              onChange={(v) => onChange(["pap_per_day", "params"], [v])}
            />
            <NumberField
              label="Non-Pap per day (λ)"
              value={Number(nonPapParams[0] ?? 0)}
              onChange={(v) => onChange(["non_pap_per_day", "params"], [v])}
            />
            <NumberField
              label="Pap slides / patient"
              value={Number(pap.slide_pt_ratio ?? 1)}
              onChange={(v) => onChange(["pap_per_day", "slide_pt_ratio"], v)}
            />
            <NumberField
              label="Non-Pap slides / patient (high)"
              value={Number(slideByCc.high ?? 4)}
              onChange={(v) =>
                onChange(["slide_pt_ratio_by_case_complexity", "high"], v)
              }
            />
            <NumberField
              label="Non-Pap slides / patient (low)"
              value={Number(slideByCc.low ?? 1)}
              onChange={(v) =>
                onChange(["slide_pt_ratio_by_case_complexity", "low"], v)
              }
            />
          </section>
        );
      }

    case "fixation":
      return (
        <section>
          <h3>Process time</h3>
          <NumberField
            label="Fixation time (min)"
            value={constantParam(parameters.cyto_fixation_time)}
            onChange={(v) =>
              onChange(["cyto_fixation_time"], {
                distribution: "constant",
                params: v,
              })
            }
          />
        </section>
      );

    case "staining":
      return (
        <>
          <section>
            <h3>Resources</h3>
            <NumberField
              label="Cytotechnicians"
              value={Number(techs.num_cytotech ?? 1)}
              onChange={(v) =>
                onChange(["cyto_technicians", "num_cytotech"], v)
              }
            />
            <NumberField
              label="Staining stations"
              value={Number(stain.num_stations ?? 1)}
              onChange={(v) =>
                onChange(["cyto_manual_staining_station", "num_stations"], v)
              }
            />
            <NumberField
              label="Stain batch size"
              value={Number(stain.batch_size ?? 5)}
              onChange={(v) =>
                onChange(["cyto_manual_staining_station", "batch_size"], v)
              }
            />
          </section>
          <section>
            <h3>Process time</h3>
            <NumberField
              label="Staining time (min)"
              value={constantParam(parameters.cyto_staining_time)}
              onChange={(v) =>
                onChange(["cyto_staining_time"], {
                  distribution: "constant",
                  params: v,
                })
              }
            />
            <NumberField
              label="Stain error rate"
              value={Number(stain.error_rate ?? 0.01)}
              step={0.01}
              onChange={(v) =>
                onChange(["cyto_manual_staining_station", "error_rate"], v)
              }
            />
          </section>
        </>
      );

    case "screening":
      return (
        <>
          <section>
            <h3>Resources</h3>
            <NumberField
              label="Junior pathologists"
              value={Number(junior.num_junior_pathologist ?? 1)}
              onChange={(v) =>
                onChange(["junior_pathologist", "num_junior_pathologist"], v)
              }
            />
          </section>
          <ComplexityTimeFields
            label="Process time"
            value={parameters.cyto_slide_screening_time}
            highFallback={[15, 20, 40]}
            lowFallback={[5, 10, 20]}
            onChange={(next) => onChange(["cyto_slide_screening_time"], next)}
          />
        </>
      );

    case "reporting":
      return (
        <>
          <section>
            <h3>Resources</h3>
            <NumberField
              label="Senior pathologists"
              value={Number(senior.num_senior_pathologist ?? 1)}
              onChange={(v) =>
                onChange(["senior_pathologists", "num_senior_pathologist"], v)
              }
            />
            <NumberField
              label="Repeat stain rate"
              value={Number(senior.repeat_stain_rate ?? 0.05)}
              step={0.01}
              onChange={(v) =>
                onChange(["senior_pathologists", "repeat_stain_rate"], v)
              }
            />
          </section>
          <ComplexityTimeFields
            label="Process time"
            value={parameters.cyto_reporting_time}
            highFallback={[5, 15, 30]}
            lowFallback={[1, 3, 5]}
            onChange={(next) => onChange(["cyto_reporting_time"], next)}
          />
        </>
      );

    default:
      return (
        <section>
          <p className="muted">No editable parameters for this step yet.</p>
        </section>
      );
  }
}

