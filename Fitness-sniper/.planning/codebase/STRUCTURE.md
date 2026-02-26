# Codebase Structure

**Analysis Date:** 2026-02-26

## Directory Layout

```
Fitness-sniper/                  # npm workspaces monorepo root
├── worker/                      # Booking daemon (runs on Mac Mini)
│   ├── src/
│   │   ├── index.ts             # Worker entry point
│   │   ├── db.ts                # PostgreSQL pool (pg)
│   │   ├── adapters/            # Platform-specific booking adapters
│   │   │   ├── mariana-tek.ts   # Barry's, Aarmy, SLT, Practice Room
│   │   │   ├── xponential.ts    # Rumble, CycleBar, Club Pilates, etc.
│   │   │   └── arketa.ts        # Saint NYC
│   │   ├── jobs/                # Job pipeline subsystems
│   │   │   ├── scheduler.ts     # Creates booking_jobs from snipe_targets (cron)
│   │   │   ├── poller.ts        # Claims jobs from DB queue
│   │   │   ├── processor.ts     # Executes claimed jobs
│   │   │   ├── schedule-scraper.ts  # Pre-populates class_schedules table
│   │   │   ├── slot-watcher.ts  # Arketa-only real-time slot polling
│   │   │   └── arketa-slot-source.ts # Arketa Cloud Run API HTTP client
│   │   ├── scrapers/            # Schedule API clients (local copies)
│   │   │   ├── mt-api-client.ts
│   │   │   ├── xpo-api-client.ts
│   │   │   ├── arketa-api-client.ts
│   │   │   └── mt-browser-scraper.ts
│   │   ├── crypto/
│   │   │   └── credentials.ts   # AES-256-GCM encrypt/decrypt
│   │   ├── notifications/
│   │   │   └── email.ts         # Resend email notifications
│   │   └── stealth/
│   │       ├── browser.ts       # playwright-extra + stealth plugin
│   │       └── human-delay.ts   # Random delays for bot evasion
│   ├── dist/                    # Compiled output (tsc, not committed)
│   ├── package.json
│   └── tsconfig.json
├── web/                         # Next.js 16 dashboard (deployed to Vercel)
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx       # Root layout (dark mode, Toaster)
│   │   │   ├── page.tsx         # Root redirect
│   │   │   ├── globals.css      # Global styles (Tailwind v4)
│   │   │   ├── (dashboard)/     # Authenticated route group
│   │   │   │   ├── layout.tsx   # Auth guard + NavBar shell
│   │   │   │   ├── dashboard/page.tsx
│   │   │   │   ├── targets/page.tsx
│   │   │   │   ├── credentials/page.tsx
│   │   │   │   ├── history/page.tsx
│   │   │   │   └── schedule/page.tsx
│   │   │   ├── login/page.tsx
│   │   │   ├── signup/page.tsx
│   │   │   └── api/             # REST API (Next.js Route Handlers)
│   │   │       ├── auth/
│   │   │       │   ├── login/route.ts
│   │   │       │   ├── logout/route.ts
│   │   │       │   └── signup/route.ts
│   │   │       ├── targets/
│   │   │       │   ├── route.ts          # GET list, POST create
│   │   │       │   └── [id]/route.ts     # PUT update, DELETE
│   │   │       ├── credentials/route.ts  # GET, POST, DELETE
│   │   │       ├── jobs/route.ts
│   │   │       ├── history/route.ts
│   │   │       ├── schedules/route.ts    # DB-first + live API fallback
│   │   │       ├── dashboard/stats/route.ts
│   │   │       └── worker-status/route.ts
│   │   ├── components/
│   │   │   ├── ui/              # shadcn/ui primitives
│   │   │   ├── nav-bar.tsx
│   │   │   ├── targets-list.tsx
│   │   │   ├── add-target-dialog.tsx
│   │   │   ├── credential-form.tsx
│   │   │   ├── active-jobs.tsx
│   │   │   ├── worker-status.tsx
│   │   │   └── skeleton.tsx
│   │   ├── lib/
│   │   │   ├── db.ts            # pg.Pool singleton (global to survive hot reload)
│   │   │   ├── cognito.ts       # AWS Cognito auth helpers
│   │   │   ├── studios.ts       # Re-export from shared (unused — import from shared directly)
│   │   │   ├── types.ts         # Re-export from shared
│   │   │   └── utils.ts         # cn() className helper
│   │   └── middleware.ts        # Cookie-based route protection
│   ├── public/
│   ├── package.json
│   ├── next.config.ts
│   ├── eslint.config.mjs
│   └── tsconfig.json
├── packages/
│   └── shared/                  # @fitness-sniper/shared workspace
│       └── src/
│           ├── index.ts         # Barrel export
│           ├── types.ts         # All DB row types + BookingResult, ClassInfo, parseTime, formatTime12
│           ├── studios.ts       # StudioConfig, STUDIOS registry, STUDIO_LOCATIONS, LOCATION_IDS
│           └── api/
│               ├── mt-api-client.ts      # Mariana Tek HTTP schedule client
│               ├── xpo-api-client.ts     # Xponential HTTP schedule client
│               └── arketa-api-client.ts  # Arketa Cloud Run schedule client
├── supabase/
│   └── migrations/              # PostgreSQL schema (canonical + incremental)
│       ├── 001_rds_schema.sql   # Canonical schema (Cognito-based, no RLS)
│       ├── 001_initial_schema.sql  # Legacy Supabase Auth version (unused)
│       ├── 002_one_time_targets.sql
│       ├── 003_class_schedules.sql
│       ├── 004_credential_separate_iv.sql
│       ├── 005_booking_timing.sql
│       └── 006_optional_time_arketa.sql
├── archive/                     # Legacy code (reference only, not deployed)
│   └── src/adapters/            # Old adapter implementations
├── data/                        # Local data files (not committed to prod)
├── screenshots/                 # Dev/debug screenshots
├── package.json                 # Workspace root (defines workspaces array)
├── tsconfig.json                # Root tsconfig (base config)
├── CLAUDE.md                    # Project guidance for Claude Code
└── vercel.json                  # Vercel deployment config
```

