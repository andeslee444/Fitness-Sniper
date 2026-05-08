# PM.md - Fitness Sniper Project

## Roles
- **Andes**: Product Owner - provides requirements
- **Shelldon 🦞**: Product Manager - formalizes goals, reviews work
- **Harbor 🐙**: Software Engineer - executes tasks, can spawn sub-agents

## Workflow
```
Andes → @shelldon (requirement)
  → Shelldon writes TASK in PM.md with clear goal/acceptance criteria
    → Harbor picks up task, plans approach, executes
    → Harbor can spawn sub-agents for parallel work
      → Harbor writes results to HARBOR_OUTPUT.md
      → Harbor pings @shelldon in WhatsApp when done
        → Shelldon reviews → feedback OR confirms to Andes
```

## Communication
- **WhatsApp group**: Quick coordination (@shelldon, @harbor mentions)
- **PM.md**: Formal task assignments (Shelldon writes)
- **HARBOR_OUTPUT.md**: Work output and results (Harbor writes)
- **REVIEW.md**: Items pending Shelldon review (Harbor writes)

---

## Current Sprint: Multi-Platform Support

### TASK: SNIPER-005 - Build MindBody Adapter
**Status**: READY
**Assigned**: Harbor 🐙
**Priority**: High

**Goal**: Build an adapter for MindBody platform to enable class sniping for Dogpound and other MindBody-powered studios.

**Context**:
- Dogpound uses MindBody (confirmed - link to mindbodyonline.com in footer)
- MindBody powers thousands of studios (huge addressable market)
- Our existing Mariana Tek adapter works for Barry's + Aarmy

**Acceptance Criteria**:
1. Research MindBody booking flow (login, schedule view, booking)
2. Document API endpoints or browser automation steps needed
3. Create `src/adapters/mindbody.ts` following same pattern as `src/adapters/mariana-tek.ts`
4. Test with Dogpound (may need to create account)
5. Document findings in HARBOR_OUTPUT.md

**Optimization Opportunity**: 
Spawn sub-agents to research in parallel:
- Sub-agent 1: MindBody API documentation research
- Sub-agent 2: Dogpound booking flow exploration  
- Sub-agent 3: Check other MindBody studios (Orangetheory, F45, etc.)

**Credentials for testing**:
- Email: user@example.com
- Password: example-password

---

## Completed Tasks

### SNIPER-001 - Barry's Integration ✅
Built turbo-sniper with direct URL navigation, ~3 second booking flow

### SNIPER-002 - Aarmy Integration ✅
Confirmed same Mariana Tek platform as Barry's, adapter works

### SNIPER-003 - Equinox Research ✅
Found mobile API at api.equinox.com, no reCAPTCHA, needs membership creds

### SNIPER-004 - Studio Compatibility Testing ✅
Tested 6 studios, found none use Mariana Tek:
- Rumble: Xponential Fitness
- SLT: Custom
- Y7: Custom
- Dogpound: MindBody
- Tone House: Unknown
- The Ness: Arketa.co

---

## Completed (Sprint 2 - 2026-02-13) ✅ FULL SPRINT

### SNIPER-012: SLT Iframe Adapter ✅
- API-first approach, 19 classes found for NoHo

### SNIPER-013: Auto-Scheduler Worker ✅
- Full Playwright booking engine
- Start/stop from web UI
- Retry logic, dry-run support

### SNIPER-014: Waitlist Auto-Join ✅
- Auto-joins when class full
- Monitors for openings

### SNIPER-015: Booking History ✅
- New History tab with stats
- Success rate tracking

### SNIPER-016: Class Type Filtering ✅
- Per-studio class types (12 studios)
- Instructor filtering

### SNIPER-017: Mobile PWA ✅
- Installable, service worker
- Offline support

### SNIPER-018: Anti-Detection ✅
- Fingerprint rotation
- Randomized delays
- Stealth mode

### SNIPER-019: Multi-Spot Fallback ✅
- Strict/flexible/any strategies

### SNIPER-020: WhatsApp Notifications ✅
- Booked/failed/waitlist alerts
- Quiet hours support

---

## Backlog
- SNIPER-007: Arketa.co adapter (The Ness)
- SNIPER-008: Equinox adapter (needs Rebecca's creds)

---

### TASK: SNIPER-011 - Web UI Target Form Improvements
**Status**: ✅ DONE
**Assigned**: Harbor 🐙
**Completed**: 2026-02-13
**Priority**: Medium

**Goal**: Improve the "Add Target" form in the web UI to better handle locations and distinguish between recurring vs one-time snipes.

**Requirements from Andes**:

1. **Location Display Enhancement**:
   - If location name isn't an address (e.g., "NoHo", "Flatiron", "Chelsea"), show the actual address in parentheses
   - Example: "NoHo (25 Howard St, New York)"
   - Locations that ARE addresses (e.g., "240 W 54th St") don't need additional info
   - Pull addresses from studio config or API responses

2. **Target Type Split - Recurring vs One-Time**:
   - **Recurring Target**: day of week + time
     - UI: Day picker (Mon/Tue/Wed/etc) + Time picker
     - Example: "Every Monday at 6:00 AM"
   - **One-Time Snipe**: specific date + time
     - UI: Date picker + Time picker
     - Example: "February 15, 2026 at 9:00 AM"
   - Toggle or tab to switch between the two modes

**Acceptance Criteria**:
- [ ] Add target type selector (Recurring / One-Time)
- [ ] Recurring: show day-of-week multi-select + time picker
- [ ] One-time: show date picker + time picker
- [ ] Location field shows address in parentheses when needed
- [ ] Both target types save correctly to config
- [ ] Existing targets display correctly in the list

**Files to modify**:
- `web/public/index.html` - UI updates
- `web/server.ts` - API updates if needed
- `config/sniper-config.json` - schema may need update

---

### TASK: SNIPER-006 - Xponential Fitness Adapter
**Status**: IN PROGRESS
**Assigned**: Harbor 🐙 (spawn sub-agents for parallel research)
**Priority**: High

**Goal**: Build adapter for Xponential Fitness platform to enable class sniping for Rumble Boxing and other Xponential-powered studios (CycleBar, Club Pilates, YogaSix, StretchLab, etc.)

**Context**:
- Rumble uses Xponential Fitness platform (confirmed via `members.rumbleboxinggym.com`)
- Xponential owns 10+ fitness brands - one adapter unlocks many studios
- Same browser automation approach as MindBody/Mariana Tek

**Acceptance Criteria**:
1. Research Xponential booking flow (login, schedule view, booking)
2. Identify if it's a unified platform or per-brand customization
3. Create `src/adapters/xponential.ts` following existing adapter patterns
4. Test with Rumble (account exists: user@example.com / example-password)
5. Dry run the full booking flow (stop before confirming)
6. Document findings in HARBOR_OUTPUT.md

**Optimization**: Spawn sub-agents for parallel research:
- Sub-agent 1: Xponential platform architecture research
- Sub-agent 2: Rumble booking flow exploration
- Sub-agent 3: Check other Xponential brands (CycleBar, Club Pilates)

**Credentials**:
- Email: user@example.com
- Password: example-password

