<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. -->

### Task 15: /years/ gates — the merged-view loader and size budgets, leg g through the era map, leg j sidecar parity, leg k lazy opening, the live probe, the Q13 clause swap, the spec §6.2 amendment (#193, #206 T4)

**Spec:** `docs/superpowers/specs/2026-10-04-families-piece1-followups-design.md` §3.6 (gates and tests; the `linkgraph.mjs`, `fetch-targets.test.mjs`, `verify_live_assets.mjs:812`, `LAUNCH.md:642` and `test_launch_deploy_landing.py:155` items), §3.7 "/methodology/ `#coverage-years-matrix`" and the byte budget, §5.5 (#206 T4 subsumed by leg j), §8 step 7 (the live checks this task makes mechanical); owner answers Q11 and Q13; the "Spec. §6.2 gets a dated amendment" line of §3.6.
**Files:**
- Create: `site/scripts/gates/years-matrix-load.mjs`, `site/scripts/gates/__tests__/years-matrix-gate.test.mjs`, `tests/test_yearsmatrix_recompute.py`, `site/src/__tests__/methodology-years-matrix-gap.test.ts`
- Modify: `site/scripts/gates/yearsmatrix.mjs` (header `:52-58`, imports `:96-98`, `sampleDecadeCells` `:194-204` plus new helpers after it, the static load `:510-533`, legs f/g `:706-818`, a leg-j call before leg d `:822`, the page listeners `:955-958`, a leg-k block `:982`, the i3 reveal `:1156-1158`, the expand wait `:1384-1386`, the Δ chip wait `:1588-1590`), `site/scripts/gates/yearsmatrix-recompute.py` (docstring, path set-up, the decade query), `site/scripts/gates/linkgraph.mjs` (`:1055-1067`, `:1144-1145`), `site/scripts/gates/__tests__/fetch-targets.test.mjs` (imports, one new test), `scripts/launch/verify_live_assets.mjs` (header assertion list, `:812`, a probe before `checkFixedName`), `tests/test_launch_deploy_landing.py` (`:155`, a helper before the `landed` fixture, two lines in `test_a_deploy_that_landed_passes`, four tests appended), `docs/superpowers/LAUNCH.md` (`:636-642`), `site/src/app/methodology/page.tsx` (`:1722-1723`), `docs/superpowers/specs/2026-10-02-era-procurement-history-design.md` (after the §6.2 table)

Line numbers are hints (anchor on the quoted text): Task 14 and earlier tasks shift them.

**Interfaces:**
- Consumes: Task 13's files and fixtures (`json/years_matrix.json` schema 2 with `build_id` and `shards`; `tests/fixtures/years_matrix_split/basic/`); Task 14's `mergeYearsMatrix` and `YEARS_SHARD_NAMES` from `site/src/lib/years-matrix-shards.mjs`, the island's `table[data-testid="years-matrix"]` `data-shards` and `aria-busy` markers, and its six static fetch targets; piece 1's `data/site/data/p1_era_line_map.parquet` (columns `edition, era_key, program_key, program_account, program_org, decision`) and `govbudget.jbooks.era_keys.is_era_procurement_key`; `data/site/json/programs.json` rows' `slug`, `account`, `org`.
- Produces:
  - `site/scripts/gates/years-matrix-load.mjs`: `loadYearsMatrix(jsonDir) -> { matrix, core, files: [{ rel, bytes, gzip }] }` (throws on a schema-1 export, a manifest byte or sha mismatch, a shard from another build or a stray file in `years_matrix/`), `gzip9(buf) -> number` (`gzip -9 -n`), `YEARS_CORE`, `YEARS_SHARD_DIR`. Task 21's P2b tool (`scripts/fu/years_shard_proof.py`, G5) may reuse it through node, or reimplement the same checks in Python with Task 13's `merge_years_matrix`.
  - `site/scripts/gates/yearsmatrix.mjs` exports: `eraCellKind(cit) -> "leaf" | "sum" | null`, `decadeSourceProblem(s, cit, rows, members) -> string | null`, `runSidecarParityLeg(matrix, jsonDir, errors, notes)`, `checkYearsFileBudgets(files, errors, notes)`, `YEARS_FILE_MAX_BYTES = 4194304`, `YEARS_CORE_GZIP_MAX = 780074`, `openingFetchProblem(requests, shards) -> string | null`, and `probeYearsOpeningFetches(baseUrl) -> Promise<{ requests, shards, problem }>` — Task 22's live check "a /years/ page load fetches only the core" runs it against `https://fiscalreceipts.com` (`problem` must be `null`).
  - Gate 20 legs after this task: a–i as before but on the merged view, g resolving era cells through `p1_era_line_map` with per-edition non-vacuity, j (sidecar parity, must read 0), k (live: opening fetches only the core), and the size budgets. On an export from before Task 13 gate 20 now FAILS (`years matrix: years_matrix.json is schema_version 1 …`): run it only on an export made with Task 13's code (Task 21's B exports, Task 22's release export).
  - `site/scripts/gates/yearsmatrix-recompute.py` accepts an optional second argument (the site data directory) and returns `era: [{era_key, program_key, decision, program_account, program_org}]` per decade fact.
  - `site/scripts/gates/linkgraph.mjs` exports `MIN_STATIC_FETCH_TARGETS` (now 6).
  - `scripts/launch/verify_live_assets.mjs` assertion 8 (`checkYearsMatrix`): the live core parses with a `build_id` and a shard manifest, and every listed shard answers 200 with the manifest's sha256 and the core's `build_id` — Task 22's live check "`decade.json` and `detail.json` return 200 and carry the core's `build_id`" runs inside `deploy.sh`'s step 4.
  - The dated amendment to piece-1 spec §6.2 (Task 22's ROADMAP stamp cites it and does not add another).

Gate 20 reads the core and its two shards through one loader that merges them
with the island's own `mergeYearsMatrix`, so every static leg checks the cells
a reader can reach, and the loader proves the three files are one export. Leg g
learns the era path: a PB2017–PB2023 procurement cell's lake rows carry an era
key, and belong to the row only through a reviewed `same_program` decision in
`p1_era_line_map` whose `program_key` is the row's code and, on a split row,
whose pins are the row's own; it must verify an era leaf and an era-map sum in
every era edition. Leg j is T4's "absent means absent" check: every row shows
exactly its program page's decade points. On today's export it finds 15,048
missing cells on 795 rows, 0 extra and 0 different (measured 2026-10-13 from
`data/site`, built 2026-10-04; Step 4 reproduces it). A read-only simulation
of the post-lift payload (each row given its own sidecar's points) passes every
static leg: size, a 47/47, b 47, f 64/64, g 64/64 with an era leaf and an
era-map sum in each of PB2017–PB2023, i 45,316 of 46,524 cells checked with no
contradiction, j 46,524 cells on 1,938 rows equal, d 53,072 fids. The live legs
wait on the island's markers instead of timeouts, and leg k checks that
opening `/years/` fetches only the core.

- [ ] **Step 1: Write the failing gate unit tests**

Create `site/scripts/gates/__tests__/years-matrix-gate.test.mjs`:

```js
/**
 * Gate 20 (yearsmatrix) after the #193 split — the pieces that need no build:
 * the loader every static leg reads through, the size budgets, leg g's
 * source check (era cells through p1_era_line_map), leg j's sidecar parity
 * and leg k's opening-fetch rule. Each planted failure must fail; the real
 * split (tests/fixtures/years_matrix_split/, written by the Python exporter)
 * must load. Hermetic: nothing reads data/site or starts a browser.
 */
import { describe, it, expect } from "vitest";
import fs from "fs";
import os from "os";
import path from "path";
import { createHash } from "node:crypto";
import { gzip9, loadYearsMatrix } from "../years-matrix-load.mjs";
import {
  checkYearsFileBudgets,
  decadeSourceProblem,
  eraCellKind,
  openingFetchProblem,
  runSidecarParityLeg,
} from "../yearsmatrix.mjs";

const FIXTURES = path.resolve(
  __dirname, "..", "..", "..", "..", "tests", "fixtures", "years_matrix_split",
);

/** A writable copy of one fixture split, as a json/ directory. */
function copyFixture(name) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "years-gate-"));
  fs.cpSync(path.join(FIXTURES, name), dir, { recursive: true });
  fs.rmSync(path.join(dir, "payload.json"));
  return dir;
}

/** Rewrite one shard and keep the core's manifest entry true to it. */
function rewriteShard(dir, name, edit) {
  const rel = path.join("years_matrix", `${name}.json`);
  const shard = edit(JSON.parse(fs.readFileSync(path.join(dir, rel), "utf8")));
  const buf = Buffer.from(JSON.stringify(shard));
  fs.writeFileSync(path.join(dir, rel), buf);
  const core = JSON.parse(fs.readFileSync(path.join(dir, "years_matrix.json"), "utf8"));
  const entry = core.shards.find((s) => s.name === name);
  entry.bytes = buf.length;
  entry.sha256 = createHash("sha256").update(buf).digest("hex");
  fs.writeFileSync(path.join(dir, "years_matrix.json"), JSON.stringify(core));
}

describe("loadYearsMatrix — the merged view every static leg reads", () => {
  it("loads the exporter's split and merges the shards back on their rows", () => {
    const { matrix, files } = loadYearsMatrix(copyFixture("basic"));
    const rows = new Map(matrix.orgs.flatMap((o) => o.programs.map((p) => [p.pe_bli, p])));
    expect(rows.get("0602303A").cells.fy2019r).toEqual({ fid: "f411000000000042", v: 888.0 });
    expect(rows.get("0601101E").projects.map((p) => p.project_number)).toEqual(["P1"]);
    expect(files.map((f) => f.rel)).toEqual([
      "years_matrix.json", "years_matrix/decade.json", "years_matrix/detail.json",
    ]);
    for (const f of files) expect(f.gzip).toBeGreaterThan(0);
  });

  it("refuses an export from before the split", () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "years-gate-"));
    fs.writeFileSync(path.join(dir, "years_matrix.json"), JSON.stringify({ schema_version: 1, orgs: [] }));
    expect(() => loadYearsMatrix(dir)).toThrow(/before the #193 split/);
  });

  it("refuses a shard whose bytes are not the manifest's", () => {
    const dir = copyFixture("basic");
    fs.appendFileSync(path.join(dir, "years_matrix", "decade.json"), " ");
    expect(() => loadYearsMatrix(dir)).toThrow(/manifest says/);
  });

  it("refuses a shard from another build", () => {
    const dir = copyFixture("basic");
    rewriteShard(dir, "decade", (s) => ({ ...s, build_id: "0".repeat(64) }));
    expect(() => loadYearsMatrix(dir)).toThrow(/build_id/);
  });

  it("refuses a file in years_matrix/ the core does not list", () => {
    const dir = copyFixture("basic");
    fs.writeFileSync(path.join(dir, "years_matrix", "stale.json"), "{}");
    expect(() => loadYearsMatrix(dir)).toThrow(/does not list: stale\.json/);
  });

  it("measures gzip the way the exporter does (gzip -9, no name or timestamp)", () => {
    const buf = Buffer.from("x".repeat(10_000));
    expect(gzip9(buf)).toBe(gzip9(buf));
    expect(gzip9(buf)).toBeLessThan(200);
  });
});

describe("size budgets (Q11) — never raised", () => {
  const files = (coreGzip, decadeBytes) => [
    { rel: "years_matrix.json", bytes: 1_100_823, gzip: coreGzip },
    { rel: "years_matrix/decade.json", bytes: decadeBytes, gzip: 433_932 },
  ];
  it("passes the split as measured on the 2026-10-04 lake", () => {
    const errors = [];
    const notes = [];
    checkYearsFileBudgets(files(344_303, 1_390_739), errors, notes);
    expect(errors).toEqual([]);
    expect(notes[0]).toMatch(/^size: years_matrix\.json 1100823 B \(344303 gzip\)/);
  });
  it("fails a file over 4 MiB and a core over 780,074 B gzip", () => {
    const errors = [];
    checkYearsFileBudgets(files(780_075, 4 * 1024 * 1024 + 1), errors, []);
    expect(errors).toHaveLength(2);
    expect(errors[0]).toMatch(/years_matrix\/decade\.json is 4194305 bytes, over the 4 MiB cap/);
    expect(errors[1]).toMatch(/gzips to 780075 bytes, over the 780074-byte budget/);
  });
});

describe("leg g — a decade cell's sources (era cells through p1_era_line_map)", () => {
  const col = { key: "fy2017a", edition: 2019 };
  const leaf = { kind: "workbook", sha256: "sha_p1" };
  const native = { n: 1, fys: [2019], pes: ["0601101E"], shas: ["sha_r1"], era: [] };
  const eraRow = (over = {}) => ({
    n: 1, fys: [2019], pes: ["0300D-DCSA-L5"], shas: ["sha_p1"],
    era: [{
      era_key: "0300D-DCSA-L5", program_key: "20", decision: "same_program",
      program_account: "0300D", program_org: "DCSA", ...over,
    }],
  });
  const members = new Map([["20-DCSA", { account: "0300D", org: "DCSA" }]]);
  const dcsa = { pe_bli: "20", slug: "20-DCSA", col };

  it("passes a native cell and an era cell that reach their row", () => {
    expect(decadeSourceProblem({ pe_bli: "0601101E", col }, { kind: "workbook", sha256: "sha_r1" }, [native], members)).toBeNull();
    expect(decadeSourceProblem(dcsa, leaf, [eraRow()], members)).toBeNull();
    // an era-map sum: two leaves, a derived citation (no sha to check)
    expect(decadeSourceProblem(dcsa, { kind: "derived" }, [eraRow(), eraRow()], members)).toBeNull();
  });

  const derived = { kind: "derived" };
  it.each([
    ["a source in another edition", derived, [{ ...eraRow(), fys: [2018] }], /edition\(s\) \[2018\] != stated PB2019/],
    ["a citation sha not among the rows", leaf, [{ ...eraRow(), shas: ["sha_other"] }], /sha256 not among/],
    ["a fid resolving to two lake rows", derived, [{ ...eraRow(), n: 2 }], /1 input fid\(s\) resolve to 2 lake row/],
    ["an era key with no map row", derived, [eraRow({ program_key: null, decision: null })], /has no p1_era_line_map row in PB2019/],
    ["a history_only decision", derived, [eraRow({ decision: "history_only" })], /decided history_only, not same_program/],
    ["another program's key", derived, [eraRow({ program_key: "30" })], /maps to program_key 30, not 20/],
    ["the sibling row's pins", derived, [eraRow({ program_org: "DTRA" })], /pinned to \(0300D, DTRA\), not the row's \(0300D, DCSA\)/],
    ["a non-era foreign row", derived, [{ ...native, pes: ["0602702E"] }], /not all of them era keys/],
  ])("fails %s", (_what, cit, rows, message) => {
    expect(decadeSourceProblem(dcsa, cit, rows, members)).toMatch(message);
  });

  it("classifies era cells by their citation", () => {
    expect(eraCellKind({ kind: "workbook", sheet: "Exhibit P-1" })).toBe("leaf");
    expect(eraCellKind({ kind: "derived", formula: "sum(budget_lines.amount_thousands where era_line_map='20' and amount_type=fy_2017_actuals and edition=2019)" })).toBe("sum");
    expect(eraCellKind({ kind: "workbook", sheet: "Exhibit R-1" })).toBeNull();
    expect(eraCellKind({ kind: "derived", formula: "sum(budget_lines.amount_thousands where pe_bli='x')" })).toBeNull();
  });
});

describe("leg j — every /years/ decade cell is its program page's point", () => {
  const COLS = [
    { key: "fy2017a", fy: 2017, kind: "actuals", edition: 2019 },
    { key: "fy2026r", fy: 2026, kind: "request", edition: 2026 },
  ];
  const point = (fy, edition, v, fid) => ({ fy, edition, v, fid, basis: "toa", measure: "actuals" });
  function run(cells, series) {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "years-legj-"));
    fs.mkdirSync(path.join(dir, "program_details"));
    fs.writeFileSync(path.join(dir, "program_details", "20-DCSA.json"), JSON.stringify({ decade_series: series }));
    const matrix = {
      decade_columns: COLS,
      orgs: [{ org: "DCSA", programs: [{ pe_bli: "20", slug: "20-DCSA", title: "Vehicles", cells, projects: [] }] }],
    };
    const errors = [];
    const notes = [];
    runSidecarParityLeg(matrix, dir, errors, notes);
    return { errors, notes };
  }
  const SERIES = {
    actuals: [point(2017, 2019, 1057, "fc11000000000055")],
    request: [point(2026, 2026, 2230, "fd11000000000001")],
  };
  const CELLS = {
    fy2017a: { v: 1057, fid: "fc11000000000055" },
    fy2026r: { v: 2230, fid: "fd11000000000001" },
  };

  it("passes when the row shows exactly the page's points", () => {
    const { errors, notes } = run(CELLS, SERIES);
    expect(errors).toEqual([]);
    expect(notes[0]).toMatch(/^leg j: 2 decade cell\(s\) on 1 row\(s\) equal/);
  });
  it("fails a point the grid leaves out (the fenced era cell)", () => {
    const { errors } = run({ fy2026r: CELLS.fy2026r }, SERIES);
    expect(errors[0]).toMatch(/^leg j: 1 cell\(s\) the program page has and \/years\/ does not: 20-DCSA\/fy2017a/);
  });
  it("fails a cell the page does not have", () => {
    const { errors } = run(CELLS, { request: SERIES.request });
    expect(errors[0]).toMatch(/^leg j: 1 cell\(s\) \/years\/ shows that the program page does not/);
  });
  it("fails a cell whose value or fid differs", () => {
    const { errors } = run({ ...CELLS, fy2026r: { v: 2231, fid: "fd11000000000001" } }, SERIES);
    expect(errors[0]).toMatch(/^leg j: 1 cell\(s\) whose value or fid differs/);
  });
  it("fails a row with no sidecar", () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "years-legj-"));
    const errors = [];
    runSidecarParityLeg(
      { decade_columns: COLS, orgs: [{ org: "N", programs: [{ pe_bli: "2013", title: "x", cells: {}, projects: [] }] }] },
      dir, errors, [],
    );
    expect(errors[0]).toMatch(/^leg j: 1 \/years\/ row\(s\) have no program_details sidecar/);
  });
});

describe("leg k — /years/ opens on the core alone", () => {
  it("passes one core request and the data-shards marker 'core'", () => {
    expect(openingFetchProblem(["/json/years_matrix.json"], "core")).toBeNull();
  });
  it("fails a shard fetched on open", () => {
    expect(
      openingFetchProblem(["/json/years_matrix.json", "/json/years_matrix/detail.json"], "core detail"),
    ).toMatch(/fetched \[\/json\/years_matrix\.json, \/json\/years_matrix\/detail\.json\]/);
  });
  it("fails an island that never marked itself", () => {
    expect(openingFetchProblem(["/json/years_matrix.json"], null)).toMatch(/data-shards="null"/);
  });
});
```

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site && npx vitest run scripts/gates/__tests__/years-matrix-gate.test.mjs
```

Expected: `FAIL  scripts/gates/__tests__/years-matrix-gate.test.mjs` with
`Error: Failed to resolve import "../years-matrix-load.mjs"`.

- [ ] **Step 2: Write the loader and teach gate 20 the split, the era path and legs j and k**

Create `site/scripts/gates/years-matrix-load.mjs`:

```js
/**
 * years-matrix-load.mjs — the ONE loader every /years/ check reads through
 * (families piece-1 follow-ups design §3.6, ROADMAP #193).
 *
 * The exporter writes json/years_matrix.json (the core) and two lazy shards,
 * json/years_matrix/decade.json and json/years_matrix/detail.json. The
 * yearsmatrix gate's static legs (a, b, d, e, f, g, i, j) run on the MERGED
 * view, built here with the same mergeYearsMatrix the /years/ island runs, so
 * a leg checks exactly the cells a reader can reach. On the way it proves the
 * files belong together: every shard the core's manifest lists exists with
 * the manifest's byte count and sha256 and carries the core's build_id, and
 * the shard directory holds nothing else.
 *
 * loadYearsMatrix(jsonDir) → { matrix, core, files }
 *   matrix  the merged view (YearsMatrixData shape, rows keep `np`)
 *   core    the parsed core
 *   files   [{ rel, bytes, gzip }] for the core and each shard, gzip
 *           measured by gzip9 (the exporter's measure)
 * Throws with the reason on any inconsistency, or on a pre-split export
 * (schema_version 1), which the gate no longer accepts.
 */
import fs from "fs";
import path from "path";
import { createHash } from "node:crypto";
import { spawnSync } from "child_process";
import { mergeYearsMatrix, YEARS_SHARD_NAMES } from "../../src/lib/years-matrix-shards.mjs";

export const YEARS_CORE = "years_matrix.json";
export const YEARS_SHARD_DIR = "years_matrix";

/**
 * gzip -9 size of a buffer, by the system gzip (`-n`: no name or timestamp
 * in the header). This is the exporter's own measure: Python's
 * gzip.compress(level 9) and `gzip -9 -n` give 780,074 B for the deployed
 * single file, where node's bundled zlib gives 754,311 B (measured
 * 2026-10-13), so a budget checked with node's zlib would be looser than the
 * one the exporter enforces.
 */
export function gzip9(buf) {
  const res = spawnSync("gzip", ["-9", "-n", "-c"], {
    input: buf,
    maxBuffer: 64 * 1024 * 1024,
  });
  if (res.status !== 0) {
    throw new Error(`gzip -9 exited ${res.status}: ${String(res.stderr).slice(0, 200)}`);
  }
  return res.stdout.length;
}

export function loadYearsMatrix(jsonDir) {
  const corePath = path.join(jsonDir, YEARS_CORE);
  if (!fs.existsSync(corePath)) {
    throw new Error(`${YEARS_CORE} missing at ${corePath} — run export-site`);
  }
  const coreBuf = fs.readFileSync(corePath);
  const core = JSON.parse(coreBuf.toString("utf8"));
  if (core.schema_version !== 2 || !Array.isArray(core.shards)) {
    throw new Error(
      `${YEARS_CORE} is schema_version ${core.schema_version} with no shard ` +
        `manifest: an export from before the #193 split — re-run export-site`,
    );
  }
  const files = [{ rel: YEARS_CORE, bytes: coreBuf.length, gzip: gzip9(coreBuf) }];
  const shards = [];
  const listed = new Set();
  for (const entry of core.shards) {
    if (!YEARS_SHARD_NAMES.includes(entry.name)) {
      throw new Error(`${YEARS_CORE} lists an unknown shard ${JSON.stringify(entry.name)}`);
    }
    listed.add(path.basename(entry.path));
    const shardPath = path.join(jsonDir, ...entry.path.split("/"));
    if (!fs.existsSync(shardPath)) {
      throw new Error(`${entry.path} is listed by ${YEARS_CORE} but missing`);
    }
    const buf = fs.readFileSync(shardPath);
    if (buf.length !== entry.bytes) {
      throw new Error(`${entry.path} is ${buf.length} bytes; the manifest says ${entry.bytes}`);
    }
    const sha = createHash("sha256").update(buf).digest("hex");
    if (sha !== entry.sha256) {
      throw new Error(`${entry.path} sha256 ${sha} != the manifest's ${entry.sha256}`);
    }
    const shard = JSON.parse(buf.toString("utf8"));
    if (shard.shard !== entry.name) {
      throw new Error(`${entry.path} says it is shard ${JSON.stringify(shard.shard)}`);
    }
    shards.push(shard);
    files.push({ rel: entry.path, bytes: buf.length, gzip: gzip9(buf) });
  }
  const shardDir = path.join(jsonDir, YEARS_SHARD_DIR);
  const strays = fs.existsSync(shardDir)
    ? fs.readdirSync(shardDir).filter((f) => !listed.has(f))
    : [];
  if (strays.length > 0) {
    throw new Error(
      `${YEARS_SHARD_DIR}/ holds file(s) the core does not list: ${strays.join(", ")}`,
    );
  }
  // mergeYearsMatrix throws if any shard's build_id is not the core's.
  return { matrix: mergeYearsMatrix(core, shards), core, files };
}
```

**Edit 15.1** — header legs — `site/scripts/gates/yearsmatrix.mjs` (anchor on the quoted text). Replace this exact text:

```js
 *  (g) edition integrity (Phase 5E, ADDITIVE — spec §2 rule 1): every
 *      sampled decade cell's source rows carry fiscal_year == the column's
 *      STATED edition and the cell's pe_bli; workbook citations' sha256
 *      must be among their lake rows' document_sha256. UI side (leg g-UI):
 *      the default view renders the decade columns with visible PB-edition
 *      tags and the edition-rule legend ("PB(N+2)"), and decade cells are
 *      state-A Cites.
```

with:

```js
 *  (g) edition integrity (Phase 5E, ADDITIVE — spec §2 rule 1): every
 *      sampled decade cell's source rows carry fiscal_year == the column's
 *      STATED edition and the cell's pe_bli; workbook citations' sha256
 *      must be among their lake rows' document_sha256. UI side (leg g-UI):
 *      the default view renders the decade columns with visible PB-edition
 *      tags and the edition-rule legend ("PB(N+2)"), and decade cells are
 *      state-A Cites.
 *      ERA CELLS (ROADMAP #193, follow-ups design §3.6): a PB2017–PB2023
 *      procurement cell's lake rows carry an era key ('3020F-AF-L8'), not
 *      the row's code, and belong to the row only through the reviewed era
 *      map (data/site/data/p1_era_line_map.parquet, joined by the recompute
 *      helper): each key must map, in the stated edition, to a same_program
 *      decision whose program_key is the row's pe_bli, a split row's
 *      (account, org) pins must be the row's own, and the rows must be one
 *      per input fid (decadeSourceProblem). Non-vacuity: at least one era
 *      leaf (a P-1 workbook fact) and one era-map sum (a decade_era_map
 *      fact) verified in every PB2017–PB2023 edition.
 *  (j) SIDECAR PARITY (ROADMAP #193; #206 T4): every row, every decade
 *      column — a cell is present iff the row's program page sidecar has
 *      the point, with the same value and fid (runSidecarParityLeg).
 *  (k) LAZY OPENING (live): opening /years/ fetches the core and nothing
 *      else; the lazy shards load only when a reader asks for a column or
 *      a project row they hold (openingFetchProblem).
 *  size: every /years/ file at most 4 MiB on disk, and the core at most
 *      780,074 B at gzip -9 (checkYearsFileBudgets; neither may be raised).
 *
 *  The static legs read the MERGED view of the core and its two shards
 *  through years-matrix-load.mjs, which also proves the three files belong
 *  to one export (manifest bytes, sha256 and build_id).
```

**Edit 15.2** — imports — `site/scripts/gates/yearsmatrix.mjs` (anchor on the quoted text). Replace this exact text:

```js
import { spawnSync } from "child_process";
import { fileURLToPath } from "url";
import { chromium } from "playwright";
```

with:

```js
import { spawnSync } from "child_process";
import { fileURLToPath } from "url";
import { chromium } from "playwright";
import { loadYearsMatrix, YEARS_CORE } from "./years-matrix-load.mjs";
```

**Edit 15.3** — decade sample carries slug — `site/scripts/gates/yearsmatrix.mjs` (anchor on the quoted text). Replace this exact text:

```js
        const { program } = programs[i];
        const cell = program.cells[key];
        if (cell && cell.fid) {
          out.push({ pe_bli: program.pe_bli, col, cell });
          n++;
        }
      }
    }
  }
  return out;
}
```

with:

```js
        const { program } = programs[i];
        const cell = program.cells[key];
        if (cell && cell.fid) {
          out.push({ pe_bli: program.pe_bli, slug: program.slug, col, cell });
          n++;
        }
      }
    }
  }
  return out;
}

