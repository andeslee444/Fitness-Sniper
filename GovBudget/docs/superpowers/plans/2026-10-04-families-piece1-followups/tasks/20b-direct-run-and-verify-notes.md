<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; the approved design is ../../../specs/2026-10-04-families-piece1-followups-design.md. -->

### Task 20b: site scripts' direct-run guards compare real paths; `npm run verify` shows every note on request (#201)

Second part of Task 20 (after 20a, before 20c).

**Spec:** design §6.6 (#201: "Direct-run guard. Use `fs.realpathSync` in `f15-page-snapshot.mjs`,
`generate-feeds.mjs:203`, `run-mobile-leg.mjs:104`, `serve-static.mjs:236`, `gates/basis.mjs:3385`"; "`verify.mjs`
prints '+N more notes', and `VERIFY_NOTES=all` prints them all"); ROADMAP #201 (Task 4: run through a symlinked path
the snapshot tool "exits 0 without checking"; Task 22: "verify.mjs prints only three notes per gate, so gate 21 leg p's
note is invisible"); §7 W4.

**Files:**
- Create: `site/scripts/direct-run.mjs`, `site/scripts/gate-report.mjs`
- Modify: `site/scripts/f15-page-snapshot.mjs` (imports :30-33, guard :135), `site/scripts/generate-feeds.mjs` (:35,
  :203), `site/scripts/run-mobile-leg.mjs` (:24, :103-104), `site/scripts/serve-static.mjs` (:18, :236),
  `site/scripts/gates/basis.mjs` (:224, :3384-3387), `site/scripts/verify.mjs` (:55, :59-90)
- Create: `site/scripts/__tests__/direct-run.test.mjs`, `site/scripts/__tests__/gate-report.test.mjs`

Line numbers are hints measured at `532205c9` (anchor on the quoted text).

**Interfaces:**
Consumes: node's module resolution (the main module's `import.meta.url` is its real path; `process.argv[1]` is the
path as typed); `verify.mjs`' `printGate(n, name, result)` callers (unchanged) and `result = {pass, notes, errors}`.
Produces: `isDirectRun(moduleUrl: string, argv1 = process.argv[1]) -> boolean` (`site/scripts/direct-run.mjs`);
`gateReportLines(n, name, result, { allNotes = process.env.VERIFY_NOTES === "all" }) -> string[]` and
`WARNING_NOTE_RE` (`site/scripts/gate-report.mjs`). The summary line keeps its shape `gate N name: … → PASS|FAIL`
(nothing parses it; `verify-phase5b3` and `deploy.sh` read the exit code), gaining `; +K more note(s)` before the
arrow. Task 20c's `f15-page-snapshot.mjs` content keeps this task's import of `isDirectRun`.

- [ ] **Step 1: See the bug**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site || exit 1
LINKDIR=$(mktemp -d "${TMPDIR:-/var/tmp}/direct-run-demo.XXXXXX") || exit 1
ln -s "$PWD/scripts/f15-page-snapshot.mjs" "$LINKDIR/f15-page-snapshot.mjs"
node "$LINKDIR/f15-page-snapshot.mjs"; echo "via symlink: exit $?"
node scripts/f15-page-snapshot.mjs; echo "direct: exit $?"
rm -r "${LINKDIR:?}"
```
Expected (measured 2026-10-13): `via symlink: exit 0` — the tool printed nothing and checked nothing — then the usage
line and `direct: exit 2`.

- [ ] **Step 2: Write the failing tests**

Create `site/scripts/__tests__/direct-run.test.mjs`:

```js
/**
 * direct-run.mjs (ROADMAP #201). Five scripts compared process.argv[1] with
 * their own path as strings; node resolves the main module's symlinks for
 * import.meta.url but leaves argv[1] as typed, so a run through a symlinked
 * spelling skipped the body and exited 0 having checked nothing.
 */
import fs from "fs";
import os from "os";
import path from "path";
import { spawnSync } from "child_process";
import { fileURLToPath, pathToFileURL } from "url";
import { afterEach, describe, expect, it } from "vitest";
import { isDirectRun } from "../direct-run.mjs";

const SCRIPTS = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SNAPSHOT = path.join(SCRIPTS, "f15-page-snapshot.mjs");
const GUARDED = ["f15-page-snapshot.mjs", "generate-feeds.mjs", "run-mobile-leg.mjs", "serve-static.mjs", "gates/basis.mjs"];

const dirs = [];
function linkTo(target) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "direct-run-"));
  dirs.push(dir);
  const link = path.join(dir, path.basename(target));
  fs.symlinkSync(target, link);
  return link;
}
afterEach(() => { for (const dir of dirs.splice(0)) fs.rmSync(dir, { recursive: true, force: true }); });

