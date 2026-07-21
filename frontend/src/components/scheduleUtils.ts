export type ScheduleSlot = {
  days: number[];
  hours: [number, number];
};

export type ScheduleDict = Record<string, ScheduleSlot>;

export const WEEKDAY_LABELS = [
  { value: 0, short: 'Mon', label: 'Monday' },
  { value: 1, short: 'Tue', label: 'Tuesday' },
  { value: 2, short: 'Wed', label: 'Wednesday' },
  { value: 3, short: 'Thu', label: 'Thursday' },
  { value: 4, short: 'Fri', label: 'Friday' },
  { value: 5, short: 'Sat', label: 'Saturday' },
  { value: 6, short: 'Sun', label: 'Sunday' },
] as const;

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
}

function clampHour(value: unknown, fallback: number): number {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  return Math.min(23, Math.max(0, Math.round(n)));
}

export function readSchedule(value: unknown): ScheduleDict {
  const raw = asRecord(value);
  const next: ScheduleDict = {};
  for (const [key, slotValue] of Object.entries(raw)) {
    const slot = asRecord(slotValue);
    const daysRaw = Array.isArray(slot.days) ? slot.days : [];
    const days = daysRaw
      .map((d) => Number(d))
      .filter((d) => Number.isInteger(d) && d >= 0 && d <= 6)
      .sort((a, b) => a - b);
    const hoursRaw = Array.isArray(slot.hours) ? slot.hours : [9, 17];
    const start = clampHour(hoursRaw[0], 9);
    const end = clampHour(hoursRaw[1], Math.max(start + 1, 17));
    next[key] = { days, hours: [start, end] };
  }
  return next;
}

export function nextTimeslotName(existing: ScheduleDict): string {
  const used = new Set(Object.keys(existing));
  let n = 1;
  while (used.has(`Timeslot_${n}`)) n += 1;
  return `Timeslot_${n}`;
}

export function defaultSlot(): ScheduleSlot {
  return { days: [0, 1, 2, 3, 4], hours: [9, 17] };
}

export function formatScheduleSlot(slot: ScheduleSlot): string {
  const dayLabel =
    slot.days.length === 0
      ? 'no days'
      : slot.days.map((d) => WEEKDAY_LABELS[d]?.short ?? String(d)).join(', ');
  const [start, end] = slot.hours;
  return `${dayLabel} · ${start}:00–${end}:00`;
}

export function formatScheduleDict(schedule: unknown): string {
  const slots = Object.entries(readSchedule(schedule));
  if (slots.length === 0) return 'No timeslots';
  return slots.map(([name, slot]) => `${name}: ${formatScheduleSlot(slot)}`).join('; ');
}
