---
phase: 01-infrastructure-hardening
verified: 2026-02-26T00:00:00Z
status: passed
score: 8/8 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Call POST /api/auth/refresh with a real expired access token and valid 30-day refresh token"
    expected: "Response status 200, new cognito_access_token and cognito_id_token cookies are set, subsequent authenticated requests succeed"
    why_human: "Cannot call live Cognito REFRESH_TOKEN_AUTH without real credentials and an actually-expired access token pair"
  - test: "Make an API request that triggers a DB error (e.g., disconnect DB pool mid-request)"
    expected: "Response is JSON { error: 'Internal server error' } with status 500 — no HTML error page"
    why_human: "Cannot induce a real DB failure in a static code check; requires runtime injection"
---

# Phase 1: Infrastructure Hardening Verification Report

**Phase Goal:** The app never silently fails — sessions stay alive, API errors are parseable, timestamps render on the correct day, and all three studio platforms produce uniform data shapes
**Verified:** 2026-02-26
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | POST /api/auth/refresh reads cognito_refresh_token, calls REFRESH_TOKEN_AUTH, sets new access + id cookies | VERIFIED | Route reads both cookies, calls `refreshSession()`, sets `cognito_access_token` and `cognito_id_token` on success |
| 2 | getSession() is unchanged — returns null on expired tokens without side effects | VERIFIED | `getSession()` at line 104 of cognito.ts is unmodified; calls only `GetUserCommand`, no cookie mutation |
| 3 | Every API route returns JSON { error: string } on DB failure — never HTML | VERIFIED | All 9 handlers across 8 routes have try/catch returning `NextResponse.json({ error: ... }, { status: 500 })` |
| 4 | All DB queries in API routes are wrapped in try/catch | VERIFIED | jobs, history, dashboard/stats, worker-status, credentials DELETE, auth/logout POST, targets GET, targets POST, targets/[id] PUT, targets/[id] DELETE — all wrapped |
| 5 | getNextClassDate in scheduler uses America/New_York timezone, not server local getDay() | VERIFIED | Line 240: `toLocaleDateString('en-CA', { timeZone: 'America/New_York' })`; no `new Date().getDay()` pattern remains |
| 6 | getClassDate recurring branch in targets/route.ts uses America/New_York | VERIFIED | Line 167: same ET pattern; etDayOfWeek derived from ET date string, not server-local `getDay()` |
| 7 | NormalizedClass interface exists with all display fields non-null | VERIFIED | `NormalizedClass` interface at types.ts line 169; `class_name: string`, `instructor: string`, `duration_minutes: number`, `spots_remaining: number` — no nulls |
| 8 | Schedule API applies normalizeClass at all 5 response paths | VERIFIED | Paths 1, 2 use `normDb()`; paths 3, 4 use `norm()` (wraps `normalizeClass()`); path 5 uses `normDb()` |

**Score:** 8/8 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `web/src/lib/cognito.ts` | Exports `refreshSession()` with `REFRESH_TOKEN_AUTH` | VERIFIED | Line 123: `export async function refreshSession`, line 131: `AuthFlow: 'REFRESH_TOKEN_AUTH'` |
| `web/src/app/api/auth/refresh/route.ts` | POST handler, reads cookie, calls refreshSession, sets cookies | VERIFIED | File exists, exports `POST`, reads `cognito_refresh_token`, calls `refreshSession`, sets `cognito_access_token` + `cognito_id_token` |
| `web/src/app/api/jobs/route.ts` | Error-wrapped GET handler | VERIFIED | try/catch at line 9-21; `console.error('[jobs] GET error:', err)` |
| `web/src/app/api/history/route.ts` | Error-wrapped GET handler | VERIFIED | try/catch at line 13-31; `console.error('[history] GET error:', err)` |
| `web/src/app/api/dashboard/stats/route.ts` | Error-wrapped GET handler | VERIFIED | try/catch at line 11-35; `console.error('[dashboard/stats] GET error:', err)` |
| `web/src/app/api/worker-status/route.ts` | Error-wrapped GET handler | VERIFIED | try/catch at line 9-18; `console.error('[worker-status] GET error:', err)` |
| `web/src/app/api/credentials/route.ts` | Error-wrapped DELETE handler | VERIFIED | try/catch at line 69-79; `console.error('[credentials] DELETE error:', err)` |
| `web/src/app/api/auth/logout/route.ts` | Error-wrapped POST handler | VERIFIED | try/catch wraps entire body; `console.error('[auth/logout] POST error:', err)` |
| `worker/src/jobs/scheduler.ts` | Timezone-safe getNextClassDate and isInBookingWindow | VERIFIED | `getNextClassDate` uses `toLocaleDateString('en-CA', { timeZone: 'America/New_York' })` at line 239-240; `isInBookingWindow` same at line 285-286 |
| `web/src/app/api/targets/route.ts` | Timezone-safe getClassDate + error-wrapped GET/POST | VERIFIED | ET pattern in `getClassDate` recurring branch (lines 166-167); try/catch in GET (line 48) and POST (line 64) |
| `web/src/app/api/targets/[id]/route.ts` | Error-wrapped PUT and DELETE handlers | VERIFIED | PUT try/catch line 14-57; DELETE try/catch line 64-77; both have `[targets]` prefix logging |
| `packages/shared/src/types.ts` | NormalizedClass interface + normalizeClass function | VERIFIED | `NormalizedClass` interface at line 169; `normalizeClass()` function at line 186; both exported via `export * from './types'` in index.ts |
| `web/src/app/api/schedules/route.ts` | normalizeClass applied at all response paths | VERIFIED | 5 response paths: normDb (line 140), normDb (line 160), norm (line 186), norm (line 256), normDb (line 267) |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `web/src/app/api/auth/refresh/route.ts` | `web/src/lib/cognito.ts` | `import { refreshSession }` | WIRED | Line 3: `import { refreshSession } from '@/lib/cognito'`; called at line 20 |
| `web/src/app/api/auth/refresh/route.ts` | `cognito_refresh_token cookie` | `cookies().get` | WIRED | Lines 7-8: `cookieStore.get('cognito_refresh_token')?.value`; used as arg to `refreshSession` |
| `web/src/app/api/schedules/route.ts` | `packages/shared/src/types.ts` | `import normalizeClass, NormalizedClass` | WIRED | Lines 4-5: imports `normalizeClass` and `NormalizedClass`; used in `norm()` at line 118 |
| `worker/src/jobs/scheduler.ts` | `toLocaleDateString 'en-CA' America/New_York` | ET timezone formatting | WIRED | Lines 239-241 in `getNextClassDate`, lines 285-287 in `isInBookingWindow` |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| INFRA-01 | Plan 01 | User session auto-refreshes when Cognito access token expires | SATISFIED | `refreshSession()` in cognito.ts + `POST /api/auth/refresh` route; reads refresh token cookie, calls `REFRESH_TOKEN_AUTH`, sets new access/id token cookies |
| INFRA-02 | Plans 02 + 03 | All API routes return consistent error shapes with user-facing messages | SATISFIED | 9 handler functions across 8 route files all have try/catch returning `{ error: string }` JSON with appropriate HTTP status codes; route-name prefix logging in all catch blocks |
| INFRA-03 | Plan 03 | Worker timezone handling in getNextClassDate uses America/New_York | SATISFIED | `getNextClassDate` rewrites `new Date().getDay()` with `toLocaleDateString('en-CA', { timeZone: 'America/New_York' })`; `isInBookingWindow` uses same pattern; `targets/route.ts getClassDate` recurring branch and `schedules/route.ts nextOccurrence` also fixed |
| INFRA-04 | Plan 03 | Data normalization layer produces consistent NormalizedClass objects from all 3 platforms | SATISFIED | All 3 platform API clients (mt-api-client, xpo-api-client, arketa-api-client) return `ClassScheduleRow[]`; `normalizeClass()` maps any `ClassScheduleRow` to `NormalizedClass` with non-null strings; applied at all 5 response paths in schedules/route.ts |

