# Class Sniper UI/UX Overhaul Plan

> **Vision:** Transform Class Sniper from a functional dark-themed tool into a premium fitness app that matches the caliber of the studios it books.

---

## 1. Design Direction

### Brand Aesthetic: "Tactical Precision meets Premium Fitness"

**Inspiration Sources:**
- **Whoop** — Data-driven, dark interfaces with strain metrics
- **Peloton** — Premium dark mode with motivational energy
- **Nike Training Club** — Bold typography, confident design language
- **F45 Training** — High-energy with structured data display

**Why This Direction:**
The "sniper" metaphor perfectly aligns with:
- **Precision** — Exact times, specific spots, targeted instructors
- **Speed** — Millisecond advantages when classes open
- **Stealth** — Works quietly in the background
- **Elite Performance** — Premium studios deserve premium tooling

### Design Principles

1. **Calm Confidence** — Dark, focused interfaces that feel professional, not aggressive
2. **Instant Clarity** — Status at a glance, no hunting for information
3. **Rewarding Success** — Celebrate bookings with satisfying feedback
4. **Touch-First** — Mobile PWA is the primary experience

---

## 2. Color Palette

### Primary Dark Theme

```css
:root {
  /* Backgrounds - Rich blacks with subtle warmth */
  --bg-primary: #09090b;      /* Near-black (zinc-950) */
  --bg-secondary: #18181b;    /* Card surfaces (zinc-900) */
  --bg-tertiary: #27272a;     /* Elevated elements (zinc-800) */
  
  /* Borders - Subtle definition */
  --border-subtle: #27272a;   /* Default borders */
  --border-emphasis: #3f3f46; /* Interactive focus */
  
  /* Text Hierarchy */
  --text-primary: #fafafa;    /* Headlines, emphasis */
  --text-secondary: #a1a1aa;  /* Body text (zinc-400) */
  --text-muted: #71717a;      /* Labels, captions (zinc-500) */
  
  /* Accent: Tactical Red */
  --accent-primary: #dc2626;  /* Primary actions (red-600) */
  --accent-hover: #ef4444;    /* Hover state (red-500) */
  --accent-muted: #991b1b;    /* Subtle accents (red-800) */
  --accent-glow: rgba(220, 38, 38, 0.15); /* Background glows */
  
  /* Semantic Colors */
  --success: #22c55e;         /* Booked, complete (green-500) */
  --success-muted: #166534;   /* Success backgrounds */
  --warning: #f59e0b;         /* Dry run, pending (amber-500) */
  --warning-muted: #92400e;   /* Warning backgrounds */
  --error: #ef4444;           /* Failed, blocked (red-500) */
  --info: #3b82f6;            /* Informational (blue-500) */
  
  /* Special: Target Lock Animation */
  --sniper-glow: #dc2626;
  --sniper-pulse: rgba(220, 38, 38, 0.4);
}
```

### Color Usage Guidelines

| Context | Color | Token |
|---------|-------|-------|
| Primary CTA (Add Target, Book Now) | Solid red | `--accent-primary` |
| Secondary actions | Ghost with border | `--border-emphasis` |
| Active/Running state | Pulsing red glow | `--sniper-pulse` |
| Success confirmations | Green accent | `--success` |
| Dry Run indicator | Amber badge | `--warning` |
| Card backgrounds | Zinc-900 | `--bg-secondary` |

---

## 3. Typography

### Font Stack

**Primary: Inter**
- Clean, modern, optimized for screens
- Excellent number legibility (important for times)
- Variable font support for performance

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-mono: 'JetBrains Mono', 'SF Mono', 'Fira Code', monospace;
}
```

**Secondary: JetBrains Mono (optional)**
- For timestamps, IDs, log output
- Adds technical precision feel

### Type Scale

```css
/* Headings */
--text-4xl: 2.25rem;    /* 36px - Page titles */
--text-3xl: 1.875rem;   /* 30px - Section headers */
--text-2xl: 1.5rem;     /* 24px - Card titles */
--text-xl: 1.25rem;     /* 20px - Emphasis */
--text-lg: 1.125rem;    /* 18px - Subheadings */

