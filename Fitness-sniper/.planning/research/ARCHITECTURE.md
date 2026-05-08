# Architecture Patterns

**Domain:** Calendar-centered fitness class auto-booking dashboard
**Researched:** 2026-02-26
**Question:** How should a calendar-centered dashboard with real-time job status integrate with an existing Next.js API + PostgreSQL backend?

---

## Recommended Architecture

The rebuild is a **frontend + API layer upgrade** — the worker daemon, adapters, and database schema are fixed constraints. The architecture problem is: how do you add a calendar-centered UI with real-time job status and schedule browsing on top of a REST API that currently uses 30-second polling and no shared state?

The answer is: **TanStack Query for server state management + a custom-built weekly calendar component + upgraded polling intervals.** SSE is architecturally valid but is ruled out by Vercel's 10-second serverless function timeout on the Hobby plan. The existing polling pattern stays but moves from raw `setInterval` inside components to TanStack Query's `refetchInterval`, which adds deduplication, caching, and stale-time control at no cost.

### High-Level Structure

```
Browser (React 19 Client Components)
│
├── TanStack Query Provider         ← single cache layer, replaces ad-hoc setInterval
│   ├── useJobsQuery()              ← polls /api/jobs every 10s
│   ├── useScheduleQuery()          ← polls /api/schedules per selected studio/date
│   ├── useTargetsQuery()           ← polls /api/targets every 30s
│   └── useDashboardStatsQuery()    ← polls /api/dashboard/stats every 30s
│
├── CalendarView (week/day display) ← custom built, NOT react-big-calendar
│   ├── WeekGrid                    ← 7-column time-slotted grid
│   ├── CalendarEvent               ← renders confirmed booking, pending snipe, available slot
│   └── DayColumn                   ← holds events for one day
│
├── SchedulePanel (slide-over)      ← triggered by calendar day/slot click
│   ├── ClassList                   ← live classes for selected studio+date
│   ├── ClassCard                   ← individual class + "Snipe This" CTA
│   └── SnipeConfigSheet            ← configure target params before creating
│
├── JobStatusTimeline               ← per-target status with countdown
│   ├── StatusBadge                 ← Scheduled → Waiting → Attempting → Booked
│   └── CountdownTimer              ← "Booking opens in 2d 4h — we'll attempt at 12:00 AM"
│
└── DashboardShell                  ← layout + nav (server component, validates session)
    └── (dashboard)/ route group    ← existing pattern, keep unchanged
```

```
Next.js API Routes (Route Handlers)
│
├── /api/calendar                   ← NEW: merged view of jobs + targets for calendar render
├── /api/jobs                       ← existing, extend with class_name + studio_slug
├── /api/schedules                  ← existing, no changes needed
├── /api/targets                    ← existing, no changes needed
├── /api/targets/[id]               ← existing, no changes needed
└── /api/dashboard/stats            ← existing, extend with booking_opens_at
│
└── PostgreSQL (via pg pool)        ← unchanged, direct queries
```

```
Worker Daemon (Mac Mini) — UNCHANGED
│
├── Scheduler (cron 15min)
├── SlotWatcher (Arketa 60s)
├── Poller + Processor
└── ScheduleScraper (2AM + 2PM)
```

---

## Component Boundaries

### What Talks To What

