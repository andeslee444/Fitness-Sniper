# Technology Stack

**Project:** Fitness Sniper — Calendar-Centered Dashboard Rebuild
**Researched:** 2026-02-26
**Scope:** Frontend stack additions for calendar UI, real-time job status, schedule browsing, and notifications

---

## Context: What Stays Unchanged

The following are already in use and must not be replaced. All new additions must integrate with them:

| Technology | Version | Role |
|------------|---------|------|
| Next.js | 16.1.6 | App Router, API routes, Vercel deployment |
| React | 19.2.3 | UI rendering |
| Tailwind CSS | v4 | CSS-first styling via `@tailwindcss/postcss` |
| radix-ui | 1.4.3 | Unified Radix primitives (unified package, not individual) |
| shadcn/ui | via shadcn 3.8.4 | Component system |
| react-day-picker | 9.6.4 | Date picker (already installed) |
| sonner | 2.0.7 | Toast notifications (already installed) |
| react-hook-form | 7.71.1 | Form state |
| zod | 4.3.6 | Schema validation (v4 API) |
| PostgreSQL | via pg 8.13.1 | Database (no ORM, no Supabase realtime) |
| AWS Cognito | via @aws-sdk 3.750.0 | Auth |

---

## New Stack Additions

### 1. Calendar UI — react-big-calendar + shadcn-ui-big-calendar pattern