/** The last edition whose procurement lines are era keys (families piece 1). */
const LAST_ERA_EDITION = 2023;

/** "leaf" for an era P-1 workbook fact, "sum" for a decade_era_map derived
 *  fact, null otherwise. Before PB2024 a P-1 line has no native program
 *  grain, so every P-1 workbook decade cell of an era column is an era leaf
 *  (on the 2026-10-04 export: 14,082 leaves and 903 sums once the fence
 *  lifts, every other PB2017–PB2023 cell an R-1 one). */
export function eraCellKind(cit) {
  if (!cit) return null;
  if (cit.kind === "workbook" && cit.sheet === "Exhibit P-1") return "leaf";
  if (cit.kind === "derived" && /\bera_line_map=/.test(cit.formula ?? "")) return "sum";
  return null;
}

/**
 * Era cells for legs f and g (non-vacuity, design §3.6): in every
 * PB2017–PB2023 edition, up to `perKind` era leaves and `perKind` era-map
 * sums, strided across rows over EVERY column of that edition, the decade
 * shard's included.
 */
function sampleEraCells(matrix, citations, { perKind = 2 } = {}) {
  const cols = (matrix.decade_columns ?? []).filter((c) => c.edition <= LAST_ERA_EDITION);
  const programs = [...iterPrograms(matrix)];
  const stride = Math.max(1, Math.floor(programs.length / 37));
  const out = [];
  for (const edition of [...new Set(cols.map((c) => c.edition))].sort((a, b) => a - b)) {
    const taken = { leaf: 0, sum: 0 };
    for (const col of cols.filter((c) => c.edition === edition)) {
      for (let pass = 0; pass < stride; pass++) {
        for (let i = pass; i < programs.length; i += stride) {
          const { program } = programs[i];
          const cell = program.cells[col.key];
          if (!cell || !cell.fid) continue;
          const kind = eraCellKind(citations[cell.fid]);
          if (!kind || taken[kind] >= perKind) continue;
          taken[kind]++;
          out.push({ pe_bli: program.pe_bli, slug: program.slug, col, cell, era: kind });
        }
      }
    }
  }
  return out;
}

