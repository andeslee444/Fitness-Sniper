# Phase 2: Data Foundation - Research

**Researched:** 2026-02-27
**Domain:** TanStack Query v5, Next.js App Router provider setup, PostgreSQL UNION calendar query
**Confidence:** HIGH

## Summary

Phase 2 has two independent workstreams. The first replaces three independent `setInterval` polling loops (in `dashboard/page.tsx`, `active-jobs.tsx`, and `worker-status.tsx`) with TanStack Query `useQuery` hooks using `refetchInterval`. The second builds a new `GET /api/calendar` route that returns a merged weekly event list from `booking_history`, `booking_jobs`, and `snipe_targets` via a PostgreSQL `UNION ALL` query.

TanStack Query v5 (`@tanstack/react-query@^5`) is confirmed compatible with React 19.2.3 (`peerDependencies: "react": "^18 || ^19"`) and Next.js 16 App Router. The provider setup requires a `'use client'` wrapper component using `useState` to initialize `QueryClient` once — this prevents a new client being created on each render. The tab-visibility behavior is automatic: `refetchIntervalInBackground` defaults to `false`, so all polling queries pause on `visibilitychange` and resume when the tab becomes active with no additional configuration.

The `/api/calendar` route requires a `UNION ALL` across three tables (booking_history, booking_jobs, snipe_targets), each shaped to produce the same output columns: `event_date`, `event_time`, `studio_slug`, `event_type` ('booked'|'failed'|'pending'|'configured'), and `meta` (JSON). The PostgreSQL date range filter is `class_date >= $weekStart AND class_date < $weekStart + INTERVAL '7 days'`. Snipe targets require computed date expansion in SQL (recurring targets need day-of-week matching against the 7-day window; one-time targets match on `target_date`).

**Primary recommendation:** Install TanStack Query, create a single `QueryClientProvider` wrapper, replace all three `setInterval` hooks with `useQuery`, then build the `/api/calendar` route. These are fully independent and can be planned as two separate plans.

<phase_requirements>
## Phase Requirements

Phase 2 has no direct requirements but enables the following:

| Enables | Behavior | How This Phase Enables It |
|---------|----------|--------------------------|
| CAL-01 | Weekly calendar showing confirmed bookings, pending snipes, and failures | `/api/calendar` UNION provides the merged weekly data Phase 3 calendar UI will render |
| CAL-02 | Color-coded calendar events by status | Calendar API includes `event_type` field encoding status for color mapping |
| CAL-03 | Availability heatmap overlay | Calendar API includes slot data needed for heatmap computation |
| TRUST-01 | Status timeline per snipe target | TanStack Query cache enables real-time status refresh without polling race conditions |
| TRUST-02 | Countdown to booking window | TanStack Query `refetchInterval` keeps booking_opens_at data fresh |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@tanstack/react-query` | `^5` (currently 5.90.21) | Server state management, query deduplication, caching, polling | Industry standard for React async state — replaces manual setInterval/useState fetch patterns |
| `@tanstack/react-query-devtools` | `^5` (matches core) | Dev-only query inspector | Official devtools — zero-config browser panel for inspecting cache |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `queryOptions` helper | Built into `@tanstack/react-query` v5 | Type-safe query definition objects reusable across useQuery, prefetchQuery, setQueryData | Use when the same query key/fn is referenced in multiple places |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| TanStack Query | SWR | TanStack Query has richer devtools, better `refetchInterval`/visibility control, and is already the project-decided choice per STATE.md |
| TanStack Query | SSE/WebSockets | SSE/WebSockets incompatible with Vercel Hobby 10s timeout — per STATE.md, polling is the chosen approach |
| `refetchInterval` | `setInterval` manually | `setInterval` doesn't deduplicate requests, doesn't pause on tab hide, leaks memory on unmount. TanStack Query handles all of this. |

**Installation:**
```bash
npm install @tanstack/react-query @tanstack/react-query-devtools --workspace=web
```

Note: No `--legacy-peer-deps` flag needed — TanStack Query v5 declares `"react": "^18 || ^19"` as a peer dependency, which is compatible with this project's React 19.2.3.

---

## Architecture Patterns

### New Files Needed
```
web/src/
├── lib/
│   └── query-client.ts          # QueryClient singleton factory
├── components/
│   └── providers.tsx            # 'use client' QueryClientProvider wrapper
└── app/api/
    └── calendar/
        └── route.ts             # GET /api/calendar?weekStart=YYYY-MM-DD