| Component | Reads From | Writes To | Boundary Notes |
|-----------|-----------|-----------|----------------|
| `DashboardShell` | Session cookie (server-side) | — | Server component. Calls `getSession()`. Renders children. |
| `CalendarView` | `useCalendarQuery()` → `/api/calendar` | — | Client component. Read-only display. Clicking a day slot opens SchedulePanel. |
| `WeekGrid` | Props from `CalendarView` | — | Pure presentational. Receives events array. |
| `CalendarEvent` | Props (event type, status) | — | Color-coded by event type: confirmed booking (green), pending snipe (yellow), available slot (blue). |
| `SchedulePanel` | `useScheduleQuery()` → `/api/schedules` | `useMutation` → `/api/targets` (POST) | Triggered by CalendarView click. Shows live classes. Creates snipe targets. |
| `ClassCard` | Props (class data) | Calls parent's `onSnipe(classData)` | Presentational. Emits upward. |
| `SnipeConfigSheet` | Props (pre-filled from ClassCard) | `POST /api/targets` via TanStack mutation | Form + submit. useOptimistic for instant calendar feedback. |
| `JobStatusTimeline` | `useJobsQuery()` → `/api/jobs` | — | Reads job rows. Derives status labels and countdown from timestamps. |
| `CountdownTimer` | Props (booking_opens_at timestamp) | — | Client-only. `setInterval` inside, 1-minute tick. No server calls. |
| `WorkerStatus` | `useWorkerStatusQuery()` → `/api/worker-status` | — | Keep as-is, just move to TanStack Query. |
| `ActiveJobs` | Shared cache from `useJobsQuery()` | — | Reads same query cache as JobStatusTimeline. No duplicate fetch. |

### Component NOT to build

Do not build a drag-and-drop booking interface. The worker owns booking timing — the UI's job is to configure targets and display results. Drag-and-drop implies users can reschedule, which is not the data model.

Do not build an SSE endpoint. Vercel Hobby plan caps serverless function duration at 10 seconds. SSE requires persistent connections. Polling at 10–15 second intervals achieves acceptable real-time feel for a ~5-10 user audience at zero infrastructure cost.

---

## Data Flow

### Calendar Data Flow

The calendar needs three data types merged into one view:

```
1. Confirmed bookings (booking_history, status = 'booked')
   Source: /api/calendar → SELECT from booking_history WHERE user_id = $1
           AND class_datetime BETWEEN week_start AND week_end

2. Pending snipes (booking_jobs, status IN pending/claimed/running)
   Source: /api/calendar → SELECT from booking_jobs WHERE user_id = $1
           AND class_datetime BETWEEN week_start AND week_end

3. Configured targets without jobs yet (snipe_targets, recurring)
   Source: /api/calendar → JOIN snipe_targets to generate projected occurrences
           for the displayed week (computed server-side, not client-side)
```

**New API route needed: `GET /api/calendar?weekStart=YYYY-MM-DD`**

This is the only new API route the calendar view requires. It returns a merged event list. The frontend does not need to join these three queries itself — doing so would require fetching all jobs AND all targets AND all history separately and merging client-side, which creates timing issues and wastes bandwidth.

Response shape:
```typescript
interface CalendarEvent {
  id: string;
  type: 'confirmed' | 'pending_snipe' | 'configured_target';
  studioSlug: string;
  locationId: string;
  classDatetime: string;       // ISO 8601
  className: string | null;
  instructor: string | null;
  jobStatus?: 'pending' | 'claimed' | 'running';
  bookingOpensAt?: string;     // for countdown
  targetId: string;
}
```

### Schedule Panel Data Flow

```
User clicks day column in CalendarView
  → CalendarView emits { date: 'YYYY-MM-DD', studioSlug: string }
  → SchedulePanel opens (sheet/drawer component)
  → useScheduleQuery({ studio, location, date }) fires
  → /api/schedules?studio=barrys&location=9594&date=2026-03-01
  → Returns live classes (existing API, no change needed)
  → User clicks "Snipe This" on a ClassCard
  → SnipeConfigSheet opens pre-filled with class data
  → User confirms → POST /api/targets
  → TanStack Query invalidates useTargetsQuery() and useCalendarQuery()
  → Calendar immediately shows new configured_target event (optimistic update)
```

### Job Status Data Flow

```
Worker inserts booking_job into PostgreSQL
  → No push — web has no direct worker connection
  → useJobsQuery() polls /api/jobs every 10 seconds
  → /api/jobs returns jobs in pending/claimed/running status
  → JobStatusTimeline derives display labels from status column
  → CountdownTimer reads booking_opens_at timestamp, ticks client-side
  → When job moves to success/failed, polling picks it up within 10s
  → TanStack Query updates cache → JobStatusTimeline re-renders
```

