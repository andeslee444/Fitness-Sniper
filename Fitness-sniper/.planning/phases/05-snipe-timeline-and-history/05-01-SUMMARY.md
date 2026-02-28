---
phase: 05-snipe-timeline-and-history
plan: 01
subsystem: ui
tags: [react, typescript, lucide-react, tailwind, timeline, countdown]

# Dependency graph
requires:
  - phase: 04-schedule-browser-click-to-snipe
    provides: TargetWithJob type and targets page foundation

provides:
  - 4-step horizontal job status timeline component (Scheduled → Waiting → Attempting → Result)
  - Live browser-side countdown timer for pending bookings
  - translateJobMessage helper for actionable failure messages
  - Extended TargetWithJob type with job_created_at and job_claimed_at
  - Enriched LATERAL SQL query selecting created_at and claimed_at from booking_jobs
  - targets-list.tsx updated to render timeline and countdown inline on each target card

affects:
  - 05-02-history (uses JobStatusTimeline pattern for history page)
  - 05-03-dashboard-stats (shares TargetWithJob type)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Client-only countdown using useState lazy initializer + useEffect setInterval to avoid SSR mismatch"
    - "translateJobMessage: centralized failure message translation with actionable language"
    - "Horizontal step timeline: completed=emerald fill, active=blue animate-pulse, failed=red AlertCircle"

key-files:
  created:
    - web/src/components/job-status-timeline.tsx
    - web/src/components/countdown-timer.tsx
  modified:
    - packages/shared/src/types.ts
    - web/src/app/(dashboard)/targets/page.tsx
    - web/src/components/targets-list.tsx

key-decisions:
  - "JobStatusTimeline returns null when jobStatus is null — the existing 'Waiting' badge in targets-list handles the no-job state"
  - "CountdownTimer uses useState(() => target - Date.now()) lazy initializer to prevent SSR/client hydration mismatch"
  - "translateJobMessage exported separately from JobStatusTimeline — reusable by history page and other consumers"
  - "Failure message promoted from text-xs text-red-400/70 to text-sm text-red-400 with AlertCircle icon for visual prominence"
  - "Both JOB_STATUS_CONFIG badge (quick scan) and JobStatusTimeline (full context) kept — serve different user needs"

patterns-established:
  - "Client countdown: useState(() => initialValue) lazy init + setInterval(1000ms) + clearInterval on unmount"
  - "Timeline step state: deriveActiveStep(status) maps JobStatus to 0-3 index; all visual state derived from step index"

requirements-completed: [TRUST-01, TRUST-02, TRUST-03]

# Metrics
duration: 8min
completed: 2026-02-28
---

# Phase 05 Plan 01: Snipe Timeline and Countdown Summary

**4-step horizontal job status timeline and live countdown timer integrated into targets page, with translated failure messages replacing muted raw text**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-02-28T06:30:44Z
- **Completed:** 2026-02-28T06:38:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Created `JobStatusTimeline` component showing Scheduled → Waiting → Attempting → Result steps with timestamps and emerald/blue/red color states
- Created `CountdownTimer` component that ticks every second in the browser showing "Booking opens in Xd Xh" without any server calls
- Exported `translateJobMessage` helper converting raw error strings to actionable user-facing messages
- Extended `TargetWithJob` with `job_created_at`/`job_claimed_at` fields and enriched LATERAL SQL query
- Integrated both components into `targets-list.tsx`, removing the old muted failure message in favor of prominent red AlertCircle display

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend type + LATERAL query + create JobStatusTimeline and CountdownTimer** - `9ce0d39` (feat — committed in previous session as part of combined 05 work)
2. **Task 2: Integrate timeline and countdown into targets-list** - `d6f331e` (feat)

**Plan metadata:** committed in final state update

## Files Created/Modified
- `packages/shared/src/types.ts` - Added `job_created_at` and `job_claimed_at` to TargetWithJob interface
- `web/src/app/(dashboard)/targets/page.tsx` - LATERAL query now selects `created_at, claimed_at` from booking_jobs
- `web/src/components/countdown-timer.tsx` - New: client countdown with setInterval, formats as Xd Xh / Xh Xm / Xm Xs
- `web/src/components/job-status-timeline.tsx` - New: 4-step timeline with deriveActiveStep, translateJobMessage export
- `web/src/components/targets-list.tsx` - Imports and renders JobStatusTimeline + CountdownTimer, removes old failure text

## Decisions Made
- JobStatusTimeline returns null when no job exists — the existing "Waiting" badge already handles the no-job display case
- CountdownTimer uses `useState(() => target - Date.now())` lazy init to avoid SSR/hydration mismatch
- translateJobMessage exported as named export for reuse by history page in Phase 05-02
- Failure message promoted from `text-xs text-red-400/70` to `text-sm text-red-400` with AlertCircle icon — TRUST-03 requirement

## Deviations from Plan

None - plan executed exactly as written.

Note: Task 1 implementation (type extension, LATERAL query update, and new component creation) was performed in the previous session as part of a combined execution that also covered plans 05-02 and 05-03. Task 2 (integration into targets-list) was the only remaining work completed in this session.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- JobStatusTimeline and translateJobMessage available for reuse in 05-02 history page
- CountdownTimer pattern established for any future live-ticking UI needs
- No blockers for 05-02

---
*Phase: 05-snipe-timeline-and-history*
*Completed: 2026-02-28*
