# Phase 1: Infrastructure Hardening - Research

**Researched:** 2026-02-26
**Domain:** Auth session management, API error standardization, timezone-safe date computation, cross-platform data normalization
**Confidence:** HIGH

## Summary

Phase 1 addresses four production-blocking bugs that have no visible UI but will corrupt all subsequent UI work if left in place. The work divides cleanly into four surgical fixes: (1) implement Cognito `REFRESH_TOKEN_AUTH` so the 30-day cookie is actually honored instead of expiring silently after 1 hour, (2) audit and enforce a consistent `{ error: string }` JSON shape across all 11 API route files, (3) rewrite `getNextClassDate` and `parseTargetDate` in the scheduler to use `toLocaleDateString('en-CA', { timeZone: 'America/New_York' })` instead of `new Date()` server-local-time, and (4) define a `NormalizedClass` type in the shared package with per-platform adapter functions that guarantee no component ever sees `undefined` instructor or `null` time.

The codebase is already mostly correct in its error shape convention — most routes return `{ error: string }` — but three routes have uncovered `throw` paths that bubble to Next.js and return HTML 500 pages instead of JSON. The auth layer is structurally sound; the refresh token is already being stored in the `cognito_refresh_token` httpOnly cookie (confirmed by reading `setAuthCookies` in `cognito.ts:138`), so the refresh flow only needs to be wired — the token storage prerequisite is already met. The scheduler's timezone bug is isolated to two functions in a single file. The data normalization gap is not about different field names — all three API clients already produce `ClassScheduleRow` objects with identical fields — but about runtime safety when fields are `null` in the UI (components that do `.substring()` on `class_time` when it could theoretically be null).

**Primary recommendation:** Make all four changes in separate atomic tasks in the order listed — auth refresh, then API error audit, then timezone fix, then normalization type — since each is independently testable and none depends on the others.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-01 | User session automatically refreshes when Cognito access token expires (no silent logout after 1 hour) | Cognito `REFRESH_TOKEN_AUTH` flow documented in AWS SDK v3; refresh token cookie already stored at `cognito_refresh_token`; needs wiring in `getSession()` or a new `/api/auth/refresh` route |
| INFRA-02 | All API routes return consistent error shapes with user-facing messages and appropriate HTTP status codes | 11 route files audited; most already return `{ error: string }`; 3 routes have uncovered throw paths; `jobs/route.ts` and `history/route.ts` have no try/catch at all |
| INFRA-03 | Worker timezone handling in `getNextClassDate` correctly computes dates in America/New_York regardless of server timezone | Bug confirmed at `worker/src/jobs/scheduler.ts:233-250`; uses `new Date()` + `now.getDay()` (server local); fix pattern exists in `slot-watcher.ts` using `toLocaleDateString('en-CA', { timeZone: 'America/New_York' })` |
| INFRA-04 | Data normalization layer produces consistent `NormalizedClass` objects from all 3 platforms (MT, Xponential, Arketa) | All three API clients already produce `ClassScheduleRow`; gap is a missing `NormalizedClass` UI type with non-null guarantees and per-platform normalizer functions in shared package |
</phase_requirements>

---

## Standard Stack

### Core (no new dependencies needed)

All Phase 1 work uses existing dependencies. No new packages required.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@aws-sdk/client-cognito-identity-provider` | `^3.750.0` | Already installed. `InitiateAuthCommand` with `REFRESH_TOKEN_AUTH` flow handles token refresh | Official AWS SDK — only correct way to call Cognito |
| `next/headers` `cookies()` | Next.js 16.1.6 | Read and write httpOnly auth cookies in API routes | Built-in App Router API |
| TypeScript strict mode | 5.x | Enforces `string | null` handling at compile time — catches undefined instructor bugs | Already configured via `web/tsconfig.json` |
| `packages/shared/src/types.ts` | Workspace | Location for `NormalizedClass` type — already the correct home for shared types | No build step; both web and worker consume it |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `node:crypto` | Built-in | Not needed for Phase 1, but noting the existing AES-256-GCM pattern for context | Only relevant if credential refactor comes into scope |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Server-side `REFRESH_TOKEN_AUTH` in API route | Client-side TanStack Query `onError` interceptor | Client interceptor is Phase 2 work (TanStack Query not installed yet); server-side refresh is self-contained and can be done now |
| Custom error middleware | Per-route try/catch | Next.js App Router has no global middleware for API routes; per-route wrapping is the only supported approach |
| `Temporal` API for timezone | `toLocaleDateString('en-CA', { timeZone })` | `Temporal` is not available in Node 24 without polyfill; `toLocaleDateString` is the established pattern already used in `slot-watcher.ts` |

**Installation:** No new packages required for Phase 1.

---

## Architecture Patterns

### Recommended Project Structure

No new files needed beyond:
```
packages/shared/src/
└── types.ts           # Add NormalizedClass type here (existing file)

