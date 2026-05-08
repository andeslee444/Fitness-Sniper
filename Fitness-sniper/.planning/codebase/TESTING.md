# Testing Patterns

**Analysis Date:** 2026-02-26

## Test Framework

**Runner:** None configured. No Jest, Vitest, Mocha, or any other test runner is installed or configured.

**Assertion Library:** None.

**Test Files:** Zero automated test files exist in the active codebase (only `archive/src/test-barrys.ts` — a legacy manual script, not an automated test).

**Run Commands:**
```bash
# No test commands exist
# npm test → error: missing script
```

## No Automated Tests

This codebase has **no automated test suite**. The `CLAUDE.md` explicitly states: "No test framework is configured. There are no automated tests."

Do not assume tests exist or attempt to run them. When adding new features, there is no test coverage to maintain or break.

## Manual Testing

The only testing mechanism is a manual dry-run script:

**`worker/src/test-booking.ts`** — Runs a live booking attempt against real APIs.
```bash
npx tsx worker/src/test-booking.ts
```
This requires real credentials in `worker/.env`. It is a smoke test against production, not an isolated unit test.

**Discovery scripts** serve as exploratory tools, not tests:
- `worker/src/discover-arketa.ts` — Intercepts Arketa API calls via browser
- `worker/src/capture-client-ids.ts` — Captures MT OAuth client_ids

## Linting as Quality Gate

The only automated quality enforcement is ESLint on the web package:

```bash
npm run lint          # runs eslint on web/ only
```

Config: `web/eslint.config.mjs` — uses `eslint-config-next/core-web-vitals` and `eslint-config-next/typescript`.

The worker package has **no linter configured** — TypeScript strict mode (`strict: true` in `worker/tsconfig.json`) is the only static check.

TypeScript strict mode catches:
- Implicit `any` types
- Null/undefined unsafe access
- Missing return types (via inference)

## Integration Test Patterns (If Tests Were Added)

If adding tests to this codebase, follow these patterns based on what the code does:

**What to test (high-value targets):**
- `packages/shared/src/types.ts` — `parseTime()` and `formatTime12()` are pure functions, easy to unit test
- `worker/src/jobs/scheduler.ts` — `getNextClassDate()`, `parseTargetDate()`, `isInBookingWindow()` are exported pure functions
- `worker/src/crypto/credentials.ts` — `encrypt()` / `decrypt()` round-trip
- API route validation — Zod schemas in `web/src/app/api/targets/route.ts`

**What NOT to test without mocking:**
- Adapter classes (`MarianaTekAdapter`, `XponentialAdapter`, `ArketaAdapter`) — require live API credentials
- `JobPoller`, `JobScheduler`, `SlotWatcher` — require a live PostgreSQL connection
- `sendBookingEmail` — requires Resend API key

**Recommended framework if tests are added:**
- Vitest — compatible with TypeScript ESM modules, no additional config for Node
- Install: `npm install -D vitest` in the relevant workspace
- Config would go in `worker/vitest.config.ts` or `web/vitest.config.ts`

## Code Structure Notes for Testability

**Easily testable (pure functions):**
- `packages/shared/src/types.ts` exports `parseTime(time: string)` and `formatTime12(input: Date | string)` — no side effects
- `worker/src/jobs/scheduler.ts` exports `getNextClassDate(dayOfWeek, time)`, `parseTargetDate(dateStr, time)`, `isInBookingWindow(classDate, windowDays)` — no side effects

**Hard to test without dependency injection:**
- `JobPoller`, `JobScheduler`, `JobProcessor`, `SlotWatcher` all take direct DB connections via `query()` import — would require mocking `../db.js`
- `MarianaTekAdapter.init()` calls `fetch()` and optionally launches Playwright browser — requires full mock or network interception
- `encrypt()` / `decrypt()` require `ENCRYPTION_KEY` env var set to a 64-char hex string

**Adapter interface contract (for mocking):**
All adapters implement an implicit interface:
```ts
class SomeAdapter {
  async init(): Promise<void>
  async close(): Promise<void>
  async bookClass(
    location: string,
    time: string,
    preferredSpots?: string[],
    classDate?: Date,
  ): Promise<BookingResult>
}
```
`BookingResult` is `{ success: boolean; message: string; spot?: string; screenshotPath?: string }`.

## Coverage

**Requirements:** None enforced (no test runner).

**Current coverage:** 0% — no tests exist.

**Highest risk areas without coverage:**
1. `worker/src/jobs/scheduler.ts` — date calculation logic for `getNextClassDate()` (timezone edge cases)
2. `worker/src/adapters/mariana-tek.ts` — `loginViaOAuthHTTP()` redirect chain parsing
3. `worker/src/jobs/slot-watcher.ts` — `isTargetMatch()` logic for null-time Arketa targets
4. `web/src/app/api/targets/route.ts` — Zod discriminated union validation edge cases

---

*Testing analysis: 2026-02-26*
