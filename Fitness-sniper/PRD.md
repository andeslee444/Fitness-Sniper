# Class Sniper — Product Requirements Document

**Version**: 1.0  
**Last Updated**: 2026-02-13  
**Status**: Production (MVP Complete)  
**Owner**: Andes Lee  
**PM**: Shelldon 🦞  
**Engineering**: Harbor 🐙

---

## 1. Executive Summary

Class Sniper is an automated fitness class booking system that monitors studio schedules and books classes the moment they become available. It solves the problem of competitive class booking at popular fitness studios where desirable time slots fill within seconds of opening.

### Key Value Proposition
- **Set-and-forget automation**: Define your preferences once, get classes booked automatically
- **Multi-studio support**: One unified system for Barry's, SLT, Aarmy, Dogpound, and 8+ other studios
- **Intelligent spot selection**: Prioritize front row, back row, or specific seats
- **Real-time notifications**: WhatsApp alerts when classes are booked or waitlisted

---

## 2. Problem Statement

### User Pain Points
1. **Time-sensitive booking windows**: Classes open 7 days in advance at specific times (often 12:00 AM)
2. **Manual refresh fatigue**: Users set alarms and repeatedly refresh pages
3. **Competitive demand**: Popular instructors/time slots fill in seconds
4. **Multiple platforms**: Each studio has different booking systems (Mariana Tek, MindBody, custom)
5. **Inconsistent availability**: Cancellation windows create sporadic openings

### Market Context
- Premium fitness memberships cost $200-500/month
- Members pay regardless of ability to book classes
- Studios benefit from full classes but not from frustrated members
- No existing unified solution for cross-studio automation

---

## 3. Target Users

### Primary Persona: "The Dedicated Regular"
- **Demographics**: Urban professional, 25-45, $100K+ income
- **Behavior**: 3-5 classes/week at 1-2 studios
- **Motivation**: Consistency, favorite instructors, specific time slots
- **Willingness to pay**: $15-30/month for reliable automation
- **Key need**: "Book my usual classes without thinking about it"

### Secondary Persona: "The Class Hopper"
- **Demographics**: Fitness enthusiast, ClassPass user
- **Behavior**: Tries different studios, chases the hardest-to-get classes
- **Motivation**: Variety, exclusivity, social currency
- **Key need**: "Get me into the classes everyone wants"

---

## 4. Goals & Success Metrics

### Product Goals
| Goal | Metric | Target |
|------|--------|--------|
| Reliable automation | Booking success rate | >95% |
| Speed to book | Time from availability to booked | <3 seconds |
| User retention | Weekly active users after 30 days | >80% |
| Coverage | Studios supported | 15+ |

### Technical Goals
| Goal | Metric | Target |
|------|--------|--------|
| Uptime | System availability | 99.9% |
| Detection avoidance | Block/ban rate | <1% |
| Latency | API response time | <200ms |

---

## 5. System Architecture

### 5.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLASS SNIPER                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Web UI     │    │  REST API    │    │   Worker     │       │
│  │  (PWA)       │◄──►│  (Express)   │◄──►│  (Scheduler) │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                   │                    │               │
│         └─────────┬─────────┴─────────┬─────────┘               │
│                   ▼                   ▼                          │
│           ┌──────────────┐    ┌──────────────┐                  │
│           │    Config    │    │   Adapters   │                  │
│           │    (JSON)    │    │  (Playwright)│                  │
│           └──────────────┘    └──────────────┘                  │
│                                      │                          │
│                   ┌─────────┬────────┴────────┬─────────┐       │
│                   ▼         ▼                 ▼         ▼       │
│              ┌────────┐ ┌────────┐       ┌────────┐ ┌────────┐  │
│              │Mariana │ │MindBody│       │Xponent.│ │ Custom │  │
│              │  Tek   │ │        │       │Fitness │ │        │  │
│              └────────┘ └────────┘       └────────┘ └────────┘  │
│                   │         │                 │         │       │
│                   ▼         ▼                 ▼         ▼       │
│              Barry's    Dogpound          Rumble     Equinox    │
│              Aarmy      F45               CycleBar   (future)   │
│              SLT        OrangeTheory      YogaSix              │
│                                           StretchLab            │
│                                           Pure Barre            │
│                                           Club Pilates          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Component Details