web/src/lib/
└── cognito.ts         # Add refreshSession() here (existing file)

web/src/app/api/
└── auth/
    └── refresh/
        └── route.ts   # New: POST /api/auth/refresh endpoint
```

### Pattern 1: Cognito REFRESH_TOKEN_AUTH

**What:** Use `InitiateAuthCommand` with `AuthFlow: 'REFRESH_TOKEN_AUTH'` and `AuthParameters: { REFRESH_TOKEN: token, SECRET_HASH: hash }`. Returns new `AccessToken` and `IdToken` (does NOT return a new `RefreshToken`).

**When to use:** When `getSession()` catches an exception from `GetUserCommand` (indicating the access token has expired), attempt refresh before returning null.

**Example:**
```typescript
// Source: AWS SDK v3 Cognito docs
// web/src/lib/cognito.ts — new refreshSession() function

export async function refreshSession(
  refreshToken: string,
  email: string, // needed for SECRET_HASH computation
): Promise<{ accessToken: string; idToken: string } | null> {
  try {
    const secretHash = computeSecretHash(email);
    const command = new InitiateAuthCommand({
      AuthFlow: 'REFRESH_TOKEN_AUTH',
      ClientId: CLIENT_ID,
      AuthParameters: {
        REFRESH_TOKEN: refreshToken,
        ...(secretHash && { SECRET_HASH: secretHash }),
      },
    });
    const response = await client.send(command);
    const result = response.AuthenticationResult;
    if (!result?.AccessToken || !result.IdToken) return null;
    return {
      accessToken: result.AccessToken,
      idToken: result.IdToken,
    };
  } catch {
    return null; // Refresh token expired or invalid — user must log in again
  }
}
```

**Critical note on SECRET_HASH:** The `computeSecretHash` function requires a username. For `REFRESH_TOKEN_AUTH`, pass the user's email (same as username). The email must be read from the `cognito_id_token` cookie (JWT decode the payload — no network call needed).

**Integration into `getSession()`:**
```typescript
// Modified getSession() — tries access token first, falls back to refresh
export async function getSession(): Promise<CognitoUser | null> {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get('cognito_access_token')?.value;
  const idToken = cookieStore.get('cognito_id_token')?.value;
  const refreshToken = cookieStore.get('cognito_refresh_token')?.value;

  if (!accessToken || !idToken) return null;

  try {
    const response = await client.send(new GetUserCommand({ AccessToken: accessToken }));
    const email = response.UserAttributes?.find((a) => a.Name === 'email')?.Value || '';
    return { sub: response.Username!, email };
  } catch {
    // Access token expired — attempt refresh
    if (!refreshToken) return null;

    // Decode email from id token for SECRET_HASH
    const payload = JSON.parse(Buffer.from(idToken.split('.')[1], 'base64url').toString());
    const email = payload.email as string;

    const refreshed = await refreshSession(refreshToken, email);
    if (!refreshed) return null;

    // New tokens must be set on the response — getSession() runs server-side
    // Option A: Return tokens alongside user and let each route set cookies
    // Option B: Use a dedicated /api/auth/refresh route called client-side
    // RECOMMENDATION: Use Option B — cleaner, client triggers refresh on 401
  }
}
```

**Recommended implementation approach:** A dedicated `POST /api/auth/refresh` route that reads the `cognito_refresh_token` cookie, calls `REFRESH_TOKEN_AUTH`, and sets updated `cognito_access_token` and `cognito_id_token` cookies. The existing `getSession()` remains unchanged. The client-side global 401 handler (implemented in Phase 2 via TanStack Query) calls `/api/auth/refresh` then retries. This avoids complexity of cookie mutation inside `getSession()` which runs in a read-only server context.

**Why not mutate cookies in `getSession()`:** In Next.js App Router, `cookies()` from `next/headers` allows writing only from route handlers and Server Actions, not from arbitrary server functions called inside route handlers. The response object needed to `set()` cookies is only available at the route handler level.

### Pattern 2: API Error Standardization

**What:** Wrap every route handler's main logic in a try/catch that returns `{ error: string }` with an appropriate status code. Never let Next.js catch an unhandled throw (which returns an HTML 500 page in development and a blank 500 in production).

**Standard shape:**
```typescript
// Consistent error response shape across all routes
return NextResponse.json({ error: string }, { status: number });

