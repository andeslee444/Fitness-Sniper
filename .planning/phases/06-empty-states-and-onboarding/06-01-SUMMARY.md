---
phase: 06-empty-states-and-onboarding
plan: 01
subsystem: web/frontend
tags: [empty-state, onboarding, worker-status, ux]
dependency_graph:
  requires: []
  provides: [EmptyStateGuide, WorkerOfflineBanner]
  affects: [targets-page, dashboard-layout]
tech_stack:
  added: []
  patterns: [shared-query-key-cache, parallel-promise-all, adaptive-ui]
key_files:
  created:
    - web/src/components/empty-state.tsx
    - web/src/components/worker-offline-banner.tsx
  modified:
    - web/src/app/(dashboard)/targets/page.tsx
    - web/src/app/(dashboard)/targets/targets-tabs.tsx
    - web/src/components/targets-list.tsx
    - web/src/app/(dashboard)/layout.tsx
decisions:
  - "WorkerOfflineBanner uses QUERY_KEYS.workerStatus (shared with WorkerStatus dot) — reuses cached data, zero extra network requests"
  - "5-minute offline threshold for banner vs 60-second for dot indicator — different UX goals: banner only for extended outage, dot is real-time status"
  - "hasCredentials passed from server component (parallel DB query) — avoids client-side fetch waterfall for credential check"
  - "EmptyStateGuide replaces both recurring and one-time empty states via shared hasCredentials prop through TargetsTabs"
metrics:
  duration: ~2 minutes
  completed: "2026-03-14"
  tasks_completed: 2
  files_created: 2
  files_modified: 4
---

# Phase 06 Plan 01: Empty States and Worker Offline Banner Summary

**One-liner:** 3-step onboarding card on empty targets page with adaptive credential check, plus layout-level worker-offline red banner polling every 30s with 5-minute stale threshold.

## What Was Built

### EmptyStateGuide (`web/src/components/empty-state.tsx`)

A `'use client'` component exported as `EmptyStateGuide({ hasCredentials: boolean })`. Replaces the plain "No targets yet" placeholder with a 3-step guidance card:

1. **Add your studio credentials** (`/credentials`) — shows green check mark when `hasCredentials=true`
2. **Browse the class schedule** (`/schedule`) — always shows numbered step
3. **Create your first snipe target** (`/schedule`) — always shows numbered step

Each step is a `Link` with Tailwind classes that respond to `done` state: emerald border/background when complete, default border when pending. Uses `Check` and `ChevronRight` from `lucide-react`.

### WorkerOfflineBanner (`web/src/components/worker-offline-banner.tsx`)

A `'use client'` banner that polls `/api/worker-status` every 30 seconds using `QUERY_KEYS.workerStatus` — the **same query key** used by the existing `WorkerStatus` dot indicator in the nav. This means:
- Zero duplicate network requests (TanStack Query deduplicates via shared key)
- Banner disappears within 30s of worker resuming
- `isLoading` guard prevents SSR hydration mismatch (returns `null` during initial load)

Offline threshold: **5 minutes** (vs the dot indicator's 60-second threshold). The banner is a higher-severity, longer-lag signal — only shown when the worker has been truly absent for an extended time.

## Integration Points

- **`layout.tsx`**: Server component imports `WorkerOfflineBanner` (client component) and inserts it between `<NavBar>` and `<main>` — renders on every dashboard page automatically.
- **`targets/page.tsx`**: Uses `Promise.all` to fetch targets and credential count in parallel. Derives `hasCredentials: boolean` and passes it to `TargetsTabs`.
- **`targets-tabs.tsx`**: Forwards `hasCredentials` prop to both `TargetsList` (recurring and one-time tabs).
- **`targets-list.tsx`**: Accepts optional `hasCredentials?: boolean`, replaces old empty state with `<EmptyStateGuide hasCredentials={hasCredentials ?? false} />`.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

Files verified:
- FOUND: web/src/components/empty-state.tsx
- FOUND: web/src/components/worker-offline-banner.tsx
- FOUND: web/src/app/(dashboard)/layout.tsx
- FOUND: web/src/app/(dashboard)/targets/page.tsx

Commits verified:
- FOUND: 8e368ec (feat(06-01): create EmptyStateGuide and WorkerOfflineBanner components)
- FOUND: fc77585 (feat(06-01): wire EmptyStateGuide and WorkerOfflineBanner into pages)

TypeScript: passes with zero errors
Production build: passes with zero errors/warnings