describe("isDirectRun", () => {
  const url = pathToFileURL(SNAPSHOT).href;

  it("is true for the module's own path and for a symlink to it", () => {
    expect(isDirectRun(url, SNAPSHOT)).toBe(true);
    expect(isDirectRun(url, linkTo(SNAPSHOT))).toBe(true);
  });

  it("is false for another file, a missing path or no argv[1]", () => {
    expect(isDirectRun(url, path.join(SCRIPTS, "verify.mjs"))).toBe(false);
    expect(isDirectRun(url, path.join(SCRIPTS, "no-such-script.mjs"))).toBe(false);
    expect(isDirectRun(url, undefined)).toBe(false);
  });
});

describe("the five guarded scripts", () => {
  it("guard their body with isDirectRun, never a string comparison of argv[1]", () => {
    for (const rel of GUARDED) {
      const src = fs.readFileSync(path.join(SCRIPTS, rel), "utf8");
      expect(src, rel).toMatch(/if \(isDirectRun\(import\.meta\.url\)\)/);
      expect(src, rel).not.toMatch(/process\.argv\[1\]\s*(===|&&)|path\.resolve\(process\.argv\[1\]\)/);
    }
  });

  it("f15-page-snapshot run through a symlink checks its arguments instead of exiting 0", () => {
    const run = spawnSync(process.execPath, [linkTo(SNAPSHOT)], { encoding: "utf8" });
    expect(run.status).toBe(2);
    expect(run.stderr).toContain("usage: node scripts/f15-page-snapshot.mjs");
  });
});
```

Create `site/scripts/__tests__/gate-report.test.mjs`:

```js
/**
 * gate-report.mjs — the lines `npm run verify` prints for one gate (ROADMAP
 * #201). It showed the first three notes and the warnings; every other note
 * was invisible (gate 21 leg p's among them). Now the summary says how many
 * notes it left out, and VERIFY_NOTES=all prints them.
 */
import { describe, expect, it } from "vitest";
import { gateReportLines } from "../gate-report.mjs";

const notes = (n) => Array.from({ length: n }, (_, i) => `note ${i + 1}`);

describe("gateReportLines", () => {
  it("prints up to three notes on the summary line and nothing else", () => {
    expect(gateReportLines(9, "x", { pass: true, notes: notes(3), errors: [] })).toEqual([
      "gate 9 x: note 1; note 2; note 3 → PASS"]);
  });

  it("says how many notes it left out", () => {
    expect(gateReportLines(9, "x", { pass: true, notes: notes(5), errors: [] }, { allNotes: false })).toEqual([
      "gate 9 x: note 1; note 2; note 3; +2 more notes (VERIFY_NOTES=all prints them) → PASS"]);
    expect(gateReportLines(9, "x", { pass: true, notes: notes(4), errors: [] }, { allNotes: false })[0])
      .toContain("; +1 more note (VERIFY_NOTES=all prints them) → PASS");
  });

  it("still surfaces a warning wherever it sits", () => {
    const result = { pass: true, notes: [...notes(4), "page weight near-ceiling: /x/"], errors: [] };
    expect(gateReportLines(1, "build", result, { allNotes: false })).toEqual([
      "gate 1 build: note 1; note 2; note 3; +2 more notes (VERIFY_NOTES=all prints them) → PASS",
      "  ⚠ page weight near-ceiling: /x/"]);
  });

  it("prints every note with VERIFY_NOTES=all", () => {
    const result = { pass: false, notes: [...notes(4), "page weight near-ceiling: /x/"], errors: ["e1"] };
    expect(gateReportLines(21, "program-skeleton", result, { allNotes: true })).toEqual([
      "gate 21 program-skeleton: note 1; note 2; note 3; +2 more notes; ERRORS: e1 → FAIL",
      "  · note 4",
      "  ⚠ page weight near-ceiling: /x/",
      "  ✗ e1"]);
  });

  it("reads VERIFY_NOTES from the environment by default", () => {
    const before = process.env.VERIFY_NOTES;
    process.env.VERIFY_NOTES = "all";
    try {
      expect(gateReportLines(9, "x", { pass: true, notes: notes(4), errors: [] })).toEqual([
        "gate 9 x: note 1; note 2; note 3; +1 more note → PASS", "  · note 4"]);
    } finally {
      if (before === undefined) delete process.env.VERIFY_NOTES;
      else process.env.VERIFY_NOTES = before;
    }
  });
});
```

- [ ] **Step 3: Run them to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && npx vitest run scripts/__tests__/direct-run.test.mjs scripts/__tests__/gate-report.test.mjs`
Expected: both files fail to load — `Failed to resolve import "../direct-run.mjs"` and `Failed to resolve import
"../gate-report.mjs"` (`Tests  no tests`).