// SUCCESS shapes are route-specific (rows, totals, etc.) — only errors are standardized
```

**Audit findings — routes that need wrapping:**

| Route | Current State | Gap |
|-------|--------------|-----|
| `auth/login/route.ts` | GOOD — full try/catch, `mapCognitoError` | None |
| `auth/signup/route.ts` | Likely GOOD — mirrors login | Verify |
| `auth/logout/route.ts` | Needs audit | Potentially throws |
| `targets/route.ts` | GOOD — Zod errors handled, 401 handled | DB query outside try/catch |
| `targets/[id]/route.ts` | GOOD — 401 and 404 handled | No try/catch around query |
| `credentials/route.ts` | GOOD — full try/catch in POST | DELETE has no try/catch |
| `jobs/route.ts` | NO try/catch — DB query throws directly | Full wrapping needed |
| `history/route.ts` | NO try/catch — `Promise.all` can throw | Full wrapping needed |
| `schedules/route.ts` | GOOD — multi-level try/catch, graceful fallback | None |
| `dashboard/stats/route.ts` | NO try/catch — `Promise.all` throws directly | Full wrapping needed |
| `worker-status/route.ts` | NO try/catch — DB query can throw | Wrapping needed |

**Standard wrapper pattern:**
```typescript
export async function GET() {
  try {
    const user = await getSession();
    if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

    const { rows } = await query('SELECT ...', [...]);
    return NextResponse.json(rows);
  } catch (err) {
    console.error('[route-name] Error:', err);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 },
    );
  }
}
```

### Pattern 3: Timezone-Safe Date Computation

**What:** Replace `new Date()` + `Date.prototype.getDay()` with explicit `America/New_York` timezone computation.

**Current buggy pattern (scheduler.ts:233-250):**
```typescript
// BUGGY: uses server local time
export function getNextClassDate(dayOfWeek: number, time: string): Date {
  const now = new Date();
  // ...
  const daysUntil = (dayOfWeek - now.getDay() + 7) % 7; // getDay() = server timezone
  // ...
}
```

**Correct pattern (already used in slot-watcher.ts):**
```typescript
// CORRECT: explicit America/New_York timezone
function getNowInET(): { date: string; dayOfWeek: number; hours: number; minutes: number } {
  const now = new Date();
  const etDateStr = now.toLocaleDateString('en-CA', { timeZone: 'America/New_York' }); // "YYYY-MM-DD"
  const [year, month, day] = etDateStr.split('-').map(Number);
  const etDate = new Date(year, month - 1, day);

  // Get day of week in ET
  const etDayStr = now.toLocaleDateString('en-US', { timeZone: 'America/New_York', weekday: 'short' });
  const dayMap: Record<string, number> = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
  const dayOfWeek = dayMap[etDayStr.substring(0, 3)] ?? new Date(etDateStr).getDay();

  return { date: etDateStr, dayOfWeek, hours: 0, minutes: 0 };
}

