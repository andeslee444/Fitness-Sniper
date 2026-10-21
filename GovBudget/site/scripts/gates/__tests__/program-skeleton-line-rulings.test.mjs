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
import { describe, it, expect } from "vitest";
import { runLineRulingsLeg, readLineRulings } from "../program-skeleton.mjs";

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

const run = ({ sidecars = clean(), flows = new Map(), rulings = RULINGS, minWithdraw = 7 } = {}) => {
  const errors = [];
  const notes = [];
  runLineRulingsLeg({ errors, notes, sidecars, programs: PROGRAMS, flows, rulings, minWithdraw });
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

  it("reads the committed seed", () => {
    const rulings = readLineRulings();
    expect(rulings.filter((r) => r.ruling === "withdraw")).toHaveLength(41);
    expect(rulings.find((r) => r.award_piid === "N0001925C0070" && r.pe_bli === "0592"))
      .toMatchObject({ ruling: "withdraw", species: "production_on_modification_line" });
  });
});