#### Web UI (PWA)
- **Technology**: Vanilla HTML/CSS/JS (intentionally simple)
- **Design System**: "Quiet Confidence" — Linear/Vercel-inspired
- **Features**:
  - Bottom navigation: Targets | History | Settings
  - Floating action button → bottom sheet for add-target
  - Real-time worker status indicator
  - Mobile-first, installable PWA
  - Dark theme with muted red accent

#### REST API (Express)
- **Port**: 3847
- **Endpoints**: 17+ (see Section 9)
- **Data**: JSON file-based (no external DB)
- **Auth**: Local only (no remote access)

#### Worker (Scheduler)
- **Trigger**: Configurable interval (default 60s)
- **Mode**: Headless Playwright (with stealth plugins)
- **State**: Tracks last check, last book per target
- **Notifications**: WhatsApp via OpenClaw

#### Adapters (Platform-specific)
- **Pattern**: Common base interface, studio-specific implementations
- **Supported Platforms**:
  - Mariana Tek (Barry's, Aarmy, SLT, Xponential brands)
  - MindBody (Dogpound, Tone House)
  - Custom (Equinox — blocked)

---

## 6. Feature Specifications

### 6.1 Target Management

#### Add Target
- **Inputs**:
  - Studio (dropdown): 12 studios supported
  - Class type (dropdown): Per-studio types (e.g., "Arms & Abs" for Barry's)
  - Location (dropdown): Per-studio locations with addresses
  - Schedule type (toggle): Recurring vs One-time
  - Day(s) of week (chips): Multi-select for recurring
  - Date (picker): For one-time
  - Time (dropdown): Per-studio time slots
  - Instructor (text, optional): Filter by specific instructor
  - Spot strategy (toggle): Strict | Flexible | Any
  - Seat preference (toggle): Front | Middle | Back | Any

#### Recurring vs One-Time
| Type | Use Case | Data Model |
|------|----------|------------|
| Recurring | "Every Monday 6AM" | `dayOfWeek: 1, time: "6:00 AM"` |
| One-time | "Feb 20, 2026 9AM" | `date: "2026-02-20", time: "9:00 AM"` |

#### Spot Strategy
| Strategy | Behavior |
|----------|----------|
| Strict | Only book if preferred spot(s) available |
| Flexible | Try preferred spots, fall back to any in zone |
| Any | Book first available spot |

#### Seat Preference Mappings
```javascript
{
  front: ['F-1', 'F-3', 'F-5', 'F-7', 'F-2', 'F-4', 'F-6', 'F-8'],
  middle: ['F-9', 'F-10', 'F-11', 'F-12', 'F-13', 'F-14', 'F-15', 'F-16'],
  back: ['T-1', 'T-3', 'T-5', 'T-7', 'T-2', 'T-4', 'T-6', 'T-8'],
  any: [] // First available
}
```

### 6.2 Supported Studios

| Studio | Platform | Adapter | Status | Class Types |
|--------|----------|---------|--------|-------------|
| Barry's Bootcamp | Mariana Tek | `mariana-tek.ts` | ✅ Live | Full Body, Arms & Abs, Chest Back & Abs, Butt & Legs, Double Floor |
| Aarmy | Mariana Tek | `mariana-tek.ts` | ✅ Live | Strength, Conditioning, Recovery |
| SLT | Mariana Tek (iframe) | `mariana-tek.ts` | ✅ Live | Strengthen, Tone, Empower, Mega, Intro |
| Rumble | Mariana Tek | `mariana-tek.ts` | ✅ Live | Boxing, Strength, Foundations |
| CycleBar | Mariana Tek | `mariana-tek.ts` | ✅ Live | Classic, Connect, Performance |
| Club Pilates | Mariana Tek | `mariana-tek.ts` | ✅ Live | Intro, CP Reformer, Center+Balance, Control |
| YogaSix | Mariana Tek | `mariana-tek.ts` | ✅ Live | Y6 101, Hot, Sculpt Flow, Slow Flow, Power |
| StretchLab | Mariana Tek | `mariana-tek.ts` | ✅ Live | 25-Min, 50-Min |
| Pure Barre | Mariana Tek | `mariana-tek.ts` | ✅ Live | Classic, Empower, Define, Align |
| Dogpound | MindBody | `mindbody.ts` | ✅ Live | Strength, Pack, Fundamentals |
| Tone House | MindBody | `mindbody.ts` | 🔄 Beta | Team Class, Open Gym |
| Y7 Studio | Custom | — | ❌ Backlog | — |
| Equinox | Custom API | — | ❌ Blocked | Needs member credentials |
| The Ness | Arketa.co | — | ❌ Backlog | — |

### 6.3 Locations (NYC)

#### Barry's Bootcamp
| Location | Address | ID |
|----------|---------|-----|
| NoHo | 636 Broadway | `noho` |
| Chelsea | 305 W 27th St | `chelsea` |
| Tribeca | 141 Watts St | `tribeca` |
| Brooklyn Heights | 194 Joralemon St | `brooklyn-heights` |
| East 64th | 213 E 64th St | `east-64th` |
| East 86th | 1526 2nd Ave | `east-86th` |
| Long Island City | 29-11 Queens Plaza N | `lic` |
| Park Ave South | 393 Park Ave S | `park-ave-south` |

#### Aarmy
| Location | Address | ID |
|----------|---------|-----|
| Chelsea (A23) | 140 West 23rd St | `chelsea` |
| NoHo | 636 Broadway | `noho` |

#### SLT
| Location | Address | ID |
|----------|---------|-----|
| NoHo | 600 Broadway | `noho` |
| Upper East Side | 1283 Madison Ave | `ues` |
| Upper West Side | 428 Amsterdam Ave | `uws` |
| NoMad | 3 W 29th St | `nomad` |
| SoHo | 42 Wooster St | `soho` |
| FiDi | 85 Broad St | `fidi` |
| Brooklyn | 111 Front St | `brooklyn` |

### 6.4 Booking Flow

```
┌────────────────────────────────────────────────────────────────┐
│ TURBO SNIPER FLOW (Direct URL Navigation)                      │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Construct direct booking URL                               │
│     └─ e.g., barrysbootcamp.marianatek.com/schedule/daily/...  │
│                                                                 │
│  2. Navigate + authenticate (single request)                    │
│     └─ Session cookie from previous login                       │
│                                                                 │
│  3. Wait for schedule render (<1s)                              │
│     └─ Selector: [class*="class-row"]                          │
│                                                                 │
│  4. Click target time slot                                      │
│     └─ text="${time}" → Reserve button                          │
│                                                                 │
│  5. Select spot (if available)                                  │
│     └─ Iterate preferred spots → first available               │
│                                                                 │
│  6. Confirm reservation                                         │
│     └─ Button: "Confirm" or "Complete"                          │
│                                                                 │
│  TOTAL TIME: ~2.5 seconds                                       │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### 6.5 Waitlist Auto-Join

When target class is full:
1. Check if waitlist is enabled for studio
2. Click "Join Waitlist" instead of "Reserve"
3. Store waitlist entry in state
4. Continue monitoring for cancellations
5. If spot opens, attempt to book immediately
6. Notify user of waitlist status

### 6.6 Notifications

| Event | Channel | Template |
|-------|---------|----------|
| Class booked | WhatsApp | "🎯 Booked: {studio} {location}, {day} {time} with {instructor}" |
| Booking failed | WhatsApp | "❌ Failed: {studio} {time} — {reason}" |
| Waitlist joined | WhatsApp | "⏳ Waitlisted: {studio} {time} — position #{position}" |
| Waitlist promoted | WhatsApp | "✅ Off waitlist! {studio} {time} is now booked" |

**Quiet Hours**: Configurable (default: 10 PM - 7 AM) — notifications queued, not sent

---

## 7. Data Models

### 7.1 Target

```typescript
interface ClassTarget {
  id: string;                    // Generated: "{studio}-{location}-{day}-{time}"
  studio: StudioSlug;            // 'barrys' | 'aarmy' | 'slt' | ...
  location: string;              // Location ID
  classType?: string;            // Class type filter
  instructor?: string;           // Instructor filter
  
  // Schedule (one of these patterns)
  dayOfWeek?: number;            // 0-6 for recurring
  daysOfWeek?: number[];         // Multi-day recurring
  date?: string;                 // ISO date for one-time
  time: string;                  // "6:00 AM" format
  
  // Spot preferences
  spotStrategy: 'strict' | 'flexible' | 'any';
  seatPreference: 'front' | 'middle' | 'back' | 'any';
  preferredSpots?: string[];     // Specific spots: ['F-1', 'F-3']
  
  // State
  enabled: boolean;
  lastChecked?: string;          // ISO timestamp
  lastBooked?: string;           // ISO timestamp
  lastResult?: 'success' | 'failed' | 'waitlisted' | 'skipped';
}
```

### 7.2 Config

```typescript
interface SniperConfig {
  credentials: {
    [studio: string]: {
      email: string;
      password: string;
    };
  };
  
  targets: ClassTarget[];
  
  settings: {
    checkIntervalMs: number;     // Default: 60000 (1 min)
    bookingWindowDays: number;   // Default: 7
    dryRun: boolean;             // Test mode (don't confirm)
    notifyOnBook: boolean;
    notifyPhone?: string;        // WhatsApp number
    quietHoursStart?: string;    // "22:00"
    quietHoursEnd?: string;      // "07:00"
  };
}
```

### 7.3 Booking History

```typescript
interface BookingRecord {
  id: string;                    // UUID
  targetId: string;              // Reference to target
  timestamp: string;             // ISO timestamp
  result: 'success' | 'failed' | 'waitlisted';
  classTime: string;             // Actual class datetime
  studio: string;
  location: string;
  instructor?: string;
  spotBooked?: string;           // "F-1"
  errorMessage?: string;         // If failed
}
```

---

## 8. Technical Requirements

### 8.1 Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Runtime | Node.js | 22.x |
| Language | TypeScript | 5.x |
| Browser Automation | Playwright | 1.x |
| Web Server | Express | 4.x |
| Process Manager | PM2 / launchd | — |
| Platform | macOS (Mac Mini) | Sonoma 15.x |

### 8.2 Dependencies

```json
{
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5",
    "playwright": "^1.42.0",
    "playwright-extra": "^4.3.6",
    "puppeteer-extra-plugin-stealth": "^2.11.2",
    "date-fns": "^3.3.1",
    "uuid": "^9.0.0"
  },
  "devDependencies": {
    "typescript": "^5.3.3",
    "@types/node": "^20.11.0",
    "@types/express": "^4.17.21",
    "ts-node": "^10.9.2"
  }
}
```

### 8.3 File Structure

```
class-sniper/
├── PRD.md                        # This document
├── README.md                     # Quick start guide
├── PM.md                         # Sprint planning
├── CLAUDE.md                     # AI agent instructions
├── package.json
├── tsconfig.json
├── config/
│   ├── sniper-config.json        # Main configuration
│   ├── preferences.example.json  # Template
│   └── com.classsniper.autobook.plist  # launchd config
├── src/
│   ├── index.ts                  # CLI entry point
│   ├── auto-sniper.ts            # Main scheduler loop
│   ├── turbo-sniper.ts           # Fast booking engine
│   ├── adapters/
│   │   ├── base.ts               # Adapter interface
│   │   ├── mariana-tek.ts        # Mariana Tek (12 studios)
│   │   └── mindbody.ts           # MindBody (3 studios)
│   ├── notifications/
│   │   └── whatsapp.ts           # WhatsApp via OpenClaw
│   └── utils/
│       ├── stealth.ts            # Anti-detection
│       └── retry.ts              # Retry logic
├── web/
│   ├── server.ts                 # Express server
│   └── public/
│       ├── index.html            # PWA shell
│       ├── styles.css            # "Quiet Confidence" theme
│       ├── app.js                # Client logic
│       ├── manifest.json         # PWA manifest
│       └── sw.js                 # Service worker
├── exploration/
│   ├── SUMMARY.md                # Research findings
│   └── *.md                      # Studio-specific notes
├── logs/
│   └── sniper.log                # Runtime logs
└── state/
    └── history.json              # Booking history
```

### 8.4 Anti-Detection (Stealth Mode)

To avoid being blocked by studios:

1. **Browser Fingerprint Rotation**
   - Random viewport sizes
   - Random user agents
   - Timezone matching
   
2. **Behavioral Mimicry**
   - Randomized delays (50-200ms between actions)
   - Natural mouse movements
   - Realistic scroll patterns
   
3. **Session Management**
   - Persistent login sessions
   - Cookie preservation across runs
   - Avoid re-auth on every check
   
4. **Rate Limiting**
   - Max 1 check per target per minute
   - Jittered intervals (±10%)
   - Backoff on errors

---

## 9. API Reference

### Base URL
```
http://localhost:3847/api
```

### Endpoints

#### Studios & Config
| Method | Path | Description |
|--------|------|-------------|
| GET | `/studios` | List all supported studios with locations |
| GET | `/spot-preferences` | Get seat preference mappings |
| GET | `/config` | Get current config (passwords masked) |
| PUT | `/settings` | Update settings |
| PUT | `/credentials/:studio` | Update studio credentials |

#### Targets
| Method | Path | Description |
|--------|------|-------------|
| GET | `/targets` | List all targets |
| POST | `/targets` | Add a target |
| PUT | `/targets/:id` | Update a target |
| DELETE | `/targets/:id` | Delete a target |
| POST | `/targets/:id/toggle` | Toggle target enabled/disabled |

#### Worker
| Method | Path | Description |
|--------|------|-------------|
| GET | `/worker/status` | Get worker status (running, idle, error) |
| POST | `/worker/start` | Start the worker |
| POST | `/worker/stop` | Stop the worker |
| GET | `/worker/logs` | Get recent worker logs |

#### Runs
| Method | Path | Description |
|--------|------|-------------|
| GET | `/run/status` | Get current run state |
| POST | `/run/start` | Start a manual run for target |
| POST | `/run/step` | Update run step (internal) |
| POST | `/run/stop` | Abort current run |

#### History
| Method | Path | Description |
|--------|------|-------------|
| GET | `/history` | Get booking history |
| GET | `/history/stats` | Get success/fail stats |

### Example Requests

#### Add Recurring Target
```bash
curl -X POST http://localhost:3847/api/targets \
  -H "Content-Type: application/json" \
  -d '{
    "studio": "barrys",
    "location": "noho",
    "dayOfWeek": 1,
    "time": "6:00 AM",
    "seatPreference": "front",
    "spotStrategy": "flexible"
  }'
