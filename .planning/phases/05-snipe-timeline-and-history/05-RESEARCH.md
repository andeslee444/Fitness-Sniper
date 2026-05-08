# Phase 5: Snipe Timeline and History - Research

**Researched:** 2026-02-28
**Domain:** React UI components (status timeline, countdown timer), PostgreSQL query enrichment, dashboard analytics
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TRUST-01 | Each snipe target shows a status timeline — "Scheduled → Waiting for booking window → Attempting → Booked/Failed" with timestamps | `TargetWithJob` already has `job_status`, `job_scheduled_for`, `job_class_datetime` — map 6 DB states to 4 user-facing steps; timestamps from existing fields |
| TRUST-02 | Pending snipes show a countdown to when the booking window opens ("Booking opens in 2d 4h — we'll attempt at 12:00 AM") | `job_scheduled_for` is booking open time; pure client-side `setInterval` countdown ticks without server calls |
| TRUST-03 | Failed booking jobs display prominent failure reasons with actionable messaging ("Class was full" / "Check your credentials") | `job_message` / `result_message` already stored in DB; need client-side translation map from raw error strings to actionable copy |
| HIST-01 | Booking history displays class names and studio names (not just times and location IDs) | `booking_history` has NO `class_name` column — must join `class_schedules` or add migration; `STUDIOS[slug].name` resolves studio name |
| HIST-02 | Dashboard shows success rate per studio ("8/10 booked, 80%") as a summary stat | New SQL query over `booking_history` — GROUP BY studio_slug, COUNT success vs total |
| HIST-03 | User can filter booking history by studio | Add `studio_slug` query param to `/api/history`; add filter UI (select or tab) to history page |
</phase_requirements>

---

## Summary

Phase 5 is primarily a UI enrichment and data wiring phase — no new infrastructure is needed. The worker pipeline already populates `booking_jobs.result_message`, `job_status`, `scheduled_for`, and `class_datetime`. The targets page already queries `TargetWithJob` with job fields. The gaps are: (1) the 4-step timeline component doesn't exist yet, (2) failure messages are rendered in muted small text rather than prominently, (3) `booking_history` has no `class_name` column so HIST-01 requires a migration + trigger update, (4) the dashboard stats query doesn't compute per-studio success rates, and (5) the history API has no studio filter.

The most consequential finding is the missing `class_name` in `booking_history`. The `on_job_completed` trigger does not populate a class_name — it copies fields from `snipe_targets` (studio_slug, location_id, time) but not from `class_schedules` (class_name). To surface class names in history, the approach is to JOIN `class_schedules` at query time using (studio_slug, location_id, class_date, class_time) as the lookup key — this avoids a schema migration risk (altering the trigger mid-production). A fallback column approach (migrate + update trigger) is the cleaner long-term fix and should be done in Plan 05-02.

The countdown timer is purely client-side: `setInterval` in a `useEffect`, computing `job_scheduled_for - Date.now()` every second, with no server round-trips. This aligns with the established project decision (TanStack Query `refetchInterval`, no SSE/WebSockets).

**Primary recommendation:** Build `JobStatusTimeline` + `CountdownTimer` as standalone components in `web/src/components/`, integrate into `targets-list.tsx`. Fix history page with a `class_schedules` JOIN, studio filter, and prominent failure messages. Add a per-studio success rate query to the dashboard stats API.

---

## Standard Stack

### Core (already in project — no new installs)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 19.2.3 | Component state, effects | Project standard |
| @tanstack/react-query | 5.x | Data fetching, cache invalidation | Project standard (used in active-jobs, calendar, worker-status) |
| lucide-react | current | Status icons (CheckCircle, XCircle, Clock, Loader2, Timer) | Already imported in targets-list |
| shadcn/ui (Badge, Button, Select) | radix-ui 1.4.3 | UI primitives | Project standard |
| Tailwind v4 | current | Styling | Project standard |
| pg (via `@/lib/db`) | current | PostgreSQL queries | Project standard |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `date-fns` or native `Date` | N/A | Countdown math, duration formatting | Use native `Date` — project already does this everywhere (`toLocaleDateString`, `Date.now()`), no `date-fns` dep in project |

**Installation:** No new packages required.

---

## Architecture Patterns