```

### Modified Files
```
web/src/
├── app/layout.tsx               # Wrap <body> content with <Providers>
├── app/(dashboard)/dashboard/page.tsx    # Replace setInterval with useQuery
├── components/active-jobs.tsx            # Replace setInterval with useQuery
└── components/worker-status.tsx          # Replace setInterval with useQuery
```

### Pattern 1: QueryClient Provider Setup

**What:** A `'use client'` wrapper component that creates a single `QueryClient` instance using `useState` and wraps children in `QueryClientProvider`.

**Why `useState` and not module-level singleton:** In Next.js App Router, module-level singletons can be shared across server renders (in React Server Components context). `useState` with a factory function guarantees one client per component instance, which is exactly one per app render on the client. This is the pattern used in the [official TanStack Next.js example](https://tanstack.com/query/v5/docs/framework/react/examples/nextjs).

**Example:**
```typescript
// Source: TanStack Query v5 official Next.js App Router pattern
// web/src/lib/query-client.ts
import { QueryClient } from '@tanstack/react-query';

export function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // Data considered fresh for 30s — prevents redundant refetches
        // when multiple components mount with the same query key
        staleTime: 30 * 1000,
        // Don't retry on 4xx errors (auth failures, not-found)
        // retry: false would suppress all retries; default (3) is fine for 5xx
      },
    },
  });
}
```

```typescript
// web/src/components/providers.tsx
'use client';

import { useState } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { makeQueryClient } from '@/lib/query-client';

export function Providers({ children }: { children: React.ReactNode }) {
  // useState with factory ensures one QueryClient per app instance
  // NOT useState(makeQueryClient()) — that runs makeQueryClient on every render
  const [queryClient] = useState(() => makeQueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {/* DevTools only loads in development (tree-shaken in production) */}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
```

```typescript
// web/src/app/layout.tsx — add Providers wrapper
import { Providers } from '@/components/providers';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body suppressHydrationWarning className="...">
        <a href="#main-content" className="skip-to-content">Skip to content</a>
        <Providers>
          <div id="main-content">{children}</div>
          <Toaster />
        </Providers>
      </body>
    </html>
  );
}
```

### Pattern 2: Query Key Constants

**What:** A central `QUERY_KEYS` object defining all query keys as tuples. This enables cache invalidation (`queryClient.invalidateQueries`) to be type-safe and avoids key string duplication.

**Example:**
```typescript
// web/src/lib/query-keys.ts
// Source: TanStack Query v5 queryOptions pattern
export const QUERY_KEYS = {
  dashboardStats: ['dashboard', 'stats'] as const,
  workerStatus: ['worker', 'status'] as const,
  jobs: ['jobs'] as const,
  calendarWeek: (weekStart: string) => ['calendar', weekStart] as const,
  targets: ['targets'] as const,
  history: (page: number) => ['history', page] as const,
  schedules: (studioSlug: string, locationId: string) =>
    ['schedules', studioSlug, locationId] as const,
} as const;
```

### Pattern 3: Migrating setInterval to useQuery

**What:** Replace the three existing manual polling loops with `useQuery` + `refetchInterval`. Tab-visibility pausing is automatic (default behavior, no configuration needed).

**Current pattern (all three components):**
```typescript
// CURRENT — manual polling with memory leak risk
useEffect(() => {
  fetchStats();
  const interval = setInterval(fetchStats, POLL_INTERVAL);
  return () => clearInterval(interval);
}, [fetchStats]);
```

**Replacement pattern:**
```typescript
// Source: TanStack Query v5 useQuery docs
// REPLACEMENT — declarative polling that auto-pauses on tab hide
const { data: stats, isLoading } = useQuery({
  queryKey: QUERY_KEYS.dashboardStats,
  queryFn: () => fetch('/api/dashboard/stats').then(r => {
    if (!r.ok) throw new Error('Failed to fetch stats');
    return r.json() as Promise<DashboardStats>;
  }),
  refetchInterval: 30_000,          // 30s — matches existing POLL_INTERVAL
  refetchIntervalInBackground: false, // DEFAULT — pauses when tab inactive
  staleTime: 10_000,                // 10s fresh window
});
```

**Tab-visibility behavior (verified):**
- `refetchIntervalInBackground: false` (default) — polling pauses on `visibilitychange` when tab is hidden
- Polling automatically resumes when the tab becomes active again
- No custom event listeners or visibility API calls needed

**The three migrations:**

| Component | Current interval | queryKey | New refetchInterval |
|-----------|-----------------|----------|---------------------|
| `dashboard/page.tsx` | 30,000ms | `QUERY_KEYS.dashboardStats` | `30_000` |
| `active-jobs.tsx` | 15,000ms | `QUERY_KEYS.jobs` | `15_000` |
| `worker-status.tsx` | 30,000ms | `QUERY_KEYS.workerStatus` | `30_000` |

**Loading state:** Replace `loading` boolean with `isLoading` from `useQuery`. `isLoading` is `true` only on the first fetch (no cached data). Subsequent refetches do NOT set `isLoading: true` — they use `isFetching`. This matches the existing skeleton behavior precisely.

**Initial data:** `active-jobs.tsx` currently receives `initialJobs` as a prop and uses `useState(initialJobs)`. After migration, the parent no longer passes jobs — `ActiveJobs` fetches its own data via `useQuery`. Remove the prop.

### Pattern 4: /api/calendar UNION Query

**What:** A single SQL `UNION ALL` across three tables that returns merged weekly calendar events.

**Query parameter:** `weekStart=YYYY-MM-DD` (Monday of the target week, or any date — API computes the 7-day window)

**Output shape per event:**
```typescript
interface CalendarEvent {
  id: string;           // from source table
  event_date: string;   // "YYYY-MM-DD"
  event_time: string | null;  // "H:MM AM" — null for Arketa any-slot targets
  studio_slug: string;
  event_type: 'booked' | 'failed' | 'pending' | 'configured';
  source: 'history' | 'job' | 'target';
  meta: {
    // From booking_history:
    spot?: string | null;
    message?: string | null;
    // From booking_jobs:
    scheduled_for?: string;    // booking attempt time
    class_datetime?: string;   // actual class time
    job_status?: string;
    // From snipe_targets:
    target_type?: string;
    day_of_week?: number | null;
  };
}
```

**PostgreSQL UNION query pattern:**
```sql
-- Source: PostgreSQL docs, direct schema analysis
-- GET /api/calendar?weekStart=YYYY-MM-DD
-- Returns merged events for the 7-day window starting at weekStart

