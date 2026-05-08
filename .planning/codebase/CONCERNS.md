# Codebase Concerns

**Analysis Date:** 2026-02-26

---

## Tech Debt

**Duplicate encryption logic:**
- Issue: AES-256-GCM encrypt/decrypt is implemented twice — once in `worker/src/crypto/credentials.ts` and again inline in `web/src/app/api/credentials/route.ts`. Both must stay in sync (same algorithm, IV length, auth tag length).
- Files: `worker/src/crypto/credentials.ts`, `web/src/app/api/credentials/route.ts`
- Impact: A divergence between the two implementations would cause the worker to fail to decrypt credentials saved by the web.
- Fix approach: Move the shared encrypt/decrypt functions to `packages/shared/src/crypto.ts` and import from both web and worker.

**Duplicate `InsufficientCreditsError` class:**
- Issue: The same error class with identical logic is defined in both `worker/src/adapters/mariana-tek.ts` and `worker/src/adapters/xponential.ts`.
- Files: `worker/src/adapters/mariana-tek.ts:63-76`, `worker/src/adapters/xponential.ts:63-75`
- Impact: Minor — any fix to the error class must be made in two places.
- Fix approach: Extract to a shared adapter error module at `worker/src/adapters/errors.ts`.

**`getNextClassDate` is not timezone-aware:**
- Issue: `getNextClassDate` in `worker/src/jobs/scheduler.ts` uses `new Date()` (server local time) and `now.getDay()` to compute the next day of week. The worker comment says it relies on the system timezone being `America/New_York`. If the worker ever runs outside NYC timezone (e.g., cloud deployment), this will produce wrong class dates.
- Files: `worker/src/jobs/scheduler.ts:233-250`
- Impact: Incorrect job scheduling — jobs could be created for the wrong date.
- Fix approach: Use `toLocaleDateString('en-CA', { timeZone: 'America/New_York' })` consistently like `slot-watcher.ts` does.

**Batch DB upserts are row-by-row:**
- Issue: `upsertClasses` in both `worker/src/jobs/schedule-scraper.ts:294-329` and `worker/src/jobs/slot-watcher.ts:387-423` iterate through each class and issue individual `INSERT ... ON CONFLICT` statements. For 8-day scrapes across multiple studios, this can be hundreds of individual queries.
- Files: `worker/src/jobs/schedule-scraper.ts:294`, `worker/src/jobs/slot-watcher.ts:387`
- Impact: Slow scrapes; potential DB connection pressure during large scrape runs.
- Fix approach: Use `UNNEST` bulk inserts or batched multi-row INSERT for class schedule upserts.

**`SPOT_PREFERENCES` are hardcoded Barry's spot IDs:**
- Issue: `packages/shared/src/types.ts:197-203` defines spot preference arrays (`front`, `middle`, `back`) with hardcoded spot names like `F-1`, `T-1`. These are specific to Barry's layout and do not apply to other studios.
- Files: `packages/shared/src/types.ts:197-203`
- Impact: Spot preference for non-Barry's studios is silently ignored or sends wrong spot IDs.
- Fix approach: Make spot preferences per-studio in `StudioConfig` or document the Barry's-only scope clearly.

---

## Known Bugs

**Attempt count double-increment risk:**
- Symptoms: `claim_next_job()` increments `attempts` by 1 on every claim. The stale job recovery in `scheduler.ts:193` also increments `attempts` when resetting stuck jobs. If a job is claimed but the worker crashes before updating status to `running`, the stale recovery will increment attempts again on the next reset — meaning `attempts` can count higher than actual booking attempts made.
- Files: `supabase/migrations/001_rds_schema.sql:204`, `worker/src/jobs/scheduler.ts:190-205`, `worker/src/jobs/processor.ts:178`
- Trigger: Worker crashes (OOM, SIGKILL) between claim and running status update.
- Workaround: `max_attempts` defaults to 3, so at worst a job gets fewer retries than expected.

**Arketa booking searches a week ahead from target date:**
- Symptoms: When `ArketaAdapter.bookClass` is called, it searches for a slot from `classDate` to `classDate + 7 days`. If the slot is exactly on `classDate`, it finds it. But if the `class_datetime` stored in the job is slightly off (due to timezone math), the search window may miss the slot.
- Files: `worker/src/adapters/arketa.ts:142-154`
- Trigger: Timezone boundary edge cases or if Arketa slot times drift.
- Workaround: The 7-day window provides slack.

