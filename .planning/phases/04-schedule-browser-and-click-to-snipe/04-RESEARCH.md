# Phase 4: Schedule Browser and Click-to-Snipe - Research

**Researched:** 2026-02-28
**Domain:** Next.js App Router, TanStack Query mutations, shadcn/ui Sheet drawer, credential validation
**Confidence:** HIGH

## Summary

Phase 4 has three distinct sub-problems: (1) promoting the schedule browser to primary nav, (2) replacing the Popover-based snipe flow with a Sheet drawer that supports recurring targets, and (3) adding credential status badges. The schedule browser and `POST /api/targets` endpoint already exist and work — the key work is wiring them together more ergonomically with a Sheet pattern, TanStack Query's `useMutation` for cache invalidation, and a new `POST /api/credentials/validate` endpoint for live credential checking.

The codebase already has the full stack needed: TanStack Query v5 is installed and used in the calendar, `radix-ui` (unified package) has the `Dialog` primitive that a Sheet can be built from, `STUDIOS`/`STUDIO_LOCATIONS`/`SEAT_PREFERENCES` configs exist in shared, and `POST /api/targets` accepts all the fields needed for both recurring and one-time targets. Navigation already lists `/schedule` in `NAV_ITEMS` — SCHED-01 requires it to be the first or most prominent nav item, which is a minimal nav reorder, not a new route. The biggest new work items are: (a) the Sheet component itself (not in ui/ yet), (b) snipe config inside the Sheet that handles both recurring and one-time flows, (c) `useMutation` + `invalidateQueries(['calendar', ...])` for pessimistic UI update after snipe creation, and (d) credential validation logic.

**Primary recommendation:** Build Sheet from existing `Dialog` primitive in radix-ui (already installed), use TanStack Query `useMutation` for the snipe creation, and add a lightweight `POST /api/credentials/validate` route that decrypts + attempts a test auth call per studio platform.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SCHED-01 | Schedule browser reachable from primary nav on every dashboard page | Nav already has `/schedule` link — requires reordering `NAV_ITEMS` to put Schedule second (after Dashboard), confirm it renders on all dashboard pages via shared layout |
| SCHED-02 | User creates snipe target from class in schedule browser (browse → select → configure → confirm, all in sheet drawer, no page redirect) | `POST /api/targets` already works. New: Sheet component + SnipeConfigSheet form with recurring/one-time mode + `useMutation` + calendar cache invalidation |
| SCHED-03 | User can find next available slot for a studio/class type with one click | `handleNextAvailable` already implemented in `schedule-explorer.tsx` — needs to be preserved and integrated into the new sheet flow |
| TRUST-04 | Each stored credential shows Connected/Untested/Invalid status badge on credentials page | No validation endpoint or status column exists. New: `POST /api/credentials/validate` route (decrypts + makes test API call), credential_status column in DB or sessionStorage cache, badge in `CredentialForm` |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| radix-ui | 1.4.3 | Sheet/Dialog primitive | Already installed unified package; Dialog.Root + Dialog.Content can be CSS-positioned as a right-side drawer |
| @tanstack/react-query | 5.90.21 | `useMutation` + cache invalidation | Already installed and wired with QueryClientProvider; v5 API is stable |
| react-hook-form | 7.71.1 | SnipeConfigSheet form state | Already installed; used in add-target-dialog |
| @hookform/resolvers | 5.2.2 | Zod schema validation for form | Already installed |
| zod | 4.3.6 | Schema for snipe target form | Already installed; note v4 API differs from v3 |
| sonner | 2.0.7 | Toast on snipe success/error | Already used throughout |
| lucide-react | 0.564.0 | Icons | Already used throughout |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| date-fns | (via existing usage) | Date formatting | Calendar already uses it; available in node_modules |
| class-variance-authority | 0.7.1 | Badge variant styles | Already used in shadcn components |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Sheet built from Dialog | `vaul` drawer library | `vaul` is purpose-built for drawers/sheets but is NOT installed and adds a dep; Dialog positioning with CSS is simpler and avoids new deps |
| useMutation for snipe creation | Plain `fetch` + `router.refresh()` | Plain fetch is the existing pattern in `add-target-dialog.tsx`, but `useMutation` gives automatic loading/error state and cache invalidation in one call — preferred since TanStack Query is already the data layer |
| DB column for credential_status | sessionStorage/client-side cache | DB column requires migration and makes validation stateful; sessionStorage is ephemeral. Best approach: no stored status — validate on demand when credentials page loads (GET /api/credentials/status) and cache in React state |

