import { useEffect, useMemo, useState } from 'react';
import type { DisruptionConfig, ParametersDict, SimulationKind } from '../types/simulation';
import {
  getDisruptionPresets,
  getDisruptionResources,
  readDisruptions,
  toApiDisruption,
  type DisruptionPreset,
  type DisruptionResourceOption,
} from './disruptionPresets';

interface DisruptionsPanelProps {
  kind: SimulationKind;
  parameters: ParametersDict;
  onChange: (path: string[], value: unknown) => void;
}

function NumberField({
  label,
  value,
  onChange,
  step = 1,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        type="number"
        step={step}
        value={Number.isFinite(value) ? value : 0}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </label>
  );
}

function TextField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input type="text" value={value} onChange={(e) => onChange(e.target.value)} />
    </label>
  );
}

function SelectField({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: DisruptionResourceOption[];
  onChange: (v: string) => void;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function nextCustomId(existing: DisruptionConfig[]): string {
  const used = new Set(existing.map((d) => d.id));
  let n = 1;
  while (used.has(`custom_disruption_${n}`)) n += 1;
  return `custom_disruption_${n}`;
}

function blankCustomDisruption(
  resources: DisruptionResourceOption[],
  existing: DisruptionConfig[],
): DisruptionConfig {
  return {
    id: nextCustomId(existing),
    resource: resources[0]?.value ?? '',
    start_day: 0,
    start_datetime: null,
    duration_days: 7,
    effective_capacity: 0,
  };
}

export function DisruptionsPanel({ kind, parameters, onChange }: DisruptionsPanelProps) {
  const presets = useMemo(() => getDisruptionPresets(kind), [kind]);
  const resources = useMemo(() => getDisruptionResources(kind), [kind]);
  const presetIds = useMemo(() => new Set(presets.map((p) => p.defaults.id)), [presets]);
  const active = readDisruptions(parameters.disruptions);
  const customDisruptions = active.filter((d) => !presetIds.has(d.id));

  const [composerOpen, setComposerOpen] = useState(false);
  const [draft, setDraft] = useState<DisruptionConfig>(() =>
    blankCustomDisruption(resources, active),
  );

  useEffect(() => {
    setComposerOpen(false);
    setDraft(blankCustomDisruption(getDisruptionResources(kind), readDisruptions(parameters.disruptions)));
  }, [kind]);

  const writeDisruptions = (next: DisruptionConfig[]) => {
    onChange(
      ['disruptions'],
      next.map((d) => toApiDisruption(d)),
    );
  };

  const findActive = (preset: DisruptionPreset) =>
    active.find((d) => d.id === preset.defaults.id) ?? null;

  const togglePreset = (preset: DisruptionPreset, enabled: boolean) => {
    if (enabled) {
      if (findActive(preset)) return;
      writeDisruptions([...active, { ...preset.defaults }]);
      return;
    }
    writeDisruptions(active.filter((d) => d.id !== preset.defaults.id));
  };

  const updateActive = (id: string, patch: Partial<DisruptionConfig>) => {
    writeDisruptions(
      active.map((d) => {
        if (d.id !== id) return d;
        const next = { ...d, ...patch };
        if ('start_day' in patch && patch.start_day != null) {
          next.start_datetime = null;
        }
        if ('start_datetime' in patch && patch.start_datetime) {
          next.start_day = null;
        }
        return next;
      }),
    );
  };

  const removeDisruption = (id: string) => {
    writeDisruptions(active.filter((d) => d.id !== id));
  };

  const openComposer = () => {
    setDraft(blankCustomDisruption(resources, active));
    setComposerOpen(true);
  };

  const addCustomDisruption = () => {
    const id = draft.id.trim() || nextCustomId(active);
    if (active.some((d) => d.id === id)) {
      return;
    }
    const resource =
      draft.resource && resources.some((r) => r.value === draft.resource)
        ? draft.resource
        : (resources[0]?.value ?? '');

    writeDisruptions([
      ...active,
      {
        id,
        resource,
        start_day: draft.start_day ?? 0,
        start_datetime: null,
        duration_days: Math.max(0.01, Number(draft.duration_days) || 1),
        effective_capacity: Math.max(0, Number(draft.effective_capacity) || 0),
      },
    ]);
    setComposerOpen(false);
    setDraft(blankCustomDisruption(resources, [...active, { id } as DisruptionConfig]));
  };

  return (
    <aside className="side-card disruptions-panel">
      <div className="side-card__header">
        <h3>Disruptions</h3>
        <p className="muted">Add ready-made capacity shocks or define your own.</p>
      </div>

      <div className="disruption-list">
        {presets.map((preset) => {
          const current = findActive(preset);
          const enabled = current != null;
          return (
            <article
              key={preset.key}
              className={`disruption-card${enabled ? ' disruption-card--active' : ''}`}
            >
              <label className="disruption-card__toggle">
                <input
                  type="checkbox"
                  checked={enabled}
                  onChange={(e) => togglePreset(preset, e.target.checked)}
                />
                <span>
                  <strong>{preset.title}</strong>
                  <span className="muted disruption-card__desc">{preset.description}</span>
                </span>
              </label>

              {enabled && current ? (
                <DisruptionFields
                  value={current}
                  resources={resources}
                  onChange={(patch) => updateActive(current.id, patch)}
                  idEditable={false}
                />
              ) : null}
            </article>
          );
        })}

        {customDisruptions.map((current) => (
          <article key={current.id} className="disruption-card disruption-card--active">
            <div className="disruption-card__header-row">
              <strong>Custom disruption</strong>
              <button
                type="button"
                className="disruption-card__remove"
                onClick={() => removeDisruption(current.id)}
              >
                Remove
              </button>
            </div>
            <DisruptionFields
              value={current}
              resources={resources}
              onChange={(patch) => updateActive(current.id, patch)}
              idEditable
            />
          </article>
        ))}

        {composerOpen ? (
          <article className="disruption-card disruption-card--composer">
            <div className="disruption-card__header-row">
              <strong>New disruption</strong>
              <button
                type="button"
                className="disruption-card__remove"
                onClick={() => setComposerOpen(false)}
              >
                Cancel
              </button>
            </div>
            <DisruptionFields
              value={draft}
              resources={resources}
              onChange={(patch) => setDraft((prev) => ({ ...prev, ...patch }))}
              idEditable
            />
            <button type="button" className="disruption-card__add" onClick={addCustomDisruption}>
              Add disruption
            </button>
          </article>
        ) : (
          <button type="button" className="disruption-card__new" onClick={openComposer}>
            + New disruption
          </button>
        )}
      </div>
    </aside>
  );
}

function DisruptionFields({
  value,
  resources,
  onChange,
  idEditable,
}: {
  value: DisruptionConfig;
  resources: DisruptionResourceOption[];
  onChange: (patch: Partial<DisruptionConfig>) => void;
  idEditable: boolean;
}) {
  const resourceOptions =
    value.resource && !resources.some((r) => r.value === value.resource)
      ? [...resources, { value: value.resource, label: value.resource }]
      : resources;

  return (
    <div className="disruption-card__fields">
      {idEditable ? (
        <TextField label="id" value={value.id} onChange={(v) => onChange({ id: v })} />
      ) : (
        <div className="field">
          <span>id</span>
          <code className="disruption-card__id">{value.id}</code>
        </div>
      )}
      <SelectField
        label="resource"
        value={value.resource}
        options={resourceOptions}
        onChange={(v) => onChange({ resource: v })}
      />
      <NumberField
        label="start_day"
        value={Number(value.start_day ?? 0)}
        onChange={(v) => onChange({ start_day: v, start_datetime: null })}
      />
      <NumberField
        label="duration_days"
        value={Number(value.duration_days)}
        onChange={(v) => onChange({ duration_days: v })}
      />
      <NumberField
        label="effective_capacity"
        value={Number(value.effective_capacity)}
        onChange={(v) => onChange({ effective_capacity: v })}
      />
    </div>
  );
}