```

#### Add One-Time Target
```bash
curl -X POST http://localhost:3847/api/targets \
  -H "Content-Type: application/json" \
  -d '{
    "studio": "slt",
    "location": "noho",
    "date": "2026-02-20",
    "time": "9:00 AM",
    "classType": "Empower",
    "seatPreference": "any"
  }'
```

---

## 10. Deployment

### 10.1 Environment

- **Host**: Mac Mini (Harbor)
- **Hostname**: `Andess-Mac-mini.local`
- **IP**: `192.168.68.57`
- **Web UI**: `http://192.168.68.57:3847`

### 10.2 Process Management

Using launchd for always-on operation:

```xml
<!-- ~/Library/LaunchAgents/com.classsniper.autobook.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "...">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.classsniper.autobook</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/node</string>
        <string>/path/to/class-sniper/dist/auto-sniper.js</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/path/to/class-sniper/logs/sniper.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/class-sniper/logs/sniper-error.log</string>
</dict>
</plist>
```

### 10.3 Commands

```bash
# Start web UI
cd class-sniper && npx ts-node web/server.ts

# Start worker (foreground)
cd class-sniper && npx ts-node src/auto-sniper.ts

# Run manual snipe for target
cd class-sniper && npx ts-node src/turbo-sniper.ts barrys-noho-1-0600AM

# Build for production
npm run build

# Load launchd service
launchctl load ~/Library/LaunchAgents/com.classsniper.autobook.plist
```

