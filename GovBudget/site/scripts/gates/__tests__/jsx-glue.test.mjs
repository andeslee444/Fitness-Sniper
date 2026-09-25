/**
 * Unit tests for gate 2 leg (sp)'s source scanner (jsx-glue.mjs) — ROADMAP #106.
 *
 * THE DEFECT. /methodology/ rendered "plus 553whose cited record", "ingested
 * for 1,936of them" and "(240at high confidence)"; nine /agency/ pages
 * rendered "OSD's 128programs"; the /years/ balanced-panel caption compiles
 * to "programs present" with no space. The JSX source had every space. Leg
 * (sp) models babel's JSXText cleaner, which KEEPS a first line's leading
 * space — but Next 16's Turbopack transform trims it when the run also
 * carries an HTML character reference (&apos; &rsquo; &ldquo; …). The repo
 * already knew: ba6c7d66 fixed one such site in methodology/page.tsx with
 * the comment "Turbopack drops the leading space of an entity-bearing text
 * chunk after an expression", and a2637af2 fixed the species in one
 * component instead of sweeping it.
 *
 * These pin the shape the rule fires on, the shapes it must not fire on, and
 * — the regression guard — that site/src carries no such site.
 *
 * Run via `npm test` (vitest).
 */

import path from "path";
import { fileURLToPath } from "url";
import { describe, it, expect } from "vitest";
import {
  INLINE_ELEMENTS,
  cleanJsxText,
  findGlueSites,
  findGlueSitesInSource,
  turbopackTrimsLeadingSpace,
} from "../jsx-glue.mjs";

const srcDir = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
  "..",
  "..",
  "src",
);

/** A component whose <p> children are exactly `children` (line 5 onward). */
const wrap = (children) =>
  `export function X({ n }: { n: number }) {\n  return (\n    <p>\n      plus{" "}\n${children}\n    </p>\n  );\n}\n`;

describe("turbopackTrimsLeadingSpace — the shape", () => {
  it("fires on a space-led, multi-line run carrying an entity", () => {
    expect(
      turbopackTrimsLeadingSpace(
        " whose cited record stops in an\n      earlier President&apos;s Budget edition.\n",
      ),
    ).toBe(true);
    expect(turbopackTrimsLeadingSpace(" at high confidence).\n  &ldquo;x&rdquo;")).toBe(true);
    expect(turbopackTrimsLeadingSpace(" programs\n  program&#8217;s")).toBe(true);
    expect(turbopackTrimsLeadingSpace(" x\n  &#x2019;")).toBe(true);
  });

  it("does not fire without an entity — babel and Turbopack agree there", () => {
    expect(
      turbopackTrimsLeadingSpace(
        " program pages in\n      total: the elements the FY2026 workbooks name, plus",
      ),
    ).toBe(false);
  });

  it("does not fire on a single-line run, entity or not", () => {
    expect(turbopackTrimsLeadingSpace(" whose President&apos;s Budget")).toBe(false);
  });

  it("does not fire when the first line is blank — that is cleanJsxText's case", () => {
    const raw = "\n      programs carry an FY2024 figure&rsquo;s\n";
    expect(turbopackTrimsLeadingSpace(raw)).toBe(false);
    expect(cleanJsxText(raw).startsWith("programs")).toBe(true);
  });

  it("a bare ampersand is not a character reference", () => {
    expect(turbopackTrimsLeadingSpace(" RDT & E books\n  more")).toBe(false);
  });
});

