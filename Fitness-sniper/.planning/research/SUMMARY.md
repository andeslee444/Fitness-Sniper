# Project Research Summary

**Project:** Fitness Sniper — Calendar-Centered Dashboard Rebuild
**Domain:** Automated fitness class booking dashboard with real-time job status
**Researched:** 2026-02-26
**Confidence:** HIGH

## Executive Summary

Fitness Sniper's booking engine is complete and reliable; this milestone is a frontend upgrade — not a backend rebuild. The central challenge is closing a trust gap: automated booking systems succeed or fail based on whether users believe the system is aware of their classes, knows when to act, and will tell them the outcome. Research across features, architecture, stack, and pitfalls consistently returns to one prescription: make the system transparent at every stage. A calendar-centered home view showing confirmed bookings, active snipes, and available slots — plus a per-snipe status timeline — is the pattern that resolves the trust problem directly. Every other feature is secondary to this core loop.

The recommended approach is a focused frontend rebuild using five new dependencies on top of the existing Next.js 16 + Tailwind v4 + shadcn/ui stack: a custom-built weekly calendar component (not react-big-calendar — Tailwind v4 incompatibility), TanStack Query for server state and polling, `motion` for status timeline animations, `date-fns` for timezone-safe date handling, and the existing `sonner` for toast feedback. Real-time job status is achieved via TanStack Query's `refetchInterval` at 10-second intervals — not SSE or WebSockets, both of which are architecturally incompatible with Vercel's serverless function timeout limits. A new `GET /api/calendar?weekStart=` route does server-side JOINs across `booking_history`, `booking_jobs`, and `snipe_targets` to deliver a single merged event list for the calendar, avoiding race conditions from client-side data merging.

The top risks in this rebuild are not technical — they are trust-destroying UX failures. Timezone rendering bugs can show classes on the wrong day (the worker already has a known timezone bug). Optimistic UI on snipe creation will show a "Sniped!" state that persists after a failure the user never sees. Cognito session expiry silently breaks all API calls after 1 hour. These three pitfalls must be addressed before any new UI ships to users. The mitigation is disciplined: pessimistic UI for booking actions, explicit ET timezone rendering everywhere, and a global 401 interceptor with token refresh.

---

## Key Findings

### Recommended Stack

The existing stack (Next.js 16.1.6, React 19.2.3, Tailwind v4, shadcn/ui, PostgreSQL via `pg`) is fixed and correct — nothing is replaced. Five targeted additions fill the gaps: `date-fns` for timezone-aware date handling, `@tanstack/react-query` for polling and cache deduplication, `react-big-calendar` is explicitly rejected in favor of a custom 150-250 line `WeekGrid` component (Tailwind v4 CSS variable incompatibility makes the library integration harder than building the grid), `motion` (the renamed `framer-motion`) for status timeline animations imported via `"motion/react"`, and `sonner` already installed for toasts.

Push notifications (web-push + VAPID) are deferred — email via Resend already covers MVP needs, and push infrastructure adds 3-5 days of work for a 5-10 person audience. No version conflicts are expected; all additions are React 19 and Tailwind v4 compatible.

**Core technologies:**
- `date-fns` v4: All date formatting and timezone display (America/New_York) — replaces ad-hoc Date manipulation; first-class timezone support in v4
- `@tanstack/react-query` v5: Server state, polling, cache — replaces raw `setInterval` loops; conditional `refetchInterval` enables fast polling only during active booking windows
- Custom `WeekGrid` component: Calendar UI — react-big-calendar rejected due to Tailwind v4 CSS variable incompatibility; custom build is ~200 lines
- `motion` (via `"motion/react"`): Status timeline animations — `AnimatePresence` needed for orchestrated multi-step status transitions; CSS transitions cannot animate unmount
- `sonner` 2.0.7 (already installed): Toast notifications — no new dependency needed

### Expected Features

The booking engine works. The product feeling broken is entirely a dashboard UX problem. Table stakes features are already 60-80% implemented in the codebase — they need surfacing and connection, not rebuilding from scratch.

**Must have (table stakes):**
- Calendar view as home screen — users think in weeks, not lists; pending snipes as dashed events, confirmed as solid green, failed as red
- Snipe timeline per target: "Scheduled → Waiting → Attempting → Booked" with booking-opens countdown — the single biggest trust builder; data already exists in DB
- Credential status indicators: "Connected / Untested / Invalid" per studio — silent credential failures destroy trust
- Failure reason visibility — `job_message` exists in DB but is shown in tiny muted text; must be prominent
- Booking history enrichment — add class name, success rate stat, studio filter to existing history page
- Schedule browser prominence — already built at `/schedule`, needs primary navigation position and calendar integration