/**
 * Leg (g) for ONE decade cell: null when its source rows sit in the column's
 * stated edition and belong to the cell's row, else what is wrong.
 *
 *   s        { pe_bli, slug?, col: { key, edition }, cell }
 *   cit      the cell's citation (a workbook one: its sha256 must be among
 *            the rows' documents)
 *   rows     the recompute helper's entry for each input fid:
 *            { n, fys, pes, shas, era: [{ era_key, program_key, decision,
 *            program_account, program_org }] }
 *   members  slug → { account, org } for split rows (programs.json)
 *
 * A native cell's rows carry the row's own pe_bli. An era cell's rows carry
 * era keys, and belong to the row only through the reviewed era map: every
 * key must map to a same_program decision whose program_key is the row's
 * pe_bli and, on a split row, whose (account, org) pins are the row's own.
 */
export function decadeSourceProblem(s, cit, rows, members) {
  const where = `${s.slug ?? s.pe_bli}/${s.col.key}`;
  const n = rows.reduce((acc, r) => acc + r.n, 0);
  if (n !== rows.length) {
    return `decade cell ${where}: ${rows.length} input fid(s) resolve to ${n} lake row(s)`;
  }
  const fys = new Set(rows.flatMap((r) => r.fys));
  if (fys.size !== 1 || !fys.has(s.col.edition)) {
    return `decade cell ${where} sources span edition(s) [${[...fys].join(",")}] != stated PB${s.col.edition}`;
  }
  if (cit.kind === "workbook" && !rows.some((r) => (r.shas ?? []).includes(cit.sha256))) {
    return `decade cell ${where} citation sha256 not among its lake rows`;
  }
  const pes = new Set(rows.flatMap((r) => r.pes));
  if (pes.size === 1 && pes.has(s.pe_bli)) return null;
  const era = rows.flatMap((r) => r.era ?? []);
  if (era.length !== n) {
    return `decade cell ${where} sources span pe_bli(s) [${[...pes].join(",")}], not all of them era keys`;
  }
  for (const e of era) {
    if (e.program_key == null) {
      return `decade cell ${where}: era key ${e.era_key} has no p1_era_line_map row in PB${s.col.edition}`;
    }
    if (e.decision !== "same_program") {
      return `decade cell ${where}: era key ${e.era_key} is decided ${e.decision}, not same_program`;
    }
    if (e.program_key !== s.pe_bli) {
      return `decade cell ${where}: era key ${e.era_key} maps to program_key ${e.program_key}, not ${s.pe_bli}`;
    }
    if (s.slug) {
      const m = members.get(s.slug);
      if (!m || e.program_account !== m.account || e.program_org !== m.org) {
        return (
          `decade cell ${where}: era key ${e.era_key} is pinned to ` +
          `(${e.program_account}, ${e.program_org}), not the row's (${m?.account}, ${m?.org})`
        );
      }
    }
  }
  return null;
}

