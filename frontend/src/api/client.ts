import type {
  AuthRequest,
  AuthResponse,
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

export async function registerUser(request: AuthRequest): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  return handle<AuthResponse>(res);
}

export async function loginUser(request: AuthRequest): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  return handle<AuthResponse>(res);
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

export async function fetchRun(
  runId: string,
  username: string,
): Promise<SimulationRunResult> {
  const qs = new URLSearchParams({ username });
  const res = await fetch(
    `${API_BASE}/api/simulations/${encodeURIComponent(runId)}?${qs.toString()}`,
  );
  return handle<SimulationRunResult>(res);
}

export function healthUrl(): string {
  return `${API_BASE}/api/health`;
}
