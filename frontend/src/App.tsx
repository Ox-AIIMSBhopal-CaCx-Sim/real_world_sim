import { useCallback, useEffect, useRef, useState } from 'react';
import { LeftPane } from './components/LeftPane';
import { LoginScreen } from './components/LoginScreen';
import { ParameterEditor } from './components/ParameterEditor';
import { useAuth } from './hooks/useAuth';
import { useWorkspace } from './hooks/useWorkspace';
import './App.css';

const LEFT_MIN = 300;
const LEFT_MAX = 480;
const LEFT_DEFAULT = 320;

function WorkspaceApp({
  username,
  onLogout,
}: {
  username: string;
  onLogout: () => void;
}) {
  const {
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
  } = useWorkspace(username);

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
        viewingResults={showResults}
        projectTitle={projectTitle}
        username={username}
        onLogout={onLogout}
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

      <main className="main-pane">
        <section className="main-pane__content">
          <ParameterEditor
            kind={kind}
            parameters={parameters}
            loading={loadingDefaults}
            onChange={updateParameter}
            onRun={handleRun}
            isRunning={isRunning}
            resetKey={workspaceEpoch}
            showResults={showResults}
            result={result}
            error={error}
            runParameters={activeRunParameters}
            seed={seed}
          />
        </section>
      </main>
    </div>
  );
}

function App() {
  const { username, login, register, logout, error, setError, busy } = useAuth();

  if (!username) {
    return (
      <LoginScreen
        onLogin={async (name, password) => {
          setError(null);
          await login(name, password);
        }}
        onRegister={async (name, password) => {
          setError(null);
          await register(name, password);
        }}
        error={error}
        busy={busy}
      />
    );
  }

  return <WorkspaceApp username={username} onLogout={logout} />;
}

export default App;
