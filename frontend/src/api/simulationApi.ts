import type { SimulationRunRequest, SimulationRunResult } from '../types/simulation';

const API_BASE = import.meta.env.VITE_API_BASE ?? '';

function mockResult(request: SimulationRunRequest): SimulationRunResult {
  const papRate = request.parameters.pap_per_day.params[0] ?? 5;
  const nonPapRate = request.parameters.non_pap_per_day.params[0] ?? 20;
  const totalPatients = Math.round((papRate + nonPapRate) * 30 * 11);

  return {
    runId: `mock-${Date.now()}`,
    completedAt: new Date().toISOString(),
    summary:
      'Mock results — connect the FastAPI backend to run the real discrete-event simulation. Values below scale with your arrival-rate parameters.',
    metrics: [
      { label: 'Patients simulated', value: totalPatients.toLocaleString() },
      { label: 'Median turnaround', value: '4.2 days', detail: 'Reporting end − arrival' },
      { label: '90th percentile TAT', value: '9.8 days' },
      { label: 'Slides completed', value: Math.round(totalPatients * 1.4).toLocaleString() },
      {
        label: 'Cytotechnicians',
        value: String(request.parameters.cyto_technicians.num_cytotech),
      },
      {
        label: 'Cytopathologists',
        value: String(request.parameters.cyto_pathologists.num_cytopath),
      },
    ],
    turnaroundHistogram: [
      { range: '0–2d', count: Math.round(totalPatients * 0.12) },
      { range: '2–5d', count: Math.round(totalPatients * 0.38) },
      { range: '5–10d', count: Math.round(totalPatients * 0.32) },
      { range: '10–20d', count: Math.round(totalPatients * 0.14) },
      { range: '>20d', count: Math.round(totalPatients * 0.04) },
    ],
    patientBreakdown: [
      { type: 'Pap smear', count: Math.round(totalPatients * 0.2), medianTatDays: 3.1 },
      { type: 'Non-Pap', count: Math.round(totalPatients * 0.8), medianTatDays: 4.6 },
    ],
    notes: [
      'Warm-up month excluded from slide-level exports (matches backend behaviour).',
      'Reporting times use triangular distributions by case complexity.',
    ],
  };
}

export async function runSimulation(
  request: SimulationRunRequest,
): Promise<SimulationRunResult> {
  try {
    const response = await fetch(`${API_BASE}/api/simulations/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });

    if (response.ok) {
      return (await response.json()) as SimulationRunResult;
    }
  } catch {
    // Backend not available — fall through to mock
  }

  await new Promise((resolve) => setTimeout(resolve, 900));
  return mockResult(request);
}
