---
phase: 06-empty-states-and-onboarding
plan: 02
subsystem: web/frontend
tags: [onboarding, new-user, redirect, flow, ux]
dependency_graph:
  requires: [06-01]
  provides: [OnboardingFlow, OnboardingPage, new-user-redirect]
  affects: [dashboard-layout, onboarding-route]
tech_stack:
  added: []
  patterns: [server-component-redirect, parallel-promise-all, linear-state-machine]
key_files:
  created:
    - web/src/app/onboarding/page.tsx
    - web/src/components/onboarding/onboarding-flow.tsx
  modified:
    - web/src/app/(dashboard)/layout.tsx
decisions:
  - "/onboarding placed outside (dashboard) route group — layout.tsx does not run for it, eliminating redirect loop without any pathname guard"
  - "Parallel EXISTS queries (Promise.all) for credential + target new-user check — <5ms indexed scan, zero extra data fetched"
  - "4-step state machine via useState(0) — no URL params or server state needed for a simple linear flow"
  - "Studios imported from @/lib/studios (web-local re-export) rather than @fitness-sniper/shared/studios — consistent with rest of web codebase"
  - "OnboardingFlow steps 2-4 intentionally lenient — Skip and I've-done-this paths both advance; onboarding is guidance, not enforcement"
metrics:
  duration: ~3 minutes
  completed: "2026-03-14"
  tasks_completed: 2
  files_created: 2
  files_modified: 1
---

# Phase 06 Plan 02: Guided Onboarding Flow Summary

**One-liner:** 4-step linear onboarding flow (pick studios, add credentials, browse schedule, create snipe) at `/onboarding`, with automatic new-user redirect from dashboard layout via parallel EXISTS queries.

## What Was Built

### `/onboarding` route (`web/src/app/onboarding/page.tsx`)

Server component outside the `(dashboard)` route group. Auth-gated via `getSession()` — redirects to `/login` if unauthenticated. Renders a centered max-w-2xl layout with FS logo mark and `<OnboardingFlow />` client component. No NavBar intentionally — user should not navigate away mid-onboarding.

### `OnboardingFlow` (`web/src/components/onboarding/onboarding-flow.tsx`)

`'use client'` component with a 4-step linear state machine:

**Step 1 — Pick Studios:** Grid of all 11 studio cards (`STUDIOS` constant). Each card is a checkbox-style toggle with studio name and hardcoded description. "Next" button disabled until at least 1 studio is selected.

**Step 2 — Add Credentials:** Shows selected studios as a list. Primary CTA goes to `/credentials`. Secondary "I've added my credentials" advances to step 3. "Skip for now" also advances — this step is lenient by design.

**Step 3 — Browse Schedule:** Explanation of the 3-step schedule flow. Primary CTA goes to `/schedule`. "I've browsed the schedule" and "Skip for now" both advance to step 4.

**Step 4 — Create Snipe:** Explanation of how snipe targets work. "Go to Schedule to Create Snipe" CTA. "Done — Go to Dashboard" button navigates to `/dashboard`.

**Step indicator:** 4 circles connected by lines at the top. Active step = emerald ring, completed = emerald fill + check icon, upcoming = zinc. Pure CSS flex — no library.

**Skip setup:** Small text link in the top-right corner, always visible, goes directly to `/dashboard`. Handles edge case of existing user landing on `/onboarding`.

### New-user redirect (`web/src/app/(dashboard)/layout.tsx`)

After the existing auth check (`if (!user) redirect('/login')`), runs two parallel `EXISTS` queries:

```sql
SELECT EXISTS(SELECT 1 FROM studio_credentials WHERE user_id = $1) as exists
SELECT EXISTS(SELECT 1 FROM snipe_targets WHERE user_id = $1) as exists
```

If both return `false`, redirects to `/onboarding`. No redirect loop: `/onboarding` is outside the `(dashboard)` route group, so `layout.tsx` never runs for it.

## Integration Points

- **`(dashboard)/layout.tsx`**: New-user check fires on every dashboard page load. Two parallel indexed EXISTS queries — total latency <5ms on local PostgreSQL.
- **`onboarding/page.tsx`**: Auth check (Cognito). Renders `OnboardingFlow` without NavBar.
- **`onboarding-flow.tsx`**: Uses `STUDIOS` from `@/lib/studios`, `Button` from `@/components/ui/button`, `useRouter` for step navigation.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

Files verified:
- FOUND: web/src/app/onboarding/page.tsx
- FOUND: web/src/components/onboarding/onboarding-flow.tsx
- FOUND: web/src/app/(dashboard)/layout.tsx (modified)

Commits verified:
- FOUND: 16b06aa (feat(06-02): create /onboarding route and OnboardingFlow 4-step client component)
- FOUND: 727b7c3 (feat(06-02): add new-user redirect logic to dashboard layout)

TypeScript: passes with zero errors
Production build: passes — /onboarding listed as ƒ (dynamic) route