**Polling intervals by data type:**

| Data | Interval | Rationale |
|------|----------|-----------|
| `/api/jobs` (active jobs) | 10 seconds | Jobs can change status during active booking window |
| `/api/calendar` (week view) | 30 seconds | Confirms from worker need to propagate; new targets appear |
| `/api/dashboard/stats` | 30 seconds | Aggregate counts, not urgent |
| `/api/schedules` (live classes) | 5 minutes | External API, expensive; matches existing cache TTL |
| `/api/worker-status` | 30 seconds | Heartbeat detection, existing interval is correct |

All intervals use TanStack Query's `refetchInterval` rather than `setInterval` directly. This gives automatic deduplication (multiple components using the same query key share one fetch) and background tab pause (`refetchIntervalInBackground: false`).

### Authentication Flow (Unchanged)

```
DashboardLayout (server component) → getSession() → redirect if no cookie
All API routes → getSession() first → 401 if invalid
TanStack Query receives 401 → does not retry (configure retry: false for auth errors)
```

---

## Patterns to Follow

### Pattern 1: Calendar Event Coloring by Type

The calendar distinguishes three event states visually:

```typescript
const EVENT_STYLES = {
  confirmed: {
    bg: 'bg-emerald-500/20',
    border: 'border-emerald-500/40',
    dot: 'bg-emerald-400',
    label: 'Booked',
  },
  pending_snipe: {
    bg: 'bg-yellow-500/10',
    border: 'border-yellow-500/30',
    dot: 'bg-yellow-400 animate-pulse',
    label: 'Sniping',
  },
  configured_target: {
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/20',
    dot: 'bg-blue-400',
    label: 'Watching',
  },
} as const;
```

This mirrors the existing `STATUS_COLORS` pattern in `active-jobs.tsx`. Extend — do not replace.

### Pattern 2: TanStack Query Provider Setup (Client Component Boundary)

```typescript
// web/src/components/providers.tsx — single provider file
'use client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () => new QueryClient({
      defaultOptions: {
        queries: {
          staleTime: 10_000,        // 10s — data is fresh for 10s after fetch
          retry: 1,                  // retry once on network error
          refetchOnWindowFocus: true,
        },
      },
    })
  );
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
```

Add `<Providers>` to `web/src/app/(dashboard)/layout.tsx` wrapping `<main>`. Do NOT add it to the root layout — it is only needed inside the authenticated shell.

### Pattern 3: Shared Query Keys

Define query keys as constants to enable invalidation across components:

```typescript
// web/src/lib/query-keys.ts
export const QUERY_KEYS = {
  calendar: (weekStart: string) => ['calendar', weekStart] as const,
  jobs: () => ['jobs'] as const,
  targets: () => ['targets'] as const,
  schedules: (studio: string, location: string, date: string) =>
    ['schedules', studio, location, date] as const,
  dashboardStats: () => ['dashboard', 'stats'] as const,
  workerStatus: () => ['worker-status'] as const,
} as const;
```

When a new target is created via `SnipeConfigSheet`, invalidate both `QUERY_KEYS.targets()` and `QUERY_KEYS.calendar(currentWeekStart)`.

### Pattern 4: Optimistic Target Creation

```typescript
const createTarget = useMutation({
  mutationFn: (data: NewTargetPayload) =>
    fetch('/api/targets', { method: 'POST', body: JSON.stringify(data) }),
  onMutate: async (newTarget) => {
    await queryClient.cancelQueries({ queryKey: QUERY_KEYS.calendar(weekStart) });
    const snapshot = queryClient.getQueryData(QUERY_KEYS.calendar(weekStart));
    queryClient.setQueryData(
      QUERY_KEYS.calendar(weekStart),
      (old: CalendarEvent[]) => [
        ...old,
        { ...newTarget, type: 'configured_target', id: `optimistic-${Date.now()}` },
      ]
    );
    return { snapshot };
  },
  onError: (_err, _vars, context) => {
    queryClient.setQueryData(QUERY_KEYS.calendar(weekStart), context?.snapshot);
  },
  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.calendar(weekStart) });
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.targets() });
  },
});
```