**Middleware does not protect `/schedule` page:**
- Symptoms: The `/schedule` route exists at `web/src/app/(dashboard)/schedule/` and requires auth (the API it calls uses `getSession()`), but the middleware `PROTECTED_PATHS` array does not include `/schedule`. The page itself is inside the `(dashboard)` group.
- Files: `web/src/middleware.ts:3`
- Trigger: A logged-out user navigating directly to `/schedule` will see the page (JS may render), and API calls will return 401 but the page won't redirect to login.
- Workaround: The API routes behind the page all check `getSession()` and return 401.

**In-memory rate limiter resets on server restart:**
- Symptoms: The rate limiters for `/api/auth/login` and `/api/auth/signup` use `Map` objects in module scope. On Vercel, serverless function restarts clear all in-memory state, effectively resetting rate limit counters.
- Files: `web/src/app/api/auth/login/route.ts:5-18`, `web/src/app/api/auth/signup/route.ts:6-19`
- Trigger: Any cold start or serverless instance recycling.
- Workaround: Cognito's own `TooManyRequestsException` provides a secondary limit.

---

## Security Considerations

**Hardcoded dummy phone number in Cognito signup:**
- Risk: Every user is registered with `phone_number: '+10000000000'` in Cognito. If SMS MFA or phone verification is ever enabled, all users will be linked to the same placeholder number.
- Files: `web/src/lib/cognito.ts:42`
- Current mitigation: Phone verification is not enabled.
- Recommendations: Remove the `phone_number` attribute entirely, or require real phone numbers at signup.

**Middleware auth check is cookie-presence only:**
- Risk: The middleware at `web/src/middleware.ts` only checks that `cognito_access_token` cookie exists — it does not validate the token. An expired or forged cookie will pass the middleware check.
- Files: `web/src/middleware.ts:12-14`
- Current mitigation: All API routes call `getSession()` which validates the token via `GetUserCommand` against Cognito. Server Components and pages that call API routes are protected.
- Recommendations: Acceptable for now since the real auth check is in the API routes. But any Server Component that directly queries the DB (without going through an API route) would be vulnerable.

**SSL certificate verification disabled for PostgreSQL:**
- Risk: `{ rejectUnauthorized: false }` in the pg Pool config means the TLS certificate of the database server is not verified. A man-in-the-middle could intercept database traffic.
- Files: `web/src/lib/db.ts:17`, `worker/src/db.ts:23`
- Current mitigation: Traffic is over a private VPC/subnet in practice (Mac Mini → RDS).
- Recommendations: Use proper CA certificate verification or provide the RDS CA cert bundle.

**Firebase API key is hardcoded in source:**
- Risk: The Firebase Web API key `AIzaSyCNSSHH1yTQ492d42qWOG_V_m2uQGdQF74` is committed to source. This key can be used by anyone to call Firebase Identity Toolkit endpoints for Arketa's project.
- Files: `worker/src/adapters/arketa.ts:22`
- Current mitigation: Firebase Web API keys are designed to be public client-side keys; access is controlled by Firebase Security Rules and the Arketa app's configuration.
- Recommendations: Document why this is safe, or move to an environment variable to be consistent with other secrets.

**Cognito `refreshToken` stored in cookie but never used:**
- Risk: The refresh token is stored as a 30-day httpOnly cookie, but there is no token refresh flow implemented. When the Cognito access token expires (default 1 hour), `getSession()` returns `null` and the user must log in again, even though their refresh token is still valid.
- Files: `web/src/lib/cognito.ts:139`, `web/src/app/api/auth/login/route.ts`
- Impact: Sessions effectively expire after 1 hour despite 30-day cookie maxAge, causing unexpected logouts.
- Recommendations: Implement a token refresh using `REFRESH_TOKEN_AUTH` flow, either in middleware or as a client-side interceptor.

---

## Performance Bottlenecks