WITH week_bounds AS (
  SELECT
    $2::date AS week_start,
    $2::date + INTERVAL '7 days' AS week_end
)
SELECT
  id::text,
  class_date::text         AS event_date,
  class_time               AS event_time,
  studio_slug,
  CASE status
    WHEN 'booked' THEN 'booked'
    ELSE 'failed'
  END                      AS event_type,
  'history'                AS source,
  jsonb_build_object(
    'spot', spot,
    'message', message
  )                        AS meta
FROM booking_history, week_bounds
WHERE user_id = $1
  AND class_date >= week_start
  AND class_date < week_end

UNION ALL

SELECT
  id::text,
  COALESCE(
    (class_datetime AT TIME ZONE 'America/New_York')::date,
    (scheduled_for AT TIME ZONE 'America/New_York')::date
  )::text                  AS event_date,
  to_char(
    COALESCE(class_datetime, scheduled_for) AT TIME ZONE 'America/New_York',
    'FMHH12:MI AM'
  )                        AS event_time,
  (SELECT studio_slug FROM snipe_targets t WHERE t.id = booking_jobs.target_id) AS studio_slug,
  'pending'                AS event_type,
  'job'                    AS source,
  jsonb_build_object(
    'scheduled_for', scheduled_for,
    'class_datetime', class_datetime,
    'job_status', status
  )                        AS meta
FROM booking_jobs, week_bounds
WHERE user_id = $1
  AND status IN ('pending', 'claimed', 'running')
  AND COALESCE(
    (class_datetime AT TIME ZONE 'America/New_York')::date,
    (scheduled_for AT TIME ZONE 'America/New_York')::date
  ) >= week_start
  AND COALESCE(
    (class_datetime AT TIME ZONE 'America/New_York')::date,
    (scheduled_for AT TIME ZONE 'America/New_York')::date
  ) < week_end

UNION ALL

