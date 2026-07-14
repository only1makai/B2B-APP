'use client';

import { createBrowserClient } from '@supabase/ssr';

// Browser-side Supabase client. Safe to call in client components; it reads
// the public anon key and manages the session cookie via @supabase/ssr.
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
}