### Recommended New Files
```
web/src/components/
├── job-status-timeline.tsx    # TRUST-01: 4-step timeline component
├── countdown-timer.tsx        # TRUST-02: client-only countdown ("Booking opens in 2d 4h")
web/src/app/(dashboard)/history/
└── page.tsx                   # HIST-01 + HIST-03: enriched with class_name JOIN + studio filter
web/src/app/api/history/
└── route.ts                   # HIST-01 + HIST-03: add studio_slug filter param + class_schedules JOIN
web/src/app/api/dashboard/stats/
└── route.ts                   # HIST-02: add per-studio success rate query
supabase/migrations/
└── 007_history_class_name.sql # HIST-01: add class_name column to booking_history (optional, see below)
```

### Pattern 1: Job Status → 4-Step Timeline Mapping

**What:** Map the 6 internal DB job statuses (`pending`, `claimed`, `running`, `success`, `failed`, `cancelled`) to 4 user-facing steps shown as a horizontal or vertical stepper.

**4-step model:**
```
Step 1: Scheduled       — always complete (job exists)
Step 2: Waiting         — pending (booking window not yet open)
Step 3: Attempting      — claimed | running
Step 4: Result          — success | failed | cancelled
```

**Timestamp logic:**
- Step 1 timestamp: `job.created_at`
- Step 2 timestamp: show `job_scheduled_for` as "Booking opens [date] at [time]" — NOT a completion timestamp, but a future target
- Step 3 timestamp: `job.claimed_at` (when worker picked it up)
- Step 4 timestamp: `job.updated_at` (when terminal status set)

**Note on `TargetWithJob`:** The current `TargetWithJob` type has `job_status`, `job_scheduled_for`, `job_class_datetime`, `job_message`, `job_spot` but NOT `job_created_at` or `job_claimed_at`. The targets page SQL query must be extended to also select `bj.created_at AS job_created_at` and `bj.claimed_at AS job_claimed_at` for the timeline to show timestamps at each step.

**Example component shape:**
```typescript
// web/src/components/job-status-timeline.tsx
'use client';
import type { JobStatus } from '@/lib/types';

interface TimelineProps {
  jobStatus: JobStatus | null;
  scheduledFor: string | null;   // booking open time (ISO)
  classDatetime: string | null;  // actual class time (ISO)
  claimedAt: string | null;
  createdAt: string | null;
  message: string | null;
}

type Step = 'scheduled' | 'waiting' | 'attempting' | 'result';

function deriveActiveStep(status: JobStatus | null): Step {
  if (!status) return 'scheduled';
  if (status === 'pending') return 'waiting';
  if (status === 'claimed' || status === 'running') return 'attempting';
  return 'result'; // success | failed | cancelled
}
```

### Pattern 2: Countdown Timer (Client-Only, No Server Calls)

**What:** A React component that reads `scheduled_for` (booking open time) and ticks down every second using `setInterval` in `useEffect`.

**Rules:**
- Mount only on client — no SSR (add `'use client'` directive; or use `useEffect` guard)
- Clear interval on unmount
- Show "Booking opens in Xd Xh" format when > 1 hour away; "Booking opens in Xm Xs" when < 1 hour
- Show "Attempting now..." when past `scheduled_for` and status is `claimed`/`running`
- Show nothing (return null) when status is terminal (`success`, `failed`, `cancelled`)

**Example:**
```typescript
// web/src/components/countdown-timer.tsx
'use client';
import { useState, useEffect } from 'react';

function formatCountdown(ms: number): string {
  if (ms <= 0) return 'Attempting now...';
  const totalSeconds = Math.floor(ms / 1000);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m ${seconds}s`;
}