**Should have (differentiators):**
- Success rate stats per studio — "8/10 Barry's booked (80%)" as a single number on dashboard stat cards
- Next attempt time on target cards — "Next attempt: Mar 3 at 12:00 AM" computable from existing DB data
- Spot confirmation label — "Spot 14 (Back Row)" from `booking_history.spot`, data already stored

**Defer to v2+:**
- In-app notification center — email + toast covers MVP; notification DB table adds significant scope
- Google Calendar sync — OAuth complexity not justified for 5-10 users
- Push notifications (web-push/VAPID) — post-MVP; email sufficient

**Explicit anti-features (do not build):**
- Analytics charts, social features, mobile app, waitlist tracking, complex spot floor plan UI, multi-user admin

### Architecture Approach

The architecture is a frontend-and-API-layer upgrade with the worker daemon, adapters, and database schema treated as fixed constraints. The browser layer is reorganized around a single TanStack Query provider that replaces all existing `setInterval` loops with shared, deduplicated polling. A custom calendar component reads from a new `/api/calendar` server-side JOIN route. The schedule panel opens as a sheet on calendar day click, uses the existing `/api/schedules` route, and feeds into the existing `/api/targets` POST mutation with TanStack Query cache invalidation.

**Major components:**
1. `TanStack Query Provider` — single cache layer in `providers.tsx`, wrapping the dashboard layout; all polling flows through here; `refetchInterval` varies by data type (10s for active jobs, 30s for calendar, 5min for schedule data)
2. Custom `WeekGrid + CalendarEvent` — 7-column CSS grid for week view; three event types with distinct visual treatment (confirmed/green, pending-snipe/yellow-pulse, configured-target/blue); opens `SchedulePanel` on day click
3. `JobStatusTimeline + CountdownTimer` — maps 6 internal DB job states to 4 user-facing states (`scheduled`, `attempting`, `booked`, `failed`); `CountdownTimer` ticks client-side from `booking_opens_at` timestamp; no additional server calls
4. `SchedulePanel + SnipeConfigSheet` — sheet/drawer triggered by calendar interaction; reads from existing schedule API; creates targets via pessimistic mutation (no optimistic UI)
5. `GET /api/calendar` (new route) — PostgreSQL UNION of `booking_history` + `booking_jobs` + projected `snipe_targets`; single round-trip for calendar render; avoids client-side join race conditions

### Critical Pitfalls

1. **Timezone rendering** — Classes stored as UTC display on wrong days in browser local time. Prevention: normalize all datetimes to `America/New_York` via `Intl.DateTimeFormat` at the API boundary; never use bare `new Date()` in components. Also fix the known worker `getNextClassDate` timezone bug in the same milestone.

2. **Optimistic UI on snipe creation** — Showing "Sniped!" before DB confirmation creates a false state that persists through delayed booking failures (days later). Prevention: pessimistic UI only for all booking actions; derive calendar event status exclusively from DB via polling; make failure states loud (red calendar indicator + toast), not silent.

3. **Cognito session expiry** — Access tokens expire after 1 hour; middleware only checks cookie presence; API calls silently return 401 with no user feedback. Prevention: implement `REFRESH_TOKEN_AUTH` flow before shipping; add global TanStack Query `onError` handler that catches 401 and redirects to `/login`.

4. **3-platform data shape mismatch** — MT, Xponential, and Arketa return fundamentally different class objects; `time = null` for Arketa targets causes `.substring()` throws; missing fields show as `undefined` in UI. Prevention: define strict `NormalizedClass` type in shared package; write one normalization function per platform at the API boundary; TypeScript strict mode catches `string | null` misuse at compile time.

5. **Inconsistent API error shapes** — Existing routes return `{ error }`, `{ message }`, or HTML error pages depending on which route handler throws. Prevention: standardize all error responses to `{ error: string, code?: string }` before building new UI on top; add a global fetch wrapper that normalizes errors and checks `Content-Type`.

---

## Implications for Roadmap

The research defines a clear dependency order. Infrastructure must precede UI. Data normalization must precede rendering. Auth hardening must precede user-facing features. The calendar is the centerpiece but cannot be built correctly until the API layer is clean.

### Phase 1: Infrastructure and Auth Hardening

**Rationale:** Three pitfalls (Cognito expiry, inconsistent API errors, timezone bugs in the worker) are production-blocking bugs that will corrupt all subsequent UI work if not fixed first. These have no UI surface but enable everything else.