-- Recurring targets: expand day_of_week into the 7-day window
SELECT
  id::text,
  (week_start + (
    (day_of_week - EXTRACT(DOW FROM week_start)::int + 7) % 7
  ) * INTERVAL '1 day')::date::text AS event_date,
  time                     AS event_time,
  studio_slug,
  'configured'             AS event_type,
  'target'                 AS source,
  jsonb_build_object(
    'target_type', target_type,
    'day_of_week', day_of_week
  )                        AS meta
FROM snipe_targets, week_bounds
WHERE user_id = $1
  AND enabled = true
  AND target_type = 'recurring'
  AND day_of_week IS NOT NULL

UNION ALL

-- One-time targets: match directly on target_date
SELECT
  id::text,
  target_date::text        AS event_date,
  time                     AS event_time,
  studio_slug,
  'configured'             AS event_type,
  'target'                 AS source,
  jsonb_build_object(
    'target_type', target_type
  )                        AS meta
FROM snipe_targets, week_bounds
WHERE user_id = $1
  AND enabled = true
  AND target_type = 'one_time'
  AND target_date >= week_start
  AND target_date < week_end

ORDER BY event_date, event_time NULLS LAST;
```

**Route signature:**
```typescript
// web/src/app/api/calendar/route.ts
// GET /api/calendar?weekStart=YYYY-MM-DD
export async function GET(request: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const { searchParams } = new URL(request.url);
  const weekStart = searchParams.get('weekStart');

  // Validate weekStart is a valid YYYY-MM-DD date
  if (!weekStart || !/^\d{4}-\d{2}-\d{2}$/.test(weekStart)) {
    return NextResponse.json({ error: 'weekStart must be YYYY-MM-DD' }, { status: 400 });
  }

  try {
    const { rows } = await query<CalendarEvent>(CALENDAR_UNION_SQL, [user.sub, weekStart]);
    return NextResponse.json(rows);
  } catch (err) {
    console.error('[calendar] GET error:', err);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
```

### Anti-Patterns to Avoid

- **Module-level `new QueryClient()`:** A module-level singleton for QueryClient leaks cache across server renders in Next.js. Always use `useState(() => makeQueryClient())` in the provider component.
- **`useState(makeQueryClient())`** (without arrow function): This calls `makeQueryClient()` on every render, creating a new client each time. Use the lazy initializer: `useState(() => makeQueryClient())`.
- **`refetchIntervalInBackground: true`:** Unnecessary for this use case and wastes network requests when users leave the tab. Leave it at the default `false`.
- **`staleTime: 0`** (default): With the default staleTime, queries are considered stale immediately, causing extra refetches when components remount. Set `staleTime: 30_000` globally and tune per-query as needed.
- **Keeping `activeJobs` prop on `<ActiveJobs>`:** After migration, `ActiveJobs` owns its own data fetch. The parent component should not also fetch jobs and pass them down — this creates two sources of truth.
- **UNION with UNION (dedup):** Use `UNION ALL` not `UNION` for the calendar query. Deduplication across history/jobs/targets is logically impossible (different tables, different row types) and `UNION` adds expensive sort/dedup overhead with no benefit.
- **Subquery for `studio_slug` in booking_jobs branch:** The JOIN in the jobs branch above uses a subquery per row to get `studio_slug`. For performance, use a `LEFT JOIN snipe_targets` instead:
  ```sql
  FROM booking_jobs bj
  LEFT JOIN snipe_targets t ON t.id = bj.target_id
  ```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Request deduplication | Custom cache layer / ref tracking | TanStack Query `useQuery` | Multiple components mounting with the same queryKey share one in-flight request automatically |
| Tab visibility polling pause | `document.addEventListener('visibilitychange', ...)` | `useQuery` with `refetchIntervalInBackground: false` (default) | Built-in behavior, no listener setup/teardown |
| Stale-while-revalidate | `useRef` + expiry check | `staleTime` option on `useQuery` | Background refresh while showing cached data — core feature of TanStack Query |
| Loading skeleton vs. refetch spinner | Two separate boolean states | `isLoading` vs `isFetching` from `useQuery` | `isLoading` = no cache yet; `isFetching` = background refresh in progress |
| Query key collisions | String concatenation | Typed array-based query keys + `QUERY_KEYS` constants | Array keys are serialized by TanStack Query; constants prevent typos |

**Key insight:** Every manual polling pattern (`setInterval` + `useState` + `useEffect`) that exists in this codebase is a subtly buggy reimplementation of what TanStack Query provides: deduplication, background refresh, tab-visibility pause, stale-while-revalidate, loading states, and memory-safe cleanup.

---

## Common Pitfalls

### Pitfall 1: QueryClient Recreation on Every Render
**What goes wrong:** Provider re-renders reset the entire query cache — all cached data is lost.
**Why it happens:** Using `new QueryClient()` directly in JSX or `useState(new QueryClient())` (eager) creates a new instance on every render.
**How to avoid:** Always use lazy initializer: `const [queryClient] = useState(() => makeQueryClient())`.
**Warning signs:** Infinite loading states, queries refetching on every navigation, DevTools showing cache being cleared on every render.

### Pitfall 2: Missing try/catch in queryFn
**What goes wrong:** If `fetch()` rejects or `res.json()` throws, TanStack Query catches it and sets `status: 'error'` — but only if the error propagates. If you swallow it with `catch { return undefined }`, TanStack Query sees a successful query with `undefined` data.
**Why it happens:** Copy-paste from existing `fetchStats` which wraps in `try/catch` and sets nothing on failure.
**How to avoid:** In `queryFn`, always throw or let errors propagate:
```typescript
queryFn: async () => {
  const res = await fetch('/api/dashboard/stats');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
},
```
**Warning signs:** Query shows `success` state but `data` is `undefined`.

### Pitfall 3: `isLoading` vs `isFetching` Confusion
**What goes wrong:** Using `isFetching` to gate the loading skeleton causes a flash on every background refetch — users see the skeleton every 30 seconds.
**Why it happens:** `isFetching` is `true` during background refetches too. `isLoading` is only `true` when there is no cached data (first fetch or stale eviction).
**How to avoid:** Show skeleton on `isLoading` only. Optionally show a small spinner or `isFetching && !isLoading` indicator for background activity.
**Warning signs:** Loading skeleton flickers on every poll interval.

### Pitfall 4: CalendarEvent Deduplication Between Tables
**What goes wrong:** A class that was booked shows up twice — once as `type: 'configured'` (from snipe_targets) and once as `type: 'booked'` (from booking_history). The Phase 3 calendar UI may render both.
**Why it happens:** `UNION ALL` returns all rows from all branches. The configured target is not automatically excluded when a booking exists.
**How to avoid:** Two options: (A) filter out `configured` targets that have a matching `booking_history` record for the same date (LEFT JOIN + WHERE history.id IS NULL), or (B) let the API return all rows and handle deduplication/priority in the Phase 3 calendar component (prefer 'booked' > 'pending' > 'configured' for the same studio+date+time). Option B is simpler for Phase 2 and defers the priority logic to Phase 3 where the UI requirements are clearer.
**Warning signs:** Calendar shows double events for successfully booked classes.

### Pitfall 5: Recurring Target Day-of-Week Math
**What goes wrong:** The SQL day-of-week expansion for recurring targets produces dates outside the 7-day window or produces negative offsets.
**Why it happens:** `EXTRACT(DOW FROM date)` returns 0=Sunday, 1=Monday...6=Saturday — same as JS `getDay()`. `snipe_targets.day_of_week` uses the same convention. The modulo formula `(target_dow - week_start_dow + 7) % 7` is correct but must be applied as integer arithmetic in SQL.
**How to avoid:** Test the boundary cases: if `weekStart` is Monday (DOW=1) and target `day_of_week=0` (Sunday), offset = (0-1+7)%7 = 6, meaning Sunday is 6 days from Monday — correct (it's the following Sunday, but that's within a 7-day window ending next Monday). Add a `WHERE (offset_days * INTERVAL '1 day' + week_start) < week_end` guard if needed.
**Warning signs:** Recurring targets appearing outside the displayed week range, or not appearing at all.

### Pitfall 6: 401 Handling in queryFn
**What goes wrong:** When the Cognito access token expires mid-session, `fetch('/api/...')` returns a 401. TanStack Query retries the query 3 times (default), then marks it as error. The user stays on the page with stale data and no feedback.
**Why it happens:** Phase 1 implemented `/api/auth/refresh` but the TanStack Query global error handler that calls it has not been wired yet. Phase 2 is where this interceptor belongs.
**How to avoid:** In the `QueryClient` configuration, add a `queryCache` with an `onError` handler:
```typescript
import { QueryCache, QueryClient } from '@tanstack/react-query';

export function makeQueryClient() {
  return new QueryClient({
    queryCache: new QueryCache({
      onError: async (error) => {
        if (error instanceof Response && error.status === 401) {
          await fetch('/api/auth/refresh', { method: 'POST' });
          // TanStack Query will retry on next focus/interval
        }
      },
    }),
  });
}
```
Note: This is a best-effort handler. Full retry-on-401 behavior (re-execute the failing query after refresh) requires `queryClient.invalidateQueries` after refresh. This can be Phase 2's interceptor or deferred.
**Warning signs:** Users see stale data with no error after the 1-hour access token expiry window.

---

## Code Examples

Verified patterns from official docs and codebase analysis:

### QueryClient factory (web/src/lib/query-client.ts)
```typescript
// Source: TanStack Query v5 official Next.js App Router pattern
import { QueryCache, QueryClient } from '@tanstack/react-query';

export function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30 * 1000,  // 30s global default
      },
    },
    queryCache: new QueryCache({
      onError: async (error: unknown) => {
        // Wire Phase 1's /api/auth/refresh on 401
        if (error instanceof Error && error.message.startsWith('HTTP 401')) {
          try {
            await fetch('/api/auth/refresh', { method: 'POST' });
          } catch {
            // Ignore — user will see stale data, next navigation will redirect to login
          }
        }
      },
    }),
  });
}
```

### Providers wrapper (web/src/components/providers.tsx)
```typescript
// Source: TanStack Query v5 Next.js App Router pattern
'use client';

