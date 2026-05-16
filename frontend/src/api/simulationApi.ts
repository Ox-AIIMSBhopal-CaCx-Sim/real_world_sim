import type { SimulationRunRequest, SimulationRunResult } from '../types/simulation';

const API_BASE = import.meta.env.VITE_API_BASE ?? '';

export async function runSimulation(
  request: SimulationRunRequest,
): Promise<SimulationRunResult> {
  const response = await fetch(`${API_BASE}/api/simulations/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail || `Simulation failed (${response.status})`);
  }

  return (await response.json()) as SimulationRunResult;
}

export async function fetchDefaultCytoParameters(): Promise<SimulationRunRequest['parameters']> {
  const response = await fetch(`${API_BASE}/api/parameters/cyto/default`);
  if (!response.ok) {
    throw new Error('Failed to load default parameters');
  }
  return (await response.json()) as SimulationRunRequest['parameters'];
}