/* Body */
--text-base: 1rem;      /* 16px - Default */
--text-sm: 0.875rem;    /* 14px - Secondary info */
--text-xs: 0.75rem;     /* 12px - Captions, timestamps */

/* Line Heights */
--leading-tight: 1.25;
--leading-normal: 1.5;
--leading-relaxed: 1.75;

/* Letter Spacing */
--tracking-tight: -0.025em;  /* Headlines */
--tracking-wide: 0.05em;     /* Labels, badges */
```

### Typography Rules

1. **Headlines**: Semi-bold (600), tight tracking, zinc-50
2. **Body**: Regular (400), normal leading, zinc-400
3. **Labels**: Medium (500), wide tracking, uppercase, zinc-500
4. **Numbers**: Tabular nums for alignment (class times)

---

## 4. Component Redesign

### 4.1 Navigation

**Current:** Simple header with title and status badge

**Redesigned: Floating Bottom Nav (Mobile-First)**

```
┌─────────────────────────────────────┐
│                                      │
│           [App Content]              │
│                                      │
│                                      │
├──────────────────────────────────────┤
│  🎯 Targets   📅 Schedule   ⚙️ Settings │
│   ●active      ○             ○        │
└──────────────────────────────────────┘
```

**Features:**
- Fixed bottom navigation for thumb reach
- Active state: Filled icon + label
- Status indicator dot (green/amber) on Targets when active
- Subtle blur backdrop
- Safe area padding for notched devices

**Desktop Enhancement:**
- Sidebar navigation with collapsed/expanded states
- Keep bottom nav on tablet portrait

### 4.2 Cards

**Current:** Basic rounded rectangles with minimal hierarchy

**Redesigned: Elevated Glass Cards**

```css
.card {
  background: linear-gradient(
    135deg,
    rgba(39, 39, 42, 0.8) 0%,
    rgba(24, 24, 27, 0.9) 100%
  );
  backdrop-filter: blur(10px);
  border: 1px solid rgba(63, 63, 70, 0.5);
  border-radius: 16px;
  box-shadow: 
    0 4px 6px -1px rgba(0, 0, 0, 0.3),
    0 0 0 1px rgba(255, 255, 255, 0.03) inset;
}
```

**Card Variants:**

| Variant | Use Case | Visual Treatment |
|---------|----------|------------------|
| Default | Content containers | Subtle glass |
| Interactive | Targets, clickable | Hover lift + glow |
| Active | Currently sniping | Red border pulse |
| Success | Booked class | Green left accent |
| Alert | Requires attention | Amber top accent |

### 4.3 Target Cards (Key Component)

**Complete Redesign:**

```
┌──────────────────────────────────────────┐
│ ●🔴 LOCKED                               │
│                                          │
│ BARRY'S CHELSEA                          │
│ ━━━━━━━━━━━━━━━━━━━━━━━━                │
│                                          │
│ 📅 Tomorrow, Feb 14          🎯 F-1      │
│ ⏰ 6:30 AM                   👤 Eddie    │
│                                          │
│ ┌────────────────────────────────────┐  │
│ │ ⏱️ Opens in 2h 34m 12s             │  │
│ └────────────────────────────────────┘  │
│                                          │
│      [  ⏸ Pause  ]   [ 🗑 Remove  ]     │
└──────────────────────────────────────────┘
```

**Features:**
- Live countdown timer to booking window
- Status pill (Locked/Sniping/Booked/Failed)
- Studio logo integration
- Spot preference badge
- Instructor tag (if specified)
- Swipe actions for pause/delete (mobile)

### 4.4 Buttons

**Button Hierarchy:**

```css
/* Primary - High emphasis actions */
.btn-primary {
  background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
  color: white;
  font-weight: 600;
  padding: 14px 24px;
  border-radius: 12px;
  box-shadow: 0 0 20px rgba(220, 38, 38, 0.3);
  transition: all 0.2s ease;
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 0 30px rgba(220, 38, 38, 0.5);
}

.btn-primary:active {
  transform: translateY(0);
}

/* Secondary - Lower emphasis */
.btn-secondary {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border-emphasis);
  padding: 14px 24px;
  border-radius: 12px;
}

/* Ghost - Minimal */
.btn-ghost {
  background: transparent;
  color: var(--accent-primary);
  padding: 14px 24px;
}

/* Icon buttons */
.btn-icon {
  width: 44px;  /* Touch target */
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}
```

### 4.5 Forms

**Input Fields:**

```css
.input {
  background: var(--bg-primary);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 14px 16px;
  color: var(--text-primary);
  font-size: 16px; /* Prevents iOS zoom */
  transition: border-color 0.2s, box-shadow 0.2s;
}

.input:focus {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px var(--accent-glow);
  outline: none;
}

.input::placeholder {
  color: var(--text-muted);
}
```

**Select Dropdowns:**
- Custom styled with chevron icon
- Option cards for location/time selection (mobile-friendly)
- Visual studio logos in dropdown

**Day Selector (Redesigned):**
```
┌─────┬─────┬─────┬─────┬─────┬─────┬─────┐
│ SUN │ MON │ TUE │ WED │ THU │ FRI │ SAT │
│     │  ●  │     │  ●  │     │     │     │
└─────┴─────┴─────┴─────┴─────┴─────┴─────┘
```
- Multiple days selectable
- Dot indicator for "has target"
- Selected = red background fill

**Seat Preference (Visual Grid):**
```
┌─────────────────────────────────────────┐
│   INSTRUCTOR                            │
│                                          │
│  [ 1 ] [ 2 ] [ 3 ] [ 4 ] [ 5 ] [ 6 ]   │  ← Front
│  [ 7 ] [ 8 ] [ 9 ] [10 ] [11 ] [12 ]   │
│  [13 ] [14 ] [15 ] [16 ] [17 ] [18 ]   │  ← Back
│                                          │
│  🔴 = Selected   ⚫ = Fallback           │
└─────────────────────────────────────────┘
```
- Actual floor map when possible
- Tap to set primary, long-press for fallback
- Preference regions (front/middle/back) as quick-select

### 4.6 Modals & Sheets

**Bottom Sheet (Mobile Primary):**

```css
.sheet {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: var(--bg-secondary);
  border-radius: 24px 24px 0 0;
  padding: 24px;
  padding-bottom: env(safe-area-inset-bottom, 24px);
  transform: translateY(100%);
  transition: transform 0.3s cubic-bezier(0.32, 0.72, 0, 1);
}

.sheet.open {
  transform: translateY(0);
}

/* Drag handle */
.sheet::before {
  content: '';
  width: 36px;
  height: 4px;
  background: var(--border-emphasis);
  border-radius: 2px;
  position: absolute;
  top: 8px;
  left: 50%;
  transform: translateX(-50%);
}
```

**Modal Dialogs (Desktop):**
- Centered cards with backdrop blur
- Close on overlay click
- Keyboard accessible (Escape to close)

---

## 5. New Features & Animations

### 5.1 Visual Class Calendar

**Weekly View (Default):**

```
┌──────────────────────────────────────────────────┐
│  ← Feb 10 - 16, 2026 →                          │
├────────┬────────┬────────┬────────┬────────┬────┤
│  MON   │  TUE   │  WED   │  THU   │  FRI   │    │
│  10    │  11    │  12    │  13    │  14    │ ▶  │
├────────┼────────┼────────┼────────┼────────┼────┤
│ 6:30am │        │ 6:30am │        │ 6:30am │    │
│ 🎯B    │        │ 🎯B    │        │ ✅B    │    │
│        │        │        │        │        │    │
│        │ 7:00am │        │ 7:00am │        │    │
│        │ 🎯A    │        │ 🎯A    │        │    │
├────────┴────────┴────────┴────────┴────────┴────┤
│ 🎯 = Target Locked    ✅ = Booked    ⏳ = Pending│
└──────────────────────────────────────────────────┘
```

**Features:**
- Horizontal scroll weeks
- Tap class for details sheet
- Color-coded by studio
- "Opens in X" badge for upcoming windows
- Integration with phone calendar (optional)

### 5.2 Booking Animations

**Target Lock Animation:**
```
1. Crosshairs converge on target card
2. Red pulse radiates outward
3. "TARGET LOCKED" text appears
4. Card border animates to locked state
```

**Sniping In Progress:**
```css
@keyframes sniper-scan {
  0% { background-position: 0% 0%; }
  100% { background-position: 100% 0%; }
}

.sniping-active {
  background: linear-gradient(
    90deg,
    var(--bg-secondary) 0%,
    var(--accent-glow) 50%,
    var(--bg-secondary) 100%
  );
  background-size: 200% 100%;
  animation: sniper-scan 2s ease-in-out infinite;
}
```

**Successful Booking:**
```
1. Card flashes green border
2. Confetti particles burst from card
3. Checkmark animates in (draw SVG path)
4. Haptic feedback (success pattern)
5. Sound effect (optional, subtle "target hit")
6. Card transitions to "Booked" state
```

**Implemented with:**
- Framer Motion for React animations
- CSS @keyframes for simple states
- Canvas API for confetti (use canvas-confetti library)
- Haptic API for mobile feedback

### 5.3 Success States

**Booking Confirmation Sheet:**

```
┌──────────────────────────────────────┐
│                                      │
│              ✓                       │
│          TARGET HIT                  │
│                                      │
│   ─────────────────────────────────  │
│                                      │
│   Barry's Chelsea                    │
│   Tomorrow, Feb 14 @ 6:30 AM         │
│   Spot F-1 · Eddie                   │
│                                      │
│   ┌────────────────────────────────┐ │
│   │  📅 Add to Calendar            │ │
│   └────────────────────────────────┘ │
│                                      │
│         [ View All Bookings ]        │
│                                      │
└──────────────────────────────────────┘
```

### 5.4 Live Progress Redesign

**Current:** Step-by-step text progress

**Redesigned: Tactical HUD Interface**

```
┌──────────────────────────────────────────────────┐
│  OPERATION: Barry's Chelsea 6:30 AM              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │  ◉───────◉───────◎───────○───────○         │ │
│  │  NAV    FIND    RESERVE  SPOT   CONFIRM    │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  CURRENT: Finding target class...                │
│  ┌─────────────────────────────────────────────┐ │
│  │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░  47%         │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  LOG ─────────────────────────────────────────── │
│  14:32:01  Navigated to schedule page            │
│  14:32:03  Loaded 12 available classes           │
│  14:32:04  Scanning for 6:30 AM...              │
│                                                   │
└──────────────────────────────────────────────────┘
```

---

## 6. Mobile-First / PWA Considerations

### 6.1 Touch Targets

**Minimum Sizes:**
- Buttons: 44px × 44px minimum
- Touch spacing: 8px between tappable elements
- Form inputs: 48px height

### 6.2 Gestures

| Gesture | Action |
|---------|--------|
| Swipe left on target | Reveal delete action |
| Swipe right on target | Toggle enable/disable |
| Pull down | Refresh targets list |
| Long press target | Open quick actions menu |
| Swipe between tabs | Navigate bottom nav |

### 6.3 Safe Areas

```css
/* Apply to all fixed elements */
.bottom-nav {
  padding-bottom: env(safe-area-inset-bottom, 16px);
}

.top-bar {
  padding-top: env(safe-area-inset-top, 16px);
}

.card-container {
  padding-left: env(safe-area-inset-left, 16px);
  padding-right: env(safe-area-inset-right, 16px);
}
```

### 6.4 PWA Manifest

```json
{
  "name": "Class Sniper",
  "short_name": "Sniper",
  "description": "Auto-book competitive fitness classes",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#09090b",
  "theme_color": "#dc2626",
  "icons": [
    {
      "src": "/icons/icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/icons/icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
```

### 6.5 Offline Support

- Cache target list for offline viewing
- Queue target additions when offline
- Show clear offline indicator
- Sync when connection restored

---

## 7. Implementation Roadmap

### Phase 1: Foundation (Week 1)
- [ ] Set up Tailwind CSS with custom theme
- [ ] Implement new color palette + typography
- [ ] Create base component library (Button, Input, Card)
- [ ] Build bottom navigation shell
- [ ] Add PWA manifest + service worker basics

### Phase 2: Core Screens (Week 2)
- [ ] Redesign Target List with new cards
- [ ] Build Add Target sheet/form
- [ ] Implement day/time selectors
- [ ] Add seat selection visual grid
- [ ] Settings screen polish

### Phase 3: Animation & Delight (Week 3)
- [ ] Target lock animation
- [ ] Sniping progress HUD
- [ ] Success confetti + haptics
- [ ] Loading states + skeletons
- [ ] Micro-interactions (hover, press)

### Phase 4: Calendar & Advanced (Week 4)
- [ ] Weekly calendar view
- [ ] Calendar integration (add to cal)
- [ ] Gesture support (swipe actions)
- [ ] Offline mode
- [ ] Notification preferences UI

---

## 8. Asset Requirements

### Icons
- Custom sniper crosshairs logo
- Studio logos (Barry's, Aarmy, etc.)
- Navigation icons (targets, calendar, settings)
- Status icons (locked, sniping, booked, failed)
- Action icons (play, pause, delete, edit)

**Recommendation:** Use Lucide Icons as base, customize key brand icons

### Illustrations
- Empty state: Target with "No targets yet"
- Onboarding: How it works sequence
- Success: Celebration/achievement art

### Sounds (Optional)
- Lock acquired (subtle click)
- Booking success (satisfying confirmation)
- Error (subtle alert)

---

## 9. Technical Stack Recommendations

| Layer | Current | Recommended |
|-------|---------|-------------|
| Framework | Vanilla HTML/JS | React or Preact (for animations) |
| Styling | Inline CSS | Tailwind CSS + CSS Modules |
| Animations | Basic CSS | Framer Motion |
| Icons | Emoji | Lucide React |
| State | Fetch + DOM | Zustand or Jotai |
| Forms | Native | React Hook Form |
| Calendar | None | date-fns + custom |

**Alternative:** Keep vanilla but use Tailwind via CDN for rapid styling

---

## 10. Accessibility Checklist

- [ ] Color contrast ratio ≥ 4.5:1 for text
- [ ] Focus indicators visible
- [ ] Touch targets ≥ 44px
- [ ] Screen reader labels on icons
- [ ] Reduced motion preference respected
- [ ] Keyboard navigation complete
- [ ] Error states clearly communicated
- [ ] Loading states announced

---

## Appendix: Design Tokens Export

```json
{
  "colors": {
    "background": {
      "primary": "#09090b",
      "secondary": "#18181b",
      "tertiary": "#27272a"
    },
    "text": {
      "primary": "#fafafa",
      "secondary": "#a1a1aa",
      "muted": "#71717a"
    },
    "accent": {
      "primary": "#dc2626",
      "hover": "#ef4444",
      "muted": "#991b1b"
    },
    "semantic": {
      "success": "#22c55e",
      "warning": "#f59e0b",
      "error": "#ef4444",
      "info": "#3b82f6"
    }
  },
  "typography": {
    "fontFamily": "'Inter', -apple-system, sans-serif",
    "fontSizes": {
      "xs": "0.75rem",
      "sm": "0.875rem",
      "base": "1rem",
      "lg": "1.125rem",
      "xl": "1.25rem",
      "2xl": "1.5rem",
      "3xl": "1.875rem",
      "4xl": "2.25rem"
    }
  },
  "spacing": {
    "touchTarget": "44px",
    "borderRadius": {
      "sm": "8px",
      "md": "12px",
      "lg": "16px",
      "xl": "24px"
    }
  }
}
```

---

*Generated by Shelldon 🦞 • Feb 2026*