import { useState } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { makeQueryClient } from '@/lib/query-client';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => makeQueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
```

### Dashboard stats migration (web/src/app/(dashboard)/dashboard/page.tsx)
```typescript
// Source: TanStack Query v5 useQuery, replacing existing setInterval pattern
'use client';

import { useQuery } from '@tanstack/react-query';
import { QUERY_KEYS } from '@/lib/query-keys';

export default function DashboardPage() {
  const { data: stats, isLoading } = useQuery({
    queryKey: QUERY_KEYS.dashboardStats,
    queryFn: async () => {
      const res = await fetch('/api/dashboard/stats');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json() as Promise<DashboardStats>;
    },
    refetchInterval: 30_000,
    // refetchIntervalInBackground defaults to false — tab pause is automatic
  });

  // isLoading: only true on first fetch (no cache) — use for skeleton
  // isFetching: true on every background refetch — do NOT use for skeleton
  if (isLoading) return <SkeletonGrid />;
  // ...rest of render
}
```

### Worker status migration (web/src/components/worker-status.tsx)
```typescript
// Source: TanStack Query v5 useQuery
'use client';

import { useQuery } from '@tanstack/react-query';
import { QUERY_KEYS } from '@/lib/query-keys';
import type { WorkerHeartbeat } from '@/lib/types';