**`getSession()` calls Cognito on every API request:**
- Problem: Every authenticated API route calls `getSession()` which issues a live `GetUserCommand` to AWS Cognito. This adds ~50-200ms of external network latency to every API call.
- Files: `web/src/lib/cognito.ts:104-121`, every API route handler
- Cause: No session caching or JWT local verification.
- Improvement path: Verify the Cognito JWT locally using the user pool's JWKS endpoint. Cache JWKS in memory and only call `GetUserCommand` on token refresh.

**Schedule scraper makes one DB upsert per class row:**
- Problem: `scrapeAll()` can process hundreds of class rows across 8 days × multiple studio/location pairs, issuing an individual `INSERT ... ON CONFLICT` per row.
- Files: `worker/src/jobs/schedule-scraper.ts:294-329`
- Cause: Row-by-row upsert pattern.
- Improvement path: Use PostgreSQL `UNNEST` for batched inserts: `INSERT INTO class_schedules SELECT * FROM UNNEST($1::...) ON CONFLICT DO UPDATE`.

**Schedule API in-memory cache is per-serverless-instance:**
- Problem: The 5-minute `apiCache` Map in `web/src/app/api/schedules/route.ts:20` is instance-local. On Vercel with multiple serverless instances, each instance has its own cache and makes redundant live API calls.
- Files: `web/src/app/api/schedules/route.ts:20-21`
- Cause: No shared cache layer (Redis, etc.).
- Improvement path: The existing DB-first path (scraped data) mitigates this for most requests; the in-memory cache only helps within a single instance's lifetime.

---

## Fragile Areas

**Mariana Tek HTML scraping selectors:**
- Files: `worker/src/scrapers/mt-browser-scraper.ts`
- Why fragile: The browser scraper parses DOM class cards by CSS selectors. MT studios update their frontend without notice. The CLAUDE.md explicitly notes: "When selectors break, check `archive/` for historical patterns."
- Safe modification: Always test against a live MT iframe before deploying selector changes. Keep archive patterns as reference.
- Test coverage: None — no automated tests exist.

**Arketa booking uses raw widget data as checkout body:**
- Files: `worker/src/adapters/arketa.ts:195-213`
- Why fragile: The checkout API receives `{ ...rawMatch, bookingType, collection, bookingWidget }` — the entire raw Arketa class object is passed as the POST body. Any schema change in Arketa's widget API will silently break the booking payload without an obvious error.
- Safe modification: Log `bookingData` response in detail; monitor for non-success responses.
- Test coverage: None.

**MT OAuth HTTP flow relies on CSRF token regex:**
- Files: `worker/src/adapters/mariana-tek.ts:163-168`
- Why fragile: The CSRF token is extracted from raw HTML via `name="csrfmiddlewaretoken" value="([^"]+)"`. Any Django template change that modifies attribute order or quoting will break authentication silently (falls back to browser auth).
- Safe modification: The browser fallback at `loginViaBrowser()` provides resilience.
- Test coverage: None.

**Stale job recovery uses `updated_at` for `running` status:**
- Files: `worker/src/jobs/scheduler.ts:188-206`
- Why fragile: Stale `running` jobs are detected by `updated_at < NOW() - INTERVAL '60 minutes'`. If a long-running booking job (e.g., browser-based MT login) takes more than 60 minutes, the stale recovery will reset it to `pending` while it's still actively running, causing a duplicate booking attempt.
- Safe modification: The 60-minute threshold is generous for current booking flows (all complete in <60 seconds). Only risky if the booking pipeline is significantly extended.
- Test coverage: None.

**Arketa `knownSlotKeys` set lives in worker memory:**
- Files: `worker/src/jobs/slot-watcher.ts:51-52`
- Why fragile: The `knownSlotKeys` Set is in-process memory. If the worker restarts, `seedKnownSlots()` re-seeds from the current API state, preventing a flood of spurious new-slot detections. However, if the worker crashes between a slot appearing and being seeded, and restarts before the next poll, that slot will be detected as "new" and trigger a booking job even if it was booked moments ago.
- Safe modification: The downstream dedup check in `matchAndCreateJobs` (checking for existing jobs with `status IN ('pending', 'claimed', 'running', 'success')`) prevents double-booking in most cases.
- Test coverage: None.

---

## Scaling Limits

