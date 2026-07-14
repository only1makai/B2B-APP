import type { SupabaseClient } from '@supabase/supabase-js';
import type { PhotoAngle } from './types';

export const PHOTO_BUCKET = 'photos';

// Short signed-URL lifetime. Photos are sensitive; keep the window tight.
export const SIGNED_URL_TTL_SECONDS = 60 * 10; // 10 minutes

// Canonical object key. The FIRST path segment MUST be the user id — the
// storage RLS policy keys ownership off it.
export function photoPath(userId: string, sessionId: string, angle: PhotoAngle) {
  return `${userId}/${sessionId}/${angle}.jpg`;
}

// Batch-sign a set of storage paths. Returns a map path -> signed URL.
// Paths that fail to sign are simply omitted.
export async function signPaths(
  supabase: SupabaseClient,
  paths: string[],
): Promise<Record<string, string>> {
  const unique = Array.from(new Set(paths)).filter(Boolean);
  if (unique.length === 0) return {};

  const { data, error } = await supabase.storage
    .from(PHOTO_BUCKET)
    .createSignedUrls(unique, SIGNED_URL_TTL_SECONDS);

  if (error || !data) return {};

  const out: Record<string, string> = {};
  for (const row of data) {
    if (row.signedUrl && row.path) out[row.path] = row.signedUrl;
  }
  return out;
}
