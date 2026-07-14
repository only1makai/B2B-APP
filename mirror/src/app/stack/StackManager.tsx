'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { prettyDate, daysBetween } from '@/lib/date';
import type { StackItem, StackSchedule } from '@/lib/types';
import { addStackItem, endStackItem, deleteStackItem } from './actions';

// Skincare has a ~6-12 week signal delay. Below this, the app refuses to
// pretend a product has "worked" yet.
const SIGNAL_WEEKS = 6;

export function StackManager({
  items,
  today,
}: {
  items: StackItem[];
  today: string;
}) {
  const router = useRouter();
  const [name, setName] = useState('');
  const [category, setCategory] = useState('');
  const [schedule, setSchedule] = useState<StackSchedule>('both');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const active = items.filter((i) => !i.ended_at || i.ended_at >= today);
  const past = items.filter((i) => i.ended_at && i.ended_at < today);

  async function onAdd() {
    if (!name.trim()) return;
    setBusy(true);
    setError(null);
    const res = await addStackItem({
      productName: name,
      category: category || null,
      schedule,
      startedAt: today,
    });
    setBusy(false);
    if (res.ok) {
      setName('');
      setCategory('');
      router.refresh();
    } else {
      setError(res.error ?? 'Could not add.');
    }
  }

  async function onEnd(id: string) {
    await endStackItem(id, today);
    router.refresh();
  }
  async function onDelete(id: string) {
    await deleteStackItem(id);
    router.refresh();
  }

  return (
    <main className="space-y-5">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Stack</h1>
        <p className="text-sm text-mute">Your active products, with start dates.</p>
      </header>

      {active.length > 0 && (
        <p className="rounded-xl bg-panel px-3 py-2 text-[11px] text-mute">
          Adding a product mid-experiment confounds the variable — you won&apos;t
          know which one did what. Change one thing at a time.
        </p>
      )}

      <section className="card space-y-3">
        <span className="label !normal-case">Add a product</span>
        <input
          className="input"
          placeholder="Product name (e.g. Adapalene 0.1%)"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <div className="grid grid-cols-2 gap-3">
          <input
            className="input"
            placeholder="Category (optional)"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          />
          <select
            className="input"
            value={schedule}
            onChange={(e) => setSchedule(e.target.value as StackSchedule)}
          >
            <option value="am">AM</option>
            <option value="pm">PM</option>
            <option value="both">AM + PM</option>
          </select>
        </div>
        {error && <p className="text-xs text-red-400">{error}</p>}
        <button className="btn-primary w-full" onClick={onAdd} disabled={busy}>
          {busy ? 'Adding…' : 'Add to stack'}
        </button>
      </section>

      <section className="space-y-2">
        <h2 className="text-sm font-medium">Active</h2>
        {active.length === 0 ? (
          <p className="text-sm text-mute">Nothing active yet.</p>
        ) : (
          active.map((it) => {
            const weeks = Math.floor(daysBetween(it.started_at, today) / 7);
            const mature = weeks >= SIGNAL_WEEKS;
            return (
              <div key={it.id} className="card flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">{it.product_name}</p>
                  <p className="text-[11px] text-mute">
                    {it.category ? `${it.category} · ` : ''}
                    {it.schedule.toUpperCase()} · started {prettyDate(it.started_at)}
                  </p>
                  <p
                    className={`text-[11px] ${mature ? 'text-accent' : 'text-mute'}`}
                  >
                    {weeks}w in ·{' '}
                    {mature
                      ? 'past the ~6w signal delay'
                      : `too early to read (needs ~${SIGNAL_WEEKS}w)`}
                  </p>
                </div>
                <button
                  className="btn-ghost text-xs"
                  onClick={() => onEnd(it.id)}
                >
                  End
                </button>
              </div>
            );
          })
        )}
      </section>

      {past.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-sm font-medium text-mute">Past</h2>
          {past.map((it) => (
            <div
              key={it.id}
              className="card flex items-center justify-between opacity-70"
            >
              <div>
                <p className="text-sm">{it.product_name}</p>
                <p className="text-[11px] text-mute">
                  {prettyDate(it.started_at)} → {prettyDate(it.ended_at!)}
                </p>
              </div>
              <button
                className="text-xs text-red-400"
                onClick={() => onDelete(it.id)}
              >
                Delete
              </button>
            </div>
          ))}
        </section>
      )}
    </main>
  );
}
