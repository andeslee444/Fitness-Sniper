import { describe, expect, it } from "vitest";
import { answerSourceExcerpt, formatAnswerBrief } from "@/lib/answer-brief";
import { getF15FamilyData } from "@/lib/f15-family-data";
import { getRecordFact } from "@/lib/f15-family";

describe("reusable answer fiscal and source context", () => {
  it("keeps the exact aggregate, year, status, basis, input receipts and separately cited passage", () => {
    const family = getF15FamilyData();
    const record = family.records.find(item => item.slug === "F015EX")!;
    const fact = getRecordFact(record, 2026)!;
    const passage = record.narratives[0];
    const text = formatAnswerBrief({
      program: { name: record.title, code: record.slug }, factId: fact.factId,
      citation: family.citations[fact.factId],
      figure: { value: fact.amountThousands, units: fact.units, fy: fact.fy, measure: fact.measure, basis: fact.basis, edition: fact.edition },
      passage: { factId: passage.factId, citation: family.citations[passage.factId], body: passage.body },
      permalink: "https://fiscalreceipts.com/families/f-15/?variant=EX&record=F015EX&fy=2026#funding",
    });
    expect(text).toContain("FY2026 request: $3,014,394 thousand");
    expect(text).toContain("Total obligation authority (TOA) · PB2026");
    expect(text).toContain("4a9ae7cc78dcf0ba");
    expect(text).toContain("https://fiscalreceipts.com/fact/03407158");
    expect(text).toContain(passage.factId);
    expect(text).toContain(answerSourceExcerpt(passage.body));
    expect(text).toContain("does not describe each selected funding year");
    expect(text).toContain("not a component cost");
    expect(text).not.toContain("$3.01B");
  });
  it("refuses an anchored passage when source text changed", () => {
    expect(answerSourceExcerpt("Different text.", "aircraft support")).toBeNull();
    const body = "Earlier context. The shipyard improves productivity. Later context.";
    const excerpt = answerSourceExcerpt(body, "shipyard");
    expect(body).toContain(excerpt);
    expect(excerpt).toContain("shipyard");
  });
});
