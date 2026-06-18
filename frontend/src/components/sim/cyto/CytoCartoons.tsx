import type { ReactNode } from 'react';

interface CartoonProps {
  className?: string;
  onClick?: () => void;
  selected?: boolean;
  label: string;
  ariaLabel: string;
}

const stroke = '#1a1a1a';
const skin = '#f5d0b5';
const hair = '#6b4423';
const coat = '#ffffff';
const shirtPink = '#f4b8c8';
const shirtBlue = '#b8d4f0';
const liquid = '#7ec8e3';

function ClickableGroup({
  className,
  onClick,
  selected,
  label,
  ariaLabel,
  children,
}: CartoonProps & { children: ReactNode }) {
  return (
    <button
      type="button"
      className={`cyto-cartoon ${className ?? ''} ${selected ? 'cyto-cartoon--selected' : ''}`}
      onClick={onClick}
      aria-label={ariaLabel}
      aria-pressed={selected}
    >
      <svg viewBox="0 0 160 180" className="cyto-cartoon__svg" aria-hidden="true">
        {children}
      </svg>
      <span className="cyto-cartoon__label">{label}</span>
    </button>
  );
}

export function ReceptionProfessional(props: Omit<CartoonProps, 'label' | 'ariaLabel'>) {
  return (
    <ClickableGroup {...props} label="Reception" ariaLabel="Reception staff — edit headcount and service times">
      <g className="cyto-anim cyto-anim--reception">
        <ellipse cx="80" cy="48" rx="22" ry="24" fill={skin} stroke={stroke} strokeWidth="2.5" />
        <path d="M58 42 Q80 28 102 42" fill={hair} stroke={stroke} strokeWidth="2" />
        <circle cx="72" cy="48" r="2.5" fill={stroke} />
        <circle cx="88" cy="48" r="2.5" fill={stroke} />
        <path d="M74 58 Q80 62 86 58" fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" />
        <rect x="48" y="70" width="64" height="70" rx="6" fill={coat} stroke={stroke} strokeWidth="2.5" />
        <rect x="58" y="78" width="44" height="18" rx="3" fill={shirtPink} stroke={stroke} strokeWidth="2" />
        <rect x="38" y="108" width="84" height="12" rx="2" fill="#d1d5db" stroke={stroke} strokeWidth="2" />
        <rect x="42" y="88" width="28" height="20" rx="2" fill="#374151" stroke={stroke} strokeWidth="2" />
        <rect x="46" y="92" width="20" height="12" fill="#93c5fd" />
        <g className="cyto-anim__typing-hand">
          <rect x="112" y="96" width="10" height="14" rx="3" fill={skin} stroke={stroke} strokeWidth="2" />
        </g>
        <rect x="18" y="120" width="36" height="24" rx="4" fill="#fef3c7" stroke={stroke} strokeWidth="2" />
        <text x="36" y="136" textAnchor="middle" fontSize="10" fill={stroke} fontWeight="700">
          IN
        </text>
      </g>
    </ClickableGroup>
  );
}

export function ProcessingProfessional(props: Omit<CartoonProps, 'label' | 'ariaLabel'>) {
  return (
    <ClickableGroup {...props} label="Processing" ariaLabel="Lab technician — edit headcount and service times">
      <g className="cyto-anim cyto-anim--processing">
        <ellipse cx="80" cy="46" rx="22" ry="24" fill={skin} stroke={stroke} strokeWidth="2.5" />
        <path d="M58 40 Q80 24 102 40" fill={hair} stroke={stroke} strokeWidth="2" />
        <circle cx="72" cy="46" r="2.5" fill={stroke} />
        <circle cx="88" cy="46" r="2.5" fill={stroke} />
        <rect x="56" y="52" width="48" height="14" rx="7" fill="none" stroke={stroke} strokeWidth="2.5" opacity="0.85" />
        <rect x="48" y="68" width="64" height="72" rx="6" fill={coat} stroke={stroke} strokeWidth="2.5" />
        <rect x="58" y="76" width="44" height="18" rx="3" fill={shirtPink} stroke={stroke} strokeWidth="2" />
        <g className="cyto-anim__flask">
          <path
            d="M34 118 L34 100 L48 82 L48 118 Z"
            fill="none"
            stroke={stroke}
            strokeWidth="2.5"
            strokeLinejoin="round"
          />
          <path d="M34 118 L48 118 L44 130 L38 130 Z" fill={liquid} stroke={stroke} strokeWidth="2" />
        </g>
        <g className="cyto-anim__pipette">
          <line x1="118" y1="78" x2="118" y2="118" stroke={stroke} strokeWidth="3" strokeLinecap="round" />
          <circle cx="118" cy="122" r="4" fill={liquid} stroke={stroke} strokeWidth="2" />
        </g>
        <ellipse cx="118" cy="128" rx="3" ry="5" fill={liquid} className="cyto-anim__drop" opacity="0.8" />
      </g>
    </ClickableGroup>
  );
}

