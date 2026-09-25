/**
 * Gate 24 leg (m) — declared cadence vs. measured ingest age (ROADMAP #8),
 * and the part-name binding added by Task 29 fix round 1.
 *
 * THE DEFECT THESE PIN. /methodology/'s USAspending card rendered "Source
 * cadence: monthly — this corpus was fetched 2026-06-11." after the branch
 * adopted the 2026-09-06 FY2026 contract and assistance archives, fetched
 * 2026-09-24. The date was the subawards' newest download — the stalest of
 * the three datasets' newest downloads, which is what leg m requires the
 * rendered date to EQUAL — so the leg was green over a sentence that gave
 * one part's date to the whole corpus.
 *
 * The page now says whose date it is (src/lib/source-freshness.mjs), and the
 * leg now requires that, whenever the named datasets' newest downloads fall
 * on different days, the rendered clause names the stalest one. The date
 * binding is unchanged; these tests prove both on fixtures, including every
 * ordering of the three datasets' fetch dates.
 *
 * Manifest and pages are injected (like link-precision.test.mjs injects its
 * corpora) so nothing here depends on a build or on the shared lake.
 */

import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";
import { runSourceCadenceLeg } from "../datatruth.mjs";
import {
  STALEST_ATTR,
  stalestPartClause,
} from "../../../src/lib/source-freshness.mjs";

const NOW = Date.parse("2026-09-25T12:00:00Z");
const MEMBERS = ["assistance", "contracts", "subawards"];

/** A manifest shaped like the adopted one: every dataset has an OLDER file
 *  (FY2017, 2026-06-10) and a newest one at the given instant. */
function manifest(newest) {
  const lines = [];
  for (const ds of MEMBERS) {
    lines.push({ dataset: ds, fiscal_year: 2017, file_name: `${ds}-fy2017.zip`,
      downloaded_at: "2026-06-10T15:58:52.133578+00:00" });
    lines.push({ dataset: ds, fiscal_year: 2026, file_name: `${ds}-newest.zip`,
      downloaded_at: newest[ds] });
  }
  lines.push({ dataset: "mts_outlays", file_name: "mts_table_5.parquet",
    downloaded_at: "2026-06-10T15:59:17.877863+00:00" });
  return lines.map((r) => JSON.stringify(r)).join("\n") + "\n";
}

/** What the exporter hands the page for these fetch dates: the member whose
 *  newest download is oldest (this test's oracle, not the gate's code). */
function exportedGroup(newest) {
  const stalest = [...MEMBERS].sort((a, b) =>
    newest[a] === newest[b] ? a.localeCompare(b) : newest[a] < newest[b] ? -1 : 1,
  )[0];
  return { stalest_dataset: stalest, as_of: newest[stalest].slice(0, 10) };
}

/** The built /methodology/ card, with `tail` where the page renders the
 *  clause after "Source cadence: monthly". */
function methodologyPage(tail) {
  return [
    "/methodology/index.html",
    `<!DOCTYPE html><html><body><main><p data-source-freshness="${MEMBERS.join(",")}">` +
      "The official federal award database (contracts, grants, loans, and " +
      "subawards), mandated by the DATA Act. Current scope: Department of " +
      `Defense agencies, FY2017 onward. Source cadence: monthly${tail}</p>` +
      "<script>self.__next_f.push([1,\"Source cadence: monthly — this corpus was fetched 1999-01-01.\"])</script>" +
      "</main></body></html>",
  ];
}

/** Exactly what page.tsx renders for a group. */
const rendered = (group) =>
  `<span ${STALEST_ATTR}="${group.stalest_dataset}">${stalestPartClause(group)}</span>`;

function run(newest, tail) {
  const errors = [];
  const notes = [];
  runSourceCadenceLeg(errors, notes, {
    manifestText: manifest(newest),
    pages: [methodologyPage(tail)],
    now: NOW,
  });
  return { errors, notes };
}

/** The adopted 2026-09-06 refresh: contracts/assistance 2026-09-24, subawards 2026-06-11. */
const ADOPTED = {
  assistance: "2026-09-24T04:29:08.025928+00:00",
  contracts: "2026-09-24T04:34:55.271404+00:00",
  subawards: "2026-06-11T12:06:10.273518+00:00",
};

