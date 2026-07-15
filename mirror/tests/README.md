# Mirror — verification harnesses

Evidence for the P0 end-to-end / RLS verification pass. Two harnesses, split by
what they can honestly exercise **without** a live Supabase project.

## Context: what could and couldn't be verified here

A real managed Supabase stack (GoTrue auth, Storage API, PostgREST) was **not**
reachable in the build environment:

- **Cloud project** — no Supabase account credentials available to create one.
- **Local `supabase start` (Docker)** — the image layers for
  Postgres/GoTrue/Storage/PostgREST are served from CloudFront domains that the
  network egress policy `403`-rejects, so the images can't be pulled.

So the security-critical guarantees were verified at their **true enforcement
layer** instead of through the HTTP services that delegate to it.

## `rls/` — adversarial Row Level Security (PRD "Privacy", schema §)

`run.sh` stands up a throwaway local Postgres 16, reconstructs the exact
Supabase-provided scaffolding the migration depends on (`00_scaffold.sql`, using
Supabase's real `auth.uid()` / `storage.foldername()` bodies and the
`anon`/`authenticated` roles with production-equivalent grants), applies
`supabase/migrations/0001_init.sql` **unchanged**, then runs `10_adversarial.sql`
as the non-owner `authenticated` role (superusers bypass RLS) with the JWT `sub`
claim set per-request exactly like PostgREST.

```bash
bash tests/rls/run.sh    # needs postgresql-16 binaries; uses sudo -u postgres if root
```

Why this is faithful: PostgREST and the Storage API do not implement their own
authorization — they `SET ROLE authenticated`, set `request.jwt.claims`, and run
SQL. The RLS policies in the migration are the whole enforcement mechanism. A
signed-URL request for an object is gated by a `SELECT` on `storage.objects`
under the caller's RLS; if that returns no row (as shown below), no URL is
signed.

**Result — all pass.** User A = `1111…`, attacker B = `2222…`:

| Attack | Outcome |
|---|---|
| B `SELECT`s all/any of A's `sessions` | `0 rows` |
| B `SELECT`s A's `photos` (storage_path leak) | `0 rows` |
| B `UPDATE`/`DELETE` A's session | `0 rows affected` |
| B `INSERT`s a session with `user_id = A` | `ERROR: new row violates row-level security policy for table "sessions"` |
| B `SELECT`s all/any of A's `storage.objects` | `0 rows` (⇒ signed-URL issuance fails) |
| B writes an object into A's `{uid}/…` folder | `ERROR: new row violates row-level security policy for table "objects"` |
| Controls: A reads its own row/object | `1 row` (not over-blocked) |
| Control: `anon` (no JWT) reads sessions | `0 rows` |

## `browser/` — client-only logic (PRD §1 lighting, §2 export)

`harness.html` copies the function bodies **verbatim** from `src/lib/image.ts`
(`meanLuminance`), `src/app/compare/CompareViewer.tsx` (`drawCover`), and the
`LIGHTING_DELTA_THRESHOLD` constant, and exercises them in real Chromium.

```bash
npm i -D playwright-core
CHROME=/opt/pw-browsers/chromium-1194/chrome-linux/chrome node tests/browser/run.mjs
```

**Result — all pass:**

- **Lighting drift (§1):** baseline gray 210 vs a genuinely darker frame (45)
  → Δ165 > 28 → warning **fires**; baseline 210 vs 205 → Δ5 < 28 → **silent**.
- **Export (§2):** produces a real `image/jpeg` blob (1272×912, ~12.5 kB) and
  the `download`-attributed anchor fires a real browser download event
  (`mirror-comparison.jpg`, bytes written to disk) — not a canvas that never
  downloads.

## Still requires a real Supabase project (not verified here)

- Magic-link sign-in round-trip (GoTrue email delivery).
- Actual photo bytes uploaded to Storage under `{user_id}/…` and fetched back
  through a signed URL (the *path* and the RLS gating it are verified; the HTTP
  upload/download round-trip is not).
- Ghost overlay rendering *real* previous-session image data (fetch logic and
  no-prior-session silent-fail are code-verified; pixel rendering is not).
