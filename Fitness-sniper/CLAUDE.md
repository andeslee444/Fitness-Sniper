# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Fitness Sniper auto-books competitive fitness classes (Barry's, Aarmy, SLT, Xponential brands) before they fill up. npm workspaces monorepo with a Playwright worker daemon, Next.js dashboard, and local PostgreSQL (via direct `pg` pool) backend.

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
npm run lint                   # Lint everything (web only — worker has no ESLint)

# Manual test (dry-run booking against real API)
npx tsx worker/src/test-booking.ts
```

No test framework is configured. There are no automated tests.

## Architecture

```
├── worker/              # Playwright booking daemon (runs on Mac Mini)
├── web/                 # Next.js 16 App Router dashboard
├── packages/shared/     # @fitness-sniper/shared — types, studio configs, API clients
├── supabase/migrations/ # PostgreSQL schema (5 migration files)
└── archive/             # Legacy code (reference only, not deployed)
```

### Worker (`worker/src/`)

Entry point: `index.ts` — initializes poller, processor, scheduler, scraper. Sends heartbeats every 30s.

**Job pipeline:** `scheduler.ts` (cron every 15 min) → creates `booking_jobs` rows → `poller.ts` claims via `claim_next_job()` RPC → `processor.ts` decrypts creds, launches browser, calls adapter → updates job status → DB trigger inserts `booking_history` → `email.ts` sends notification (from `noreply@fitnesssniper.app` via Resend).

**Scheduler extras:** Stale job recovery runs every 5 min (resets `claimed` jobs stuck >30 min, `running` jobs stuck >60 min). One-time targets auto-disabled after terminal job or passed date.

- `adapters/mariana-tek.ts` — Mariana Tek studios (Barry's, Aarmy, SLT, Practice Room). API-first with OAuth PKCE auth. Browser fallback for booking only.
- `adapters/xponential.ts` — Xponential/ClubReady studios (Rumble, CycleBar, Club Pilates, YogaSix, StretchLab, Pure Barre). API-only, no browser fallback. JWT auth via `X-Authorization` header.
- `stealth/browser.ts` — `playwright-extra` with `puppeteer-extra-plugin-stealth`. Random UA/viewport, NYC geolocation, timezone `America/New_York`.
- `stealth/human-delay.ts` — 3-8s between actions, 50-150ms per keystroke, random click offsets.
- `crypto/credentials.ts` — AES-256-GCM encrypt/decrypt. Requires `ENCRYPTION_KEY` (64-char hex = 32 bytes).
- `jobs/schedule-scraper.ts` — Scrapes 8 days ahead. 30s boot delay. Only scrapes studios with active snipe targets. Runs at 2 AM + 2 PM ET with up to 3 attempts and exponential backoff.
- `jobs/poller.ts` — Exponential backoff: 5s → 10s → 30s → 60s when idle. Concurrency limit (default 2).

**Critical: Worker imports must use `.js` extensions** (required by `moduleResolution: NodeNext`):
```ts
import { JobPoller } from './jobs/poller.js';  // ✓ correct
import { JobPoller } from './jobs/poller';      // ✗ will fail
```

### Frontend (`web/src/`)

Next.js 16.1.6 App Router with Tailwind v4 + shadcn/ui. Dark-mode only (hardcoded `className="dark"` on `<html>`).

**Auth:** AWS Cognito (not Supabase Auth). Three httpOnly cookies: `cognito_access_token`, `cognito_id_token`, `cognito_refresh_token` (30-day maxAge). Middleware checks cookie presence for protected routes (`/dashboard`, `/targets`, `/history`, `/credentials`). API routes validate via `getSession()` (calls Cognito `GetUserCommand`). Auth flow: `USER_PASSWORD_AUTH`. Signup auto-confirms via `AdminConfirmSignUpCommand`. Config: `lib/cognito.ts`.

**Database:** Direct PostgreSQL via `pg` pool (`lib/db.ts`), not Supabase client. Global singleton pattern prevents connection pool exhaustion during dev hot reload.

**API routes** (`app/api/`): `auth/signup|login|logout`, `targets/` (list/create), `targets/[id]/` (update/delete), `credentials/`, `jobs/`, `history/`, `schedules/`, `dashboard/stats/`, `worker-status/`

**Pages** (`app/(dashboard)/`): `/dashboard`, `/targets`, `/credentials`, `/history`

### Shared (`packages/shared/src/`)

Consumed as raw TypeScript source (no build step). Next.js handles via `transpilePackages: ['@fitness-sniper/shared']`. Worker resolves via workspace link.

- `types.ts` — All DB row types, `BookingResult`, `ClassInfo`, `SPOT_PREFERENCES`
- `studios.ts` — `StudioConfig`, `STUDIOS`, `STUDIO_LOCATIONS`, `LOCATION_IDS`
- `api/mt-api-client.ts` — Mariana Tek HTTP schedule scraper (shared between worker and web)
- `api/xpo-api-client.ts` — Xponential HTTP schedule scraper

### Database

5 migration files in `supabase/migrations/`. The canonical schema is `001_rds_schema.sql` (Cognito-based, `user_id` is `text`, no RLS). `001_initial_schema.sql` is the legacy Supabase Auth version (unused).

**Tables:** `profiles`, `studio_credentials`, `snipe_targets`, `booking_jobs`, `booking_history`, `worker_heartbeats`, `class_schedules`, `scrape_runs`

**Key RPC:** `claim_next_job(p_worker_id)` — atomic claim with `FOR UPDATE SKIP LOCKED`

**Triggers:** `on_job_completed()` auto-inserts `booking_history` when job status changes to success/failed.

**Migration 004** added separate `password_iv` and `password_auth_tag` columns — existing credentials need re-saving after this migration.

## Environment Variables

### Worker (`worker/.env`)
`DATABASE_URL`, `ENCRYPTION_KEY` (64-char hex), `RESEND_API_KEY`, `WORKER_ID`

### Frontend (`web/.env.local`)
`DATABASE_URL`, `ENCRYPTION_KEY` (same as worker), `AWS_REGION`, `COGNITO_CLIENT_ID`, `COGNITO_CLIENT_SECRET`, `COGNITO_USER_POOL_ID`

## Key Patterns

- **Two platforms** — Mariana Tek (Barry's, Aarmy, SLT, Practice Room) and Xponential/ClubReady (Rumble, CycleBar, Club Pilates, YogaSix, StretchLab, Pure Barre). Completely different APIs, auth mechanisms, and adapters.
- **Mariana Tek auth** — All iframe studios share one OAuth client_id: `sbLziNCoF5HcOhkSV6zRL8O7betwd3mDDIQbWZa3`. API: `{tenant}.marianatek.com/api/customer/v1/`.
- **Xponential auth** — JWT via `X-Authorization: Bearer {token}` (not standard `Authorization`). API: `members.{brand}.com/api/`.
- **Encryption symmetry** — Web encrypts credentials on save, worker decrypts at booking time. Both must share the same `ENCRYPTION_KEY`.
- **Job deduplication** — Scheduler checks for existing jobs before creating new ones for the same target + date.
- **Booking window** — 7 days. Scheduler only creates jobs for classes within this window. Scraper fetches 8 days ahead.
- **Target types** — `recurring` (day_of_week + time, repeats weekly) and `one_time` (target_date + time, auto-disables after attempt).
- **Fragile selectors** — Studio sites change DOM frequently. When selectors break, check `archive/` for historical patterns.

## Key Dependency Versions

| Package | Version | Notes |
|---|---|---|
| Next.js | 16.1.6 | App Router |
| React | 19.2.3 | |
| Tailwind | v4 | Uses `@tailwindcss/postcss`, breaking changes from v3 |
| Zod | v4.3.6 | Breaking API changes from v3 |
| radix-ui | 1.4.3 | Unified package (not `@radix-ui/react-*` individual packages) |
| Playwright | 1.50.0 | Via `playwright-extra` in worker |
| ESLint | 9 | Flat config format (web only) |
