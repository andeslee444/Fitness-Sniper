# Phase 6: Empty States and Onboarding - Research

**Researched:** 2026-03-14
**Domain:** React/Next.js onboarding UX, empty state patterns, worker-status alerting
**Confidence:** HIGH

---

## Summary

Phase 6 is the final polish phase. The codebase is already feature-complete; this phase adds the guidance layer that makes the product usable for a brand-new friend with no prior context. Three requirements: (1) empty states on the targets page that explain the three setup steps, (2) a prominent worker-offline banner visible across all dashboard pages, and (3) a linear guided onboarding flow (pick studios → add creds → browse schedule → create first snipe).

All three requirements are achievable with zero new dependencies. The design language is fully established (dark mode, emerald/red/yellow traffic-light semantics, Tailwind v4, shadcn/ui components, Radix Dialog/Sheet primitives). The `WorkerStatus` component already polls `/api/worker-status` every 30s — the offline state just needs to be elevated from a small icon in the page header to a layout-level banner. The onboarding flow should be a URL-parameter-driven multi-step view rendered inside the existing `(dashboard)` layout, not a separate wizard route.

**Primary recommendation:** Implement in two plans — Plan 06-01 covers empty states (targets page, history page, dashboard no-targets calendar) plus the worker-offline banner in the layout. Plan 06-02 implements the guided onboarding flow with a step-router approach, persisting completion state in the database or a simple `profiles.onboarding_completed` flag. No new dependencies required.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ONBD-01 | New users with no targets see clear empty state guidance explaining the 3 steps to get started | Targets page has a minimal placeholder empty state today (`No targets yet. Add one to start auto-booking.`). Needs enrichment with three numbered steps and CTAs linking to /credentials, /schedule. |
| ONBD-02 | Worker offline status displayed prominently with a banner/alert when daemon hasn't sent heartbeat recently | `WorkerStatus` component already fetches `/api/worker-status` with 30s refetch. Threshold is currently 60s; requirement specifies 5 minutes. Banner should be added to `(dashboard)/layout.tsx` as a client component wrapper. |
| ONBD-03 | Guided onboarding flow: pick studios → add credentials → browse schedule → create first snipe | No onboarding flow exists. Best approach is a step-state component mounted in the layout or a full-page `/onboarding` route driven by URL step param. Completion persisted server-side so refresh doesn't reset flow. |
</phase_requirements>

---

## Standard Stack

### Core (all already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React + Next.js | 19 / 16.1.6 | UI and routing | Project stack |
| Tailwind v4 | 4.x | Styling | Project stack |
| radix-ui | 1.4.3 | Dialog, Sheet, Portal primitives for onboarding overlay | Already used for SnipeConfigSheet, AddTargetDialog |
| TanStack Query | 5.x | Worker status polling | Already used for `WorkerStatus` 30s poll |
| lucide-react | latest | Icons for empty state illustrations | Already used everywhere |
| sonner | latest | Toast notifications | Already installed |

### No New Dependencies Needed
The entire phase can be built with the existing stack. The temptation to reach for a step-wizard library (e.g., `react-joyride`, `shepherd.js`) should be avoided — those tools are designed for DOM overlay tutorials, not linear onboarding flows. A simple step index with conditional rendering and URL query params is the correct approach at this scale.

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom step router | `react-joyride` | `joyride` does DOM overlay popovers, not linear setup flows — wrong tool for this. Custom is cleaner and less brittle. |
| Custom banner | `react-hot-toast` sticky toasts | Sticky toasts are ephemeral and don't persist across navigation. A layout-level `<div>` banner is simpler and more reliable. |

---

## Architecture Patterns

### Existing Empty State Pattern (to extend)
The codebase has minimal empty states today. The existing patterns are:

```tsx
// TargetsList — current empty state (too thin)
if (targets.length === 0) {
  return (
    <div className="rounded-2xl border border-dashed border-white/10 p-12 text-center">
      <p className="text-zinc-500">No targets yet. Add one to start auto-booking.</p>
    </div>
  );
}

// HistoryPage — current empty state
<div className="rounded-2xl border border-dashed border-white/10 p-12 text-center">
  <p className="text-zinc-500">No bookings yet. Once the worker books a class, it will appear here.</p>
</div>
```

