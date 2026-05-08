# Architecture

**Analysis Date:** 2026-02-26

## Pattern Overview

**Overall:** Event-driven worker daemon + REST API monorepo

**Key Characteristics:**
- Two independent runtime environments: a Mac Mini daemon worker and a Vercel-hosted Next.js dashboard
- Worker uses an internal job queue backed by PostgreSQL (not a separate queue service)
- Three completely distinct adapter pipelines per studio platform (Mariana Tek, Xponential, Arketa)
- Platform-specific auth and booking flows — no shared adapter interface
- Shared TypeScript package consumed without a build step (raw source)

## Layers

**Worker Entry Point:**
- Purpose: Bootstraps all subsystems and manages graceful shutdown
- Location: `worker/src/index.ts`
- Contains: Heartbeat loop, signal handlers, subsystem initialization
- Depends on: All job subsystems, `worker/src/db.ts`
- Used by: Process manager / launchd on Mac Mini

**Job Scheduler:**
- Purpose: Creates `booking_jobs` rows from enabled `snipe_targets` on a cron cadence
- Location: `worker/src/jobs/scheduler.ts`
- Contains: Cron loop (every 15 min), stale job recovery (every 5 min), one-time target auto-disable
- Depends on: `worker/src/db.ts`, `@fitness-sniper/shared` STUDIOS config
- Used by: `worker/src/index.ts`
- Note: Explicitly skips Arketa-platform targets (`platform === 'arketa'`)

**Slot Watcher (Arketa-only):**
- Purpose: Polls Arketa Cloud Run API every 60s for newly-available slots; creates jobs with `scheduled_for=NOW()` for immediate booking
- Location: `worker/src/jobs/slot-watcher.ts`
- Contains: Delta detection via in-memory `knownSlotKeys` Set, target refresh (every 5 min), key cleanup (hourly)
- Depends on: `worker/src/jobs/arketa-slot-source.ts`, `worker/src/db.ts`
- Used by: `worker/src/index.ts`

**Job Poller:**
- Purpose: Atomically claims ready `booking_jobs` from the database queue and dispatches to processor
- Location: `worker/src/jobs/poller.ts`
- Contains: Exponential backoff (5s → 10s → 30s → 60s), concurrency limiter (default 2)
- Depends on: `worker/src/db.ts`, `claim_next_job()` PostgreSQL RPC
- Used by: `worker/src/index.ts` (wires `onJob` callback to `processor.process`)

**Job Processor:**
- Purpose: Executes a single claimed booking job end-to-end
- Location: `worker/src/jobs/processor.ts`
- Contains: Target + credential fetch, adapter instantiation, booking execution, status updates, email notification
- Depends on: `worker/src/adapters/`, `worker/src/crypto/credentials.ts`, `worker/src/notifications/email.ts`
- Used by: `worker/src/jobs/poller.ts` via callback

**Adapters:**
- Purpose: Platform-specific auth and booking implementations
- Location: `worker/src/adapters/`
- Files:
  - `mariana-tek.ts` — Barry's, Aarmy, SLT, Practice Room. OAuth PKCE auth; API-first; browser fallback for booking only
  - `xponential.ts` — Rumble, CycleBar, Club Pilates, YogaSix, StretchLab, Pure Barre. JWT via `X-Authorization`; API-only
  - `arketa.ts` — Saint NYC. Firebase `signInWithPassword` → idToken; Arketa checkout API
- Depends on: `worker/src/stealth/browser.ts` (MT only), `@fitness-sniper/shared`
- Used by: `worker/src/jobs/processor.ts`

**Schedule Scraper:**
- Purpose: Background cron that pre-populates `class_schedules` table for active targets
- Location: `worker/src/jobs/schedule-scraper.ts`
- Contains: Cron at 2 AM + 2 PM ET, 30s boot delay, per-platform scrape with HTTP API first then browser fallback, 3 attempts with exponential backoff
- Depends on: `worker/src/scrapers/`, `worker/src/db.ts`
- Used by: `worker/src/index.ts`

**Scrapers:**
- Purpose: HTTP API clients for schedule discovery (used by both worker scraper and web API routes)
- Location: `worker/src/scrapers/` (worker copies) and `packages/shared/src/api/` (shared copies)
- Files:
  - `mt-api-client.ts` — Mariana Tek REST schedule fetch
  - `xpo-api-client.ts` — Xponential schedule fetch
  - `arketa-api-client.ts` — Arketa Cloud Run schedule fetch (splits cross-month ranges)
  - `mt-browser-scraper.ts` — Playwright fallback when MT HTTP API fails

