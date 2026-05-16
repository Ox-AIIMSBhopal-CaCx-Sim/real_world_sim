import type { ReactNode } from 'react';

interface AppLayoutProps {
  sidebar: ReactNode;
  center: ReactNode;
  results: ReactNode;
}

export function AppLayout({ sidebar, center, results }: AppLayoutProps) {
  return (
    <div className="app-shell">
      <aside className="panel panel--sidebar">{sidebar}</aside>
      <main className="panel panel--center">{center}</main>
      <aside className="panel panel--results">{results}</aside>
    </div>
  );
}