The enriched pattern for ONBD-01 should replace the targets empty state with numbered steps:

```tsx
// NEW: Enriched empty state for TargetsList when user has no targets
<div className="rounded-2xl border border-dashed border-white/10 p-10 text-center">
  <p className="mb-6 text-lg font-semibold text-white">Get started in 3 steps</p>
  <div className="mx-auto max-w-sm space-y-4 text-left">
    <Step number={1} done={hasCredentials} label="Add your studio credentials" href="/credentials" />
    <Step number={2} done={false} label="Browse the class schedule" href="/schedule" />
    <Step number={3} done={false} label="Create your first snipe target" href="/schedule" />
  </div>
</div>
```

The `hasCredentials` prop flows from the server component (`targets/page.tsx` already queries the DB) — add a parallel query for `studio_credentials`.

### Worker-Offline Banner Pattern (ONBD-02)

The current `WorkerStatus` lives inside `dashboard/page.tsx` header — only visible on the dashboard. The requirement says "every dashboard page."

The correct insertion point is `(dashboard)/layout.tsx`. Since layout is a server component, the banner itself must be a `'use client'` component that owns the polling:

```tsx
// (dashboard)/layout.tsx — add WorkerOfflineBanner inside the layout
export default async function DashboardLayout({ children }) {
  const user = await getSession();
  if (!user) redirect('/login');

  return (
    <div className="min-h-screen bg-black text-white">
      <NavBar userEmail={user.email || ''} />
      <WorkerOfflineBanner />   {/* NEW — client component, self-contained */}
      <main className="mx-auto max-w-6xl px-4 py-6 pb-24 sm:px-6 sm:py-8 sm:pb-8">
        {children}
      </main>
    </div>
  );
}
```

The banner component reuses the existing `QUERY_KEYS.workerStatus` key so it shares the cache with the existing `WorkerStatus` component — no extra network requests:

```tsx
'use client';
export function WorkerOfflineBanner() {
  const { data: worker } = useQuery<WorkerHeartbeat | null>({
    queryKey: QUERY_KEYS.workerStatus,   // shared key — reuses cached data
    queryFn: async () => { /* same as WorkerStatus */ },
    refetchInterval: 30_000,
  });

  // ONBD-02: offline = no heartbeat in >5 minutes (300,000 ms)
  const OFFLINE_THRESHOLD_MS = 5 * 60 * 1000;
  const isOffline = !worker || (Date.now() - new Date(worker.last_heartbeat).getTime() > OFFLINE_THRESHOLD_MS);

  if (!isOffline) return null;

  return (
    <div className="border-b border-red-500/30 bg-red-500/10 px-4 py-2.5 text-center text-sm text-red-400">
      Worker is offline — automatic booking is paused. Start the worker daemon on your Mac Mini.
    </div>
  );
}
```

**Critical detail:** The existing `WorkerStatus` component uses a 60-second threshold for its `isOnline` check. ONBD-02 specifies 5 minutes (300s) for the banner. These are two different components with different thresholds — that is intentional. The navbar dot remains a fine-grained "is the process alive" indicator; the banner is a "should the user worry" indicator.

### Guided Onboarding Flow Pattern (ONBD-03)

The success criterion specifies a linear sequence that users "cannot accidentally skip." The recommended approach:

**Option A: URL-based step router (recommended)**
- Route: `/onboarding?step=1` (or `1`, `2`, `3`, `4`)
- Steps: `pick-studios` → `add-credentials` → `browse-schedule` → `create-snipe`
- Completion: stored in `profiles.onboarding_completed = true` via DB + cookie
- New users detected: check `profiles.onboarding_completed` in the `(dashboard)/layout.tsx` server component — redirect to `/onboarding` if false and user has no targets

**Option B: Overlay/sheet over existing pages**
- A full-page `Sheet` or `Dialog` that walks through steps while the underlying dashboard is visible
- More complex, harder to deep-link, harder to test

