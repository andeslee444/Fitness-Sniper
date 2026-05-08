# Coding Conventions

**Analysis Date:** 2026-02-26

## Naming Patterns

**Files:**
- Worker modules: `kebab-case.ts` — e.g., `mariana-tek.ts`, `slot-watcher.ts`, `schedule-scraper.ts`
- Web components: `kebab-case.tsx` — e.g., `add-target-dialog.tsx`, `targets-list.tsx`
- Web API routes: Next.js App Router convention — `route.ts` inside `app/api/[resource]/`
- Web pages: `page.tsx` inside `app/(dashboard)/[route]/`

**Classes:**
- PascalCase — `JobScheduler`, `JobPoller`, `JobProcessor`, `MarianaTekAdapter`, `SlotWatcher`, `ScheduleScraper`
- Always exported as named exports: `export class JobPoller { ... }`

**Functions:**
- camelCase for all functions: `sendHeartbeat()`, `getNextClassDate()`, `parseTime()`, `formatTime12()`
- Exported util functions use plain `export function` (not class methods) when stateless
- Private class methods are prefixed with `private` keyword, not underscore

**Variables and Constants:**
- camelCase for local variables: `classDate`, `scheduledFor`, `backoffMs`
- SCREAMING_SNAKE_CASE for module-level constants: `DEFAULT_BOOKING_WINDOW_DAYS`, `MT_IFRAME_CLIENT_ID`, `ALGORITHM`, `BACKOFF_STEPS`
- SCREAMING_SNAKE_CASE for exported config objects: `STUDIOS`, `STUDIO_LOCATIONS`, `LOCATION_IDS`, `SPOT_PREFERENCES`

**Interfaces and Types:**
- PascalCase — `SnipeTarget`, `BookingJob`, `StudioConfig`, `EncryptedData`, `PollerOptions`
- DB row types use snake_case property names matching the database schema directly
- Adapter-facing types use camelCase property names: `ClassInfo`, `BookingResult`

**Database slug values:**
- lowercase kebab-case strings: `'barrys'`, `'club-pilates'`, `'mariana-tek'`

## Code Style

**Formatting:**
- 2-space indentation (consistent across all files)
- Single quotes for strings in TypeScript/TSX
- Trailing commas in multi-line arrays and objects
- Semicolons at end of statements

**Linting:**
- Web (`web/`): ESLint 9 flat config with `eslint-config-next/core-web-vitals` and `eslint-config-next/typescript`
- Config: `web/eslint.config.mjs`
- Worker: no ESLint configured — TypeScript compiler (`strict: true`) is the only static check

**TypeScript:**
- Strict mode enabled in both worker and web (`"strict": true`)
- Worker uses `"module": "NodeNext"` — imports MUST include `.js` extensions:
  ```ts
  import { JobPoller } from './jobs/poller.js';   // correct
  import { JobPoller } from './jobs/poller';       // fails at runtime
  ```
- Web uses `"moduleResolution": "bundler"` — no `.js` extension needed in web imports
- `@/*` path alias in web maps to `web/src/*`
- Generic DB query function: `query<T extends pg.QueryResultRow>(text, params)`

## Import Organization

**Worker imports — consistent order observed:**
1. Node built-ins: `import crypto from 'node:crypto'`
2. External npm packages: `import cron from 'node-cron'`
3. Shared workspace: `import { STUDIOS } from '@fitness-sniper/shared'`
4. Internal relative (with `.js` extension): `import { query } from '../db.js'`
5. Type-only imports last: `import type { BookingJob } from '@fitness-sniper/shared'`

**Web imports — consistent order observed:**
1. Framework: `import { NextRequest, NextResponse } from 'next/server'`
2. Internal lib aliases: `import { getSession } from '@/lib/cognito'`
3. External packages: `import { z } from 'zod'`
4. Shared workspace: `import { STUDIOS } from '@fitness-sniper/shared'`
5. Type imports: `import type { TargetWithJob } from '@/lib/types'`

**Shared package:**
- No barrel re-exports from `packages/shared/src/index.ts` beyond what's there
- Consumed as raw TypeScript (no build step) — Next.js transpiles via `transpilePackages`

## Error Handling

**Worker pattern — try/catch with explicit message extraction:**
```ts
} catch (err) {
  const message = err instanceof Error ? err.message : String(err);
  console.error(`[module] Context:`, message);
}
```

**Worker — fire-and-forget non-critical operations:**
```ts
await adapter.close().catch(() => {});  // silently ignore cleanup errors
```

**API routes — early return on unauthorized:**
```ts
const user = await getSession();
if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
```

**API routes — Zod validation before DB operations:**
```ts
const parsed = targetSchema.safeParse(body);
if (!parsed.success) {
  const firstError = parsed.error.issues[0]?.message || 'Invalid input';
  return NextResponse.json({ error: firstError }, { status: 400 });
}
```

**Custom error classes for domain errors:**
```ts
export class InsufficientCreditsError extends Error {
  public readonly studioName: string;
  constructor(studioName: string, ...) {
    super(msg);
    this.name = 'InsufficientCreditsError';
  }
}
```
- Always set `this.name` in custom errors
- Catch and re-surface with `instanceof` checks

