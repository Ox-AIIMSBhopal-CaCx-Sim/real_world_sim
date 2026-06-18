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
const hair = '#3d2914';
const coat = '#ffffff';
const shirtGreen = '#c8e6c9';
const shirtBlue = '#b8d4f0';
const liquid = '#d4e157';

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

export function HistoReceptionProfessional(props: Omit<CartoonProps, 'label' | 'ariaLabel'>) {
  return (
    <ClickableGroup {...props} label="Reception" ariaLabel="Reception staff — edit headcount and service times">
      <g className="cyto-anim cyto-anim--reception">
        <ellipse cx="80" cy="48" rx="22" ry="24" fill={skin} stroke={stroke} strokeWidth="2.5" />
        <path d="M58 42 Q80 28 102 42" fill={hair} stroke={stroke} strokeWidth="2" />
        <circle cx="72" cy="48" r="2.5" fill={stroke} />
        <circle cx="88" cy="48" r="2.5" fill={stroke} />
        <path d="M74 58 Q80 62 86 58" fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" />
        <rect x="48" y="70" width="64" height="70" rx="6" fill={coat} stroke={stroke} strokeWidth="2.5" />
        <rect x="58" y="78" width="44" height="18" rx="3" fill={shirtGreen} stroke={stroke} strokeWidth="2" />
        <rect x="38" y="108" width="84" height="12" rx="2" fill="#d1d5db" stroke={stroke} strokeWidth="2" />
        <g className="cyto-anim__typing-hand">
          <rect x="108" y="92" width="28" height="22" rx="3" fill="#fef3c7" stroke={stroke} strokeWidth="2" />
          <rect x="112" y="98" width="20" height="4" rx="1" fill={stroke} opacity="0.4" />
        </g>
        <rect x="20" y="118" width="28" height="36" rx="4" fill="#e0e7ff" stroke={stroke} strokeWidth="2" />
        <rect x="24" y="124" width="20" height="20" rx="2" fill={liquid} opacity="0.7" />
        <text x="34" y="138" textAnchor="middle" fontSize="7" fill={stroke} fontWeight="700">
          BX
        </text>
      </g>
    </ClickableGroup>
  );
}

export function HistoReceptionEquipment(props: Omit<CartoonProps, 'label' | 'ariaLabel'>) {
  return (
    <ClickableGroup
      {...props}
      label="Accession system"
      ariaLabel="Biopsy accession equipment — edit arrival rates and biopsy size settings"
    >
      <g className="cyto-anim cyto-anim--equipment">
        <rect x="20" y="40" width="120" height="80" rx="8" fill="#e5e7eb" stroke={stroke} strokeWidth="2.5" />
        <rect x="30" y="50" width="100" height="56" rx="4" fill="#374151" stroke={stroke} strokeWidth="2" />
        <rect x="38" y="58" width="84" height="40" fill="#86efac" />
        <rect x="46" y="66" width="40" height="6" rx="2" fill="#ffffff" opacity="0.8" />
        <rect x="46" y="78" width="60" height="6" rx="2" fill="#ffffff" opacity="0.6" />
        <rect x="24" y="128" width="112" height="28" rx="6" fill="#f1f5f9" stroke={stroke} strokeWidth="2.5" />
        <rect x="32" y="134" width="14" height="16" rx="2" fill="#fca5a5" stroke={stroke} strokeWidth="1.5" />
        <rect x="52" y="134" width="14" height="16" rx="2" fill="#fdba74" stroke={stroke} strokeWidth="1.5" />
        <rect x="72" y="134" width="14" height="16" rx="2" fill="#fcd34d" stroke={stroke} strokeWidth="1.5" />
        <rect x="92" y="134" width="14" height="16" rx="2" fill="#86efac" stroke={stroke} strokeWidth="1.5" className="cyto-anim__sample-blink" />
        <rect x="112" y="134" width="14" height="16" rx="2" fill="#93c5fd" stroke={stroke} strokeWidth="1.5" />
      </g>
    </ClickableGroup>
  );
}

