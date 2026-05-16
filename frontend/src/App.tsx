import { AppLayout } from './components/layout/AppLayout';
import { ResultsPanel } from './components/results/ResultsPanel';
import { Sidebar } from './components/sidebar/Sidebar';
import { SimPanel } from './components/sim/SimPanel';
import { useSimulation } from './hooks/useSimulation';
import './App.css';

function App() {
  const {
    workspace,
    activeSession,
    startNewSimulation,
    selectSession,
    renameSession,
    setKind,
    updateParameters,
    executeRun,
    isRunning,
    error,
  } = useSimulation();

  return (
    <AppLayout
      sidebar={
        <Sidebar
          sessions={workspace.sessions}
          activeSessionId={workspace.activeSessionId}
          onNewSim={startNewSimulation}
          onSelectSession={selectSession}
          onRenameSession={renameSession}
          isRunning={isRunning}
        />
      }
      center={
        <SimPanel
          kind={activeSession.kind}
          parameters={activeSession.parameters}
          onKindChange={setKind}
          onParametersChange={updateParameters}
          onRun={executeRun}
          isRunning={isRunning}
          error={error}
        />
      }
      results={
        <ResultsPanel results={activeSession.results} isRunning={isRunning} />
      }
    />
  );
}

export default App;
