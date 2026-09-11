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

describe("site/src", () => {
  it("carries no glue site of either kind (the #106 sweep fixed five)", () => {
    const { hits, filesScanned } = findGlueSites(srcDir);
    expect(filesScanned).toBeGreaterThan(100);
    expect(hits.map((h) => `${h.file}:${h.line} (${h.why})`)).toEqual([]);
  });
});
