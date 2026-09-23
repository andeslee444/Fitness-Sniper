import { describe, it, expect } from "vitest";
import { getProgramDetails, getPrograms } from "@/lib/data";
import { isZeroContentDetails } from "@/lib/program-tier";
import { normalizeExhibitFamily } from "@/lib/basis";
import { selectFamilyLead, familyLeadKicker, familyLedgerCaption, familyLeadAbsence, type FamilyLeadMember } from "@/lib/family-lead";
import { F15_RECORD_SLUGS } from "@/lib/f15-family";
import { F15_DEFAULT_VIEW } from "@/lib/f15-browser-state";

/** Build members from the REAL sidecars — the way the family loader will. */
function members(slugs: readonly string[]): FamilyLeadMember[] {
  const rows = getPrograms();
  return slugs.map((slug) => {
    const details = getProgramDetails(slug);
    const row = rows.find((p) => p.slug === slug);
    if (!row) throw new Error(`no programs.json row for ${slug}`);
    const exhibitFamily = normalizeExhibitFamily(row.exhibit_family);
    if (exhibitFamily !== "rdte" && exhibitFamily !== "procurement") throw new Error(`${slug} has no single exhibit family`);
    return {
      slug,
      title: row.title,
      identifierKind: exhibitFamily === "procurement" ? "BLI" : "PE",
      exhibitFamily,
      tier: (details as { tier?: "full" | "rollup" | "decade" }).tier ?? "full",
      zeroContent: isZeroContentDetails(details),
      summary: details.summary,
      fy26Split: details.fy26_split ?? null,
      absenceNotes: [],
    };
  });
}

describe("family lead rule — real sidecars", () => {
  it("F-15: F015EX leads at FY26 request; EPAWSS development is the one absence", () => {
    const lead = selectFamilyLead(members(F15_RECORD_SLUGS), "F-15");
    expect(lead.kind).toBe("lead");
    if (lead.kind !== "lead") return;
    expect(lead.slug).toBe("F015EX");
    expect(lead.card.fid).toBe("4a9ae7cc78dcf0ba");
    expect(lead.card.value).toBe(3014394);
    expect(lead.reconciled).toBe(true);
    expect(lead.reconShare).toBe(1);
    expect(lead.excluded).toEqual(["0207171F"]);
    expect(lead.ledger.map((r) => r.slug)).toEqual(["F15EWS", "0207134F", "F01500", "0207146F", "0207171F"]);
    expect(lead.ledger.at(-1)?.card).toBeNull();
    expect(lead.ledger.at(-1)?.absenceText).toMatch(/^No /);
    expect(familyLeadKicker(lead, "F-15")).toBe("Largest cited FY26 Request of 6 F-15 records · 1 without a cited FY26 Request");
    expect(familyLedgerCaption(lead, "F-15")).toBe("FY26 Request · P-1/R-1 TOA · PB2026 · 5 other F-15 records, not added");
    // the lead is the funding sheet's SSR default statement — one fact, two places
    expect(F15_DEFAULT_VIEW.record).toBe(lead.slug);
  });

  it("Virginia-class: 2013 leads with a 64.4% reconciliation share; spares are the absence", () => {
    const lead = selectFamilyLead(members(["2013", "0942", "9021"]), "Virginia-class");
    expect(lead.kind).toBe("lead");
    if (lead.kind !== "lead") return;
    expect(lead.slug).toBe("2013");
    expect(lead.card.fid).toBe("a46814a7c44e6bdc");
    expect(Math.round((lead.reconShare ?? 0) * 1000) / 10).toBe(64.4);
    expect(lead.excluded).toEqual(["9021"]);
    expect(familyLeadKicker(lead, "Virginia-class")).toBe("Largest cited FY26 Request of 3 Virginia-class records · 1 without a cited FY26 Request");
  });

  it("Tomahawk: the mods line leads, not the eponymous line; 2101-PMC is absent without an fy2026_absent flag", () => {
    const lead = selectFamilyLead(members(["2101-WPN", "2101-PMC", "2301", "5253", "0204229N"]), "Tomahawk");
    expect(lead.kind).toBe("lead");
    if (lead.kind !== "lead") return;
    expect(lead.slug).toBe("2301");
    expect(lead.excluded).toEqual(["2101-PMC"]);
    expect(lead.ledger.map((r) => r.slug)).toEqual(["2101-WPN", "0204229N", "5253", "2101-PMC"]);
  });

  it("AMRAAM: all four eligible, no exclusion clause", () => {
    const lead = selectFamilyLead(members(["MAMRA0", "2206", "0207163F", "0207163N"]), "AMRAAM");
    expect(lead.kind).toBe("lead");
    if (lead.kind !== "lead") return;
    expect(lead.slug).toBe("MAMRA0");
    expect(lead.excluded).toEqual([]);
    expect(familyLeadKicker(lead, "AMRAAM")).toBe("Largest cited FY26 Request of 4 AMRAAM records");
  });
});

