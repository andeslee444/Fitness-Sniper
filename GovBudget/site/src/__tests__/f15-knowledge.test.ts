import { describe, expect, it } from "vitest";
import { getPrograms } from "@/lib/data";
import { F15_VARIANT_IDS } from "@/lib/f15-family";
import { getF15Knowledge, validateF15Knowledge } from "@/lib/f15-knowledge";
import type { F15Knowledge } from "@/lib/f15-knowledge-types";

const knowledge = getF15Knowledge();
const programSlugs = new Set(getPrograms().map((program) => program.slug));
const sources = new Map(knowledge.sources.map((source) => [source.id, source]));
const topics = ["airframe", "cockpit", "sensors", "support"] as const;
// Some annual reports identify only a year; preserve the precision of the source.
const sourceDate = /^\d{4}(?:-\d{2}(?:-\d{2})?)?$/;

function mutableKnowledge(): F15Knowledge {
  return JSON.parse(JSON.stringify(knowledge)) as F15Knowledge;
}

describe("F-15 public knowledge and provenance", () => {
  it("provides one substantive sourced explanation for every variant and model hotspot", () => {
    expect(knowledge.contexts).toHaveLength(24);
    for (const variant of F15_VARIANT_IDS) {
      for (const topic of topics) {
        const matches = knowledge.contexts.filter(
          (context) => context.variant === variant && context.topic === topic,
        );
        expect(matches, `${variant}/${topic}`).toHaveLength(1);
        expect(matches[0].title.trim()).not.toBe("");
        expect(matches[0].text.trim().length).toBeGreaterThanOrEqual(80);
        expect(matches[0].sourceIds.length).toBeGreaterThan(0);
        for (const sourceId of matches[0].sourceIds) {
          expect(
            sources.has(sourceId),
            `${variant}/${topic}: ${sourceId}`,
          ).toBe(true);
        }
      }
    }
    expect(() => validateF15Knowledge(knowledge, programSlugs)).not.toThrow();
  });

  it("dates the evidence review without inventing publication dates for undated sources", () => {
    expect(knowledge.reviewed).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    for (const source of knowledge.sources) {
      expect(source.publisher.trim()).not.toBe("");
      expect(source.title.trim()).not.toBe("");
      expect(new URL(source.url).protocol).toBe("https:");
      expect(source.accessed).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(source.accessed <= knowledge.reviewed, source.id).toBe(true);
      if (source.published !== null) {
        expect(source.published).toMatch(sourceDate);
        expect(source.published <= source.accessed, source.id).toBe(true);
      }
    }
    for (const entry of [...knowledge.operators, ...knowledge.systems]) {
      expect(entry.asOf).toMatch(sourceDate);
      expect(entry.asOf <= knowledge.reviewed, entry.id).toBe(true);
    }
    expect(sources.get("sys-raytheon-apg82")?.published).toBeNull();
  });

  it("distinguishes manufacturer statements from government confirmation", () => {
    for (const id of [
      "sys-bae-flight-controls",
      "sys-raytheon-vx-announcement",
      "sys-lockheed-sniper",
    ]) {
      expect(sources.get(id)?.evidence, id).toBe("manufacturer");
    }
    for (const id of [
      "sys-usaf-f110-contract",
      "sys-usaf-epawss-delivery",
      "sys-ex-msar2023",
    ]) {
      expect(sources.get(id)?.evidence, id).toBe("government");
    }
    const announcedRadar = knowledge.systems.find(
      (system) => system.id === "apg82-vx-announcement",
    )!;
    expect(announcedRadar.category).toBe("development");
    expect(announcedRadar.summary).toMatch(/manufacturer announcement/i);
    expect(announcedRadar.summary).toMatch(/does not establish.*order/i);
    expect(announcedRadar.recordSlugs ?? []).toEqual([]);
  });

  it("resolves every context citation and related link to an actual canonical budget record", () => {
    const entries = [
      ...knowledge.contexts,
      ...knowledge.operators,
      ...knowledge.procurement,
      ...knowledge.systems,
    ];
    for (const entry of entries) {
      expect(entry.sourceIds.length).toBeGreaterThan(0);
      for (const id of entry.sourceIds) expect(sources.has(id), id).toBe(true);
      if ("recordSlugs" in entry) {
        for (const slug of entry.recordSlugs ?? []) {
          expect(programSlugs.has(slug), slug).toBe(true);
        }
      }
    }
  });

  it("retains the scope of money, quantities, approvals, orders and deliveries", () => {
    expect(knowledge.procurement.length).toBeGreaterThan(0);
    for (const event of knowledge.procurement) {
      expect(event.country.trim()).not.toBe("");
      expect(event.date).toMatch(sourceDate);
      expect(event.date <= knowledge.reviewed, event.id).toBe(true);
      expect(event.summary.trim().length).toBeGreaterThan(30);
      if (event.amount !== null) {
        expect(event.amount.trim()).not.toBe("");
        expect(event.amountBasis?.trim().length, event.id).toBeGreaterThan(10);
      }
      if (event.quantity !== null) {
        expect(Number.isFinite(event.quantity), event.id).toBe(true);
        expect(event.quantity, event.id).toBeGreaterThanOrEqual(0);
        expect(event.quantityLabel.trim().length, event.id).toBeGreaterThan(3);
      }
      expect(
        event.sourceIds.some((id) => {
          const evidence = sources.get(id)?.evidence;
          return evidence === "government" || evidence === "manufacturer";
        }),
        `${event.id}: quantities and financial events need a primary source`,
      ).toBe(true);
    }
    const statuses = new Set(
      knowledge.procurement.map((event) => event.status),
    );
    expect(statuses.has("approval")).toBe(true);
    expect(statuses.has("contract")).toBe(true);
    expect(statuses.has("delivery")).toBe(true);
    expect(statuses.has("request")).toBe(true);
  });

  it("does not turn an export component or a documented retrofit into universal installation", () => {
    const system = (id: string) =>
      knowledge.systems.find((entry) => entry.id === id)!;
    expect(system("ge-f110-engine").usVariants).toEqual(["EX"]);
    expect(system("pratt-f100-engine").usVariants).not.toContain("EX");
    expect(system("epawss-system").usVariants).toEqual(["E", "EX"]);
    expect(system("lockheed-legion-pod").usVariants).toEqual(["C"]);
    expect(system("korean-industrial-parts").usVariants).toEqual([]);
    expect(system("korean-industrial-parts").variants.join(" ")).toContain("K");
    expect(system("epawss-system").summary).toMatch(/separate records/i);
  });
});

