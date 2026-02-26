# Domain Pitfalls

**Domain:** Calendar-centered automated fitness class booking dashboard (frontend rebuild on existing backend)
**Researched:** 2026-02-26
**Scope:** Layering a polished frontend onto an existing booking engine with 3 heterogeneous studio platforms

---

## Critical Pitfalls

Mistakes that cause rewrites, user trust failures, or booking failures.

---

### Pitfall 1: Timezone Rendering Bug — Classes Displayed on Wrong Day

**What goes wrong:** The frontend renders class times using JavaScript's `new Date()` which parses ISO strings into the browser's local timezone. A class at "06:00 AM ET" stored as `2026-03-04T11:00:00Z` renders as "3:00 AM" for a user in PST or "11:00 AM" for a user in UTC. The calendar view shows the class on the wrong day when the local offset crosses midnight.

**Why it happens:** Three distinct failure modes combine:
1. The worker's `getNextClassDate` already has a known timezone bug (uses server local time, not explicit `America/New_York`) per CONCERNS.md.
2. API responses return mixed datetime formats — some as ISO 8601 UTC, some as naive local strings, some as Unix timestamps — across MT, Xponential, and Arketa.
3. Calendar UI libraries (react-big-calendar, FullCalendar) default to browser local time; passing UTC strings directly produces silent day-boundary errors for any non-ET user.

**Consequences:** A user in a different timezone (a friend traveling) sees the Barry's class on Tuesday when it's actually Wednesday. They attempt to snipe a class that's already passed. Trust is immediately broken.

**Prevention:**
- Store and transmit all datetimes as UTC ISO 8601 strings from the API layer.
- Normalize ALL three platform datetime formats in a single shared utility before the data reaches any component.
- Display all class times explicitly in `America/New_York` (the only timezone that matters — all studios are NYC). Use `Intl.DateTimeFormat` with `timeZone: 'America/New_York'` throughout. Never use `new Date().toLocaleString()` without an explicit timezone.
- Fix the worker's `getNextClassDate` in the same milestone — the frontend can't paper over a backend timezone bug.

**Detection (warning signs):**
- A class appears on Saturday in the calendar but the DB record says Friday.
- Booking attempts for "past" classes that users swear were in the future.
- Daylight saving time transitions (March, November) shift all classes by one hour overnight.

**Phase:** Calendar view build (Phase 1 of the milestone). Must be fixed before any calendar rendering ships.

---

### Pitfall 2: Treating 3 Platform Data Shapes as One — Silent Display Bugs

**What goes wrong:** MT, Xponential, and Arketa return fundamentally different class objects. When the frontend builds a unified `ClassCard` component or calendar event, it either (a) silently shows `undefined` for fields that don't exist on a given platform, or (b) the rendering logic quietly skips classes from one platform because a field check fails.

**Why it happens:** The existing `class_schedules` DB table normalizes data at scrape time, but:
- MT classes have `instructor_name` and `location_name`; Arketa classes may have neither.
- Xponential classes have a `credits` cost field that MT doesn't.
- Arketa "any slot" targets have `time = null` — components that render `class.time.substring(0, 5)` will throw.
- Platform-specific booking status vocabulary differs: MT uses `reservation_type`, Xponential has `booking_status`, Arketa has no traditional spot concept.

**Consequences:** The schedule page for Club Pilates shows blank instructor names everywhere. Saint NYC classes silently vanish from the calendar because a null-check failed. Users think "the app doesn't work for my studio."

**Prevention:**
- Define a strict `NormalizedClass` type in `packages/shared/src/types.ts` with all optional fields explicitly typed as `T | null` (not `T | undefined`).
- Write one normalization function per platform at the API boundary, not in components.
- Use TypeScript strict mode so that `class.time.substring(...)` fails at compile time when `time` is `string | null`.
- Render components defensively: always provide fallbacks (`instructor ?? 'Instructor TBD'`).

