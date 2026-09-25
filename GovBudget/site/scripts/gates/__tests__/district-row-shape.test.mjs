/**
 * Unit tests for gate 9 leg (g) — every /district/{code}/ program row is
 * individually addressable (Task 27, fix round 1 2026-09-19).
 *
 * Why the leg exists: the district page keys its program table on
 * `split_key` and prints it as the row's mono code. A sidecar written before
 * Task 27 has no such field, so a build against it renders an empty code cell
 * on every row and hands React a duplicate key — a dev-mode warning and
 * nothing else. Leg e, the only other leg that walks program rows, reads the
 * field through `prog.split_key ?? prog.pe_bli` (a message may be lenient; a
 * check may not), so it stays green on exactly that payload.
 *
 * Synthetic sidecars are used so the leg never touches site/out or
 * data/site/json.
 *
 * Run via `npm test` (vitest).
 */

import { describe, it, expect } from "vitest";
import { runDistrictRowShapeLeg } from "../district.mjs";

/** A well-formed ordinary row: no account, split_key == pe_bli, stub URL. */
function ordinary(pe_bli) {
  return {
    account: null,
    pe_bli,
    split_key: pe_bli,
    program_url: `/program/${pe_bli}/`,
    total_obligation: 1_000_000,
  };
}

/** A well-formed member row of an account-split code ('3010' → '3010-SCN'). */
function member(pe_bli, code, account) {
  return {
    account,
    pe_bli,
    split_key: `${pe_bli}-${code}`,
    program_url: `/program/${pe_bli}-${code}/`,
    total_obligation: 900_000,
  };
}

/**
 * The corpus shape measured read-only 2026-09-19 against
 * data/duckdb/govbudget.duckdb at the member grain, transposed onto
 * synthetic district codes: 189 districts, 608 program rows. (Chain C run 4,
 * 2026-09-25, published 611 rows across the same 189; the counts only
 * exercise the logic.) Rows are spread as evenly as the counts allow so
 * every district carries at least one.
 */
function corpus({ districts = 189, rows = 608, mutate = null } = {}) {
  const base = Math.floor(rows / districts);
  const remainder = rows - base * districts;
  const out = [];
  for (let i = 0; i < districts; i++) {
    const n = base + (i < remainder ? 1 : 0);
    const programs = [];
    for (let j = 0; j < n; j++) programs.push(ordinary(`06${i}${j}01E`));
    const sidecar = { pop_district: `ZZ-${String(i).padStart(3, "0")}`, programs };
    out.push(sidecar);
  }
  if (mutate) mutate(out);
  return out;
}

function run(sidecars) {
  const errors = [];
  const notes = [];
  runDistrictRowShapeLeg({ errors, notes, sidecars });
  return { errors, notes };
}

describe("gate 9 leg g — district program rows are addressable", () => {
  it("passes on the 2026-09-19 corpus shape and says what it saw", () => {
    const { errors, notes } = run(corpus());
    expect(errors).toEqual([]);
    expect(notes[0]).toContain("608 program row(s)");
    expect(notes[0]).toContain("189 district(s)");
  });

  it("accepts both members of a shared code in one district", () => {
    const sidecars = corpus({
      mutate: (out) => {
        out[0].programs.push(member("3010", "SCN", "1611N"));
        out[0].programs.push(member("3010", "OPN", "1810N"));
      },
    });
    expect(run(sidecars).errors).toEqual([]);
  });

  it("accepts an organization-split row: an account, and still the stub", () => {
    // '20' carries the SAME account ('0300D') on both of its members, so an
    // account cannot name one — the row keeps the bare key as its address.
    // `account !== null` is therefore NOT the member test; split_key is.
    const sidecars = corpus({
      mutate: (out) => {
        out[0].programs.push({
          account: "0300D",
          pe_bli: "20",
          split_key: "20",
          program_url: "/program/20/",
          total_obligation: 5_000,
        });
      },
    });
    expect(run(sidecars).errors).toEqual([]);
  });

  it("fails a row with no split_key — the pre-Task-27 sidecar shape", () => {
    const sidecars = corpus({
      mutate: (out) => {
        const p = out[3].programs[0];
        delete p.split_key;
      },
    });
    const { errors } = run(sidecars);
    expect(errors.length).toBe(1);
    expect(errors[0]).toContain("leg g: 1 district program row problem(s)");
    expect(errors[0]).toContain("no split_key");
    expect(errors[0]).toContain("re-run export-site");
  });

  it("fails an empty-string split_key too", () => {
    const sidecars = corpus({
      mutate: (out) => {
        out[3].programs[0].split_key = "";
      },
    });
    expect(run(sidecars).errors[0]).toContain("no split_key");
  });

  it("fails a program_url that does not address the row's own split_key", () => {
    const sidecars = corpus({
      mutate: (out) => {
        out[5].programs.push({
          ...member("3010", "SCN", "1611N"),
          program_url: "/program/3010/",
        });
      },
    });
    const { errors } = run(sidecars);
    expect(errors[0]).toContain("does not address its own split_key");
    expect(errors[0]).toContain("/program/3010-SCN/");
  });

  it("fails an account-null row whose split_key is not the bare code", () => {
    const sidecars = corpus({
      mutate: (out) => {
        out[7].programs.push({
          account: null,
          pe_bli: "3010",
          split_key: "3010-SCN",
          program_url: "/program/3010-SCN/",
          total_obligation: 1,
        });
      },
    });
    const { errors } = run(sidecars);
    expect(errors[0]).toContain("account is null");
    expect(errors[0]).toContain("not the bare code");
  });

  it("fails a split_key that is neither the bare code nor a member slug", () => {
    const sidecars = corpus({
      mutate: (out) => {
        out[9].programs.push({
          account: "1611N",
          pe_bli: "3010",
          split_key: "9999-SCN",
          program_url: "/program/9999-SCN/",
          total_obligation: 1,
        });
      },
    });
    expect(run(sidecars).errors[0]).toContain("member slug");
  });

  it("fails two rows in one district sharing a split_key", () => {
    const sidecars = corpus({
      mutate: (out) => {
        out[11].programs.push(member("3010", "SCN", "1611N"));
        out[11].programs.push({
          ...member("3010", "SCN", "1810N"),
          pe_bli: "3010",
        });
      },
    });
    const { errors } = run(sidecars);
    expect(errors[0]).toContain("two program rows share split_key");
    expect(errors[0]).toContain("one address, two figures");
  });

  it("counts every bad row and caps only the detail list", () => {
    const sidecars = corpus({
      mutate: (out) => {
        for (let i = 0; i < 20; i++) delete out[i].programs[0].split_key;
      },
    });
    const { errors } = run(sidecars);
    expect(errors[0]).toContain("leg g: 20 district program row problem(s)");
    expect(errors[0]).toContain("(+15 more)");
  });

  it("cannot pass vacuously on an empty districts/ directory", () => {
    const { errors } = run([]);
    expect(errors.some((e) => e.includes("only 0 district(s)"))).toBe(true);
    expect(errors.some((e) => e.includes("0 district program row(s)"))).toBe(true);
    expect(errors.join(" ")).toContain("do not lower the floor");
  });

  it("fails a corpus that quietly collapsed to a tenth of its rows", () => {
    const { errors } = run(corpus({ districts: 189, rows: 189 }));
    expect(errors.length).toBe(1);
    expect(errors[0]).toContain("189 district program row(s)");
    expect(errors[0]).toContain("measured 2026-09-19 at 608");
  });
});