**Recommendation: Option A** — a dedicated `/onboarding` route is cleaner, bookmarkable, and easier to implement without state management complexity.

The key constraint from ONBD-03: "linear sequence they cannot accidentally skip." This means:
1. Step navigation should only allow moving forward via completing an action (not just clicking "Next")
2. Back navigation is allowed but not required
3. The flow should be dismissible by a user who already has targets (edge case: user cleared targets)

**Completion persistence:** The `profiles` table already exists with `subscription_tier` and `display_name`. The planner should consider adding `onboarding_completed boolean DEFAULT false` in a migration (or use a lightweight cookie if DB migration feels too heavy for this final phase).

**Alternative (lighter weight):** Check for `snipe_targets` count on layout load — if zero AND no credentials, redirect to `/onboarding`. This avoids any DB migration. The downside: a user who completed onboarding and then deleted all targets gets redirected again. For a 5-10 user personal tool, this tradeoff is acceptable.

```tsx
// Lightweight redirect trigger (no migration needed)
// In (dashboard)/layout.tsx:
const { rows: creds } = await query('SELECT 1 FROM studio_credentials WHERE user_id = $1 LIMIT 1', [user.sub]);
const { rows: targets } = await query('SELECT 1 FROM snipe_targets WHERE user_id = $1 LIMIT 1', [user.sub]);
const isNewUser = creds.length === 0 && targets.length === 0;
if (isNewUser) redirect('/onboarding');
```

### Recommended Project Structure for New Files

```
web/src/
├── app/
│   ├── (dashboard)/
│   │   ├── layout.tsx              # MODIFY: add WorkerOfflineBanner
│   │   └── targets/
│   │       └── page.tsx            # MODIFY: pass hasCredentials to TargetsTabs
│   └── onboarding/
│       └── page.tsx                # NEW: onboarding multi-step page (server component shell)
├── components/
│   ├── worker-offline-banner.tsx   # NEW: layout-level offline alert
│   ├── empty-state.tsx             # NEW: reusable empty state component
│   └── onboarding/
│       └── onboarding-flow.tsx     # NEW: client component with step state
```

### Anti-Patterns to Avoid

- **Putting the banner in NavBar:** NavBar is already complex (desktop + mobile). Separate concerns — banner is its own component in the layout.
- **Using `window.localStorage` for onboarding completion:** Server-side check prevents flash. localStorage check happens after hydration, causing visible redirect flicker.
- **Overriding `WorkerStatus` threshold:** Keep the existing 60s dot and add a new 5-min banner. Don't change WorkerStatus — it's used in dashboard header and serves a different purpose.
- **Multi-step Dialog:** A Dialog mounted at layout level with `open` driven by onboarding state will conflict with other dialogs (AddTargetDialog, SnipeConfigSheet). Use a dedicated route.
- **Skipping the `hasCredentials` check in empty state:** ONBD-01 says "explains the three steps" — step 1 (add credentials) should be visually marked as done if the user already has credentials saved. This makes the empty state adaptive, not static.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Step progress indicator | Custom SVG stepper | CSS flex with numbered circles + line connectors | Simpler, no library needed, matches dark design |
| Worker status polling | New fetch in banner | Reuse `QUERY_KEYS.workerStatus` with TanStack Query | Shared cache — no duplicate network requests |
| Studio selector in onboarding | Custom multi-select | Checkbox grid using existing `STUDIOS` constant | Already have studio data; checkbox + CSS grid is sufficient |
| Onboarding completion state | Zustand/Redux | DB column or lightweight redirect logic | Only 5-10 users; global state management is overkill |

**Key insight:** This phase is UI-only complexity. The backend already provides all data needed (credentials, targets, worker heartbeat). The challenge is surfacing it in the right place with the right visual weight.

---

## Common Pitfalls

