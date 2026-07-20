import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
    openTabs,
    activeTabId,
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
  } = useWorkspace(username);

  const [leftWidth, setLeftWidth] = useState(LEFT_DEFAULT);
  const [isResizing, setIsResizing] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [compareRunId, setCompareRunId] = useState<string | null>(null);
  const dragStartX = useRef(0);
  const dragStartWidth = useRef(LEFT_DEFAULT);

  const compareEntry = useMemo(() => {
    if (!compareRunId) return null;
    return history.find((entry) => entry.run_id === compareRunId) ?? null;
  }, [compareRunId, history]);

  const compareResult = compareEntry?.result ?? null;
  const compareParameters = compareEntry?.parameters ?? null;
  const compareSeed = compareEntry?.seed ?? null;

  const clearCompare = useCallback(() => setCompareRunId(null), []);

  const handleRun = useCallback(() => {
    clearCompare();
    setShowResults(true);
    void executeRun();
  }, [clearCompare, executeRun]);

  const handleNewSimulation = useCallback(() => {
    clearCompare();
    setShowResults(false);
    void startNewSimulation();
  }, [clearCompare, startNewSimulation]);

  const handleSelectTab = useCallback(
    (tabId: string) => {
      const isDraft = tabId.startsWith('draft-');
      const open = openTabs.find((t) => t.id === tabId);
      clearCompare();
      setShowResults(!(isDraft || open?.type === 'draft'));
      selectTab(tabId);
    },
    [clearCompare, openTabs, selectTab],
  );

  const handleCloseTab = useCallback(
    (tabId: string) => {
      if (activeTabId === tabId) {
        clearCompare();
        setShowResults(false);
      }
      closeTab(tabId);
    },
    [activeTabId, clearCompare, closeTab],
  );

  const handleCopyParameters = useCallback(
    (runId: string) => {
      clearCompare();
      setShowResults(false);
      copyParametersFromRun(runId);
    },
    [clearCompare, copyParametersFromRun],
  );

  const handleDeleteRun = useCallback(
    (runId: string) => {
      if (compareRunId === runId) clearCompare();
      if (activeTabId === runId) {
        clearCompare();
        setShowResults(false);
      }
      deleteRun(runId);
    },
    [activeTabId, clearCompare, compareRunId, deleteRun],
  );

  const handleDropRun = useCallback(
    (runId: string) => {
      const entry = history.find((h) => h.run_id === runId);
      if (!entry) return;

      // Already viewing this run alone — nothing to compare
      if (result?.run_id === runId && !compareRunId) {
        setShowResults(true);
        return;
      }

      // Dropping the active run while comparing just clears the partner
      if (result?.run_id === runId) {
        clearCompare();
        setShowResults(true);
        return;
      }

      // Have a primary result → add / replace compare partner
      if (result && result.run_id !== runId) {
        setCompareRunId(runId);
        setShowResults(true);
        return;
      }

      // No primary yet — open the dropped run as primary
      clearCompare();
      setShowResults(true);
      selectTab(runId);
    },
    [clearCompare, compareRunId, history, result, selectTab],
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
        openTabs={openTabs}
        activeTabId={activeTabId}
        onSelectTab={handleSelectTab}
        onCloseTab={handleCloseTab}
        onNewSimulation={handleNewSimulation}
        onCopyParametersFromRun={handleCopyParameters}
        onDeleteRun={handleDeleteRun}
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
            compareResult={compareResult}
            compareParameters={compareParameters}
            compareSeed={compareSeed}
            onClearCompare={clearCompare}
            onDropRun={handleDropRun}
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