/**
 * Leg (j) — SIDECAR PARITY (follow-ups design §3.6, ROADMAP #193; #206 T4).
 * /years/ shows exactly what each program page shows: for every row and
 * every decade column, a cell is present if and only if the row's sidecar
 * (program_details/<slug ?? pe_bli>.json) has a decade point with the same
 * (kind, edition, fy), and then with the same value and fid. On the
 * 2026-10-04 export, before the fence lifted, it found 15,048 missing cells
 * on 795 rows (5,030 of them in the default view: 4,995 era cells and the 35
 * modern default cells of the seven organization-split rows), none extra and
 * none different; it must find none in either direction. /methodology/'s
 * #coverage-years-matrix and #coverage-editions gap sentences rest on it: a
 * "—" means the book has no figure, never that the grid left one out.
 */
export function runSidecarParityLeg(matrix, jsonDirArg, errors, notes) {
  const cols = matrix.decade_columns ?? [];
  if (cols.length === 0) {
    errors.push("leg j is VACUOUS: the payload carries no decade_columns");
    return;
  }
  const byKindFy = new Map(cols.map((c) => [`${c.kind}|${c.fy}`, c]));
  let rows = 0;
  let compared = 0;
  const found = { missing: [], extra: [], differ: [] };
  const counts = { missing: 0, extra: 0, differ: 0 };
  const note = (kind, text) => {
    counts[kind]++;
    if (found[kind].length < 5) found[kind].push(text);
  };
  const noSidecar = [];
  for (const { program } of iterPrograms(matrix)) {
    const key = program.slug ?? program.pe_bli;
    const sidecar = path.join(jsonDirArg, "program_details", `${key}.json`);
    if (!fs.existsSync(sidecar)) {
      noSidecar.push(key);
      continue;
    }
    rows++;
    const points = new Map();
    for (const [kind, series] of Object.entries(readJson(sidecar).decade_series ?? {})) {
      for (const pt of series) {
        const col = byKindFy.get(`${kind}|${pt.fy}`);
        if (!col || col.edition !== pt.edition) {
          note("missing", `${key}: FY${pt.fy} ${kind} (PB${pt.edition}, fid ${pt.fid}) has no /years/ column`);
          continue;
        }
        points.set(col.key, pt);
      }
    }
    for (const col of cols) {
      const cell = program.cells[col.key];
      const pt = points.get(col.key);
      if (!cell && !pt) continue;
      compared++;
      if (!cell) note("missing", `${key}/${col.key} (PB${col.edition}, fid ${pt.fid})`);
      else if (!pt) note("extra", `${key}/${col.key} (fid ${cell.fid})`);
      else if (cell.v !== pt.v || cell.fid !== pt.fid) {
        note("differ", `${key}/${col.key}: grid ${cell.v} ${cell.fid}, page ${pt.v} ${pt.fid}`);
      }
    }
  }
  if (noSidecar.length > 0) {
    errors.push(
      `leg j: ${noSidecar.length} /years/ row(s) have no program_details sidecar ` +
        `(first: ${noSidecar.slice(0, 5).join(", ")})`,
    );
  }
  if (rows === 0 || compared === 0) {
    errors.push(`leg j is VACUOUS: ${rows} row(s), ${compared} cell(s) compared`);
    return;
  }
  for (const [kind, what] of [
    ["missing", "cell(s) the program page has and /years/ does not"],
    ["extra", "cell(s) /years/ shows that the program page does not"],
    ["differ", "cell(s) whose value or fid differs from the program page"],
  ]) {
    if (counts[kind] > 0) {
      errors.push(`leg j: ${counts[kind]} ${what}: ${found[kind].join(" | ")}`);
    }
  }
  if (counts.missing + counts.extra + counts.differ === 0) {
    notes.push(
      `leg j: ${compared} decade cell(s) on ${rows} row(s) equal their program ` +
        `page's points, 0 missing, 0 extra ✓`,
    );
  }
}

/** The /years/ size budgets (follow-ups design §3.6, Q11). Never raise them. */
export const YEARS_FILE_MAX_BYTES = 4 * 1024 * 1024;
export const YEARS_CORE_GZIP_MAX = 780_074;

/** Every /years/ file at most 4 MiB on disk, the core at most 780,074 B at
 *  gzip -9 (what the deployed single file cost a reader on open). */
export function checkYearsFileBudgets(files, errors, notes) {
  for (const f of files) {
    if (f.bytes > YEARS_FILE_MAX_BYTES) {
      errors.push(`size: ${f.rel} is ${f.bytes} bytes, over the 4 MiB cap per /years/ file`);
    }
  }
  const core = files.find((f) => f.rel === YEARS_CORE);
  if (!core) {
    errors.push(`size: ${YEARS_CORE} was not measured`);
  } else if (core.gzip > YEARS_CORE_GZIP_MAX) {
    errors.push(
      `size: ${YEARS_CORE} gzips to ${core.gzip} bytes, over the ` +
        `${YEARS_CORE_GZIP_MAX}-byte budget for what /years/ downloads on open`,
    );
  }
  notes.push(
    `size: ${files.map((f) => `${f.rel} ${f.bytes} B (${f.gzip} gzip)`).join("; ")}`,
  );
}

/** Leg (k): null when opening /years/ fetched only the core, else why not.
 *  `requests` are the /json/years_matrix* paths requested while the page
 *  loaded; `shards` is the table's data-shards marker once it was idle. */
export function openingFetchProblem(requests, shards) {
  if (requests.length === 1 && requests[0] === `/json/${YEARS_CORE}` && shards === "core") {
    return null;
  }
  return (
    `opening /years/ fetched [${requests.join(", ")}] (data-shards="${shards}"); ` +
    `it must fetch only /json/${YEARS_CORE} until a reader asks for a lazy column or project row`
  );
}

/**
 * Open /years/ at `baseUrl` and report what it fetched before anyone touched
 * it — leg (k)'s probe, exported so the release can run it against
 * production (`node -e "import('./scripts/gates/yearsmatrix.mjs').then(async
 * (m) => console.log(await m.probeYearsOpeningFetches('https://fiscalreceipts.com')))"`).
 */
export async function probeYearsOpeningFetches(baseUrl) {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    const requests = [];
    page.on("request", (req) => {
      const u = new URL(req.url());
      if (u.pathname.startsWith("/json/years_matrix")) requests.push(u.pathname);
    });
    await page.goto(`${baseUrl}/years/`, { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForSelector('[data-testid="years-matrix"][aria-busy="false"]', {
      timeout: 30000,
    });
    const shards = await page
      .locator('[data-testid="years-matrix"]')
      .getAttribute("data-shards");
    return { requests, shards, problem: openingFetchProblem(requests, shards) };
  } finally {
    await browser.close();
  }
}
```

**Edit 15.4** — load through the loader — `site/scripts/gates/yearsmatrix.mjs` (anchor on the quoted text). Replace this exact text:

```js
  // ── Load static inputs ────────────────────────────────────────────────────
  const matrixPath = path.join(jsonDir, "years_matrix.json");
  if (!fs.existsSync(matrixPath)) {
    return {
      pass: false,
      errors: [`years_matrix.json missing at ${matrixPath} — run export-site`],
      notes,
    };
  }
  const matrix = readJson(matrixPath);
  const citations = readJson(path.join(jsonDir, "citations.json"));

  const size = fs.statSync(matrixPath).size;
  // Payload budget: ~1.6–2KB/program. Raised 900KB → 2MB in Phase 5G when the
  // Navy FY2026 J-book ingestion grew the detail-grade matrix from ~462 to 813
  // programs (~1.53MB). Raised 2MB → 4MB in the Phase 5G Army/AF/SF archive
  // round: the matrix grew 813 → 1,741 programs (~2.74MB) at the SAME
  // per-program density — legitimate corpus growth, not design regression.
  // Still catches runaway bloat (a doubling from here, 1,741 → ~2,540+).
  if (size >= 4096 * 1024) {
    errors.push(`years_matrix.json is ${size} bytes — over the 4MB budget`);
  }
  const nPrograms = [...iterPrograms(matrix)].length;
  notes.push(`matrix: ${nPrograms} programs / ${matrix.orgs.length} orgs / ${size} bytes`);
```

with:

```js
  // ── Load static inputs: the core and its two shards, merged (#193) ──────
  let loaded;
  try {
    loaded = loadYearsMatrix(jsonDir);
  } catch (e) {
    return { pass: false, errors: [`years matrix: ${e.message}`], notes };
  }
  const { matrix, files } = loaded;
  const citations = readJson(path.join(jsonDir, "citations.json"));

  // Size (Q11): every file ≤ 4 MiB on disk, the core ≤ 780,074 B at gzip -9.
  // The per-file cap is the Phase 5G 4 MB budget, now per file; the core
  // budget is what the single pre-split file cost a reader on open.
  checkYearsFileBudgets(files, errors, notes);
  const nPrograms = [...iterPrograms(matrix)].length;
  notes.push(`matrix: ${nPrograms} programs / ${matrix.orgs.length} orgs`);
```

**Edit 15.5** — legs f and g sample era cells — `site/scripts/gates/yearsmatrix.mjs` (anchor on the quoted text). Replace this exact text:

```js
      const samples = sampleDecadeCells(matrix);
      const colsCovered = new Set(samples.map((s) => s.col.key));
```

with:

```js
      const samples = [
        ...sampleDecadeCells(matrix),
        ...sampleEraCells(matrix, citations),
      ];
      const colsCovered = new Set(samples.map((s) => s.col.key));
      // split rows' own (account, org), for leg g's era pins
      const members = new Map(
        readJson(path.join(jsonDir, "programs.json")).map((p) => [
          p.slug,
          { account: p.account, org: p.org },
        ]),
      );
```

**Edit 15.6** — leg g through the map — `site/scripts/gates/yearsmatrix.mjs` (anchor on the quoted text). Replace this exact text:

```js
          okF++;
          // Leg (g): sources must all sit in the column's STATED edition,
          // belong to the cell's pe_bli, and a workbook citation's sha256
          // must be among its lake rows' documents (spec §2 rule 1).
          const fys = new Set(rows.flatMap((r) => r.fys));
          const pes = new Set(rows.flatMap((r) => r.pes));
          if (fys.size !== 1 || !fys.has(s.col.edition)) {
            errors.push(
              `leg g: decade cell ${s.pe_bli}/${s.col.key} sources span edition(s) [${[...fys].join(",")}] != stated PB${s.col.edition}`
            );
            continue;
          }
          if (pes.size !== 1 || !pes.has(s.pe_bli)) {
            errors.push(
              `leg g: decade cell ${s.pe_bli}/${s.col.key} sources span pe_bli(s) [${[...pes].join(",")}]`
            );
            continue;
          }
          if (
            cit.kind === "workbook" &&
            !rows.some((r) => (r.shas ?? []).includes(cit.sha256))
          ) {
            errors.push(
              `leg g: decade cell ${s.pe_bli}/${s.col.key} citation sha256 not among its lake rows`
            );
            continue;
          }
          okG++;
        }
        notes.push(
          `leg f: ${okF}/${checks.length} decade cells recomputed from budget_lines_decade.parquet across ${colsCovered.size} columns ✓`
        );
        notes.push(`leg g: ${okG}/${checks.length} decade cells edition-integrity verified ✓`);