export function ReportingProfessional(props: Omit<CartoonProps, 'label' | 'ariaLabel'>) {
  return (
    <ClickableGroup {...props} label="Reporting" ariaLabel="Cytopathologist — edit headcount and service times">
      <g className="cyto-anim cyto-anim--reporting">
        <ellipse cx="80" cy="46" rx="22" ry="24" fill={skin} stroke={stroke} strokeWidth="2.5" />
        <path d="M58 40 Q80 24 102 40" fill={hair} stroke={stroke} strokeWidth="2" />
        <circle cx="72" cy="46" r="2.5" fill={stroke} />
        <circle cx="88" cy="46" r="2.5" fill={stroke} />
        <rect x="48" y="68" width="64" height="72" rx="6" fill={coat} stroke={stroke} strokeWidth="2.5" />
        <rect x="58" y="76" width="44" height="18" rx="3" fill={shirtBlue} stroke={stroke} strokeWidth="2" />
        <g className="cyto-anim__microscope-head">
          <rect x="22" y="108" width="56" height="8" rx="2" fill="#94a3b8" stroke={stroke} strokeWidth="2" />
          <rect x="38" y="88" width="24" height="22" rx="4" fill="#64748b" stroke={stroke} strokeWidth="2" />
          <circle cx="50" cy="98" r="6" fill="#bae6fd" stroke={stroke} strokeWidth="2" />
        </g>
        <g className="cyto-anim__writing-hand">
          <rect x="108" y="100" width="36" height="28" rx="3" fill="#fef9c3" stroke={stroke} strokeWidth="2" />
          <line x1="114" y1="110" x2="138" y2="110" stroke={stroke} strokeWidth="1.5" />
          <line x1="114" y1="118" x2="132" y2="118" stroke={stroke} strokeWidth="1.5" />
          <path d="M142 112 L148 118 L142 124" fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" />
        </g>
      </g>
    </ClickableGroup>
  );
}

export function ReceptionEquipment(props: Omit<CartoonProps, 'label' | 'ariaLabel'>) {
  return (
    <ClickableGroup {...props} label="Intake system" ariaLabel="Sample intake equipment — edit arrival and complexity settings">
      <g className="cyto-anim cyto-anim--equipment">
        <rect x="20" y="40" width="120" height="80" rx="8" fill="#e5e7eb" stroke={stroke} strokeWidth="2.5" />
        <rect x="30" y="50" width="100" height="56" rx="4" fill="#374151" stroke={stroke} strokeWidth="2" />
        <rect x="38" y="58" width="84" height="40" fill="#93c5fd" />
        <rect x="46" y="66" width="36" height="6" rx="2" fill="#ffffff" opacity="0.8" />
        <rect x="46" y="78" width="52" height="6" rx="2" fill="#ffffff" opacity="0.6" />
        <rect x="24" y="128" width="112" height="28" rx="6" fill="#fef3c7" stroke={stroke} strokeWidth="2.5" />
        <circle cx="44" cy="142" r="8" fill="#fca5a5" stroke={stroke} strokeWidth="2" />
        <circle cx="68" cy="142" r="8" fill="#86efac" stroke={stroke} strokeWidth="2" />
        <circle cx="92" cy="142" r="8" fill="#93c5fd" stroke={stroke} strokeWidth="2" />
         <circle cx="116" cy="142" r="8" fill="#fcd34d" stroke={stroke} strokeWidth="2" className="cyto-anim__sample-blink" />
      </g>
    </ClickableGroup>
  );
}

export function ProcessingEquipment(props: Omit<CartoonProps, 'label' | 'ariaLabel'>) {
  return (
    <ClickableGroup {...props} label="Staining station" ariaLabel="Staining station — edit batch size, stations, and error rate">
      <g className="cyto-anim cyto-anim--equipment">
        <rect x="28" y="48" width="104" height="88" rx="10" fill="#f1f5f9" stroke={stroke} strokeWidth="2.5" />
        <circle cx="80" cy="92" r="32" fill="#ffffff" stroke={stroke} strokeWidth="2.5" />
        <g className="cyto-anim__centrifuge">
          <circle cx="80" cy="92" r="20" fill="none" stroke={stroke} strokeWidth="2" strokeDasharray="6 4" />
          <rect x="72" y="84" width="16" height="16" rx="2" fill={liquid} stroke={stroke} strokeWidth="2" />
        </g>
        <rect x="40" y="138" width="80" height="16" rx="4" fill="#64748b" stroke={stroke} strokeWidth="2" />
        <circle cx="52" cy="146" r="4" fill="#22c55e" className="cyto-anim__status-light" />
        <text x="80" y="154" textAnchor="middle" fontSize="8" fill="#ffffff" fontWeight="600">
          BATCH
        </text>
      </g>
    </ClickableGroup>
  );
}

export function ReportingEquipment(props: Omit<CartoonProps, 'label' | 'ariaLabel'>) {
  return (
    <ClickableGroup {...props} label="Microscope bench" ariaLabel="Reporting microscope bench — edit stations, batch size, and error rate">
      <g className="cyto-anim cyto-anim--equipment">
        <rect x="16" y="130" width="128" height="20" rx="4" fill="#78716c" stroke={stroke} strokeWidth="2.5" />
        <rect x="48" y="72" width="12" height="58" fill="#57534e" stroke={stroke} strokeWidth="2" />
        <rect x="32" y="64" width="44" height="16" rx="4" fill="#44403c" stroke={stroke} strokeWidth="2" />
        <g className="cyto-anim__scope-lens">
          <circle cx="54" cy="56" r="14" fill="#bae6fd" stroke={stroke} strokeWidth="2.5" />
          <circle cx="54" cy="56" r="6" fill="#0ea5e9" opacity="0.5" />
        </g>
        <rect x="96" y="88" width="40" height="32" rx="4" fill="#fef9c3" stroke={stroke} strokeWidth="2" />
        <line x1="102" y1="98" x2="130" y2="98" stroke={stroke} strokeWidth="1.5" />
        <line x1="102" y1="106" x2="124" y2="106" stroke={stroke} strokeWidth="1.5" />
        <rect x="104" y="112" width="24" height="4" rx="1" fill={stroke} className="cyto-anim__slide-tray" />
      </g>
    </ClickableGroup>
  );
}
