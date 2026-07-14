import Link from 'next/link';
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import { signOut } from '@/app/auth/actions';
import { signPaths } from '@/lib/photos';
import { prettyDate, localDateString, daysBetween } from '@/lib/date';
import type { Photo, Session, Log } from '@/lib/types';
import { GhostThumb } from '@/components/GhostThumb';

export const dynamic = 'force-dynamic';

export default async function HomePage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect('/login');

  const [{ data: sessions }, { data: photos }, { data: todayLog }] = await Promise.all([
    supabase
      .from('sessions')
      .select('*')
      .order('captured_at', { ascending: false })
      .limit(3),
    supabase
      .from('photos')
      .select('*')
      .eq('angle', 'front')
      .order('created_at', { ascending: false })
      .limit(3),
    supabase
      .from('logs')
      .select('*')
      .eq('date', localDateString())
      .maybeSingle(),
  ]);

  const sessionList = (sessions ?? []) as Session[];
  const frontPhotos = (photos ?? []) as Photo[];
  const signed = await signPaths(
    supabase,
    frontPhotos.map((p) => p.storage_path),
  );

  const latest = sessionList[0];
  const oldest = sessionList[sessionList.length - 1];
  const span =
    latest && oldest && latest.id !== oldest.id
      ? daysBetween(oldest.captured_at, latest.captured_at)
      : 0;

  const loggedToday = !!(todayLog as Log | null);

  return (
    <main className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Mirror</h1>
          <p className="text-sm text-mute">{user.email}</p>
        </div>
        <form action={signOut}>
          <button className="btn-ghost text-xs" type="submit">
            Sign out
          </button>
        </form>
      </header>

      <section className="grid grid-cols-2 gap-3">
        <Link href="/capture" className="card flex flex-col gap-1 hover:bg-edge">
          <span className="text-lg">⊙ Capture</span>
          <span className="text-xs text-mute">New three-angle session</span>
        </Link>
        <Link
          href="/log"
          className="card flex flex-col gap-1 hover:bg-edge"
        >
          <span className="text-lg">✎ Log</span>
          <span className="text-xs text-mute">
            {loggedToday ? 'Logged today ✓' : 'Not logged today'}
          </span>
        </Link>
      </section>

      <section className="card">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-medium">Recent sessions</h2>
          {sessionList.length >= 2 && (
            <Link href="/compare" className="text-xs text-accent">
              Compare →
            </Link>
          )}
        </div>

        {sessionList.length === 0 ? (
          <div className="py-8 text-center text-sm text-mute">
            No sessions yet.{' '}
            <Link href="/capture" className="text-accent">
              Capture your first
            </Link>{' '}
            to start the baseline.
          </div>
        ) : (
          <>
            {span > 0 && (
              <p className="mb-3 text-xs text-mute">
                {span} days between your oldest and newest session here.
              </p>
            )}
            <ul className="flex gap-3 overflow-x-auto">
              {frontPhotos.map((p) => (
                <li key={p.id} className="shrink-0 text-center">
                  <GhostThumb
                    src={signed[p.storage_path]}
                    className="h-28 w-20 rounded-lg border border-edge object-cover"
                  />
                  <span className="mt-1 block text-[10px] text-mute">
                    {prettyDate(p.created_at)}
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      <p className="px-1 text-center text-[11px] leading-relaxed text-mute">
        Mirror tracks the things that move — skin, hair, sleep. No score, no
        rating. Bone structure doesn&apos;t change, so we don&apos;t pretend to
        measure it.
      </p>
    </main>
  );
}