describe("family lead rule — synthetic", () => {
  const card = (over: Partial<import("@/lib/data").SummaryCard>): import("@/lib/data").SummaryCard => ({
    key: "fy2026", fy: 2026, measure: "request", basis: "toa", value: 100, units: "USD thousands", fid: "f".repeat(16), public_id: "ffffffff", dataset: "fct_decade_series", edition: 2026, absence_reason: null, ...over,
  });
  const member = (slug: string, cards: import("@/lib/data").SummaryCard[], extra: Partial<FamilyLeadMember> = {}): FamilyLeadMember => ({
    slug, title: slug, identifierKind: "PE", exhibitFamily: "rdte", tier: "full", zeroContent: false,
    summary: { edition: 2026, basis_preference: "toa", cards, reconciliation: [], named_primes: [] }, fy26Split: null, absenceNotes: [], ...extra,
  });

  it("ties: the un-reconciled member leads, then code-point slug order", () => {
    const a = member("B1", [card({ fid: "a".repeat(16) })]);
    const b = member("A1", [card({ fid: "b".repeat(16) })], { summary: { edition: 2026, basis_preference: "toa", cards: [card({ fid: "b".repeat(16) })], reconciliation: [{ fy: 2026, measure: "request" } as never], named_primes: [] } });
    const lead = selectFamilyLead([a, b], "X");
    expect(lead.kind === "lead" && lead.slug).toBe("B1");
    const c = member("A0", [card({ fid: "c".repeat(16) })]);
    const lead2 = selectFamilyLead([a, c], "X");
    expect(lead2.kind === "lead" && lead2.slug).toBe("A0");
  });

  it("never ranks fy2025 against itself: eligible fy2025 cards with ineligible fy2026 cards → absent", () => {
    const m = member("P1", [card({ key: "fy2025", fy: 2025, measure: "enacted" }), card({ key: "fy2026", fid: null, value: null, absence_reason: "not-published" })]);
    const lead = selectFamilyLead([m], "X");
    expect(lead.kind).toBe("absent");
    expect(lead.kind === "absent" && lead.text).toBe(familyLeadAbsence(2026, 1, "X"));
    expect(familyLeadAbsence(2026, 1, "X")).toBe("No cited P-1/R-1 workbook figure for any of the 1 X budget records in the PB2026 workbooks. Missing coverage is not zero spending.");
  });

  it("rollup tier, zero-content, jbook-detail and edition mismatch are ineligible", () => {
    const rollup = member("R", [card({})], { tier: "rollup" });
    const zero = member("Z", [card({})], { zeroContent: true });
    const detail = member("D", [card({ basis: "jbook-detail", units: "USD millions" })]);
    const stale = member("S", [card({ edition: 2025 })]);
    expect(selectFamilyLead([rollup, zero, detail, stale], "X").kind).toBe("absent");
  });

  it("caps cited ledger rows at five and counts the overflow; absence rows always render", () => {
    const ms = Array.from({ length: 8 }, (_, i) => member(`M${i}`, [card({ value: 1000 - i, fid: String(i).repeat(16) })]));
    ms.push(member("ABS", [card({ fid: null, value: null, absence_reason: "no-rollup" })]));
    const lead = selectFamilyLead(ms, "X");
    if (lead.kind !== "lead") throw new Error("expected lead");
    expect(lead.ledger.filter((r) => r.card).length).toBe(5);
    expect(lead.ledgerOverflow).toBe(2);
    expect(lead.ledger.at(-1)?.slug).toBe("ABS");
    expect(lead.ledger.at(-1)?.absenceText).toBe("No single program-level figure; see the line items below");
  });
});
