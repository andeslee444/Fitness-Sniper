---
phase: 03-calendar-home
plan: "02"
subsystem: web/dashboard
tags: [calendar, dashboard, navigation, week-view]
dependency_graph:
  requires: [03-01]
  provides: [03-03]
  affects: [web/src/app/(dashboard)/dashboard/page.tsx, web/src/components/calendar-view.tsx]
tech_stack:
  added: [date-fns (startOfWeek, addWeeks, subWeeks, addDays, format)]
  patterns: [ET timezone-safe date computation, lazy useState initializer, isLoading vs isFetching skeleton gate]
key_files:
  created:
    - web/src/components/calendar-view.tsx
  modified:
    - web/src/app/(dashboard)/dashboard/page.tsx
decisions:
  - "Use isLoading (not isFetching) to gate skeleton — prevents flash on every 60s background refetch"
  - "Lazy useState initializer (function reference, not call) prevents getInitialWeekStart() running on every render"
  - "Today button recomputes ET week start via getInitialWeekStart() — consistent with initial load"
  - "Complete removal of StatCard, OnboardingStep, stats query — onboarding deferred to Phase 6 with calendar-integrated guidance"
metrics:
  duration: "~72 seconds"
  completed_date: "2026-02-27"
  tasks_completed: 2
  files_modified: 2
requirements: [CAL-01, CAL-02, CAL-03]
---

# Phase 03 Plan 02: CalendarView Wire-up and Dashboard Replace Summary

CalendarView with Monday-anchored week navigation wired to useCalendarQuery; dashboard page rewritten to "Your Week" + WorkerStatus header + CalendarView as sole content element.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create CalendarView component with week navigation | 165138d | web/src/components/calendar-view.tsx |
| 2 | Replace dashboard stats grid with CalendarView | 3793eb8 | web/src/app/(dashboard)/dashboard/page.tsx |

## What Was Built

### Task 1: CalendarView (`web/src/components/calendar-view.tsx`)

A top-level client component that owns week navigation state and renders the WeekGrid:

- `getInitialWeekStart()` — non-exported helper that computes Monday of the current ET week using `toLocaleDateString('en-CA', { timeZone: 'America/New_York' })` (consistent with Phase 1 timezone decision). Safe date parsing via `split('-').map(Number)` avoids UTC-midnight offset bugs.
- `useState(getInitialWeekStart)` — lazy initializer (function reference) so the computation only runs once on mount.
- `useCalendarQuery(weekStart)` — fetches events for the current week; `data` defaults to `[]` via `placeholderData`.
- Week navigation: `goToPrevWeek`, `goToNextWeek`, `goToToday` update `weekStart` state, triggering TanStack Query to fetch the new week's data.
- `isLoading` (not `isFetching`) gates the skeleton — ensures skeleton only appears on initial load, not on every 60s background refetch or week-change navigation (which shows empty grid while fetching via `placeholderData: []`).
- Week label: `"Feb 24 – Mar 2, 2026"` format using em-dash separator.
- Renders `<WeekGrid days={days} events={events} />` from Plan 03-01.

### Task 2: Dashboard Page Rewrite (`web/src/app/(dashboard)/dashboard/page.tsx`)

Complete replacement of the old stats grid with calendar:

- **Removed:** All old imports (`Link`, `Target`, `Clock`, `CheckCircle`, `Wifi`, `ArrowRight`, `KeyRound`, `Crosshair`, `useQuery`, `ActiveJobs`, `StatCardSkeleton`, `QUERY_KEYS`, `JobStatus` type)
- **Removed:** `DashboardStats` interface, stats `useQuery`, computed values (`enabledTargets`, `totalTargets`, `activeJobCount`, `successfulBookings`, `isNewUser`)
- **Removed:** `StatCard` local component, `OnboardingStep` local component (both permanently deleted)
- **New structure:** `"Your Week"` title + `<WorkerStatus />` inline in header + `<CalendarView />` as sole primary content
- Page reduced from 184 lines to 14 lines

## Decisions Made

- **isLoading vs isFetching for skeleton gate:** `isLoading` is true only on initial fetch (no cached data). `isFetching` would be true on every 60s background refetch, causing skeleton flash. Using `isLoading` gives stable UX.
- **Lazy useState initializer:** `useState(getInitialWeekStart)` passes the function reference, so the ET timezone computation only runs once on mount — not on every re-render.
- **Onboarding deferred:** The `OnboardingStep` component (shown to new users with 0 targets) was removed entirely without replacement. Phase 6 will add calendar-integrated onboarding that makes more sense in the week context.
- **Today button placement:** Between the chevrons (not at edge) makes it visually clear it's related to week navigation, not a separate action.

## Verification Results

All plan verification checks passed:
- `CalendarView` imported and rendered in dashboard/page.tsx
- Old stats components removed (grep count = 0)
- `WorkerStatus` inline in page header
- Week navigation functions count = 6 (3 definitions + 3 onClick references)
- ET timezone initialization: `toLocaleDateString('en-CA', { timeZone: 'America/New_York' })`
- Monday week start: `startOfWeek(todayLocal, { weekStartsOn: 1 })`
- TypeScript: zero errors
- Next.js build: succeeded

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

Files exist:
- FOUND: web/src/components/calendar-view.tsx
- FOUND: web/src/app/(dashboard)/dashboard/page.tsx

Commits exist:
- FOUND: 165138d (feat(03-02): create CalendarView component with week navigation)
- FOUND: 3793eb8 (feat(03-02): replace stats grid with CalendarView on dashboard)
