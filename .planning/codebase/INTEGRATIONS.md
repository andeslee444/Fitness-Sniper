# External Integrations

**Analysis Date:** 2026-02-26

## APIs & External Services

**Mariana Tek (MT) - Primary Studio Platform:**
- Studios: Barry's Bootcamp, Aarmy, SLT, Practice Room
- API base: `https://{tenant}.marianatek.com/api/customer/v1/`
- Auth: OAuth PKCE flow. All iframe studios share client_id `sbLziNCoF5HcOhkSV6zRL8O7betwd3mDDIQbWZa3`
- Booking: `POST /me/reservations { class_session, spot, reservation_type }`
- Schedule: `GET /classes?min_start_date=...&max_start_date=...&location=...&region=...`
- HTTP-only auth works (no browser needed): CSRF → POST login → follow redirects → token exchange
- Browser fallback via `worker/src/stealth/browser.ts` if HTTP auth fails
- Adapter: `worker/src/adapters/mariana-tek.ts`
- Shared HTTP client: `packages/shared/src/api/mt-api-client.ts`
- No env var required; all communication is per-user credentials

**Xponential Fitness (ClubReady) - Secondary Studio Platform:**
- Studios: Rumble, CycleBar, Club Pilates, YogaSix, StretchLab, Pure Barre
- API base: `https://members.{brand}.com/api/` (each brand has its own subdomain)
- Auth: `POST /api/xpass/sessions` → JWT returned in `X-Authorization: Bearer {token}` header
- Schedule: `GET /api/v2/locations/{slug}/schedule_entries` (public, no auth)
- Booking: `POST /api/v2/locations/{slug}/bookings/{entry_id}` (auth required)
- API-only, no browser fallback
- Adapter: `worker/src/adapters/xponential.ts`
- Shared HTTP client: `packages/shared/src/api/xpo-api-client.ts`

**Arketa - Saint NYC Platform:**
- Studio: Saint NYC (private sauna/ice bath appointments)
- Booking API: `https://app.arketa.co/api/app/checkout?classId={id}` (auth required)
- Widget data API: `https://app.arketa.co/api/widget/data?widgetName={name}&type=classes&start_time={unix}` (public)
- Schedule polling API (Cloud Run): `https://widget-api-tkaeguucxq-uc.a.run.app` (public)
  - `GET /{partnerId}/services/{serviceId}/availableDays?startDate=...&endDate=...`
  - `GET /{partnerId}/services/{serviceId}/availableTimes?date=...`
  - Critical constraint: `availableDays` requires `startDate`/`endDate` in the same calendar month
- partnerId: `wdTh7EBQYGU9Ian0S68coANGqQG3`, serviceId: `Tukn5jgFtZDpbl1mMQPY` (in `packages/shared/src/studios.ts`)
- Adapter: `worker/src/adapters/arketa.ts`
- Shared HTTP client: `packages/shared/src/api/arketa-api-client.ts`
- Scraper client: `worker/src/scrapers/arketa-api-client.ts`
- Slot watcher: `worker/src/jobs/slot-watcher.ts` (polls every 60s)

**Firebase (Identity Toolkit) - Arketa Authentication:**
- Service: Google Firebase Identity Toolkit REST API
- URL: `https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}`
- Firebase API key (public client key): `AIzaSyCNSSHH1yTQ492d42qWOG_V_m2uQGdQF74` (hardcoded in `worker/src/adapters/arketa.ts` — this is a public browser key, not a secret)
- Auth flow: `signInWithPassword` → `idToken` → used as `Authorization: Bearer {idToken}` for Arketa checkout
- No Firebase SDK; pure REST calls via `fetch`

## Data Storage

**Databases:**
- PostgreSQL (AWS RDS or compatible)
  - Connection env var: `DATABASE_URL` (both worker and web use the same DB)
  - Client: `pg` (node-postgres) direct pool, no ORM
  - Worker client: `worker/src/db.ts` — pool with max 10 connections, SSL auto-detected
  - Web client: `web/src/lib/db.ts` — global singleton to prevent pool exhaustion on hot reload
  - SSL: auto-disabled for localhost, enabled (without cert verification) for remote hosts

**Schema:**
- 7 migration files in `supabase/migrations/`
- Canonical schema: `supabase/migrations/001_rds_schema.sql` (Cognito-based, `user_id` is `text`)
- Legacy: `supabase/migrations/001_initial_schema.sql` (Supabase Auth — unused)
- Tables: `profiles`, `studio_credentials`, `snipe_targets`, `booking_jobs`, `booking_history`, `worker_heartbeats`, `class_schedules`, `scrape_runs`
- Key RPC: `claim_next_job(p_worker_id)` — atomic job claim with `FOR UPDATE SKIP LOCKED`
- Triggers: `on_job_completed()` — auto-inserts `booking_history` when job status reaches `success`/`failed`

