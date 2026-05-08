# Feature Landscape

**Domain:** Fitness class auto-booking calendar dashboard (snipe management UI)
**Researched:** 2026-02-26
**Overall confidence:** HIGH

---

## Context

The booking engine is complete and reliable. This research answers: what does the **user-facing dashboard** need to feel like a polished, trustworthy product — not a developer tool? The primary audience is 5-10 NYC fitness regulars who do Barry's, Aarmy, SLT, and similar boutique studios. They're tech-savvy but expect the product to feel like ClassPass or Mindbody, not a cron job manager.

The central user problem is a **trust gap**: automated systems book on your behalf invisibly. Users abandon automation tools when they can't see what's happening, why it failed, or what's coming next. Every feature below is evaluated through that lens.

---

## Table Stakes

Features users expect. Missing any of these makes the product feel incomplete or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Calendar view showing confirmed bookings and pending snipes | Users think in weekly terms, not lists. ClassPass and every scheduling tool uses this pattern. | Medium | Primary interface. Week view + month mini-calendar. Color-code by status (confirmed/pending/failed). |
| Snipe status with clear labels | Users need to know if the system is "on it". Current states (Queued/Claimed/Booking.../Booked/Failed) exist but are shown only in targets list, not surfaced proactively. | Low | Status labels already implemented. Surface them more prominently. |
| "Booking opens in X" countdown | Boutique fitness classes have strict booking windows (e.g. 7 days out for Barry's). Users need to understand WHY the snipe hasn't fired yet. Without this, they assume the tool is broken. | Low | `class_datetime - bookingWindowDays` is already in DB as `booking_opens_at`. Just need to display it. |
| Failure reason on failed jobs | When a booking fails, users must know why: full class, wrong credentials, network error, etc. Currently `job_message` exists in DB but is shown in tiny muted text. | Low | Already stored in DB. Needs better UI treatment — not hidden. |
| Booking history with status | Users need a record of what was booked, when, and which spot. History page exists but is a raw list. | Low | History page exists. Needs enrichment with class names, success rate stats. |
| Schedule browser — see live class schedules | Users can't create snipes for classes they can't see. Browsing schedules is the discovery mechanism. Schedule explorer exists but is buried at `/schedule`. | Low | Already built. Needs prominence in the navigation and connection to calendar. |
| Snipe from schedule — click-to-snipe flow | Discovering a class in the schedule should lead directly to creating a snipe, not navigating to a separate form. | Low | Already implemented via Popover on schedule page. Flow can be tightened. |
| Credential status indicator | Users need to know their studio credentials are valid and connected. If credentials are stale or wrong, snipes will fail silently. | Low | Credentials page exists. Needs validation state display: "Connected" / "Untested" / "Invalid". |
| Empty state guidance | New users with no targets see nothing and don't know what to do. Onboarding steps exist on dashboard but only appear when targets = 0. | Low | 3-step onboarding exists. Can be improved. |
| Worker/system health visibility | If the worker daemon is down, all snipes will fail. Dashboard shows a worker status card but it's small and easy to miss. | Low | WorkerStatus component exists. Needs more prominence when offline. |
| Email notification on booking result | Users must know when a class is booked or fails — especially since booking happens at 12 AM. | Low | Already implemented via Resend. Table stakes, not to be removed. |

---

## Differentiators

Features that set this product apart from manual booking or generic scheduling tools. These build trust and delight.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Snipe timeline — "Scheduled → Waiting → Attempting → Booked" | The single biggest trust builder for automated systems. Users see that the system is aware of their class, knows when booking opens, and will attempt at the right moment. Comparable to a package tracking feed. | Medium | Requires combining `booking_opens_at`, `scheduled_for`, and job status into a coherent timeline display per snipe target. No new DB columns needed — data already exists. |
| Calendar heatmap showing class availability | Already partially built in the schedule explorer (green/red days). Making this the primary calendar view — overlaid with the user's own snipes — creates a "mission control" feel. | Medium | Calendar component with month view + day heatmap already built. Needs to become the primary home view, not a side feature in the schedule explorer. |
| "Next available slot" finder | Already built in schedule explorer. Surfaces immediately when a user is blocked ("Find next Barry's opening"). Saves manual date-clicking. | Low | Already implemented. Needs better discoverability. |
| Success rate stats per studio/target | Show users their booking success rate: "You've booked 8 of 10 Barry's attempts (80%)". Builds confidence in the system and surfaces problems (e.g. a studio where credentials always fail). | Medium | Computable from `booking_history`. Need query + stat card. |
| Real-time job status with live polling | Dashboard currently polls every 30s. Making the active job card show animated "Booking..." state with elapsed time gives users confidence during the booking attempt window. | Low | Polling infrastructure exists. Animated status badge for running jobs already done (spinner). Can add elapsed time. |
| Contextual snipe card (not just a list row) | Each snipe target should be a card that shows: studio + location + class time + seat preference + next booking attempt time + current status. Users shouldn't need to decode the UI — it reads like a sentence. | Low | Current targets list shows this info but layout is compact. Enriching with a "next attempt" time is the key addition. |
| In-app notification bell (not just email) | Email at 12 AM is often missed or buried. An in-app notification center (even just a badge + dropdown) lets users check results when they open the app in the morning. | High | Requires notification storage in DB + frontend polling. Out of scope for MVP, but differentiating. |
| Spot confirmation with visual indicator | When booked, show which spot was secured: "You got Spot 14 (Back Row Left)". Barry's and SLT users are particular about spots. Currently stored in `booking_history.spot` but not visualized beyond "Spot 14" text. | Low | Data is already there. A simple spot label with studio-specific description (front/back/left/right) would delight users. |
| Recurring vs one-time snipe visual distinction | Recurring snipes (weekly pattern) and one-time snipes should look different in the UI. Currently distinguished only by a badge. | Low | Simple icon differentiation (repeat icon vs calendar-x icon). Already have badge. |

---

## Anti-Features

Features to explicitly NOT build in this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Custom notification rules UI (quiet hours, per-studio preferences) | Overkill for 5-10 users. Adds settings complexity without proportional value. | Simple: email on result. Future: add push toggle. |
| Analytics dashboard with charts and graphs | Fitness app analytics (streak counters, workout frequency charts) are for consumer motivation apps, not an automation tool. Users aren't tracking fitness metrics here — they're managing bookings. | Show success rate as a single number. No charts. |
| Social features (sharing bookings, seeing friends' schedules) | The audience is 5-10 friends. No need for social layer — they text each other. | Not in scope. |
| Mobile native app | Responsive web is sufficient. Friends are tech-savvy and will use the web app on desktop to configure snipes, check results on mobile via browser. | Keep responsive dark-mode web design. |
| Google Calendar sync | Nice-to-have. Adds OAuth complexity (Google API credentials, token management) for a feature that email notifications already partially address. | Mark as post-MVP. |
| Multi-user admin / user management | This is a personal tool for friends, not a SaaS. Admin dashboards for managing other users adds complexity with no benefit for MVP. | Single user per account. |
| Class recommendation engine | AI-powered class suggestions are irrelevant — users already know which Barry's class they want. They need booking automation, not discovery. | Not in scope. |
| Waitlist position tracking | The existing system already handles this better than a waitlist: it doesn't join waitlists, it books at the moment the window opens. Waitlist position tracking would suggest a different architecture. | Keep current approach: book at window open. |
| Complex spot selection UI with floor plan | Studio floor plans would require per-studio visual assets and frequent updates as studios change layouts. Spot preference text labels (Front Row, Back Row, etc.) already work well. | Keep text-based spot preferences. |

---

## Feature Dependencies

```
Credential Status Validation
  → Credentials must be validated before schedule browsing is meaningful
  → Invalid credentials → snipes will fail → user trust collapses

Schedule Browser
  → Required before: Click-to-Snipe Flow
  → Required before: Calendar Heatmap (heatmap data comes from schedule API)

Snipe Target Creation
  → Requires: Credential stored (at least one studio)
  → Required before: Snipe Timeline can display

Snipe Timeline
  → Requires: booking_opens_at in class_schedules (migration 005 — already exists)
  → Requires: Snipe target with scheduled_for set by scheduler
  → Enhances: Calendar View (timeline data populates calendar events)

Calendar View (primary home view)
  → Requires: Snipe targets (shows pending snipes)
  → Requires: Booking history (shows confirmed bookings)
  → Enhanced by: Schedule heatmap data (available slots on calendar days)
  → Enhanced by: Snipe timeline (status per event on calendar)

Success Rate Stats
  → Requires: booking_history with sufficient entries (>= 3-5 bookings)
  → Feeds: Dashboard stat cards

In-App Notification Center
  → Requires: notifications table in DB
  → Requires: background job to write notifications
  → Blocked by: significant scope — defer to post-MVP
```

---

## MVP Recommendation

### Must have (blocking trust)

1. **Snipe timeline per target** — "Booking opens Mar 3 at 12:00 AM — we'll attempt then." This single addition turns the tool from opaque to transparent. Users gain trust instantly when they see the system is aware and scheduled.

2. **Calendar view as home screen** — Replace the current stats-grid dashboard with a week-view calendar. Confirmed bookings (from history) show as solid events. Pending snipes show as outlined/dashed events. Failed snipes show as red. Users can see their whole fitness week at a glance.

3. **Credential status indicators** — "Barry's: Connected" vs "Barry's: Untested" vs "Barry's: Invalid." If credentials are bad, every snipe fails silently. This surfaces that.

4. **Failure reason visibility** — When a job fails, the reason should be prominent, not muted. "Failed: Class was already full when booking window opened" is actionable. "Failed: Credential error — check your Barry's password" is a prompt to fix something.

5. **Improved booking history** — Add: class name (not just time), success rate summary stat ("8/10 booked, 80%"), filter by studio.

### Nice to have (delight)

6. **Success rate stats per studio** — Single-number stat card per studio. Low complexity, builds confidence.

7. **Next attempt time on target cards** — Each snipe card shows: "Next attempt: Mar 3 at 12:00 AM." Already computable from DB data.

8. **"Next available" prominently surfaced** — Move the "Next Available" button from the schedule explorer into the calendar or snipe creation flow.

### Defer

- In-app notification center — email is sufficient for MVP
- Google Calendar sync — post-MVP
- Social features — never (for this audience)

---

## Sources

- [ClassPass UX Case Study (Camille Kurasz)](https://medium.com/@ckurasz/redesigning-classpass-enhancing-visual-identity-navigation-for-a-smoother-booking-experience-4dd4215c1f19) — MEDIUM confidence
- [Fitness booking app features 2025 (Touchlane)](https://touchlane.com/how-to-build-a-fitness-trainer-booking-app-key-features-ux-trends-tech-stack-2025/) — MEDIUM confidence
- [Trust-driven UX (LogRocket)](https://blog.logrocket.com/ux-design/trust-driven-ux-examples/) — HIGH confidence (well-researched article)
- [Push notification best practices (Braze)](https://www.braze.com/resources/articles/push-notifications-best-practices) — HIGH confidence (official source)
- [Calendar UI design best practices (Eleken)](https://www.eleken.co/blog-posts/calendar-ui) — MEDIUM confidence
- [Dashboard design principles (UXPin)](https://www.uxpin.com/studio/blog/dashboard-design-principles/) — MEDIUM confidence
- [Booking UX best practices 2025 (Ralabs)](https://ralabs.org/blog/booking-ux-best-practices/) — MEDIUM confidence
- [Psychology of trust in AI (Smashing Magazine)](https://www.smashingmagazine.com/2025/09/psychology-trust-ai-guide-measuring-designing-user-confidence/) — HIGH confidence
- Existing codebase analysis (direct code review) — HIGH confidence
- Project context (`PROJECT.md`) — HIGH confidence (primary source)

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Table stakes identification | HIGH | Based on direct codebase review + established patterns from ClassPass, Mindbody |
| Differentiators | HIGH | Derived from domain knowledge of automation trust patterns + code analysis |
| Anti-features | HIGH | Grounded in explicit project scope constraints from PROJECT.md + team size |
| Feature dependencies | HIGH | Based on direct DB schema and code review — not speculative |
| Complexity estimates | MEDIUM | Based on existing code review; actual complexity depends on API data availability |