**Delivers:** Safe foundation — no silent auth failures, no timezone day-boundary bugs, standardized API error shapes across all routes used by new UI.

**Addresses:** Pitfall 3 (Cognito expiry), Pitfall 9 (API error shapes), Pitfall 1 (worker timezone bug fix)

**Specific work:**
- Implement Cognito `REFRESH_TOKEN_AUTH` flow in `/api/auth/` routes
- Add global 401 interceptor (TanStack Query `onError` default) that redirects to `/login`
- Standardize API error responses: audit all routes, enforce `{ error: string }` JSON shape
- Fix `getNextClassDate` in worker to use explicit `America/New_York` timezone
- Add `NormalizedClass` type in shared package; write per-platform normalizer functions

**Research flag:** Standard patterns — no additional research needed. Cognito token refresh is documented in AWS SDK v3 docs.

---

### Phase 2: TanStack Query Foundation and Calendar API

**Rationale:** The TanStack Query provider is a zero-visible-change infrastructure addition that enables all subsequent polling and cache invalidation. The `/api/calendar` route is the data backbone the calendar component needs. Building both before any UI ensures the UI is built on clean abstractions.

**Delivers:** TanStack Query provider in dashboard layout; query key constants file; `/api/calendar?weekStart=` route returning merged events; migrated polling for `WorkerStatus`, `ActiveJobs`, and dashboard stats (setInterval removed).

**Addresses:** Architecture anti-pattern (per-component setInterval), Pitfall 6 (calendar jank from reference equality misses), Pitfall 12 (mobile battery drain via tab visibility pause)

**Uses:** `@tanstack/react-query` v5, `@tanstack/react-query-devtools`, existing `pg` query pattern

**Specific work:**
- Install `@tanstack/react-query` and `@tanstack/react-query-devtools`
- Create `web/src/components/providers.tsx` with `QueryClientProvider`; add to dashboard layout
- Create `web/src/lib/query-keys.ts` with shared key constants
- Build `GET /api/calendar` route with PostgreSQL UNION query
- Migrate `WorkerStatus`, `ActiveJobs`, and `DashboardPage` stats from `setInterval` to TanStack Query hooks
- Set `refetchIntervalInBackground: false` on all queries

**Research flag:** Standard patterns — TanStack Query App Router integration is officially documented. No additional research needed.

---

### Phase 3: Calendar View (Core Trust Builder)

**Rationale:** The calendar replaces the current stats-grid dashboard as the primary home view. This is the highest-impact single change: it makes the "what do I have booked, what is being watched, what failed" question answerable at a glance. Must come before the snipe creation flow because users need to see the calendar to understand what they're adding snipes to.

**Delivers:** `WeekGrid` + `DayColumn` + `CalendarEvent` components; `CalendarView` wired to `/api/calendar`; week navigation (prev/next); three event types with distinct color coding; calendar as primary dashboard content.

**Addresses:** Table stakes feature (calendar view as home screen), Pitfall 1 (timezone rendering via `Intl.DateTimeFormat` with explicit ET timezone), Pitfall 6 (memoized events array, TanStack Query structural sharing)

**Uses:** Custom CSS grid (no react-big-calendar), `date-fns` for week-start computation, `motion/react` for event enter/exit animations, existing shadcn CSS variable system

**Specific work:**
- Install `date-fns` and `motion`
- Build `WeekGrid` (7-column CSS grid, time slots) with static fixture data first
- Build `CalendarEvent` with `EVENT_STYLES` for confirmed/pending-snipe/configured-target
- Wire `CalendarView` to `useCalendarQuery()` hook; handle week navigation
- All datetime display through `Intl.DateTimeFormat({ timeZone: 'America/New_York' })`
- Replace dashboard stats-grid with `CalendarView` as primary element; demote stats to secondary

**Research flag:** No additional research needed for the custom calendar grid — it is a straightforward CSS grid. Timezone-safe rendering via `Intl.DateTimeFormat` is standard.

---

### Phase 4: Schedule Browser Integration and Click-to-Snipe

**Rationale:** The schedule explorer is already built at `/schedule` but is disconnected from the calendar. Promoting it to primary navigation and connecting it to target creation via a sheet flow closes the core user journey: browse → select → snipe → see status. This is the completion of the "discover and book" loop.

**Delivers:** `SchedulePanel` sheet (opens on calendar day click); `ClassCard` with "Snipe This" CTA; `SnipeConfigSheet` with pessimistic mutation and validation; schedule browser promoted to primary nav; credential status indicators ("Connected / Untested / Invalid").