- [ ] **Step 4: Add the helper and the report module, and use them**

Create `site/scripts/direct-run.mjs`:

```js
/**
 * direct-run.mjs — "is this module the script node was asked to run?"
 *
 * ROADMAP #201: five scripts compared process.argv[1] with their own path as
 * strings. Node resolves the main module's symlinks (import.meta.url is the
 * real path) but leaves argv[1] as typed, so a script run through a
 * symlinked spelling — a worktree link, /tmp for /private/tmp — saw two
 * different strings, skipped its body and exited 0 having checked nothing.
 * Compare real paths instead.
 */
import fs from "fs";
import { fileURLToPath } from "url";

/** True when `argv1` (default process.argv[1]) is the file `moduleUrl` names. */
export function isDirectRun(moduleUrl, argv1 = process.argv[1]) {
  if (!argv1) return false;
  try {
    return fs.realpathSync(argv1) === fs.realpathSync(fileURLToPath(moduleUrl));
  } catch {
    return false;
  }
}
```

Create `site/scripts/gate-report.mjs`:

```js
/**
 * gate-report.mjs — the lines `npm run verify` (scripts/verify.mjs) prints for
 * one gate result {pass, notes, errors}.
 *
 * The summary line carries the first three notes. A WARNING note is printed
 * wherever it sits in the list: gate 1's page-weight warning lands well past
 * position 3, so the near-ceiling alarm added 2026-08-14 was generated on
 * every run and shown on none of them (/coverage/ reached NINE bytes of
 * headroom that way). ROADMAP #201: every other note was still invisible —
 * gate 21 leg p's among them — so the summary now says how many it left out,
 * and VERIFY_NOTES=all prints each one on its own line.
 */

/** Notes that must surface regardless of their position in the list. */
export const WARNING_NOTE_RE = /at or above|near-ceiling|\bWARN\b/i;
const SUMMARY_NOTES = 3;

export function gateReportLines(n, name, result, { allNotes = process.env.VERIFY_NOTES === "all" } = {}) {
  const status = result.pass ? "PASS" : "FAIL";
  const more = result.notes.length - SUMMARY_NOTES;
  const details =
    result.notes.slice(0, SUMMARY_NOTES).join("; ") +
    (more > 0 ? `; +${more} more note${more === 1 ? "" : "s"}${allNotes ? "" : " (VERIFY_NOTES=all prints them)"}` : "") +
    (result.errors.length > 0 ? `; ERRORS: ${result.errors.slice(0, 5).join(" | ")}` : "");
  const lines = [`gate ${n} ${name}: ${details} → ${status}`];
  for (const note of result.notes.slice(SUMMARY_NOTES)) {
    if (WARNING_NOTE_RE.test(note)) lines.push(`  ⚠ ${note}`);
    else if (allNotes) lines.push(`  · ${note}`);
  }
  for (const e of result.errors) lines.push(`  ✗ ${e}`);
  return lines;
}
```

In `site/scripts/verify.mjs` (:55), replace:

```js
import { runCopyGate } from "./gates/copy.mjs";
```

with:

```js
import { runCopyGate } from "./gates/copy.mjs";
import { gateReportLines } from "./gate-report.mjs";
```

In `site/scripts/verify.mjs` (:59-90), replace:

```js
/** Notes that must surface regardless of their position in the list. */
const WARNING_NOTE_RE = /at or above|near-ceiling|\bWARN\b/i;

function printGate(n, name, result) {
  const status = result.pass ? "PASS" : "FAIL";
  const details =
    result.notes.slice(0, 3).join("; ") +
    (result.errors.length > 0
      ? `; ERRORS: ${result.errors.slice(0, 5).join(" | ")}`
      : "");
  console.log(`gate ${n} ${name}: ${details} → ${status}`);
  // A WARNING note is printed wherever it sits in the list. notes.slice(0, 3)
  // above is a summary, and gate 1's page-weight warning lands well past
  // position 3 — so the near-ceiling alarm added 2026-08-14 was being
  // generated on every run and shown on none of them. A warning nobody sees
  // is not a warning; /coverage/ reached NINE bytes of headroom precisely
  // because nothing surfaced the drift.
  for (const note of result.notes) {
    if (WARNING_NOTE_RE.test(note) && !details.includes(note)) {
      console.log(`  ⚠ ${note}`);
    }
  }
  if (result.errors.length > 0) {
    for (const e of result.errors) {
      console.log(`  ✗ ${e}`);
    }
  }
  return result.pass;
}
```