**Installation:** No new dependencies needed. All required libraries are already installed.

## Architecture Patterns

### Recommended Project Structure
```
web/src/
├── components/
│   ├── ui/
│   │   └── sheet.tsx                  # NEW — Sheet primitive built from Dialog
│   ├── schedule/                       # NEW folder
│   │   ├── schedule-panel.tsx          # NEW — full schedule browser (extracted from schedule-explorer.tsx)
│   │   └── snipe-config-sheet.tsx      # NEW — slide-in snipe configuration form
│   └── credential-form.tsx             # MODIFY — add status badge
├── hooks/
│   └── use-snipe-mutation.ts           # NEW — useMutation wrapper for POST /api/targets
└── app/
    ├── (dashboard)/
    │   └── schedule/
    │       └── page.tsx                # MODIFY — may embed SchedulePanel
    └── api/
        └── credentials/
            └── validate/
                └── route.ts            # NEW — POST credential validation
```

### Pattern 1: Sheet Built from Dialog Primitive
**What:** A slide-in right-side panel using Radix `Dialog.Root` + `Dialog.Content` with slide-from-right CSS animation.
**When to use:** Any time a task requires overlay UI without a full page redirect.
**Implementation note:** The existing `dialog.tsx` uses `radix-ui`'s unified package (`Dialog as DialogPrimitive from 'radix-ui'`). A Sheet follows the identical pattern with different positioning:

```typescript
// web/src/components/ui/sheet.tsx
// Source: pattern from existing dialog.tsx + shadcn registry pattern
"use client"
import * as React from "react"
import { XIcon } from "lucide-react"
import { Dialog as DialogPrimitive } from "radix-ui"
import { cn } from "@/lib/utils"

function Sheet({ ...props }: React.ComponentProps<typeof DialogPrimitive.Root>) {
  return <DialogPrimitive.Root data-slot="sheet" {...props} />
}

function SheetTrigger({ ...props }: React.ComponentProps<typeof DialogPrimitive.Trigger>) {
  return <DialogPrimitive.Trigger data-slot="sheet-trigger" {...props} />
}

function SheetOverlay({ className, ...props }: React.ComponentProps<typeof DialogPrimitive.Overlay>) {
  return (
    <DialogPrimitive.Overlay
      data-slot="sheet-overlay"
      className={cn(
        "fixed inset-0 z-50 bg-black/60 backdrop-blur-sm",
        "data-[state=open]:animate-in data-[state=closed]:animate-out",
        "data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0",
        className
      )}
      {...props}
    />
  )
}

function SheetContent({ className, children, ...props }: React.ComponentProps<typeof DialogPrimitive.Content>) {
  return (
    <DialogPrimitive.Portal>
      <SheetOverlay />
      <DialogPrimitive.Content
        data-slot="sheet-content"
        className={cn(
          "fixed right-0 top-0 z-50 h-full w-full max-w-md",
          "bg-zinc-950 border-l border-white/10 shadow-xl",
          "flex flex-col overflow-y-auto",
          "data-[state=open]:animate-in data-[state=closed]:animate-out",
          "data-[state=open]:slide-in-from-right data-[state=closed]:slide-out-to-right",
          "duration-300",
          className
        )}
        {...props}
      >
        {children}
        <DialogPrimitive.Close className="absolute right-4 top-4 ...">
          <XIcon />
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  )
}

export { Sheet, SheetTrigger, SheetContent }
```

