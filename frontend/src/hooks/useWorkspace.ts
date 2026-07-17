import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { fetchDefaults, runSimulation } from '../api/client';
import type {
  ParametersDict,
  RunHistoryEntry,
  SimulationKind,
  SimulationRunResult,
} from '../types/simulation';

function historyKey(username: string) {
  return `des-sim-run-history:${username}`;
}

function loadHistory(username: string): RunHistoryEntry[] {
  try {
    const raw = localStorage.getItem(historyKey(username));
    if (!raw) return [];
    return JSON.parse(raw) as RunHistoryEntry[];
  } catch {
    return [];
  }
}

function saveHistory(username: string, entries: RunHistoryEntry[]) {
  localStorage.setItem(historyKey(username), JSON.stringify(entries.slice(0, 30)));
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

export function useWorkspace(username: string) {
  const [kind, setKind] = useState<SimulationKind>('cyto');
  const [parameters, setParameters] = useState<ParametersDict | null>(null);
  const [seed] = useState<number>(42);
  const [history, setHistory] = useState<RunHistoryEntry[]>(() => loadHistory(username));
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [result, setResult] = useState<SimulationRunResult | null>(null);
  const [activeRunParameters, setActiveRunParameters] = useState<ParametersDict | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingDefaults, setLoadingDefaults] = useState(true);
  const [workspaceEpoch, setWorkspaceEpoch] = useState(0);
  const skipKindReloadRef = useRef(false);

  useEffect(() => {
    setHistory(loadHistory(username));
    setActiveRunId(null);
    setResult(null);
    setActiveRunParameters(null);
    setError(null);
  }, [username]);

  useEffect(() => {
    if (skipKindReloadRef.current) {
      skipKindReloadRef.current = false;
      return;
    }

    let cancelled = false;
    setLoadingDefaults(true);
    setError(null);
    fetchDefaults(kind)
      .then((defaults) => {
        if (!cancelled) {
          setParameters(defaults);
          setResult(null);
          setActiveRunId(null);
          setActiveRunParameters(null);
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
    const snapshot = structuredClone(parameters);
    setIsRunning(true);
    setError(null);
    setActiveRunParameters(snapshot);
    try {
      const runResult = await runSimulation({
        kind,
        parameters: snapshot,
        seed,
        username,
      });
      setResult(runResult);
      setActiveRunId(runResult.run_id);
      const entry: RunHistoryEntry = {
        run_id: runResult.run_id,
        lab: runResult.lab,
        project_title: runResult.project_title ?? kind,
        seed: runResult.seed,
        completed_at: new Date().toISOString(),
        result: runResult,
        parameters: snapshot,
      };
      setHistory((prev) => {
        const next = [entry, ...prev.filter((e) => e.run_id !== entry.run_id)];
        saveHistory(username, next);
        return next;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsRunning(false);
    }
  }, [kind, parameters, seed, username]);

  const selectRun = useCallback(
    (runId: string) => {
      const entry = history.find((h) => h.run_id === runId);
      if (!entry) return;
      if (entry.lab !== kind) {
        skipKindReloadRef.current = true;
        setKind(entry.lab);
      }
      setActiveRunId(runId);
      setResult(entry.result);
      if (entry.parameters) {
        setParameters(entry.parameters);
        setActiveRunParameters(entry.parameters);
      } else {
        setActiveRunParameters(null);
      }
    },
    [history, kind],
  );

  const startNewSimulation = useCallback(async () => {
    setLoadingDefaults(true);
    setError(null);
    setResult(null);
    setActiveRunId(null);
    setActiveRunParameters(null);
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
    activeRunParameters,
    isRunning,
    error,
    loadingDefaults,
    executeRun,
    startNewSimulation,
    workspaceEpoch,
    projectTitle,
    seed,
  };
}
