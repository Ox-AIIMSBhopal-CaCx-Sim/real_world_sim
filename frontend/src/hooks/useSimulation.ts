import { useCallback, useMemo, useState } from 'react';
import { runSimulation } from '../api/simulationApi';
import { defaultCytoParameters } from '../data/defaultParameters';
import type {
  CytoParameters,
  SimulationRunResult,
  SimulationSession,
  SimulationWorkspace,
} from '../types/simulation';

function newSessionId(): string {
  return crypto.randomUUID();
}

function formatSessionLabel(parameters: CytoParameters, results: SimulationRunResult | null): string {
  const title = parameters.project_title?.trim() || 'Untitled';
  if (results) {
    const when = new Date(results.completedAt).toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
    return `${title} · ${when}`;
  }
  return title;
}

function createSession(
  parameters: CytoParameters = structuredClone(defaultCytoParameters),
  results: SimulationRunResult | null = null,
): SimulationSession {
  const now = new Date().toISOString();
  return {
    id: newSessionId(),
    label: formatSessionLabel(parameters, results),
    kind: 'cyto',
    parameters,
    results,
    createdAt: now,
    updatedAt: now,
  };
}

function createInitialWorkspace(): SimulationWorkspace {
  const session = createSession();
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
  patch: Partial<Pick<SimulationSession, 'parameters' | 'results' | 'label' | 'labelIsCustom'>>,
): SimulationSession[] {
  return sessions.map((s) => {
    if (s.id !== sessionId) return s;
    const next = { ...s, ...patch, updatedAt: new Date().toISOString() };
    if (!next.labelIsCustom) {
      next.label = formatSessionLabel(next.parameters, next.results);
    }
    return next;
  });
}

export function useSimulation() {
  const [workspace, setWorkspace] = useState<SimulationWorkspace>(createInitialWorkspace);

  const activeSession = useMemo(
    () => workspace.sessions.find((s) => s.id === workspace.activeSessionId) ?? workspace.sessions[0],
    [workspace.sessions, workspace.activeSessionId],
  );

  const startNewSimulation = useCallback(() => {
    setWorkspace((prev) => {
      const fresh = createSession();
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

  const updateParameters = useCallback((parameters: CytoParameters) => {
    setWorkspace((prev) => ({
      ...prev,
      error: null,
      sessions: patchSession(prev.sessions, prev.activeSessionId, { parameters }),
    }));
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
    updateParameters,
    executeRun,
    isRunning: workspace.isRunning,
    error: workspace.error,
  };
}