```

with:

```js
          okF++;
          // Leg (g): sources must all sit in the column's STATED edition,
          // belong to the cell's row — directly, or for an era cell through
          // the reviewed era map — and a workbook citation's sha256 must be
          // among its lake rows' documents (spec §2 rule 1; #193).
          const problem = decadeSourceProblem(s, cit, rows, members);
          if (problem) {
            errors.push(`leg g: ${problem}`);
            continue;
          }
          okG++;
          if (s.era) eraVerified.add(`${s.col.edition}|${s.era}`);
        }
        notes.push(
          `leg f: ${okF}/${checks.length} decade cells recomputed from budget_lines_decade.parquet across ${colsCovered.size} columns ✓`
        );
        notes.push(`leg g: ${okG}/${checks.length} decade cells edition-integrity verified ✓`);
        // Non-vacuity (#193): an era leaf and an era-map sum verified in
        // every PB2017–PB2023 edition the grid carries.
        const eraEditions = [
          ...new Set(
            (matrix.decade_columns ?? [])
              .map((c) => c.edition)
              .filter((e) => e <= LAST_ERA_EDITION),
          ),
        ].sort((a, b) => a - b);
        const unproven = eraEditions.flatMap((e) =>
          ["leaf", "sum"].filter((k) => !eraVerified.has(`${e}|${k}`)).map((k) => `PB${e} ${k}`),
        );
        if (eraEditions.length === 0 || unproven.length > 0) {
          errors.push(
            `leg g is VACUOUS for era procurement: no verified ${unproven.join(", ") || "era edition at all"}`
          );
        } else {
          notes.push(
            `leg g: an era leaf and an era-map sum verified through p1_era_line_map in each of PB${eraEditions[0]}–PB${eraEditions.at(-1)} ✓`
          );
        }
```

**Edit 15.7** — leg f/g era tally — `site/scripts/gates/yearsmatrix.mjs` (anchor on the quoted text). Replace this exact text:

```js
      let dec = null;
      if (wanted.size > 0) {
```

with:

```js
      const eraVerified = new Set();
      let dec = null;
      if (wanted.size > 0) {
```

**Edit 15.8** — leg j call — `site/scripts/gates/yearsmatrix.mjs` (anchor on the quoted text). Replace this exact text:

```js
  // ── Leg (d): shard integrity ──────────────────────────────────────────────
```

with:

```js
  // ── Leg (j): sidecar parity (#193) ────────────────────────────────────────
  runSidecarParityLeg(matrix, jsonDir, errors, notes);

  // ── Leg (d): shard integrity ──────────────────────────────────────────────
```

**Edit 15.9** — request recorder — `site/scripts/gates/yearsmatrix.mjs` (anchor on the quoted text). Replace this exact text:

```js
    const consoleErrors = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });
```

with:

```js
    const consoleErrors = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });
    // Leg (k): every /json/years_matrix* request, from the first navigation.
    const yearsRequests = [];
    page.on("request", (req) => {
      const u = new URL(req.url());
      if (u.pathname.startsWith("/json/years_matrix")) yearsRequests.push(u.pathname);
    });
```

**Edit 15.10** — leg k — `site/scripts/gates/yearsmatrix.mjs` (anchor on the quoted text). Replace this exact text:

```js
    if (pageUp) {
      // ---- honesty-marker legend near the table controls (strengthened) ----
```

with:

```js
    if (pageUp) {
      // ---- leg k: the opening view fetched the core and nothing else ----
      {
        await page
          .waitForSelector('[data-testid="years-matrix"][aria-busy="false"]', { timeout: 15000 })
          .catch(() => null);
        const shards = await page
          .locator('[data-testid="years-matrix"]')
          .getAttribute("data-shards");
        const problem = openingFetchProblem([...yearsRequests], shards);
        if (problem) errors.push(`leg k: ${problem}`);
        else notes.push('leg k: /years/ opened on the core alone (data-shards="core") ✓');
      }

      // ---- honesty-marker legend near the table controls (strengthened) ----
```

**Edit 15.11** — i3 reveal waits for the grid — `site/scripts/gates/yearsmatrix.mjs` (anchor on the quoted text). Replace this exact text:

```js
              await showChip.first().click({ timeout: 10000 });
              const th = page.locator(`th[data-col="${col.key}"]`).first();
              await th.waitFor({ state: "attached", timeout: 10000 });
```

with:

```js
              await showChip.first().click({ timeout: 10000 });
              // The column joins once its shard has merged (#193).
              const th = page.locator(`th[data-col="${col.key}"]`).first();
              await th.waitFor({ state: "attached", timeout: 15000 });
              await page.waitForSelector(
                '[data-testid="years-matrix"][aria-busy="false"]',
                { timeout: 15000 },
              );
```

**Edit 15.12** — expand waits for detail.json — `site/scripts/gates/yearsmatrix.mjs` (anchor on the quoted text). Replace this exact text:

```js
          await caret.click();
          await page.waitForTimeout(400);
          const after = await page.locator("tr[data-project-row]:visible").count();
```

with:

```js
          await caret.click();
          // Project rows ship in detail.json (#193): wait for it to merge.
          await page
            .locator('[data-testid="years-matrix"][data-shards~="detail"][aria-busy="false"]')
            .waitFor({ timeout: 15000 })
            .catch(() => null);
          const after = await page.locator("tr[data-project-row]:visible").count();
```

**Edit 15.13** — delta chip waits for its column — `site/scripts/gates/yearsmatrix.mjs` (anchor on the quoted text). Replace this exact text:

```js
              await chip.click();
              await page.waitForTimeout(300);
            }
          }
```

with:

```js
              await chip.click();
              // The Δ column joins once detail.json has merged (#193).
              await page
                .locator('th[data-col="fy2526_change"]')
                .first()
                .waitFor({ state: "attached", timeout: 15000 })
                .catch(() => null);
            }
          }
```

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site || exit 1
npx vitest run scripts/gates/__tests__/years-matrix-gate.test.mjs
npx eslint scripts/gates/yearsmatrix.mjs scripts/gates/years-matrix-load.mjs scripts/gates/__tests__/years-matrix-gate.test.mjs
```

Expected: `Tests  26 passed (26)` (loader 6, size 2, leg g 10, leg j 5, leg k 3);
eslint prints nothing.

- [ ] **Step 3: Give leg g the era map — the recompute helper**

Create `tests/test_yearsmatrix_recompute.py`:

```python
"""site/scripts/gates/yearsmatrix-recompute.py — the era join gate 20 leg g
reads (ROADMAP #193, families piece-1 follow-ups design §3.6).

Since the /years/ era fence lifted, a PB2017–PB2023 procurement cell's lake
rows carry an era key ('0300D-DCSA-L5'), not the row's code. The helper hands
the gate, per decade fact, the p1_era_line_map row of every era-keyed lake row
(by edition = fiscal_year and era_key = pe_bli), so the gate can prove the
cell reaches its program only through a reviewed same_program decision. Run
against a fixture data directory, never data/site.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb

HELPER = (
    Path(__file__).resolve().parents[1]
    / "site" / "scripts" / "gates" / "yearsmatrix-recompute.py"
)


def _fixture(data_dir: Path) -> None:
    con = duckdb.connect()
    d = str(data_dir).replace("'", "''")
    con.execute(
        "copy (select 'p' as pe_bli, 'A' as organization, 'fy_2024_actuals' as"
        " amount_type, 'Line' as title, 1.0 as amount_thousands)"
        f" to '{d}/budget_lines.parquet' (format parquet)"
    )
    con.execute(
        "copy (select 'p' as pe_bli, 'P1' as project_number, 'PriorYear' as"
        f" scenario, 1.0 as amount_millions) to '{d}/jbook_details.parquet'"
        " (format parquet)"
    )
    con.execute(
        "copy (select * from (values"
        " ('aaaa000000000001', 2019, '0300D-DCSA-L5', 1057.0, 'sha_p1_19'),"
        " ('aaaa000000000002', 2019, '0300D-DCAA-L1', 25.0, 'sha_p1_19'),"
        " ('aaaa000000000003', 2026, '20', 2135.0, 'sha_p1_26'),"
        " ('aaaa000000000004', 2018, '0300D-DCSA-L5', 1000.0, 'sha_p1_18')"
        ") t(fact_id, fiscal_year, pe_bli, amount_thousands, document_sha256))"
        f" to '{d}/budget_lines_decade.parquet' (format parquet)"
    )
    con.execute(
        "copy (select * from (values"
        " (2019, '0300D-DCSA-L5', '20', 'same_program', '0300D', 'DCSA'),"
        " (2019, '0300D-DCAA-L1', '20', 'history_only', '0300D', 'DCAA')"
        ") t(edition, era_key, program_key, decision, program_account, program_org))"
        f" to '{d}/p1_era_line_map.parquet' (format parquet)"
    )
    con.close()


def _run(tmp_path: Path, fids: list[str]) -> dict:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _fixture(data_dir)
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"decade_fids": fids}))
    res = subprocess.run(
        [sys.executable, str(HELPER), str(request), str(data_dir)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(res.stdout)["decade"]


def test_an_era_row_carries_its_map_row(tmp_path):
    out = _run(tmp_path, ["aaaa000000000001", "aaaa000000000002"])
    assert out["aaaa000000000001"] == {
        "v": 1057.0, "n": 1, "fys": [2019], "pes": ["0300D-DCSA-L5"],
        "shas": ["sha_p1_19"],
        "era": [{
            "era_key": "0300D-DCSA-L5", "program_key": "20",
            "decision": "same_program", "program_account": "0300D",
            "program_org": "DCSA",
        }],
    }
    assert out["aaaa000000000002"]["era"][0]["decision"] == "history_only"


def test_a_native_row_carries_no_era_entry(tmp_path):
    out = _run(tmp_path, ["aaaa000000000003"])
    assert out["aaaa000000000003"]["pes"] == ["20"]
    assert out["aaaa000000000003"]["era"] == []


def test_an_era_row_the_map_does_not_name_is_listed_with_nulls(tmp_path):
    """The map has no PB2018 row for the key: the gate must see that, not
    an empty list it would read as a native row."""
    out = _run(tmp_path, ["aaaa000000000004"])
    assert out["aaaa000000000004"]["era"] == [{
        "era_key": "0300D-DCSA-L5", "program_key": None, "decision": None,
        "program_account": None, "program_org": None,
    }]


def test_an_unknown_fact_is_null(tmp_path):
    assert _run(tmp_path, ["ffff000000000000"]) == {"ffff000000000000": None}
```

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && uv run --project . pytest tests/test_yearsmatrix_recompute.py -q
```

Expected: `4 failed` — each a `subprocess.CalledProcessError` (exit status 2:
the helper accepts one argument and prints its usage).

**Edit 15.14** — docstring — `site/scripts/gates/yearsmatrix-recompute.py`. Replace this exact text:

```python
Invoked by site/scripts/gates/yearsmatrix.mjs:
    uv run python site/scripts/gates/yearsmatrix-recompute.py <request.json>
