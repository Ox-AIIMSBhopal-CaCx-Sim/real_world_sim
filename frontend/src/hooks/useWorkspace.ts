import { useCallback, useEffect, useMemo, useState } from 'react';
import { fetchDefaults, runSimulation } from '../api/client';
import type {
  ParametersDict,
  RunHistoryEntry,
  SimulationKind,
  SimulationRunResult,
} from '../types/simulation';

const HISTORY_KEY = 'des-sim-run-history';

function loadHistory(): RunHistoryEntry[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as RunHistoryEntry[];
  } catch {
    return [];
  }
}

function saveHistory(entries: RunHistoryEntry[]) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(entries.slice(0, 30)));
}

function setNestedValue(obj: ParametersDict, path: string[], value: unknown): ParametersDict {
  const next = structuredClone(obj);
  let cursor: Record<string, unknown> = next;
  for (let i = 0; i < path.length - 1; i += 1) {
    const key = path[i];
    const child = cursor[key];
    if (child === undefined || typeof child !== 'object' || child === null) {
      cursor[key] = {};
    }
    cursor = cursor[key] as Record<string, unknown>;
  }
  cursor[path[path.length - 1]] = value;
  return next;
}

export function useWorkspace() {
  const [kind, setKind] = useState<SimulationKind>('cyto');
  const [parameters, setParameters] = useState<ParametersDict | null>(null);
  const [seed] = useState<number>(42);
  const [history, setHistory] = useState<RunHistoryEntry[]>(() => loadHistory());
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [result, setResult] = useState<SimulationRunResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingDefaults, setLoadingDefaults] = useState(true);

  const [workspaceEpoch, setWorkspaceEpoch] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoadingDefaults(true);
    setError(null);
    fetchDefaults(kind)
      .then((defaults) => {
        if (!cancelled) {
          setParameters(defaults);
          setResult(null);
          setActiveRunId(null);
          setWorkspaceEpoch((n) => n + 1);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoadingDefaults(false);
      });
    return () => {
      cancelled = true;
    };
  }, [kind]);

  const updateParameter = useCallback((path: string[], value: unknown) => {
    setParameters((prev) => (prev ? setNestedValue(prev, path, value) : prev));
  }, []);

  const executeRun = useCallback(async () => {
    if (!parameters) return;
    setIsRunning(true);
    setError(null);
    try {
      const runResult = await runSimulation({ kind, parameters, seed });
      setResult(runResult);
      setActiveRunId(runResult.run_id);
      const entry: RunHistoryEntry = {
        run_id: runResult.run_id,
        lab: runResult.lab,
        project_title: runResult.project_title ?? kind,
        seed: runResult.seed,
        completed_at: new Date().toISOString(),
        result: runResult,
      };
      setHistory((prev) => {
        const next = [entry, ...prev.filter((e) => e.run_id !== entry.run_id)];
        saveHistory(next);
        return next;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsRunning(false);
    }
  }, [kind, parameters, seed]);

  const selectRun = useCallback(
    (runId: string) => {
      const entry = history.find((h) => h.run_id === runId);
      if (!entry) return;
      setActiveRunId(runId);
      setResult(entry.result);
      setKind(entry.lab);
    },
    [history],
  );

  const startNewSimulation = useCallback(async () => {
    setLoadingDefaults(true);
    setError(null);
    setResult(null);
    setActiveRunId(null);
    try {
      const defaults = await fetchDefaults(kind);
      setParameters(defaults);
      setWorkspaceEpoch((n) => n + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoadingDefaults(false);
    }
  }, [kind]);

  const projectTitle = useMemo(() => {
    if (!parameters) return '';
    return String(parameters.project_title ?? '');
  }, [parameters]);

  return {
    kind,
    setKind,
    parameters,
    updateParameter,
    history,
    activeRunId,
    selectRun,
    result,
    isRunning,
    error,
    loadingDefaults,
    executeRun,
    startNewSimulation,
    workspaceEpoch,
    projectTitle,
  };
}