describe("findGlueSitesInSource — the entity trim", () => {
  it("reports the /methodology/ shape as entity-trim glue", () => {
    const src = wrap(
      "      {n} whose cited record stops in an\n      earlier President&apos;s Budget edition.",
    );
    const hits = findGlueSitesInSource("fixture.tsx", src, ".");
    expect(hits).toHaveLength(1);
    expect(hits[0].why).toBe("entity-trim");
    expect(hits[0].right.startsWith("whose")).toBe(true);
    expect(hits[0].line).toBe(5);
  });

  it('is silent once the space is an explicit {" "} child', () => {
    const src = wrap(
      '      {n}{" "}whose cited record stops in an\n      earlier President&apos;s Budget edition.',
    );
    expect(findGlueSitesInSource("fixture.tsx", src, ".")).toEqual([]);
  });

  it("is silent on the entity-free multi-line run both compilers keep", () => {
    const src = wrap(
      "      {n} program pages in\n      total: the elements the FY2026 workbooks name.",
    );
    expect(findGlueSitesInSource("fixture.tsx", src, ".")).toEqual([]);
  });

  it("still reports the original newline glue, labelled as such", () => {
    const src = wrap("      {n}\n      programs carry an FY2024 figure.");
    const hits = findGlueSitesInSource("fixture.tsx", src, ".");
    expect(hits).toHaveLength(1);
    expect(hits[0].why).toBe("newline");
  });

  it("a punctuation edge is still not glue, entity or not", () => {
    const src = wrap("      {n}, the edition immediately\n      before this one&rsquo;s.");
    expect(findGlueSitesInSource("fixture.tsx", src, ".")).toEqual([]);
  });
});

/**
 * Task 29S (2026-09-25). The same Turbopack trim, one neighbour over: chain C
 * run 3's built /methodology/ rendered "never the name.</strong>A family’s",
 * "<em>XML</em>mean", "extent_competed</code>(full & open" (ten sites);
 * /fact/ rendered "{id}</span>resolves"; /lineage/ "<em>year</em>axis"; 48
 * /program/ pages "F-35 C2D2</span>is one of the lines". Leg (sp) scoped
 * element neighbours out as layout — true of a block sibling, false of an
 * inline one, whose trimmed space is a missing space in a sentence.
 */
/** A component whose <p> children are exactly `children` (line 4 onward). */
const wrapEl = (children) =>
  `export function X({ t }: { t: string }) {\n  return (\n    <p>\n${children}\n    </p>\n  );\n}\n`;