export function WorkerStatus() {
  const { data: worker } = useQuery({
    queryKey: QUERY_KEYS.workerStatus,
    queryFn: async () => {
      const res = await fetch('/api/worker-status');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return data as WorkerHeartbeat | null;
    },
    refetchInterval: 30_000,
  });

  if (!worker) return <OfflineIndicator />;
  // ...rest of render
}
```

### Active jobs migration — removes prop (web/src/components/active-jobs.tsx)
```typescript
// Source: TanStack Query v5 useQuery
// NOTE: Remove the 'jobs' prop — component now owns its data
'use client';

import { useQuery } from '@tanstack/react-query';
import { QUERY_KEYS } from '@/lib/query-keys';

// No longer accepts 'jobs' prop — self-contained
export function ActiveJobs() {
  const { data: jobs = [] } = useQuery({
    queryKey: QUERY_KEYS.jobs,
    queryFn: async () => {
      const res = await fetch('/api/jobs');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    },
    refetchInterval: 15_000,
  });

  if (jobs.length === 0) return null;
  // ...rest of render
}
```

### Calendar API route (web/src/app/api/calendar/route.ts)
```typescript
// Source: direct schema analysis + PostgreSQL UNION ALL docs
import { NextRequest, NextResponse } from 'next/server';
import { getSession } from '@/lib/cognito';
import { query } from '@/lib/db';

