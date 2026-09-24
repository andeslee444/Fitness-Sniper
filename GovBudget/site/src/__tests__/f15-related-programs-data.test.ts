import { afterEach, describe, expect, it, vi } from "vitest";
import * as data from "@/lib/data";
import { F15_RECORD_SLUGS } from "@/lib/f15-family";
import { getF15RelatedPrograms, validateF15RelatedPrograms } from "@/lib/f15-related-programs-data";
import type { F15RelatedProgram } from "@/lib/f15-related-programs";

const rows = getF15RelatedPrograms();
const subjectIndex = rows.findIndex(row => row.identifier === "000071");
const copy = (): F15RelatedProgram[] => structuredClone(rows);
afterEach(() => vi.restoreAllMocks());

describe("reviewed F-15 shared-program evidence", () => {
  it("preserves all 30 published and six historical relationships without budget amounts", () => {
    expect(rows).toHaveLength(36);
    expect(rows.filter(row => row.factId)).toHaveLength(30);
    expect(rows.filter(row => row.factId === null && row.slug !== null)).toHaveLength(4);
    expect(rows.filter(row => row.slug === null)).toHaveLength(2);
    expect(new Set(rows.map(row => row.identifier)).size).toBe(36);
    expect(rows).toEqual([...rows].sort((a, b) => b.sourceEdition - a.sourceEdition || a.title.localeCompare(b.title) || a.identifier.localeCompare(b.identifier)));
    for (const row of rows) {
      expect(F15_RECORD_SLUGS).not.toContain(row.identifier);
      expect(Object.keys(row).sort()).toEqual(["association", "excerpt", "factId", "identifier", "locator", "officialUrl", "pageNumber", "slug", "sourceEdition", "title"]);
      expect(row.excerpt.length).toBeLessThanOrEqual(400);
    }
    expect(() => validateF15RelatedPrograms(rows)).not.toThrow();
  });

  it("preserves exact public receipt identities, source pages and source-edition limits", () => {
    expect(rows.filter(row => row.pageNumber !== null)).toHaveLength(16);
    for (const row of rows) {
      if (row.factId === null) {
        expect(row.sourceEdition).toBeLessThan(2026);
        expect(row.association).toContain(`PB${row.sourceEdition}`);
        continue;
      }
      expect(row.sourceEdition).toBe(2026);
      const narrative = data.getProgramDetails(row.slug!).narratives.find(item => item.fact_id === row.factId)!;
      const citation = data.getCitation(row.factId)!;
      expect(narrative.body.replace(/\s+/g, " ")).toContain(row.excerpt);
      expect(row.excerpt).not.toBe(narrative.body);
      expect(citation.official_url).toBe(row.officialUrl);
      expect(citation.page_number).toBe(row.pageNumber);
      expect(citation.xml_path).toBe(row.locator);
    }
    expect(rows.find(row => row.identifier === "000999")?.association).toContain("no FY2026 F-15EX spares funding");
    expect(rows.find(row => row.identifier === "0604735F")?.association).toContain("FY2027");
  });

  it("rejects a changed passage instead of attaching a real receipt to unsupported text", () => {
    const changed = copy();
    changed[subjectIndex].excerpt = "F-15 aircraft receive all of this program's funding.";
    expect(() => validateF15RelatedPrograms(changed)).toThrow("excerpt is absent");
  });

  it("rejects another program's receipt and missing canonical membership", () => {
    const changed = copy();
    changed[subjectIndex].factId = rows.find(row => row.identifier === "000075")!.factId;
    expect(() => validateF15RelatedPrograms(changed)).toThrow("not a narrative of this exact program");
    const missing = copy();
    missing[subjectIndex].slug = "invented-program";
    expect(() => validateF15RelatedPrograms(missing)).toThrow("canonical program identity");
  });

  it("requires the actual published receipt and prevents downgrading it to historical evidence", () => {
    const missing = copy();
    missing[subjectIndex].factId = null;
    expect(() => validateF15RelatedPrograms(missing)).toThrow("published narrative receipt is missing");
    const original = data.getCitation;
    vi.spyOn(data, "getCitation").mockImplementation(id => id === rows[subjectIndex].factId ? undefined : original(id));
    expect(() => validateF15RelatedPrograms(rows)).toThrow("published narrative receipt is missing");
  });

  it("rejects a wrong source edition or government PDF identity", () => {
    const changed = copy();
    changed[subjectIndex].sourceEdition = 2025;
    expect(() => validateF15RelatedPrograms(changed)).toThrow("source edition disagrees");
    const wrongUrl = copy();
    wrongUrl[subjectIndex].officialUrl = wrongUrl[subjectIndex].officialUrl.replace("Vol%20I.pdf", "Vol%20II.pdf");
    expect(() => validateF15RelatedPrograms(wrongUrl)).toThrow("receipt URL, page or XML identity");
  });

  it("rejects changed PDF pages and XML locators", () => {
    const changed = copy();
    changed[subjectIndex].pageNumber! += 1;
    changed[subjectIndex].officialUrl = changed[subjectIndex].officialUrl.replace(/#page=\d+$/, `#page=${changed[subjectIndex].pageNumber}`);
    expect(() => validateF15RelatedPrograms(changed)).toThrow("receipt URL, page or XML identity");
    const locator = copy();
    locator[subjectIndex].locator = "LineItem[999]";
    expect(() => validateF15RelatedPrograms(locator)).toThrow("receipt URL, page or XML identity");
  });

  it("requires an identical receipt in the prefix shard that the browser will request", () => {
    expect(() => validateF15RelatedPrograms(rows, () => ({}))).toThrow("missing or changed in its citation shard");
    const citations = data.getCitations();
    expect(() => validateF15RelatedPrograms(rows, prefix => Object.fromEntries(
      Object.entries(citations).filter(([id]) => id.startsWith(prefix)).map(([id, citation]) => [id, id === rows[subjectIndex].factId && citation.kind === "jbook_narrative" ? { ...citation, xml_path: "changed" } : citation]),
    ))).toThrow("missing or changed in its citation shard");
  });

  it("rejects dedicated-family overlaps and duplicate shared program rows", () => {
    const changed = copy();
    changed[subjectIndex].slug = "F015EX";
    changed[subjectIndex].identifier = "F015EX";
    expect(() => validateF15RelatedPrograms(changed)).toThrow("dedicated family record");
    expect(() => validateF15RelatedPrograms([...rows, rows[subjectIndex]])).toThrow("duplicate or missing program identity");
  });

  it("does not manufacture receipts or canonical links for imported historical evidence", () => {
    const changed = copy();
    changed.find(row => row.factId === null)!.factId = rows[subjectIndex].factId;
    expect(() => validateF15RelatedPrograms(changed)).toThrow("historical evidence has no published receipt");
    const hiddenLink = copy();
    hiddenLink.find(row => row.factId === null && row.slug !== null)!.slug = null;
    expect(() => validateF15RelatedPrograms(hiddenLink)).toThrow("historical source identity");
  });
});