export function HistoProcessingProfessional(props: Omit<CartoonProps, 'label' | 'ariaLabel'>) {
  return (
    <ClickableGroup {...props} label="Lab staff" ariaLabel="Histotechnicians and residents — edit headcount and service times">
      <g className="cyto-anim cyto-anim--processing">
        <ellipse cx="80" cy="46" rx="22" ry="24" fill={skin} stroke={stroke} strokeWidth="2.5" />
        <path d="M58 40 Q80 24 102 40" fill={hair} stroke={stroke} strokeWidth="2" />
        <circle cx="72" cy="46" r="2.5" fill={stroke} />
        <circle cx="88" cy="46" r="2.5" fill={stroke} />
        <rect x="56" y="52" width="48" height="14" rx="7" fill="none" stroke={stroke} strokeWidth="2.5" opacity="0.85" />
        <rect x="48" y="68" width="64" height="72" rx="6" fill={coat} stroke={stroke} strokeWidth="2.5" />
        <rect x="58" y="76" width="44" height="18" rx="3" fill={shirtGreen} stroke={stroke} strokeWidth="2" />
        <g className="cyto-anim__writing-hand">
          <rect x="22" y="108" width="40" height="24" rx="3" fill="#fef9c3" stroke={stroke} strokeWidth="2" />
          <rect x="28" y="114" width="12" height="12" rx="1" fill="#78716c" stroke={stroke} strokeWidth="1.5" />
          <line x1="44" y1="116" x2="56" y2="116" stroke={stroke} strokeWidth="1.5" />
          <line x1="44" y1="122" x2="52" y2="122" stroke={stroke} strokeWidth="1.5" />
        </g>
        <g className="cyto-anim__pipette">
          <rect x="108" y="100" width="24" height="8" rx="2" fill="#94a3b8" stroke={stroke} strokeWidth="2" />
          <rect x="112" y="88" width="16" height="14" rx="2" fill="#e2e8f0" stroke={stroke} strokeWidth="2" />
          <line x1="120" y1="108" x2="120" y2="128" stroke={stroke} strokeWidth="2.5" strokeLinecap="round" />
        </g>
        <ellipse cx="120" cy="132" rx="4" ry="6" fill={liquid} className="cyto-anim__drop" opacity="0.8" />
      </g>
    </ClickableGroup>
  );
}

export function HistoProcessingEquipment(props: Omit<CartoonProps, 'label' | 'ariaLabel'>) {
  return (
    <ClickableGroup
      {...props}
      label="Processing line"
      ariaLabel="Histology processing equipment — edit stations, batch sizes, and error rates"
    >
      <g className="cyto-anim cyto-anim--equipment">
        <rect x="16" y="56" width="128" height="96" rx="10" fill="#f1f5f9" stroke={stroke} strokeWidth="2.5" />
        <rect x="24" y="64" width="52" height="72" rx="6" fill="#cbd5e1" stroke={stroke} strokeWidth="2" />
        <g className="cyto-anim__centrifuge">
          <circle cx="50" cy="100" r="22" fill="#ffffff" stroke={stroke} strokeWidth="2" />
          <circle cx="50" cy="100" r="14" fill="none" stroke={stroke} strokeWidth="2" strokeDasharray="5 3" />
          <rect x="44" y="94" width="12" height="12" rx="1" fill="#78716c" stroke={stroke} strokeWidth="1.5" />
        </g>
        <rect x="84" y="72" width="52" height="28" rx="4" fill="#e2e8f0" stroke={stroke} strokeWidth="2" />
        <rect x="90" y="78" width="10" height="16" rx="1" fill="#78716c" stroke={stroke} strokeWidth="1" />
        <rect x="104" y="78" width="10" height="16" rx="1" fill="#78716c" stroke={stroke} strokeWidth="1" />
        <rect x="118" y="78" width="10" height="16" rx="1" fill="#78716c" stroke={stroke} strokeWidth="1" />
        <rect x="84" y="108" width="52" height="28" rx="4" fill="#fef3c7" stroke={stroke} strokeWidth="2" />
        <rect x="90" y="114" width="40" height="4" rx="1" fill="#dc2626" className="cyto-anim__slide-tray" />
        <rect x="90" y="122" width="40" height="4" rx="1" fill="#2563eb" />
        <rect x="32" y="140" width="96" height="14" rx="3" fill="#64748b" stroke={stroke} strokeWidth="2" />
        <circle cx="44" cy="147" r="3" fill="#22c55e" className="cyto-anim__status-light" />
        <text x="80" y="150" textAnchor="middle" fontSize="7" fill="#ffffff" fontWeight="600">
          HISTO LINE
        </text>
      </g>
    </ClickableGroup>
  );
}