const CALENDAR_SQL = `
  WITH week_bounds AS (
    SELECT $2::date AS week_start, $2::date + INTERVAL '7 days' AS week_end
  )
  SELECT
    id::text,
    class_date::text    AS event_date,
    class_time          AS event_time,
    studio_slug,
    CASE status WHEN 'booked' THEN 'booked' ELSE 'failed' END AS event_type,
    'history'           AS source,
    jsonb_build_object('spot', spot, 'message', message) AS meta
  FROM booking_history, week_bounds
  WHERE user_id = $1
    AND class_date >= week_start AND class_date < week_end

  UNION ALL

  SELECT
    bj.id::text,
    COALESCE(
      (bj.class_datetime AT TIME ZONE 'America/New_York')::date,
      (bj.scheduled_for  AT TIME ZONE 'America/New_York')::date
    )::text             AS event_date,
    to_char(
      COALESCE(bj.class_datetime, bj.scheduled_for) AT TIME ZONE 'America/New_York',
      'FMHH12:MI AM'
    )                   AS event_time,
    t.studio_slug,
    'pending'           AS event_type,
    'job'               AS source,
    jsonb_build_object(
      'scheduled_for', bj.scheduled_for,
      'class_datetime', bj.class_datetime,
      'job_status', bj.status
    )                   AS meta
  FROM booking_jobs bj
  LEFT JOIN snipe_targets t ON t.id = bj.target_id, week_bounds
  WHERE bj.user_id = $1
    AND bj.status IN ('pending', 'claimed', 'running')
    AND COALESCE(
      (bj.class_datetime AT TIME ZONE 'America/New_York')::date,
      (bj.scheduled_for  AT TIME ZONE 'America/New_York')::date
    ) >= week_start
    AND COALESCE(
      (bj.class_datetime AT TIME ZONE 'America/New_York')::date,
      (bj.scheduled_for  AT TIME ZONE 'America/New_York')::date
    ) < week_end

  UNION ALL

  -- Recurring targets: expand day_of_week into this week
  SELECT
    st.id::text,
    (week_start + ((st.day_of_week - EXTRACT(DOW FROM week_start)::int + 7) % 7)
      * INTERVAL '1 day')::date::text AS event_date,
    st.time             AS event_time,
    st.studio_slug,
    'configured'        AS event_type,
    'target'            AS source,
    jsonb_build_object('target_type', 'recurring', 'day_of_week', st.day_of_week) AS meta
  FROM snipe_targets st, week_bounds
  WHERE st.user_id = $1
    AND st.enabled = true
    AND st.target_type = 'recurring'
    AND st.day_of_week IS NOT NULL

  UNION ALL

  -- One-time targets: match directly on target_date
  SELECT
    st.id::text,
    st.target_date::text AS event_date,
    st.time             AS event_time,
    st.studio_slug,
    'configured'        AS event_type,
    'target'            AS source,
    jsonb_build_object('target_type', 'one_time') AS meta
  FROM snipe_targets st, week_bounds
  WHERE st.user_id = $1
    AND st.enabled = true
    AND st.target_type = 'one_time'
    AND st.target_date >= week_start
    AND st.target_date < week_end

  ORDER BY event_date, event_time NULLS LAST
`;