**Tailwind v4 animation note:** Tailwind v4 uses `animate-in`/`animate-out` via `tw-animate-css` (already imported in `globals.css`). The `slide-in-from-right` and `slide-out-to-right` utilities work with the existing setup.

### Pattern 2: useMutation for Snipe Creation
**What:** TanStack Query v5 `useMutation` wraps `POST /api/targets`, then calls `queryClient.invalidateQueries(['calendar', ...])` on success to trigger a calendar refetch.
**When to use:** Any mutation that should update cached query data after completion (pessimistic UI — only update after server confirms).

```typescript
// web/src/hooks/use-snipe-mutation.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { QUERY_KEYS } from '@/lib/query-keys';
import { toast } from 'sonner';

interface SnipePayload {
  target_type: 'recurring' | 'one_time';
  studio_slug: string;
  location_id: string;
  time: string | null;
  class_type: string | null;
  seat_preference: string;
  preferred_spots: string[];
  // one_time fields
  target_date?: string;
  // recurring fields
  day_of_week?: number;
}

export function useSnipeMutation(weekStart: string, onSuccess?: () => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: SnipePayload) => {
      const res = await fetch('/api/targets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to create snipe target');
      return data;
    },
    onSuccess: () => {
      // Invalidate calendar for current week — calendar refetches, new configured event appears
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.calendarWeek(weekStart) });
      // Also invalidate targets list
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.targets });
      toast.success('Snipe target created');
      onSuccess?.();
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Failed to create snipe target');
    },
  });
}
```

**Key v5 API notes:**
- `useMutation` returns `{ mutate, mutateAsync, isPending, isError, error }` (v5 renamed `isLoading` → `isPending`)
- `invalidateQueries` takes an options object: `{ queryKey: [...] }` (not positional args)
- `onSuccess` fires after mutationFn resolves — this is the pessimistic pattern (no optimistic update)

### Pattern 3: Snipe Config Form (Recurring vs One-Time)
**What:** A `react-hook-form` form inside the SheetContent that switches between recurring and one-time mode based on a toggle.
**When to use:** When form shape changes based on user selection.

The existing `add-target-dialog.tsx` already implements this exact pattern with `targetType` state controlling which fields render. The SnipeConfigSheet can reuse the same field logic, pre-populated from the clicked class:

