'use server';

import { revalidatePath } from 'next/cache';
import { createClient } from '@/lib/supabase/server';
import type { PhotoAngle } from '@/lib/types';

export interface CapturedPhoto {
  angle: PhotoAngle;
  storage_path: string;
  width: number;
  height: number;
}

export interface SaveSessionInput {
  sessionId: string;
  capturedAt: string;
  lightingScore: number | null;
  notes: string | null;
  photos: CapturedPhoto[];
}

export interface SaveSessionResult {
  ok: boolean;
  error?: string;
}

// Persists a capture session and its photos. The blobs have already been
// uploaded to Storage client-side (RLS-locked); here we only write the rows.
// If the row writes fail, we best-effort clean up the orphaned objects.
export async function saveSession(
  input: SaveSessionInput,
): Promise<SaveSessionResult> {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return { ok: false, error: 'Not signed in.' };

  if (input.photos.length === 0) {
    return { ok: false, error: 'Capture at least one angle before saving.' };
  }

  const { error: sessionErr } = await supabase.from('sessions').insert({
    id: input.sessionId,
    user_id: user.id,
    captured_at: input.capturedAt,
    lighting_score: input.lightingScore,
    notes: input.notes,
  });

  if (sessionErr) {
    await cleanupObjects(supabase, input.photos.map((p) => p.storage_path));
    return { ok: false, error: sessionErr.message };
  }

  const { error: photoErr } = await supabase.from('photos').insert(
    input.photos.map((p) => ({
      session_id: input.sessionId,
      user_id: user.id,
      angle: p.angle,
      storage_path: p.storage_path,
      width: p.width,
      height: p.height,
    })),
  );

  if (photoErr) {
    // Roll back: remove the session row (cascade drops any photo rows) and
    // the uploaded objects.
    await supabase.from('sessions').delete().eq('id', input.sessionId);
    await cleanupObjects(supabase, input.photos.map((p) => p.storage_path));
    return { ok: false, error: photoErr.message };
  }

  revalidatePath('/');
  revalidatePath('/compare');
  return { ok: true };
}

async function cleanupObjects(
  supabase: Awaited<ReturnType<typeof createClient>>,
  paths: string[],
) {
  if (paths.length) {
    await supabase.storage.from('photos').remove(paths);
  }
}