export function CountdownTimer({ scheduledFor }: { scheduledFor: string }) {
  const target = new Date(scheduledFor).getTime();
  const [remaining, setRemaining] = useState(() => target - Date.now());

  useEffect(() => {
    const id = setInterval(() => setRemaining(target - Date.now()), 1000);
    return () => clearInterval(id);
  }, [target]);

  return (
    <span className="text-xs text-zinc-400">
      Booking opens in {formatCountdown(remaining)} — we&apos;ll attempt at{' '}
      {new Date(scheduledFor).toLocaleTimeString('en-US', {
        hour: 'numeric', minute: '2-digit', hour12: true,
        timeZone: 'America/New_York',
      })}
    </span>
  );
}
```

### Pattern 3: Actionable Failure Message Translation

**What:** Map raw `result_message` strings from the worker into user-facing actionable copy. The messages are produced by `processor.ts` and adapter code.

**Known raw messages (from processor.ts):**
- `"No credentials found for {studio}"` → "Credential check failed — update your {studio} password"
- `"Target not found"` → "This snipe target was deleted — no action needed"
- `"All 3 attempts failed. Last: {detail}"` → "Class was full when we attempted"
- `"Class not found in schedule"` → "Class wasn't on the schedule yet — try again"
- `"Authentication failed"` / login errors → "Credential check failed — update your password"
- `"Attempt X failed: {detail}"` → currently shows during retry, will be replaced on final failure

**Translation approach:** A `translateJobMessage(raw: string | null): string` helper function using `includes()` pattern matching — not regex, to keep it simple.

```typescript
// In job-status-timeline.tsx or a separate lib/job-messages.ts
export function translateJobMessage(raw: string | null): string {
  if (!raw) return 'An unknown error occurred';
  const lower = raw.toLowerCase();
  if (lower.includes('no credentials') || lower.includes('authentication failed') || lower.includes('login'))
    return 'Credential check failed — update your password in Credentials';
  if (lower.includes('class was full') || lower.includes('no available spots') || lower.includes('full'))
    return 'Class was full when we attempted';
  if (lower.includes('class not found') || lower.includes('not in schedule'))
    return "Class wasn't on the schedule yet";
  if (lower.includes('target not found'))
    return 'Snipe target was removed';
  return raw; // fallback: show raw message
}
```

**Display rule:** Render failure reason in `text-red-400` (NOT `text-red-400/70` — the current muted style). Use a warning icon (`AlertCircle`) alongside the message. Size should be `text-sm`, not `text-xs`.

### Pattern 4: History Enrichment — Class Name via JOIN

**What:** `booking_history` does not have a `class_name` column. Studio name is derived from `STUDIOS[slug].name` (already works). Class name requires a lookup.

**Two approaches:**
1. **JOIN at query time** (no migration): `LEFT JOIN class_schedules cs ON cs.studio_slug = bh.studio_slug AND cs.location_id = bh.location_id AND cs.class_date = bh.class_date AND cs.class_time = bh.class_time` — works if `class_schedules` hasn't been cleaned up (scraper deletes rows older than 2 days). **Problem: old history won't have class names.** Works for recent entries only.
2. **Add `class_name` column + update trigger** (migration): `ALTER TABLE booking_history ADD COLUMN class_name text;` and update `on_job_completed` trigger to also join `class_schedules`. This provides class_name for all future entries. Old entries remain null — show fallback.

**Recommended approach: Option 2 (migration)** — named migration `007_history_class_name.sql`. The trigger update is safe (idempotent `CREATE OR REPLACE FUNCTION`). Old entries render the fallback `class_type` from `snipe_targets` (already available as they join via `target_id`).

**Updated trigger pattern:**
```sql
-- In 007_history_class_name.sql
ALTER TABLE booking_history ADD COLUMN IF NOT EXISTS class_name text;

CREATE OR REPLACE FUNCTION public.on_job_completed()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF (old.status IS DISTINCT FROM new.status) AND new.status IN ('success', 'failed') THEN
    INSERT INTO public.booking_history (
      user_id, job_id, target_id, studio_slug, location_id,
      class_time, class_date, status, spot, message, class_name
    )
    SELECT
      new.user_id, new.id, new.target_id,
      t.studio_slug, t.location_id, t.time,
      (COALESCE(new.class_datetime, new.scheduled_for) AT TIME ZONE 'America/New_York')::date,
      CASE WHEN new.status = 'success' THEN 'booked' ELSE 'failed' END,
      new.spot_booked, new.result_message,
      cs.class_name  -- from class_schedules, may be null
    FROM public.snipe_targets t
    LEFT JOIN public.class_schedules cs
      ON cs.studio_slug = t.studio_slug
      AND cs.location_id = t.location_id
      AND cs.class_date = (COALESCE(new.class_datetime, new.scheduled_for) AT TIME ZONE 'America/New_York')::date
      AND cs.class_time = t.time
    WHERE t.id = new.target_id;
  END IF;
  RETURN new;
