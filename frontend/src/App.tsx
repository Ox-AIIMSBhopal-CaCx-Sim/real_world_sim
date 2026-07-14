import { LeftPane } from './components/LeftPane';
import { ParameterEditor } from './components/ParameterEditor';
import { ResultsPanel } from './components/ResultsPanel';
import { useWorkspace } from './hooks/useWorkspace';
import './App.css';

function App() {
  const {
    kind,
    setKind,
    parameters,
    updateParameter,
    seed,
    setSeed,
    history,
    activeRunId,
    selectRun,
    result,
    isRunning,
    error,
    loadingDefaults,
    executeRun,
    projectTitle,
  } = useWorkspace();

  return (
    <div className="app-shell">
      <LeftPane
        kind={kind}
        onKindChange={setKind}
        seed={seed}
        onSeedChange={setSeed}
        history={history}
        activeRunId={activeRunId}
        onSelectRun={selectRun}
        onRun={executeRun}
        isRunning={isRunning}
        projectTitle={projectTitle}
      />
      <main className="main-pane">
        <section className="main-pane__top">
          <ParameterEditor
            kind={kind}
            parameters={parameters}
            loading={loadingDefaults}
            onChange={updateParameter}
          />
        </section>
        <section className="main-pane__bottom">
          <ResultsPanel result={result} isRunning={isRunning} error={error} />
        </section>
      </main>
      {/* Reserved for future chatbot pane
      <aside className="chat-pane" />
      */}
    </div>
  );
}

export default App;
