# Mirror

A grooming progress tracker that shows you week 1 vs. week 12, logs what you
actually did, and correlates it against what changed.

No score. No rating. No phi mask. The only facial variables that move are skin,
hair, body composition, and sleep — so Mirror tracks the movable things and
shows change over time.

This is the **P0 core** (build-order sessions 1–4): auth, schema + RLS + private
photo storage, guided capture with ghost-outline alignment, side-by-side/slider
compare, and the 15-second daily log. Correlate (§5) and the Mirror Toy (§6) are
future work.

## Stack

- **Next.js** (App Router, TypeScript) — installable PWA, camera via `getUserMedia`
- **Supabase** — Postgres + Storage + Auth (magic-link email)
- **Tailwind CSS**

## What's built

| Feature | Status | Where |
|---|---|---|
| Auth (magic link) | ✅ | `src/app/login`, `src/app/auth`, `src/middleware.ts` |
| Schema + RLS + Storage | ✅ | `supabase/migrations/0001_init.sql` |
| Capture (3-angle, ghost overlay, lighting warn) | ✅ | `src/app/capture` |
| Compare (side-by-side + slider + timeline + export) | ✅ | `src/app/compare` |
| Log (15-second daily entry) | ✅ | `src/app/log` |
| Stack (products + adherence) | ✅ (minimal) | `src/app/stack` |
| Correlate (≥8 weeks) | ⬜ future | — |
| Mirror Toy | ⬜ future | — |

## Setup

### 1. Create a Supabase project

At [supabase.com](https://supabase.com), create a project and grab the URL and
anon key from **Project Settings → API**.

### 2. Run the migration

Apply `supabase/migrations/0001_init.sql`. Either:

- Paste it into the Supabase **SQL Editor** and run, or
- With the [Supabase CLI](https://supabase.com/docs/guides/cli):
  ```bash
  supabase link --project-ref <your-ref>
  supabase db push
  ```

This creates every table, the default-deny owner-only RLS policies, and the
**private** `photos` storage bucket with owner-scoped access.

### 3. Configure environment

```bash
cp .env.example .env.local
# then fill in NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY
```

### 4. Run

```bash
npm install
npm run dev        # http://localhost:3000
```

> **Camera note:** `getUserMedia` requires a secure context. `localhost` is
> treated as secure; on any other host you need HTTPS.

## Privacy model

Face photos are the most sensitive data here, so:

- Photos live in a **private** Storage bucket, reachable only via **signed URLs
  with a 10-minute TTL** (`src/lib/photos.ts`).
- Object keys are `{user_id}/{session_id}/{angle}.jpg`; storage RLS keys
  ownership off the first path segment.
- Every table is RLS default-deny, owner-only.
- The service worker never caches photo bytes or Supabase responses
  (`public/sw.js`); comparison exports are generated client-side and never
  uploaded.
- `/capture` and `/compare` send `Cache-Control: no-store` and
  `Referrer-Policy: no-referrer`.

**Not yet implemented:** full account deletion (delete = actually delete,
including Storage objects). Row deletes cascade today; a "delete everything"
flow that also purges Storage is on the roadmap before this goes multi-user.

## Layout

```
mirror/
  supabase/migrations/   SQL: schema, RLS, storage bucket + policies
  src/
    app/
      login/  auth/       magic-link sign-in + PKCE callback
      capture/            guided 3-angle session + ghost overlay
      compare/            slider / side-by-side / timeline / export
      log/                daily log (scores, breakout map, adherence)
      stack/              product list + start dates
    components/           NavBar, ServiceWorker, GhostThumb
    lib/                  supabase clients, photos, image, date helpers, types
```