export async function GET(request: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const { searchParams } = new URL(request.url);
  const weekStart = searchParams.get('weekStart');

  if (!weekStart || !/^\d{4}-\d{2}-\d{2}$/.test(weekStart)) {
    return NextResponse.json({ error: 'weekStart must be YYYY-MM-DD' }, { status: 400 });
  }

  try {
    const { rows } = await query(CALENDAR_SQL, [user.sub, weekStart]);
    return NextResponse.json(rows);
  } catch (err) {
    console.error('[calendar] GET error:', err);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `setInterval` + `useState` + `useEffect` | `useQuery` with `refetchInterval` | Phase 2 | Automatic tab-pause, deduplication, stale-while-revalidate — no manual cleanup |
| Three separate polling loops at different intervals | Single QueryClient cache — queries share state, dedup inflight requests | Phase 2 | Network savings when multiple components poll the same endpoint |
| No server state layer | TanStack Query `queryCache` | Phase 2 | Foundation for Phase 3+ to use `queryClient.invalidateQueries` after mutations |
| N+1 API calls for calendar data | Single `UNION ALL` across 3 tables | Phase 2 | One round-trip for all weekly event types |

**Deprecated/outdated after Phase 2:**
- `setInterval` in dashboard components: Replaced by `useQuery`. Zero instances should remain.
- `useState(initialJobs)` in `ActiveJobs`: Component becomes self-contained with `useQuery`.
- `useCallback(fetchStats, [])` pattern: No longer needed — `queryFn` is stable inside `useQuery`.

---

## Open Questions

1. **Should `ActiveJobs` remain a separate component or be absorbed into dashboard `useQuery`?**
   - What we know: `dashboard/page.tsx` already fetches `activeJobs` from `/api/dashboard/stats`. `active-jobs.tsx` also polls `/api/jobs` separately.
   - What's unclear: Whether to consolidate into a single `dashboardStats` query or keep them independent.
   - Recommendation: Keep them independent for now. `dashboardStats` has a 30s interval (stat cards), `jobs` has a 15s interval (active booking display). Different staleTime requirements justify separate queries. TanStack Query deduplicates if they end up using the same key.

2. **Should `dashboard/page.tsx` remain a `'use client'` page or become a Server Component?**
   - What we know: Currently `'use client'` because it uses `useCallback` and `useEffect`. After migration to TanStack Query, all data fetching moves to `useQuery`.
   - What's unclear: Whether to split into a Server Component wrapper + Client Component islands.
   - Recommendation: Keep as `'use client'` for Phase 2. The RSC/Server Component split is an optimization that can be done separately. The current page is simple enough that the complexity cost of splitting is not justified yet.

3. **CalendarEvent deduplication: API-side or UI-side?**
   - What we know: A booked class will appear as both `'configured'` (from targets) and `'booked'` (from history).
   - What's unclear: Whether to exclude `configured` events that have matching `history` records in the SQL query.
   - Recommendation: Return all rows from the API (no dedup in Phase 2). Let Phase 3 calendar UI apply priority logic (booked > pending > configured) when multiple events share the same `studio_slug + event_date + event_time`. This is simpler for Phase 2 and correct for Phase 3.

4. **Should `/api/calendar` use `booking_opens_at` from `class_schedules`?**
   - What we know: `class_schedules` has `booking_opens_at` which enables TRUST-02 (countdown to booking window). This data is not in `snipe_targets` or `booking_jobs`.
   - What's unclear: Whether to JOIN `class_schedules` in the calendar query or fetch it separately.
   - Recommendation: Defer joining `class_schedules` to Phase 5 (TRUST-01/TRUST-02 implementation). Phase 2's calendar route provides the event skeleton — Phase 5 enriches it with booking window timing.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis — `web/src/app/(dashboard)/dashboard/page.tsx`, `components/active-jobs.tsx`, `components/worker-status.tsx`, all API routes, `packages/shared/src/types.ts`, all 7 migration SQL files
- PostgreSQL UNION ALL docs: https://www.postgresql.org/docs/current/queries-union.html
- TanStack Query GitHub `packages/react-query/package.json` (confirmed `"react": "^18 || ^19"` peerDependency)

### Secondary (MEDIUM confidence)
- TanStack Query v5 npm: https://www.npmjs.com/package/@tanstack/react-query — current version 5.90.21
- `refetchIntervalInBackground` default `false` behavior — verified via multiple TanStack Query v5 docs references and GitHub issues
- `useState(() => makeQueryClient())` lazy initialization pattern — verified via LogRocket TanStack + Next.js App Router guide and official Next.js example discussion
- `queryOptions` helper — verified from TanStack Query v5 docs: https://tanstack.com/query/v5/docs/react/guides/query-options

### Tertiary (LOW confidence — flagged for validation)
- `QueryCache.onError` interceptor pattern for 401 refresh — structurally correct per TanStack Query v5 API but the exact behavior when combined with retry logic should be validated against v5.90.x changelog

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — TanStack Query v5 peer dep React 19 confirmed from GitHub source; no install conflicts expected
- Architecture: HIGH — provider pattern verified from official sources; setInterval migration is mechanical
- Calendar UNION SQL: MEDIUM-HIGH — schema read directly from migration files; SQL pattern is standard PostgreSQL; day-of-week math needs validation against edge cases
- Pitfalls: HIGH — isLoading/isFetching confusion is a well-documented v5 behavior; QueryClient recreation is explicitly called out in official docs

**Research date:** 2026-02-27
**Valid until:** 2026-03-29 (30 days — TanStack Query v5 is stable; provider pattern unlikely to change)