## Directory Purposes

**`worker/src/adapters/`:**
- Purpose: One file per studio platform. Each adapter handles auth + booking for its platform
- Contains: Class definitions with `init()`, `bookClass()`, `close()` methods
- Key files: `mariana-tek.ts`, `xponential.ts`, `arketa.ts`
- Rule: Import extensions required — use `.js` suffix (e.g., `import { X } from './adapters/mariana-tek.js'`)

**`worker/src/jobs/`:**
- Purpose: All job pipeline logic. Each file is a distinct lifecycle subsystem
- Contains: Scheduler, poller, processor, scraper, slot-watcher, Arketa slot source
- Key files: `processor.ts` is the core — it orchestrates a full booking attempt

**`worker/src/scrapers/`:**
- Purpose: Local copies of schedule API clients. Duplicates of `packages/shared/src/api/`
- Note: The schedule scraper imports from here directly; the shared package versions are used by the web API

**`worker/src/stealth/`:**
- Purpose: Anti-bot-detection layer for Playwright-based adapter steps
- Key files: `browser.ts` (randomized UA/viewport/geolocation), `human-delay.ts` (randomized timing)

**`web/src/app/(dashboard)/`:**
- Purpose: Next.js App Router route group for authenticated pages. Parentheses in dir name mean it is not part of the URL path
- Contains: All pages a logged-in user sees, plus shared `layout.tsx` with auth guard

**`web/src/app/api/`:**
- Purpose: Next.js Route Handlers (server-side). All require `getSession()` check before any DB access
- Pattern: Each subdirectory is one resource. `route.ts` contains the HTTP method exports

**`web/src/components/ui/`:**
- Purpose: shadcn/ui component library primitives (Button, Card, Dialog, Input, etc.)
- Rule: Do not modify these files; regenerate via `shadcn` CLI if updates needed

**`web/src/lib/`:**
- Purpose: Server-side utilities for Next.js pages and API routes
- Key files: `db.ts` (pg pool singleton), `cognito.ts` (all Cognito operations)

**`packages/shared/src/`:**
- Purpose: Code shared between worker and web without a compilation step
- Rule: No build step. Next.js transpiles via `transpilePackages`. Worker imports raw `.ts` via `tsx`
- Rule: Keep free of runtime-specific APIs (no `next/headers`, no Node-only modules)

**`supabase/migrations/`:**
- Purpose: SQL migration files applied manually to the PostgreSQL (AWS RDS) instance
- Rule: `001_rds_schema.sql` is the canonical schema. Subsequent files are incremental. `001_initial_schema.sql` is superseded legacy — do not use

## Key File Locations

**Entry Points:**
- `worker/src/index.ts`: Worker daemon bootstrap
- `web/src/app/layout.tsx`: Next.js root layout
- `web/src/app/(dashboard)/layout.tsx`: Authenticated layout with session guard
- `web/src/middleware.ts`: Edge middleware for cookie-based route protection

**Configuration:**
- `package.json`: Workspace root, defines `worker`, `web`, `packages/shared` workspaces
- `worker/tsconfig.json`: Worker TypeScript config (`moduleResolution: NodeNext` — requires `.js` import extensions)
- `web/next.config.ts`: Next.js config (`transpilePackages: ['@fitness-sniper/shared']`)
- `web/eslint.config.mjs`: ESLint flat config (web only; worker has no ESLint)

**Core Logic:**
- `worker/src/jobs/processor.ts`: Central booking execution (adapter selection, credential decryption, retry logic)
- `worker/src/jobs/scheduler.ts`: Job creation cron + stale recovery
- `worker/src/jobs/slot-watcher.ts`: Arketa real-time slot detection
- `packages/shared/src/studios.ts`: Studio registry (`STUDIOS` object) — source of truth for platform routing
- `packages/shared/src/types.ts`: All shared TypeScript interfaces
- `supabase/migrations/001_rds_schema.sql`: Database schema + `claim_next_job()` RPC