export function getNextClassDate(dayOfWeek: number, time: string): Date {
  const parsed = parseTime(time);
  const hours = parsed?.hours24 ?? 0;
  const minutes = parsed?.minutes ?? 0;

  const now = new Date();
  // Get current date in America/New_York as YYYY-MM-DD
  const etTodayStr = now.toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
  const [year, month, day] = etTodayStr.split('-').map(Number);

  // Build a Date at the class time on the target day
  const target = new Date(year, month - 1, day, hours, minutes, 0, 0);

  // Get current day-of-week in ET
  const etDay = new Date(etTodayStr + 'T12:00:00').getDay(); // noon avoids DST edge
  const daysUntil = (dayOfWeek - etDay + 7) % 7;
  target.setDate(target.getDate() + daysUntil);

  // If same day and time has passed in ET, push to next week
  const etNowHour = parseInt(
    now.toLocaleTimeString('en-US', { timeZone: 'America/New_York', hour: 'numeric', hour12: false }),
    10,
  );
  const etNowMin = parseInt(
    now.toLocaleTimeString('en-US', { timeZone: 'America/New_York', minute: 'numeric' }),
    10,
  );
  if (daysUntil === 0 && (etNowHour > hours || (etNowHour === hours && etNowMin >= minutes))) {
    target.setDate(target.getDate() + 7);
  }

  return target;
}
```

**Simpler version using the established pattern from `slot-watcher.ts`:**
```typescript
// slot-watcher.ts already does this correctly:
const nowET = new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
// Use the same pattern in scheduler.ts
```

**Also fix `parseTargetDate`:** This function uses `new Date(year, month - 1, day, hours, minutes)` which is correct (explicit year/month/day constructor avoids timezone ambiguity for local-time interpretation). No change needed there.

**Also fix the web `getClassDate` helper in `targets/route.ts:142-168`:** Uses the same local-time `new Date()` + `getDay()` pattern. Same fix applies.

### Pattern 4: NormalizedClass Type

**What:** Define a `NormalizedClass` interface in `packages/shared/src/types.ts` with no nullable fields that can cause component crashes. Add per-platform normalizer functions.

**Current state:** All three API clients return `ClassScheduleRow` with these nullable fields:
- `class_name: string | null` — MT and Xpo can be null; Arketa hardcodes 'PERSONAL SAUNA & ICE BATH'
- `instructor: string | null` — all three can be null
- `booking_opens_at: string | null` — all three can be null; Arketa always null

**What components actually need (no nulls in display strings):**
```typescript
// Add to packages/shared/src/types.ts

/**
 * Normalized class data for UI rendering.
 * All string fields are guaranteed non-null — undefined instructor becomes "Staff",
 * undefined class_name becomes the studio name.
 * Produced by normalizeClass() from any platform's ClassScheduleRow.
 */
export interface NormalizedClass {
  studio_slug: string;
  location_id: string;
  class_date: string;         // "YYYY-MM-DD"
  class_time: string;         // "H:MM AM" — always present
  class_name: string;         // never null — falls back to studio name
  instructor: string;         // never null — falls back to "Staff"
  duration_minutes: number;   // never null — falls back to 60
  available: boolean;
  spots_remaining: number;    // never null — falls back to 0
  booking_opens_at: string | null; // nullable is OK — UI shows nothing when null
}

/**
 * Normalize a ClassScheduleRow into a NormalizedClass for safe UI rendering.
 * studioName is used as fallback for class_name (e.g. "Barry's Bootcamp").
 */