```

with:

```python
Invoked by site/scripts/gates/yearsmatrix.mjs:
    uv run python site/scripts/gates/yearsmatrix-recompute.py <request.json> [site_data_dir]

site_data_dir defaults to data/site/data (tests pass a fixture directory).
```

**Edit 15.15** — response doc — `site/scripts/gates/yearsmatrix-recompute.py`. Replace this exact text:

```python
      "decade":   {"{fact_id}": {"v": float, "n": int, "fys": [int],
                                 "pes": [str], "shas": [str]} | null}
    }
```

with:

```python
      "decade":   {"{fact_id}": {"v": float, "n": int, "fys": [int],
                                 "pes": [str], "shas": [str],
                                 "era": [{"era_key", "program_key",
                                          "decision", "program_account",
                                          "program_org"}]} | null}
    }
```

**Edit 15.16** — era doc — `site/scripts/gates/yearsmatrix-recompute.py`. Replace this exact text:

```python
behind the fact. The gate checks the value against the payload cell AND
that every source row's edition equals the column's stated edition.
"""
```

with:

```python
behind the fact. The gate checks the value against the payload cell AND
that every source row's edition equals the column's stated edition.
Era rows (ROADMAP #193): a row whose pe_bli is an era procurement key
('3020F-AF-L8') is listed under "era" with its p1_era_line_map row for
(edition = fiscal_year, era_key = pe_bli) — program_key and decision null
when the map has none — so the gate can prove the cell reaches its program
through a reviewed decision.
"""
```

**Edit 15.17** — imports and paths — `site/scripts/gates/yearsmatrix-recompute.py`. Replace this exact text:

```python
from govbudget.config import ROOT
from govbudget.jbooks.orgs import workbook_org

BL_PARQUET = ROOT / "data" / "site" / "data" / "budget_lines.parquet"
JD_PARQUET = ROOT / "data" / "site" / "data" / "jbook_details.parquet"
DEC_PARQUET = ROOT / "data" / "site" / "data" / "budget_lines_decade.parquet"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: yearsmatrix-recompute.py <request.json>", file=sys.stderr)
        return 2
    request = json.loads(Path(sys.argv[1]).read_text())
```

with:

```python
from govbudget.config import ROOT
from govbudget.jbooks.era_keys import is_era_procurement_key
from govbudget.jbooks.orgs import workbook_org


def main() -> int:
    if len(sys.argv) not in (2, 3):
        print(
            "usage: yearsmatrix-recompute.py <request.json> [site_data_dir]",
            file=sys.stderr,
        )
        return 2
    request = json.loads(Path(sys.argv[1]).read_text())
    data_dir = Path(sys.argv[2]) if len(sys.argv) == 3 else ROOT / "data" / "site" / "data"
    BL_PARQUET = data_dir / "budget_lines.parquet"
    JD_PARQUET = data_dir / "jbook_details.parquet"
    DEC_PARQUET = data_dir / "budget_lines_decade.parquet"
    MAP_PARQUET = data_dir / "p1_era_line_map.parquet"
```

**Edit 15.18** — era join — `site/scripts/gates/yearsmatrix-recompute.py`. Replace this exact text:

```python
    decade_fids = request.get("decade_fids", [])
    out["decade"] = {}
    if decade_fids:
        if not DEC_PARQUET.exists():
            print(f"decade parquet missing: {DEC_PARQUET}", file=sys.stderr)
            return 2
        dec = str(DEC_PARQUET).replace("'", "''")
        for fid in decade_fids:
            rows = con.execute(
                f"select amount_thousands, fiscal_year, pe_bli, document_sha256"
                f" from read_parquet('{dec}') where fact_id = ?",
                [fid],
            ).fetchall()
            if not rows or any(r[0] is None for r in rows):
                out["decade"][fid] = None
                continue
            out["decade"][fid] = {
                "v": float(sum(r[0] for r in rows)),
                "n": len(rows),
                "fys": sorted({int(r[1]) for r in rows}),
                "pes": sorted({r[2] for r in rows}),
                "shas": sorted({r[3] for r in rows}),
            }
```

with:

```python
    decade_fids = request.get("decade_fids", [])
    out["decade"] = {}
    if decade_fids:
        for needed in (DEC_PARQUET, MAP_PARQUET):
            if not needed.exists():
                print(f"decade recompute input missing: {needed}", file=sys.stderr)
                return 2
        dec = str(DEC_PARQUET).replace("'", "''")
        emap = str(MAP_PARQUET).replace("'", "''")
        for fid in decade_fids:
            rows = con.execute(
                f"select d.amount_thousands, d.fiscal_year, d.pe_bli,"
                f" d.document_sha256, m.program_key, m.decision,"
                f" m.program_account, m.program_org"
                f" from read_parquet('{dec}') d"
                f" left join read_parquet('{emap}') m"
                f" on m.edition = d.fiscal_year and m.era_key = d.pe_bli"
                f" where d.fact_id = ?",
                [fid],
            ).fetchall()
            if not rows or any(r[0] is None for r in rows):
                out["decade"][fid] = None
                continue
            out["decade"][fid] = {
                "v": float(sum(r[0] for r in rows)),
                "n": len(rows),
                "fys": sorted({int(r[1]) for r in rows}),
                "pes": sorted({r[2] for r in rows}),
                "shas": sorted({r[3] for r in rows}),
                "era": [
                    {
                        "era_key": r[2],
                        "program_key": r[4],
                        "decision": r[5],
                        "program_account": r[6],
                        "program_org": r[7],
                    }
                    for r in rows
                    if is_era_procurement_key(r[2])
                ],
            }
```

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
uv run --project . pytest tests/test_yearsmatrix_recompute.py -q
uvx --offline ruff check --isolated --select F,E9 site/scripts/gates/yearsmatrix-recompute.py tests/test_yearsmatrix_recompute.py
```

Expected: `4 passed`; ruff `All checks passed!`.

- [ ] **Step 4: Leg j on today's export (read-only of `data/site`)**