**Next.js API Routes:**
- Purpose: REST API for the dashboard frontend; validate session then query PostgreSQL directly
- Location: `web/src/app/api/`
- Contains: `auth/` (signup/login/logout), `targets/` (CRUD), `credentials/` (CRUD), `jobs/`, `history/`, `schedules/` (DB-first with 5-min cache + live API fallback), `dashboard/stats/`, `worker-status/`
- Depends on: `web/src/lib/db.ts`, `web/src/lib/cognito.ts`, `@fitness-sniper/shared`
- Used by: Next.js App Router, browser-side client components

**Next.js Pages:**
- Purpose: Dashboard UI pages rendered by App Router
- Location: `web/src/app/(dashboard)/`
- Contains: `/dashboard`, `/targets`, `/credentials`, `/history`, `/schedule`
- Depends on: `web/src/components/`, `web/src/app/api/` (via fetch)
- Auth: Dashboard route group layout (`web/src/app/(dashboard)/layout.tsx`) calls `getSession()` server-side and redirects to `/login` if unauthenticated

**Shared Package:**
- Purpose: Types, studio configs, and API client functions shared between worker and web without a build step
- Location: `packages/shared/src/`
- Contains: `types.ts`, `studios.ts`, `api/mt-api-client.ts`, `api/xpo-api-client.ts`, `api/arketa-api-client.ts`, `index.ts`
- Used by: Worker (via workspace link), Next.js (via `transpilePackages` in `next.config.ts`)

## Data Flow

**Standard Booking Flow (Mariana Tek / Xponential):**

1. `ScheduleScraper` populates `class_schedules` with `booking_opens_at` for upcoming classes
2. `JobScheduler` (every 15 min) reads enabled `snipe_targets`, looks up `booking_opens_at` from `class_schedules`, inserts `booking_jobs` row with `scheduled_for = booking_opens_at`
3. `JobPoller` calls `claim_next_job(worker_id)` (Postgres RPC with `FOR UPDATE SKIP LOCKED`), receives a job whose `scheduled_for <= NOW()`
4. `JobProcessor` decrypts studio credentials → instantiates adapter → calls `adapter.bookClass()`
5. Adapter authenticates with studio API, finds the class, books the spot, returns `BookingResult`
6. Processor updates `booking_jobs.status` to `success` or `failed`
7. PostgreSQL trigger `on_job_completed()` fires, inserts row into `booking_history`
8. `sendBookingEmail()` sends success/failure notification via Resend

**Arketa Booking Flow (Slot-Watcher path):**

1. `SlotWatcher` (every 60s) calls Arketa Cloud Run API for each watched studio/location
2. Compares new slots against `knownSlotKeys` Set (seeded at boot to avoid flood)
3. New slots are upserted into `class_schedules` and matched against Arketa `snipe_targets`
4. For each match, `SlotWatcher` inserts `booking_jobs` with `scheduled_for = NOW()`
5. `JobPoller` claims immediately (no wait)
6. `JobProcessor` → `ArketaAdapter` → Firebase auth → Arketa checkout API → result
7. Same `on_job_completed` trigger + email notification as standard flow

**Schedule Query Flow (Web):**

1. Browser fetches `/api/schedules?studio=barrys&location=9594&date=2026-03-01`
2. API route checks `class_schedules` DB first (returns immediately if data fresh)
3. If DB miss or range query, calls live API via shared client (`fetchClassesFromAPI`, `fetchXpoClassesFromAPI`, or `fetchArketaClassesFromAPI`)
4. Live results cached in-memory (5 min) and written back to `class_schedules` (fire-and-forget)

**Authentication Flow:**

1. User submits login form → `POST /api/auth/login`
2. API calls AWS Cognito `InitiateAuthCommand` (`USER_PASSWORD_AUTH`)
3. On success, sets three httpOnly cookies: `cognito_access_token`, `cognito_id_token`, `cognito_refresh_token` (30-day maxAge)
4. Subsequent API requests: `getSession()` reads `cognito_access_token` cookie and calls `GetUserCommand` to validate
5. Middleware (`web/src/middleware.ts`) checks cookie presence for protected routes; redirects to `/login` if missing

**State Management:**
- No client-side global state store. Each dashboard page fetches directly from `/api/` endpoints
- Dashboard page polls every 30s via `setInterval`
- Worker state is entirely in PostgreSQL — no in-memory job queues

