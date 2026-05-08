# Fitness Sniper

## What This Is

A fitness class auto-booking web app that snipes competitive classes (Barry's, Aarmy, SLT, Xponential brands, Saint NYC) before they fill up. Users add their studio credentials, browse real class schedules, and set up recurring or one-time snipe targets — the system handles the rest, booking at the exact moment the booking window opens. Currently a working personal tool being rebuilt into a polished calendar-centered product that friends (and eventually strangers) can use.

## Core Value

Users never miss a class they want — the system books it automatically the moment it becomes available, with clear visibility into what's happening at every step.

## Requirements

### Validated

- ✓ Multi-platform booking engine — Mariana Tek, Xponential, Arketa adapters all working
- ✓ Recurring and one-time snipe targets with day/time/location targeting
- ✓ Encrypted credential storage (AES-256-GCM, web encrypts, worker decrypts)
- ✓ Job pipeline — scheduler creates jobs, poller claims atomically, processor executes
- ✓ Stale job recovery (claimed >30 min, running >60 min reset to pending)
- ✓ Slot watcher for unpredictable availability (Arketa/Saint NYC)
- ✓ Schedule scraping from live APIs (MT, Xponential, Arketa)
- ✓ Email notifications on booking success/failure (via Resend)
- ✓ AWS Cognito authentication (signup, login, session management)
- ✓ Basic dashboard with targets, credentials, history, and schedule pages
- ✓ Spot preference support (preferred spots per target)
- ✓ One-time target auto-disable after terminal job or passed date

### Active

- [ ] Calendar-centered home view showing confirmed bookings, pending snipes, and available slots
- [ ] Schedule browser — see real class schedules across studios and click to snipe directly
- [ ] Snipe status timeline — "Scheduled → Waiting → Attempting → Booked" with timestamps
- [ ] Countdown to booking window — "Booking opens in 2d 4h — we'll attempt at 12:00 AM"
- [ ] Push/in-app notifications at key moments (snipe scheduled, attempt starting, result)
- [ ] Polished, production-grade UI — dark mode, clean design, feels like a real product
- [ ] Smooth onboarding flow — pick studios, add credentials, start browsing
- [ ] API route cleanup to support new frontend patterns (consistent responses, proper error shapes)
- [ ] Target creation from schedule — browse → select class → configure snipe in one flow
- [ ] Improved booking history with success rate and patterns

### Out of Scope

- Mobile native app — web-first, responsive design covers mobile for now
- Billing/payments — MVP for friends, no monetization yet
- Real-time chat/support — not needed for friend group
- New studio integrations — existing 3 platforms (MT, Xponential, Arketa) are sufficient
- Worker/adapter changes — booking engine works, focus is frontend + API layer
- Google Calendar sync — nice-to-have for later, not MVP

## Context

- **Existing codebase:** Working monorepo with worker daemon (Mac Mini), Next.js dashboard (Vercel), and shared package. See `.planning/codebase/` for full analysis.
- **Current state:** Backend is solid — adapters book successfully, scheduler/poller/processor pipeline is reliable. Frontend is rough and hard to use — manual target entry, no schedule browsing, minimal status feedback.
- **Target audience:** Initially 5-10 friends who do Barry's, Aarmy, SLT, and similar classes in NYC. They're tech-savvy enough to trust a tool like this but need it to feel polished and trustworthy.
- **Key pain points to solve:** (1) No way to browse schedules and snipe from them, (2) Unclear whether snipes are set up correctly and will fire, (3) UI feels like a developer tool, not a product.

## Constraints

- **Stack:** Next.js 16 + React 19 + Tailwind v4 + shadcn/ui — keep existing stack, just build better with it
- **Backend:** Worker daemon and adapters are out of scope for changes — API routes and data model can be cleaned up
- **Auth:** AWS Cognito stays — already working, no reason to change
- **Database:** PostgreSQL via direct `pg` pool — no ORM migration
- **Deployment:** Vercel (web) + Mac Mini (worker) — same infra
- **Dark mode:** Keep dark-mode-only design

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Keep existing booking engine unchanged | Worker/adapters are working reliably — don't fix what isn't broken | — Pending |
| Calendar view as primary interface | Users think in terms of their week, not a list of targets | — Pending |
| Frontend + API cleanup scope | Backend works; focus investment where the pain is (UX) | — Pending |
| MVP for friends before public launch | Validate the product experience with real users before scaling | — Pending |
| Keep Next.js + shadcn stack | Already in use, good ecosystem, no reason to switch | — Pending |

---
*Last updated: 2026-02-26 after initialization*