**Auth:**
- `web/src/lib/cognito.ts`: All Cognito operations (`signIn`, `signUp`, `signOut`, `getSession`, cookie helpers)
- `web/src/middleware.ts`: Edge route protection (cookie presence check only — full validation in API routes)
- `worker/src/crypto/credentials.ts`: AES-256-GCM encrypt/decrypt for studio passwords

**Notifications:**
- `worker/src/notifications/email.ts`: Resend email after each booking attempt

## Naming Conventions

**Files:**
- Worker files: `kebab-case.ts` (e.g., `schedule-scraper.ts`, `slot-watcher.ts`)
- Web components: `kebab-case.tsx` (e.g., `add-target-dialog.tsx`, `worker-status.tsx`)
- Web API routes: always named `route.ts` (Next.js convention)
- Web pages: always named `page.tsx` (Next.js convention)
- Shared types: `camelCase` for interfaces, `UPPER_SNAKE_CASE` for constants

**Directories:**
- Worker subsystems: flat directory names (`adapters`, `jobs`, `scrapers`, `stealth`, `crypto`, `notifications`)
- Web: Next.js App Router conventions (`(dashboard)` route group, `[id]` dynamic segment)

**Classes:**
- Worker: PascalCase classes with descriptive names (`JobScheduler`, `JobPoller`, `JobProcessor`, `SlotWatcher`, `ScheduleScraper`)
- Adapter methods: `init()`, `bookClass()`, `close()` — consistent across all three adapters

**Imports (Worker):**
- Must use `.js` extension on all local imports: `import { X } from './file.js'` not `'./file'`
- Shared package: `import { X } from '@fitness-sniper/shared'` (no extension needed)

## Where to Add New Code

**New Studio Platform:**
1. Add config entry to `packages/shared/src/studios.ts` → `STUDIOS` object with correct `platform` value
2. Create adapter: `worker/src/adapters/{platform}.ts` implementing `init()`, `bookClass()`, `close()`
3. Add adapter instantiation case to `worker/src/jobs/processor.ts` → `process()` method
4. Add schedule API client to `packages/shared/src/api/{platform}-api-client.ts`
5. Add live API fetch case to `web/src/app/api/schedules/route.ts`
6. Add scraper case to `worker/src/jobs/schedule-scraper.ts`

**New Worker Job Subsystem:**
- Implementation: `worker/src/jobs/{name}.ts` as a class with `start()` and `stop()` methods
- Register in: `worker/src/index.ts` — instantiate, call `.start()`, add `.stop()` to `shutdown()`

**New API Endpoint:**
- Create: `web/src/app/api/{resource}/route.ts`
- Pattern: `export async function GET/POST/PUT/DELETE(request: NextRequest)`
- Always start with: `const user = await getSession(); if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });`
- Use: `query()` from `web/src/lib/db.ts` for DB access

**New Dashboard Page:**
- Create: `web/src/app/(dashboard)/{name}/page.tsx`
- Server or Client component — auth is handled by `(dashboard)/layout.tsx`
- Add nav link to: `web/src/components/nav-bar.tsx`

**New Shared Type:**
- Add to: `packages/shared/src/types.ts`
- Export from: `packages/shared/src/index.ts` (barrel)

**Database Schema Change:**
- Create: `supabase/migrations/00{N}_{description}.sql`
- Apply manually to the RDS instance
- Update corresponding TypeScript interfaces in `packages/shared/src/types.ts`

**Utility Functions:**
- Shared between worker and web: `packages/shared/src/` (ensure no runtime-specific imports)
- Web-only: `web/src/lib/utils.ts`
- Worker-only: add to the relevant subsystem file or `worker/src/` root

## Special Directories

**`archive/`:**
- Purpose: Legacy code from the original class-sniper project
- Generated: No
- Committed: Yes
- Note: Reference only. Some adapter patterns are preserved here when studio sites change DOM

**`worker/dist/`:**
- Purpose: Compiled TypeScript output from `tsc`
- Generated: Yes (by `npm run worker:build`)
- Committed: No (in `.gitignore`)

**`web/.next/`:**
- Purpose: Next.js build output
- Generated: Yes
- Committed: No

**`data/`:**
- Purpose: Local data files for development/debugging
- Generated: Mixed
- Committed: No (in `.gitignore`)

**`screenshots/`:**
- Purpose: Debug screenshots captured during development
- Generated: Yes (by Playwright during testing)
- Committed: No (development artifact)

**`.planning/`:**
- Purpose: GSD planning documents (phases, codebase analysis)
- Generated: No (written by GSD agents)
- Committed: Yes

---

*Structure analysis: 2026-02-26*