The optimistic update makes the calendar feel immediate. The `onSettled` invalidation reconciles with the server after the POST returns.

### Pattern 5: Custom Weekly Calendar (Not react-big-calendar)

Use a custom-built weekly calendar, not react-big-calendar or a third-party library. The reasons:

1. The project uses Tailwind v4 (not v3) — react-big-calendar's CSS overrides are designed for v3 and the integration layer (`shadcn-ui-big-calendar`) targets v3 CSS variables.
2. The event types are custom (confirmed booking / pending snipe / configured target) with app-specific interaction patterns (click to open SchedulePanel).
3. The project already has a custom `calendar.tsx` shadcn component (for date picker). A full event calendar is a different beast and needs to match the existing dark design system exactly.
4. A weekly grid for 5-10 classes per day is not complex: it is a 7-column CSS grid with time slots rendered as `div` rows.

Estimated complexity: 150-250 lines for `WeekGrid` + `DayColumn` + `CalendarEvent`. This is less than a react-big-calendar integration + theming fix.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Per-Component setInterval

**What:** Each component independently calls `setInterval` to poll its endpoint (current pattern in `dashboard/page.tsx` and `active-jobs.tsx` and `worker-status.tsx`).

**Why bad:** Three components polling three endpoints independently = 3 separate fetch loops. If multiple tabs are open, each tab multiplies this. No deduplication, no shared cache, no stale-time awareness.

**Instead:** Replace all `setInterval` fetch loops with TanStack Query `useQuery` + `refetchInterval`. Multiple components using the same query key share one fetch — zero code duplication, automatic deduplication.

### Anti-Pattern 2: Client-Side Merging of Jobs + Targets + History

**What:** Fetching `/api/jobs`, `/api/targets`, and `/api/history` separately and merging them in a React component to build the calendar event list.

**Why bad:** Three round-trips for every calendar render. Race conditions (jobs arrive before targets, calendar shows inconsistent state). Complex client-side join logic that reimplements what PostgreSQL does in 5ms.

**Instead:** New `/api/calendar?weekStart=YYYY-MM-DD` route does the JOIN server-side. Single round-trip. No race conditions. The existing pattern for `/api/dashboard/stats` (multi-table query in one route handler) demonstrates this is already the project's preferred approach.

### Anti-Pattern 3: Pushing Schedule Browsing State into URL Params

**What:** Making the selected studio/date for schedule browsing a URL query param like `/schedule?studio=barrys&date=2026-03-01`.

**Why bad:** Every studio or date change causes a full navigation event. The schedule page already exists as a client component (`schedule-explorer.tsx`) that manages this state locally. URL-driven browsing would require converting to a server component or using `useSearchParams` carefully — unnecessary complexity for a tool used by 5-10 people.

**Instead:** Keep schedule browser state local (current pattern in `schedule-explorer.tsx`). Calendar selection state (`selectedDate`, `selectedStudio`) lives in the CalendarView component as `useState`. Only the target creation result needs to be reflected in the URL (via router.refresh or query invalidation).

### Anti-Pattern 4: SSE for Job Status

**What:** Implementing a Server-Sent Events endpoint at `/api/jobs/stream` for real-time job status push.

