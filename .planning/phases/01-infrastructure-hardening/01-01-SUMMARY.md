---
phase: 01-infrastructure-hardening
plan: 01
subsystem: auth
tags: [cognito, refresh-token, session, api-route]
dependency_graph:
  requires: []
  provides: [refreshSession, POST /api/auth/refresh]
  affects: [web/src/lib/cognito.ts, web/src/app/api/auth/refresh/route.ts]
tech_stack:
  added: []
  patterns: [REFRESH_TOKEN_AUTH, httpOnly cookie rotation]
key_files:
  created:
    - web/src/app/api/auth/refresh/route.ts
  modified:
    - web/src/lib/cognito.ts
decisions:
  - "refreshSession() does not return or update the refresh token cookie — Cognito REFRESH_TOKEN_AUTH only returns new access and ID tokens"
  - "getSession() remains unchanged as a read-only validator; cookie mutation lives only in the refresh route"
  - "Email decoded from ID token JWT payload locally — avoids extra network call"
metrics:
  duration: "< 1 minute"
  completed: "2026-02-26"
  tasks_completed: 1
  files_changed: 2
---

# Phase 01 Plan 01: Cognito Token Refresh Flow Summary

## One-liner

Wired Cognito REFRESH_TOKEN_AUTH into `refreshSession()` + `POST /api/auth/refresh` so 30-day refresh tokens silently renew expired 1-hour access tokens.

## What Was Built

### Task 1: Add refreshSession() to cognito.ts and create POST /api/auth/refresh route

**Commit:** `410c7b4`
**Files:** `web/src/lib/cognito.ts`, `web/src/app/api/auth/refresh/route.ts`

Added `refreshSession(refreshToken: string, email: string)` to `cognito.ts`. This function calls `InitiateAuthCommand` with `AuthFlow: 'REFRESH_TOKEN_AUTH'`, includes `SECRET_HASH` when `COGNITO_CLIENT_SECRET` is set, and returns the new `accessToken` + `idToken` pair — or `null` on failure (expired token, network error, etc.).

Created `POST /api/auth/refresh` route that:
1. Reads `cognito_refresh_token` and `cognito_id_token` from httpOnly cookies
2. Decodes the user's email from the ID token JWT payload (no network call)
3. Calls `refreshSession()` with the refresh token and email
4. On success, sets new `cognito_access_token` and `cognito_id_token` cookies (30-day maxAge)
5. Does NOT overwrite `cognito_refresh_token` — `REFRESH_TOKEN_AUTH` does not return a new one

## Decisions Made

| Decision | Rationale |
|---|---|
| `getSession()` unchanged | It runs in a read-only server context; cookie mutation belongs in the refresh route called by the client-side 401 interceptor (Phase 2) |
| Email decoded locally from ID token | Avoids an extra Cognito `GetUser` call — the JWT payload already contains `email` |
| Refresh token cookie not updated | `REFRESH_TOKEN_AUTH` only returns access + ID tokens; refresh token stays valid for 30 days per Cognito behavior |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

Verified:
- `web/src/lib/cognito.ts` — exports `refreshSession`, contains `REFRESH_TOKEN_AUTH`
- `web/src/app/api/auth/refresh/route.ts` — exists, exports `POST`, reads `cognito_refresh_token`, calls `refreshSession`, sets `cognito_access_token` and `cognito_id_token`
- `getSession()` — unchanged at line 104
- TypeScript compiles without errors (`npx tsc --noEmit -p web/tsconfig.json`)
- Commit `410c7b4` verified in git log

## Self-Check: PASSED
