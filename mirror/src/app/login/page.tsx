'use client';

import { Suspense, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';

function LoginForm() {
  const params = useSearchParams();
  const next = params.get('next') || '/';
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus('sending');
    setError(null);
    const supabase = createClient();
    const base =
      process.env.NEXT_PUBLIC_SITE_URL ||
      (typeof window !== 'undefined' ? window.location.origin : '');
    const redirect = `${base}/auth/callback?next=${encodeURIComponent(next)}`;

    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: redirect },
    });

    if (error) {
      setError(error.message);
      setStatus('error');
    } else {
      setStatus('sent');
    }
  }

  return (
    <main className="mx-auto mt-16 w-full max-w-sm">
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-semibold tracking-tight">Mirror</h1>
        <p className="mt-2 text-sm text-mute">
          Week 1 vs. week 12 — and what actually worked.
        </p>
      </div>

      {status === 'sent' ? (
        <div className="card text-center">
          <p className="text-sm">
            Check <span className="text-accent">{email}</span> for a sign-in link.
          </p>
          <button
            className="btn-ghost mt-4 w-full"
            onClick={() => setStatus('idle')}
          >
            Use a different email
          </button>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="card space-y-4">
          <div>
            <label className="label mb-1" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              className="input"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <button
            className="btn-primary w-full"
            type="submit"
            disabled={status === 'sending'}
          >
            {status === 'sending' ? 'Sending…' : 'Send magic link'}
          </button>
          {error && <p className="text-xs text-red-400">{error}</p>}
          <p className="text-center text-xs text-mute">
            No password. We email you a one-time sign-in link.
          </p>
        </form>
      )}
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