## Key Abstractions

**BookingJob (Database Queue Item):**
- Purpose: Represents a single scheduled booking attempt
- Type: `packages/shared/src/types.ts` → `BookingJob`
- Key fields: `scheduled_for` (booking open time), `class_datetime` (actual class time), `status`, `attempts`, `max_attempts`
- Note: These two timestamps are distinct — `scheduled_for` is when to execute the booking, `class_datetime` is the class being booked

**SnipeTarget:**
- Purpose: User-configured rule for recurring or one-time auto-booking
- Type: `packages/shared/src/types.ts` → `SnipeTarget`
- Key fields: `target_type` (recurring/one_time), `day_of_week`, `time` (nullable for Arketa "any slot"), `preferred_spots`

**StudioConfig:**
- Purpose: Registry entry for each supported studio
- Type: `packages/shared/src/studios.ts` → `StudioConfig`
- Key fields: `platform` (routes to correct adapter), `bookingWindowDays`, `partnerId`/`serviceId`/`widgetName` (Arketa-only)
- Registry: `STUDIOS` record keyed by studio slug (e.g., `STUDIOS['barrys']`)

**Adapter Interface (informal):**
- All three adapters expose: `init()`, `bookClass(locationId, time, preferredSpots, classDate)`, `close()`
- Return: `BookingResult` (`{ success, message, spot?, screenshotPath? }`)
- No formal TypeScript interface — duck-typed by `JobProcessor`

**claim_next_job() RPC:**
- Purpose: Atomic single-row claim from the job queue
- Location: `supabase/migrations/001_rds_schema.sql` (PostgreSQL function)
- Pattern: `SELECT ... FOR UPDATE SKIP LOCKED` → update status to `claimed` → return row
- Guarantees no two workers claim the same job under concurrent load

## Entry Points

**Worker Process:**
- Location: `worker/src/index.ts`
- Triggers: `npm run worker` (via `tsx`) or compiled binary
- Responsibilities: Initialize all subsystems, manage heartbeat, handle SIGINT/SIGTERM graceful shutdown

**Next.js App:**
- Location: `web/src/app/layout.tsx` (root), `web/src/app/(dashboard)/layout.tsx` (authenticated shell)
- Triggers: Vercel deployment, `npm run web:dev`
- Responsibilities: Root layout sets dark mode and Toaster; dashboard layout validates session server-side

**API Route Base:**
- Location: `web/src/app/api/`
- Triggers: HTTP requests from browser
- Pattern: All routes call `getSession()` first; return 401 if unauthenticated

## Error Handling

**Strategy:** Log-and-continue at subsystem boundaries; retry-with-backoff at job level

**Worker Patterns:**
- `JobProcessor.handleFailure()` — resets job to `pending` for retry up to `max_attempts` (default 3); marks `failed` on final attempt
- `JobScheduler` — catches per-target errors, continues to next target; logs `[scheduler] Error processing target`
- `JobPoller` — catches uncaught errors from `onJob`, decrements `activeJobs` in `finally`
- Stale job recovery — resets `claimed` jobs stuck >30 min and `running` jobs stuck >60 min back to `pending`

**Web API Patterns:**
- Schedule route: tries DB → live API → DB fallback → empty response; never throws to client
- Auth routes: return `{ error: string }` JSON with appropriate HTTP status

## Cross-Cutting Concerns

**Logging:** `console.log` / `console.error` with prefix tags: `[scheduler]`, `[poller]`, `[processor]`, `[slot-watcher]`, `[email]`, `[job:${id}]`

**Validation:** No schema validation library. Whitelisted column sets for UPDATE routes (e.g., `ALLOWED_COLUMNS` in `web/src/app/api/targets/[id]/route.ts`). Type safety via TypeScript interfaces.

**Authentication:** AWS Cognito (`web/src/lib/cognito.ts`) for web users. No auth for worker — it runs as a trusted daemon with DB access via `DATABASE_URL`.

**Encryption:** AES-256-GCM for studio credentials (`worker/src/crypto/credentials.ts`). Web encrypts on save; worker decrypts at booking time. Both share `ENCRYPTION_KEY` env var. Separate IV and auth tag stored per field (email and password encrypted independently).

**Timezone:** Worker runs in `America/New_York`. Stealth browser context set to `America/New_York` timezone and NYC geolocation. All scheduling logic references ET.

---

*Architecture analysis: 2026-02-26*