**File Storage:**
- Local filesystem only — no cloud file storage (S3, GCS, etc.)
- Screenshots saved locally during worker debug sessions

**Caching:**
- None (no Redis, Memcached, etc.)
- Web API `schedules/` route uses a 5-minute in-memory cache (request-level, not persistent)

## Authentication & Identity

**Auth Provider:**
- AWS Cognito (not Supabase Auth)
- Config: `web/src/lib/cognito.ts`
- Region: `AWS_REGION` env var (defaults to `us-east-2`)
- Auth flow: `USER_PASSWORD_AUTH`
- Signup: auto-confirmed via `AdminConfirmSignUpCommand` (no email verification)
- Session storage: three httpOnly cookies — `cognito_access_token`, `cognito_id_token`, `cognito_refresh_token`
  - MaxAge: 30 days (`60 * 60 * 24 * 30`)
- Session validation: calls `GetUserCommand` on every protected API route via `getSession()` in `web/src/lib/cognito.ts`
- Middleware route guard: `web/src/middleware.ts` — checks `cognito_access_token` cookie; redirects to `/login` if absent

**Required Cognito Env Vars (Web):**
- `AWS_REGION`
- `COGNITO_CLIENT_ID`
- `COGNITO_CLIENT_SECRET`
- `COGNITO_USER_POOL_ID`

**Studio Credentials (User-Provided):**
- Per-studio email/password encrypted with AES-256-GCM before DB storage
- Encryption: `worker/src/crypto/credentials.ts`
- Key: `ENCRYPTION_KEY` (64-char hex = 32 bytes)
- Separate columns: `password_iv`, `password_auth_tag`, `encrypted_password` (added in migration 004)
- Both web and worker must share the same `ENCRYPTION_KEY`

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry, Datadog, etc.)

**Logs:**
- `console.log` / `console.error` throughout worker and web
- Worker uses structured log prefixes: `[heartbeat]`, `[scheduler]`, `[poller]`, `[processor]`, `[auth]`, `[book]`, etc.

**Worker Health:**
- Heartbeat: every 30s, upserts into `worker_heartbeats` table with `pid`, `memory`, `uptime`, `active_jobs`
- Dashboard reads `worker_heartbeats` via `web/src/app/api/worker-status/` route

## CI/CD & Deployment

**Hosting (Web):**
- Vercel (configured via `vercel.json`)
- Auto-deploy on git push to main branch
- Build: `cd web && next build`

**Hosting (Worker):**
- Mac Mini (local daemon, not cloud-hosted)
- Started manually: `npm run worker` (dev) or `node dist/index.js` (prod)
- No containerization or auto-restart configured in codebase (would need external process manager like PM2 or launchd)

**CI Pipeline:**
- None (no GitHub Actions, CircleCI, etc.)

## Notifications

**Email:**
- Provider: Resend (`resend ^4.1.2`)
- From address: `noreply@fitnesssniper.app`
- Triggered: on booking success or failure after job completion
- Implementation: `worker/src/notifications/email.ts`
- Env var: `RESEND_API_KEY`

## Webhooks & Callbacks

**Incoming:**
- None (no webhook endpoints)

**Outgoing:**
- None (no outgoing webhooks; email is the only notification mechanism)

## Environment Configuration

**Worker (`worker/.env`) Required Vars:**
- `DATABASE_URL` — PostgreSQL connection string
- `ENCRYPTION_KEY` — 64-char hex (32 bytes) for AES-256-GCM
- `RESEND_API_KEY` — Resend email API key
- `WORKER_ID` — Unique worker identifier (defaults to `worker-{timestamp}`)

**Web (`web/.env.local`) Required Vars:**
- `DATABASE_URL` — Same PostgreSQL connection string as worker
- `ENCRYPTION_KEY` — Same 32-byte key as worker (web encrypts, worker decrypts)
- `AWS_REGION` — Cognito region (e.g., `us-east-2`)
- `COGNITO_CLIENT_ID` — Cognito app client ID
- `COGNITO_CLIENT_SECRET` — Cognito app client secret
- `COGNITO_USER_POOL_ID` — Cognito user pool ID

**Secrets Location:**
- `worker/.env` (gitignored)
- `web/.env.local` (gitignored)
- Example files: `worker/.env.example`, `web/.env.local.example`

---

*Integration audit: 2026-02-26*
