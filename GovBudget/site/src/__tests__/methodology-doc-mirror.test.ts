/**
 * /methodology/ §4 and docs/methodology.md §4 are ONE passage, mirrored.
 *
 * ROADMAP #80 fix round 3 (2026-09-11, finding 2). The concentration passage
 * in §4 states the floor a program page publishes an HHI under, and it exists
 * twice: as JSX on the rendered page and as markdown in docs/methodology.md,
 * which ships to readers who never load the site. Round 2 rewrote both by
 * hand and checked the mirror once, off-line; nothing kept them equal
 * afterwards. This does: the §4 passage is extracted from each file, tag-
 * stripped, entity-unescaped and whitespace-normalized, and compared.
 *
 * Scope is §4's concentration passage only — the rest of §4 renders measured
 * figures from build artifacts that no markdown file can carry. A general
 * page↔docs mirror gate is a bigger design; it is on the backlog, not here.
 */
import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";
import { parse } from "node-html-parser";

const SITE = path.resolve(__dirname, "..", "..");
const PAGE = path.join(SITE, "src", "app", "methodology", "page.tsx");
const DOC = path.join(SITE, "..", "docs", "methodology.md");

const HEADING =
  "Contractor concentration is computed on two bases and published on one";

/** Tag-stripped, entity-unescaped, whitespace-normalized. */
const norm = (fragment: string): string =>
  parse(fragment).text.replace(/\s+/g, " ").trim();

/** The slice of a file between two section markers — §4 only. */
const between = (src: string, start: string, end: string): string => {
  const a = src.indexOf(start);
  const b = src.indexOf(end);
  expect(a, `marker not found: ${start}`).toBeGreaterThan(-1);
  expect(b, `marker not found: ${end}`).toBeGreaterThan(a);
  return src.slice(a, b);
};

function pagePassage(): string {
  const section = between(
    fs.readFileSync(PAGE, "utf8"),
    "{/* §4",
    "{/* §5",
  );
  const blocks = [
    ...section.matchAll(/<h3[^>]*>([\s\S]*?)<\/h3>\s*<p[^>]*>([\s\S]*?)<\/p>/g),
  ];
  const block = blocks.find((m) => norm(m[1]) === HEADING);
  expect(
    block,
    `no <h3>${HEADING}</h3> + <p> block inside §4 of methodology/page.tsx`,
  ).toBeDefined();
  // The mirror only holds while the paragraph is plain prose: a JSX
  // expression here renders something markdown cannot carry.
  expect(block![2], "the mirrored paragraph grew a JSX expression").not.toMatch(
    /[{}]/,
  );
  return `${HEADING}. ${norm(block![2])}`;
}

function docPassage(): string {
  const section = between(
    fs.readFileSync(DOC, "utf8"),
    "\n## 4.",
    "\n## 5.",
  );
  const para = section
    .split(/\n[ \t]*\n/)
    .find((p) => p.trimStart().startsWith(`**${HEADING}.**`));
  expect(
    para,
    `docs/methodology.md §4 no longer opens a paragraph with **${HEADING}.**`,
  ).toBeDefined();
  return norm(para!.replace(/\*\*/g, ""));
}

describe("methodology §4 ↔ docs/methodology.md §4", () => {
  it("the contractor-concentration passage is identical on both surfaces", () => {
    expect(docPassage()).toBe(pagePassage());
  });

  it("and that passage states the whole floor, so the markdown stands alone", () => {
    const text = docPassage();
    expect(text).toContain("at least three such awards");
    expect(text).toContain(
      "two or more contractor families holding positive obligations",
    );
    expect(text).toContain("positive net linked dollars");
    // Below the floor the page states the absence — it never substitutes the
    // all-links figure (ROADMAP #80, "publish the smaller true number").
    expect(text).toMatch(/states the absence rather than substituting/);
  });
});

