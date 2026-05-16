import { AppLayout } from './components/layout/AppLayout';
import { ResultsPanel } from './components/results/ResultsPanel';
import { Sidebar } from './components/sidebar/Sidebar';
import { SimPanel } from './components/sim/SimPanel';
import { useSimulation } from './hooks/useSimulation';
import './App.css';

function App() {
  const { state, resetSimulation, updateParameters, executeRun } = useSimulation();

  return (
    <AppLayout
      sidebar={
        <Sidebar
          onNewSim={resetSimulation}
          projectTitle={state.parameters.project_title}
          isRunning={state.isRunning}
        />
      }
      center={
        <SimPanel
          parameters={state.parameters}
          onParametersChange={updateParameters}
          onRun={executeRun}
          isRunning={state.isRunning}
          error={state.error}
        />
      }
      results={
        <ResultsPanel results={state.results} isRunning={state.isRunning} />
      }
    />
  );
}

export default App;
