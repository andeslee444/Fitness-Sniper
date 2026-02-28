# Requirements: Fitness Sniper

**Defined:** 2026-02-26
**Core Value:** Users never miss a class they want — the system books it automatically the moment it becomes available, with clear visibility into what's happening at every step.

## v1 Requirements

Requirements for the dashboard rebuild. Each maps to roadmap phases.

### Infrastructure

- [x] **INFRA-01**: User session automatically refreshes when Cognito access token expires (no silent logout after 1 hour)
- [x] **INFRA-02**: All API routes return consistent error shapes with user-facing messages and appropriate HTTP status codes
- [x] **INFRA-03**: Worker timezone handling in `getNextClassDate` correctly computes dates in America/New_York regardless of server timezone
- [x] **INFRA-04**: Data normalization layer produces consistent `NormalizedClass` objects from all 3 platforms (MT, Xponential, Arketa)

### Calendar

- [x] **CAL-01**: User sees a weekly calendar as the dashboard home showing confirmed bookings, pending snipes, and failed attempts
- [x] **CAL-02**: Calendar events are color-coded by status — solid for booked, outlined/dashed for pending snipes, red for failures
- [x] **CAL-03**: Calendar days show availability heatmap overlay indicating how many classes have open slots vs are full

### Schedule

- [x] **SCHED-01**: User can browse live class schedules from primary navigation (not buried under a sub-page)
- [x] **SCHED-02**: User can create a snipe target directly from a class in the schedule browser (browse → select → configure → confirm in one flow)
- [x] **SCHED-03**: User can find the next available opening for a given studio/class type with one click

### Trust

- [x] **TRUST-01**: Each snipe target shows a status timeline — "Scheduled → Waiting for booking window → Attempting → Booked/Failed" with timestamps
- [x] **TRUST-02**: Pending snipes show a countdown to when the booking window opens ("Booking opens in 2d 4h — we'll attempt at 12:00 AM")
- [ ] **TRUST-03**: Failed booking jobs display prominent failure reasons with actionable messaging ("Class was full" / "Check your credentials")
- [x] **TRUST-04**: Each stored credential shows validation status — "Connected", "Untested", or "Invalid" — so users know if their credentials will work

### History

- [ ] **HIST-01**: Booking history displays class names and studio names (not just times and location IDs)
- [x] **HIST-02**: Dashboard shows success rate per studio ("8/10 booked, 80%") as a summary stat
- [ ] **HIST-03**: User can filter booking history by studio

### Onboarding

- [ ] **ONBD-01**: New users with no targets see clear empty state guidance explaining the 3 steps to get started
- [ ] **ONBD-02**: Worker offline status is displayed prominently with a banner/alert when the daemon hasn't sent a heartbeat recently
- [ ] **ONBD-03**: New user onboarding guides through: pick studios → add credentials → browse schedule → create first snipe

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Notifications

- **NOTF-01**: User receives in-app notifications via notification bell (not just email)
- **NOTF-02**: User can configure notification preferences per event type

### Integrations

- **INTG-01**: User can sync confirmed bookings to Google Calendar

### Polish

- **POL-01**: Spot confirmation shows visual indicator with position description (e.g., "Spot 14 — Back Row Left")
- **POL-02**: Month mini-calendar navigation for quick date jumping
- **POL-03**: Live animated "Booking..." state with elapsed time during active attempts

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Analytics dashboard with charts/graphs | Automation tool, not fitness tracker — single success rate number suffices |
| Social features (sharing, friends' schedules) | 5-10 friend audience texts each other — no product need |
| Mobile native app | Responsive web covers mobile; no app store complexity |
| Class recommendation engine | Users know what they want — they need automation, not discovery |
| Waitlist position tracking | System books at window open, doesn't join waitlists — different architecture |
| Complex spot selection with floor plan | Text-based spot preferences work; floor plans require per-studio visual assets |
| Custom notification rules UI | Overkill for 5-10 users — simple email on result is sufficient |
| Multi-user admin/user management | Personal tool for friends, not a SaaS — no admin needed |
| Billing/payments | MVP for friends, no monetization yet |
| New studio platform integrations | 3 platforms (MT, Xponential, Arketa) cover target studios |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 1 | Complete |
| INFRA-02 | Phase 1 | Complete |
| INFRA-03 | Phase 1 | Complete |
| INFRA-04 | Phase 1 | Complete |
| CAL-01 | Phase 3 | Complete |
| CAL-02 | Phase 3 | Complete |
| CAL-03 | Phase 3 | Complete |
| SCHED-01 | Phase 4 | Complete |
| SCHED-02 | Phase 4 | Complete |
| SCHED-03 | Phase 4 | Complete |
| TRUST-01 | Phase 5 | Complete |
| TRUST-02 | Phase 5 | Complete |
| TRUST-03 | Phase 5 | Pending |
| TRUST-04 | Phase 4 | Complete |
| HIST-01 | Phase 5 | Pending |
| HIST-02 | Phase 5 | Complete |
| HIST-03 | Phase 5 | Pending |
| ONBD-01 | Phase 6 | Pending |
| ONBD-02 | Phase 6 | Pending |
| ONBD-03 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0

---
*Requirements defined: 2026-02-26*
*Last updated: 2026-02-26 after roadmap creation*