describe("leg m on the adopted refresh", () => {
  it("passes on the clause the page renders: the subawards, last fetched 2026-06-11", () => {
    const group = exportedGroup(ADOPTED);
    expect(group).toEqual({ stalest_dataset: "subawards", as_of: "2026-06-11" });
    const { errors, notes } = run(ADOPTED, rendered(group));
    expect(errors).toEqual([]);
    expect(notes.join("\n")).toMatch(/leg m: 1 of 1 cadence claim\(s\) checked/);
  });

  it("FAILS on the sentence that shipped: one date over three parts, naming none", () => {
    const { errors } = run(ADOPTED, " — this corpus was fetched 2026-06-11.");
    expect(errors).toHaveLength(1);
    expect(errors[0]).toMatch(/without naming the part/);
    expect(errors[0]).toMatch(/stalest is subawards/);
  });

  it("FAILS when the clause names a part the date does not belong to", () => {
    const { errors } = run(
      ADOPTED,
      rendered({ stalest_dataset: "contracts", as_of: "2026-06-11" }),
    );
    expect(errors).toHaveLength(1);
    expect(errors[0]).toMatch(/names "contracts"/);
  });

  it("FAILS when the attribute and the visible name disagree", () => {
    const { errors } = run(
      ADOPTED,
      `<span ${STALEST_ATTR}="subawards"> — its least recently refreshed dataset (contracts) was last fetched 2026-06-11.</span>`,
    );
    expect(errors).toHaveLength(1);
  });

  it("still binds the DATE: the right part with another date fails exactly as before", () => {
    const { errors } = run(
      ADOPTED,
      rendered({ stalest_dataset: "subawards", as_of: "2026-09-24" }),
    );
    expect(errors).toHaveLength(1);
    expect(errors[0]).toMatch(/renders as-of date\(s\) 2026-09-24/);
    expect(errors[0]).toMatch(/is 2026-06-11 \(subawards/);
  });

  it("still requires a date on a stale corpus", () => {
    const { errors } = run(ADOPTED, ".");
    expect(errors).toHaveLength(1);
    expect(errors[0]).toMatch(/no built page states an as-of date/);
  });

  it("still refuses a site whose every cadence line is unmetered (vacuity)", () => {
    const errors = [];
    runSourceCadenceLeg(errors, [], {
      manifestText: manifest(ADOPTED),
      pages: [
        [
          "methodology/index.html",
          '<p data-source-freshness="unmetered">J-books. Source cadence: annual.</p>',
        ],
      ],
      now: NOW,
    });
    expect(errors).toHaveLength(1);
    expect(errors[0]).toMatch(/decorative/);
  });
});

describe("leg m for every ordering of the three datasets' fetch dates", () => {
  const DAYS = [
    "2026-06-11T12:06:10+00:00",
    "2026-08-01T09:00:00+00:00",
    "2026-09-24T04:34:55+00:00",
  ];
  const orders = [];
  for (const a of MEMBERS)
    for (const b of MEMBERS)
      for (const c of MEMBERS)
        if (new Set([a, b, c]).size === 3) orders.push([a, b, c]);

  it.each(orders)("stalest %s, then %s, then %s", (first, second, third) => {
    const newest = { [first]: DAYS[0], [second]: DAYS[1], [third]: DAYS[2] };
    const group = exportedGroup(newest);
    expect(group.stalest_dataset).toBe(first);
    expect(run(newest, rendered(group)).errors).toEqual([]);
    for (const other of [second, third]) {
      const wrong = run(newest, rendered({ ...group, stalest_dataset: other }));
      expect(wrong.errors).toHaveLength(1);
    }
  });

  it("asks no name when every part's newest download falls on one day", () => {
    const sameDay = {
      assistance: "2026-06-11T11:50:18+00:00",
      contracts: "2026-06-11T11:50:15+00:00",
      subawards: "2026-06-11T12:06:10+00:00",
    };
    expect(run(sameDay, " — this corpus was fetched 2026-06-11.").errors).toEqual([]);
    // …and the named clause stays true there too.
    expect(run(sameDay, rendered(exportedGroup(sameDay))).errors).toEqual([]);
  });

  it("accepts either name on an exact tie — both parts are equally stale", () => {
    const tie = {
      assistance: "2026-09-24T04:29:08+00:00",
      contracts: "2026-06-11T12:06:10+00:00",
      subawards: "2026-06-11T12:06:10+00:00",
    };
    for (const name of ["contracts", "subawards"]) {
      expect(
        run(tie, rendered({ stalest_dataset: name, as_of: "2026-06-11" })).errors,
      ).toEqual([]);
    }
  });
});

describe("one clause, one attribute: the page and the gate", () => {
  const site = path.resolve(__dirname, "..", "..", "..");
  const read = (p) => fs.readFileSync(path.join(site, p), "utf8");

  it("/methodology/ renders the helper's clause inside the attribute leg m reads", () => {
    const src = read("src/app/methodology/page.tsx");
    expect(src).toMatch(/from "@\/lib\/source-freshness\.mjs"/);
    expect(src).toContain("stalestPartClause(");
    expect(src).toContain(`${STALEST_ATTR}={`);
    expect(src).not.toMatch(/this corpus was fetched/);
  });

  it("gate 24 leg m reads the attribute name from the helper", () => {
    const src = read("scripts/gates/datatruth.mjs");
    expect(src).toMatch(
      /import \{ STALEST_ATTR \} from "\.\.\/\.\.\/src\/lib\/source-freshness\.mjs"/,
    );
  });
});
