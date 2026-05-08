---
phase: 01-infrastructure-hardening
plan: 03
subsystem: scheduler, targets-api, schedules-api, shared-types
tags: [timezone, error-handling, type-safety, normalization]
dependency_graph:
  requires: []
  provides: [NormalizedClass, normalizeClass, timezone-safe-date-utils]
  affects: [worker/src/jobs/scheduler.ts, web/src/app/api/targets/route.ts, web/src/app/api/targets/[id]/route.ts, web/src/app/api/schedules/route.ts, packages/shared/src/types.ts]
tech_stack:
  added: []
  patterns: [ET-timezone-explicit, normalizer-at-api-boundary, structured-error-logging]
key_files:
  created: []
  modified:
    - worker/src/jobs/scheduler.ts
    - web/src/app/api/targets/route.ts
    - web/src/app/api/targets/[id]/route.ts
    - packages/shared/src/types.ts
    - web/src/app/api/schedules/route.ts
decisions:
  - "Use toLocaleDateString('en-CA', { timeZone: 'America/New_York' }) for explicit ET date computation instead of server-local getDay()"
  - "NormalizedClass placed in shared/types.ts so both web and worker can reference it"
  - "normDb() local helper used instead of modifying ScheduleRow to match ClassScheduleRow shape"
  - "studioSlug/locationId const captures used to satisfy TypeScript closure narrowing inside nested functions"
metrics:
  duration_seconds: 233
  completed_date: "2026-02-26"
  tasks_completed: 2
  files_modified: 5
---

# Phase 1 Plan 3: Timezone Bug Fix and NormalizedClass Type Summary

**One-liner:** Timezone-safe date computation using explicit America/New_York locale formatting, NormalizedClass type with normalizeClass() applied at the schedules API boundary.

## What Was Built

### Task 1: Timezone-safe date computation and error wrapping

**Problem:** `getNextClassDate` in `worker/src/jobs/scheduler.ts` and `getClassDate` in `web/src/app/api/targets/route.ts` both used `new Date().getDay()` which returns the server's local day-of-week. When the worker runs on a server not in ET (e.g., UTC+0), this produces wrong class dates — a Sunday at 11:59 PM UTC is still Saturday in New York.

**Fix applied across 3 files:**

`worker/src/jobs/scheduler.ts`:
- `getNextClassDate`: Replaced `new Date().getDay()` with `toLocaleDateString('en-CA', { timeZone: 'America/New_York' })` to get today's date in ET as `YYYY-MM-DD`. Day-of-week extracted via `new Date(etTodayStr + 'T12:00:00').getDay()` (noon avoids DST edge case).
- `isInBookingWindow`: Replaced `new Date()` with an explicit ET midnight boundary.

`web/src/app/api/targets/route.ts`:
- `getClassDate` recurring branch: Same ET pattern, with ET current-time comparison before pushing to next week.
- GET handler: Wrapped `query(...)` in try/catch returning `{ error: 'Internal server error' }` on failure.
- POST handler: Wrapped entire body in outer try/catch; inner job-creation try/catch preserved.

`web/src/app/api/targets/[id]/route.ts`:
- PUT handler: Wrapped body in try/catch with `console.error('[targets] PUT error:', err)`.
- DELETE handler: Wrapped body in try/catch with `console.error('[targets] DELETE error:', err)`.

### Task 2: NormalizedClass type and schedules API normalization

**Problem:** `ClassScheduleRow` has nullable `class_name`, `instructor`, `duration_minutes`, and `spots_remaining`. UI components that call `.substring()` on instructor crash on null values.

**`packages/shared/src/types.ts`** — added after `ClassScheduleRow`:
- `NormalizedClass` interface: all display string fields non-null (`class_name: string`, `instructor: string`, `duration_minutes: number`, `spots_remaining: number`).
- `normalizeClass(row, studioName)` function: maps `ClassScheduleRow` → `NormalizedClass` with fallbacks (`instructor || 'Staff'`, `class_name || studioName`, `duration_minutes ?? 60`, `spots_remaining ?? 0`).

**`web/src/app/api/schedules/route.ts`** — normalizer applied at all 5 response paths:
1. **Path 1** — Single-date DB hit: `rows.map(normDb)` using local `normDb()` helper
2. **Path 2** — No-location DB fallback: `dbFallbackRows.map(normDb)`
3. **Path 3** — In-memory cache hit: `cached.data.map(norm)` using `norm = (c) => normalizeClass(c, studioName)`
4. **Path 4** — Live API result (including merged DB/range data): `classes.map(norm)`
5. **Path 5** — DB fallback on API failure: `dbFallbackRows.map(normDb)`

Also fixed `nextOccurrence()` in schedules route to use ET timezone (was the same `getDay()` bug).

Added `booking_opens_at` field to all response objects (`null` for DB rows, `c.booking_opens_at` for API rows).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] nextOccurrence was in schedules/route.ts, not targets/route.ts**
- **Found during:** Task 1 verification
- **Issue:** Plan stated "Also fix the `nextOccurrence` helper function (line 27-34) in `targets/route.ts`" but `nextOccurrence` is in `web/src/app/api/schedules/route.ts` line 27. `targets/route.ts` has no `nextOccurrence` function.
- **Fix:** Applied the ET timezone fix to `nextOccurrence` in `schedules/route.ts` instead (correct file).
- **Files modified:** `web/src/app/api/schedules/route.ts`
- **Commit:** `8ea1c36`

**2. [Rule 1 - Bug] TypeScript closure narrowing issue in nested normDb function**
- **Found during:** Task 2 TypeScript compilation
- **Issue:** `studio` variable typed as `string | null` from `searchParams.get()`. After `if (!studio)` guard, TypeScript narrows it in the outer scope but NOT inside nested function closures — TS error `Type 'string | null' is not assignable to type 'string'`.
- **Fix:** Captured narrowed values in explicit `const studioSlug = studio as string` and `const locationId = location || ''` before the nested functions.
- **Files modified:** `web/src/app/api/schedules/route.ts`
- **Commit:** `8ea1c36`

## Commits

| Hash | Message |
|------|---------|
| `28e2be1` | fix(01-03): timezone-safe date computation and error wrapping in targets routes |
| `8ea1c36` | feat(01-03): add NormalizedClass type and apply normalizer in schedules API |

## Self-Check

Files verified:
- `worker/src/jobs/scheduler.ts` — contains 4 `America/New_York` references, 0 `now.getDay()` calls
- `web/src/app/api/targets/route.ts` — contains 2 `America/New_York` references, try/catch in GET and POST
- `web/src/app/api/targets/[id]/route.ts` — try/catch in PUT and DELETE
- `packages/shared/src/types.ts` — exports `NormalizedClass` and `normalizeClass`
- `web/src/app/api/schedules/route.ts` — applies normalization at all 5 response paths

TypeScript: Both `web/tsconfig.json` and `worker/tsconfig.json` compile with zero errors.

## Self-Check: PASSED
