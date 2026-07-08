> **This is the annotated, in-repo copy of the build spec.** The original
> lives at `C:\Users\KAI_t\Downloads\B2B_REBUILD_SPEC.md` and is left
> untouched as the historical record of what was originally handed over.
> This file is the one future sessions should read — it carries the same
> content plus dated corrections (in blockquotes like this one) where the
> original plan turned out to be stale. See **§15 Amendments log** at the
> bottom for a flat summary of every change.
>
> Copied into the repo 2026-07-08 (Phase 7 session), because it wasn't
> actually in the repo before despite being the single source of truth.

# B2B — Rebuild Spec v2 (Full, Improved)

*Hand this file to Claude Code. It is the single source of truth for rebuilding the app from zero.*
*The original codebase is lost. This spec recreates everything it did and closes the security gaps the old build left as TODOs.*
*Snapshot: July 3, 2026. Name history: calinks → Mitos → **B2B**. Pilot campus: UC Santa Cruz.*

> **AMENDED 2026-07-08:** the project is being renamed away from "B2B" —
> name TBD, "B2B" becomes an umbrella brand rather than the product name.
> No new user-facing "B2B" strings as of Phase 5 onward; existing branding
> (templates, this doc's title, etc.) stays untouched until a dedicated
> rename session.

---

## 1. What you are building

B2B is a cross-campus student networking platform for the UC system. AI-powered course equivalency matching is the invisible infrastructure; the social layer is the product students see. A student at UCSC taking CSE 101 discovers peers at UCLA taking CS 32 because the system knows those courses are equivalent. Peers surface through that academic context: profiles, peer discovery, and a help request board.

The name comes from DJ culture — "back to back," two DJs sharing the decks. Two students, two campuses, one course.

**Build target:** a Flask app that boots at `localhost:5000` after `python seed.py`, with seeded test students across UCSC, UCLA, UCSD, and UC Berkeley, a dark glassmorphic UI, secure session auth, dual-mode Gemini wired in, and the compliance layer (CSRF, FERPA consent, CCPA deletion) implemented — not stubbed.

> **AMENDED 2026-07-08:** "dual-mode Gemini wired in" is stale — see the
> Phase 6 redesign note in §7. "dark glassmorphic UI" is stale — see the
> pending-design-pass note in §9.

**Do not build past this spec.** §13 lists pipeline features that are out of scope.

---

## 2. What "better" means in this rebuild

The old build shipped Security Phase 1 (password hashing, no auto-login, `login_as` neutralized, POST /login and /logout) and left five items as TODO comments. This rebuild implements all of them:

| Old state | v2 requirement |
|---|---|
| CSRF: TODO | Flask-WTF `CSRFProtect` on the whole app; every POST form carries a token |
| FERPA consent: TODO | Consent screen at registration + per-student course visibility toggle |
| CCPA deletion: TODO | `POST /account/delete` cascades: enrollments, help posts/responses, interaction logs, then the student row |
| Prompt injection: TODO | User-supplied text never lands raw in Gemini prompts (see §7.3) |
| PII in `interaction_log`: TODO | Store no raw PII in payloads; encrypt payload column at rest with Fernet |
| Single-file-ish structure | App factory + blueprints, config classes, `.env` via python-dotenv |
| No tests | Minimal pytest suite covering auth, CSRF, equivalency cache, deletion cascade |
| `render_template_string` login (SSTI risk) | Template files only. `render_template_string` is banned across the codebase |

> **AMENDED 2026-07-03 (Phase 2):** CCPA deletion cascade was changed —
> authored help requests are anonymized (student reference → NULL,
> rendered "Deleted User") rather than deleted, so other students'
> genuine responses on them survive. Everything else the student owns
> (profile, enrollments, interaction logs, their own responses elsewhere)
> is still hard-deleted. See `repository.delete_student_and_data()`.

---

## 3. Stack

| Layer | Choice | Notes |
|---|---|---|
| Backend | Python Flask (app factory pattern) | Blueprints per domain |
| Database | SQLite via SQLAlchemy | ~~Schema stays Firestore-migration-ready~~ **AMENDED 2026-07-08: if this DB ever migrates, the target is Supabase Postgres, not Firestore. No migration work is being built now — this only corrects the stated target so no future session builds toward Firestore.** UUID string PKs, flat documents, JSON columns instead of deep joins remain good practice independent of the target. |
| AI | ~~Google Gemini, dual-mode~~ **AMENDED 2026-07-08 — see §7 redesign note.** | `from google import genai` — **never** the deprecated `google.generativeai` import (still true if/when the batch script is built) |
| Frontend | Server-rendered Jinja, HTML/CSS | ~~Dark glassmorphic design system (§9)~~ **AMENDED 2026-07-08 — see §9 pending-design-pass note.** |
| Auth | `werkzeug.security` hashing, Flask sessions | Extended 2026-07-03 (Phase 3): two independently-verified emails (`edu_email` proof-of-affiliation only, `personal_email` is the login identity) — see `routes/auth.py` |
| CSRF | Flask-WTF | |
| Encryption | `cryptography` (Fernet) for interaction_log payloads | Key from env var `LOG_ENC_KEY` |
| Config | python-dotenv | `GEMINI_API_KEY`, `SECRET_KEY`, `LOG_ENC_KEY` |
| Tests | pytest | |

`requirements.txt`: flask, flask-sqlalchemy, flask-wtf, google-genai, werkzeug, python-dotenv, cryptography, pytest.

~~Gemini dual-mode:~~
- ~~**Deep Research** — async, bulk course equivalency mapping jobs (batch endpoint, admin-triggered)~~
- ~~**Gemini Flash** — synchronous, real-time single-pair lookups~~

> **AMENDED 2026-07-08 (see §7 for full redesign note):** the two-mode
> split above (runtime Flash + async Deep Research) is being replaced by
> a single **offline batch resolution script**. Unknown pairs queue up;
> a script resolves them later (model TBD at build time). Not built yet
> — do not build the version described above.

The app must boot and fully function on seeded data with **no** `GEMINI_API_KEY` set. Gemini is an enhancement path, never a boot dependency. *(This constraint still holds under the batch-script redesign — seeded/cached equivalencies are still the only thing the running app depends on.)*

---

## 4. Project layout

```
b2b/
  app.py                    # entry point: create_app() + run
  config.py                 # Config classes (Dev, Test), env loading
  models.py                 # SQLAlchemy models + password helpers
  repository.py             # DB access layer — all queries route through here
  routes/
    auth.py                 # POST /login, /logout, /register (with consent), /account/delete
    students.py              # profiles, peer discovery, visibility settings
    courses.py               # course CRUD, equivalency lookup + confirm/deny
    help_board.py            # help request board
  services/
    gemini_service.py         # AMENDED 2026-07-08: see §7 — this becomes an
                              # offline batch script (name/location TBD at
                              # build time, likely scripts/ not services/),
                              # not a runtime Flask service module.
    equivalency.py            # equivalency engine: cache, confidence math, confirmations
    crypto.py                 # Fernet encrypt/decrypt for interaction_log payloads
  templates/
    base.html
    login.html
    register.html            # includes FERPA consent block
    dashboard.html
    profile.html
    peers.html
    help_board.html
    settings.html             # visibility toggle, delete account
  static/css/glass.css         # AMENDED 2026-07-08: pending design pass, §9
  seed.py
  tests/
    test_auth.py
    test_equivalency.py
    test_deletion.py
  b2b.db                    # generated
  requirements.txt
  .env.example
```

> **Note (2026-07-03, Phase 3):** actual auth also added
> `templates/verify_pending.html`, `personal_email.html` for the two-email
> verification flow, not listed in the original layout above.

---

## 5. Database schema

All PKs are UUID strings ~~(Firestore-friendly)~~ **AMENDED 2026-07-08: "portable across a future migration" — the concrete target, if one ever happens, is Supabase Postgres, not Firestore (§3).** Timestamps are ISO UTC strings from `datetime.now(timezone.utc)` — `datetime.utcnow()` is deprecated, never use it.

**students**
- id (uuid pk), name, ~~email (unique)~~ **AMENDED 2026-07-03 (Phase 3): split into `edu_email` (unique, verification-only proof of UC affiliation, never a login credential) and `personal_email` (unique, nullable until onboarding step 2, the actual login identity) — each with its own `edu_verified`/`personal_verified` boolean. Account is fully active (`is_fully_active`) only when both are true.**, password_hash
- campus — enum of the 9 UCs: Berkeley, UCLA, UCSD, UCSC, Davis, Irvine, UCSB, Riverside, Merced
- year, interests (JSON list), social_handles (JSON: instagram/twitter/github)
- **consent_given_at** (nullable ISO string — set at registration when FERPA consent box checked; registration fails without it)
- **course_visibility** ("peers" | "hidden", default "peers") — FERPA user control
- created_at

**courses**
- id (uuid pk), campus, course_code (e.g. "CSE 101"), title, description, source ("uc_directory")

**enrollments**
- id (uuid pk), student_id (fk), course_id (fk), term

**equivalencies** ← the persistent equivalency database: mapped once, stays mapped
- id (uuid pk), course_a_id, course_b_id, confidence (float 0–1)
- method ("gemini_deep_research" | "gemini_flash" | "student_confirmed")
- confirmations (int), denials (int), created_at
- Store pairs canonically (lower UUID first) so A↔B and B↔A never duplicate

**help_requests**
- id (uuid pk), student_id, course_id, topic, body, status ("open" | "resolved"), created_at
- **AMENDED 2026-07-03 (Phase 3):** `student_id` is nullable — set to NULL on account deletion (anonymized authorship, "Deleted User") rather than deleting the row, per §2's amendment.

**help_responses**
- id (uuid pk), request_id, student_id, body, rating (nullable int), created_at

**interaction_log**
- id (uuid pk), student_id, event_type, payload_encrypted (Fernet-encrypted JSON blob), created_at
- Payloads carry event metadata only (course ids, action names) — never email, never message bodies. Encryption is defense in depth, not a license to log PII.

---

## 6. Auth and account lifecycle

Replicate Security Phase 1 exactly, then extend:

1. Passwords hashed with `werkzeug.security.generate_password_hash` / verified with `check_password_hash`. No plaintext anywhere, ever.
2. **No auto-login.** Nothing authenticates on boot.
3. No `login_as` route exists. If a request hits that path, redirect to `/login`. It must never authenticate.
4. `POST /login` from `templates/login.html`, `POST /logout` clears the session. `render_template_string` is banned.
5. `POST /register`: name, email, password, campus, year, and a required FERPA consent checkbox. Unchecked box → 400 with a clear message. Checked → `consent_given_at` timestamped.
6. CSRF tokens on every form via Flask-WTF. A POST without a token returns 400 in tests.
7. `POST /account/delete` (session-authenticated, confirm step in UI): delete enrollments, help_requests, help_responses, interaction_log rows, then the student. Log nothing about the deleted user afterward. Return the user to a logged-out goodbye page.
8. Protected pages redirect unauthenticated users to `/login`.

> **AMENDED 2026-07-03 (Phase 3):** items 5 and 7 above evolved —
> registration is now a three-step flow (edu email + password + consent →
> mandatory personal email → both independently verified via magic link)
> and item 7's cascade anonymizes authored help requests instead of
> deleting them. See §5's amendments and `routes/auth.py`.

---

## 7. Gemini service (`services/gemini_service.py`)

> **AMENDED 2026-07-08 — REDESIGNED, not yet built.** Everything in §7.1–§7.4
> below describes the *original* plan: a runtime Flask service, invoked
> synchronously by user actions, with per-request prompt-injection
> hardening and a per-user rate limit. **That plan is superseded.** The
> new direction: unknown equivalency pairs queue up (already true today —
> `services/equivalency.check_equivalency()` returns `{"status":
> "unknown"}` on a cache miss with zero side effects, per Phase 5), and a
> separate **offline batch script** resolves them later, off the request
> path entirely (model TBD at build time — this may or may not end up
> being Gemini). Because resolution is no longer triggered by a live user
> request, most of §7.3's scope (per-request prompt-injection hardening,
> the 10-lookups/hour rate limit) is **largely obsolete** — a batch job
> reading from the `courses` table has no live user input to inject
> anything through in the first place. Course-code format validation
> before persisting any course row is still worth keeping regardless of
> resolution mode. **Do not build the runtime dual-mode service described
> below.** This phase (whichever phase eventually builds the batch
> script) needs its own spec pass once the model choice is made — this
> annotation exists so no session builds the old version by default.