All 4 phase requirements satisfied. No orphaned requirements — REQUIREMENTS.md traceability table maps INFRA-01 through INFRA-04 exclusively to Phase 1, and all are now complete.

---

### Anti-Patterns Found

No blockers. The `return null` patterns in cognito.ts and targets/route.ts are intentional — typed nullable returns from authentication and date-parsing functions, not stub implementations.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | — | — | No anti-patterns found in any phase-modified file |

---

### Human Verification Required

#### 1. Live Token Refresh End-to-End

**Test:** Log in, wait for the 1-hour Cognito access token to expire (or manually clear the `cognito_access_token` cookie while keeping `cognito_refresh_token` and `cognito_id_token`), then make a protected page request.
**Expected:** Client-side 401 interceptor (Phase 2, not yet implemented) calls `POST /api/auth/refresh`, which silently renews the session without a logout. The current `POST /api/auth/refresh` route itself is verified — the full silent-renewal user experience is blocked on Phase 2's interceptor.
**Why human:** Requires real Cognito credentials, an actually-expired access token, and a browser session. Cannot simulate live Cognito token exchange in static analysis. Note: the refresh route is wired and correct; Phase 2 adds the client-side 401 interceptor that calls it automatically.

#### 2. DB Failure Returns JSON (not HTML)

**Test:** Temporarily misconfigure `DATABASE_URL` and make a request to `/api/jobs`, `/api/history`, `/api/dashboard/stats`, or any other wrapped route.
**Expected:** Response is `Content-Type: application/json` with body `{ "error": "Internal server error" }` and status 500. No HTML error page in the response.
**Why human:** Requires inducing a real runtime DB failure. Static analysis confirms the try/catch is correctly placed and returns `NextResponse.json({ error: 'Internal server error' }, { status: 500 })`.

---

### Gaps Summary

No gaps. All automated checks passed. Phase goal is achieved:

- **Sessions stay alive:** `refreshSession()` + `POST /api/auth/refresh` route are wired and correct. The 30-day refresh token is used. `getSession()` is unchanged.
- **API errors are parseable:** 9 handler functions across 8 route files all return `{ error: string }` JSON on every error path. No code path produces an unhandled throw that would yield an HTML 500 page.
- **Timestamps render on the correct day:** `getNextClassDate`, `isInBookingWindow` (scheduler), `getClassDate` (targets route), and `nextOccurrence` (schedules route) all use explicit `America/New_York` locale formatting instead of server-local `getDay()`. No raw `new Date().getDay()` pattern remains in any of these functions.
- **Uniform data shapes from all 3 platforms:** All 3 API clients (MT, Xponential, Arketa) return `ClassScheduleRow[]`. `NormalizedClass` interface guarantees non-null display strings. `normalizeClass()` is applied at all 5 response paths in the schedules API. TypeScript compiles cleanly for both web and worker packages.

Two items are flagged for human verification but do not block the phase — the refresh route is mechanically correct, and the JSON error boundary is structurally correct. These items require live runtime conditions to confirm end-to-end behavior.

---

_Verified: 2026-02-26_
_Verifier: Claude (gsd-verifier)_
