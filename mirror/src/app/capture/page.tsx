import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import { signPaths } from '@/lib/photos';
import type { Photo, Session, PhotoAngle } from '@/lib/types';
import { CaptureStudio } from './CaptureStudio';

export const dynamic = 'force-dynamic';

export default async function CapturePage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect('/login');

  // Fetch the most recent session's photos to use as alignment ghosts.
  const { data: last } = await supabase
    .from('sessions')
    .select('*')
    .order('captured_at', { ascending: false })
    .limit(1)
    .maybeSingle();

  const lastSession = last as Session | null;

  let ghosts: Partial<Record<PhotoAngle, string>> = {};
  if (lastSession) {
    const { data: lastPhotos } = await supabase
      .from('photos')
      .select('*')
      .eq('session_id', lastSession.id);
    const photos = (lastPhotos ?? []) as Photo[];
    const signed = await signPaths(
      supabase,
      photos.map((p) => p.storage_path),
    );
    for (const p of photos) {
      const url = signed[p.storage_path];
      if (url) ghosts[p.angle] = url;
    }
  }

  return (
    <CaptureStudio
      userId={user.id}
      ghosts={ghosts}
      lastLighting={lastSession?.lighting_score ?? null}
    />
  );
}
