---
phase: 04-schedule-browser-and-click-to-snipe
plan: "01"
subsystem: ui
tags: [react, tanstack-query, radix-ui, sheet-drawer, schedule-browser]

# Dependency graph
requires:
  - phase: 03-calendar-home
    provides: CalendarView with TanStack Query setup and QUERY_KEYS

provides:
  - Sheet UI primitive (slide-in right drawer from Radix Dialog)
  - SchedulePanel component (full schedule browser with onSnipeClick prop)
  - useSnipeMutation hook (TanStack Query wrapper for POST /api/targets)

affects:
  - 04-02-snipe-config-sheet (uses Sheet, SchedulePanel, useSnipeMutation)
  - 04-03-navigation-and-integration (references SchedulePanel as embedded component)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sheet drawer: Radix Dialog repurposed as slide-in right panel with slide-in-from-right animation"
    - "onSnipeClick prop pattern: SchedulePanel delegates snipe action to parent when prop provided, falls back to inline Popover otherwise"
    - "TanStack Query invalidation: invalidate ['calendar'] partial key (not specific week) so ALL calendar weeks refresh on new recurring target"

key-files:
  created:
    - web/src/components/ui/sheet.tsx
    - web/src/components/schedule/schedule-panel.tsx
    - web/src/hooks/use-snipe-mutation.ts
  modified: []

key-decisions:
  - "Sheet built from Radix Dialog (not Drawer or Sheet library) — consistent with existing dialog.tsx pattern and unified radix-ui package"
  - "onSnipeClick prop on SchedulePanel allows Plan 04-02 to intercept snipe actions for full config sheet without modifying SchedulePanel"
  - "useSnipeMutation invalidates ['calendar'] (not calendarWeek(weekStart)) to cover all weeks for recurring targets"
  - "SchedulePanel exports ScheduleClass and ScheduleResponse interfaces for Plan 04-02 SnipeConfigSheet to consume"
  - "SchedulePanel does NOT import useSnipeMutation — inline Popover uses plain fetch for backward compatibility"

patterns-established:
  - "Sheet pattern: SheetContent wraps SheetPortal + SheetOverlay internally (matches DialogContent pattern)"
  - "Callback delegation: component accepts optional onXClick prop to delegate action to parent, falls back to inline behavior"

requirements-completed: [SCHED-02, SCHED-03]

# Metrics
duration: 3min
completed: 2026-02-28
---

# Phase 4 Plan 01: Sheet Primitive, SchedulePanel, and useSnipeMutation Summary

**Sheet slide-in drawer from Radix Dialog, SchedulePanel with onSnipeClick callback delegation, and TanStack Query mutation hook for snipe target creation with full calendar cache invalidation**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-28T05:28:00Z
- **Completed:** 2026-02-28T05:31:00Z
- **Tasks:** 2
- **Files modified:** 3 created

## Accomplishments

- Sheet UI primitive with slide-in-from-right animation, sm:max-w-md width, Radix Dialog as base
- SchedulePanel component refactored from schedule-explorer.tsx with full schedule browser, class cards, and onSnipeClick callback support
- useSnipeMutation TanStack Query hook wrapping POST /api/targets with cache invalidation for all calendar weeks and targets list

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Sheet UI primitive from Dialog** - `4d9c7ce` (feat)
2. **Task 2: Create SchedulePanel component and useSnipeMutation hook** - `ee1bb6a` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `web/src/components/ui/sheet.tsx` - Slide-in right drawer built from Radix DialogPrimitive.Root; exports Sheet, SheetTrigger, SheetClose, SheetPortal, SheetOverlay, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter
- `web/src/components/schedule/schedule-panel.tsx` - Full schedule browser with studio/location pickers, date navigation, calendar heatmap, class list with availability badges and Snipe buttons; accepts onSnipeClick prop for callback delegation; exports ScheduleClass and ScheduleResponse interfaces
- `web/src/hooks/use-snipe-mutation.ts` - TanStack Query useMutation wrapping POST /api/targets; invalidates ['calendar'] (all weeks) and QUERY_KEYS.targets on success; toast on success/error

## Decisions Made

- Sheet built from Radix Dialog (unified `radix-ui` package) to match dialog.tsx — no new dependencies needed
- SchedulePanel's `onSnipeClick` prop follows a delegation pattern: when provided, clicking Snipe calls the callback (enabling Plan 04-02's SnipeConfigSheet to show a configuration form); when absent, falls back to inline Popover with seat preference selection
- `useSnipeMutation` invalidates `['calendar']` (partial key) rather than a specific week key so ALL cached weeks are refreshed — critical for recurring targets that affect multiple future weeks
- `SchedulePanel` does NOT import `useSnipeMutation` — the inline Popover path uses plain `fetch` to keep SchedulePanel self-contained and avoid TanStack Query coupling in the schedule-explorer.tsx fallback

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None — TypeScript compiled with zero errors on first attempt.

## Next Phase Readiness

- Plan 04-02 can now import `Sheet`, `SheetContent`, `SheetHeader`, etc. from `@/components/ui/sheet`
- Plan 04-02 can import `SchedulePanel` and pass `onSnipeClick` to open the snipe config form
- Plan 04-02 can import `useSnipeMutation` and `SnipePayload` from `@/hooks/use-snipe-mutation`
- Plan 04-02 can import `ScheduleClass` from `@/components/schedule/schedule-panel` for type safety in the config sheet

---
*Phase: 04-schedule-browser-and-click-to-snipe*
*Completed: 2026-02-28*