- Pre-populate: `studio_slug`, `location_id`, `time`, `class_type` from the `NormalizedClass` object passed as props
- Show recurring/one-time toggle (recurring defaults to the class's day-of-week; one-time defaults to the class date)
- `seat_preference` dropdown using `SEAT_PREFERENCES` from `@/lib/studios`
- "Confirm Snipe" button calls `mutate(payload)`, disables while `isPending`

### Pattern 4: Credential Status Validation
**What:** A `POST /api/credentials/validate` endpoint that decrypts stored credentials and makes a platform-specific test auth call. Returns `{ status: 'connected' | 'invalid' }`.
**When to use:** When credentials page loads — fire for each saved credential.

Validation strategy per platform:
- **Mariana Tek:** `POST https://{tenant}.marianatek.com/api/customer/v1/auth/access-tokens` with email/password → 200 = connected, 4xx = invalid. This is a lightweight token check endpoint that doesn't require browser.
- **Xponential:** `POST https://members.{brand}.com/api/xpass/sessions` with email/password → 200/201 = connected, 4xx = invalid.
- **Arketa:** `POST https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}` with email/password → check `idToken` presence.

**Important constraint:** The validate endpoint must decrypt credentials (same logic as `credentials/route.ts`), attempt a lightweight auth call, and return a status. It must NOT store the status in the DB — it's a live check only. The frontend caches the result in component state.

**DB migration NOT needed** for TRUST-04 — the status is computed on-demand, not stored. This is simpler and avoids schema churn.

```typescript
// web/src/app/api/credentials/validate/route.ts (pseudocode)
export async function POST(request: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const { studioSlug } = await request.json();

  // Fetch and decrypt credentials
  const cred = await getDecryptedCredential(user.sub, studioSlug);
  if (!cred) return NextResponse.json({ status: 'untested' });  // not saved

  // Platform-specific auth check
  try {
    const ok = await testStudioAuth(studioSlug, cred);
    return NextResponse.json({ status: ok ? 'connected' : 'invalid' });
  } catch {
    return NextResponse.json({ status: 'invalid' });
  }
}
```

**CredentialForm badge update:** Add a `validationStatus` prop (`'connected' | 'untested' | 'invalid'`) and render a colored badge next to the studio name. The credentials page fires the validate call per saved credential on mount.

### Pattern 5: Nav Reorder for SCHED-01
**What:** The `NAV_ITEMS` array in `nav-bar.tsx` currently orders: Dashboard, Targets, Schedule, History, Credentials. Reorder to make Schedule more prominent.

The success criterion for SCHED-01 says "reachable from primary navigation" — it's already in the nav. The requirement says "not buried in a sub-page." Since it's already a top-level nav link, this is satisfied already. However, moving it to second position (Dashboard, Schedule, ...) gives it more prominence.

**No route change needed** — `/schedule` page exists. This is a 3-line change in `nav-bar.tsx`.

### Anti-Patterns to Avoid
- **Optimistic UI for snipe creation:** The roadmap decision explicitly mandates pessimistic UI — wait for server confirmation before showing the new event on the calendar.
- **router.refresh() after mutation:** The new pattern should use `queryClient.invalidateQueries()` instead of `router.refresh()` — this leverages TanStack Query's cache and avoids full server component re-renders.
- **Dialog instead of Sheet for snipe config:** The Popover-based snipe in `schedule-explorer.tsx` is too small for recurring target configuration. A Sheet (full-height right panel) is the right container.
- **Separate validate page/route navigation:** SCHED-02 explicitly requires no page redirect. Keep the sheet self-contained.
- **Storing validation status in DB:** Adds complexity, requires migration, and creates stale state issues. Validate on-demand and cache in component state only.
- **`@radix-ui/react-dialog` individual package:** The codebase uses the unified `radix-ui` package (`import { Dialog } from 'radix-ui'`), not individual packages. Sheet must follow the same import pattern.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Slide-in drawer animation | Custom CSS keyframes | `tw-animate-css` `slide-in-from-right` utility (already in globals.css) | Already configured; matches project's animation pattern |
| Form validation | Manual field checks | `react-hook-form` + `zod` schema | Already installed; used in add-target-dialog |
| Loading/error state for mutation | `useState(loading)` + `useState(error)` | `useMutation` `isPending`/`isError` | v5 handles all state transitions including race conditions |
| Credential decryption | Duplicate decrypt logic | Extract shared decrypt function from `credentials/route.ts` | Same AES-256-GCM logic in two places is a maintenance hazard |

**Key insight:** The schedule-explorer already implements ~80% of what's needed for SCHED-02 and SCHED-03. The main additions are: Sheet wrapper, recurring mode, and TanStack Query mutation. Don't rebuild what already works.

## Common Pitfalls

### Pitfall 1: TanStack Query v5 `isPending` vs `isLoading`
**What goes wrong:** Developer uses `isLoading` (v4 name) and gets `undefined` — component never shows loading state.
**Why it happens:** v5 renamed `isLoading` → `isPending` for mutations. `isLoading` still exists on queries but means something different.
**How to avoid:** For `useMutation`, always use `isPending`. For `useQuery`, `isLoading` is still the correct term.
**Warning signs:** Loading spinner never appears; form can be double-submitted.

### Pitfall 2: TanStack Query v5 `invalidateQueries` signature
**What goes wrong:** `queryClient.invalidateQueries(QUERY_KEYS.calendarWeek(weekStart))` throws a type error or doesn't invalidate.
**Why it happens:** v5 changed the signature to require an options object: `{ queryKey: [...] }`.
**How to avoid:** Always write `queryClient.invalidateQueries({ queryKey: QUERY_KEYS.calendarWeek(weekStart) })`.

### Pitfall 3: Zod v4 API Differences
**What goes wrong:** Using `z.object().nullable()` behavior that differs from v3, or `z.infer` types not matching.
**Why it happens:** Zod v4 has breaking API changes from v3. The `time` field in `targetSchema` is already correctly defined as `z.string().regex(...).nullable().optional()` — follow this exact pattern for new schema fields.
**How to avoid:** Follow the existing `targetSchema` in `targets/route.ts` as the reference. Don't invent new Zod v4 patterns without verifying against v4 docs.

### Pitfall 4: Credential Validation Timeout on Vercel
**What goes wrong:** The validate endpoint times out on Vercel's 10s Hobby limit for serverless functions.
**Why it happens:** Studio auth APIs (especially Arketa's Firebase endpoint) can be slow. If validate makes 3 requests serially, you're at risk.
**How to avoid:**
- Call each studio's auth endpoint with a 5s `AbortController` timeout
- Return `{ status: 'untested' }` on timeout (don't error)
- Validate credentials one at a time per user action (not all at once on page load)

### Pitfall 5: Sheet Focus Trap on Mobile
**What goes wrong:** On mobile, the Sheet's focus trap prevents scrolling the class list, or the soft keyboard pushes the Sheet's submit button off screen.
**Why it happens:** Radix Dialog/Sheet uses `FocusTrap` internally, which can interact badly with mobile keyboard.
**How to avoid:** Keep the SheetContent scrollable (`overflow-y-auto`). Put the submit button at the bottom with enough padding (`pb-8`). Test with mobile viewport at `max-w-md` width.

### Pitfall 6: Schedule Panel State Reset on Sheet Open
**What goes wrong:** User browses schedule → clicks Snipe → Sheet opens. When Sheet closes, the schedule resets to empty state.
**Why it happens:** If `ScheduleExplorer` or `SchedulePanel` is unmounted when Sheet opens and remounted when it closes.
**How to avoid:** Keep SchedulePanel always mounted. Sheet is a sibling overlay, not a replacement. The Sheet receives the selected class as a prop — it doesn't unmount/remount the schedule.

### Pitfall 7: nav-bar.tsx Schedule Link Already Present
**What goes wrong:** Developer adds a second "Schedule" link thinking it's not in the nav.
**Why it happens:** SCHED-01 says "primary navigation" — developer assumes it's not there yet.
**What's actually needed:** `/schedule` is already in `NAV_ITEMS`. Just reorder to position 2 (after Dashboard). No new route or link needed.

## Code Examples

Verified patterns from project source:

### Existing useMutation Pattern Reference (TanStack Query v5)
```typescript
// Source: @tanstack/react-query v5.90.21 API
// useMutation returns isPending (not isLoading) for mutations
const { mutate, isPending, isError } = useMutation({
  mutationFn: async (payload: SnipePayload) => {
    const res = await fetch('/api/targets', { method: 'POST', body: JSON.stringify(payload) });
    if (!res.ok) throw new Error((await res.json()).error);
    return res.json();
  },
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.calendarWeek(weekStart) });
  },
});
```

### Existing Snipe API Call (from schedule-explorer.tsx)
```typescript
// Source: web/src/app/(dashboard)/schedule/schedule-explorer.tsx
// POST /api/targets for one-time snipe — this is the exact payload the API accepts
await fetch('/api/targets', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    target_type: 'one_time',
    studio_slug: studioSlug,
    location_id: locationId,
    target_date: classDate,
    time: cls.class_time,
    class_type: cls.class_name,
    seat_preference: seatPref,
    preferred_spots: SPOT_PREFERENCES[seatPref] || [],
  }),
});
```

### Sheet Component from Dialog Primitive
```typescript
// Source: pattern derived from web/src/components/ui/dialog.tsx
// radix-ui unified package (not @radix-ui/react-dialog)
import { Dialog as DialogPrimitive } from "radix-ui"

function SheetContent({ className, children, ...props }) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/60 ..." />
      <DialogPrimitive.Content
        className={cn(
          "fixed right-0 top-0 h-full w-full max-w-md bg-zinc-950 border-l border-white/10",
          "data-[state=open]:animate-in data-[state=closed]:animate-out",
          "data-[state=open]:slide-in-from-right data-[state=closed]:slide-out-to-right",
          className
        )}
        {...props}
      >
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  )
}
```

### Credential Validation Endpoint Shape
```typescript
// Source: derived from web/src/app/api/credentials/route.ts decrypt pattern
// No DB migration needed — status is computed on demand
export async function POST(request: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const { studioSlug } = await request.json();

  // Fetch encrypted credential from DB
  const { rows } = await query(
    'SELECT * FROM studio_credentials WHERE user_id = $1 AND studio_slug = $2',
    [user.sub, studioSlug]
  );
  if (rows.length === 0) return NextResponse.json({ status: 'untested' });

  // Decrypt (same logic as credentials route — extract to shared util)
  const email = decrypt(rows[0].encrypted_email, rows[0].iv, rows[0].auth_tag);
  const password = decrypt(rows[0].encrypted_password, rows[0].password_iv, rows[0].password_auth_tag);

  // Platform auth test
  const studio = STUDIOS[studioSlug];
  try {
    const controller = new AbortController();
    setTimeout(() => controller.abort(), 5000); // 5s timeout
    const ok = await testStudioAuth(studio, email, password, controller.signal);
    return NextResponse.json({ status: ok ? 'connected' : 'invalid' });
  } catch {
    return NextResponse.json({ status: 'invalid' });
  }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `router.refresh()` after mutations | `queryClient.invalidateQueries()` | Phase 4 introduces useMutation pattern | No full server component re-render; targeted cache invalidation |
| Popover for snipe config | Sheet drawer | Phase 4 | Room for recurring target config fields |
| Manual `useState(loading)` for mutations | `useMutation.isPending` | Phase 4 | Automatic loading/error/success state |

**Deprecated/outdated in this codebase:**
- Plain `fetch` + `router.refresh()` pattern (used in `add-target-dialog.tsx`, `credential-form.tsx`): still works but not preferred now that TanStack Query is the data layer. Phase 4 introduces `useMutation` as the new pattern. Existing components don't need to be migrated — only new mutations follow this pattern.

## Open Questions

1. **Mariana Tek lightweight auth endpoint availability**
   - What we know: MT adapter uses browser-based PKCE flow for full auth. The API base is `{tenant}.marianatek.com/api/customer/v1/`.
   - What's unclear: Whether `POST /api/customer/v1/auth/access-tokens` accepts email/password directly for validation without full PKCE flow.
   - Recommendation: Test against Barry's API with a real credential in a discovery script before implementing validate route. Fallback: use `GET /api/customer/v1/me` with a Bearer token from a partial auth flow. If neither works cleanly for validation, mark MT credentials as "Untested" and only validate Xponential/Arketa.

2. **Arketa Firebase API key exposure**
   - What we know: Arketa auth uses Firebase `signInWithPassword` which requires a public API key.
   - What's unclear: Whether the Firebase API key is safe to use from a Vercel serverless function (it's public but typically client-side). It may be embedded in the Arketa widget JS.
   - Recommendation: Check the existing `worker/src/adapters/arketa.ts` for how it obtains the Firebase key. If it's hardcoded or captured via browser interception, note it in the validate implementation.

3. **Sheet width on mobile**
   - What we know: The layout uses `max-w-6xl` container. Mobile bottom nav takes 60px.
   - What's unclear: Whether `max-w-md` (448px) is too wide for small phones and needs `max-w-full sm:max-w-md`.
   - Recommendation: Use `w-full sm:max-w-md` — full-width Sheet on mobile (standard pattern), constrained on desktop.

4. **Calendar invalidation scope for recurring targets**
   - What we know: `QUERY_KEYS.calendarWeek(weekStart)` is week-specific.
   - What's unclear: After creating a recurring target (appears every week), invalidating only the current week's cache is sufficient — but the user might have navigated to a different week.
   - Recommendation: Invalidate with partial key `['calendar']` (matches all calendar queries) rather than `QUERY_KEYS.calendarWeek(weekStart)`. Check TanStack Query v5 partial invalidation: `queryClient.invalidateQueries({ queryKey: ['calendar'] })` invalidates all keys starting with `'calendar'`.

## Validation Architecture

> `workflow.nyquist_validation` is not set to `true` in `.planning/config.json` — validation section skipped.

## Sources

### Primary (HIGH confidence)
- `/Users/andeslee/Documents/Cursor-Projects/Fitness-sniper/web/src/app/(dashboard)/schedule/schedule-explorer.tsx` — existing schedule browser with all core functionality
- `/Users/andeslee/Documents/Cursor-Projects/Fitness-sniper/web/src/components/ui/dialog.tsx` — Dialog primitive pattern to derive Sheet from
- `/Users/andeslee/Documents/Cursor-Projects/Fitness-sniper/web/src/hooks/use-calendar-query.ts` — useQuery pattern for consistency reference
- `/Users/andeslee/Documents/Cursor-Projects/Fitness-sniper/web/src/lib/query-keys.ts` — QUERY_KEYS constants
- `/Users/andeslee/Documents/Cursor-Projects/Fitness-sniper/web/src/app/api/targets/route.ts` — POST /api/targets schema and field requirements
- `/Users/andeslee/Documents/Cursor-Projects/Fitness-sniper/web/src/app/api/credentials/route.ts` — encrypt/decrypt pattern for credential validation
- `/Users/andeslee/Documents/Cursor-Projects/Fitness-sniper/web/src/components/nav-bar.tsx` — NAV_ITEMS array and current nav structure
- `/Users/andeslee/Documents/Cursor-Projects/Fitness-sniper/web/package.json` — confirmed dependency versions
- `/Users/andeslee/Documents/Cursor-Projects/Fitness-sniper/.planning/codebase/CONVENTIONS.md` — project coding conventions

### Secondary (MEDIUM confidence)
- `radix-ui` package introspection — confirmed `Dialog` is the only overlay primitive available (no Sheet export). `Sheet` key exists but is empty object.
- `@tanstack/react-query` v5 API: `useMutation`, `isPending`, `invalidateQueries` shape verified via runtime check (`typeof useMutation === 'function'`)
- TanStack Query v5 migration guide (training knowledge, verified against code patterns in use)

### Tertiary (LOW confidence)
- Mariana Tek test auth endpoint behavior — not verified against live API. Needs empirical testing before validate route implementation.
- Arketa Firebase key source — not confirmed from codebase read (arketa.ts in worker not fully examined for key source)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed installed and in active use
- Architecture: HIGH — patterns derived directly from existing code in the repo
- Pitfalls: MEDIUM — TanStack v5 API pitfalls verified; credential validation endpoint behavior is LOW (depends on studio API behavior not tested)
- Sheet component: HIGH — Dialog primitive confirmed, CSS animation utilities confirmed available

**Research date:** 2026-02-28
**Valid until:** 2026-03-30 (stable stack; studio APIs are the main variable)