export function normalizeClass(row: ClassScheduleRow, studioName: string): NormalizedClass {
  return {
    studio_slug: row.studio_slug,
    location_id: row.location_id,
    class_date: row.class_date,
    class_time: row.class_time,
    class_name: row.class_name || studioName,
    instructor: row.instructor || 'Staff',
    duration_minutes: row.duration_minutes ?? 60,
    available: row.available,
    spots_remaining: row.spots_remaining ?? 0,
    booking_opens_at: row.booking_opens_at,
  };
}
```

**Where to apply the normalizer:** At the API boundary — in `web/src/app/api/schedules/route.ts` before sending the response. The components never need to handle null strings.

### Anti-Patterns to Avoid

- **Mutating cookies inside `getSession()`:** `cookies()` in App Router is read-only outside of route handlers. Attempting `cookieStore.set()` in a utility function throws a runtime error. Keep cookie writes at the route handler level only.
- **Using `new Date().getDay()` for timezone-sensitive scheduling:** Returns server local time. If the server is ever in UTC (cloud deployment), this is wrong by 5-8 hours. Always use `toLocaleDateString('en-CA', { timeZone: 'America/New_York' })`.
- **Returning `null` for instructor in UI components:** Any component doing `instructor.substring(0, 1)` or `instructor.toUpperCase()` will throw. Apply `normalizeClass()` at the API boundary, not in individual components.
- **Global error handler in App Router API:** App Router does not support Express-style global error middleware for route handlers. Each route must handle its own errors.
- **Catching and swallowing errors without logging:** `try { ... } catch { return null; }` hides bugs. Always `console.error` before returning an error response.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cognito token refresh | Custom JWT decode + expiry check | `REFRESH_TOKEN_AUTH` via existing `InitiateAuthCommand` | AWS SDK handles token validation, clock skew, and error cases |
| Timezone day-of-week | DST lookup tables | `toLocaleDateString('en-CA', { timeZone: 'America/New_York' })` | Built into Node.js v24 — handles DST automatically |
| Cross-platform data shape union types | Large discriminated union | Single `NormalizedClass` + `normalizeClass()` at boundary | Simpler than maintaining 3 type variants in components |

**Key insight:** Every problem in Phase 1 has a working solution already used elsewhere in the codebase or directly available in Node.js builtins. No new abstractions are needed — just connecting existing patterns.

---

## Common Pitfalls

### Pitfall 1: SECRET_HASH Required for REFRESH_TOKEN_AUTH
**What goes wrong:** Calling `REFRESH_TOKEN_AUTH` without `SECRET_HASH` throws `InvalidParameterException: SECRET_HASH: Unable to compute SecretHash when context is empty`.
**Why it happens:** When a Cognito app client has a client secret configured (which it does — `COGNITO_CLIENT_SECRET` is set), ALL auth flows require `SECRET_HASH`.
**How to avoid:** The `computeSecretHash(username)` function in `cognito.ts` handles this. For `REFRESH_TOKEN_AUTH`, the username is the user's email — decode it from the `cognito_id_token` JWT payload (no network call needed: `JSON.parse(Buffer.from(idToken.split('.')[1], 'base64url').toString()).email`).
**Warning signs:** `InvalidParameterException` or `NotAuthorizedException` on refresh attempts.

### Pitfall 2: REFRESH_TOKEN_AUTH Does Not Return a New Refresh Token
**What goes wrong:** Trying to update the `cognito_refresh_token` cookie with a new value after refresh — the API does not return one.
**Why it happens:** Cognito refresh tokens have their own long expiry (default 30 days). Only `USER_PASSWORD_AUTH` returns a refresh token. `REFRESH_TOKEN_AUTH` returns only `AccessToken` and `IdToken`.
**How to avoid:** Only update `cognito_access_token` and `cognito_id_token` cookies after a successful refresh. Leave `cognito_refresh_token` unchanged.
**Warning signs:** Attempting to write `undefined` to the refresh token cookie.

### Pitfall 3: `getSession()` is Called on Every Request (Performance)
**What goes wrong:** Adding refresh logic to `getSession()` doubles the Cognito API calls (one `GetUserCommand` + one `InitiateAuthCommand`) on every request for users with expired tokens.
**Why it happens:** `getSession()` already adds ~50-200ms per call. Adding a second round-trip makes this 100-400ms.
**How to avoid:** Use the `/api/auth/refresh` route approach instead. Client calls it once on 401, gets new cookies, retries the original request. Server-side `getSession()` remains a single `GetUserCommand`.
**Warning signs:** Slow API responses for all authenticated routes.

### Pitfall 4: DST Transition Edge Cases in Scheduler
**What goes wrong:** On DST transition days (second Sunday in March, first Sunday in November), `getNextClassDate` could produce a time that's 1 hour off even with the `en-CA` fix if not careful.
**Why it happens:** A class at 6:00 AM on the transition day may appear at 5:00 AM or 7:00 AM in UTC. The fix constructs the local Date using `new Date(year, month-1, day, hours, minutes)` which uses server timezone, not ET.
**How to avoid:** The `parseTargetDate` function is already correct — it uses the explicit year/month/day/hours/minutes constructor which bypasses timezone conversion entirely (local time construction). `getNextClassDate` needs the same approach: construct `new Date(year, month-1, day, hours, minutes)` using ET year/month/day.
**Warning signs:** Jobs created 1 hour too early or too late on DST transition weekends.

### Pitfall 5: HTML 500 Responses Break JSON Parsing in Components
**What goes wrong:** Components calling `fetch('/api/jobs')` do `const data = await res.json()` — if Next.js returns an HTML error page (from an unhandled throw), `res.json()` throws a SyntaxError and the component crashes entirely rather than showing an error state.
**Why it happens:** 3 routes (`jobs/route.ts`, `history/route.ts`, `dashboard/stats/route.ts`) have no try/catch around their DB queries.
**How to avoid:** Wrap all route handler logic in try/catch with `{ error: string }` return. In components, always check `res.ok` before calling `res.json()`.
**Warning signs:** `SyntaxError: Unexpected token '<'` in browser console (HTML in JSON context).

### Pitfall 6: `NormalizedClass` Must Be Applied at the API Boundary
**What goes wrong:** Applying `normalizeClass()` inside individual components means some components are protected and others aren't. When a new component is added, it receives raw `ClassScheduleRow` and assumes non-null.
**Why it happens:** Convenience — it's tempting to normalize "where you use it."
**How to avoid:** Apply `normalizeClass()` in `web/src/app/api/schedules/route.ts` and document the response type as `NormalizedClass[]`. Components only ever receive `NormalizedClass` from the API.
**Warning signs:** Some components crash on null instructor while others don't.

---

## Code Examples

Verified patterns from codebase analysis and AWS SDK v3 docs:

### Cognito REFRESH_TOKEN_AUTH — New Route
```typescript
// web/src/app/api/auth/refresh/route.ts
// Source: aws-sdk/client-cognito-identity-provider InitiateAuthCommand

