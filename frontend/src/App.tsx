import { useCallback, useEffect, useRef, useState } from 'react';
import { LeftPane } from './components/LeftPane';
import { ParameterEditor } from './components/ParameterEditor';
import { ResultsPanel } from './components/ResultsPanel';
import { useWorkspace } from './hooks/useWorkspace';
import './App.css';

const LEFT_MIN = 300;
const LEFT_MAX = 480;
const LEFT_DEFAULT = 320;

function App() {
  const {
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
  } = useWorkspace();

  const [leftWidth, setLeftWidth] = useState(LEFT_DEFAULT);
  const [isResizing, setIsResizing] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const dragStartX = useRef(0);
  const dragStartWidth = useRef(LEFT_DEFAULT);

  const handleRun = useCallback(() => {
    setShowResults(true);
    void executeRun();
  }, [executeRun]);

  const handleNewSimulation = useCallback(() => {
    setShowResults(false);
    void startNewSimulation();
  }, [startNewSimulation]);

  const handleSelectRun = useCallback(
    (runId: string) => {
      setShowResults(true);
      selectRun(runId);
    },
    [selectRun],
  );

  useEffect(() => {
    if (!isResizing) return;

    const onMove = (event: MouseEvent) => {
      const delta = event.clientX - dragStartX.current;
      const next = Math.min(LEFT_MAX, Math.max(LEFT_MIN, dragStartWidth.current + delta));
      setLeftWidth(next);
    };

    const onUp = () => setIsResizing(false);

    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizing]);

  const onResizeStart = (event: React.MouseEvent) => {
    event.preventDefault();
    dragStartX.current = event.clientX;
    dragStartWidth.current = leftWidth;
    setIsResizing(true);
  };

  return (
    <div
      className={`app-shell${isResizing ? ' app-shell--resizing' : ''}`}
      style={{ ['--left-pane-width' as string]: `${leftWidth}px` }}
    >
      <LeftPane
        kind={kind}
        onKindChange={setKind}
        history={history}
        activeRunId={activeRunId}
        onSelectRun={handleSelectRun}
        onNewSimulation={handleNewSimulation}
        isRunning={isRunning}
        projectTitle={projectTitle}
      />

      <div
        className="resize-handle"
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize left panel"
        aria-valuenow={leftWidth}
        aria-valuemin={LEFT_MIN}
        aria-valuemax={LEFT_MAX}
        onMouseDown={onResizeStart}
      />

      <main className={`main-pane${showResults ? ' main-pane--with-results' : ''}`}>
        <section className="main-pane__top">
          <ParameterEditor
            kind={kind}
            parameters={parameters}
            loading={loadingDefaults}
            onChange={updateParameter}
            onRun={handleRun}
            isRunning={isRunning}
            resetKey={workspaceEpoch}
          />
        </section>
        {showResults ? (
          <section className="main-pane__bottom">
            <ResultsPanel result={result} isRunning={isRunning} error={error} />
          </section>
        ) : null}
      </main>
    </div>
  );
}

export default App;
