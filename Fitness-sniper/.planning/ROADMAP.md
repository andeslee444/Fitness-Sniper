# Roadmap: Fitness Sniper Dashboard Rebuild

## Overview

The booking engine is complete and reliable. This milestone transforms a working developer tool into a polished product that friends (and eventually strangers) can trust. The journey: first harden the invisible infrastructure that silently breaks sessions and corrupts time-zone rendering, then install the data layer that powers real-time UI, then build the calendar-centered home that makes the system legible at a glance, then close the browse-to-snipe loop, then surface the per-snipe lifecycle so users know their booking will happen, then seal the gaps with empty states and onboarding that make the experience feel complete.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Infrastructure Hardening** - Fix the invisible bugs that silently destroy auth sessions, corrupt timezone rendering, and return unparseable API errors (completed 2026-02-26)
- [x] **Phase 2: Data Foundation** - Install TanStack Query and the `/api/calendar` route that power all real-time UI (completed 2026-02-27)
- [x] **Phase 3: Calendar Home** - Replace the stats-grid dashboard with a weekly calendar view that shows bookings, snipes, and failures at a glance (completed 2026-02-27)
- [x] **Phase 4: Schedule Browser and Click-to-Snipe** - Promote the schedule browser to primary nav and wire it to a one-flow snipe creation sheet (completed 2026-02-28)
- [x] **Phase 5: Snipe Timeline and History** - Surface the per-snipe lifecycle and enrich booking history so users understand what happened and why (completed 2026-02-28)
- [x] **Phase 6: Empty States and Onboarding** - Add guided empty states, worker-offline alerts, and an onboarding flow so new users know exactly what to do (completed 2026-03-14)

## Phase Details

### Phase 1: Infrastructure Hardening
**Goal**: The app never silently fails — sessions stay alive, API errors are parseable, timestamps render on the correct day, and all three studio platforms produce uniform data shapes
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04
**Success Criteria** (what must be TRUE):
  1. User stays logged in after 1 hour without any silent redirect or 401 error in the network tab
  2. Every API route returns `{ error: string }` JSON with an appropriate HTTP status code — never an HTML error page or unstructured object
  3. A class that starts at 6:00 AM ET always appears on the correct day in the UI regardless of the server's system timezone
  4. MT, Xponential, and Arketa schedule data all produce `NormalizedClass` objects with the same fields — no `undefined` instructor or `null` time causes a component crash
**Plans**: 3 plans (all Wave 1 — parallel)

Plans:
- [x] 01-01-PLAN.md — Implement Cognito REFRESH_TOKEN_AUTH flow via POST /api/auth/refresh route
- [x] 01-02-PLAN.md — Wrap all API route handlers in try/catch with consistent { error: string } JSON shape
- [x] 01-03-PLAN.md — Fix timezone bug in scheduler/targets date computation; add NormalizedClass type with API-boundary normalizer

### Phase 2: Data Foundation
**Goal**: TanStack Query manages all server state in the dashboard, existing `setInterval` polling is eliminated, and the `/api/calendar` route provides merged weekly event data in a single round-trip
**Depends on**: Phase 1
**Requirements**: (No direct requirements — enables CAL-01, CAL-02, CAL-03, TRUST-01, TRUST-02)
**Success Criteria** (what must be TRUE):
  1. No `setInterval` calls exist in dashboard components — all polling flows through TanStack Query
  2. `GET /api/calendar?weekStart=YYYY-MM-DD` returns a merged list of confirmed bookings, pending snipes, and configured targets for that week
  3. Dashboard stat cards (worker status, active jobs) refresh without full page reload
  4. Switching browser tabs pauses background polling and resumes when the tab becomes active
**Plans**: 2 plans (all Wave 1 — parallel)

Plans:
- [ ] 02-01-PLAN.md — Install TanStack Query, create providers and query key constants, migrate existing setInterval polling
- [ ] 02-02-PLAN.md — Build GET /api/calendar route with PostgreSQL UNION ALL across booking_history, booking_jobs, and snipe_targets

### Phase 3: Calendar Home
**Goal**: Users see their fitness week at a glance — booked classes in green, pending snipes in yellow, failures in red — from the moment they open the dashboard
**Depends on**: Phase 2
**Requirements**: CAL-01, CAL-02, CAL-03
**Success Criteria** (what must be TRUE):
  1. The dashboard home page shows a 7-column weekly calendar (not the old stats grid) as the primary content element
  2. Confirmed bookings appear as solid green events, pending snipes as dashed/pulsing yellow events, and failed attempts as red events — visually distinct at a glance
  3. Calendar days show a heatmap overlay that communicates slot availability across studios (e.g., a busy day looks visually denser than an empty one)
  4. User can navigate to the previous and next week and all events update without a page reload
  5. All class times display in America/New_York regardless of the user's browser timezone
**Plans**: 2 plans (Wave 1 → Wave 2 sequential)

