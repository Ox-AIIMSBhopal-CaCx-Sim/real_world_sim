import type {
  ParametersDict,
  SimulationKind,
  SimulationRunRequest,
  SimulationRunResult,
} from '../types/simulation';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}

export async function fetchDefaults(kind: SimulationKind): Promise<ParametersDict> {
  const res = await fetch(`${API_BASE}/api/parameters/defaults/${kind}`);
  return handle<ParametersDict>(res);
}

export async function runSimulation(
  request: SimulationRunRequest,
): Promise<SimulationRunResult> {
  const res = await fetch(`${API_BASE}/api/simulations/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  return handle<SimulationRunResult>(res);
}

export async function fetchRun(runId: string): Promise<SimulationRunResult> {
  const res = await fetch(`${API_BASE}/api/simulations/${encodeURIComponent(runId)}`);
  return handle<SimulationRunResult>(res);
}

export function healthUrl(): string {
  return `${API_BASE}/api/health`;
}
