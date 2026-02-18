# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Fitness Sniper auto-books competitive fitness classes (Barry's, Aarmy, SLT, Xponential brands) before they fill up. npm workspaces monorepo with a Playwright worker daemon, Next.js dashboard, and PostgreSQL (Supabase) backend.

## Commands

```bash
npm install                    # Install all workspaces

# Worker (Mac Mini daemon)
npm run worker                 # Start worker dev (tsx)
npm run worker:build           # Build worker (tsc → dist/)

# Frontend (Next.js 16 + React 19)
npm run web:dev                # Next.js dev server
npm run web:build              # Production build

# All workspaces
npm run build                  # Build everything
npm run lint                   # Lint everything
```

## Architecture

```
├── worker/              # Playwright booking daemon (runs on Mac Mini)
├── web/                 # Next.js App Router dashboard
├── packages/shared/     # @fitness-sniper/shared — types, studio configs
├── supabase/migrations/ # PostgreSQL schema (3 migrations)
└── archive/             # Legacy code (reference only, not deployed)
```

### Worker (`worker/src/`)

Entry point: `index.ts` — initializes poller, processor, scheduler, scraper. Sends heartbeats every 30s.

**Job pipeline:** `scheduler.ts` (cron every 15 min) → creates `booking_jobs` rows → `poller.ts` claims via `claim_next_job()` RPC → `processor.ts` decrypts creds, launches browser, calls adapter → updates job status → DB trigger inserts `booking_history` → `email.ts` sends notification.

- `adapters/mariana-tek.ts` — Booking for Mariana Tek studios (Barry's, Aarmy, SLT, Practice Room). API-first with OAuth PKCE auth.
- `adapters/xponential.ts` — Booking for Xponential/ClubReady studios (Rumble, CycleBar, Club Pilates, YogaSix, StretchLab, Pure Barre). JWT auth via `X-Authorization`.
- `stealth/browser.ts` — Playwright with anti-detection (random UA, viewport, geolocation, webdriver override).
- `stealth/human-delay.ts` — 3-8s between actions, 50-150ms per keystroke, random click offsets.
- `crypto/credentials.ts` — AES-256-GCM encrypt/decrypt. Requires `ENCRYPTION_KEY` (64-char hex = 32 bytes).
- `scrapers/` — `mt-api-client.ts` (HTTP API, preferred) and `mt-browser-scraper.ts` (fallback). Runs at 2 AM + 2 PM ET.
- `jobs/poller.ts` — Exponential backoff: 5s → 10s → 30s → 60s when idle. Concurrency limit (default 2).

### Frontend (`web/src/`)

Next.js App Router with Tailwind + shadcn/ui.

**Auth:** AWS Cognito (not Supabase Auth). Tokens stored in httpOnly cookies (`cognito_access_token`). Middleware redirects unauthenticated users to `/login`. Config: `lib/cognito.ts`.

**Database:** Direct PostgreSQL via `pg` pool (`lib/db.ts`), not Supabase client. Same Supabase-hosted DB but accessed directly.

**API routes** (`app/api/`):
- `auth/signup|login|logout` — Cognito flows
- `targets/` — CRUD for snipe targets
- `credentials/` — Encrypt & upsert studio credentials
- `jobs/` — Active job listing
- `history/` — Booking history (50 most recent)
- `schedules/` — Scraped class schedules from `class_schedules` table
- `dashboard/stats/` — Aggregated stats
- `worker-status/` — Latest worker heartbeat

**Pages** (`app/(dashboard)/`): `/dashboard`, `/targets`, `/credentials`, `/history`

### Shared (`packages/shared/src/`)

- `types.ts` — All DB row types, `BookingResult`, `ClassInfo`, `SPOT_PREFERENCES`
- `studios.ts` — `StudioConfig` (slug, platform, tenant, scheduleUrl, iframe selector), `STUDIO_LOCATIONS`, `LOCATION_IDS`, `STUDIO_TIMES`

### Database

3 migrations in `supabase/migrations/`:

**Tables:** `profiles`, `studio_credentials`, `snipe_targets`, `booking_jobs`, `booking_history`, `worker_heartbeats`, `class_schedules`, `scrape_runs`

**Key RPC:** `claim_next_job(p_worker_id)` — atomic claim with `FOR UPDATE SKIP LOCKED`

**Triggers:** `on_job_completed()` auto-inserts `booking_history` when job status changes to success/failed.

**RLS:** All user tables scoped by `user_id`. Worker uses service key to bypass RLS.

## Environment Variables

### Worker (`worker/.env`)
`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `ENCRYPTION_KEY` (64-char hex), `RESEND_API_KEY`, `WORKER_ID`, `DATABASE_URL`

### Frontend (`web/.env.local`)
`DATABASE_URL`, `ENCRYPTION_KEY` (same as worker), `AWS_REGION`, `COGNITO_CLIENT_ID`, `COGNITO_CLIENT_SECRET`, `COGNITO_USER_POOL_ID`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`

## Key Patterns

- **Two platforms** — Mariana Tek (Barry's, Aarmy, SLT, Practice Room) and Xponential/ClubReady (Rumble, CycleBar, Club Pilates, YogaSix, StretchLab, Pure Barre). Different APIs, auth, and adapters.
- **Fragile selectors** — Studio sites change DOM frequently. When selectors break, check `archive/` for historical patterns.
- **Encryption symmetry** — Web encrypts credentials on save, worker decrypts at booking time. Both must share the same `ENCRYPTION_KEY`.
- **Job deduplication** — Scheduler checks for existing jobs before creating new ones for the same target + date.
- **Booking window** — 7 days. Scheduler only creates jobs for classes within this window.
- **Target types** — `recurring` (day_of_week + time, repeats weekly) and `one_time` (target_date + time, auto-disables after attempt).

## Studio Configuration

Two platforms: `mariana-tek` (Barry's, Aarmy, SLT, Practice Room) and `xponential` (Rumble, CycleBar, Club Pilates, YogaSix, StretchLab, Pure Barre). Configs in `packages/shared/src/studios.ts`. MT studios have `tenant` subdomain and `iframe` selector. Xponential studios have `membersDomain` for their portal URL.