END;
$$;
```

**Fallback chain for display:** `entry.class_name || entry.class_type || studio.name`

### Pattern 5: Studio Filter on History Page

**What:** Add `?studio=barrys` query param support to `/api/history`. Add a studio selector to the history page UI.

**API change:**
```typescript
// In /api/history/route.ts — add after existing params:
const studioFilter = searchParams.get('studio') || null;

// SQL change: add optional WHERE clause
const conditions = ['user_id = $1'];
const params: unknown[] = [user.sub];
if (studioFilter) {
  conditions.push(`studio_slug = $${params.length + 1}`);
  params.push(studioFilter);
}
```

**UI approach:** A `<Select>` (shadcn/ui) listing studios the user has history for. Populate the select options from a distinct query `SELECT DISTINCT studio_slug FROM booking_history WHERE user_id = $1` OR hardcode STUDIOS keys. On change, reset offset to 0, refetch.

**State management:** History page is currently a client component using `useState` + `useCallback` + manual `fetch`. Keep this pattern (no TanStack Query needed given the filter reset logic). Add `studioFilter` state; pass as query param on every `fetchHistory` call.

### Pattern 6: Per-Studio Success Rate (Dashboard Stats)

**What:** Add a SQL GROUP BY query to `/api/dashboard/stats` that returns per-studio counts over a rolling 30-day window.

**SQL:**
```sql
SELECT
  studio_slug,
  COUNT(*) FILTER (WHERE status = 'booked') AS booked,
  COUNT(*) AS total
FROM booking_history
WHERE user_id = $1
  AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY studio_slug
