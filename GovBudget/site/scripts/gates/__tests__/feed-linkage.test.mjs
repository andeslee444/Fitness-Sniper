import assert from "node:assert/strict";
import { it as test } from "vitest";
import { JSDOM } from "jsdom";
import { companyLinkageReference, runLinkageLeg } from "../feed.mjs";
import { FR_NS, escapeXml } from "../../../src/lib/feed-model.mjs";

const entity = {
  slug: "raytheon",
  display_name: "RAYTHEON COMPANY",
  label: "Raytheon Company registrations",
  family_key: "RAYTHEON",
};
const details = {
  awards: [{ pe_bli: "0207134F", confidence: "high" }],
  linked_programs: [{ pe_bli: "0603000F" }],
};

function inspect({
  source = entity,
  name = "Raytheon Company registrations",
  basis = ["award"],
  pe = "0207134F",
  includeLinkage = true,
} = {}) {
  const reference = companyLinkageReference(source, details);
  const target = {
    kind: "company",
    key: source.slug,
    rssPath: `/feeds/company/${source.slug}.xml`,
    items: [{ guid: "fixture-item", card: { pe_bli: pe } }],
  };
  const linkage = includeLinkage
    ? `<fr:linkage entity="${escapeXml(name)}">${basis.map(id => `<fr:basis id="${escapeXml(id)}"/>`).join("")}</fr:linkage>`
    : "";
  const dom = new JSDOM(
    `<rss xmlns:fr="${FR_NS}"><channel><item><guid>fixture-item</guid><title>Budget change</title>${linkage}</item></channel></rss>`,
    { contentType: "application/xml" },
  );
  const errors = [];
  const notes = [];
  try {
    runLinkageLeg(errors, notes, [target], new Map([[target.rssPath, dom.window.document]]), new Map([[source.slug, reference]]));
    return { errors, notes };
  } finally {
    dom.window.close();
  }
}

test("accepts the exact curated entity label with an independently supported award link", () => {
  const result = inspect();
  assert.deepEqual(result.errors, []);
  assert.ok(result.notes.some(note => note.includes("1 company watch-feed items")));
});

test("rejects registry-only or different-company attribution when the source has a curated label", () => {
  for (const name of ["Raytheon Company", "RTX Corporation", "raytheon company registrations"]) {
    assert.ok(inspect({ name }).errors.some(error => error.includes("attributes its linkage")));
  }
});

test("uses registry-name casing only when no curated source label exists", () => {
  assert.deepEqual(inspect({ source: { ...entity, label: null }, name: "Raytheon Company" }).errors, []);
  assert.ok(inspect({ source: { ...entity, label: null } }).errors.some(error => error.includes("attributes its linkage")));
});

test("still rejects unsupported or missing linkage bases under the correct curated name", () => {
  assert.ok(inspect({ basis: ["mention"] }).errors.some(error => error.includes("overstates the link")));
  assert.ok(inspect({ basis: ["mention"] }).errors.some(error => error.includes("omits linkage basis \"award\"")));
  assert.ok(inspect({ basis: ["ownership"] }).errors.some(error => error.includes("unknown linkage basis")));
  assert.ok(inspect({ basis: [] }).errors.some(error => error.includes("EMPTY linkage block")));
  assert.ok(inspect({ includeLinkage: false }).errors.some(error => error.includes("states no linkage basis")));
});

test("keeps filing mentions distinct from award links when the curated entity label matches", () => {
  assert.deepEqual(inspect({ pe: "0603000F", basis: ["mention"] }).errors, []);
  assert.ok(inspect({ pe: "0603000F", basis: ["award"] }).errors.some(error => error.includes("overstates the link")));
});
