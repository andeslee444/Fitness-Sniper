/**
 * Gate 21 leg (q) — a pair the owner ruled withdrawn publishes nowhere
 * (program-skeleton.mjs runLineRulingsLeg), proof that it can fail.
 *
 * R-DEC-LINK-2026-10-21 (owner, 2026-10-21: "approved, would process with
 * recommendation to approve all"). dbt/seeds/link_line_rulings.csv withdraws
 * 41 (award, line) pairs — the Lot 12 and Lot 20 F-35 production contracts on
 * the F-35 modification lines 0592/0593, TH-73A full-rate production on 0549,
 * the C-32/C-40 O&M support task order on C03200/C04000, and 34 fpds-ap
 * production buys on seven modification lines. audit_link_grading grades
 * them low, so the mart, the program pages and the flows drop them; this leg
 * reads the SHIPPED sidecars, so an export that reached the site some other
 * way still fails.
 *
 * Run via `npm test` (vitest).
 */
import { createHash } from "crypto";
import { describe, it, expect } from "vitest";
import { runLineRulingsLeg, readLineRulings } from "../program-skeleton.mjs";

const sha16 = (s) => createHash("sha256").update(s).digest("hex").slice(0, 16);
/** export_site.fact_id_derived("budget_to_awards", f"{pe}|{piid}", "link") */
const linkFid = (pe, piid) => sha16(`derived|budget_to_awards|${pe}|${piid}|link`);

const W = (award_piid, pe_bli) => ({ award_piid, pe_bli, ruling: "withdraw" });
const A = (award_piid, pe_bli) => ({ award_piid, pe_bli, ruling: "allow" });
const award = (award_piid) => ({ award_piid, confidence: "high" });

/** The four pinned pages as release 2026-10-21 must ship them. */
const clean = () =>
  new Map([
    ["0592", { awards: [award("N0001915C0016"), award("N0001920F0571"), award("N0001923F0002")] }],
    ["0593", { awards: [award("N0001920F0571"), award("N0001923F0002")] }],
    ["0549", { awards: [] }],
    ["C03200", { awards: [award("FA813423DB004")] }],
    ["ATA000", { awards: [award("N0001925C0070")] }],
    ["3010-SCN", { awards: [award("N0002420C0001")] }],
  ]);
const RULINGS = [
  W("N0001917C0001", "0592"), W("N0001925C0070", "0592"),
  W("N0001917C0001", "0593"), W("N0001925C0070", "0593"),
  W("N6134020C0007", "0549"), W("FA813423FB001", "C03200"),
  W("N0002420C0009", "3010"),
  A("N0001915C0036", "0515"),
];
const PROGRAMS = [
  { pe_bli: "3010", slug: "3010-SCN" },
  { pe_bli: "0592", slug: "0592" },
];

/** The F-35 flow and IN-07 as release 2026-10-21 must ship them (R4): the
 *  Lockheed order N0001922F0001 stays; the Rolls-Royce one does not. */
const cleanFlows = () =>
  new Map([
    ["ATA000", { awards: [
      { piid: "N0001922F0001", recipient_name: "LOCKHEED MARTIN CORPORATION", district: "TX-12", dollars: 184551699.01 },
    ] }],
  ]);
const cleanIN07 = () => ({
  programs: [{ pe_bli: "0164", split_key: "0164", total_obligation: 1 }],
  by_year_programs: [{ pe_bli: "0164", fiscal_year: 2022, total_obligation: 1 }],
});

const run = ({
  sidecars = clean(), flows = cleanFlows(), rulings = RULINGS, minWithdraw = 7,
  citations = {}, shards = new Map(), districts = new Map([["IN-07", cleanIN07()]]),
} = {}) => {
  const errors = [];
  const notes = [];
  runLineRulingsLeg({
    errors, notes, sidecars, programs: PROGRAMS, flows, rulings, minWithdraw,
    citations, shards, districts,
  });
  return errors;
};