ORDER BY total DESC
```

**Response shape:**
```typescript
interface StudioStat {
  studio_slug: string;
  booked: number;
  total: number;
}
// Added to dashboard/stats response: { ..., studioStats: StudioStat[] }
```

**Display on dashboard:** Add a small stats section below the calendar (or within dashboard page). For each studio with history, show `"{studio.name}: {booked}/{total} booked, {pct}%"`. Only show studios with at least 1 attempt. Use the existing card/badge styling — no new components needed beyond a loop.

### Anti-Patterns to Avoid

- **Don't poll `job_scheduled_for` from server for countdown.** The value is already in the `TargetWithJob` returned at page load. Client-side countdown suffices; no server involvement needed.
- **Don't show muted/small failure text.** Current `targets-list.tsx` renders `text-xs text-red-400/70` for failure messages. Phase 5 replaces this with prominent `text-sm text-red-400` with an icon.
- **Don't use `booking_history.class_time` raw for display.** It's stored as `t.time` from `snipe_targets` — already in "H:MM AM" format, safe for direct display.
- **Don't join class_schedules without a fallback.** Class schedules are deleted after 2 days. Old history rows will have null `class_name` — always chain `class_name || class_type || studio.name`.
- **Don't rewrite TargetsList from scratch.** Enhance in-place: add `JobStatusTimeline` + `CountdownTimer` inside existing card layout. The existing switch/delete/badge structure stays.
- **Don't add refetchInterval to history page.** History is not a live-updating view — static fetch on mount + load-more is correct (matching current implementation).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Countdown display | Custom time formatting library | Native `Date` arithmetic + `Math.floor` | Project already uses native Date everywhere; no `date-fns` in deps |
| Studio name lookup | DB join or extra API call | `STUDIOS[slug].name` from shared package | Already imported in history page and targets-list |
| Step stepper UI | Third-party stepper component | Custom with Tailwind flex + border | Only 4 steps; any stepper lib is overkill and may conflict with Tailwind v4 |
| Filter UI | Complex filter panel | Single `<Select>` from shadcn/ui | Only filtering by studio_slug |

---

## Common Pitfalls

### Pitfall 1: Countdown Timer SSR Hydration Mismatch
**What goes wrong:** `new Date(scheduledFor).getTime() - Date.now()` computed on server returns a different value than on client, causing React hydration error.
**Why it happens:** Server and client compute `Date.now()` at different times.
**How to avoid:** Initialize countdown state with `useState(() => target - Date.now())` (lazy initializer runs only on client). The component already has `'use client'` so SSR won't render it — but if placed inside a server component tree, add a `suppressHydrationWarning` or guard with `useEffect` before first render.
**Warning signs:** React hydration warning in console about text content mismatch.

### Pitfall 2: `booking_history.class_date` UTC Shift
**What goes wrong:** `class_date` stored as a PostgreSQL `date` value reads as midnight UTC in JS; `new Date(entry.class_date)` in the browser shifts the date backward by hours for US-East users.
**Why it happens:** JS `new Date("2026-03-01")` parses as UTC midnight → local display shows Feb 28.
**How to avoid:** Parse with `new Date(entry.class_date + 'T00:00:00')` (forces local time interpretation) — this pattern is already used in `targets-list.tsx` (`formatTargetDate`). Apply the same pattern in history page.
**Warning signs:** Dates in history showing one day earlier than expected.

### Pitfall 3: `class_name` NULL in booking_history After Migration
**What goes wrong:** After adding `class_name` column, old history rows are NULL and UI shows nothing where class name should appear.
**Why it happens:** Migration only affects future trigger executions; existing rows have no class_name.
**How to avoid:** Apply fallback chain: `entry.class_name || entry.class_type || STUDIOS[entry.studio_slug]?.name || entry.studio_slug`. Update `BookingHistory` type in `packages/shared/src/types.ts` to add `class_name: string | null`.
**Warning signs:** Blank class name cells in history for entries created before migration.

### Pitfall 4: `TargetWithJob` Missing Timeline Timestamp Fields
**What goes wrong:** `JobStatusTimeline` needs `created_at` and `claimed_at` from the job, but the current targets page SQL query does not select them.
**Why it happens:** The LATERAL join only selects `status, scheduled_for, class_datetime, result_message, spot_booked`.
**How to avoid:** Extend the LATERAL query in `targets/page.tsx` to also select `bj.created_at AS job_created_at` and `bj.claimed_at AS job_claimed_at`. Add these fields to `TargetWithJob` type.
**Warning signs:** TypeScript errors when `JobStatusTimeline` tries to access `target.job_created_at`.

### Pitfall 5: History Page State Reset on Studio Filter Change
**What goes wrong:** User switches studio filter, but `offset` is not reset, causing empty results (offset 20 into a 5-entry set).
**Why it happens:** Filter state and pagination state are independent.
**How to avoid:** In `fetchHistory`, when filter changes, always call with `offset = 0` and `append = false`. A single `useEffect` watching `[studioFilter]` that calls `fetchHistory(0, false)` is the cleanest fix.
**Warning signs:** Empty results when switching filters.

### Pitfall 6: Per-Studio Stats with Zero-History Studios
**What goes wrong:** Dashboard stats shows stats for studios with no history — divide-by-zero or confusing "0/0, NaN%" display.
**Why it happens:** SQL GROUP BY only returns studios with history — but UI might try to iterate all STUDIOS.
**How to avoid:** Only render stat cards for studios returned by the query (i.e., those with at least 1 history record). Do not show studios with `total = 0`.

---

## Code Examples

### Extending LATERAL query in targets/page.tsx
```typescript
// Source: existing targets/page.tsx pattern — extend bj selects
const { rows: targets } = await query<TargetWithJob>(
  `SELECT st.*,
     bj.status AS job_status,
     bj.scheduled_for AS job_scheduled_for,
     bj.class_datetime AS job_class_datetime,
     bj.result_message AS job_message,
     bj.spot_booked AS job_spot,
     bj.created_at AS job_created_at,
     bj.claimed_at AS job_claimed_at
   FROM snipe_targets st
   LEFT JOIN LATERAL (
     SELECT status, scheduled_for, class_datetime, result_message, spot_booked, created_at, claimed_at
     FROM booking_jobs
     WHERE target_id = st.id
     ORDER BY created_at DESC
     LIMIT 1
   ) bj ON true
   WHERE st.user_id = $1
   ORDER BY st.created_at DESC`,
  [user!.sub],
);
```

### Per-studio success rate query
```typescript
// Source: pattern consistent with existing dashboard/stats/route.ts
const { rows: studioStats } = await query<{
  studio_slug: string; booked: string; total: string;
}>(
  `SELECT
     studio_slug,
     COUNT(*) FILTER (WHERE status = 'booked') AS booked,
     COUNT(*) AS total
   FROM booking_history
   WHERE user_id = $1
     AND created_at >= NOW() - INTERVAL '30 days'
   GROUP BY studio_slug
   ORDER BY total DESC`,
  [user.sub],
);
```

### History route with studio filter
```typescript
// Source: consistent with existing /api/history/route.ts pattern
const studioFilter = searchParams.get('studio') || null;
const params: unknown[] = [user.sub, limit, offset];
let whereClause = 'WHERE user_id = $1';
if (studioFilter) {
  whereClause += ' AND studio_slug = $4';
  params.push(studioFilter);
}
const sql = `
  SELECT bh.*, cs.class_name AS resolved_class_name
  FROM booking_history bh
  LEFT JOIN class_schedules cs
    ON cs.studio_slug = bh.studio_slug
    AND cs.location_id = bh.location_id
    AND cs.class_date = bh.class_date
    AND cs.class_time = bh.class_time
  ${whereClause}
  ORDER BY bh.created_at DESC
  LIMIT $2 OFFSET $3`;