**DB failures in non-critical paths — swallow with comment:**
```ts
} catch {
  // Non-critical — scheduler will pick it up on next scan
}
```

## Logging

**Pattern — bracketed module tag prefix on all logs:**
```ts
console.log(`[scheduler] Found ${targets.length} enabled targets`);
console.error(`[processor] Job ${job.id} error:`, message);
console.warn(`[scheduler] Unknown studio '${target.studio_slug}'`);
```

**Tag format:** `[module-name]` or `[module:subcontext]` for job-level detail:
```ts
const logFn = (step: string, detail: string) => {
  console.log(`[job:${job.id}] [${step}] ${detail}`);
};
```

**No structured logging library** — plain `console.log/error/warn` throughout.

**Log levels used:**
- `console.log` — normal operational events (job created, adapter step, heartbeat)
- `console.warn` — recoverable issues (unknown studio slug)
- `console.error` — actual failures (job error, DB failure, API error)

## Comments

**File-level JSDoc block at top of every worker module:**
```ts
/**
 * Job Scheduler — creates booking_jobs from snipe_targets
 *
 * Runs on cron (every 15 min): scans all enabled targets...
 */
```

**Inline section dividers with visual separators:**
```ts
// ============================================================
// Config
// ============================================================
```

**Inline rationale comments for non-obvious logic:**
```ts
// Use class_datetime (not scheduled_for) for dedup since scheduled_for is now booking open time
// Postgres may return a Date object instead of a string
// Drop URL template placeholders like {location}
```

**JSDoc on exported utility functions:**
```ts
/**
 * Parse "H:MM AM/PM" into { hours24, minutes }.
 * Returns null if the string doesn't match.
 */
export function parseTime(time: string): { hours24: number; minutes: number } | null {
```

**React components:** No JSDoc — inline comments for conditional rendering sections only.

## Function Design

**Size:** Worker classes have focused methods (10-30 lines typical); `bookClass()` in adapters is the longest at ~120 lines.

**Parameters:** Options objects for optional config (never long positional parameter lists):
```ts
constructor(
  studioSlug: string,
  credentials: StudioCredentials,
  opts: { log?: StepLogger; screenshotDir?: string } = {},
)
```

**Return Values:**
- Async operations return `Promise<void>` or `Promise<T>` (never mixed sync/async)
- DB queries return typed results: `Promise<pg.QueryResult<T>>`
- Booking results always return structured `BookingResult` (`success`, `message`, optional `spot`)
- Null returned for "not found" cases; never throwing for expected-null states

## Module Design

**Worker — class-based with `start()` / `stop()` lifecycle:**
```ts
export class JobScheduler {
  start(): void { ... }
  stop(): void { ... }
  private async scan(): Promise<void> { ... }
}
```

**Web API routes — named export HTTP handlers:**
```ts
export async function GET() { ... }
export async function POST(request: NextRequest) { ... }
export async function PUT(request: NextRequest, { params }) { ... }
export async function DELETE(...) { ... }
```

**Shared package — pure exported functions and `interface`/`type` definitions only (no classes).

**Singleton pattern for expensive resources:**
```ts
// DB pool (web/src/lib/db.ts) — prevents hot-reload exhaustion
const globalForPg = globalThis as unknown as { pgPool?: pg.Pool };
export const pool = globalForPg.pgPool ?? new Pool({ ... });
if (process.env.NODE_ENV !== 'production') {
  globalForPg.pgPool = pool;
}

// Resend client (worker/src/notifications/email.ts) — lazy init
let resend: Resend | null = null;
function getResend(): Resend { ... }
```

**No barrel re-export pattern in web** — components import directly from source files.

## React Component Conventions

**File structure:** `'use client'` directive at very top for interactive components; omit for server components.

**State management:** Local `useState` + `useEffect` — no global state library.

**Data fetching pattern:** Server components fetch via DB query through API route; client components use `fetch()` inside `useEffect` with `AbortController` for cleanup:
```ts
useEffect(() => {
  const controller = new AbortController();
  fetch(`/api/schedules?${params}`, { signal: controller.signal })
    .then(...)
    .catch((err) => {
      if (err instanceof DOMException && err.name === 'AbortError') return;
      ...
    });
  return () => controller.abort();
}, [deps]);
```

**Toast notifications:** `toast.success()` / `toast.error()` from `sonner` for all user-facing feedback. Never `alert()`.

**Form submission pattern:**
```ts
async function handleSubmit(e: React.FormEvent) {
  e.preventDefault();
  setLoading(true);
  try {
    const res = await fetch('/api/...', { method: 'POST', ... });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || 'Failed');
    }
    toast.success('Done');
    router.refresh();
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'Failed');
  } finally {
    setLoading(false);
  }
}
```

**Navigation refresh:** `router.refresh()` (App Router) after mutations — never full page reload.

---

*Convention analysis: 2026-02-26*