### Pitfall 1: Layout hydration mismatch with client-only banner
**What goes wrong:** `WorkerOfflineBanner` uses `Date.now()` to check staleness, causing SSR/hydration mismatch because server renders at one time and client hydrates at another.
**Why it happens:** The banner returns `null` until data loads, so it never renders on the server anyway — this is fine. But if someone tries to pre-render based on `worker.last_heartbeat`, that would mismatch.
**How to avoid:** Return `null` from `WorkerOfflineBanner` until `useQuery` data is available (which it never is on the server). The pattern is identical to `WorkerStatus` — safe as-is.
**Warning signs:** Hydration error in browser console.

### Pitfall 2: Onboarding redirect loop
**What goes wrong:** Layout redirects new users to `/onboarding`, but `/onboarding` is inside the `(dashboard)` layout group, which runs the same check → infinite redirect.
**Why it happens:** If the redirect logic runs on the layout for `/onboarding` itself.
**How to avoid:** Either put `/onboarding` outside the `(dashboard)` layout group (its own route group), or exempt `/onboarding` from the redirect check with a pathname guard.
**Warning signs:** Browser stuck in redirect loop, network tab shows 307s.

### Pitfall 3: Empty state flashes on every load
**What goes wrong:** Server component renders empty state, then TanStack Query hydration runs and shows populated state — causing layout shift.
**Why it happens:** Targets page is currently a server component — no hydration issue there. But if targets page is converted to a client component with loading state, empty state could flash.
**How to avoid:** Keep `targets/page.tsx` as a server component (it already is). The empty state is rendered server-side with the correct data, so no flash.
**Warning signs:** Brief flash of "Get started in 3 steps" before targets appear.

### Pitfall 4: Onboarding "pick studios" step is confusing
**What goes wrong:** Users see all 10 studios and don't know which to pick. They abandon at step 1.
**Why it happens:** The studio list (10 studios) shown without context (what each is, whether user is a member) overwhelms new users.
**How to avoid:** The pick-studios step should show studio cards with brief descriptions and a note: "Pick studios you have memberships at." Emphasize that they'll add credentials next. The `STUDIOS` object has `name` but no description — the planner may need to add short descriptions inline in the onboarding component.
**Warning signs:** User confusion in user testing about what "pick studios" means.

### Pitfall 5: Worker offline threshold mismatch
**What goes wrong:** Banner shows "offline" even though the worker just restarted. The worker sends a heartbeat every 30s. With a 5-minute threshold, the banner won't clear until a heartbeat lands.
**Why it happens:** The query refetches every 30s — so the banner correctly clears within 30s of a heartbeat. This is fine.
**How to avoid:** Keep the 30s `refetchInterval` on the banner. Do not use a longer interval thinking it reduces load — 30s is necessary for the banner to clear promptly.

---

## Code Examples

### Empty State Step Component

```tsx
// Source: codebase patterns (targets-list.tsx, job-status-timeline.tsx)
function SetupStep({
  number,
  label,
  done,
  href,
}: {
  number: number;
  label: string;
  done: boolean;
  href: string;
}) {
  return (
    <Link
      href={href}
      className={`flex items-center gap-3 rounded-xl border p-4 transition-colors hover:bg-white/[0.04] ${
        done ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-white/10 bg-white/[0.02]'
      }`}
    >
      <span
        className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-sm font-bold ${
          done ? 'bg-emerald-500 text-black' : 'bg-white/10 text-zinc-400'
        }`}
      >
        {done ? <CheckCircle className="h-4 w-4" /> : number}
      </span>
      <span className={done ? 'text-emerald-400' : 'text-white'}>{label}</span>
      {!done && <ChevronRight className="ml-auto h-4 w-4 text-zinc-600" />}
    </Link>
  );
}
```

### Worker Offline Banner

```tsx
// Source: WorkerStatus pattern + layout structure
'use client';

import { useQuery } from '@tanstack/react-query';
import { AlertTriangle } from 'lucide-react';
import { QUERY_KEYS } from '@/lib/query-keys';
import type { WorkerHeartbeat } from '@/lib/types';

const OFFLINE_THRESHOLD_MS = 5 * 60 * 1000; // 5 minutes per ONBD-02