**Detection (warning signs):**
- The schedule page for Saint NYC shows 0 classes but the DB has rows.
- Spot preference UI appears on Arketa targets (they don't have spots).
- "undefined" visible anywhere in the rendered UI.

**Phase:** API normalization layer (should precede any calendar/schedule UI work).

---

### Pitfall 3: Optimistic UI on Booking Actions — Trust Destruction on Failure

**What goes wrong:** A user clicks "Snipe This Class" and the UI immediately shows "Snipe Set!" before the backend confirms. The worker then fails to execute (wrong credentials, class already full, studio API down). The calendar shows the class as "sniped" indefinitely while the DB record shows a failure. The user never sees the failure because the optimistic state is never rolled back, or the rollback is jarring.

**Why it happens:** Optimistic UI is the standard pattern for fast-feeling apps, but booking systems have a uniquely asymmetric failure profile:
- Failures are NOT rare: credentials expire, studio APIs go down, classes fill before the booking window, and the worker is a single Mac Mini that can crash.
- The failure window is delayed: the snipe target is created now but the booking attempt may not happen for days. "Optimistic" state spanning days is not recoverable optimism — it's a lie.

**Consequences:** User sets a snipe for Thursday's Barry's class. Calendar shows "Snipe Active." Worker fails Saturday night (Mac Mini restart). User shows up to the studio Monday and is turned away because they were never booked. The app has destroyed trust catastrophically.

**Prevention:**
- Do NOT use optimistic UI for snipe creation or status changes. Pessimistic UI only: show a loading state, wait for DB confirmation, then update.
- For the calendar view, always derive booking status from the DB (via polling or SWR revalidation), never from local UI state.
- Make failure states loud, not quiet: a failed booking job must surface visually in the calendar (red indicator, toast notification) — not just in the history log users never look at.
- Implement the "Snipe status timeline" (Scheduled → Waiting → Attempting → Booked/Failed) as the primary feedback mechanism, not as a secondary history view.

**Detection (warning signs):**
- Any component that calls `setStatus('active')` before the API response resolves.
- The calendar color for a class changes before a DB mutation is confirmed.
- Status displayed in calendar does not match `booking_jobs` status in the DB.

**Phase:** Target creation flow and calendar status display (Phase 1-2 of the milestone).

---

### Pitfall 4: Cognito Session Expiry Silently Breaks the Dashboard

**What goes wrong:** Cognito access tokens expire after 1 hour. The refresh token flow is not implemented (documented in CONCERNS.md). A user leaves the dashboard open for 90 minutes, comes back, the tab still looks normal — but every API call silently returns 401. The calendar stops updating, actions don't register, and nothing tells the user they need to log in again.

**Why it happens:** The middleware only checks cookie presence (not validity). Client-side polling loops (SWR, custom `setInterval`) continue firing but get 401s back. Without a global 401 handler, each component handles errors independently — or ignores them.

**Consequences:** A user sets a snipe target, sees no error, but the request was rejected. They believe the snipe is set. It isn't. The class fills up. Same catastrophic trust failure as Pitfall 3.

**Prevention:**
- Implement token refresh using `REFRESH_TOKEN_AUTH` flow before shipping the new frontend. This is a backend/API concern, but the new frontend's polling patterns make it critical.
- Add a global fetch interceptor / SWR `onError` handler that catches 401 responses and redirects to `/login` with a clear message ("Your session expired — please log in again").
- The `/schedule` route missing from `PROTECTED_PATHS` must also be fixed.

**Detection (warning signs):**
- Any API call returns 401 after the user has been on the page for >1 hour.
- The SWR `error` prop is not checked in any data-fetching hook.
- Network tab shows 401s but the page looks "fine."

**Phase:** Must be fixed before shipping the new UI to friends (auth hardening, likely pre-Phase 1 or Phase 1).

---

## Moderate Pitfalls

Mistakes that cause UX degradation or significant debugging time.

---

### Pitfall 5: Per-Serverless-Instance Cache Creates Stale Schedule Data

**What goes wrong:** The schedule API uses an in-memory `Map` for 5-minute caching. On Vercel, multiple serverless instances run in parallel — each has its own cache state. One instance fetched fresh data from the MT API 4 minutes ago; another instance, cold-started on a different request, hits the live MT API again. Worse, when the scraper updates `class_schedules` in the DB, the in-memory cache in a running instance doesn't invalidate — users see stale class data for up to 5 minutes after updates.

**Why it happens:** In-memory caching is instance-local on serverless. It's documented as a known issue in CONCERNS.md.

**Consequences:** User sees Thursday's 6 AM Barry's class as "Available" in the schedule view, sets a snipe, but the class was actually removed from the schedule 3 minutes ago. The snipe job is created for a non-existent class.

**Prevention:**
- For the new schedule browser, use DB-first fetching as the primary path (read from `class_schedules`, which the worker keeps updated). The in-memory live API fallback should be a last resort, not the primary path.
- If live API calls are needed, add cache-busting headers in the API response so the browser doesn't re-serve stale data: `Cache-Control: no-store` or short `max-age`.
- Consider using Next.js route handler's `revalidate` (ISR) for schedule data rather than manual in-memory caching.

**Detection (warning signs):**
- A class appears in the schedule browser but has no corresponding row in `class_schedules`.
- The schedule data timestamps in the API response are older than 5 minutes.

**Phase:** Schedule browser build.

---

### Pitfall 6: Calendar Rendering Performance — Loading All Classes at Once

**What goes wrong:** The calendar component fetches all class sessions for the visible month (or week) at once. For a user with snipe targets across 4 studios × 8 days, this is potentially 200-400 class rows returned in a single API call. The calendar re-renders every time any cell changes (polling interval), causing visible jank on every refresh.

**Why it happens:** Calendar UI components like react-big-calendar re-render the entire grid when the `events` prop reference changes — even if the data is identical. SWR's `refreshInterval` creates a new object reference on every fetch, even when the response data hasn't changed.

**Consequences:** The calendar "flickers" every 30 seconds as the polling interval fires. Users notice the jank and the app feels unstable.

**Prevention:**
- Use SWR with `compare` or TanStack Query's `select` to deduplicate responses — only trigger re-renders when data actually changes.
- Paginate calendar data by the visible time window (week or month), not by studio/target.
- Memoize event arrays (`useMemo`) before passing to the calendar component.
- Set polling interval to a minimum of 60 seconds for schedule data (it doesn't change that fast). Use a shorter interval (15s) only for active job status.

**Detection (warning signs):**
- React DevTools Profiler shows the calendar component re-rendering more than once per minute with no user interaction.
- The `events` prop reference is new on every SWR revalidation even when data is identical.

**Phase:** Calendar view build.

---

### Pitfall 7: "Snipe Status" Out of Sync with Job Pipeline Reality

**What goes wrong:** The frontend shows a "Pending" badge on a snipe target. The user sees it and thinks "great, it's queued." In reality, the job has been claimed and is currently executing (status: `running`), or it has already failed (status: `failed`) but the frontend is polling on a 60-second interval and hasn't caught up. Alternatively, the job is stuck in `claimed` state because the worker crashed — the stale recovery will reset it in 30 minutes but the frontend shows "Claimed" forever with no indication of a problem.

**Why it happens:** The job pipeline has 6 status states (`pending`, `claimed`, `running`, `success`, `failed`, `skipped`) but they don't map 1:1 to user-facing status vocabulary. "Claimed" and "Running" are internal states with no user-meaningful distinction.

**Consequences:** User sees "Pending" on a failed snipe for 60 seconds, or sees "Claimed" on a stale job for 30 minutes, and has no idea whether the system is working.

**Prevention:**
- Map internal job statuses to 4 user-facing states: `scheduled` (pending/claimed), `attempting` (running), `booked` (success), `failed` (failed/skipped).
- For stale detection: if `status = 'claimed'` and `updated_at` is >5 minutes ago, show a "System Check" warning rather than the normal "Scheduled" state.
- Poll job status at 15-second intervals only for jobs where `scheduled_for` is within the next 2 hours. For jobs scheduled days away, 5-minute polling is sufficient.

**Detection (warning signs):**
- The frontend status badge says "Pending" but the DB record shows `status = 'failed'`.
- A job has `status = 'claimed'` and `updated_at` is >30 minutes ago (stale — stale recovery should have reset it).

**Phase:** Snipe status timeline display.

---

### Pitfall 8: Over-Engineering Before Validating Core UX

**What goes wrong:** The milestone spends 3 weeks building a perfect real-time push notification system, a sophisticated animation framework, or a pixel-perfect design system — before verifying that the fundamental calendar + schedule browsing UX is clear to the target users (5-10 friends doing NYC fitness classes).

**Why it happens:** Frontend rebuilds often attract scope creep toward polish. With a working backend, it's tempting to skip the "does this make sense?" validation and go straight to "how do we make it beautiful?"

**Consequences:** The polished app is shipped, friends use it, and the core UX turns out to be confusing. "I couldn't figure out how to set a snipe from the schedule" or "I didn't know my Barry's snipe was set for the wrong location." Weeks of polish wasted on the wrong UX model.

**Prevention:**
- Ship a functional-but-rough version of the calendar + schedule browser to 2-3 friends first. Watch them use it (or get their feedback after 1 week of real use) before investing in polish.
- Defer: push/in-app notifications, sophisticated animations, onboarding tours.
- Prioritize: can the user browse the schedule → select a class → set a snipe → see its status, without confusion? That flow must work and be clear before anything else.

**Detection (warning signs):**
- A phase is defined as "add subtle transition animations" before "verify users can complete the core flow."
- More time is spent on the notification system than on the calendar + schedule browser combined.

**Phase:** Entire milestone — this is a process pitfall, not a code pitfall.

---

### Pitfall 9: Inconsistent API Error Shapes Break Frontend Error Handling

**What goes wrong:** The existing API routes return errors in different formats: some return `{ error: string }`, others return `{ message: string }`, others return Next.js default error pages (HTML, not JSON) when an unhandled exception occurs. The new frontend's error handling code assumes one shape and fails silently or crashes on the others.

**Why it happens:** The existing API routes were built organically without a shared error contract. CONCERNS.md documents this implicitly through the multiple security concerns and missing auth handling.

**Consequences:** A user tries to add a Barry's snipe target, the API returns a 500 with an HTML error page, the frontend JSON-parses it and throws, the catch block swallows the error and shows nothing. The user clicks "Save" five more times wondering why nothing happens.

**Prevention:**
- Before building new frontend pages, audit all API routes used by the new UI and standardize on `{ error: string, code?: string }` for error responses.
- Add a global fetch wrapper that normalizes all responses and throws typed errors — before any UI component has to handle them.
- Ensure all API routes return `Content-Type: application/json` on errors (not HTML).

**Detection (warning signs):**
- Any API route that does `throw error` or `return NextResponse.error()` without a JSON body.
- `JSON.parse()` errors in the browser console originating from fetch calls.

**Phase:** API cleanup (should precede or run parallel to UI build).

---

## Minor Pitfalls

---

### Pitfall 10: Spot Preference UI Appearing for Non-Barry's Studios

**What goes wrong:** The `SPOT_PREFERENCES` in `packages/shared/src/types.ts` defines front/middle/back rows using Barry's-specific spot IDs (`F-1`, `T-1`, etc.). If the spot preference selector is shown generically for all studios, it will send meaningless spot data to Xponential or Arketa bookings.

**Why it happens:** CONCERNS.md identifies this as existing tech debt.

**Prevention:** Gate the spot preference UI behind a studio-specific capability flag in `StudioConfig`. Show spot preference only when `studio.hasSpotPreference === true` (currently only Barry's and Aarmy MT studios).

**Phase:** Target creation flow redesign.

---

### Pitfall 11: Empty States Causing User Panic

**What goes wrong:** A new user onboards, credentials are added, but no snipe targets are set yet. The calendar shows a completely empty week. The schedule browser shows a spinner that resolves to an empty list (if the scraper hasn't run yet for their studios). The user thinks "the app is broken" or "my credentials didn't work."

**Why it happens:** Empty states are treated as afterthoughts. The scraper runs at 2 AM and 2 PM ET — a user who adds credentials at 4 PM will see empty schedule data until 2 AM the next morning.

**Prevention:**
- Design explicit empty states for: (a) no snipe targets set, (b) no upcoming classes scraped yet, (c) worker offline.
- Include a "Schedule not yet loaded — check back in a few hours" message if `class_schedules` has no rows for the user's studios within the last 24 hours.
- Trigger an immediate scrape for newly-added studios when credentials are first saved (or at least show the live API fallback immediately).

**Phase:** Onboarding flow and schedule browser.

---

### Pitfall 12: Polling Without Tab Visibility Check Drains Mobile Batteries

**What goes wrong:** The dashboard's SWR polling (worker status, job status, schedule data) continues firing at full rate when the browser tab is hidden — when the user switches tabs, locks their phone, or leaves the app open in the background. On mobile, this drains the battery noticeably and may keep the Vercel serverless function awake unnecessarily.

**Prevention:** Use `document.addEventListener('visibilitychange', ...)` or SWR's built-in `revalidateOnFocus` + browser Page Visibility API to pause polling when the tab is hidden. Resume at full rate when the tab becomes visible again.

**Phase:** Calendar view + dashboard build.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Calendar view build | Timezone rendering bugs (Pitfall 1) | Normalize all datetimes to `America/New_York` at the API boundary; never use bare `new Date()` |
| API normalization layer | 3-platform data shape mismatch (Pitfall 2) | Write per-platform normalizers, strict `NormalizedClass` type, TypeScript strict mode |
| Snipe target creation flow | Optimistic UI trust destruction (Pitfall 3) | Pessimistic UI only for snipe creation — wait for DB confirmation |
| Auth / session handling | Cognito expiry silently breaking actions (Pitfall 4) | Implement refresh token flow; global 401 interceptor before shipping to friends |
| Schedule browser build | Stale cache serving old class data (Pitfall 5) | DB-first fetching; avoid instance-local in-memory cache for schedule data |
| Calendar polling | Jank from reference equality misses (Pitfall 6) | Memoize events array; SWR `compare` option; 60s interval for schedule data |
| Snipe status display | Internal job states confusing users (Pitfall 7) | Map to 4 user-facing states; detect and surface stale claimed jobs |
| Milestone scope | Over-engineering before UX validation (Pitfall 8) | Ship functional version to 2-3 friends before polish sprint |
| API cleanup | Inconsistent error shapes (Pitfall 9) | Standardize all API error responses before building new UI on top |
| Target creation | Spot preference shown to non-Barry's users (Pitfall 10) | Gate behind `StudioConfig.hasSpotPreference` flag |
| Onboarding | Empty states look broken (Pitfall 11) | Design explicit empty states; trigger live API fallback when scraper hasn't run yet |
| Dashboard polling | Mobile battery drain (Pitfall 12) | Pause polling on tab hidden; resume on tab visible |

---

## Sources

- [Timezone Handling — react-calendar Issue #135](https://github.com/wojtekmaj/react-calendar/issues/135) (MEDIUM confidence — community issue, verified by multiple reports)
- [Wrong event display upon timezone change — react-big-calendar Issue #1716](https://github.com/jquense/react-big-calendar/issues/1716) (MEDIUM confidence — official repo issue tracker)
- [Why I Never Use Optimistic Updates — DEV Community](https://dev.to/criscmd/why-i-never-use-optimistic-updates-and-why-you-might-regret-it-too-4jem) (MEDIUM confidence — community post with engineering reasoning)
- [Optimistic UI and Clobbering — Hasura Blog](https://blog.hasura.io/optimistic-ui-and-clobbering/) (MEDIUM confidence — engineering blog with concrete examples)
- [Common Mistakes with the Next.js App Router — Vercel](https://vercel.com/blog/common-mistakes-with-the-next-js-app-router-and-how-to-fix-them) (HIGH confidence — official Vercel documentation)
- [Aggregating Data from Multiple APIs: Patterns and Pitfalls — DEV Community](https://dev.to/tim_derzhavets/aggregating-data-from-multiple-apis-patterns-and-pitfalls-4l8p) (MEDIUM confidence — community post)
- [The top challenges of normalizing multiple API integrations — Merge.dev](https://www.merge.dev/blog/normalizing-multiple-api-integrations-challenges) (MEDIUM confidence — product blog from integration platform)
- [Designing Empty States in Complex Applications — Nielsen Norman Group](https://www.nngroup.com/articles/empty-state-interface-design/) (HIGH confidence — authoritative UX research source)
- [API contracts and everything I wish I knew — Evil Martians](https://evilmartians.com/chronicles/api-contracts-and-everything-i-wish-i-knew-a-frontend-survival-guide) (MEDIUM confidence — engineering blog with practical examples)
- [6 React Server Component performance pitfalls in Next.js — LogRocket](https://blog.logrocket.com/react-server-components-performance-mistakes) (MEDIUM confidence — engineering blog verified against Next.js docs)
- `.planning/codebase/CONCERNS.md` — Existing tech debt and known bugs (HIGH confidence — first-party codebase analysis)
- `.planning/PROJECT.md` — Project requirements and constraints (HIGH confidence — first-party project spec)
