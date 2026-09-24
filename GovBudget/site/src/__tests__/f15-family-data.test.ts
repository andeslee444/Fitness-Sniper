import { describe, expect, it } from "vitest";
import { getF15FamilyData, validateF15FamilyEvidence } from "@/lib/f15-family-data";
import { F15_RECORD_SLUGS, getFamilyFundingSummary, getRecordFact, getVariantRecords, type FamilyFundingRecord, type VariantId } from "@/lib/f15-family";
import { getProgramDetails } from "@/lib/data";

const family = getF15FamilyData();
const record = (slug: string) => family.records.find((item) => item.slug === slug)!;

describe("F-15 curated family and source coverage", () => {
  it("has the six product variants above exactly six canonical budget identities", () => {
    expect(family.variants.map((variant) => variant.id)).toEqual(["A", "B", "C", "D", "E", "EX"]);
    expect(family.records.map((item) => item.slug)).toEqual([...F15_RECORD_SLUGS]);
    expect(new Set(family.records.map((item) => item.slug)).size).toBe(6);
    expect(JSON.parse(JSON.stringify(family))).toEqual(family);
  });

  it("keeps historical variants useful without inventing a zero budget", () => {
    for (const variant of ["A", "B"] as VariantId[]) {
      expect(getVariantRecords(family, variant)).toEqual([]);
      const entry = family.variants.find((item) => item.id === variant)!;
      expect(entry.coverageNote).toContain("No separately identified");
      expect(entry.sourceIds.length).toBeGreaterThan(0);
    }
    expect(getFamilyFundingSummary([], 2026, "request").amountThousands).toBeNull();
  });

  it("traces every editorial source and curated association to supplied evidence", () => {
    for (const variant of family.variants) {
      for (const sourceId of variant.sourceIds) {
        expect(family.sources.find((source) => source.id === sourceId)?.officialUrl).toMatch(/^https:\/\/www\.af\.mil\//);
      }
      for (const link of variant.recordLinks) {
        expect(record(link.slug).narratives.some((item) => item.factId === link.evidenceFactId)).toBe(true);
        expect(family.citations[link.evidenceFactId]).toBeDefined();
        for (const sourceId of link.evidenceSourceIds ?? []) expect(family.sources.some((source) => source.id === sourceId && source.officialUrl)).toBe(true);
      }
    }
    for (const milestone of family.milestones) expect(family.sources.some((source) => source.id === milestone.sourceId)).toBe(true);
  });

  it("shares complete source objects across the client payload for Flight deduplication", () => {
    const sources = new Map(family.sources.map(source => [source.id, source]));
    const referenced = [
      ...family.topics.map(topic => topic.source),
      ...family.records.flatMap(item => [
        ...item.facts.map(fact => fact.source),
        ...item.componentRows.map(fact => fact.source),
        ...item.narratives.map(narrative => narrative.source),
        ...(item.change ? [item.change.source] : []),
      ]),
    ];
    for (const source of referenced) {
      expect(source).toBe(sources.get(source.id));
      expect(source.receiptUrl).toBe(`/fact/${source.factId!.slice(0, 8)}/`);
      expect(source).toHaveProperty("officialUrl");
      expect(source).toHaveProperty("locator");
    }
    for (const narrative of family.records.flatMap(item => item.narratives)) {
      const citation = family.citations[narrative.factId];
      if (citation.kind === "jbook_narrative") expect(citation.source_passage).toBe(narrative);
    }
  });

  it("maps shared C/D/E/EX software while keeping F-15E installation separate from EX", () => {
    expect(record("0207134F").variantIds).toEqual(["C", "D", "E", "EX"]);
    const evidence = record("0207134F").narratives.find((item) => item.factId === "0026c924483c6624")!;
    expect(evidence.body).toContain("F-15C, F-15D, F-15E, and F-15EX");
    for (const id of ["C", "D", "E", "EX"] as VariantId[]) {
      expect(family.variants.find((item) => item.id === id)!.recordLinks.find((link) => link.slug === "0207134F")?.scope).toBe("shared");
    }
    expect(getVariantRecords(family, "E", "upgrade").map((item) => item.slug)).toContain("F15EWS");
    expect(getVariantRecords(family, "EX").map((item) => item.slug)).not.toContain("F15EWS");
    expect(record("0207171F").scopeNote).toContain("does not allocate");
    expect(family.variants.find((item) => item.id === "EX")!.recordLinks.find((link) => link.slug === "0207171F")?.evidenceSourceIds).toContain("usaf-ex-delivery");
  });

  it("stops if a hotspot's narrative was changed or removed", () => {
    const changed = family.records.map((item) => ({ ...item, narratives: item.narratives.map((narrative) => narrative.factId === "cb4796e48126e4a7" ? { ...narrative, body: "Unrelated replacement text" } : narrative) }));
    expect(() => validateF15FamilyEvidence(changed, family.variants, family.topics)).toThrow("Missing or changed airframe evidence");
  });
});

describe("F-15 funding identity and accounting basis", () => {
  it("defaults to the exporter's exact summary fact even when another status has an equal value", () => {
    for (const item of family.records) {
      for (const card of getProgramDetails(item.slug).summary.cards) {
        if (card.key === "change" || card.basis !== "toa" || !card.fid) continue;
        expect(getRecordFact(item, card.fy)?.factId).toBe(card.fid);
        expect(getRecordFact(item, card.fy)?.measure).toBe(card.measure);
      }
    }
    const development = record("0207146F");
    expect(getRecordFact(development, 2025)?.factId).toBe("c889c1ad92557fc0");
    expect(getRecordFact(development, 2025)?.measure).toBe("total");
    expect(getRecordFact(development, 2025, "enacted")?.factId).toBe("1634576efacdc10f");
    const diverged = { ...development, facts: development.facts.map((fact) => fact.fy === 2025 && fact.measure === "enacted" ? { ...fact, amountThousands: fact.amountThousands - 500 } : fact) };
    expect(getRecordFact(diverged, 2025)?.amountThousands).toBe(56_228);
    expect(getRecordFact(diverged, 2025, "enacted")?.amountThousands).toBe(55_728);
  });

  it("keeps each change's displayed endpoints aligned with its actual citation inputs", () => {
    function containsFact(root: string, target: string, seen = new Set<string>()): boolean {
      if (root === target) return true;
      if (seen.has(root)) return false;
      seen.add(root);
      const citation = family.citations[root];
      if (citation?.kind !== "derived") return false;
      return (JSON.parse(citation.inputs ?? "[]") as string[]).some((input) => containsFact(input, target, seen));
    }
    for (const item of family.records) {
      if (!item.change) continue;
      const from = getRecordFact(item, item.change.fy - 1)!;
      const to = getRecordFact(item, item.change.fy)!;
      expect(item.change.fromFactId).toBe(from.factId);
      expect(item.change.toFactId).toBe(to.factId);
      expect(containsFact(item.change.factId, from.factId)).toBe(true);
      expect(containsFact(item.change.factId, to.factId)).toBe(true);
      expect(to.amountThousands - from.amountThousands).toBeCloseTo(item.change.amountThousands, 6);
    }
  });

  it("has matching fiscal statuses and editions within every available comparison purpose/year", () => {
    for (const purpose of ["develop", "buy", "upgrade"] as const) {
      for (const fy of family.years) {
        const facts = family.records.filter((item) => item.purpose === purpose).flatMap((item) => {
          const fact = getRecordFact(item, fy);
          return fact ? [fact] : [];
        });
        expect(new Set(facts.map((fact) => `${fact.measure}/${fact.basis}/${fact.edition}/${fact.units}`)).size).toBeLessThanOrEqual(1);
      }
    }
  });

  it("retains each figure's accounting context and resolves every receipt including derived inputs", () => {
    for (const item of family.records) {
      expect(new Set(item.facts.map((fact) => fact.factId)).size).toBe(item.facts.length);
      for (const fact of [...item.facts, ...item.componentRows, ...(item.change ? [item.change] : [])]) {
        expect(fact.recordSlug).toBe(item.slug);
        expect(fact.basis).toBe("toa");
        expect(fact.units).toBe("USD thousands");
        expect(fact.dataset).toBeTruthy();
        expect(fact.fy).toBeGreaterThan(2000);
        expect(fact.edition).toBeGreaterThanOrEqual(fact.fy - 1);
        expect(fact.measure).toBeTruthy();
        expect(fact.status).toBeTruthy();
        expect(fact.source.receiptUrl).toBe(`/fact/${fact.publicId}/`);
        const citation = family.citations[fact.factId];
        expect(citation).toBeDefined();
        if (citation.kind === "workbook") {
          expect(citation.amount_thousands).toBe(fact.amountThousands);
          expect(fact.source.officialUrl).toBe(citation.official_url);
          expect(fact.source.locator).toContain(citation.cells);
        } else if (citation.kind === "derived") {
          expect(Number(citation.recorded_value)).toBe(fact.amountThousands);
          for (const input of JSON.parse(citation.inputs ?? "[]") as string[]) {
            if (/^[a-f0-9]{16}$/.test(input)) expect(family.citations[input]).toBeDefined();
          }
        }
      }
    }
  });

  it("uses the EX procurement total across budget activities rather than its first row", () => {
    const procurement = record("F015EX");
    const fact = getRecordFact(procurement, 2026, "request")!;
    const components = procurement.componentRows.filter((row) => row.fy === 2026 && row.measure === "request");
    expect(components).toHaveLength(3);
    expect(fact.amountThousands).toBe(3_014_394);
    expect(fact.factId).toBe("4a9ae7cc78dcf0ba");
    expect(components.reduce((sum, row) => sum + row.amountThousands, 0)).toBe(fact.amountThousands);
    expect(fact.amountThousands).not.toBe(components[0].amountThousands);
    expect(procurement.scopeNote).toContain("broader than the price of new aircraft");
  });

  it("preserves separate EX development and procurement records and request components", () => {
    const development = record("0207146F");
    expect(development.identifierKind).toBe("PE");
    expect(getRecordFact(development, 2026, "request")?.amountThousands).toBe(80_445);
    expect(getRecordFact(development, 2026, "request")?.exhibit).toBe("R-1");
    expect(record("F015EX").identifierKind).toBe("BLI");
    expect(getRecordFact(record("F015EX"), 2026, "request")?.exhibit).toBe("P-1");
    const disc = getRecordFact(development, 2026, "disc-request")!;
    const recon = getRecordFact(development, 2026, "reconciliation-request")!;
    expect(disc.amountThousands).toBe(78_345);
    expect(recon.amountThousands).toBe(2_100);
    expect(disc.amountThousands + recon.amountThousands).toBe(getRecordFact(development, 2026, "request")!.amountThousands);
    expect(getRecordFact(record("F015EX"), 2026, "disc-request")).toBeNull();
  });

  it("does not replace missing EPAWSS TOA with the separate J-book zero", () => {
    const epawss = record("0207171F");
    const jbook = getProgramDetails(epawss.slug).summary.cards.find((card) => card.key === "fy2026")!;
    expect(jbook.value).toBe(0);
    expect(jbook.basis).toBe("jbook-detail");
    expect(getRecordFact(epawss, 2026)).toBeNull();
    expect(epawss.absenceNotes.find((note) => note.fy === 2026)?.text).toContain("separate J-book detail figure");
  });

  it("deduplicates shared records and never adds canonical totals to their component rows", () => {
    const selected = [record("F015EX"), record("0207146F")];
    const expected = getFamilyFundingSummary(selected, 2026, "request");
    const repeated = getFamilyFundingSummary([...selected, ...selected], 2026, "request");
    expect(expected.amountThousands).toBe(3_094_839);
    expect(repeated).toEqual(expected);
    expect(repeated.facts).toHaveLength(2);
  });

  it("keeps an incomplete or mixed-basis family total absent", () => {
    expect(getFamilyFundingSummary(family.records, 2026, "request").amountThousands).toBeNull();
    expect(getFamilyFundingSummary(family.records, 2026, "request").missingSlugs).toContain("0207171F");
    expect(getRecordFact(record("F015EX"), 2026, "actuals")).toBeNull();
    const altered: FamilyFundingRecord = { ...record("0207146F"), facts: record("0207146F").facts.map((fact) => ({ ...fact, basis: "jbook-detail" })) };
    expect(getFamilyFundingSummary([altered, record("F015EX")], 2026, "request").amountThousands).toBeNull();
  });
});
