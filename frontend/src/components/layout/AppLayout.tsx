import { useCallback, useState, type ReactNode } from 'react';
import { ResizeHandle } from './ResizeHandle';

const SIDEBAR_MIN = 180;
const SIDEBAR_MAX = 420;
const SIDEBAR_DEFAULT = 240;
const RESULTS_MIN = 280;
const RESULTS_MAX = 640;
const RESULTS_DEFAULT = 380;

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

interface AppLayoutProps {
  sidebar: ReactNode;
  center: ReactNode;
  results: ReactNode;
}

export function AppLayout({ sidebar, center, results }: AppLayoutProps) {
  const [sidebarWidth, setSidebarWidth] = useState(SIDEBAR_DEFAULT);
  const [resultsWidth, setResultsWidth] = useState(RESULTS_DEFAULT);

  const resizeSidebar = useCallback((deltaX: number) => {
    setSidebarWidth((w) => clamp(w + deltaX, SIDEBAR_MIN, SIDEBAR_MAX));
  }, []);

  const resizeResults = useCallback((deltaX: number) => {
    setResultsWidth((w) => clamp(w - deltaX, RESULTS_MIN, RESULTS_MAX));
  }, []);

  return (
    <div className="app-shell">
      <aside className="panel panel--sidebar" style={{ width: sidebarWidth }}>
        {sidebar}
      </aside>
      <ResizeHandle onDrag={resizeSidebar} ariaLabel="Resize sidebar" />
      <main className="panel panel--center">{center}</main>
      <ResizeHandle onDrag={resizeResults} ariaLabel="Resize results panel" />
      <aside className="panel panel--results" style={{ width: resultsWidth }}>
        {results}
      </aside>
    </div>
  );
}
