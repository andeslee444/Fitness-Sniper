# Class Sniper 🎯

Auto-book competitive fitness classes the moment they open.

## The Problem

Popular fitness classes (Barry's, SoulCycle, Equinox, Rumble) fill up in seconds. Users currently:
- Set 6am alarms to book when classes open
- Refresh pages obsessively
- Miss out on favorite instructors/time slots
- Pay for memberships they can't fully use

## The Solution

A "sniper" that watches for openings and books automatically.

## User Personas

### Primary: "The Dedicated Regular"
- Goes 3-5x/week to the same studio
- Has favorite instructors and time slots
- Hates the booking game, willing to pay $10-20/mo for automation
- Values: reliability, specific preferences, notifications

### Secondary: "The Class Hopper"
- Uses ClassPass or multiple studios
- Wants the hardest-to-get classes across studios
- Values: breadth of studio support, discovery

## MVP Scope (Week 1)

**One studio, one flow:** Barry's Bootcamp NYC
- Login handling
- Class search by date/time/location/instructor
- Auto-book when target class is available
- Email/SMS notification on success

**Why Barry's first:**
- Notoriously competitive booking
- Clear value prop for users
- Validates the hardest technical challenges

## User Experience

### Setup Flow
1. Enter Barry's credentials (stored locally/encrypted)
2. Set preferences:
   - Preferred locations (e.g., "Chelsea", "Tribeca")
   - Preferred times (e.g., "6am-8am weekdays", "10am weekends")
   - Preferred instructors (optional)
   - Booking window (how far in advance)
3. Enable notifications (email/SMS)

### Ongoing Experience
- Sniper runs on schedule (when classes open + continuous monitoring)
- User gets notification: "🎯 Booked: Barry's Chelsea, Tue 6:30am with Eddie"
- Dashboard shows upcoming booked classes, success rate
- Can pause/adjust preferences anytime

### Key UX Principles
1. **Set and forget** — shouldn't need daily interaction
2. **Transparent** — show what's being attempted, success/failure
3. **Respectful** — don't overbook, respect cancellation policies
4. **Secure** — credentials encrypted, user controls data

## Technical Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Class Sniper                      │
├─────────────────────────────────────────────────────┤
│  Config (preferences.json)                          │
│  - Credentials (encrypted)                          │
│  - Target classes (locations, times, instructors)   │
│  - Notification settings                            │
├─────────────────────────────────────────────────────┤
│  Scheduler (cron)                                   │
│  - Runs at class release times                      │
│  - Continuous monitoring for cancellations          │
├─────────────────────────────────────────────────────┤
│  Studio Adapters                                    │
│  - barrys.ts (first)                               │
│  - soulcycle.ts (later)                            │
│  - equinox.ts (later)                              │
├─────────────────────────────────────────────────────┤
│  Browser Automation (Playwright)                    │
│  - Login                                           │
│  - Search classes                                  │
│  - Book                                            │
├─────────────────────────────────────────────────────┤
│  Notifications                                      │
│  - Email (SendGrid/Resend)                         │
│  - SMS (Twilio)                                    │
└─────────────────────────────────────────────────────┘
```

## File Structure

```
class-sniper/
├── README.md
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts              # Main entry point
│   ├── config.ts             # Configuration management
│   ├── scheduler.ts          # Cron scheduling
│   ├── adapters/
│   │   ├── base.ts           # Base adapter interface
│   │   └── barrys.ts         # Barry's implementation
│   ├── notifications/
│   │   ├── email.ts
│   │   └── sms.ts
│   └── utils/
│       └── crypto.ts         # Credential encryption
├── config/
│   └── preferences.example.json
└── tests/
    └── barrys.test.ts
```

## Success Metrics

- **Booking success rate:** % of target classes actually booked
- **Time to book:** How fast after class opens
- **User retention:** Do users keep using after week 1?
- **Willingness to pay:** Conversion on $10-20/mo pricing

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Studios block automation | Rotate IPs, respect rate limits, mimic human behavior |
| TOS violations | Clear user agreement, user provides own credentials |
| Captchas | Browser fingerprinting, possibly manual fallback |
| Class cancellation fees | Smart booking (don't overbook), easy cancellation flow |

## Roadmap

### Week 1: Barry's MVP
- [ ] Project setup (TypeScript, Playwright)
- [ ] Barry's login flow
- [ ] Class search and parsing
- [ ] Booking automation
- [ ] Basic notifications (console/email)
- [ ] CLI for configuration

### Week 2: Polish & Test
- [ ] Encrypted credential storage
- [ ] Scheduling (cron-based)
- [ ] SMS notifications
- [ ] Error handling and retries
- [ ] User testing with real accounts

### Week 3+: Expand
- [ ] SoulCycle adapter
- [ ] Equinox adapter
- [ ] Web dashboard
- [ ] Waitlist feature (book if cancellation)
- [ ] Multi-user support (SaaS)

## Getting Started

```bash
# Install dependencies
npm install

# Copy config template
cp config/preferences.example.json config/preferences.json

# Edit with your preferences
code config/preferences.json

# Run sniper
npm run snipe
```

## Configuration Example

```json
{
  "studios": {
    "barrys": {
      "email": "user@example.com",
      "password": "encrypted:xxxxx",
      "preferences": {
        "locations": ["Chelsea", "Tribeca"],
        "times": {
          "weekdays": ["06:00-08:00"],
          "weekends": ["09:00-11:00"]
        },
        "instructors": ["Eddie", "Dani"],
        "daysInAdvance": 7
      }
    }
  },
  "notifications": {
    "email": "user@example.com",
    "sms": "+14255551234"
  }
}
```

---

Built by Andes with Shelldon 🦞
