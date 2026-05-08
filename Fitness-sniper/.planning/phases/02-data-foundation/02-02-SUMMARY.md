---
phase: 02-data-foundation
plan: 02
subsystem: api
tags: [calendar, api, types, postgresql, union-all]
dependency_graph:
  requires: []
  provides: [CalendarEvent type, GET /api/calendar endpoint]
  affects: [Phase 3 calendar UI]
tech_stack:
  added: []
  patterns: [UNION ALL multi-source query, CTE week_bounds, AT TIME ZONE conversion]
key_files:
  created:
    - packages/shared/src/types.ts (CalendarEvent interface added)
    - web/src/app/api/calendar/route.ts
  modified:
    - web/src/lib/types.ts (re-export CalendarEvent, CalendarEventType, CalendarEventSource)
decisions:
  - "Do not deduplicate configured targets with history records — return all rows, let Phase 3 UI handle priority (booked > pending > configured)"
  - "Use CTE week_bounds to avoid repeating $2::date + INTERVAL date arithmetic across 4 UNION ALL branches"
  - "LEFT JOIN booking_jobs to snipe_targets (not subquery) per research anti-patterns"
  - "Use COALESCE(bj.class_datetime, bj.scheduled_for) for booking_jobs event time — class_datetime is actual class time when known"
metrics:
  duration: "~1 minute"
  completed_date: "2026-02-27"
  tasks_completed: 2
  files_changed: 3
---

# Phase 02 Plan 02: Calendar API Endpoint Summary

PostgreSQL UNION ALL calendar endpoint merging booking_history, pending booking_jobs, and configured snipe_targets into a single CalendarEvent[] response for any 7-day window.

## What Was Built

### Task 1: CalendarEvent Type (commit 666d39e)

Added three type exports to `packages/shared/src/types.ts`:

```typescript
export type CalendarEventType = 'booked' | 'failed' | 'pending' | 'configured';
export type CalendarEventSource = 'history' | 'job' | 'target';

export interface CalendarEvent {
  id: string;
  event_date: string;        // "YYYY-MM-DD"
  event_time: string | null;  // "H:MM AM" format — null for Arketa any-slot targets
  studio_slug: string;
  event_type: CalendarEventType;
  source: CalendarEventSource;
  meta: Record<string, unknown>;
}
```

Re-exported from `web/src/lib/types.ts` for use by web API routes and future UI components.

### Task 2: GET /api/calendar Route (commit 1ce0a7b)

Created `web/src/app/api/calendar/route.ts` with:

- Auth guard: `getSession()` returns 401 if unauthenticated
- Param validation: `weekStart` required, regex `/^\d{4}-\d{2}-\d{2}$/`, returns 400 with clear message on invalid input
- UNION ALL SQL with CTE `week_bounds` across 4 branches:
  1. `booking_history` — booked/failed events by `class_date`
  2. `booking_jobs` — pending/claimed/running events, LEFT JOIN to `snipe_targets` for `studio_slug`, COALESCE(class_datetime, scheduled_for) AT TIME ZONE 'America/New_York'
  3. `snipe_targets` recurring — day_of_week expansion formula to compute exact date in 7-day window
  4. `snipe_targets` one_time — filter by `target_date` within window
- ORDER BY `event_date, event_time NULLS LAST`
- Error handling: try/catch with `console.error('[calendar] GET error:', err)`, returns 500

## Verification Results

- `npx tsc --noEmit -p web/tsconfig.json`: zero errors in plan files (pre-existing unrelated error in dashboard/page.tsx is out of scope)
- `npm run web:build`: completed successfully, `/api/calendar` appears in route list
- `grep -c "UNION ALL" route.ts`: 3 (connecting 4 branches)

## Deviations from Plan

None — plan executed exactly as written.

## API Contract

```
GET /api/calendar?weekStart=YYYY-MM-DD
Authorization: via httpOnly cognito cookies

200 OK → CalendarEvent[]
400 Bad Request → { error: "weekStart query parameter is required (YYYY-MM-DD)" }
401 Unauthorized → { error: "Unauthorized" }
500 Internal Server Error → { error: "Internal server error" }
```

## Self-Check: PASSED
