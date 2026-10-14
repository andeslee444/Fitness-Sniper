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