```

Note: The JOIN approach works for recent history (class_schedules keeps 2-day window). For robust class_name display, rely on the `007_history_class_name.sql` migration which backfills via trigger.

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Raw DB status badge in targets-list | 4-step user-facing timeline with timestamps | User understands WHERE in the process their snipe is |
| Muted `text-red-400/70 text-xs` failure text | Prominent `text-red-400 text-sm` with icon | User sees failures clearly and knows what to do |
| History shows `studio_slug` + `location_id` | History shows studio name + class name | User recognizes entries without decoding IDs |
| Single global "recent history" stat | Per-studio success rate breakdown | User can see which studios the sniping works best for |

---

## Open Questions

1. **Does `booking_history.class_name` need backfilling for existing rows?**
   - What we know: Migration 007 adds the column and updates the trigger for future rows. Existing rows will have `class_name = null`.
   - What's unclear: How many existing history rows exist? If users have meaningful history, null class names for all of them is noticeable.
   - Recommendation: Accept null for existing rows. Display fallback `class_type || studio.name`. A backfill UPDATE joining class_schedules would only work for recent rows (2-day cleanup window) — not worth the complexity.

2. **Should `JobStatusTimeline` replace or augment the existing badge in `targets-list.tsx`?**
   - What we know: The existing `JOB_STATUS_CONFIG` badge in `targets-list.tsx` is a compact single badge. A timeline is more verbose.
   - What's unclear: Whether to show timeline inline in the target card or as an expand/detail panel.
   - Recommendation: Show the compact badge for quick scan; show the full timeline below the target metadata row. Timeline is always visible (not collapsed) — this matches the phase goal of users seeing "exactly where each snipe is."

3. **Which studios appear in the per-studio stats panel?**
   - What we know: SQL returns only studios with history in the last 30 days.
   - What's unclear: If a user has Barry's history but not Aarmy, should Aarmy show at all?
   - Recommendation: Only show studios returned by the query (with history). Don't pad with empty studios.

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection — `targets-list.tsx`, `history/page.tsx`, `processor.ts`, `packages/shared/src/types.ts`, DB migrations — all read from project filesystem
- `active-jobs.tsx` — established TanStack Query + refetchInterval pattern used as countdown timer basis
- `005_booking_timing.sql` — confirms `scheduled_for` = booking open time, `class_datetime` = actual class time

### Secondary (MEDIUM confidence)
- React `useEffect` + `setInterval` countdown pattern — well-established React idiom, consistent with project's existing `useEffect` patterns in `history/page.tsx` and `credentials-page-client.tsx`
- PostgreSQL `COUNT(*) FILTER (WHERE ...)` — standard PostgreSQL aggregate filter syntax, valid for PostgreSQL 9.4+

### Tertiary (LOW confidence — validate against actual DB)
- Assumption that `class_schedules` rows for a given (studio_slug, location_id, class_date, class_time) tuple match the same tuple stored in `booking_history`. The UNIQUE constraint on `class_schedules` is `(studio_slug, location_id, class_date, class_time, class_name)` — meaning multiple rows can exist per time slot if class_name differs. The JOIN could return multiple rows. **Verify:** Use `LIMIT 1` in the JOIN subquery or add `AND cs.class_name IS NOT NULL` to select the most specific match.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all tools are already in project
- Architecture: HIGH — patterns derived from direct code inspection of existing files
- Pitfalls: HIGH — derived from existing code issues visible in source (muted failure text, missing timeline fields)
- DB schema gap (class_name): HIGH — confirmed by reading all 6 migration files; `booking_history` definitively has no `class_name` column

**Research date:** 2026-02-28
**Valid until:** 2026-04-01 (stable stack — Next.js 16, React 19, Tailwind v4 are locked in project)
