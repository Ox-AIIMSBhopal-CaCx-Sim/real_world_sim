import { useCallback, useMemo, useState } from 'react';
import { runSimulation } from '../api/simulationApi';
import { defaultParametersForKind } from '../data/defaultParameters';
import type {
  SimulationKind,
  SimulationParameters,
  SimulationRunResult,
  SimulationSession,
  SimulationWorkspace,
} from '../types/simulation';

function newSessionId(): string {
  return crypto.randomUUID();
}

function formatSessionLabel(
  parameters: SimulationParameters,
  results: SimulationRunResult | null,
  kind: SimulationKind,
): string {
  const title = parameters.project_title?.trim() || 'Untitled';
  const prefix = kind === 'histo' ? 'Histo' : 'Cyto';
  if (results) {
    const when = new Date(results.completedAt).toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
    return `${prefix}: ${title} · ${when}`;
  }
  return `${prefix}: ${title}`;
}

function createSession(
  kind: SimulationKind = 'cyto',
  parameters?: SimulationParameters,
  results: SimulationRunResult | null = null,
): SimulationSession {
  const params = parameters ?? defaultParametersForKind(kind);
  const now = new Date().toISOString();
  return {
    id: newSessionId(),
    label: formatSessionLabel(params, results, kind),
    kind,
    parameters: params,
    paramCache: { [kind]: { parameters: structuredClone(params), results } },
    results,
    createdAt: now,
    updatedAt: now,
  };
}

function createInitialWorkspace(): SimulationWorkspace {
  const session = createSession('cyto');
  return {
    sessions: [session],
    activeSessionId: session.id,
    isRunning: false,
    error: null,
  };
}

function patchSession(
  sessions: SimulationSession[],
  sessionId: string,
  patch: Partial<
    Pick<
      SimulationSession,
      'parameters' | 'results' | 'label' | 'labelIsCustom' | 'kind' | 'paramCache'
    >
  >,
): SimulationSession[] {
  return sessions.map((s) => {
    if (s.id !== sessionId) return s;
    const next: SimulationSession = { ...s, ...patch, updatedAt: new Date().toISOString() };
    if (patch.parameters !== undefined || patch.results !== undefined) {
      next.paramCache = {
        ...next.paramCache,
        [next.kind]: { parameters: next.parameters, results: next.results },
      };
    }
    if (!next.labelIsCustom) {
      next.label = formatSessionLabel(next.parameters, next.results, next.kind);
    }
    return next;
  });
}

export function useSimulation() {
  const [workspace, setWorkspace] = useState<SimulationWorkspace>(createInitialWorkspace);

  const activeSession = useMemo(
    () =>
      workspace.sessions.find((s) => s.id === workspace.activeSessionId) ??
      workspace.sessions[0],
    [workspace.sessions, workspace.activeSessionId],
  );

  const startNewSimulation = useCallback(() => {
    setWorkspace((prev) => {
      const active = prev.sessions.find((s) => s.id === prev.activeSessionId);
      const kind = active?.kind ?? 'cyto';
      const fresh = createSession(kind);
      return {
        ...prev,
        sessions: [...prev.sessions, fresh],
        activeSessionId: fresh.id,
        isRunning: false,
        error: null,
      };
    });
  }, []);

  const selectSession = useCallback((sessionId: string) => {
    setWorkspace((prev) => {
      if (prev.isRunning || !prev.sessions.some((s) => s.id === sessionId)) return prev;
      return { ...prev, activeSessionId: sessionId, error: null };
    });
  }, []);

  const renameSession = useCallback((sessionId: string, label: string) => {
    const trimmed = label.trim() || 'Untitled';
    setWorkspace((prev) => ({
      ...prev,
      sessions: patchSession(prev.sessions, sessionId, {
        label: trimmed,
        labelIsCustom: true,
      }),
    }));
  }, []);

  const setKind = useCallback((kind: SimulationKind) => {
    setWorkspace((prev) => {
      const session = prev.sessions.find((s) => s.id === prev.activeSessionId);
      if (!session || session.kind === kind || prev.isRunning) return prev;

      const cache = {
        ...session.paramCache,
        [session.kind]: {
          parameters: structuredClone(session.parameters),
          results: session.results,
        },
      };
      const cached = cache[kind];
      const parameters = cached?.parameters ?? defaultParametersForKind(kind);
      const results = cached?.results ?? null;

      return {
        ...prev,
        error: null,
        sessions: patchSession(prev.sessions, prev.activeSessionId, {
          kind,
          parameters,
          paramCache: cache,
          results,
        }),
      };
    });
  }, []);

  const updateParameters = useCallback((parameters: SimulationParameters) => {
    setWorkspace((prev) => {
      const session = prev.sessions.find((s) => s.id === prev.activeSessionId);
      if (!session) return prev;
      const cache = {
        ...session.paramCache,
        [session.kind]: { parameters, results: session.results },
      };
      return {
        ...prev,
        error: null,
        sessions: patchSession(prev.sessions, prev.activeSessionId, {
          parameters,
          paramCache: cache,
        }),
      };
    });
  }, []);

  const executeRun = useCallback(() => {
    setWorkspace((prev) => {
      const session = prev.sessions.find((s) => s.id === prev.activeSessionId);
      if (!session) return prev;

      const run = async () => {
        try {
          const results = await runSimulation({
            kind: session.kind,
            parameters: session.parameters,
          });
          setWorkspace((p) => ({
            ...p,
            isRunning: false,
            sessions: patchSession(p.sessions, p.activeSessionId, { results }),
          }));
        } catch (err) {
          const message = err instanceof Error ? err.message : 'Simulation failed';
          setWorkspace((p) => ({ ...p, isRunning: false, error: message }));
        }
      };

      void run();
      return {
        ...prev,
        isRunning: true,
        error: null,
        sessions: patchSession(prev.sessions, prev.activeSessionId, { results: null }),
      };
    });
  }, []);

  return {
    workspace,
    activeSession,
    startNewSimulation,
    selectSession,
    renameSession,
    setKind,
    updateParameters,
    executeRun,
    isRunning: workspace.isRunning,
    error: workspace.error,
  };
}