**Recommended:** `react-big-calendar` ^1.19.4 with `date-fns` ^4.x as localizer, styled using shadcn CSS variable conventions (following the [list-jonas/shadcn-ui-big-calendar](https://github.com/list-jonas/shadcn-ui-big-calendar) pattern).

**Why react-big-calendar over alternatives:**
- ~755K weekly npm downloads, 8,600+ GitHub stars — most-used React calendar library for event-display use cases
- Supports month, week, day, and agenda views — exactly what a fitness schedule dashboard needs
- React 19 compatible
- Provides `date-fns` localizer built-in — no Moment.js dependency required
- Pre-compiled CSS (`react-big-calendar/lib/css/react-big-calendar.css`) works without Sass — critical because Tailwind v4 dropped Sass support
- The [shadcn-ui-big-calendar](https://github.com/list-jonas/shadcn-ui-big-calendar) open-source project demonstrates pure-CSS dark mode integration using shadcn CSS variables — directly applicable to this dark-mode-only app

**Why NOT FullCalendar:**
- Standard (free/MIT) plugins lack resource views and timeline — no real gain over react-big-calendar for this use case
- Premium plugins required for advanced features cost $480+/developer/year — not justified for a friends MVP
- heavier bundle than react-big-calendar

**Why NOT a custom shadcn calendar built on react-day-picker:**
- react-day-picker (already installed) is a date picker, not an event calendar — building week/day event grid views from scratch adds 2-3 weeks of effort for no library benefit
- Month view can be added later on top of the existing shadcn `<Calendar>` component for single-cell booking dots (complementary, not replacement)

**date-fns as localizer (over dayjs or moment):**
- date-fns v4 released with first-class timezone support — the most current option
- 39M+ weekly npm downloads — dominant choice
- Tree-shakeable ESM package — smaller bundle than Moment.js
- v4 adds `@date-fns/tz` for timezone-aware formatting, relevant for NYC class times
- react-big-calendar's `dateFnsLocalizer` is the officially maintained path

**Confidence:** HIGH — Multiple sources confirm react-big-calendar 1.19.4 as current; shadcn-ui-big-calendar pattern verified via live demo

```bash
npm install react-big-calendar date-fns
```

---

### 2. Real-Time Job Status — Client-side Polling via TanStack Query

**Recommended:** `@tanstack/react-query` ^5.x with `refetchInterval` polling (NOT Server-Sent Events, NOT WebSockets).

**Why polling over SSE:**
Vercel has hard request duration limits for SSE: **10 seconds on Hobby plans, 60 seconds on Pro plans**. Long-lived SSE connections are not viable on Vercel serverless functions. The Fitness Sniper app is Vercel-deployed, and booking jobs run on 15-minute scheduler cycles — not sub-second latency requirements. A 10-30 second polling interval is appropriate and avoids the Vercel timeout problem entirely.

**Why TanStack Query over SWR:**
- TanStack Query v5 has first-class support for `refetchInterval` — the exact feature needed for job status polling
- `refetchInterval` can be a function that returns a dynamic interval (e.g., poll faster when a job is in `running` state, slower when idle)
- DevTools for debugging query state during development
- `useSuspenseQuery` with `HydrationBoundary` enables prefetching job data on the server in Next.js App Router, then handing off to client-side polling — better initial load
- Superior mutation support with optimistic updates — useful for target creation and snipe configuration
- SWR is simpler but lacks the conditional refetch interval pattern; TanStack Query's `enabled` + `refetchInterval` combination enables "poll only when there are active jobs"

**Why NOT WebSockets:**
- Requires a persistent server connection that Vercel serverless cannot maintain
- Worker daemon is on Mac Mini — adding a WebSocket server to the Mac Mini worker and a Next.js WebSocket adapter adds significant complexity with no UX benefit over 10s polling for this use case

**Polling strategy for job status:**
```ts
// Fast poll when jobs are active, slow otherwise
useQuery({
  queryKey: ['jobs', 'active'],
  queryFn: fetchActiveJobs,
  refetchInterval: (query) =>
    query.state.data?.hasRunningJobs ? 5000 : 30000,
  refetchIntervalInBackground: false,
})
```

**Confidence:** HIGH — TanStack Query v5 SSR/App Router support documented in official TanStack docs; Vercel SSE timeout limits confirmed in Vercel community forum

```bash
npm install @tanstack/react-query @tanstack/react-query-devtools
```

---

### 3. Animation — motion (formerly framer-motion)

**Recommended:** `motion` ^11.x (import from `"motion/react"`, NOT `"framer-motion"`).

**Why motion:**
- Framer Motion was rebranded to `motion` as of v11/v12. The package is now `motion` on npm; importing from `"motion/react"` is the React 19-compatible path
- React 19 compatibility: confirmed via official Motion upgrade guide — v12+ supports React 19 concurrent features
- Essential for the snipe status timeline ("Scheduled → Waiting → Attempting → Booked") — animate state transitions cleanly
- Countdown timer reveal, booking result success/failure animations, calendar event enter/exit — all achievable with `<motion.div>` and `AnimatePresence`
- Tailwind v4 + Motion is an established 2025 stack (multiple guides confirm compatibility)

**Why NOT CSS transitions only:**
- The status timeline with timestamps needs orchestrated sequencing across multiple elements — difficult with pure CSS
- `AnimatePresence` handles component unmount animations (e.g., a job completing and leaving the active list) — this is not possible with CSS alone in React

**Why NOT Motion One / Web Animations API directly:**
- Motion One is lower-level; Motion for React (`motion/react`) provides the declarative `<motion.div>` API that pairs naturally with React state — less boilerplate for the status timeline use case

**Confidence:** MEDIUM — React 19 compatibility confirmed via official Motion docs; "motion" package rebranding confirmed. Bundle size ~32KB gzipped is acceptable for this app.

```bash
npm install motion
```

---

### 4. In-App Notification Display — Sonner (already installed)

**Status:** Sonner 2.0.7 is already installed and configured via shadcn/ui.

**No new dependency needed.** Use Sonner for:
- Booking result alerts (success/failure) surfaced when the user is active in the app
- "Snipe scheduled" confirmation after target creation
- API error feedback

Sonner is the shadcn/ui-native toast library — already used in the codebase. Extend usage rather than add a competing notification library.

**Confidence:** HIGH — Already in the codebase at 2.0.7.

---

### 5. Push Notifications — Web Push via `web-push` library (deferred to later phase)

**If/when push notifications are added:** Use `web-push` npm package with VAPID keys. Service worker registered via Next.js `/public/sw.js`. API route handles sending via `web-push.sendNotification()` on job completion (triggered from worker or DB trigger → API call).

**Critical Vercel constraint:** Push notification sending (the outbound POST to push services) can be done from a standard API route — this is a short HTTP call, not a long-lived connection. The service worker runs client-side. No Vercel limitation applies.

**Why NOT Firebase Cloud Messaging for MVP:**
- FCM adds Google Cloud dependency and CORS complexity
- `web-push` with VAPID keys is standards-based, provider-free, and simpler for a small user base
- iOS 16.4+ supports Web Push for installed PWAs — covers the target audience

**Recommend deferring:** Push notification infrastructure (service worker, VAPID key management, subscription storage) adds 3-5 days of work. In-app Sonner toasts + email (already working via Resend) cover the MVP notification needs for 5-10 friends.

**Confidence:** MEDIUM — web-push + VAPID pattern is well-documented for Next.js; Vercel serverless compatibility confirmed. iOS 16.4+ support confirmed via MDN/Apple docs.

```bash
# When this phase is implemented:
npm install web-push
npm install -D @types/web-push
```

---

### 6. Data Utilities

**date-fns** (see §1 above — installed as react-big-calendar dependency):
- Use for all date formatting across the dashboard (class times, booking windows, countdowns)
- Replaces any ad-hoc `Date` manipulation
- `formatDistance` for "booking opens in 2d 4h" countdowns
- `@date-fns/tz` for NYC timezone display

**No additional utility libraries recommended.** The existing stack (zod, react-hook-form, clsx, tailwind-merge) is sufficient.

---

## Integration Notes for Existing Stack

### Tailwind v4 + react-big-calendar
react-big-calendar ships pre-compiled CSS in `react-big-calendar/lib/css/react-big-calendar.css`. Import it in `web/src/app/globals.css` alongside Tailwind. Then override RBC styles with CSS custom properties matching shadcn's CSS variable names (`--background`, `--foreground`, `--primary`, etc.). This is the approach used by the shadcn-ui-big-calendar reference project — pure CSS, no Sass required.

```css
/* web/src/app/globals.css */
@import "tailwindcss";
@import "react-big-calendar/lib/css/react-big-calendar.css";

/* Override RBC with shadcn CSS variables */
.rbc-calendar { background: var(--background); color: var(--foreground); }
.rbc-header { border-color: var(--border); }
.rbc-event { background: var(--primary); }
```

### Dark mode compatibility
The app uses `className="dark"` on `<html>`. Tailwind v4 dark mode is configured via `@custom-variant dark (&:where(.dark, .dark *))` — already the correct pattern for a class-based dark-only app. No change needed to existing Tailwind config.

### TanStack Query + Next.js App Router
Wrap the app in a `QueryClientProvider` in a client component (`providers.tsx`), then use `HydrationBoundary` in server components to prefetch initial data. Client components use `useQuery` with `refetchInterval` for polling.

### motion/react + React 19
Import from `"motion/react"` not `"framer-motion"`. Use `'use client'` directive on any component using `<motion.div>` or `AnimatePresence` — server components cannot use Motion animations.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Calendar | react-big-calendar | FullCalendar | Premium features cost $480+/dev/yr; free tier is not meaningfully better |
| Calendar | react-big-calendar | Custom shadcn grid | 2-3 week build time for what a library provides in a day |
| Real-time | TanStack Query polling | Server-Sent Events | Vercel SSE timeout: 10s Hobby / 60s Pro — not viable for persistent job status |
| Real-time | TanStack Query polling | WebSockets | Requires persistent server; Vercel serverless cannot hold WebSocket connections |
| Real-time | TanStack Query | SWR | SWR lacks conditional `refetchInterval` function signature; weaker mutations |
| Animation | motion (motion/react) | CSS transitions | AnimatePresence needed for orchestrated status timeline; CSS can't unmount-animate |
| Animation | motion | Motion One | Higher-level API needed; Motion One is lower-level WAAPI wrapper |
| Toasts | Sonner (existing) | react-hot-toast | Sonner already installed and shadcn-native |
| Push notifs | web-push + VAPID | Firebase FCM | Adds Google Cloud dependency unnecessarily for <10 users |

---

## Installation Summary

```bash
# Calendar
npm install react-big-calendar date-fns

# Real-time polling
npm install @tanstack/react-query @tanstack/react-query-devtools

# Animation
npm install motion
```

**Total new dependencies: 5** (react-big-calendar, date-fns, @tanstack/react-query, @tanstack/react-query-devtools, motion)

**No version conflicts expected** with existing stack — all are React 19 compatible and Tailwind v4 compatible as of 2026.

---

## Sources

- [react-big-calendar npm](https://www.npmjs.com/package/react-big-calendar) — version 1.19.4, ~755K weekly downloads
- [shadcn-ui-big-calendar by list-jonas](https://github.com/list-jonas/shadcn-ui-big-calendar) — open-source RBC + shadcn CSS variables pattern
- [FullCalendar Pricing](https://fullcalendar.io/pricing) — $480+/dev for premium plugins
- [Vercel SSE time limits](https://community.vercel.com/t/sse-time-limits/5954) — 10s Hobby, 60s Pro confirmed
- [TanStack Query v5 Next.js App Router guide](https://tanstack.com/query/v5/docs/framework/react/examples/nextjs) — official integration
- [TanStack Query auto-refetching](https://tanstack.com/query/v4/docs/framework/react/examples/auto-refetching) — `refetchInterval` pattern
- [Motion for React upgrade guide](https://motion.dev/docs/react-upgrade-guide) — React 19 compatibility via `motion/react` import
- [Next.js PWA guides](https://nextjs.org/docs/app/guides/progressive-web-apps) — web push implementation path
- [Tailwind v4 dark mode](https://tailwindcss.com/docs/dark-mode) — `@custom-variant` configuration
- [shadcn/ui Tailwind v4 docs](https://ui.shadcn.com/docs/tailwind-v4) — confirmed full Tailwind v4 + React 19 support
- [date-fns v4 announcement](https://blog.date-fns.org/v40-with-time-zone-support/) — timezone support in v4
- [Builder.io: Best React calendar components 2025](https://www.builder.io/blog/best-react-calendar-component-ai) — ecosystem overview