describe("findGlueSitesInSource — the entity trim after an inline element", () => {
  it("reports the /methodology/ shape: a space-led, multi-line, entity-bearing run after </strong>", () => {
    const src = wrapEl(
      "      <strong>The tier grades the grouping, never the name.</strong> A\n      family&rsquo;s label is the registered parent name.",
    );
    const hits = findGlueSitesInSource("fixture.tsx", src, ".");
    expect(hits).toHaveLength(1);
    expect(hits[0].why).toBe("entity-trim");
    expect(hits[0].left.endsWith("never the name.</strong>")).toBe(true);
    expect(hits[0].right.startsWith("A family")).toBe(true);
    expect(hits[0].line).toBe(4);
  });

  it.each([...INLINE_ELEMENTS])("fires after <%s>", (tag) => {
    const src = wrapEl(
      `      <${tag}>XML</${tag}> mean different\n      things. &ldquo;–&rdquo; is absent.`,
    );
    const hits = findGlueSitesInSource("fixture.tsx", src, ".");
    expect(hits.map((h) => h.why)).toEqual(["entity-trim"]);
  });

  it("the element list is the inline text elements the brief names, no more", () => {
    expect([...INLINE_ELEMENTS].sort()).toEqual(
      ["a", "abbr", "b", "cite", "code", "em", "i", "span", "strong", "sub", "sup"],
    );
  });

  it("fires when the run opens on punctuation — the author typed the space, so its loss is glue", () => {
    // /methodology/ rendered "extent_competed(full & open" and
    // "Defense Research Sciences“zeroed out”".
    for (const run of [
      `<code className="text-xs">extent_competed</code> (full &amp;\n      open / set-aside)`,
      `<em>Defense Research Sciences</em> &ldquo;zeroed out&rdquo; described\n      a renumbering`,
    ]) {
      const hits = findGlueSitesInSource("fixture.tsx", wrapEl(`      ${run}`), ".");
      expect(hits).toHaveLength(1);
    }
  });

  it("fires when the element wraps an expression (/program/'s title span)", () => {
    const src = wrapEl(
      "      <span data-program-name>{t}</span> is one of the lines that\n      funds it, and GAO&rsquo;s work above says nothing.",
    );
    expect(findGlueSitesInSource("fixture.tsx", src, ".")).toHaveLength(1);
  });

  it('is silent once the space is an explicit {" "} child — the #106 idiom', () => {
    const src = wrapEl(
      '      <strong>The tier grades the grouping, never the name.</strong>{" "}A\n      family&rsquo;s label is the registered parent name.',
    );
    expect(findGlueSitesInSource("fixture.tsx", src, ".")).toEqual([]);
  });

  it("is silent after a block-level neighbour — layout, not prose", () => {
    for (const tag of ["div", "p", "ul", "li", "h3", "section"]) {
      const src = wrapEl(
        `      <${tag}>XML</${tag}> mean different\n      things. &ldquo;–&rdquo; is absent.`,
      );
      expect(findGlueSitesInSource("fixture.tsx", src, ".")).toEqual([]);
    }
  });

  it("is silent on the entity-free run both compilers keep", () => {
    const src = wrapEl("      <em>XML</em> mean different\n      things, and absent is absent.");
    expect(findGlueSitesInSource("fixture.tsx", src, ".")).toEqual([]);
  });

  it("is silent on a single-line run, entity or not", () => {
    // The run must END on its line too: a run that is the last child carries
    // the newline before </p>, and that is turbopackTrimsLeadingSpace's
    // multi-line shape.
    const src = wrapEl("      <em>XML</em> mean &ldquo;different&rdquo; things.<br />");
    expect(findGlueSitesInSource("fixture.tsx", src, ".")).toEqual([]);
  });

  it("is silent on /lineage/'s quote-glyph span: a line break is JSX's no-space, and the glyph is meant to touch", () => {
    // lineage-flow.tsx / lineage-rail.tsx render “cited with the open-quote
    // glyph flush against the word. The author wrote a LINE BREAK, not a
    // space, after </span>: nothing was typed, so nothing was trimmed.
    const src = wrapEl(
      '      <span aria-hidden="true" className="not-italic">\n        &#8220;\n      </span>\n      cited',
    );
    expect(findGlueSitesInSource("fixture.tsx", src, ".")).toEqual([]);
  });

  // The glyph fixture above is silent for TWO reasons — the run after </span>
  // starts on a new line, and "cited" carries no entity — so it would stay
  // green with either condition deleted from the rule. Each case below keeps
  // exactly one reason, so each condition is pinned on its own.
  it("the LINE BREAK alone keeps it silent: an entity-bearing run that starts on a new line", () => {
    const src = wrapEl(
      '      <span aria-hidden="true">\n        &#8220;\n      </span>\n      cited&rsquo;s source',
    );
    expect(findGlueSitesInSource("fixture.tsx", src, ".")).toEqual([]);
  });

  it("…and with a same-line space instead, that very run is reported", () => {
    const src = wrapEl(
      '      <span aria-hidden="true">\n        &#8220;\n      </span> cited&rsquo;s\n      source',
    );
    const hits = findGlueSitesInSource("fixture.tsx", src, ".");
    expect(hits).toHaveLength(1);
    expect(hits[0].why).toBe("entity-trim");
  });

  it("the missing ENTITY alone keeps it silent: a space-led multi-line run with none", () => {
    const src = wrapEl(
      '      <span aria-hidden="true">\n        &#8220;\n      </span> cited\n      source',
    );
    expect(findGlueSitesInSource("fixture.tsx", src, ".")).toEqual([]);
  });
});

describe("site/src", () => {
  it("carries no glue site of any kind (#106 fixed five; Task 29S fourteen after inline elements)", () => {
    const { hits, filesScanned } = findGlueSites(srcDir);
    expect(filesScanned).toBeGreaterThan(100);
    expect(hits.map((h) => `${h.file}:${h.line} (${h.why})`)).toEqual([]);
  });
});