describe("program-skeleton leg (q): withdrawn line rulings", () => {
  it("passes on the pages the release must ship", () => {
    expect(run()).toEqual([]);
  });

  it("fails when a program page still lists a withdrawn pair", () => {
    const sidecars = clean();
    sidecars.get("0592").awards.push(award("N0001917C0001"));
    const errors = run({ sidecars });
    expect(errors.join("\n")).toMatch(/N0001917C0001.*\/program\/0592\//);
  });

  it("reads an account-split member page under its own code", () => {
    const sidecars = clean();
    sidecars.get("3010-SCN").awards.push(award("N0002420C0009"));
    expect(run({ sidecars }).join("\n")).toMatch(/N0002420C0009.*3010-SCN/);
  });

  it("leaves the same award on another line alone", () => {
    // N0001925C0070 is withdrawn from 0592/0593, never from ATA000
    expect(run()).toEqual([]);
  });

  it("fails when a flows file still sums a withdrawn pair", () => {
    const flows = new Map([["0592", { awards: [{ piid: "N0001925C0070", dollars: 1 }] }]]);
    expect(run({ flows }).join("\n")).toMatch(/flows\/0592\.json.*N0001925C0070/);
  });

  it("pins 0549 as a page with no awards and the F-35 pages as present", () => {
    const sidecars = clean();
    sidecars.get("0549").awards.push(award("N0001919C0099"));
    sidecars.delete("0593");
    const errors = run({ sidecars }).join("\n");
    expect(errors).toMatch(/0549.*no awards/);
    expect(errors).toMatch(/0593.*missing/);
  });

  it("fails when the seed lost its withdraw rows", () => {
    expect(run({ rulings: [A("N0001915C0036", "0515")] }).join("\n")).toMatch(/withdraw/);
  });

  it("fails when citations.json or a cite shard still carries a withdrawn pair's fact id (review 1 M-3)", () => {
    const fid = linkFid("0592", "N0001917C0001");
    expect(fid).toBe("98b6dcf90fc2fc67"); // one of the 41 measured leaving, 2026-10-21
    expect(run({ citations: { [fid]: { kind: "announcement" } } }).join("\n"))
      .toMatch(/citations\.json.*98b6dcf90fc2fc67.*N0001917C0001.*0592/);
    const shards = new Map([["98", { [fid]: { kind: "announcement" } }]]);
    expect(run({ shards }).join("\n")).toMatch(/cite-shards\/98\.json.*98b6dcf90fc2fc67/);
    // a fact id of a pair nobody withdrew is no finding
    expect(run({ citations: { [linkFid("ATA000", "N0001925C0070")]: {} } })).toEqual([]);
  });

  it("pins the N0001922F0001 collision off flows/ATA000.json and /district/IN-07/ (R4)", () => {
    const flows = cleanFlows();
    flows.get("ATA000").awards.push({
      piid: "N0001922F0001", recipient_name: "ROLLS-ROYCE CORPORATION", district: "IN-07", dollars: 157917295.93,
    });
    expect(run({ flows }).join("\n")).toMatch(/flows\/ATA000\.json.*N0001922F0001.*ROLLS-ROYCE/);

    const inProgram = cleanIN07();
    inProgram.programs.push({ pe_bli: "ATA000", split_key: "ATA000", fact_id: "44ee093c2bab2ea8", total_obligation: 147027390.49 });
    expect(run({ districts: new Map([["IN-07", inProgram]]) }).join("\n")).toMatch(/IN-07.*ATA000/);

    const inYear = cleanIN07();
    inYear.by_year_programs.push({ pe_bli: "ATA000", fiscal_year: 2022, total_obligation: 147169527.81 });
    expect(run({ districts: new Map([["IN-07", inYear]]) }).join("\n")).toMatch(/IN-07.*ATA000.*2022/);

    // the IN-07 F-35 receipt the collision minted (usaspending district_program)
    expect(sha16("usaspending|district_program|IN|IN-07|ATA000|total_obligation")).toBe("44ee093c2bab2ea8");
    expect(run({ citations: { "44ee093c2bab2ea8": {} } }).join("\n")).toMatch(/44ee093c2bab2ea8/);

    // a missing file is a finding, never a silent pass
    expect(run({ flows: new Map() }).join("\n")).toMatch(/flows\/ATA000\.json.*missing/);
    expect(run({ districts: new Map() }).join("\n")).toMatch(/IN-07.*missing/);
  });

  // Review r2 M-2: the export names a flows row by its UEI, or "Unknown",
  // when the UEI→name lookup misses (_emit_flows_sidecars' uei_names), so a
  // name-only pin would pass the Rolls-Royce dollars back under any other
  // label. The order performed only in IN-07 and the Lockheed one only in
  // TX-12, so N0001922F0001 at IN-07 is the Rolls-Royce award whatever the
  // row is called.
  it("pins the N0001922F0001 IN-07 row whatever its recipient name (review r2 M-2)", () => {
    for (const recipient_name of ["RRUEI0000001", "Unknown", null, "ALLISON ENGINE CO"]) {
      const flows = cleanFlows();
      flows.get("ATA000").awards.push({
        piid: "N0001922F0001", recipient_name, district: "IN-07", dollars: 157917295.93,
      });
      expect(run({ flows }).join("\n"), String(recipient_name))
        .toMatch(/flows\/ATA000\.json.*N0001922F0001.*IN-07/);
    }
    // the Lockheed award the ATA000 link names (TX-12) stays a clean pass,
    // and so does the same district under another PIID
    const flows = cleanFlows();
    flows.get("ATA000").awards.push({
      piid: "N0001922F0002", recipient_name: "Unknown", district: "IN-07", dollars: 1,
    });
    expect(run({ flows })).toEqual([]);
  });

  it("reads the committed seed", () => {
    const rulings = readLineRulings();
    expect(rulings.filter((r) => r.ruling === "withdraw")).toHaveLength(41);
    expect(rulings.find((r) => r.award_piid === "N0001925C0070" && r.pe_bli === "0592"))
      .toMatchObject({ ruling: "withdraw", species: "production_on_modification_line" });
  });
});
