---
phase: 05-snipe-timeline-and-history
plan: 03
subsystem: ui
tags: [react, postgres, tanstack-query, dashboard, sql]

# Dependency graph
requires:
  - phase: 05-snipe-timeline-and-history
    provides: booking_history table with studio_slug column
provides:
  - Per-studio success rate stats query on dashboard stats API
  - StudioSuccessRates component with color-coded success percentages
  - Dashboard page renders per-studio success rates below calendar
affects: [dashboard, history]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - GROUP BY studio_slug SQL aggregation with COUNT FILTER for conditional counts
    - Reuse dashboardStats TanStack Query key to colocate stats data in single fetch

key-files:
  created:
    - web/src/components/studio-success-rates.tsx
  modified:
    - web/src/app/api/dashboard/stats/route.ts
    - web/src/app/(dashboard)/dashboard/page.tsx

key-decisions:
  - "Reuse dashboardStats query key in StudioSuccessRates — single fetch, shared cache, no extra network request"
  - "COUNT(*) FILTER (WHERE status = 'booked') in SQL — database does the aggregation, not JavaScript"
  - "Studios with zero history excluded automatically — GROUP BY only returns rows that exist"
  - "Color thresholds: >=80% emerald, 50-79% yellow, <50% red — consistent with common traffic light semantics"

patterns-established:
  - "SQL GROUP BY aggregation pattern: COUNT(*) FILTER for conditional counts in PostgreSQL"

requirements-completed:
  - HIST-02

# Metrics
duration: 5min
completed: 2026-02-28
---

# Phase 5 Plan 03: Studio Success Rates Summary

**Per-studio success rate stats surfaced on dashboard with SQL GROUP BY aggregation and color-coded TanStack Query component showing booked/total/pct for each studio with 30-day history**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-02-28T00:00:00Z
- **Completed:** 2026-02-28T00:05:00Z
- **Tasks:** 1
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments
- Dashboard stats API now returns studioStats array via SQL GROUP BY query with 30-day window
- New StudioSuccessRates component renders per-studio success rates with emerald/yellow/red color coding
- Dashboard page renders StudioSuccessRates below CalendarView — no new network requests (reuses dashboardStats query cache)
- Studios with zero history do not appear (SQL GROUP BY naturally excludes them)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add studioStats query to dashboard stats API and build StudioSuccessRates component** - `9ce0d39` (feat)

**Plan metadata:** _(final commit after SUMMARY/STATE/ROADMAP update)_

## Files Created/Modified
- `web/src/app/api/dashboard/stats/route.ts` - Added fourth query to Promise.all: GROUP BY studio_slug with COUNT FILTER for booked status, studioStats added to response JSON
- `web/src/components/studio-success-rates.tsx` - New client component; uses dashboardStats query key; renders per-studio rows with name, booked/total counts, and color-coded percentage
- `web/src/app/(dashboard)/dashboard/page.tsx` - Imports and renders StudioSuccessRates below CalendarView

## Decisions Made
- Reused `QUERY_KEYS.dashboardStats` key in StudioSuccessRates so the component shares the dashboard stats cache with no duplicate network requests.
- SQL `COUNT(*) FILTER (WHERE status = 'booked')` pushes conditional aggregation to Postgres rather than filtering in JS.
- Color thresholds: >=80% emerald-400, <50% red-400, else yellow-400 — standard traffic light semantics.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- HIST-02 complete: per-studio success rates visible on dashboard
- Ready to continue with remaining Phase 5 plans (booking history timeline, snipe timeline UI)

---
*Phase: 05-snipe-timeline-and-history*
*Completed: 2026-02-28*