**Addresses:** Table stakes features (schedule browser prominence, click-to-snipe flow, credential status display), Pitfall 2 (3-platform data shapes handled via normalizers from Phase 1), Pitfall 3 (pessimistic UI — no optimistic update on snipe creation), Pitfall 10 (spot preference gated behind `StudioConfig.hasSpotPreference`)

**Uses:** Existing `/api/schedules` route (no changes), `/api/targets` POST (no changes), TanStack Query mutation with cache invalidation

**Specific work:**
- Build `SchedulePanel` as Sheet component; trigger from `CalendarView` day click
- Build `ClassCard` with studio name, time, instructor, "Snipe This" button
- Build `SnipeConfigSheet` form: pessimistic submission, `onSettled` invalidates `QUERY_KEYS.calendar()` and `QUERY_KEYS.targets()`
- Add credential status validation endpoint; surface "Connected / Untested / Invalid" badge in credentials page
- Move schedule browser link to primary nav; add "Find Next Available" button to snipe creation flow
- Gate spot preference UI behind `studio.hasSpotPreference` flag

**Research flag:** Standard patterns. No additional research needed; the existing `SnipeConfigSheet` form and `/api/targets` route already handle the data model.

---

### Phase 5: Snipe Status Timeline and Failure Surfacing

**Rationale:** The final trust-building layer. Users who set snipes via the new flow need to see their snipe's lifecycle clearly. This phase adds the countdown timer, the status timeline, and makes failure states loud. It also enriches booking history. By this phase, the calendar, schedule browser, and snipe creation are all working — the timeline is additive, reading from the already-established job query cache.

**Delivers:** `JobStatusTimeline` component (4 user-facing states mapped from 6 DB states); `CountdownTimer` for booking-opens countdown; prominent failure reason display; enriched booking history with class name + success rate stats.

**Addresses:** Table stakes features (snipe timeline, failure reason visibility, booking history enrichment), Pitfall 7 (internal job states mapped to user-facing vocabulary with stale-claim detection), Differentiators (success rate stats per studio, next attempt time on target cards, spot confirmation label)

**Uses:** Shared `useJobsQuery()` cache (established in Phase 2), `motion/react` for `AnimatePresence` state transitions, `booking_opens_at` from `class_schedules` already in DB

**Specific work:**
- Build `JobStatusTimeline` with status mapping: `pending|claimed → scheduled`, `running → attempting`, `success → booked`, `failed|skipped → failed`
- Add stale-claim detection: if `status = 'claimed'` and `updated_at > 5 min ago`, show "System Check" warning
- Build `CountdownTimer` using `booking_opens_at` — ticks client-side, no server calls, paused when tab hidden
- Surface `job_message` prominently on failed jobs in both timeline and calendar event popover
- Add success rate query to dashboard stats: `COUNT(*) FILTER (WHERE status = 'booked') / COUNT(*) FROM booking_history GROUP BY studio_slug`
- Enrich history page: add class name column, per-studio filter, success rate summary card

**Research flag:** No additional research needed. All data exists in DB; the display patterns are straightforward.

---

### Phase 6: Polish, Empty States, and UX Validation

**Rationale:** Pitch the functional-but-rough version to 2-3 friends after Phase 5. Gather feedback. This phase addresses what's missing from real-world use: empty states, onboarding, mobile battery drain, and whatever UX gaps emerge from friend feedback. Keep this phase lightweight and reactive — do not invest in polish before validating the core flow works for real users.

**Delivers:** Explicit empty states for no-targets, no-schedule-data, and worker-offline conditions; onboarding improvements; polling paused on tab hidden; animation polish where it matters (not everywhere).

**Addresses:** Pitfall 8 (over-engineering before UX validation — this phase is explicitly deferred until after core works), Pitfall 11 (empty states), Pitfall 12 (tab visibility polling pause)

**Research flag:** No research needed — this phase is reactive to friend feedback, not speculative. Keep scope minimal.

---

### Phase Ordering Rationale

- **Infrastructure first (Phases 1-2):** Auth expiry and timezone bugs are production-blocking. They cannot be patched after the UI is built without rewrites. TanStack Query must be installed before any polling component is written.
- **Calendar before schedule panel (Phase 3 before 4):** Users need to see the calendar to understand what they're adding. The schedule panel opens on calendar day click — it architecturally depends on the calendar existing.
- **Timeline last among core features (Phase 5):** The timeline reads from the job query cache established in Phase 2 and refined by Phase 3. It is additive with no new API routes needed — correct to build last when the cache is already proven.
- **Polish gated on user feedback (Phase 6):** Pitfall 8 (over-engineering before validation) is the most expensive mistake in this domain. Phase 6 is explicitly reactive to real user feedback, not speculative.