export function HistoReportingProfessional(props: Omit<CartoonProps, 'label' | 'ariaLabel'>) {
  return (
    <ClickableGroup {...props} label="Reporting" ariaLabel="Histopathologist — edit headcount and service times">
      <g className="cyto-anim cyto-anim--reporting">
        <ellipse cx="80" cy="46" rx="22" ry="24" fill={skin} stroke={stroke} strokeWidth="2.5" />
        <path d="M58 38 Q80 22 102 38" fill={hair} stroke={stroke} strokeWidth="2" />
        <circle cx="72" cy="46" r="2.5" fill={stroke} />
        <circle cx="88" cy="46" r="2.5" fill={stroke} />
        <rect x="62" y="54" width="36" height="8" rx="2" fill="none" stroke={stroke} strokeWidth="2" />
        <rect x="48" y="68" width="64" height="72" rx="6" fill={coat} stroke={stroke} strokeWidth="2.5" />
        <rect x="58" y="76" width="44" height="18" rx="3" fill={shirtBlue} stroke={stroke} strokeWidth="2" />
        <g className="cyto-anim__microscope-head">
          <rect x="18" y="108" width="58" height="8" rx="2" fill="#94a3b8" stroke={stroke} strokeWidth="2" />
          <rect x="34" y="86" width="26" height="24" rx="4" fill="#64748b" stroke={stroke} strokeWidth="2" />
          <circle cx="47" cy="98" r="7" fill="#bae6fd" stroke={stroke} strokeWidth="2" />
        </g>
        <g className="cyto-anim__writing-hand">
          <rect x="106" y="98" width="38" height="32" rx="3" fill="#fef9c3" stroke={stroke} strokeWidth="2" />
          <line x1="112" y1="108" x2="138" y2="108" stroke={stroke} strokeWidth="1.5" />
          <line x1="112" y1="116" x2="130" y2="116" stroke={stroke} strokeWidth="1.5" />
          <line x1="112" y1="124" x2="134" y2="124" stroke={stroke} strokeWidth="1.5" />
        </g>
      </g>
    </ClickableGroup>
  );
}

export function HistoReportingEquipment(props: Omit<CartoonProps, 'label' | 'ariaLabel'>) {
  return (
    <ClickableGroup
      {...props}
      label="Microscope bench"
      ariaLabel="Reporting microscope bench — edit stations, batch size, and error rate"
    >
      <g className="cyto-anim cyto-anim--equipment">
        <rect x="12" y="132" width="136" height="18" rx="4" fill="#78716c" stroke={stroke} strokeWidth="2.5" />
        <rect x="36" y="68" width="14" height="64" fill="#57534e" stroke={stroke} strokeWidth="2" />
        <rect x="88" y="68" width="14" height="64" fill="#57534e" stroke={stroke} strokeWidth="2" />
        <g className="cyto-anim__scope-lens">
          <circle cx="43" cy="58" r="16" fill="#bae6fd" stroke={stroke} strokeWidth="2.5" />
          <circle cx="43" cy="58" r="7" fill="#0ea5e9" opacity="0.5" />
        </g>
        <g className="cyto-anim__microscope-head">
          <circle cx="95" cy="58" r="16" fill="#bae6fd" stroke={stroke} strokeWidth="2.5" />
          <circle cx="95" cy="58" r="7" fill="#0ea5e9" opacity="0.5" />
        </g>
        <rect x="108" y="92" width="36" height="28" rx="4" fill="#fef9c3" stroke={stroke} strokeWidth="2" />
        <line x1="114" y1="102" x2="138" y2="102" stroke={stroke} strokeWidth="1.5" />
        <line x1="114" y1="110" x2="132" y2="110" stroke={stroke} strokeWidth="1.5" />
        <text x="72" y="148" textAnchor="middle" fontSize="7" fill="#ffffff" fontWeight="600">
          MULTI-HEAD
        </text>
      </g>
    </ClickableGroup>
  );
}
