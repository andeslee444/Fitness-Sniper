/**
 * ROADMAP #193 — the JS merge inverts the Python split.
 *
 * tests/fixtures/years_matrix_split/<name>/ is written by the Python split
 * (export_site.split_years_matrix) and held current by
 * tests/test_export_years_matrix.py::TestCrossLanguageFixture. Here the JS
 * merge — what the /years/ island and the yearsmatrix gate run — must turn
 * those files back into the payload they were split from. Hermetic: the
 * fixtures are committed, nothing reads data/site.
 */
import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";
import {
  mergeYearsMatrix,
  shardOfColumns,
  yearsRowKey,
  YEARS_SHARD_NAMES,
  type YearsMatrixCore,
  type YearsMatrixShard,
} from "@/lib/years-matrix-shards.mjs";
import type { YearsMatrixData } from "@/components/years-matrix";

const FIXTURES = path.resolve(
  __dirname, "..", "..", "..", "tests", "fixtures", "years_matrix_split",
);

function read<T>(...parts: string[]): T {
  return JSON.parse(fs.readFileSync(path.join(FIXTURES, ...parts), "utf8")) as T;
}

/** A payload or merged view without the keys the split adds (design §3.3:
 *  merge(split(p)) == p ignoring schema_version, build_id, shards and np). */
const SPLIT_KEYS = new Set(["schema_version", "build_id", "shards"]);
function strip(view: YearsMatrixData): unknown {
  const without = (obj: object, drop: (k: string) => boolean) =>
    Object.fromEntries(Object.entries(obj).filter(([k]) => !drop(k)));
  return {
    ...without(view, (k) => SPLIT_KEYS.has(k)),
    orgs: view.orgs.map((o) => ({
      ...o,
      programs: o.programs.map((p) => without(p, (k) => k === "np")),
    })),
  };
}

describe.each(["basic", "split_keys"])("the %s split fixture", (name) => {
  const core = read<YearsMatrixCore>(name, "years_matrix.json");
  const shards = YEARS_SHARD_NAMES.map((s) =>
    read<YearsMatrixShard>(name, "years_matrix", `${s}.json`),
  );
  const payload = read<YearsMatrixData>(name, "payload.json");

  it("merges back into the payload it was split from", () => {
    expect(strip(mergeYearsMatrix(core, shards))).toEqual(strip(payload));
  });

  it("keeps each row's np equal to its merged project count", () => {
    for (const o of mergeYearsMatrix(core, shards).orgs) {
      for (const p of o.programs) expect(p.np).toBe(p.projects.length);
    }
  });

  it("maps every shard column to its shard and no default column to any", () => {
    const of = shardOfColumns(core);
    for (const k of core.decade_default_columns ?? []) expect(of.has(k)).toBe(false);
    for (const s of shards) for (const c of s.columns) expect(of.get(c)).toBe(s.shard);
  });

  it("leaves a not-yet-loaded column's cells absent, never zero", () => {
    const of = shardOfColumns(core);
    for (const o of mergeYearsMatrix(core, []).orgs) {
      for (const p of o.programs) {
        for (const k of Object.keys(p.cells)) expect(of.has(k)).toBe(false);
        expect(p.projects).toEqual([]);
      }
    }
  });

  it("refuses a shard from another build", () => {
    const stale = { ...shards[0], build_id: "0".repeat(64) };
    expect(() => mergeYearsMatrix(core, [stale])).toThrow(/build_id/);
  });

  it("merges a pre-split payload (schema 1, one file) to itself", () => {
    const asCore = payload as unknown as YearsMatrixCore;
    expect(strip(mergeYearsMatrix(asCore, []))).toEqual(strip(payload));
  });
});

describe("split-key rows", () => {
  it("are keyed by slug in the core and in the shards", () => {
    const core = read<YearsMatrixCore>("split_keys", "years_matrix.json");
    const keys = core.orgs.flatMap((o) => o.programs.map(yearsRowKey));
    expect(keys).toEqual(expect.arrayContaining(["20-DCSA", "20-DTRA"]));
    const detail = read<YearsMatrixShard>("split_keys", "years_matrix", "detail.json");
    expect(Object.keys(detail.rows).sort()).toEqual(["20-DCSA", "20-DTRA"]);
  });
});