The gate itself runs on Task 21's exports; this step shows leg j's teeth on
the live export, which still carries piece 1's fence. It splits
`data/site/json/years_matrix.json` with Task 13's code into a scratch
directory under `$GOVBUDGET_PROOFS`, loads it through the gate's loader and
runs the size and parity legs against the live sidecars. It reads only JSON
under `data/site/json` (no lake, no DuckDB), so it needs no SAM-window guard,
and it writes only the scratch directory, which it removes.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
SPLIT="${GOVBUDGET_PROOFS:?}/fu-t15-years-split"
rm -rf "${SPLIT:?}" && mkdir -p "$SPLIT"
uv run --project . python - "$SPLIT" <<'PY'
import json, os, sys
from pathlib import Path
from govbudget import export_site as es
src = Path(os.environ["GOVBUDGET_DATA"]) / "site" / "json" / "years_matrix.json"
print(es._write_years_matrix_files(Path(sys.argv[1]), es.split_years_matrix(json.loads(src.read_text()))))
PY
cd site && node --input-type=module -e "
import { loadYearsMatrix } from './scripts/gates/years-matrix-load.mjs';
import { runSidecarParityLeg, checkYearsFileBudgets } from './scripts/gates/yearsmatrix.mjs';
const { matrix, files } = loadYearsMatrix(process.argv[1]);
const errors = [];
const notes = [];
checkYearsFileBudgets(files, errors, notes);
runSidecarParityLeg(matrix, process.env.GOVBUDGET_DATA + '/site/json', errors, notes);
for (const line of [...notes, ...errors]) console.log(line.slice(0, 240));
" "$SPLIT"
rm -rf "${SPLIT:?}"
```

Expected (measured 2026-10-13 on the 2026-10-04 export):
```
{'years_matrix/decade.json': 900935, 'years_matrix/detail.json': 1231643, 'years_matrix.json': 855969}
size: years_matrix.json 855969 B (263763 gzip); years_matrix/decade.json 900935 B (278811 gzip); years_matrix/detail.json 1231643 B (284232 gzip)
leg j: 15048 cell(s) the program page has and /years/ does not: 0023A01001/fy2015a (PB2017, fid 2d964af966f8f5e1) | 0023A01001/fy2016a (PB2018, fid 9ba2e40da6f3c7b1) | 0023A01001/fy2016e (PB2017, fid 921c4dab3b9fe28b) | 0023A01001/fy2017a (
```
15,048 = the 14,985 era cells the fence dropped plus the 63 PB2024–PB2026
cells of the seven organization-split rows (#207); 5,030 of them are in the
default view (4,995 era plus 35 modern). After Task 22's export leg j must
read `0 missing, 0 extra`.

- [ ] **Step 5: The Q13 clause on /methodology/**

Create `site/src/__tests__/methodology-years-matrix-gap.test.ts`:

```ts
/**
 * /methodology/ #coverage-years-matrix — what a "–" on /years/ means
 * (families piece-1 follow-ups design §3.7, owner Q13; ROADMAP #193, #206 T4).
 *
 * The clause said an absent cell meant "the trajectory workbook simply has no
 * row for that program and column". For a decade column the source is the
 * edition workbook the column states, and since the era fence lifted every
 * /years/ row carries exactly its program page's decade points (gate 20 leg j),
 * so the clause names the edition workbook — at the replaced clause's exact
 * length (69 bytes, no ' or &, so the escaped HTML is as long too):
 * /methodology/ sits near its gate-1 ceiling.
 */
import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";

const PAGE = path.resolve(__dirname, "..", "app", "methodology", "page.tsx");

const OLD_CLAUSE = "the trajectory workbook simply has no row for that program and column";
const NEW_CLAUSE = "the edition workbook simply holds no line for that program and column";

/** Rendered text of the JSX between two markers: {" "} is a space, tags drop,
 *  whitespace collapses, &amp; is &. */
function visible(start: string, end: string): string {
  const src = fs.readFileSync(PAGE, "utf8");
  const a = src.indexOf(start);
  const b = src.indexOf(end, a + start.length);
  expect(a, `marker not found: ${start}`).toBeGreaterThan(-1);
  expect(b, `marker not found: ${end}`).toBeGreaterThan(a);
  return src
    .slice(a, b)
    .replaceAll('{" "}', " ")
    .replace(/<[^>]+>/g, "")
    .replace(/\s+/g, " ")
    .replaceAll("&amp;", "&")
    .trim();
}

describe("/methodology/ #coverage-years-matrix absent-cell clause", () => {
  const clause = visible("is <em>absent</em>:", "(most");

  it("names the edition workbook as the source an absent cell is silent in", () => {
    expect(clause).toBe(`is absent: ${NEW_CLAUSE}`);
  });

  it("no longer names the trajectory workbook", () => {
    expect(fs.readFileSync(PAGE, "utf8").replace(/\s+/g, " ")).not.toContain(OLD_CLAUSE);
  });

  it("is exactly as long as the clause it replaced, and needs no escaping", () => {
    expect(Buffer.byteLength(OLD_CLAUSE)).toBe(69);
    expect(Buffer.byteLength(NEW_CLAUSE)).toBe(69);
    expect(NEW_CLAUSE).not.toMatch(/['&"<>]/);
  });
});
```

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site && npx vitest run src/__tests__/methodology-years-matrix-gap.test.ts
```

Expected: `Tests  2 failed | 1 passed (3)` — the clause still names the
trajectory workbook.

**Edit 15.28** — Q13 clause — `site/src/app/methodology/page.tsx`. Replace this exact text:

```tsx
                  things. &ldquo;–&rdquo; is <em>absent</em>: the trajectory
                  workbook simply has no row for that program and column (most
```

with:

```tsx
                  things. &ldquo;–&rdquo; is <em>absent</em>: the edition
                  workbook simply holds no line for that program and column (most
```

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site && npx vitest run src/__tests__/methodology-years-matrix-gap.test.ts src/__tests__/methodology-era-sentence.test.ts
```

Expected: `Tests  8 passed (8)` (3 + the 5 era-sentence pins beside it).
Weight, measured by substitution on `site/out/methodology/index.html` (built
2026-10-04, the clause appears twice: SSR and RSC) with gate 1's own
`weigh()` (node zlib, level 9): raw 161,353 → 161,353, gzip 45,338 → 45,332
against the 162,000 / 45,400 ceiling. Task 21 re-stamps the page on the real
build; no ceiling moves.

- [ ] **Step 6: linkgraph's static fetch-target floor is the measured six**

**Edit 15.30** — import the floor — `site/scripts/gates/__tests__/fetch-targets.test.mjs`. Replace this exact text:

```js
import {
  runJsonXmlHrefLeg,
  sameOriginJsonXmlTarget,
```

with:

```js
import {
  MIN_STATIC_FETCH_TARGETS,
  runJsonXmlHrefLeg,
  sameOriginJsonXmlTarget,
```

**Edit 15.31** — pin the floor — `site/scripts/gates/__tests__/fetch-targets.test.mjs`. Replace this exact text:

```js
  it("does not pick targets out of test files' fetch mocks", () => {
```

with:

```js
  it("floors the static scan at exactly the population it measures (ROADMAP #193)", () => {
    expect(MIN_STATIC_FETCH_TARGETS).toBe(scanFetchTargets(srcDir).size);
  });

  it("does not pick targets out of test files' fetch mocks", () => {
```

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site && npx vitest run scripts/gates/__tests__/fetch-targets.test.mjs
```

Expected: `Tests  1 failed | 32 passed (33)` — `floors the static scan at
exactly the population it measures (ROADMAP #193)`, `expected undefined to be
6` (the floor is not exported yet).

**Edit 15.19** — floor — `site/scripts/gates/linkgraph.mjs`. Replace this exact text:

```js
/** Non-vacuity floor for the static fetch-target scan. Measured 2026-09-04
 *  at FIVE; RE-MEASURED 2026-09-05 (ROADMAP #88) at FOUR — /config.json,
 *  /json/flow_chart.json, /json/years_matrix.json,
 *  /json-lite/search_quick.json — because the client genuinely stopped
 *  fetching /json/feed.json (FeedSectionExpand now fetches the
 *  directory-templated /json/feed-sections/${eventType}.json, floored
 *  separately by MIN_TEMPLATED_FETCH_DIRS so neither floor can backfill the
 *  other). Below this the scanner has stopped matching (a fetch wrapper, a
 *  moved file, a regex regression) and the leg would report "all targets
 *  resolve" while checking none — the state in which /json/feed.json 404'd
 *  in production. RE-MEASURE if the client stops fetching one of these; do
 *  not lower it to fit. */
const MIN_STATIC_FETCH_TARGETS = 4;
```

with:

```js
/** Non-vacuity floor for the static fetch-target scan. Measured 2026-09-04
 *  at FIVE; RE-MEASURED 2026-09-05 (ROADMAP #88) at FOUR — /config.json,
 *  /json/flow_chart.json, /json/years_matrix.json,
 *  /json-lite/search_quick.json — because the client genuinely stopped
 *  fetching /json/feed.json (FeedSectionExpand now fetches the
 *  directory-templated /json/feed-sections/${eventType}.json, floored
 *  separately by MIN_TEMPLATED_FETCH_DIRS so neither floor can backfill the
 *  other). RE-MEASURED for ROADMAP #193 at SIX: the /years/ island also
 *  fetches its two lazy shards, /json/years_matrix/decade.json and
 *  /json/years_matrix/detail.json, by literal URL (a floor, so this
 *  tightens it). Below this the scanner has stopped matching (a fetch
 *  wrapper, a moved file, a regex regression) and the leg would report "all
 *  targets resolve" while checking none — the state in which
 *  /json/feed.json 404'd in production. RE-MEASURE if the client stops
 *  fetching one of these; do not lower it to fit. Exported for
 *  scripts/gates/__tests__/fetch-targets.test.mjs, which pins it to the
 *  population it floors. */
export const MIN_STATIC_FETCH_TARGETS = 6;
```

**Edit 15.20** — floor message — `site/scripts/gates/linkgraph.mjs`. Replace this exact text:

```js
        `under site/src (floor ${MIN_STATIC_FETCH_TARGETS}: measured 2026-09-04 ` +
        `at 5, re-measured 2026-09-05 at 4, ROADMAP #88). The scanner has ` +
```

with:

```js
        `under site/src (floor ${MIN_STATIC_FETCH_TARGETS}: measured 2026-09-04 ` +
        `at 5, re-measured 2026-09-05 at 4 (ROADMAP #88) and at 6 for the ` +
        `/years/ shards (ROADMAP #193)). The scanner has ` +
```

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site || exit 1
npx vitest run scripts/gates/__tests__/fetch-targets.test.mjs
npx eslint scripts/gates/linkgraph.mjs scripts/gates/__tests__/fetch-targets.test.mjs
```

Expected: `Tests  33 passed (33)`; eslint prints nothing.

- [ ] **Step 7: The post-deploy probe checks the core and every shard it lists**

**Edit 15.24** — fixture routes — `tests/test_launch_deploy_landing.py`. Replace this exact text:

```python
    routes["/json/years_matrix.json"] = (200, b"{}", "application/json")
```

with:

```python
    # ROADMAP #193: the /years/ core and the one shard it lists, one build.
    for path, body in _years_files("b" * 64).items():
        routes[path] = (200, body, "application/json")
```

**Edit 15.25** — helper — `tests/test_launch_deploy_landing.py`. Replace this exact text:

```python
@pytest.fixture()
def landed(tmp_path: Path, mock_host):
```

with:

```python
def _years_files(build_id: str, *, shard_build_id: str | None = None) -> dict[str, bytes]:
    """A /years/ core whose manifest lists one shard, and that shard."""
    shard = json.dumps({
        "schema_version": 2, "build_id": shard_build_id or build_id,
        "shard": "decade", "columns": [], "rows": {},
    }).encode()
    core = json.dumps({
        "schema_version": 2, "build_id": build_id, "orgs": [],
        "shards": [{
            "name": "decade", "path": "years_matrix/decade.json", "columns": [],
            "bytes": len(shard), "sha256": hashlib.sha256(shard).hexdigest(),
        }],
    }).encode()
    return {"/json/years_matrix.json": core, "/json/years_matrix/decade.json": shard}


@pytest.fixture()
def landed(tmp_path: Path, mock_host):
```

**Edit 15.26** — landed passes probes years — `tests/test_launch_deploy_landing.py`. Replace this exact text:

```python
    assert "PASS: /.build-meta.json build — built_at 2026-09-26T22:36:02.525Z" in r.stdout
```

with:

```python
    assert "PASS: /.build-meta.json build — built_at 2026-09-26T22:36:02.525Z" in r.stdout
    assert "PASS: /json/years_matrix.json — build_id bbbbbbbbbbbb…, 1 shard(s) listed" in r.stdout
    assert "PASS: /json/years_matrix/decade.json" in r.stdout
```

Then append to the end of `tests/test_launch_deploy_landing.py`, two blank
lines after its last line:

```python
# ---------------------------------------------------------------------------
# Assertion 8 (ROADMAP #193): the /years/ core and its shards are one build
# ---------------------------------------------------------------------------


def test_a_years_shard_from_another_build_fails(landed):
    root, head, meta, host, run = landed
    for path, body in _years_files("b" * 64, shard_build_id="c" * 64).items():
        host.routes[path] = (200, body, "application/json")
    r = run()
    assert r.returncode == 1, r.stdout
    assert f"FAIL: /json/years_matrix/decade.json — build_id {'c' * 64} != the core's {'b' * 64}" in r.stdout


def test_a_years_shard_that_differs_from_the_manifest_fails(landed):
    root, head, meta, host, run = landed
    host.routes["/json/years_matrix/decade.json"] = (200, b'{"build_id": "x"}', "application/json")
    r = run()
    assert r.returncode == 1, r.stdout
    assert "FAIL: /json/years_matrix/decade.json — sha256" in r.stdout


def test_a_pre_split_years_matrix_fails(landed):
    root, head, meta, host, run = landed
    host.routes["/json/years_matrix.json"] = (200, b'{"schema_version": 1}', "application/json")
    r = run()
    assert r.returncode == 1, r.stdout
    assert "FAIL: /json/years_matrix.json — no build_id or shard manifest (schema_version 1)" in r.stdout


def test_a_missing_years_shard_fails(landed):
    root, head, meta, host, run = landed
    del host.routes["/json/years_matrix/decade.json"]
    r = run()
    assert r.returncode == 1, r.stdout
    assert "FAIL: /json/years_matrix/decade.json — HTTP 404" in r.stdout
```

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && uv run --project . pytest tests/test_launch_deploy_landing.py -q
```

Expected: `5 failed, 29 passed` — `test_a_deploy_that_landed_passes` (no
`PASS: /json/years_matrix.json — build_id …` line) and the four new tests
(the old probe only checks that `/json/years_matrix.json` answers 200 with a
body, so every one of them exits 0).

**Edit 15.21** — assertion doc — `scripts/launch/verify_live_assets.mjs`. Replace this exact text:

```js
 *      broken source link #191 was. Skipped with --skip-site.
 *
 * USAGE
```

with:

```js
 *      broken source link #191 was. Skipped with --skip-site.
 *   8. THE /years/ FILES BELONG TOGETHER (ROADMAP #193). /json/years_matrix.json
 *      is the core of a split matrix: it must parse and carry a build_id and
 *      a shard manifest, and every shard it lists
 *      (/json/years_matrix/decade.json, /json/years_matrix/detail.json) must
 *      answer 200 with the manifest's sha256 and the core's build_id. A shard
 *      left over from another deployment would leave a reader's column
 *      showing an error. Skipped with --skip-site.
 *
 * USAGE
```

**Edit 15.22** — call — `scripts/launch/verify_live_assets.mjs`. Replace this exact text:

```js
    await checkUrl("/json/years_matrix.json", `${siteBase}/json/years_matrix.json`);
```

with:

```js
    await checkYearsMatrix();
```

**Edit 15.23** — probe — `scripts/launch/verify_live_assets.mjs`. Replace this exact text:

```js
/** Assertion 5 probe: the live object's sha256 and size equal the local file's. */
```

with:

```js
/** Assertion 8 probe: the /years/ core and every shard it lists, from one
 *  build (ROADMAP #193). */
async function checkYearsMatrix() {
  const coreLabel = "/json/years_matrix.json";
  const coreUrl = `${siteBase}/json/years_matrix.json`;
  let core;
  try {
    const res = await fetchWithTimeout(coreUrl, { headers: { "Cache-Control": "no-cache" } });
    if (res.status !== 200) {
      record(false, coreLabel, `HTTP ${res.status} from ${coreUrl}`);
      return;
    }
    core = JSON.parse(Buffer.from(await res.arrayBuffer()).toString("utf8"));
  } catch (e) {
    record(false, coreLabel, `request or parse failed: ${e.message} (${coreUrl})`);
    return;
  }
  if (typeof core.build_id !== "string" || !Array.isArray(core.shards) || core.shards.length === 0) {
    record(false, coreLabel, `no build_id or shard manifest (schema_version ${core.schema_version})`);
    return;
  }
  record(true, coreLabel, `build_id ${core.build_id.slice(0, 12)}…, ${core.shards.length} shard(s) listed`);
  for (const entry of core.shards) {
    const label = `/json/${entry.path}`;
    const url = `${siteBase}/json/${entry.path}`;
    try {
      const res = await fetchWithTimeout(url, { headers: { "Cache-Control": "no-cache" } });
      if (res.status !== 200) {
        record(false, label, `HTTP ${res.status} from ${url}`);
        continue;
      }
      const buf = Buffer.from(await res.arrayBuffer());
      const sha = crypto.createHash("sha256").update(buf).digest("hex");
      const shard = JSON.parse(buf.toString("utf8"));
      if (sha !== entry.sha256) {
        record(false, label, `sha256 ${sha.slice(0, 12)}… != the core manifest's ${String(entry.sha256).slice(0, 12)}…`);
      } else if (shard.build_id !== core.build_id) {
        record(false, label, `build_id ${shard.build_id} != the core's ${core.build_id}`);
      } else {
        record(true, label, `sha256 ${sha.slice(0, 12)}…, the core's build_id`);
      }
    } catch (e) {
      record(false, label, `request or parse failed: ${e.message} (${url})`);
    }
  }
}

/** Assertion 5 probe: the live object's sha256 and size equal the local file's. */
```

**Edit 15.27** — LAUNCH years probe — `docs/superpowers/LAUNCH.md`. Replace this exact text:

```markdown
  `site/out/json/sam/` is fetched in full from the site host and must equal
  the local file's sha256 — a SAM registration citation links nowhere else.

  `--skip-site` skips every site-host check: the build stamp, the `/fact/`
  rewrite and `/json/years_matrix.json` probes, and the SAM receipts.
```

with:

```markdown
  `site/out/json/sam/` is fetched in full from the site host and must equal
  the local file's sha256 — a SAM registration citation links nowhere else;
- **the `/years/` files belong together** (ROADMAP #193): the core,
  `/json/years_matrix.json`, carries a `build_id` and a shard manifest, and
  every shard it lists (`/json/years_matrix/decade.json`,
  `/json/years_matrix/detail.json`) answers 200 with the manifest's sha256
  and the core's `build_id`.

  `--skip-site` skips every site-host check: the build stamp, the `/fact/`
  rewrite probe, the `/years/` probe, and the SAM receipts.
```

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
uv run --project . pytest tests/test_launch_deploy_landing.py -q
uvx --offline ruff check --isolated --select F,E9 tests/test_launch_deploy_landing.py
```

Expected: `34 passed`; ruff `All checks passed!` (as at base).

- [ ] **Step 8: Amend piece-1 spec §6.2 (dated)**

**Edit 15.29** — spec 6.2 amendment — `docs/superpowers/specs/2026-10-02-era-procurement-history-design.md`. Replace this exact text:

```markdown
| `/methodology/` | Live weight is 161,166 / 45,270 gzip against 162,000 / 45,400 (about 130 B gzip of headroom; the build stamp still says 45,147) | One sentence replaced at equal length plus a link (§6.4); everything else goes elsewhere | Build gate passes with the re-measured stamp and no raised ceiling |

### 6.3 Receipts
```

with:

```markdown
| `/methodology/` | Live weight is 161,166 / 45,270 gzip against 162,000 / 45,400 (about 130 B gzip of headroom; the build stamp still says 45,147) | One sentence replaced at equal length plus a link (§6.4); everything else goes elsewhere | Build gate passes with the re-measured stamp and no raised ceiling |

*Amendment (families piece-1 follow-ups, owner decision 2026-10-04: "shard `/years/`
and lift its era fence"; nothing above reworded).* `/years/` is no longer fenced.
ROADMAP #193 split it into a core (`json/years_matrix.json`, schema 2: the header,
every row and the default decade columns) and two lazy shards
(`json/years_matrix/decade.json`, `json/years_matrix/detail.json`) that share its
`build_id`. The 4,194,304 B cap is unchanged and now applies to each file, measured
on the bytes written; the core may not gzip above 780,074 B, what the single file
cost a reader on open. `_emit_years_matrix` no longer takes `era_grain_fids`, and a
`/years/` row now shows exactly its program page's decade points, PB2017–PB2023
procurement included: gate 20 leg j checks that parity, and leg g resolves an era
cell's source rows through `p1_era_line_map`. Lineage funding lines and the F-15
browser stay fenced as above.

### 6.3 Receipts
```

- [ ] **Step 9: Run every touched suite**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site || exit 1
npx vitest run scripts/gates/__tests__ src/__tests__/methodology-years-matrix-gap.test.ts src/__tests__/methodology-era-sentence.test.ts
npx eslint scripts/gates/yearsmatrix.mjs scripts/gates/years-matrix-load.mjs scripts/gates/linkgraph.mjs scripts/gates/__tests__/years-matrix-gate.test.mjs scripts/gates/__tests__/fetch-targets.test.mjs src/__tests__/methodology-years-matrix-gap.test.ts src/app/methodology/page.tsx
cd .. && uv run --project . pytest tests/test_yearsmatrix_recompute.py tests/test_launch_deploy_landing.py -q
```

Expected: `Test Files  47 passed (47)`, `Tests  870 passed (870)` (the gates
suite was 44 files / 835 tests at base: +26 in the new gate test file, +1
fetch-targets pin, plus the two methodology files' 8; more if an earlier task
added gate tests — the criterion is 0 failed); eslint prints nothing; pytest
`38 passed`.

- [ ] **Step 10: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/site/scripts/gates/years-matrix-load.mjs GovBudget/site/scripts/gates/yearsmatrix.mjs GovBudget/site/scripts/gates/yearsmatrix-recompute.py GovBudget/site/scripts/gates/linkgraph.mjs GovBudget/site/scripts/gates/__tests__/years-matrix-gate.test.mjs GovBudget/site/scripts/gates/__tests__/fetch-targets.test.mjs GovBudget/tests/test_yearsmatrix_recompute.py GovBudget/scripts/launch/verify_live_assets.mjs GovBudget/tests/test_launch_deploy_landing.py GovBudget/docs/superpowers/LAUNCH.md GovBudget/site/src/app/methodology/page.tsx GovBudget/site/src/__tests__/methodology-years-matrix-gap.test.ts GovBudget/docs/superpowers/specs/2026-10-02-era-procurement-history-design.md && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "test(gates): /years/ merged-view loader and budgets, leg g through the era map, sidecar parity (j), lazy opening (k); live probe of every shard; Q13 clause (#193, #206 T4)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