export function WorkerOfflineBanner() {
  const { data: worker, isLoading } = useQuery<WorkerHeartbeat | null>({
    queryKey: QUERY_KEYS.workerStatus,
    queryFn: async () => {
      const res = await fetch('/api/worker-status');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    },
    refetchInterval: 30_000,
  });

  // Don't show banner while loading (avoids flash)
  if (isLoading) return null;

  const lastHeartbeat = worker?.last_heartbeat ? new Date(worker.last_heartbeat).getTime() : 0;
  const isOffline = !worker || (Date.now() - lastHeartbeat > OFFLINE_THRESHOLD_MS);

  if (!isOffline) return null;

  return (
    <div className="flex items-center justify-center gap-2 border-b border-red-500/30 bg-red-500/10 px-4 py-2.5 text-sm text-red-400">
      <AlertTriangle className="h-4 w-4 shrink-0" />
      <span>
        Worker offline — automatic booking is paused.{' '}
        <span className="text-red-300">Start the worker daemon on your Mac Mini.</span>
      </span>
    </div>
  );
}
```

### Onboarding Flow Step Router

```tsx
// Source: Next.js App Router patterns + existing Sheet/Dialog usage
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

type OnboardingStep = 'pick-studios' | 'add-credentials' | 'browse-schedule' | 'create-snipe';

const STEPS: OnboardingStep[] = ['pick-studios', 'add-credentials', 'browse-schedule', 'create-snipe'];

