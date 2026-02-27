---
phase: 03-calendar-home
plan: "01"
subsystem: calendar-ui
tags: [calendar, components, tanstack-query, tailwind]
dependency_graph:
  requires: [CalendarEvent type from Phase 2 (02-02)]
  provides: [WeekGrid, DayColumn, CalendarEventPill, useCalendarQuery]
  affects: [web/src/components/calendar/, web/src/hooks/]
tech_stack:
  added: []
  patterns: [CSS grid 7-column layout, TanStack Query with placeholderData, event deduplication by studio+time]
key_files:
  created:
    - web/src/components/calendar/calendar-event.tsx
    - web/src/components/calendar/day-column.tsx
    - web/src/components/calendar/week-grid.tsx
    - web/src/hooks/use-calendar-query.ts
  modified: []
decisions:
  - "Do NOT add 'use client' to use-calendar-query.ts — hooks need no directive; client context comes from importing component"
  - "Safe date parsing: split('-').map(Number) + new Date(y, m-1, d) to avoid UTC interpretation of YYYY-MM-DD strings"
  - "ET today check via toLocaleDateString('en-CA', { timeZone: 'America/New_York' }) for consistent timezone handling"
metrics:
  duration: "~2 minutes"
  completed_date: "2026-02-27"
  tasks_completed: 2
  files_created: 4
  files_modified: 0
---

# Phase 3 Plan 01: Calendar UI Components Summary

**One-liner:** 4-file calendar building block — CSS grid WeekGrid, deduplicating DayColumn with ET heatmap, status-colored CalendarEventPill, and 60s-polling useCalendarQuery hook — ready for Plan 03-02 wiring.

## What Was Built

Four new files forming the core calendar UI infrastructure:

1. **`calendar-event.tsx`** — `CalendarEventPill` renders an event with 4 visually distinct treatments:
   - `booked`: emerald-500 background + border
   - `pending`: dashed yellow border + animate-pulse
   - `failed`: red-500 background + border
   - `configured`: dashed zinc-700 border, muted text
   - Looks up studio display name from `STUDIOS[slug]`, shows time if non-null

2. **`day-column.tsx`** — `DayColumn` receives raw events and:
   - Deduplicates by `studio_slug|event_time` key, keeping lowest priority (booked > failed > pending > configured)
   - Applies heatmap tint: 0 events = none, 1-2 = `bg-emerald-500/5`, 3+ = `bg-emerald-500/10`
   - Highlights today's header in emerald using ET timezone via `toLocaleDateString('en-CA', { timeZone: 'America/New_York' })`
   - Parses date safely with `split('-').map(Number)` to avoid UTC-midnight interpretation

3. **`week-grid.tsx`** — `WeekGrid` renders a responsive 7-column CSS grid:
   - `overflow-x-auto` wrapper + `min-w-[560px]` grid for horizontal scroll on mobile
   - Filters events to each column by `event_date === date`

4. **`use-calendar-query.ts`** — `useCalendarQuery(weekStart)` wraps TanStack Query:
   - Fetches `GET /api/calendar?weekStart={weekStart}`
   - 60s `staleTime` + `refetchInterval`
   - `placeholderData: []` for instant empty-grid render on week navigation

## Verification Results

- TypeScript: zero errors (`npx tsc --noEmit -p web/tsconfig.json`)
- Next.js build: succeeded (all routes compiled)
- All 4 key patterns confirmed present via grep checks

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| Hash | Message |
|------|---------|
| 2858fd4 | feat(03-01): create CalendarEventPill and DayColumn components |
| 7ffbf6c | feat(03-01): create WeekGrid component and useCalendarQuery hook |

## Self-Check: PASSED

- FOUND: web/src/components/calendar/calendar-event.tsx
- FOUND: web/src/components/calendar/day-column.tsx
- FOUND: web/src/components/calendar/week-grid.tsx
- FOUND: web/src/hooks/use-calendar-query.ts
- FOUND: commit 2858fd4 (feat(03-01): create CalendarEventPill and DayColumn components)
- FOUND: commit 7ffbf6c (feat(03-01): create WeekGrid component and useCalendarQuery hook)
