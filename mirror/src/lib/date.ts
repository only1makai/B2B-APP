// Local-calendar-day helpers. Logs are keyed by the user's local day, not UTC,
// so a late-night entry lands on the right date.

export function localDateString(d: Date = new Date()): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export function prettyDate(iso: string): string {
  // iso is either a YYYY-MM-DD date or a full timestamp.
  const d = iso.length <= 10 ? new Date(`${iso}T00:00:00`) : new Date(iso);
  return d.toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function daysBetween(a: string, b: string): number {
  const da = new Date(a.length <= 10 ? `${a}T00:00:00` : a).getTime();
  const db = new Date(b.length <= 10 ? `${b}T00:00:00` : b).getTime();
  return Math.round((db - da) / (1000 * 60 * 60 * 24));
}