with:

```js
/** Print one gate's report (scripts/gate-report.mjs; VERIFY_NOTES=all prints every note). */
function printGate(n, name, result) {
  for (const line of gateReportLines(n, name, result)) console.log(line);
  return result.pass;
}
```

In `site/scripts/generate-feeds.mjs` (:35), replace:

```js
import { fileURLToPath } from "url";
```

with:

```js
import { fileURLToPath } from "url";
import { isDirectRun } from "./direct-run.mjs";
```

In `site/scripts/generate-feeds.mjs` (:203), replace:

```js
if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url))) {
```

with:

```js
if (isDirectRun(import.meta.url)) {
```

In `site/scripts/run-mobile-leg.mjs` (:24-25; `fileURLToPath` had no other use here), replace:

```js
import { fileURLToPath } from "url";
import { startServer as defaultStartServer } from "./serve-static.mjs";
```

with:

```js
import { isDirectRun } from "./direct-run.mjs";
import { startServer as defaultStartServer } from "./serve-static.mjs";
```

In `site/scripts/run-mobile-leg.mjs` (:103-104), replace:

```js
// Same guard serve-static.mjs uses (:236).
if (process.argv[1] === fileURLToPath(import.meta.url)) {
```

with:

```js
// Same guard serve-static.mjs uses (real paths: ROADMAP #201).
if (isDirectRun(import.meta.url)) {
```

In `site/scripts/serve-static.mjs` (:18), replace:

```js
import { fileURLToPath } from "url";
```

with:

```js
import { fileURLToPath } from "url";
import { isDirectRun } from "./direct-run.mjs";
```

In `site/scripts/serve-static.mjs` (:236), replace:

```js
if (process.argv[1] === fileURLToPath(import.meta.url)) {
```

with:

```js
if (isDirectRun(import.meta.url)) {
```

In `site/scripts/gates/basis.mjs` (:224), replace:

```js
import { parse } from "node-html-parser";
```

with:

```js
import { parse } from "node-html-parser";
import { isDirectRun } from "../direct-run.mjs";
```

In `site/scripts/gates/basis.mjs` (:3384-3387), replace:

```js
if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href
) {
```

with:

```js
if (isDirectRun(import.meta.url)) {
```

In `site/scripts/f15-page-snapshot.mjs` (:32-33; `fileURLToPath` had no other use here), replace:

```js
import { fileURLToPath } from "url";
import { parse } from "node-html-parser";
```

with:

```js
import { parse } from "node-html-parser";
import { isDirectRun } from "./direct-run.mjs";
```

In `site/scripts/f15-page-snapshot.mjs` (:135), replace:

```js
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
```

with:

```js
if (isDirectRun(import.meta.url)) {
```

- [ ] **Step 5: Run the tests and the scripts**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && npx vitest run scripts/__tests__/direct-run.test.mjs scripts/__tests__/gate-report.test.mjs scripts/__tests__/run-mobile-leg.test.mjs scripts/gates/__tests__/f15-page-snapshot.test.mjs`
Expected: no failures (overlay: `17 passed` for the first three files; the snapshot tests are unchanged here).

Run the Step 1 block again.
Expected: the usage line and `via symlink: exit 2`, then the usage line and `direct: exit 2`.

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && node -e 'Promise.all(["./scripts/gates/basis.mjs", "./scripts/serve-static.mjs", "./scripts/generate-feeds.mjs"].map(p => import(p))).then(() => console.log("imports ok"))' && node --check scripts/verify.mjs && node --check scripts/run-mobile-leg.mjs && echo syntax-ok`
Expected: `imports ok` then `syntax-ok` (importing runs no body: each guard is false under `node -e`).

- [ ] **Step 6: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/site/scripts/direct-run.mjs GovBudget/site/scripts/gate-report.mjs GovBudget/site/scripts/verify.mjs GovBudget/site/scripts/generate-feeds.mjs GovBudget/site/scripts/run-mobile-leg.mjs GovBudget/site/scripts/serve-static.mjs GovBudget/site/scripts/gates/basis.mjs GovBudget/site/scripts/f15-page-snapshot.mjs GovBudget/site/scripts/__tests__/direct-run.test.mjs GovBudget/site/scripts/__tests__/gate-report.test.mjs && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "fix(site-scripts): direct-run guards compare real paths; verify says how many notes it left out (#201)" -m "Five scripts compared argv[1] with their own path as strings; run through a symlink they exited 0 having checked nothing. isDirectRun compares realpaths. gateReportLines appends +K more notes and prints them all with VERIFY_NOTES=all; warnings still surface wherever they sit." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