**Single Mac Mini worker:**
- Current capacity: 1 worker process, concurrency limit of 2 parallel jobs (configurable via `CONCURRENCY` env var).
- Limit: All booking automation depends on a single physical machine. No redundancy.
- Scaling path: The job queue design (PostgreSQL `FOR UPDATE SKIP LOCKED`) supports multiple workers. A second Mac Mini or a cloud VM can run a second worker process pointing at the same DB.

**PostgreSQL connection pool capped at 10:**
- Current capacity: `max: 10` connections in both web (`web/src/lib/db.ts:15`) and worker (`worker/src/db.ts:23`).
- Limit: Vercel serverless can spin up many concurrent instances; each has its own pool of up to 10 connections. With high traffic, this could exhaust RDS connection limits.
- Scaling path: Use PgBouncer or `@neondatabase/serverless` for connection pooling in the web layer.

---

## Dependencies at Risk

**No automated tests — fragile at every layer:**
- Risk: Zero test coverage across the entire codebase (confirmed: no test framework configured per CLAUDE.md).
- Impact: Any change to an adapter, scheduler, or database query can silently break booking. Refactors are high-risk.
- Migration plan: At minimum, add unit tests for `parseTime`, `getNextClassDate`, `parseTargetDate`, and the `isTargetMatch` logic in slot-watcher.

**`playwright-extra` with stealth plugin:**
- Risk: The stealth plugin (`puppeteer-extra-plugin-stealth`) and `playwright-extra` are community packages that may not keep pace with Playwright updates or anti-bot detection advances.
- Impact: Browser-based auth fallback and schedule scraping may fail if studios improve bot detection.
- Migration plan: Keep `playwright` version pinned at 1.50.0 and test upgrades carefully.

---

## Missing Critical Features

**No token refresh for Cognito sessions:**
- Problem: Cognito access tokens expire after 1 hour. There is no refresh flow. Users are silently logged out after 1 hour of inactivity despite the 30-day cookie.
- Blocks: Good user experience for long dashboard sessions.

**No alerting when worker goes offline:**
- Problem: `worker_heartbeats` table tracks worker status, and the dashboard shows it, but there is no automated alert (email, SMS, webhook) when the worker stops sending heartbeats.
- Blocks: Operator awareness — a dead worker means all bookings silently fail.

**No retry backoff between booking attempts:**
- Problem: Failed jobs reset to `pending` immediately, allowing the poller to re-claim them without delay. If a class is full and won't open again for an hour, the job will attempt 3 times in rapid succession and exhaust retries within minutes.
- Blocks: Effective retry behavior for timing-sensitive booking failures.

---

## Test Coverage Gaps

**Booking pipeline — zero coverage:**
- What's not tested: The entire path from `JobPoller` claiming a job → `JobProcessor` decrypting credentials → adapter authenticating → `bookClass` succeeding.
- Files: `worker/src/jobs/processor.ts`, `worker/src/adapters/mariana-tek.ts`, `worker/src/adapters/xponential.ts`, `worker/src/adapters/arketa.ts`
- Risk: Breaking changes in any adapter go undetected until a user's real booking fails.
- Priority: High

**Scheduler date logic — zero coverage:**
- What's not tested: `getNextClassDate`, `parseTargetDate`, `isInBookingWindow`. These have timezone-sensitive logic.
- Files: `worker/src/jobs/scheduler.ts:233-272`
- Risk: Daylight saving time transitions (March, November) could shift booking times by 1 hour undetected.
- Priority: High

**Slot watcher matching logic — zero coverage:**
- What's not tested: `isTargetMatch` in `slot-watcher.ts` handles `time = null` (any-slot) targets, recurring day-of-week matching, and one-time date matching.
- Files: `worker/src/jobs/slot-watcher.ts:350-382`
- Risk: Incorrect target-to-slot matching silently misses bookings or creates spurious jobs.
- Priority: High

**API route auth — zero coverage:**
- What's not tested: Auth middleware behavior, `getSession()` returning null, API routes rejecting unauthorized requests.
- Files: `web/src/app/api/`, `web/src/middleware.ts`
- Risk: Auth regression could expose user data.
- Priority: Medium

---

*Concerns audit: 2026-02-26*