export function OnboardingFlow({ initialStep = 'pick-studios' }: { initialStep?: OnboardingStep }) {
  const [step, setStep] = useState<OnboardingStep>(initialStep);
  const [selectedStudios, setSelectedStudios] = useState<string[]>([]);
  const router = useRouter();

  function goToNext() {
    const idx = STEPS.indexOf(step);
    if (idx < STEPS.length - 1) {
      setStep(STEPS[idx + 1]);
    }
  }

  async function completeOnboarding() {
    // Mark complete server-side
    await fetch('/api/onboarding/complete', { method: 'POST' });
    router.push('/dashboard');
  }

  // Render current step...
}
```

### Targets Page with hasCredentials prop

```tsx
// Modification to targets/page.tsx — add credential check
export default async function TargetsPage() {
  const user = await getSession();

  const [{ rows: targets }, { rows: creds }] = await Promise.all([
    query<TargetWithJob>(/* existing query */, [user!.sub]),
    query<{ count: string }>('SELECT COUNT(*) as count FROM studio_credentials WHERE user_id = $1', [user!.sub]),
  ]);

  const hasCredentials = parseInt(creds[0]?.count ?? '0', 10) > 0;

  return (
    <div className="space-y-6">
      {/* ...existing header... */}
      <TargetsTabs
        recurring={recurring}
        oneTime={oneTime}
        hasCredentials={hasCredentials}  // NEW prop
      />
    </div>
  );
}
```

---

## Existing Assets Inventory

| Asset | File | Current State | Phase 6 Usage |
|-------|------|--------------|---------------|
| WorkerStatus component | `components/worker-status.tsx` | Polls every 30s, shows dot+label | Keep as-is; add separate WorkerOfflineBanner |
| Worker status API | `app/api/worker-status/route.ts` | Returns latest heartbeat row | Reuse — no changes needed |
| QUERY_KEYS.workerStatus | `lib/query-keys.ts` | Defined | Shared between WorkerStatus + banner |
| Targets empty state | `components/targets-list.tsx` lines 62-67 | Single line placeholder | Replace with 3-step guidance component |
| History empty state | `app/(dashboard)/history/page.tsx` lines 97-103 | "No bookings yet" text | Leave as-is (not in ONBD requirements) |
| Dashboard layout | `app/(dashboard)/layout.tsx` | Server component, NavBar + children | Add WorkerOfflineBanner client component |
| STUDIOS constant | `packages/shared/src/studios.ts` | 10 studios with name/config | Used in onboarding studio picker |
| profiles table | DB schema | Has `subscription_tier`, `display_name` | Consider adding `onboarding_completed` column |
| sheet.tsx | `components/ui/sheet.tsx` | Built from Radix Dialog | Available for onboarding overlay if needed |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| setInterval polling | TanStack Query refetchInterval | Phase 2 | WorkerStatus already uses this — banner should match |
| Supabase Auth | AWS Cognito | Initial build | Auth is stable; no changes needed |
| Global stats grid dashboard | Calendar-centered week view | Phase 3 | Onboarding should guide users to calendar as home |

**Deprecated/outdated:**
- `schedule-explorer.tsx` — marked DEPRECATED in Phase 4 comments. Do not reference in onboarding.

---

## Plan Decomposition Recommendation

The roadmap pre-specifies two plans:
- `06-01`: Empty state components (targets, history, dashboard no-targets)
- `06-02`: Worker-offline banner + guided onboarding flow

**Revised recommended split** (after code analysis):

**Plan 06-01 — Empty States + Worker Banner** (simpler, lower risk)
- Replace thin empty states in TargetsList with 3-step guidance (ONBD-01)
- Add WorkerOfflineBanner to dashboard layout (ONBD-02)
- Both are localized, zero API changes

**Plan 06-02 — Guided Onboarding Flow** (ONBD-03, higher complexity)
- New `/onboarding` route (outside or exempt from redirect guard)
- Multi-step client component with studio picker, credential redirect, schedule redirect, snipe CTA
- New `/api/onboarding/complete` POST route (marks completion)
- Lightweight DB check (or profiles column) for new-user detection
- Redirect logic in layout for new users

This split respects the sequential dependency (you need the empty state design language before the onboarding flow references it).

---

## Open Questions

1. **Onboarding completion persistence**
   - What we know: `profiles` table exists. A `boolean DEFAULT false` column is the right approach.
   - What's unclear: Whether adding a migration for a column that only matters for 5-10 users is worth it vs. using the "no targets + no credentials" heuristic.
   - Recommendation: Use the heuristic (no migration needed). If a user deletes all targets, they get the onboarding redirect — acceptable for this audience.

2. **Onboarding route placement**
   - What we know: The `(dashboard)` layout redirects if no session. Onboarding needs auth but cannot be inside the `(dashboard)` group if that group has redirect-to-onboarding logic.
   - What's unclear: Whether to create a separate `(onboarding)` route group or exempt `/onboarding` from the redirect.
   - Recommendation: Exempt `/onboarding` from the redirect with a `pathname !== '/onboarding'` guard in the layout. Simpler than a new route group.

3. **Studio picker in onboarding — what does "pick studios" mean?**
   - What we know: Users will add credentials per-studio. "Picking studios" is really just selecting which studio credentials to add.
   - What's unclear: Should the onboarding studio picker store a preference, or just route to the credentials page pre-filtered?
   - Recommendation: Onboarding step 1 = pick studios (visual selection, stored in component state). Step 2 = redirect to `/credentials` with pre-selected studios highlighted. No new DB column needed.

---

## Sources

### Primary (HIGH confidence)
- Codebase direct inspection — all files read match actual source of truth
- `worker-status.tsx` — existing polling pattern, verified
- `(dashboard)/layout.tsx` — confirmed server component structure
- `targets-list.tsx` — confirmed existing empty state location
- `targets/page.tsx` — confirmed server component with DB query

### Secondary (MEDIUM confidence)
- TanStack Query shared cache behavior — `queryKey` identity guarantees shared cache within same QueryClient provider (standard documented behavior, confirmed by existing Phase 2 patterns in codebase)
- Next.js App Router server component redirect behavior — standard, used in multiple existing pages (`credentials/page.tsx`, `schedule/page.tsx`)

### Tertiary (LOW confidence)
- "5-10 user personal tool" audience assumption for onboarding complexity decisions — inferred from PROJECT.md "initially 5-10 friends"

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies, all existing
- Architecture: HIGH — patterns directly verified from source files
- Pitfalls: HIGH — hydration mismatch and redirect loop are well-known Next.js patterns
- Onboarding flow design: MEDIUM — user experience choices are informed but not user-tested

**Research date:** 2026-03-14
**Valid until:** Stable — no fast-moving dependencies involved. Valid until Next.js 17 or major Radix breaking changes.
