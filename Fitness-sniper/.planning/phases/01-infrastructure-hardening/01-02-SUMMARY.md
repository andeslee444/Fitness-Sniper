---
phase: 01-infrastructure-hardening
plan: 02
subsystem: web/api
tags: [error-handling, try-catch, api-routes, json-responses]
dependency_graph:
  requires: []
  provides: [consistent-api-error-responses]
  affects: [web/src/app/api/jobs/route.ts, web/src/app/api/history/route.ts, web/src/app/api/dashboard/stats/route.ts, web/src/app/api/worker-status/route.ts, web/src/app/api/credentials/route.ts, web/src/app/api/auth/logout/route.ts]
tech_stack:
  added: []
  patterns: [try-catch-wrapper, json-error-shape, route-name-prefix-logging]
key_files:
  created: []
  modified:
    - web/src/app/api/jobs/route.ts
    - web/src/app/api/history/route.ts
    - web/src/app/api/dashboard/stats/route.ts
    - web/src/app/api/worker-status/route.ts
    - web/src/app/api/credentials/route.ts
    - web/src/app/api/auth/logout/route.ts
decisions:
  - Session check stays outside try/catch — getSession returns null on auth failure (no throw risk), so 401 responses remain unaffected
  - Existing successful response shapes preserved exactly — only error paths changed
metrics:
  duration: 2 minutes
  completed: 2026-02-26
  tasks_completed: 2
  tasks_total: 2
  files_modified: 6
---

# Phase 1 Plan 02: API Route Error Wrapping Summary

**One-liner:** Wrapped 7 handler functions across 6 API route files in try/catch blocks ensuring all DB query failures return `{ error: string }` JSON instead of HTML 500 pages.

## What Was Built

Every API route handler in scope now returns well-formed JSON on every code path — including DB failures. Previously, three routes (`jobs`, `history`, `dashboard/stats`) had zero error handling, and two more (`credentials` DELETE, `auth/logout`) had unprotected handlers. A DB connection error or query failure in any of these would cause Next.js to emit an HTML error page, resulting in `SyntaxError: Unexpected token '<'` crashes in client-side `res.json()` calls.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Wrap unprotected routes in try/catch | d846540 | jobs/route.ts, history/route.ts, dashboard/stats/route.ts, worker-status/route.ts |
| 2 | Add try/catch to partially-covered routes | f0a3836 | credentials/route.ts, auth/logout/route.ts |

## Pattern Applied

Session check remains **outside** try/catch in all routes — `getSession()` returns `null` on auth failure without throwing, so the 401 path is safe:

```typescript
export async function GET() {
  const user = await getSession();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  try {
    // DB queries and business logic
    return NextResponse.json(/* existing response */);
  } catch (err) {
    console.error('[route-name] GET error:', err);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
```

## Routes Modified

| Route | Handler | Was Wrapped | Now Wrapped |
|-------|---------|-------------|-------------|
| `api/jobs` | GET | No | Yes |
| `api/history` | GET | No | Yes |
| `api/dashboard/stats` | GET | No | Yes |
| `api/worker-status` | GET | No | Yes |
| `api/credentials` | POST | Yes (unchanged) | Yes |
| `api/credentials` | DELETE | No | Yes |
| `api/auth/logout` | POST | No | Yes |

**Note:** `targets/route.ts` and `targets/[id]/route.ts` error wrapping is handled in Plan 03 (avoids parallel file conflicts with timezone fixes).

## Decisions Made

1. **Session check outside try/catch** — `getSession()` does not throw on auth failure; it returns `null`. Moving it inside try/catch would be incorrect (the 401 path is not an error condition).
2. **Preserve existing response shapes** — No modifications to successful return values. Only error paths changed.
3. **`console.error` with bracketed prefix** — Each catch block uses `[route-name]` prefix for log filtering in production.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

Files exist:
- web/src/app/api/jobs/route.ts: FOUND
- web/src/app/api/history/route.ts: FOUND
- web/src/app/api/dashboard/stats/route.ts: FOUND
- web/src/app/api/worker-status/route.ts: FOUND
- web/src/app/api/credentials/route.ts: FOUND
- web/src/app/api/auth/logout/route.ts: FOUND

Commits exist:
- d846540: FOUND (fix(01-02): wrap unprotected API routes in try/catch)
- f0a3836: FOUND (fix(01-02): add try/catch to partially-covered route handlers)

TypeScript: Compiles cleanly (zero errors).