---

## 11. Security Considerations

### 11.1 Credential Storage
- Credentials stored in `config/sniper-config.json`
- File permissions: `600` (owner read/write only)
- Passwords in plaintext (local-only system)
- Future: Add encryption at rest

### 11.2 Network Security
- Web UI bound to LAN only (not exposed to internet)
- No authentication (assumes trusted network)
- Future: Add basic auth or API key

### 11.3 Studio TOS
- Users provide their own credentials
- System books on user's behalf (not reselling)
- Rate limiting prevents abuse
- No credential sharing or pooling

---

## 12. Future Roadmap

### Phase 2: Multi-User SaaS (Q2 2026)
- [ ] User authentication (OAuth)
- [ ] Multi-tenant data isolation
- [ ] Stripe billing integration
- [ ] Cloud deployment (Railway/Render)
- [ ] Mobile app (React Native)

### Phase 3: Intelligence (Q3 2026)
- [ ] Class popularity prediction
- [ ] Optimal booking time recommendations
- [ ] Instructor rating integration
- [ ] Social features (friends' classes)

### Backlog
- [ ] Equinox adapter (needs member access)
- [ ] Arketa.co adapter (The Ness)
- [ ] Calendar sync (Google Calendar, Apple Calendar)
- [ ] ClassPass integration
- [ ] Cancellation management (auto-cancel if double-booked)

---

## 13. Appendix

### A. Mariana Tek Technical Details

Mariana Tek is the dominant booking platform, used by:
- Barry's Bootcamp
- Aarmy
- SLT
- All Xponential Fitness brands (Rumble, CycleBar, Club Pilates, YogaSix, StretchLab, Pure Barre)

**Authentication Flow**:
1. POST to `/auth/login/` with `{email, password}`
2. Receive session cookie (`sessionid`)
3. All subsequent requests include cookie

**Schedule API**:
- Endpoint: `/schedule/daily/` or `/schedule/weekly/`
- Params: `location_id`, `date`
- Response: JSON with class list

**Booking API**:
1. GET `/schedule/daily/?location_id=X&date=Y`
2. POST `/reserve/` with `{class_id, spot_id}`
3. POST `/confirm/` with `{reservation_id}`

### B. MindBody Technical Details

Used by:
- Dogpound
- Tone House
- F45
- OrangeTheory

**Authentication**:
- OAuth2 flow with studio-specific credentials
- API key required (per-studio)

**Booking Flow**:
- Different from Mariana Tek
- Uses `POST /classes/{id}/book`
- Spot selection in single request

### C. Error Codes

| Code | Meaning | Resolution |
|------|---------|------------|
| `CLASS_NOT_FOUND` | Target class doesn't exist for date | Check schedule manually |
| `CLASS_FULL` | No spots available | Join waitlist if enabled |
| `SPOT_TAKEN` | Preferred spot unavailable | Fall back or retry |
| `AUTH_FAILED` | Login credentials invalid | Update credentials |
| `RATE_LIMITED` | Too many requests | Increase check interval |
| `BLOCKED` | IP or account blocked | Rotate IP, contact studio |

---

**Document Version History**:
- v1.0 (2026-02-13): Initial PRD, MVP complete