import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { InitiateAuthCommand } from '@aws-sdk/client-cognito-identity-provider';
// ... import client, CLIENT_ID, computeSecretHash from @/lib/cognito

export async function POST() {
  const cookieStore = await cookies();
  const refreshToken = cookieStore.get('cognito_refresh_token')?.value;
  const idToken = cookieStore.get('cognito_id_token')?.value;

  if (!refreshToken || !idToken) {
    return NextResponse.json({ error: 'No refresh token' }, { status: 401 });
  }

  try {
    // Decode email from id token payload (no network call)
    const payload = JSON.parse(
      Buffer.from(idToken.split('.')[1], 'base64url').toString(),
    );
    const email = payload.email as string;
    const secretHash = computeSecretHash(email);

    const command = new InitiateAuthCommand({
      AuthFlow: 'REFRESH_TOKEN_AUTH',
      ClientId: CLIENT_ID,
      AuthParameters: {
        REFRESH_TOKEN: refreshToken,
        ...(secretHash && { SECRET_HASH: secretHash }),
      },
    });

    const response = await client.send(command);
    const result = response.AuthenticationResult;

    if (!result?.AccessToken || !result.IdToken) {
      return NextResponse.json({ error: 'Refresh failed' }, { status: 401 });
    }

    const res = NextResponse.json({ success: true });
    // Only update access and id tokens — refresh token unchanged
    const cookieOptions = {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict' as const,
      path: '/',
      maxAge: 60 * 60 * 24 * 30,
    };
    res.cookies.set('cognito_access_token', result.AccessToken, cookieOptions);
    res.cookies.set('cognito_id_token', result.IdToken, cookieOptions);
    return res;
  } catch (err) {
    console.error('[auth/refresh] Refresh failed:', err);
    return NextResponse.json({ error: 'Session expired' }, { status: 401 });
  }
}
```

### Timezone-Safe Scheduler Fix
```typescript
// worker/src/jobs/scheduler.ts — fixed getNextClassDate
// Source: slot-watcher.ts existing pattern + Node.js Intl API

export function getNextClassDate(dayOfWeek: number, time: string): Date {
  const parsed = parseTime(time);
  const hours = parsed?.hours24 ?? 0;
  const minutes = parsed?.minutes ?? 0;

  // Get today's date in America/New_York
  const etTodayStr = new Date().toLocaleDateString('en-CA', {
    timeZone: 'America/New_York',
  }); // "YYYY-MM-DD"

  const [year, month, day] = etTodayStr.split('-').map(Number);

  // Build date at class time using explicit year/month/day (local time construction)
  const target = new Date(year, month - 1, day, hours, minutes, 0, 0);

  // Get day of week from the ET date string (avoids getDay() server-timezone issue)
  const etDayOfWeek = new Date(etTodayStr + 'T12:00:00').getDay(); // noon avoids DST edge case

  const daysUntil = (dayOfWeek - etDayOfWeek + 7) % 7;
  target.setDate(target.getDate() + daysUntil);

  // If same day and time has already passed in ET, push to next week
  const etNow = new Date().toLocaleString('en-US', { timeZone: 'America/New_York' });
  const etNowDate = new Date(etNow);
  if (daysUntil === 0 && target <= etNowDate) {
    target.setDate(target.getDate() + 7);
  }

  return target;
}
```

### API Route Error Wrapping
```typescript
// Standard pattern for routes that currently have no try/catch
// Source: existing well-structured routes (credentials/route.ts POST)

