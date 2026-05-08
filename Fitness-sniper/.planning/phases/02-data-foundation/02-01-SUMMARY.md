---
phase: 02-data-foundation
plan: "01"
subsystem: web-frontend
tags: [tanstack-query, data-fetching, polling, react, dashboard]
dependency_graph:
  requires: []
  provides: [tanstack-query-provider, query-key-constants, declarative-polling]
  affects: [web/src/app/layout.tsx, web/src/app/(dashboard)/dashboard/page.tsx, web/src/components/active-jobs.tsx, web/src/components/worker-status.tsx]
tech_stack:
  added: ["@tanstack/react-query@5", "@tanstack/react-query-devtools@5"]
  patterns: [QueryClient-provider-singleton, lazy-useState-initializer, refetchInterval-polling, 401-refresh-handler]
key_files:
  created:
    - web/src/lib/query-client.ts
    - web/src/lib/query-keys.ts
    - web/src/components/providers.tsx
  modified:
    - web/src/app/layout.tsx
    - web/src/app/(dashboard)/dashboard/page.tsx
    - web/src/components/active-jobs.tsx
    - web/src/components/worker-status.tsx
decisions:
  - "Use useState(() => makeQueryClient()) lazy initializer — not eager construction — to prevent QueryClient recreation on rerenders"
  - "QueryCache onError handler fires /api/auth/refresh fire-and-forget on HTTP 401; ignores refresh failures so next navigation redirects to login"
  - "ActiveJobs is now fully self-contained — no props passed from dashboard page; handles empty state internally via useQuery default empty array"
  - "isLoading used for skeleton (true only on first fetch), not isFetching (true on every background refetch) — avoids flash on every 30s poll"
  - "refetchIntervalInBackground left as false (default) — auto-pauses polling when browser tab is hidden"
metrics:
  duration: "~2 minutes"
  completed: "2026-02-27"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 4
---

# Phase 02 Plan 01: TanStack Query v5 Provider + Dashboard Polling Migration Summary

TanStack Query v5 installed in web workspace with app-wide QueryClientProvider, typed query key constants, and all three dashboard polling components migrated from manual setInterval to declarative useQuery with refetchInterval — eliminating race conditions, enabling tab-visibility pause, and establishing the foundation for Phase 3+ UI data fetching.

## What Was Built

### Task 1: TanStack Query Provider Infrastructure

**`web/src/lib/query-client.ts`** — Factory function `makeQueryClient()` creating a `QueryClient` with:
- 30-second global `staleTime` (reduces redundant refetches for stable data)
- `QueryCache` `onError` handler that detects `HTTP 401` errors and fires `/api/auth/refresh` fire-and-forget (ignores failures — next navigation redirects to login)

**`web/src/lib/query-keys.ts`** — `QUERY_KEYS` constant with 7 typed tuple key definitions:
- `dashboardStats`, `workerStatus`, `jobs`, `targets` — static keys
- `calendarWeek(weekStart)`, `history(page)`, `schedules(studioSlug, locationId)` — factory keys for parameterized queries

**`web/src/components/providers.tsx`** — `'use client'` `Providers` component using `useState(() => makeQueryClient())` lazy initializer with `QueryClientProvider` wrapper and `ReactQueryDevtools` (tree-shaken in production).

**`web/src/app/layout.tsx`** — Imports `Providers` and wraps `<div id="main-content">` and `<Toaster />` so the entire app has access to the QueryClient.

### Task 2: Dashboard Polling Component Migration

**`web/src/app/(dashboard)/dashboard/page.tsx`**:
- Removed: `POLL_INTERVAL`, `fetchStats` callback, `setInterval` effect, `stats`/`loading` state, `useCallback`/`useEffect`/`useState` imports
- Added: `useQuery({ queryKey: QUERY_KEYS.dashboardStats, refetchInterval: 30_000 })`
- `ActiveJobs` rendered unconditionally without props (self-contained now)
- `isLoading` drives skeleton (not `isFetching`) — no flash on background refetch

**`web/src/components/active-jobs.tsx`**:
- Removed: `Props` interface, `jobs: initialJobs` prop, `useState(initialJobs)`, `setInterval` polling loop
- Added: `useQuery({ queryKey: QUERY_KEYS.jobs, refetchInterval: 15_000 })` with default `jobs = []`
- Component is now fully self-contained — no parent prop threading

**`web/src/components/worker-status.tsx`**:
- Removed: `useState`, `useEffect`, manual `setInterval` fetch loop
- Added: `useQuery({ queryKey: QUERY_KEYS.workerStatus, refetchInterval: 30_000 })`
- Same rendering logic preserved

## Verification

- TypeScript: `npx tsc --noEmit -p web/tsconfig.json` — zero errors
- setInterval grep: 0 matches in all three migrated dashboard components
- Next.js build: `npm run web:build` — compiled successfully (23 static/dynamic pages)

## Commits

| Task | Hash | Message |
|------|------|---------|
| Task 1 | 6d8ecae | feat(02-01): install TanStack Query v5 and create provider infrastructure |
| Task 2 | 23c333a | feat(02-01): migrate dashboard polling components to TanStack Query |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED
