# Fast Booking Flow - Verified 2026-02-13

## Summary
**5 browser calls** from schedule to confirmation (when logged in):
1. Navigate to schedule
2. Snapshot to find Reserve link
3. Click Reserve → spot selection
4. Click spot (e.g., F-1) → confirm modal appears
5. Click "Buy & Reserve Class" → BOOKED

**Total time:** ~8-12 seconds

## Optimized Barry's Flow

### Step 1: Navigate (1 call)
```
browser action=navigate profile=openclaw targetUrl="https://www.barrys.com/schedule/noho"
```

### Step 2: Get Reserve Links (1 call)
Wait briefly, then snapshot iframe:
```
browser action=act profile=openclaw request='{"kind":"wait","timeMs":1500}'
browser action=snapshot profile=openclaw frame="iframe.visible" interactive=true
```
Returns: `link "Reserve" [ref=e21]`, `link "Reserve" [ref=e23]`, etc.

### Step 3: Click Reserve (1 call)
```
browser action=act profile=openclaw frame="iframe.visible" request='{"kind":"click","ref":"e21"}'
```
→ Goes directly to spot selection (if logged in)

### Step 4: Select Spot (1 call)
Spot buttons appear as `button "Available Spot"` with image labels (T-1, F-1, etc.)
```
# Get spots
browser action=snapshot profile=openclaw frame="iframe.visible" depth=5

# Click desired spot (e.g., F-1)
browser action=act profile=openclaw frame="iframe.visible" request='{"kind":"click","ref":"e49"}'
```

### Step 5: Confirm (1 call)
Modal appears with:
- `link "Buy & Reserve Class"` [ref=e66] ← CLICK THIS
- `button "Change Spot"` [ref=e67]
- `button "Close this dialog window"` [ref=e68]

```
browser action=act profile=openclaw frame="iframe.visible" request='{"kind":"click","ref":"e66"}'
```

**DONE!** Class booked.

---

## If NOT Logged In

After clicking Reserve, login modal appears instead of spot selection.

### Login Flow (2 extra calls)
```
# Fill credentials
browser action=act profile=openclaw frame="iframe.visible" request='{"kind":"fill","fields":[{"ref":"textbox \"Email\"","text":"EMAIL"},{"ref":"textbox \"Password\"","text":"PASS"}]}'

# Submit
browser action=act profile=openclaw frame="iframe.visible" request='{"kind":"click","ref":"button \"Log in\""}'
```

Then continues to spot selection.

---

## Key Selectors

### Schedule Page (iframe.visible)
| Element | Selector |
|---------|----------|
| Reserve button | `link "Reserve"` |
| Join Waitlist | `link "Join Waitlist"` |
| Day button | `button "Feb 14 Sat"` |
| Instructor | `button "Jennifer S."` |

### Spot Selection (iframe.visible)
| Element | Selector |
|---------|----------|
| Any spot | `button "Available Spot"` |
| Specific spot | Use depth=5 to see labels (T-1, F-1, etc.) |
| Back | `button "Back to Schedule"` |
| Myself/Guest | `radio "Myself"`, `radio "Guest"` |

### Confirm Modal (iframe.visible)
| Element | Selector |
|---------|----------|
| Confirm booking | `link "Buy & Reserve Class"` |
| Change spot | `button "Change Spot"` |
| Cancel | `button "Close this dialog window"` |

### Login Modal (iframe.visible)
| Element | Selector |
|---------|----------|
| Email | `textbox "Email"` |
| Password | `textbox "Password"` |
| Submit | `button "Log in"` |

---

## Speed Optimizations

1. **Skip unnecessary waits** - Only wait 1.5s after navigate
2. **Use `interactive=true`** - Compact snapshots, faster parsing
3. **Batch fill** - Fill email+password in one call
4. **Know the refs** - Memorize common refs to skip snapshots
5. **Stay logged in** - Browser keeps session, saves 2 calls

## Aarmy Differences

Same Mariana Tek platform, slightly different URLs:
- Schedule: `https://mt.aarmy.com/index.html?_mt=%2Fschedule%2Fdaily`
- Iframe: `iframe` (not `iframe.visible`)
- Location selection is in-page buttons before schedule

Flow is identical once on schedule page.
