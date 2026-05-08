---
phase: 05-snipe-timeline-and-history
plan: 02
subsystem: ui
tags: [postgresql, react, nextjs, tailwind, shadcn, booking-history]

# Dependency graph
requires:
  - phase: 05-01
    provides: translateJobMessage exported from job-status-timeline.tsx for reuse

provides:
  - booking_history.class_name column populated by on_job_completed trigger via class_schedules lookup
  - /api/history accepts optional ?studio=slug filter parameter for scoped history
  - History page shows class name prominently as primary text (fallback: studio name)
  - Studio filter Select dropdown on history page resets pagination on change
  - Failed booking entries show red prominent messages via translateJobMessage + AlertCircle

affects: [06-onboarding, any phase consuming booking_history table]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - scalar subquery in trigger to avoid duplicate inserts from LEFT JOIN with multiple rows
    - T00:00:00 suffix on YYYY-MM-DD strings to prevent UTC midnight date shift
    - Dynamic WHERE clause with baseParams/dataParams split for COUNT vs paginated queries
    - studioFilter in useCallback dep array + separate useEffect triggers fetch+reset

key-files:
  created:
    - supabase/migrations/007_history_class_name.sql
  modified:
    - packages/shared/src/types.ts
    - web/src/app/api/history/route.ts
    - web/src/app/(dashboard)/history/page.tsx

key-decisions:
  - "Scalar subquery in trigger (not LEFT JOIN) — avoids duplicate history inserts when class_schedules has multiple rows per timeslot"
  - "baseParams/dataParams split — COUNT query uses baseParams only (no limit/offset), data query adds limit+offset after studio filter"
  - "Separate useEffect on [studioFilter] resets pagination — fetchHistory dep array already includes studioFilter so no double-fetch on mount"
  - "T00:00:00 suffix on class_date parsing — forces local time interpretation, consistent with Phase 1 timezone decisions"
  - "translateJobMessage reused from job-status-timeline.tsx — keeps failure message translation logic DRY across timeline and history"

patterns-established:
  - "Pattern: Dynamic WHERE clause builder — conditions array + baseParams, then extend for pagination"
  - "Pattern: Studio filter Select resets to page 0 via separate useEffect watching filter state"

requirements-completed: [HIST-01, HIST-03]

# Metrics
duration: 1min
completed: 2026-02-28
---

# Phase 5 Plan 2: Booking History Enrichment Summary

**class_name added to booking_history via migration + trigger, /api/history studio filter, and rebuilt history page showing class names, studio dropdown, and prominent failure messages**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-02-28T06:36:55Z
- **Completed:** 2026-02-28T06:38:15Z
- **Tasks:** 2
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments
- Migration 007 adds `class_name` column to `booking_history` and replaces the `on_job_completed` trigger with a version that looks up class name from `class_schedules` via scalar subquery
- `/api/history` now accepts `?studio=slug` to filter results to a single studio, using dynamic WHERE clause with correct parameter indexing for COUNT vs paginated data queries
- History page rebuilt: class name is primary display text (fallback: studio name), studio filter Select in header, failure messages shown in red with AlertCircle icon via `translateJobMessage`

## Task Commits

Each task was committed atomically:

1. **Task 1: Migration, BookingHistory type, history API enrichment** - `4c08e12` (feat)
2. **Task 2: Rebuild history page UI** - `f5fecc6` (feat)

**Plan metadata:** (to follow)

## Files Created/Modified
- `supabase/migrations/007_history_class_name.sql` - ALTER TABLE + updated on_job_completed trigger with scalar subquery for class_name
- `packages/shared/src/types.ts` - Added `class_name: string | null` to BookingHistory interface
- `web/src/app/api/history/route.ts` - Dynamic WHERE clause with optional studio_slug filter; separate baseParams/dataParams/countParams
- `web/src/app/(dashboard)/history/page.tsx` - class_name display, studio Select filter, T00:00:00 date fix, prominent red failure messages

## Decisions Made
- **Scalar subquery over LEFT JOIN in trigger**: The `class_schedules` table can have multiple rows per `(studio_slug, location_id, class_date, class_time)` combo. A LEFT JOIN would create duplicate `booking_history` inserts. A scalar subquery with `LIMIT 1` returns exactly one class_name safely.
- **baseParams/dataParams split**: The COUNT query should not receive `limit`/`offset` params. Created `baseParams = [user.sub, ...optional studio]`, then `countParams = [...baseParams]` and `dataParams = [...baseParams, limit, offset]`. The dynamic `$N` indexing prevents param mismatch bugs.
- **Separate `useEffect` on `[studioFilter]`**: The `fetchHistory` callback already includes `studioFilter` in its dep array (so it re-creates when filter changes). A separate `useEffect([studioFilter])` provides the explicit fetch+reset behavior described in the plan without double-fetching on mount (the initial `useEffect([fetchHistory])` handles first load).
- **T00:00:00 date parsing**: Consistent with Phase 1/3 project pattern for YYYY-MM-DD strings.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- Git `git add` with parentheses in path failed without quoting — used quoted path `"web/src/app/(dashboard)/history/page.tsx"` to resolve.

## User Setup Required
**Database migration required.** Apply `supabase/migrations/007_history_class_name.sql` to production database:
```sql
-- Run on production PostgreSQL:
ALTER TABLE booking_history ADD COLUMN IF NOT EXISTS class_name text;
CREATE OR REPLACE FUNCTION public.on_job_completed() ...
```
Existing history rows will have `class_name = NULL` (handled by fallback to studio name in UI).

## Next Phase Readiness
- Booking history now shows class names — ready for Phase 6 onboarding or any phase building on history data
- Existing history rows show NULL class_name (UI fallback to studio name handles gracefully)
- New bookings from this point forward will capture class_name from class_schedules if available

---
*Phase: 05-snipe-timeline-and-history*
*Completed: 2026-02-28*

## Self-Check: PASSED

- FOUND: supabase/migrations/007_history_class_name.sql
- FOUND: packages/shared/src/types.ts (class_name: string | null in BookingHistory)
- FOUND: web/src/app/api/history/route.ts (studio_slug filter)
- FOUND: web/src/app/(dashboard)/history/page.tsx (studioFilter state + class_name display)
- FOUND: commit 4c08e12 (Task 1)
- FOUND: commit f5fecc6 (Task 2)
- TypeScript: PASSED (npx tsc --noEmit)
- Build: PASSED (npm run web:build)
