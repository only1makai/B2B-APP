import Link from 'next/link';
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import { signPaths } from '@/lib/photos';
import type { Photo, Session, PhotoAngle } from '@/lib/types';
import { CompareViewer, type CompareSession } from './CompareViewer';

export const dynamic = 'force-dynamic';

export default async function ComparePage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect('/login');

  const [{ data: sessions }, { data: photos }] = await Promise.all([
    supabase.from('sessions').select('*').order('captured_at', { ascending: true }),
    supabase.from('photos').select('*'),
  ]);

  const sessionRows = (sessions ?? []) as Session[];
  const photoRows = (photos ?? []) as Photo[];

  const signed = await signPaths(
    supabase,
    photoRows.map((p) => p.storage_path),
  );

  const bySession = new Map<string, Partial<Record<PhotoAngle, string>>>();
  for (const p of photoRows) {
    const url = signed[p.storage_path];
    if (!url) continue;
    const entry = bySession.get(p.session_id) ?? {};
    entry[p.angle] = url;
    bySession.set(p.session_id, entry);
  }

  const compareSessions: CompareSession[] = sessionRows.map((s) => ({
    id: s.id,
    capturedAt: s.captured_at,
    photos: bySession.get(s.id) ?? {},
  }));

  if (compareSessions.length < 2) {
    return (
      <main className="space-y-4">
        <h1 className="text-2xl font-semibold tracking-tight">Compare</h1>
        <div className="card text-center text-sm text-mute">
          You need at least two sessions to compare.{' '}
          <Link href="/capture" className="text-accent">
            Capture another →
          </Link>
        </div>
      </main>
    );
  }

  return <CompareViewer sessions={compareSessions} />;
}