### Research Flags

**No additional phase-level research needed** for any phase. All patterns are well-documented:
- TanStack Query App Router integration: official docs available
- Cognito token refresh: AWS SDK v3 docs available
- Custom CSS grid calendar: straightforward implementation
- PostgreSQL UNION query for `/api/calendar`: direct extension of existing query patterns in the codebase

**One gap requiring validation during Phase 3 implementation:** The custom `WeekGrid` event overlap handling — when two snipes are at the same time slot. The research recommends building with a simple "stack" approach first and refining if user feedback indicates it's confusing.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technologies verified against official docs; React 19 + Tailwind v4 compatibility confirmed; react-big-calendar rejection grounded in concrete Tailwind v4 CSS variable analysis |
| Features | HIGH | Feature list derived from direct codebase review + established domain patterns; dependency graph based on actual DB schema analysis |
| Architecture | HIGH | Official TanStack Query App Router docs; Vercel SSE timeout confirmed in community forums and Next.js GitHub discussion #48427; `/api/calendar` UNION query directly extends existing patterns |
| Pitfalls | HIGH | Critical pitfalls grounded in existing CONCERNS.md (first-party codebase analysis); timezone bug is a documented known issue; Cognito expiry is documented in CONCERNS.md |

**Overall confidence:** HIGH

### Gaps to Address

- **Event overlap rendering in WeekGrid:** Research does not prescribe a specific approach for overlapping time slots in the custom calendar. Build simple (stacked), observe with friends, refine if needed. Low risk — the use case (2 snipes at same time) is rare.

- **Cognito refresh token availability:** CONCERNS.md documents that token refresh is not implemented. Research assumes the `refresh_token` cookie value is being set. Verify the cookie exists before implementing the refresh flow — if it was never stored, the auth route needs to be updated to store it first.

- **`booking_history.class_name` population:** The enriched history page (Phase 5) assumes `class_name` is populated in `booking_history`. Verify this is consistently populated by the job processor across all three platforms before building the history enrichment UI.

---

## Sources

### Primary (HIGH confidence)
- First-party codebase analysis (CLAUDE.md, CONCERNS.md, direct code review) — architecture constraints, known bugs, existing patterns
- [TanStack Query v5 official docs](https://tanstack.com/query/v5/docs) — App Router integration, `refetchInterval` pattern
- [Next.js App Router docs](https://nextjs.org/docs/app) — route handler patterns, streaming constraints
- [React 19 official docs](https://react.dev/reference/react/useOptimistic) — `useOptimistic` hook
- [AWS Cognito SDK v3 docs](https://docs.aws.amazon.com/AWSJavaScriptSDK/v3/latest/client/cognito-identity-provider/) — token refresh flow
- [Motion for React upgrade guide](https://motion.dev/docs/react-upgrade-guide) — React 19 compatibility via `motion/react`
- [shadcn/ui Tailwind v4 docs](https://ui.shadcn.com/docs/tailwind-v4) — confirmed full Tailwind v4 + React 19 support

### Secondary (MEDIUM confidence)
- [Vercel SSE time limits community forum](https://community.vercel.com/t/sse-time-limits/5954) — 10s Hobby / 60s Pro SSE timeout confirmation
- [Next.js GitHub Discussion #48427](https://github.com/vercel/next.js/discussions/48427) — SSE not viable on Vercel Hobby
- [shadcn-ui-big-calendar](https://github.com/list-jonas/shadcn-ui-big-calendar) — reviewed and found to target Tailwind v3 CSS variables; reason for custom calendar recommendation
- [Nielsen Norman Group — Empty State Design](https://www.nngroup.com/articles/empty-state-interface-design/) — empty state UX patterns
- [Psychology of Trust in AI (Smashing Magazine)](https://www.smashingmagazine.com/2025/09/psychology-trust-ai-guide-measuring-designing-user-confidence/) — trust gap analysis for automated systems

### Tertiary (LOW confidence — findings validated by primary sources)
- [react-big-calendar GitHub Issue #1716](https://github.com/jquense/react-big-calendar/issues/1716) — timezone display bugs in event calendar libraries (supports custom build recommendation)
- [DEV Community: Why I Never Use Optimistic Updates](https://dev.to/criscmd/why-i-never-use-optimistic-updates-and-why-you-might-regret-it-too-4jem) — pessimistic UI recommendation for booking systems

---
*Research completed: 2026-02-26*
*Ready for roadmap: yes*
