import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { fetchDefaults, runSimulation } from '../api/client';
import type {
  ParametersDict,
  RunHistoryEntry,
  SimulationKind,
  SimulationRunResult,
} from '../types/simulation';

export type WorkspaceTab =
  | { type: 'draft'; id: string; kind: SimulationKind; parameters: ParametersDict }
  | {
      type: 'run';
      id: string;
      kind: SimulationKind;
      parameters: ParametersDict | null;
      result: SimulationRunResult;
    };

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

function newDraftId() {
  return `draft-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

export function useWorkspace(username: string) {
  const [kind, setKindState] = useState<SimulationKind>('cyto');
  const [parameters, setParameters] = useState<ParametersDict | null>(null);
  const [seed] = useState<number>(42);
  const [history, setHistory] = useState<RunHistoryEntry[]>(() => loadHistory(username));
  const [openTabs, setOpenTabs] = useState<WorkspaceTab[]>([]);
  const [activeTabId, setActiveTabId] = useState<string | null>(null);
  const [result, setResult] = useState<SimulationRunResult | null>(null);
  const [activeRunParameters, setActiveRunParameters] = useState<ParametersDict | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingDefaults, setLoadingDefaults] = useState(true);
  const [workspaceEpoch, setWorkspaceEpoch] = useState(0);
  const skipKindReloadRef = useRef(false);
  const activeTabIdRef = useRef<string | null>(null);
  const parametersRef = useRef<ParametersDict | null>(null);
  const openTabsRef = useRef<WorkspaceTab[]>([]);
  const historyRef = useRef<RunHistoryEntry[]>(history);
  const kindRef = useRef(kind);

  useEffect(() => {
    activeTabIdRef.current = activeTabId;
  }, [activeTabId]);

  useEffect(() => {
    parametersRef.current = parameters;
  }, [parameters]);

  useEffect(() => {
    openTabsRef.current = openTabs;
  }, [openTabs]);

  useEffect(() => {
    historyRef.current = history;
  }, [history]);

  useEffect(() => {
    kindRef.current = kind;
  }, [kind]);

  const persistActiveDraft = useCallback(() => {
    const tabId = activeTabIdRef.current;
    const params = parametersRef.current;
    if (!tabId || !params) return;
    setOpenTabs((prev) =>
      prev.map((tab) =>
        tab.type === 'draft' && tab.id === tabId
          ? { ...tab, parameters: structuredClone(params), kind: kindRef.current }
          : tab,
      ),
    );
  }, []);

  useEffect(() => {
    setHistory(loadHistory(username));
    setOpenTabs([]);
    setActiveTabId(null);
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
        if (cancelled) return;
        setParameters(defaults);
        setResult(null);
        setActiveRunParameters(null);
        setActiveTabId((current) => {
          const tab = openTabsRef.current.find((t) => t.id === current);
          if (tab?.type === 'draft') {
            setOpenTabs((prev) =>
              prev.map((t) =>
                t.id === current && t.type === 'draft'
                  ? { ...t, kind, parameters: defaults }
                  : t,
              ),
            );
            return current;
          }
          return null;
        });
        setWorkspaceEpoch((n) => n + 1);
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

  const setKind = useCallback((next: SimulationKind) => {
    if (next === kindRef.current) return;
    persistActiveDraft();
    setKindState(next);
  }, [persistActiveDraft]);

  const updateParameter = useCallback((path: string[], value: unknown) => {
    setParameters((prev) => (prev ? setNestedValue(prev, path, value) : prev));
  }, []);

  const activateTabState = useCallback((tab: WorkspaceTab) => {
    if (tab.kind !== kindRef.current) {
      skipKindReloadRef.current = true;
      setKindState(tab.kind);
    }
    setActiveTabId(tab.id);
    if (tab.type === 'draft') {
      setParameters(structuredClone(tab.parameters));
      setResult(null);
      setActiveRunParameters(null);
    } else {
      setResult(tab.result);
      if (tab.parameters) {
        setParameters(structuredClone(tab.parameters));
        setActiveRunParameters(tab.parameters);
      } else {
        setActiveRunParameters(null);
      }
    }
    setWorkspaceEpoch((n) => n + 1);
    setError(null);
  }, []);

  const executeRun = useCallback(async () => {
    if (!parameters) return;
    const snapshot = structuredClone(parameters);
    const sourceTabId = activeTabIdRef.current;
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
      setActiveTabId(runResult.run_id);
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
      // Convert the draft into a completed recent-run selection
      setOpenTabs((prev) => prev.filter((t) => t.id !== sourceTabId));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsRunning(false);
    }
  }, [kind, parameters, seed, username]);

  const selectTab = useCallback(
    (tabId: string) => {
      persistActiveDraft();
      const open = openTabsRef.current.find((t) => t.id === tabId);
      if (open) {
        activateTabState(open);
        return;
      }

      const entry = historyRef.current.find((h) => h.run_id === tabId);
      if (!entry) return;
      const runTab: WorkspaceTab = {
        type: 'run',
        id: entry.run_id,
        kind: entry.lab,
        parameters: entry.parameters ?? null,
        result: entry.result,
      };
      activateTabState(runTab);
    },
    [activateTabState, persistActiveDraft],
  );

  const startNewSimulation = useCallback(async () => {
    persistActiveDraft();
    setLoadingDefaults(true);
    setError(null);
    try {
      const defaults = await fetchDefaults(kindRef.current);
      const id = newDraftId();
      const draft: WorkspaceTab = {
        type: 'draft',
        id,
        kind: kindRef.current,
        parameters: defaults,
      };
      setOpenTabs((prev) => [draft, ...prev]);
      setActiveTabId(id);
      setParameters(defaults);
      setResult(null);
      setActiveRunParameters(null);
      setWorkspaceEpoch((n) => n + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoadingDefaults(false);
    }
  }, [persistActiveDraft]);

  const copyParametersFromRun = useCallback((runId: string) => {
    const entry = historyRef.current.find((h) => h.run_id === runId);
    if (!entry?.parameters) return;
    const snapshot = structuredClone(entry.parameters);
    if (entry.lab !== kindRef.current) {
      skipKindReloadRef.current = true;
      setKindState(entry.lab);
    }
    setParameters(snapshot);
    setWorkspaceEpoch((n) => n + 1);
    setOpenTabs((prev) =>
      prev.map((tab) =>
        tab.type === 'draft' && tab.id === activeTabIdRef.current
          ? { ...tab, parameters: snapshot, kind: entry.lab }
          : tab,
      ),
    );
    // Keep editing — don't jump to that run's results
    setResult(null);
    setActiveRunParameters(null);
    setError(null);
  }, []);

  const deleteRun = useCallback((runId: string) => {
    setHistory((prev) => {
      const next = prev.filter((e) => e.run_id !== runId);
      saveHistory(username, next);
      return next;
    });
    if (activeTabIdRef.current === runId) {
      const fallbackDraft = openTabsRef.current.find((t) => t.type === 'draft');
      if (fallbackDraft) {
        queueMicrotask(() => activateTabState(fallbackDraft));
      } else {
        setActiveTabId(null);
        setResult(null);
        setActiveRunParameters(null);
      }
    }
  }, [activateTabState, username]);

  const closeTab = useCallback(
    (tabId: string) => {
      persistActiveDraft();
      setOpenTabs((prev) => {
        const next = prev.filter((t) => t.id !== tabId);
        if (activeTabIdRef.current === tabId) {
          const fallbackDraft = next.find((t) => t.type === 'draft');
          if (fallbackDraft) {
            queueMicrotask(() => activateTabState(fallbackDraft));
          } else {
            setActiveTabId(null);
            setResult(null);
            setActiveRunParameters(null);
          }
        }
        return next;
      });
    },
    [activateTabState, persistActiveDraft],
  );

  const projectTitle = useMemo(() => {
    if (!parameters) return '';
    return String(parameters.project_title ?? '');
  }, [parameters]);

  const activeRunId = useMemo(() => {
    if (!activeTabId) return null;
    const tab = openTabs.find((t) => t.id === activeTabId);
    if (tab?.type === 'run') return tab.id;
    if (history.some((h) => h.run_id === activeTabId)) return activeTabId;
    return null;
  }, [activeTabId, history, openTabs]);

  return {
    kind,
    setKind,
    parameters,
    updateParameter,
    history,
    openTabs,
    activeTabId,
    activeRunId,
    selectTab,
    closeTab,
    result,
    activeRunParameters,
    isRunning,
    error,
    loadingDefaults,
    executeRun,
    startNewSimulation,
    copyParametersFromRun,
    deleteRun,
    workspaceEpoch,
    projectTitle,
    seed,
  };
}
