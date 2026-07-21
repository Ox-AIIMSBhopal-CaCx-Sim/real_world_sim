import {
  defaultSlot,
  nextTimeslotName,
  readSchedule,
  WEEKDAY_LABELS,
  type ScheduleDict,
  type ScheduleSlot,
} from './scheduleUtils';

interface ScheduleEditorProps {
  title?: string;
  description?: string;
  schedule: unknown;
  onChange: (next: ScheduleDict) => void;
}

function HourSelect({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <label className="field schedule-editor__hour">
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(Number(e.target.value))}>
        {Array.from({ length: 24 }, (_, hour) => (
          <option key={hour} value={hour}>
            {String(hour).padStart(2, '0')}:00
          </option>
        ))}
      </select>
    </label>
  );
}

function updateSlot(
  schedule: ScheduleDict,
  name: string,
  patch: Partial<ScheduleSlot>,
): ScheduleDict {
  const current = schedule[name] ?? defaultSlot();
  const nextSlot: ScheduleSlot = {
    days: patch.days ?? current.days,
    hours: patch.hours ?? current.hours,
  };
  const [start, end] = nextSlot.hours;
  if (end <= start) {
    nextSlot.hours = [start, Math.min(23, start + 1)];
  }
  return { ...schedule, [name]: nextSlot };
}

function toggleDay(days: number[], day: number): number[] {
  if (days.includes(day)) return days.filter((d) => d !== day).sort((a, b) => a - b);
  return [...days, day].sort((a, b) => a - b);
}

export function ScheduleEditor({
  title = 'Schedule',
  description = 'Define when this resource is on shift. Days use Monday = 0.',
  schedule,
  onChange,
}: ScheduleEditorProps) {
  const slots = readSchedule(schedule);
  const entries = Object.entries(slots);

  const addSlot = () => {
    const name = nextTimeslotName(slots);
    onChange({ ...slots, [name]: defaultSlot() });
  };

  const removeSlot = (name: string) => {
    const next = { ...slots };
    delete next[name];
    onChange(next);
  };

  return (
    <section className="schedule-editor">
      <div className="schedule-editor__header">
        <div>
          <h3>{title}</h3>
          <p className="muted">{description}</p>
        </div>
        <button type="button" className="schedule-editor__add" onClick={addSlot}>
          + Add timeslot
        </button>
      </div>

      {entries.length === 0 ? (
        <p className="muted schedule-editor__empty">
          No timeslots yet. Add one to define working hours.
        </p>
      ) : (
        <ul className="schedule-editor__list">
          {entries.map(([name, slot]) => (
            <li key={name} className="schedule-editor__card">
              <div className="schedule-editor__card-top">
                <strong>{name}</strong>
                <button
                  type="button"
                  className="text-button schedule-editor__remove"
                  onClick={() => removeSlot(name)}
                >
                  Remove
                </button>
              </div>

              <div className="schedule-editor__days" role="group" aria-label={`${name} days`}>
                {WEEKDAY_LABELS.map((day) => {
                  const active = slot.days.includes(day.value);
                  return (
                    <button
                      key={day.value}
                      type="button"
                      className={`schedule-editor__day${active ? ' active' : ''}`}
                      aria-pressed={active}
                      title={day.label}
                      onClick={() =>
                        onChange(
                          updateSlot(slots, name, {
                            days: toggleDay(slot.days, day.value),
                          }),
                        )
                      }
                    >
                      {day.short}
                    </button>
                  );
                })}
              </div>

              <div className="schedule-editor__hours">
                <HourSelect
                  label="Start"
                  value={slot.hours[0]}
                  onChange={(start) =>
                    onChange(
                      updateSlot(slots, name, {
                        hours: [start, slot.hours[1]],
                      }),
                    )
                  }
                />
                <HourSelect
                  label="End"
                  value={slot.hours[1]}
                  onChange={(end) =>
                    onChange(
                      updateSlot(slots, name, {
                        hours: [slot.hours[0], end],
                      }),
                    )
                  }
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