Plans:
- [ ] 03-01-PLAN.md — Build WeekGrid, DayColumn, CalendarEventPill components and useCalendarQuery hook
- [ ] 03-02-PLAN.md — Create CalendarView with week navigation; replace dashboard stats grid with calendar

### Phase 4: Schedule Browser and Click-to-Snipe
**Goal**: Users can browse live class schedules from the top navigation and create a snipe target for any class in three clicks — without leaving the page
**Depends on**: Phase 3
**Requirements**: SCHED-01, SCHED-02, SCHED-03, TRUST-04
**Success Criteria** (what must be TRUE):
  1. Schedule browser is reachable from the primary navigation on every dashboard page (not buried in a sub-page)
  2. User can click any class in the schedule browser, configure a snipe target (recurring or one-time, optional spot preference), and confirm — all within a sheet drawer without a page redirect
  3. User can click "Find next available" for a studio/class type and see the earliest open slot
  4. Each stored credential shows one of three statuses — "Connected", "Untested", or "Invalid" — as a visible badge on the credentials page
  5. After snipe creation, the new snipe target appears on the calendar without a page reload (pessimistic UI — only shown after DB confirmation)
**Plans**: TBD

Plans:
- [ ] 04-01: Build SchedulePanel sheet component triggered from calendar day click; build ClassCard with "Snipe This" CTA
- [ ] 04-02: Build SnipeConfigSheet form with pessimistic mutation and cache invalidation; promote schedule browser to primary nav
- [ ] 04-03: Add credential status validation endpoint; surface Connected/Untested/Invalid badge on credentials page

### Phase 5: Snipe Timeline and History
**Goal**: Users can see exactly where each snipe is in its lifecycle and understand at a glance whether past bookings succeeded, failed, and why
**Depends on**: Phase 4
**Requirements**: TRUST-01, TRUST-02, TRUST-03, HIST-01, HIST-02, HIST-03
**Success Criteria** (what must be TRUE):
  1. Each snipe target displays a four-step status timeline — "Scheduled → Waiting for booking window → Attempting → Booked / Failed" — with timestamps for completed steps
  2. Pending snipes show a live countdown ("Booking opens in 2d 4h — we'll attempt at 12:00 AM") that ticks in the browser without server calls
  3. Failed jobs display a prominent failure reason with actionable language ("Class was full when we attempted" / "Credential check failed — update your password") — not hidden in small muted text
  4. Booking history shows class name and studio name for every entry (not just timestamps and location IDs)
  5. Dashboard shows a per-studio success rate ("Barry's: 8/10 booked, 80%") as a summary stat
  6. User can filter booking history to show only a single studio's entries
**Plans**: 3 plans (Wave 1: 05-01 + 05-03 parallel, Wave 2: 05-02)

Plans:
- [ ] 05-01-PLAN.md — Build JobStatusTimeline + CountdownTimer components; extend TargetWithJob type; integrate into targets page with prominent failure messages
- [ ] 05-02-PLAN.md — Add class_name column to booking_history (migration 007); enrich history API with studio filter; rebuild history page with class name and filter UI
- [x] 05-03-PLAN.md — Add per-studio success rate query to dashboard stats API; build StudioSuccessRates component on dashboard

### Phase 6: Empty States and Onboarding
**Goal**: A new user with no data understands exactly what to do, and an existing user whose worker is offline immediately knows something is wrong
**Depends on**: Phase 5
**Requirements**: ONBD-01, ONBD-02, ONBD-03
**Success Criteria** (what must be TRUE):
  1. A new user with no snipe targets sees an empty state that explains the three steps to get started (add credentials, browse schedule, create snipe) — not a blank page
  2. When the worker daemon has not sent a heartbeat in more than 5 minutes, a prominent banner or alert appears on every dashboard page (not just a buried status indicator)
  3. A guided onboarding flow walks a new user through: pick studios → add credentials → browse schedule → create first snipe — in a linear sequence they cannot accidentally skip
**Plans**: 2 plans (Wave 1: 06-01, Wave 2: 06-02)

Plans:
- [ ] 06-01-PLAN.md — Build EmptyStateGuide for targets page with 3-step guidance and WorkerOfflineBanner for dashboard layout
- [ ] 06-02-PLAN.md — Build guided onboarding flow at /onboarding route with 4-step linear sequence and new-user redirect

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Infrastructure Hardening | 3/3 | Complete   | 2026-02-26 |
| 2. Data Foundation | 2/2 | Complete   | 2026-02-27 |
| 3. Calendar Home | 2/2 | Complete   | 2026-02-27 |
| 4. Schedule Browser and Click-to-Snipe | 3/3 | Complete   | 2026-02-28 |
| 5. Snipe Timeline and History | 3/3 | Complete   | 2026-02-28 |
| 6. Empty States and Onboarding | 2/2 | Complete   | 2026-03-14 |
