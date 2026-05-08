---
phase: "04-schedule-browser-and-click-to-snipe"
plan: "03"
subsystem: "credentials"
tags: ["credential-validation", "trust", "auth-check", "badges", "TRUST-04"]
dependency_graph:
  requires: []
  provides:
    - "POST /api/credentials/validate — live auth test for MT, Xponential, Arketa"
    - "CredentialForm validationStatus badge (Connected/Untested/Invalid/Checking)"
    - "Credentials page fires validation on mount for each saved credential"
  affects:
    - "web/src/components/credential-form.tsx"
    - "web/src/app/(dashboard)/credentials/page.tsx"
tech_stack:
  added: []
  patterns:
    - "Server component passes DB-fetched slugs to client component for validation"
    - "Sequential async validation to avoid rate limiting studio APIs"
    - "AbortController with 5s timeout returns untested (not invalid) on slow network"
    - "AES-256-GCM decrypt in API route mirrors worker/src/crypto/credentials.ts pattern"
key_files:
  created:
    - "web/src/app/api/credentials/validate/route.ts"
    - "web/src/app/(dashboard)/credentials/credentials-page-client.tsx"
  modified:
    - "web/src/components/credential-form.tsx"
    - "web/src/app/(dashboard)/credentials/page.tsx"
decisions:
  - "Status computed on demand (not stored in DB) — avoids stale data and DB migration"
  - "Sequential validation loop (not Promise.all) — prevents rate-limit errors from studio APIs"
  - "Timeout returns 'untested' not 'invalid' — network failure != bad credentials"
  - "Server component fetches slugs from DB, client component renders UI and fires validation"
metrics:
  duration_seconds: 116
  completed_date: "2026-02-28"
  tasks_completed: 2
  files_created: 2
  files_modified: 2
---

# Phase 04 Plan 03: Credential Validation with Status Badges Summary

**One-liner:** Live auth validation for all three studio platforms (MT, Xponential, Arketa) with Connected/Untested/Invalid/Checking badges on the credentials page.

## What Was Built

Added credential validation that tests whether stored credentials actually work by making lightweight auth calls to each studio's platform API, surfacing results as colored badges.

**TRUST-04 requirement satisfied:** Users can now see at a glance if their stored credentials will work before a booking window opens.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Create POST /api/credentials/validate endpoint | a4e8272 | `web/src/app/api/credentials/validate/route.ts` (new) |
| 2 | Add validation status badge and wire credentials page | 827c349 | `credential-form.tsx`, `credentials/page.tsx`, `credentials-page-client.tsx` (new) |

## Implementation Details

### Validate Endpoint (`/api/credentials/validate`)

- Accepts `{ studioSlug }` via POST, returns `{ status: 'connected' | 'untested' | 'invalid' }`
- Decrypts stored credentials using AES-256-GCM (same pattern as worker `crypto/credentials.ts`)
- Platform-specific auth tests:
  - **Mariana Tek:** `POST /{tenant}.marianatek.com/api/customer/v1/auth/access-tokens`
  - **Xponential:** `POST /{membersDomain}/api/xpass/sessions`
  - **Arketa:** Firebase `POST /v1/accounts:signInWithPassword` with `idToken` check
- 5s AbortController timeout returns `untested` (not `invalid`) on slow networks
- No DB storage — status computed fresh on each page load

### Credential Badge (`CredentialForm`)

- New optional `validationStatus` prop: `'connected' | 'untested' | 'invalid' | 'checking'`
- Badge renders inline with studio name in the compact saved card:
  - `checking` → gray `Checking...`
  - `connected` → green `Connected`
  - `untested` → amber `Untested`
  - `invalid` → red `Invalid`
- Unsaved credentials show no badge (no prop passed)

### Credentials Page Refactor

- `page.tsx` — Now a lean server component: fetches `studio_slug` list from DB, passes `savedSlugs[]` to client component
- `credentials-page-client.tsx` — New client component:
  - Sets all saved credentials to `checking` on mount
  - Runs sequential `fetch('/api/credentials/validate')` loop (not parallel)
  - Updates each credential's status as responses come in
  - Cleanup function prevents state updates after unmount

## Verification Results

- TypeScript: Zero errors (`npx tsc --noEmit`)
- Next.js build: Succeeds — `/api/credentials/validate` and `/credentials` both appear as dynamic routes
- All key patterns present: 3 platform test functions, 3 status values, 5s timeout, createDecipheriv

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

Files confirmed present:
- `/Users/andeslee/Documents/Cursor-Projects/Fitness-sniper/web/src/app/api/credentials/validate/route.ts` — FOUND
- `/Users/andeslee/Documents/Cursor-Projects/Fitness-sniper/web/src/app/(dashboard)/credentials/credentials-page-client.tsx` — FOUND

Commits confirmed:
- `a4e8272` — feat(04-03): add POST /api/credentials/validate endpoint — FOUND
- `827c349` — feat(04-03): add validation status badge to credentials page — FOUND
