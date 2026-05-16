import { useCallback, useState } from 'react';
import { runSimulation } from '../api/simulationApi';
import { defaultCytoParameters } from '../data/defaultParameters';
import type { CytoParameters, SimulationState } from '../types/simulation';

function createInitialState(): SimulationState {
  return {
    kind: 'cyto',
    parameters: structuredClone(defaultCytoParameters),
    results: null,
    isRunning: false,
    error: null,
  };
}

export function useSimulation() {
  const [state, setState] = useState<SimulationState>(createInitialState);

  const resetSimulation = useCallback(() => {
    setState(createInitialState());
  }, []);

  const updateParameters = useCallback((parameters: CytoParameters) => {
    setState((prev) => ({ ...prev, parameters, error: null }));
  }, []);

  const executeRun = useCallback(() => {
    setState((prev) => {
      const run = async () => {
        try {
          const results = await runSimulation({
            kind: prev.kind,
            parameters: prev.parameters,
          });
          setState((p) => ({ ...p, results, isRunning: false }));
        } catch (err) {
          const message = err instanceof Error ? err.message : 'Simulation failed';
          setState((p) => ({ ...p, isRunning: false, error: message }));
        }
      };
      void run();
      return { ...prev, isRunning: true, error: null, results: null };
    });
  }, []);

  return {
    state,
    resetSimulation,
    updateParameters,
    executeRun,
  };
}