**Why bad:** Vercel Hobby plan limits serverless functions to 10 seconds. SSE requires persistent connections. This is a documented limitation in the Next.js GitHub discussions (issue #48427). Even if it worked, it adds complexity (connection manager, cleanup, reconnection logic) for a 5-10 user audience where 10-second polling is indistinguishable from real-time.

**Instead:** TanStack Query `refetchInterval: 10_000` on the jobs query. Imperatively trigger `queryClient.invalidateQueries({ queryKey: QUERY_KEYS.jobs() })` after a target creation mutation to force immediate refresh.

### Anti-Pattern 5: Modifying the Worker or Database Schema

**What:** Adding real-time infrastructure (WebSockets, Redis pub/sub, Postgres LISTEN/NOTIFY) between the worker and the web frontend.

**Why bad:** The worker is a stable, working daemon. Any change risks breaking the booking pipeline — the most critical part of the product. Postgres LISTEN/NOTIFY would require a persistent connection in the Next.js layer, incompatible with serverless.

**Instead:** Accept polling. The booking jobs table is already the source of truth. Read it efficiently with indexed queries. The 10-second polling interval is invisible to users watching the countdown.

---

## Build Order

Dependencies between components determine the build sequence:

### Phase 1: Foundation (no component dependencies)

1. **TanStack Query provider** — install `@tanstack/react-query`, create `providers.tsx`, add to dashboard layout. This is a zero-risk change: it wraps existing children with no behavior change.
2. **Query key constants** — `web/src/lib/query-keys.ts`. Pure TypeScript, no UI.
3. **`/api/calendar` route** — new route, no existing code modified. PostgreSQL JOIN of `booking_history + booking_jobs + snipe_targets` for a week window.

### Phase 2: Migrate Existing Polls to TanStack Query

4. **Migrate `WorkerStatus`** — simplest component, one endpoint, no interaction. Convert `setInterval` to `useQuery`. Validates the TanStack Query setup.
5. **Migrate `ActiveJobs`** — same pattern, slightly more data.
6. **Migrate `DashboardPage` stats** — replaces the page-level `setInterval`.

These migrations should produce zero visible change. They are risk reduction before adding new UI.

### Phase 3: Calendar View

7. **`WeekGrid` component** — pure presentational, renders a 7-column grid with time slots. No data fetching yet. Build and style it with static fixture data.
8. **`CalendarEvent` component** — renders a single event with type-based styling. Static props.
9. **`CalendarView` component** — wires `useCalendarQuery()` to the grid. Handles week navigation (prev/next). This is the integration layer.
10. **Replace `DashboardPage` contents** — swap stat cards + `ActiveJobs` for `CalendarView` as the primary element. Keep stats as secondary.

### Phase 4: Schedule Panel + Target Creation

11. **`SchedulePanel` (sheet)** — opens on calendar day click. Reads from existing `useScheduleQuery`. No new API needed.
12. **`ClassCard`** — class row with "Snipe This" button. Presentational.
13. **`SnipeConfigSheet`** — form with `useMutation`. Invalidates calendar on success. This is the most complex component: needs optimistic update + validation + error handling.

### Phase 5: Job Status Timeline

14. **`JobStatusTimeline`** — reads from shared `useJobsQuery()` cache. By this point the cache is already established by the migrated `ActiveJobs`. Timeline is additive.
15. **`CountdownTimer`** — reads `booking_opens_at` from job row. Client-side tick, no server calls.

---

## Scalability Considerations

This system is scoped for 5-10 users. These are the constraints to be aware of:

| Concern | At 5-10 users | At 100+ users | Notes |
|---------|--------------|---------------|-------|
| Polling load | Negligible | `/api/jobs` every 10s × N users hits PostgreSQL directly | Add connection pooling (PgBouncer) or reduce interval before public launch |
| `/api/calendar` query | Fast — indexes on `user_id + class_datetime` | Still fast with proper indexes | Ensure `booking_jobs` and `booking_history` have composite index on `(user_id, class_datetime)` |
| Schedule API calls | 5-min in-memory cache is enough | Cache is per-Vercel-instance (no distributed cache) | At scale, move cache to Redis. Not needed now. |
| Vercel function cold starts | Rarely cold at low traffic | Can cause 1-2s latency spikes | Not actionable at this scale |

---

## New API Route Specification

### `GET /api/calendar?weekStart=YYYY-MM-DD`

**Purpose:** Returns all calendar events for the authenticated user for the week starting at `weekStart`.

**PostgreSQL query structure:**

```sql
-- Confirmed bookings
SELECT
  bh.id,
  'confirmed' AS type,
  st.studio_slug,
  st.location_id,
  bh.class_datetime,
  bh.class_name,
  bh.instructor,
  NULL AS job_status,
  NULL AS booking_opens_at,
  bh.target_id
FROM booking_history bh
JOIN snipe_targets st ON st.id = bh.target_id
WHERE bh.user_id = $1
  AND bh.class_datetime >= $2
  AND bh.class_datetime < $3
  AND bh.status = 'booked'

UNION ALL

-- Active jobs (pending/claimed/running)
SELECT
  bj.id,
  'pending_snipe' AS type,
  st.studio_slug,
  st.location_id,
  bj.class_datetime,
  cs.class_name,
  cs.instructor,
  bj.status AS job_status,
  cs.booking_opens_at,
  bj.target_id
FROM booking_jobs bj
JOIN snipe_targets st ON st.id = bj.target_id
LEFT JOIN class_schedules cs ON cs.studio_slug = st.studio_slug
  AND cs.location_id = st.location_id
  AND DATE(cs.class_date) = DATE(bj.class_datetime)
  AND cs.class_time = st.time
WHERE bj.user_id = $1
  AND bj.class_datetime >= $2
  AND bj.class_datetime < $3
  AND bj.status IN ('pending', 'claimed', 'running')

ORDER BY class_datetime ASC
```

Configured targets without jobs yet require server-side date projection (recurring targets → project occurrences for the week). This is deferred to the roadmap phase for target visualization; the first calendar iteration covers confirmed + active only.

---

## Existing Code to Preserve

These existing patterns are correct and should not change:

- `DashboardLayout` server component pattern — session check in server, redirect to `/login`
- `getSession()` call at the top of every API route — keep exactly as-is
- `query()` from `web/src/lib/db.ts` — direct PostgreSQL pool, no ORM
- The `ALLOWED_COLUMNS` whitelist pattern in PUT routes — correct security approach
- Dark mode via `className="dark"` on `<html>` — hardcoded, no theme toggling needed
- `schedules/route.ts` — complex but correct; DB-first with live API fallback; do not rewrite

The only existing frontend pattern to replace is raw `setInterval` inside components. Everything else carries forward.

---

## Sources

- [Server-Sent Events with Next.js App Router — Vercel limitations (GitHub Discussion #48427)](https://github.com/vercel/next.js/discussions/48427) — confirmed SSE not viable on Vercel Hobby; MEDIUM confidence
- [TanStack Query — refetchInterval polling pattern](https://tanstack.com/query/latest) — official docs; HIGH confidence
- [TanStack Query App Router integration guide](https://tanstack.com/query/latest/docs/framework/react/guides/advanced-ssr) — official docs; HIGH confidence
- [Zustand + TanStack Query: server state vs client state separation](https://javascript.plainenglish.io/zustand-and-tanstack-query-the-dynamic-duo-that-simplified-my-react-state-management-e71b924efb90) — MEDIUM confidence, matches multiple sources
- [React 19 useOptimistic hook](https://react.dev/reference/react/useOptimistic) — official React docs; HIGH confidence
- [shadcn-ui-big-calendar (react-big-calendar + shadcn integration)](https://github.com/list-jonas/shadcn-ui-big-calendar) — reviewed; targets Tailwind v3 CSS variables; LOW confidence for v4 compatibility, reason to build custom
- [Next.js route handler streaming — ReadableStream pattern](https://nextjs.org/docs/app/api-reference/file-conventions/route) — official Next.js docs; HIGH confidence
- [Fixing slow SSE in Next.js + Vercel (Jan 2026)](https://medium.com/@oyetoketoby80/fixing-slow-sse-server-sent-events-streaming-in-next-js-and-vercel-99f42fbdb996) — confirms Vercel timeout constraints are current as of 2026; MEDIUM confidence

---

*Architecture research: 2026-02-26*
