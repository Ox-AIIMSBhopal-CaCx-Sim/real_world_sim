/** Shared SVG pictograms for pipeline resource badges. */

export type ResourceIconKind =
  | 'technician'
  | 'junior_pathologist'
  | 'senior_pathologist'
  | 'equipment'
  | 'timer'
  | 'intake';

const LABELS: Record<ResourceIconKind, string> = {
  technician: 'Technician',
  junior_pathologist: 'Junior pathologist',
  senior_pathologist: 'Senior pathologist',
  equipment: 'Equipment',
  timer: 'Timed process',
  intake: 'Case intake',
};

export function ResourceIcon({ kind }: { kind: ResourceIconKind }) {
  return (
    <span className="resource-badge" title={LABELS[kind]}>
      <svg viewBox="0 0 40 40" width="28" height="28" aria-hidden>
        {kind === 'technician' && (
          <>
            <circle cx="20" cy="12" r="6" fill="currentColor" opacity="0.85" />
            <path
              d="M8 34c1.5-8 6-12 12-12s10.5 4 12 12"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.4"
              strokeLinecap="round"
            />
            <rect x="15" y="22" width="10" height="6" rx="1.5" fill="currentColor" opacity="0.55" />
          </>
        )}
        {kind === 'junior_pathologist' && (
          <>
            <circle cx="20" cy="11" r="5.5" fill="currentColor" opacity="0.85" />
            <path
              d="M9 34c1.2-7.5 5.5-11.5 11-11.5S30.8 26.5 32 34"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.4"
              strokeLinecap="round"
            />
            <circle cx="28" cy="22" r="5" fill="none" stroke="currentColor" strokeWidth="2" />
            <line x1="31.5" y1="25.5" x2="35" y2="29" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </>
        )}
        {kind === 'senior_pathologist' && (
          <>
            <circle cx="20" cy="11" r="5.5" fill="currentColor" opacity="0.85" />
            <path
              d="M9 34c1.2-7.5 5.5-11.5 11-11.5S30.8 26.5 32 34"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.4"
              strokeLinecap="round"
            />
            <path d="M17 21h6v3h-6z" fill="currentColor" opacity="0.45" />
            <path
              d="M14 24h12M20 24v6M16 30h8"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
            />
          </>
        )}
        {kind === 'equipment' && (
          <>
            <rect x="6" y="14" width="28" height="16" rx="3" fill="none" stroke="currentColor" strokeWidth="2.2" />
            <rect x="10" y="18" width="8" height="8" rx="1.5" fill="currentColor" opacity="0.35" />
            <circle cx="26" cy="22" r="3.2" fill="currentColor" opacity="0.7" />
            <path d="M12 10h16" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
          </>
        )}
        {kind === 'timer' && (
          <>
            <circle cx="20" cy="22" r="11" fill="none" stroke="currentColor" strokeWidth="2.2" />
            <path d="M20 22V15M20 22l5 3" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
            <path d="M16 8h8" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
          </>
        )}
        {kind === 'intake' && (
          <>
            <rect x="10" y="7" width="20" height="26" rx="2.5" fill="none" stroke="currentColor" strokeWidth="2.2" />
            <path d="M14 14h12M14 19h12M14 24h8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </>
        )}
      </svg>
      <span className="resource-badge__label">{LABELS[kind]}</span>
    </span>
  );
}
