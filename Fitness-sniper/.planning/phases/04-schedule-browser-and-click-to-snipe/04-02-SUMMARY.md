---
phase: 04-schedule-browser-and-click-to-snipe
plan: "02"
subsystem: ui
tags: [react, sheet-drawer, snipe-form, navigation, tanstack-query]

# Dependency graph
requires:
  - phase: 04-01
    provides: Sheet UI primitive, SchedulePanel with onSnipeClick prop, useSnipeMutation hook

provides:
  - SnipeConfigSheet component (slide-in sheet with recurring/one-time snipe config form)
  - SchedulePageClient (client wrapper wiring SchedulePanel to SnipeConfigSheet)
  - Schedule in second nav position (SCHED-01)
  - Browse-to-snipe loop completion (SCHED-02)

affects:
  - web/src/components/nav-bar.tsx (Schedule now second in all nav renders)
  - web/src/app/(dashboard)/schedule/page.tsx (now delegates to SchedulePageClient)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "State reset via useEffect on open: reset targetType and seatPref when sheet opens so stale values never show"
    - "Safe date parsing for dayOfWeek: split('-').map(Number) + new Date(y, m-1, d).getDay() avoids UTC midnight shift"
    - "Client boundary via dedicated *-page-client.tsx: server page.tsx does auth, passes no props to client wrapper"

key-files:
  created:
    - web/src/components/schedule/snipe-config-sheet.tsx
    - web/src/app/(dashboard)/schedule/schedule-page-client.tsx
  modified:
    - web/src/app/(dashboard)/schedule/page.tsx
    - web/src/components/nav-bar.tsx
    - web/src/app/(dashboard)/schedule/schedule-explorer.tsx

key-decisions:
  - "State reset on open (useEffect on open=true) rather than on close — ensures form is fresh even if sheet is re-opened rapidly"
  - "SchedulePageClient is a thin wrapper (no state sharing with page.tsx) — auth stays fully in server component, zero props crossing the boundary"
  - "schedule-explorer.tsx kept (not deleted) with DEPRECATED comment — allows safe rollback until Phase 4 is fully verified"
  - "NAV_ITEMS reorder is a 2-line swap — Dashboard, Schedule, Targets, History, Credentials"

requirements-completed: [SCHED-01, SCHED-02]

# Metrics
duration: 2min
completed: 2026-02-28
---

# Phase 4 Plan 02: SnipeConfigSheet, Schedule Page Wiring, and Nav Reorder Summary

**Slide-in SnipeConfigSheet form with recurring/one-time toggle wired to SchedulePanel via SchedulePageClient, and Schedule promoted to second nav position**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-28T05:32:50Z
- **Completed:** 2026-02-28T05:34:40Z
- **Tasks:** 2
- **Files modified:** 3 modified, 2 created

## Accomplishments

- SnipeConfigSheet: slide-in Sheet with pre-populated class info (studio name, class name, time, instructor, date), one-time/recurring toggle with date/day-of-week labels, seat preference dropdown, Confirm Snipe button with isPending spinner, auto-closes on successful mutation via useSnipeMutation onSuccess callback
- SchedulePageClient: client wrapper wiring SchedulePanel.onSnipeClick to open SnipeConfigSheet with correct selectedClass, studioSlug, and locationId
- Schedule moved to second position in NAV_ITEMS (satisfies SCHED-01)
- page.tsx simplified to server auth check + render SchedulePageClient
- schedule-explorer.tsx marked DEPRECATED (safe to delete post-Phase 4 verification)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create SnipeConfigSheet component** - `dcbb858` (feat)
2. **Task 2: Wire schedule page + reorder nav** - `e09e68a` (feat)

## Files Created/Modified

- `web/src/components/schedule/snipe-config-sheet.tsx` - Slide-in Sheet form; one-time/recurring toggle; seat preference Select; Confirm Snipe calls useSnipeMutation; resets state on open; returns null if no selectedClass
- `web/src/app/(dashboard)/schedule/schedule-page-client.tsx` - Client wrapper holding sheetOpen, selectedClass, snipeStudio, snipeLocation state; wires SchedulePanel.onSnipeClick to populate and open SnipeConfigSheet
- `web/src/app/(dashboard)/schedule/page.tsx` - Now server-only auth check; renders SchedulePageClient (no props)
- `web/src/components/nav-bar.tsx` - NAV_ITEMS reordered: Dashboard, Schedule, Targets, History, Credentials
- `web/src/app/(dashboard)/schedule/schedule-explorer.tsx` - DEPRECATED comment added at top

## Decisions Made

- State reset uses `useEffect` on `open` (not `onOpenChange`) — fires reliably when Radix sets open=true, before any render with stale values
- Safe dayOfWeek parsing: `const [y, m, d] = classDate.split('-').map(Number); new Date(y, m - 1, d).getDay()` — avoids UTC midnight interpretation of ISO date strings (consistent with Phase 1/3 pattern)
- `SchedulePageClient` is stateless relative to the server page — no props pass the client boundary, auth is fully server-side
- `schedule-explorer.tsx` NOT deleted — kept as fallback reference with DEPRECATED comment until Phase 4 is verified end-to-end

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None — TypeScript compiled with zero errors on first attempt. Next.js build succeeded on first run.

## Requirements Completed

- SCHED-01: Schedule appears second in navigation on all dashboard pages
- SCHED-02: User can click "Snipe" on any class, sheet opens with pre-populated config form, supports recurring/one-time, closes on successful creation

## Next Phase Readiness

- Phase 4 is fully complete (Plans 01, 02, 03 all done)
- Phase 5 can consume the targets list and booking history with enriched data
- SnipeConfigSheet is the canonical snipe-creation UX for the /schedule page

---
*Phase: 04-schedule-browser-and-click-to-snipe*
*Completed: 2026-02-28*
