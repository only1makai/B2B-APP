'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { prettyDate } from '@/lib/date';
import type { Log, StackItem, LogAdherence, BreakoutZone } from '@/lib/types';
import { saveLog } from './actions';

const SCORE_LABELS = ['None', 'Mild', 'Moderate', 'Severe'];

export function LogForm({
  date,
  existing,
  stackItems,
  adherence,
}: {
  date: string;
  existing: Log | null;
  stackItems: StackItem[];
  adherence: LogAdherence[];
}) {
  const router = useRouter();
  const [shineTzone, setShineTzone] = useState<number | null>(existing?.shine_tzone ?? null);
  const [shineCheeks, setShineCheeks] = useState<number | null>(existing?.shine_cheeks ?? null);
  const [dryness, setDryness] = useState<number | null>(existing?.dryness ?? null);
  const [irritation, setIrritation] = useState<boolean>(existing?.irritation ?? false);
  const [sleep, setSleep] = useState<string>(
    existing?.sleep_hours != null ? String(existing.sleep_hours) : '',
  );
  const [note, setNote] = useState<string>(existing?.note ?? '');
  const [zones, setZones] = useState<BreakoutZone[]>(existing?.breakout_zones ?? []);
  const [taken, setTaken] = useState<Record<string, boolean>>(() => {
    const m: Record<string, boolean> = {};
    for (const a of adherence) m[a.stack_item_id] = a.taken;
    return m;
  });
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);

  function addZone(z: BreakoutZone) {
    setZones((prev) => [...prev, z]);
  }
  function clearZones() {
    setZones([]);
  }

  async function onSave() {
    setStatus('saving');
    setError(null);
    const res = await saveLog({
      date,
      sleepHours: sleep.trim() === '' ? null : Number(sleep),
      note: note.trim() === '' ? null : note.trim(),
      shineTzone,
      shineCheeks,
      breakoutCount: zones.length > 0 ? zones.length : null,
      breakoutZones: zones,
      dryness,
      irritation,
      adherence: stackItems.map((s) => ({
        stackItemId: s.id,
        taken: !!taken[s.id],
      })),
    });
    if (res.ok) {
      setStatus('saved');
      router.refresh();
      setTimeout(() => setStatus('idle'), 1500);
    } else {
      setError(res.error ?? 'Could not save.');
      setStatus('error');
    }
  }

  return (
    <main className="space-y-5">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Daily log</h1>
        <p className="text-sm text-mute">{prettyDate(date)}</p>
      </header>

      <section className="card space-y-4">
        <Segmented
          label="Shine — T-zone"
          value={shineTzone}
          onChange={setShineTzone}
        />
        <Segmented
          label="Shine — cheeks"
          value={shineCheeks}
          onChange={setShineCheeks}
        />
        <Segmented label="Dryness" value={dryness} onChange={setDryness} />
        <label className="flex items-center justify-between">
          <span className="label !normal-case">Irritation / redness</span>
          <button
            type="button"
            onClick={() => setIrritation((v) => !v)}
            className={`h-6 w-11 rounded-full transition-colors ${
              irritation ? 'bg-accent' : 'bg-edge'
            }`}
          >
            <span
              className={`block h-5 w-5 translate-x-0.5 rounded-full bg-white transition-transform ${
                irritation ? 'translate-x-[22px]' : ''
              }`}
            />
          </button>
        </label>
      </section>

      <section className="card space-y-2">
        <div className="flex items-center justify-between">
          <span className="label !normal-case">Breakouts</span>
          <span className="text-xs text-mute">
            {zones.length} tapped
            {zones.length > 0 && (
              <button className="ml-2 text-accent" onClick={clearZones}>
                clear
              </button>
            )}
          </span>
        </div>
        <FaceMap zones={zones} onAdd={addZone} />
        <p className="text-center text-[11px] text-mute">
          Tap where breakouts are. Count is inferred from taps.
        </p>
      </section>

      <section className="card grid grid-cols-2 gap-4">
        <label className="space-y-1">
          <span className="label">Sleep (hours)</span>
          <input
            type="number"
            inputMode="decimal"
            step="0.5"
            min="0"
            max="24"
            className="input"
            placeholder="7.5"
            value={sleep}
            onChange={(e) => setSleep(e.target.value)}
          />
        </label>
        <label className="space-y-1">
          <span className="label">Note</span>
          <input
            type="text"
            className="input"
            placeholder="optional"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </label>
      </section>

      {stackItems.length > 0 && (
        <section className="card space-y-2">
          <span className="label !normal-case">Routine adherence</span>
          <ul className="space-y-1">
            {stackItems.map((s) => (
              <li key={s.id}>
                <label className="flex cursor-pointer items-center gap-3 py-1.5">
                  <input
                    type="checkbox"
                    className="h-5 w-5 accent-accent"
                    checked={!!taken[s.id]}
                    onChange={(e) =>
                      setTaken((prev) => ({ ...prev, [s.id]: e.target.checked }))
                    }
                  />
                  <span className="text-sm">{s.product_name}</span>
                  <span className="ml-auto text-[10px] uppercase text-mute">
                    {s.schedule}
                  </span>
                </label>
              </li>
            ))}
          </ul>
        </section>
      )}

      {error && <p className="text-xs text-red-400">{error}</p>}

      <button
        className="btn-primary w-full"
        onClick={onSave}
        disabled={status === 'saving'}
      >
        {status === 'saving'
          ? 'Saving…'
          : status === 'saved'
            ? 'Saved ✓'
            : existing
              ? 'Update log'
              : 'Save log'}
      </button>
    </main>
  );
}

function Segmented({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number | null;
  onChange: (n: number) => void;
}) {
  return (
    <div>
      <span className="label !normal-case mb-1 block">{label}</span>
      <div className="flex gap-1.5">
        {SCORE_LABELS.map((lbl, i) => (
          <button
            key={i}
            type="button"
            onClick={() => onChange(i)}
            className={`flex-1 rounded-lg border px-2 py-2 text-xs ${
              value === i
                ? 'border-accent bg-accent/10 text-accent'
                : 'border-edge text-mute'
            }`}
          >
            {lbl}
          </button>
        ))}
      </div>
    </div>
  );
}

function FaceMap({
  zones,
  onAdd,
}: {
  zones: BreakoutZone[];
  onAdd: (z: BreakoutZone) => void;
}) {
  function handleClick(e: React.MouseEvent<HTMLDivElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    onAdd({ x: Math.min(1, Math.max(0, x)), y: Math.min(1, Math.max(0, y)) });
  }

  return (
    <div
      onClick={handleClick}
      className="relative mx-auto aspect-[3/4] w-40 cursor-crosshair rounded-xl border border-edge bg-ink"
    >
      {/* Simple face outline */}
      <svg viewBox="0 0 120 160" className="h-full w-full">
        <ellipse
          cx="60"
          cy="72"
          rx="42"
          ry="54"
          fill="none"
          stroke="#262b33"
          strokeWidth="2"
        />
        <line x1="60" y1="20" x2="60" y2="124" stroke="#1c2026" strokeWidth="1" />
        <ellipse cx="44" cy="60" rx="6" ry="4" fill="none" stroke="#262b33" strokeWidth="1.5" />
        <ellipse cx="76" cy="60" rx="6" ry="4" fill="none" stroke="#262b33" strokeWidth="1.5" />
      </svg>
      {zones.map((z, i) => (
        <span
          key={i}
          className="absolute h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-red-400"
          style={{ left: `${z.x * 100}%`, top: `${z.y * 100}%` }}
        />
      ))}
    </div>
  );
}