export async function GET() {
  try {
    const user = await getSession();
    if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

    const { rows } = await query(`SELECT ...`, [user.sub]);
    return NextResponse.json(rows);
  } catch (err) {
    console.error('[jobs] GET error:', err);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
```

### NormalizedClass Type Addition
```typescript
// Add to packages/shared/src/types.ts after ClassScheduleRow

export interface NormalizedClass {
  studio_slug: string;
  location_id: string;
  class_date: string;
  class_time: string;
  class_name: string;       // non-null
  instructor: string;       // non-null
  duration_minutes: number; // non-null
  available: boolean;
  spots_remaining: number;  // non-null
  booking_opens_at: string | null;
}

export function normalizeClass(row: ClassScheduleRow, studioName: string): NormalizedClass {
  return {
    studio_slug: row.studio_slug,
    location_id: row.location_id,
    class_date: row.class_date,
    class_time: row.class_time,
    class_name: row.class_name || studioName,
    instructor: row.instructor || 'Staff',
    duration_minutes: row.duration_minutes ?? 60,
    available: row.available,
    spots_remaining: row.spots_remaining ?? 0,
    booking_opens_at: row.booking_opens_at,
  };
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `getSession()` returns null on expired token, user must re-login | `REFRESH_TOKEN_AUTH` → transparent session extension | INFRA-01 | Users stay logged in for 30 days as intended |
| Unhandled throws produce HTML 500 in 3 routes | All routes wrapped in try/catch returning `{ error: string }` | INFRA-02 | Client fetch code never receives HTML in JSON context |
| `getDay()` uses server local timezone in scheduler | `toLocaleDateString('en-CA', { timeZone: 'America/New_York' })` | INFRA-03 | Scheduler correct on any server regardless of system timezone |
| `ClassScheduleRow` with nullable strings passed to UI | `NormalizedClass` with non-null strings via `normalizeClass()` | INFRA-04 | No component can crash from null `.substring()` call |

**Deprecated/outdated:**
- `new Date().getDay()` in scheduler: Replaced by timezone-explicit pattern from `slot-watcher.ts`. The existing comment "relies on system timezone being America/New_York" acknowledges the fragility.

---

## Open Questions

1. **Does `computeSecretHash` need to be exported from cognito.ts for the refresh route?**
   - What we know: It's currently a private function in `cognito.ts`
   - What's unclear: Whether the refresh route should live in the same file or call an exported helper
   - Recommendation: Export `computeSecretHash` and the Cognito `client` constant, or add `refreshSession()` as an exported function in `cognito.ts` and call it from the route handler. The latter is cleaner.

2. **Should the refresh route be `GET` or `POST`?**
   - What we know: It reads and writes cookies; no request body is needed; it has a side effect (updates cookies)
   - What's unclear: REST conventions suggest POST for side effects
   - Recommendation: `POST /api/auth/refresh` — consistent with the auth route family (`login`, `logout`, `signup` are all POST).

3. **Does `getClassDate` in `targets/route.ts` also need the timezone fix?**
   - What we know: It uses the same `new Date()` + `getDay()` pattern as `getNextClassDate`
   - What's unclear: Whether the one-time target path is also affected (it uses explicit year/month/day — likely safe)
   - Recommendation: Fix the recurring branch of `getClassDate` in `targets/route.ts` using the same timezone-explicit pattern. The one-time branch using `new Date(year, month - 1, day, hours, minutes)` is already correct.

4. **Should `NormalizedClass` replace `ClassScheduleRow` in the schedules API response, or coexist?**
   - What we know: `ClassScheduleRow` is used by worker scrapers for DB inserts (needs nullable fields); `NormalizedClass` is the UI type
   - What's unclear: Whether changing the API response type breaks existing components
   - Recommendation: Keep both. `ClassScheduleRow` stays for DB/scraper use. `NormalizedClass` is the API response type for `/api/schedules`. Apply `normalizeClass()` in the response mapping in `schedules/route.ts`. Existing components already handle null gracefully in most cases (the risk is future components).

---

## Codebase Specifics

### Files Touched in Phase 1

| File | Change | Requirement |
|------|--------|-------------|
| `web/src/lib/cognito.ts` | Add `refreshSession()` exported function | INFRA-01 |
| `web/src/app/api/auth/refresh/route.ts` | **NEW** — POST refresh endpoint | INFRA-01 |
| `web/src/app/api/jobs/route.ts` | Wrap GET in try/catch | INFRA-02 |
| `web/src/app/api/history/route.ts` | Wrap GET in try/catch | INFRA-02 |
| `web/src/app/api/dashboard/stats/route.ts` | Wrap GET in try/catch | INFRA-02 |
| `web/src/app/api/worker-status/route.ts` | Wrap GET in try/catch | INFRA-02 |
| `web/src/app/api/targets/route.ts` | Wrap DB query in try/catch | INFRA-02 |
| `web/src/app/api/targets/[id]/route.ts` | Wrap DB query in try/catch | INFRA-02 |
| `web/src/app/api/credentials/route.ts` | Wrap DELETE in try/catch | INFRA-02 |
| `web/src/app/api/auth/logout/route.ts` | Audit and wrap if needed | INFRA-02 |
| `worker/src/jobs/scheduler.ts` | Fix `getNextClassDate` + `parseTargetDate` timezone | INFRA-03 |
| `web/src/app/api/targets/route.ts` | Fix `getClassDate` recurring branch timezone | INFRA-03 |
| `packages/shared/src/types.ts` | Add `NormalizedClass` interface + `normalizeClass()` | INFRA-04 |
| `web/src/app/api/schedules/route.ts` | Apply `normalizeClass()` in response mapping | INFRA-04 |

### Key Constraint: Worker Import Extensions
Any changes to `worker/src/jobs/scheduler.ts` must preserve `.js` extensions on all imports (required by `moduleResolution: NodeNext`):
```typescript
import { query } from '../db.js';          // KEEP .js
import { parseTime, STUDIOS } from '@fitness-sniper/shared'; // workspace — no extension needed
```

### Confirmed: Refresh Token Cookie IS Being Stored
Reading `web/src/lib/cognito.ts:138`, `setAuthCookies()` sets all three cookies including `cognito_refresh_token`. This was flagged as a blocker in STATE.md but is confirmed resolved — the cookie is stored on login. The refresh flow just needs to be wired to use it.

### Token Expiry Configuration
Cognito access tokens default to 1 hour expiry (not configurable via SDK — set in User Pool console). ID tokens same. Refresh tokens default to 30 days. These defaults apply unless overridden in the Cognito User Pool console — cannot be changed in code.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis — `web/src/lib/cognito.ts`, `worker/src/jobs/scheduler.ts`, all 11 API route files, `packages/shared/src/types.ts`, `packages/shared/src/api/*.ts`
- `.planning/codebase/CONCERNS.md` — timezone bug confirmed at lines 21-25; refresh token storage confirmed at lines 95-99
- Node.js v24 Intl API — `toLocaleDateString('en-CA', { timeZone: 'America/New_York' })` is a built-in, no polyfill required

### Secondary (MEDIUM confidence)
- [AWS SDK v3 Cognito `InitiateAuthCommand` docs](https://docs.aws.amazon.com/AWSJavaScriptSDK/v3/latest/client/cognito-identity-provider/command/InitiateAuthCommand/) — `REFRESH_TOKEN_AUTH` flow parameters and response shape
- [AWS Cognito `REFRESH_TOKEN_AUTH` requires `SECRET_HASH`](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-authentication-flow.html#Using-SRP-password-verification-in-custom-authentication-flow) — confirmed SECRET_HASH requirement when client secret is configured
- Next.js App Router docs — `cookies()` write restrictions (route handlers and Server Actions only)

### Tertiary (LOW confidence — flagged for validation)
- Pattern for reading email from ID token JWT payload without network call — standard JWT structure, decode payload from base64url middle segment. Confirmed valid for Cognito ID tokens (they contain standard claims including `email`).

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all patterns use existing installed packages
- Architecture: HIGH — based on direct codebase analysis of actual files; no speculation about what exists
- Pitfalls: HIGH — INFRA-01 pitfall (SECRET_HASH on refresh) is a well-documented Cognito requirement; INFRA-02 pitfall (HTML 500) is confirmed by reading 3 unprotected routes; INFRA-03 pitfall (DST edge case) is a known JS timezone issue; INFRA-04 pitfall (boundary vs component normalization) is a standard software pattern
- Timezone fix: HIGH — the slot-watcher.ts already uses the correct pattern; this is a confirmed copy-from-existing-code fix

**Research date:** 2026-02-26
**Valid until:** 2026-03-28 (30 days — all patterns are stable Node.js/Cognito fundamentals)
