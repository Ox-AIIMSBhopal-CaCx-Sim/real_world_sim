import { useEffect, useRef, useState } from 'react';
import type { SimulationSession } from '../../types/simulation';

interface SessionTabProps {
  session: SimulationSession;
  isActive: boolean;
  disabled: boolean;
  onSelect: () => void;
  onRename: (label: string) => void;
}

export function SessionTab({
  session,
  isActive,
  disabled,
  onSelect,
  onRename,
}: SessionTabProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(session.label);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!editing) setDraft(session.label);
  }, [session.label, editing]);

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  const commitRename = () => {
    setEditing(false);
    onRename(draft);
  };

  const cancelRename = () => {
    setEditing(false);
    setDraft(session.label);
  };

  if (editing) {
    return (
      <div className={`session-tab session-tab--editing${isActive ? ' session-tab--active' : ''}`}>
        <input
          ref={inputRef}
          type="text"
          className="session-tab__input"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commitRename}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              commitRename();
            }
            if (e.key === 'Escape') {
              e.preventDefault();
              cancelRename();
            }
          }}
          onClick={(e) => e.stopPropagation()}
          aria-label="Simulation name"
        />
      </div>
    );
  }

  return (
    <div className={`session-tab${isActive ? ' session-tab--active' : ''}`}>
      <button
        type="button"
        role="tab"
        aria-selected={isActive}
        className="session-tab__select"
        onClick={onSelect}
        disabled={disabled}
        title={session.label}
        onDoubleClick={(e) => {
          e.preventDefault();
          if (!disabled) setEditing(true);
        }}
      >
        <span className="session-tab__label">{session.label}</span>
        {session.results && (
          <span className="session-tab__badge" aria-label="Has results">
            ●
          </span>
        )}
      </button>
      <button
        type="button"
        className="session-tab__rename"
        onClick={() => setEditing(true)}
        disabled={disabled}
        aria-label={`Rename ${session.label}`}
        title="Rename"
      >
        ✎
      </button>
    </div>
  );
}