### 7.1 Client

```python
from google import genai
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
```

If the key is missing, the service returns `None` results and the app degrades to cached equivalencies without erroring.

### 7.2 Cache-first flow

Any equivalency lookup checks the `equivalencies` table first. Only an unmapped pair may trigger a Gemini call. A successful call writes a new row (method `gemini_flash`, confidence from the model's structured response). The second lookup of the same pair must hit the cache with zero API calls. Deep Research mode batches many pairs in one admin-triggered job and writes rows with method `gemini_deep_research`.

> **Still accurate and already built (Phase 5):** the cache-first check
> itself. `services/equivalency.check_equivalency()` implements exactly
> this — hits the table, returns `unknown` on a miss, makes no external
> call. What's redesigned per the note above is *what happens next* on a
> miss (batch script, not a live per-request Gemini call).

### 7.3 Prompt injection hardening

User-typed strings (course codes, titles, topics) never get concatenated raw into prompt text. Rules:

- Whitelist-sanitize course codes (`[A-Za-z]{2,6}\s?\d{1,3}[A-Z]?`) before use; reject anything else with a validation error before Gemini is touched.
- Course titles/descriptions passed to Gemini come only from the `courses` table rows sourced from `uc_directory` seeds — not free text from the request.
- The prompt template instructs the model to respond with JSON only (`{"equivalent": bool, "confidence": float, "reason": str}`) and the service parses defensively: strip fences, `json.loads` in try/except, discard on failure.
- Per-user rate limit: max 10 Gemini-triggering lookups per user per hour, tracked in memory (simple dict) with a TODO comment noting Redis for production.

> **AMENDED 2026-07-08:** see the §7 redesign note — this whole
> subsection assumes a runtime, user-triggered call path that no longer
> exists in the new design. Course-code whitelisting is still sensible
> input validation regardless (keep it wherever courses get created), but
> the per-user rate limit was specifically about live-request abuse and
> has no equivalent concern in an offline batch job.

### 7.4 Confidence and confirmations

Students can confirm or deny a surfaced equivalency (`POST /equivalencies/<id>/confirm` and `/deny`). Confirmations increment the counter and nudge confidence up (cap 0.99); denials nudge down. A pair with denials > confirmations and confidence < 0.5 stops surfacing in peer discovery but stays in the table as data.

> **AMENDED 2026-07-03 (Phase 5):** the spec never states the nudge
> magnitude or a floor. Resolved with the project owner rather than
> guessed: fixed **±0.05 per confirm/deny event**, clamped to **[0.01,
> 0.99]**. Implemented in `services/equivalency.py`
> (`confirm_equivalency` / `deny_equivalency` / `is_surfaceable`). This
> subsection is unaffected by the §7 Gemini redesign — confirm/deny is a
> student action against an existing row, not a Gemini call.

---

## 8. Peer discovery

Dashboard and `/peers` show, for each of the logged-in student's enrollments: students at other campuses enrolled in equivalent courses (confidence ≥ 0.5), respecting `course_visibility` — students set to "hidden" never appear in anyone's results. Each peer card: name, campus, year, interests, the matched course pair with confidence, and social handles. All of this works from seed data alone.

> **Note (2026-07-08, Phase 7):** "confidence ≥ 0.5" here and
> `is_surfaceable()`'s "denials > confirmations AND confidence < 0.5" from
> §7.4 are two different gates that both apply: a match must clear the
> confidence floor *and* not have been denied into non-surfaceable
> status. Also: unverified accounts (`is_fully_active == False`) are
> excluded from peer discovery in addition to hidden-visibility students —
> not stated explicitly in this section, but required by §6's
> verification-gate amendment (an account isn't real until both emails
> verify, so it shouldn't be discoverable either). The exact fields shown
> per peer card (name form, contact path) were escalated to the project
> owner as a privacy decision — see the Phase 7 commit message and
> amendments log for the resolution.

---

## 9. UI — dark glassmorphic design system

> **AMENDED 2026-07-08: PENDING DESIGN PASS.** The aesthetic direction
> below is the *original* plan and is being re-decided in Claude Design
> before implementation. Nothing here is confirmed. Do not implement this
> section literally — when Phase 9 (styling) actually starts, check for
> an updated design direction first. Left in place, not deleted, as the
> fallback/reference if no redesign happens before then.

- Background: deep navy-to-black gradient (`#0a0e1a` → `#05070d`)
- Cards: `rgba(255,255,255,0.06)` fill, `backdrop-filter: blur(14px)`, 1px `rgba(255,255,255,0.12)` border, 16px radius, soft shadow
- Accent: one gradient used sparingly (electric blue `#4f8cff` → violet `#8b5cf6`) for primary buttons and confidence bars
- Typography: system stack (`-apple-system, Segoe UI, Inter, sans-serif`), high-contrast white/near-white text, muted `rgba(255,255,255,0.55)` secondary text
- Confidence shown as a slim gradient bar with the percentage
- Layout: single-column mobile-first, max-width ~960px centered on desktop
- No frontend framework, no build step. One `glass.css`.

---

## 10. Seed data (`seed.py`)

- 4 active campuses: UCSC, UCLA, UCSD, UC Berkeley
- 20–30 real courses with genuine codes/titles from official UC course directories. Anchor pair: UCSC CSE 101 ↔ UCLA CS 32, confidence 0.87
- 6–8 test students spread across the 4 campuses, hashed password `testpass123`, each with `consent_given_at` set, 2–4 enrollments, interests, and at least one social handle. Make one student `course_visibility="hidden"` so the privacy filter is testable
- 5+ pre-mapped equivalencies (method `gemini_flash`) so peer discovery works offline
- 3 open help requests, at least one with a response
- Idempotent: running `seed.py` twice must not duplicate rows (wipe-and-recreate is fine for dev)

Run order: `python seed.py` → `python app.py` → `localhost:5000`.

> **Delivered (Phase 4, 2026-07-03):** 29 courses, 17 equivalencies
> (anchor pair at 0.87 as specified), 7 students all pre-verified on both
> emails, Priya Patel (UCSC) seeded hidden, 3 help requests with 1 answer.

---

## 11. Build order and git discipline

**PHASE GATING — HARD RULE:** Execute exactly ONE phase per session, then STOP. After committing a phase: report what you built, show the commit hash, state which acceptance checklist items (§12) now pass, and wait for Makai to say "continue" or "next phase" before touching anything else. Never chain phases. Never start the next phase "since it's small." If Makai's message names a specific phase, do only that phase. If anything in the current phase fails, fix it within the same session, but still stop at the phase boundary.

Initialize a git repo before writing code (this counts as part of phase 1). Conventional commits, one commit per phase, working state at every commit:

1. `chore: scaffold project tree, config, requirements` — app factory boots to a hello page
2. `feat: models and repository per spec §5`
3. `feat: auth with hashing, CSRF, consent registration, deletion cascade (§6)`
4. `feat: seed data (§10)` — app now shows real content
5. `feat: equivalency engine with cache-first logic (§7.2, §7.4)`
6. ~~`feat: gemini dual-mode service with injection hardening (§7.1, §7.3)`~~ **AMENDED 2026-07-08: this phase is redesigned per §7's note — an offline batch resolution script, not a runtime dual-mode service. Do not build the original version of this phase. New scope TBD at build time (model choice pending).**
7. `feat: peer discovery with visibility filtering (§8)`
8. `feat: help board`
9. ~~`style: glassmorphic UI pass (§9)`~~ **AMENDED 2026-07-08: pending design pass — see §9. Phase number/scope may change once a direction is confirmed.**
10. `test: pytest suite for auth, CSRF, cache, deletion`
11. `docs: README with run instructions and .env.example`

Within each phase: run the app (and tests once they exist) before committing. If something fails, fix it before committing. Then stop and report per the phase-gating rule above. The end-of-phase report format:

```
PHASE N COMPLETE — <phase name>
Commit: <hash> <message>
Built: <2-4 bullet summary>
Checklist items now passing: <items from §12>
Blockers/notes: <anything Makai should know>
Awaiting go-ahead for Phase N+1.
```

---

## 12. Acceptance checklist

- [x] `python seed.py && python app.py` boots clean at localhost:5000 with **no** `GEMINI_API_KEY` set
- [x] Registration requires the FERPA consent checkbox; refusing it blocks signup
- [x] Login as a seeded student works; wrong password rejected; no auto-login anywhere; `login_as` path never authenticates
- [x] Every POST form fails without a CSRF token
- [ ] Dashboard shows cross-campus peers from seeded equivalencies with zero Gemini calls
- [ ] The seeded "hidden" student never appears in anyone's peer results
- [ ] ~~With `GEMINI_API_KEY` set, an unmapped pair triggers one Flash lookup, writes an `equivalencies` row, and the second lookup hits cache~~ **AMENDED 2026-07-08: not applicable under the batch-script redesign (§7). Replacement checklist item TBD when that phase is built.**
- [ ] ~~Invalid course-code input is rejected before any Gemini call~~ **AMENDED 2026-07-08: rate-limit/injection framing is obsolete per §7.3's note; basic course-code format validation may still apply wherever courses are created, TBD.**
- [x] Confirm/deny endpoints adjust confidence and counters
- [ ] Help board: post, view across equivalent courses, respond
- [x] `POST /account/delete` removes the student and every dependent row; their peers' pages no longer show them *(amended: authored help requests are anonymized, not removed — §2, §6)*
- [ ] `interaction_log.payload_encrypted` is unreadable in a raw DB dump; decrypts with `LOG_ENC_KEY`
- [x] `grep -ri render_template_string` returns nothing
- [x] pytest passes

---

## 13. Out of scope — do not build

Pipeline features, planned but not for this rebuild: professor-tied course reviews surfacing across equivalents, subject mastery leaderboards (contribution-based, semester reset), study group matching, transfer-specific boards and roadmap builders, skill/interest tagging, degree planning graduation mapper, creative portfolios, ~~Firestore migration~~ **AMENDED 2026-07-08: if migration ever happens, the target is Supabase Postgres — see §3.**, custom LLM fine-tuning on interaction data, deployment beyond localhost.

---

## 14. Environment notes (Makai's machine)

- Project path: `C:\Users\KAI_t\Documents\Anti-Claude Projects\b2b\`
- Run everything from a **normal, non-Administrator PowerShell**. Admin context breaks `Path.home()`, agy credentials, and pip.
- Python 3.14, Windows 11, username KAI_t
- Env vars before boot: `GEMINI_API_KEY` (optional), `SECRET_KEY`, `LOG_ENC_KEY` (generate with `Fernet.generate_key()`; put instructions in `.env.example`)
- If dispatching parts through the bridge instead of Claude Code directly: `.task` headers on separate lines (`PROJECT:`, `CONTEXT:`, `OUTPUT:`, `ROUTE:`, `MODEL:`), blank line, prompt body. Model string `gemini-3.5-flash`. Bridge division of labor: Antigravity scaffolds trees/templates/seed boilerplate; Claude Code owns auth, the Gemini service, repository verification, and tests.

---

## 15. Amendments log

Flat, dated summary of every place this copy diverges from the original `B2B_REBUILD_SPEC.md`. Inline blockquotes above are the authoritative detail; this is the index.

| Date | Area | What changed | Where |
|---|---|---|---|
| 2026-07-03 (Phase 2) | CCPA deletion | Authored help requests anonymized (student_id → NULL), not deleted — preserves other students' responses | §2, §5, §6 |
| 2026-07-03 (Phase 3) | Identity/auth | Single `email` split into `edu_email` (verification-only, never a login credential, no password ever collected for it) + `personal_email` (the actual login), each independently verified; account active only when both are | §3, §5, §6 |
| 2026-07-03 (Phase 3) | Registration | UC-domain allowlist on `edu_email` (10 domains incl. `g.ucla.edu`); `personal_email` accepts any domain | §6 |
| 2026-07-03 (Phase 5) | Confidence math | Confirm/deny nudge and floor weren't specified numerically; resolved as ±0.05 per event, clamped [0.01, 0.99] | §7.4 |
| 2026-07-08 (Phase 7 prep) | DB migration target | Firestore → **Supabase Postgres**, if migration ever happens (nothing being built now) | §3, §5, §13 |
| 2026-07-08 (Phase 7 prep) | Phase 6 scope | Runtime dual-mode Gemini service → **offline batch resolution script**; per-request injection hardening / rate limiting scope is largely obsolete under this design; model TBD | §7, §11 item 6, §12 |
| 2026-07-08 (Phase 7 prep) | Phase 9 / UI | Dark glassmorphic design system flagged **pending design pass** — direction to be re-decided in Claude Design before implementation | §1, §3, §9, §11 item 9 |
| 2026-07-08 | Branding | Project being renamed away from "B2B" (name TBD); no new user-facing "B2B" strings from Phase 5 onward | title block |