describe("F-15 knowledge validation rejects misleading or broken evidence", () => {
  it.each(["operators", "systems"] as const)(
    "rejects a future %s snapshot",
    (collection) => {
      const data = mutableKnowledge();
      data[collection][0].asOf = "9999-01-01";
      expect(() => validateF15Knowledge(data, programSlugs)).toThrow(
        "Future context snapshot",
      );
    },
  );

  it("keeps the reported inactive campaign distinct from an operator and its historical proposals", () => {
    const country = knowledge.operators.find(
      (item) => item.id === "indonesia",
    )!;
    expect(country.status).toBe("inactive");
    expect(
      country.sourceIds.some((id) => sources.get(id)?.evidence === "reporting"),
    ).toBe(true);
    expect(
      knowledge.procurement
        .filter((item) => item.country === "Indonesia")
        .every((item) => item.status === "approval" || item.status === "plan"),
    ).toBe(true);
  });
  it("rejects a claim whose source was removed", () => {
    const data = mutableKnowledge();
    data.contexts[0].sourceIds = ["missing-source"];
    expect(() => validateF15Knowledge(data, programSlugs)).toThrow(
      "Unresolved claim source",
    );
  });

  it("rejects duplicate variant/topic coverage even when the array still has 24 entries", () => {
    const data = mutableKnowledge();
    data.contexts[1] = { ...data.contexts[0] };
    expect(data.contexts).toHaveLength(24);
    expect(() => validateF15Knowledge(data, programSlugs)).toThrow(
      "Missing substantive context",
    );
  });

  it("rejects replacing a real explanation with an unmapped placeholder", () => {
    const data = mutableKnowledge();
    data.contexts[0].text = "Configuration funding explanation is not mapped.";
    expect(() => validateF15Knowledge(data, programSlugs)).toThrow(
      "Missing substantive context",
    );
  });

  it.each(["accessed", "published"] as const)(
    "rejects a source with a future %s date",
    (field) => {
      const data = mutableKnowledge();
      data.sources[0][field] = "9999-01-01";
      expect(() => validateF15Knowledge(data, programSlugs)).toThrow(
        "Future-dated source",
      );
    },
  );

  it("rejects presenting a future procurement event as an observed event", () => {
    const data = mutableKnowledge();
    data.procurement[0].date = "9999-01-01";
    expect(() => validateF15Knowledge(data, programSlugs)).toThrow(
      "Future event",
    );
  });

  it("rejects a monetary figure without its basis", () => {
    const data = mutableKnowledge();
    data.procurement[0].amount = "$1 million";
    data.procurement[0].amountBasis = null;
    expect(() => validateF15Knowledge(data, programSlugs)).toThrow(
      "Amount has no scope",
    );
  });

  it.each([Number.NaN, -1])("rejects invalid quantity %s", (quantity) => {
    const data = mutableKnowledge();
    data.procurement[0].quantity = quantity;
    expect(() => validateF15Knowledge(data, programSlugs)).toThrow(
      "Quantity has no scope",
    );
  });

  it("rejects a quantity whose unit or scope label was removed", () => {
    const data = mutableKnowledge();
    data.procurement[0].quantity = 12;
    data.procurement[0].quantityLabel = "";
    expect(() => validateF15Knowledge(data, programSlugs)).toThrow(
      "Quantity has no scope",
    );
  });

  it("rejects a supplier link to a nonexistent budget record", () => {
    const data = mutableKnowledge();
    data.systems[0].recordSlugs = ["invented-record"];
    expect(() => validateF15Knowledge(data, programSlugs)).toThrow(
      "Unresolved related budget record",
    );
  });

  it("rejects duplicate source identities and ambiguous evidence lookup", () => {
    const data = mutableKnowledge();
    data.sources.push({ ...data.sources[0] });
    expect(() => validateF15Knowledge(data, programSlugs)).toThrow(
      "Duplicate source identity",
    );
  });
});