/**
 * Task 29 fix round 1: the company-families passage. The page's census
 * sentence is DERIVED at build (entity-label-margins.mjs), so no markdown can
 * mirror it literally — and the doc kept typing "15 of the 200 families we
 * publish carry…" and a present-tense "The largest is a family that is 97%
 * Raytheon…" after the FY2026 refresh made both false. What CAN be bound is
 * bound: the page's typed lead, the rule clause the helper renders (scoped,
 * at the helper's threshold, over the recompute's published limit), and that
 * any count the doc types is dated.
 */
import {
  NEAR_TIE_MARGIN,
  labelCensusSentence,
} from "@/lib/entity-label-margins.mjs";

describe("methodology §4 company families ↔ docs/methodology.md §4", () => {
  const LEAD = "The tier grades the grouping, never the name.";
  const quotes = (s: string) => s.replace(/[‘’]/g, "'").replace(/[“”]/g, '"');

  function pageTypedLead(): string {
    const src = fs.readFileSync(PAGE, "utf8");
    const m = src.match(
      /<strong>The tier grades the grouping, never the name\.<\/strong>\{" "\}([\s\S]*?)\{\/\*/,
    );
    expect(m, "the company-families lead is no longer where this test reads it").toBeTruthy();
    return quotes(norm(m![1].replace(/\{" "\}/g, " ")));
  }

  function docParagraph(): string {
    const section = between(fs.readFileSync(DOC, "utf8"), "\n## 4.", "\n## 5.");
    const para = section
      .split(/\n[ \t]*\n/)
      .find((p) => p.trimStart().startsWith(`**${LEAD}**`));
    expect(para, `docs §4 no longer opens a paragraph with **${LEAD}**`).toBeDefined();
    return quotes(norm(para!.replace(/\*\*/g, "")));
  }

  /** The published set leg l measures — familylabel-recompute.py's limit. */
  function publishedLimit(): number {
    const py = fs.readFileSync(
      path.join(SITE, "scripts", "gates", "familylabel-recompute.py"),
      "utf8",
    );
    const m = py.match(/^PUBLISHED_LIMIT = (\d+)$/m);
    expect(m, "PUBLISHED_LIMIT not found in familylabel-recompute.py").toBeTruthy();
    return Number(m![1]);
  }

  it("opens with the page's typed sentences", () => {
    expect(docParagraph().startsWith(`${LEAD} ${pageTypedLead()}`)).toBe(true);
  });

  it("states the rule clause the page renders — scoped to the published set, at the helper's threshold", () => {
    const sentence = labelCensusSentence({
      published: publishedLimit(),
      closeMargin: null,
      curated: 0,
      thresholdPct: Math.round(NEAR_TIE_MARGIN * 100),
    });
    const rule = quotes(sentence.slice(0, sentence.indexOf(";")));
    expect(rule.startsWith(`Among the ${publishedLimit()} families we publish,`)).toBe(true);
    expect(docParagraph()).toContain(rule);
  });

  it("types no undated census, and dates the example that prompted the rule", () => {
    const text = docParagraph();
    expect(text).not.toMatch(/\b\d+ of the \d+ families we publish carry\b/);
    for (const m of text.matchAll(/\b\d+ of the \d+\b/g)) {
      const sentence = text.slice(text.lastIndexOf(". ", m.index) + 1, m.index);
      expect(sentence, `undated count "${m[0]}"`).toMatch(/Measured \d{4}-\d{2}-\d{2}/);
    }
    expect(text).toContain('"ROCKWELL COLLINS AUSTRALIA PTY LIMITED" (measured 2026-09-01)');
    expect(text).not.toMatch(/The largest is a family that is/);
  });
});

/**
 * Task 26 (final review): two more §4 passages the branch changed on the page
 * and left behind in the markdown.
 *
 * 1. The company-families tier paragraph said "as on /companies/, every family
 *    of which resolves by name inference — … stated once in the header",
 *    while the final export publishes 149 high / 51 medium families and the
 *    method note sits under the table. The page now states the rule alone;
 *    the markdown carries the same sentence.
 *
 * 2. The budget-to-contract opener: the markdown typed the 2026-09-11 census
 *    (9,587 of 12,595; three paths with no adjudication) while the page
 *    rendered the run-4 export's (9,588 of 12,917; two paths). What the page
 *    derives from site_meta.link_adjudication, the markdown can only copy —
 *    so this binds the copy to the shipped export (ROADMAP #117's census
 *    sentence, and the opener beside it): re-state docs §4 when it reds.
 */
describe("methodology §4 ↔ docs §4 — the Task 26 passages", () => {
  const RULE =
    "Where a whole table is uniform, the per-row chip is suppressed and the method stated once.";
  const docSection = () =>
    norm(between(fs.readFileSync(DOC, "utf8"), "\n## 4.", "\n## 5.").replace(/\*\*/g, ""));
  const pageSection = () =>
    norm(between(fs.readFileSync(PAGE, "utf8"), "{/* §4", "{/* §5"));

  it("the company-family uniform-table rule is the same sentence on both, and names no page as uniform", () => {
    expect(pageSection()).toContain(RULE);
    expect(docSection()).toContain(RULE);
    expect(pageSection()).not.toMatch(/every family of which resolves by name inference/);
    expect(pageSection()).not.toMatch(/stated once in the header/);
  });

  const meta = JSON.parse(
    fs.readFileSync(path.join(SITE, "..", "data", "site", "json", "site_meta.json"), "utf8"),
  ) as {
    link_adjudication: {
      measured_on: string;
      as_of: string;
      published: number;
      adjudicated: number;
      unpinned: number;
      unpinned_tier: string;
      unadjudicated_methods: string[];
      high: {
        published_high: number;
        adjudicated_high: number;
        two_lens_high: number;
        by_path: Record<string, { high: number; adjudicated: number; with_match_basis?: number }>;
      };
    };
  };
  const la = meta.link_adjudication;
  const n = (v: number) => v.toLocaleString("en-US");
  const and = (xs: string[]) =>
    xs.length > 1 ? `${xs.slice(0, -1).join(", ")} and ${xs[xs.length - 1]}` : xs.join("");

  it("the opener states the shipped export's census, in the page's words", () => {
    const doc = docSection();
    expect(doc).toContain(
      `As of ${la.measured_on}, ${n(la.adjudicated)} of the ${n(la.published)} links ` +
        `the crosswalk grades high or medium carry a per-award hand adjudication — ` +
        `the most recent made on ${la.as_of} —`,
    );
    expect(doc).toContain(
      `${n(la.unpinned)} of those found work that could not be pinned to any one ` +
        `program element; those links publish at ${la.unpinned_tier}.`,
    );
    expect(doc).toContain(
      `The ${and(la.unadjudicated_methods)} paths carry no per-link adjudication`,
    );
  });

  it("the High sentence states the shipped export's high census, in the page's words", () => {
    const h = la.high;
    const remainder = Object.entries(h.by_path)
      .filter(([, v]) => v.high > v.adjudicated)
      .map(([m]) => m)
      .sort();
    const doc = docSection();
    expect(doc).toContain(
      `${n(h.adjudicated_high)} of the ${n(h.published_high)} links published at high ` +
        `carry a per-award hand adjudication, ${
          h.two_lens_high === h.adjudicated_high ? `all ${n(h.two_lens_high)}` : n(h.two_lens_high)
        } challenged by two independent adversarial reviewers; the other ` +
        `${n(h.published_high - h.adjudicated_high)} rest on the ${and(remainder)} path`,
    );
    const ann = h.by_path["announcement+lexicon"];
    expect(doc).toContain(
      `Of the ${n(ann.high)} announcement links, a match basis is recorded on ${n(ann.with_match_basis ?? 0)}`,
    );
  });
});
