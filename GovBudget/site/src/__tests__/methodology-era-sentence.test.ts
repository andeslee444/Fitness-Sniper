/**
 * /methodology/'s "Two honest gaps" paragraph, first gap (families piece 1,
 * spec 2026-10-02 §6.4). The sentence said cross-edition procurement
 * comparisons stop at the PB2024 boundary. Era procurement lines now join a
 * program only through a dated, reviewed decision on the code each P-1
 * printed, and the rest stay data only, so the sentence states that gap, at
 * the replaced sentence's exact rendered byte length: /methodology/ sits near
 * its gate-1 ceiling and only the link markup is new. It must still read as
 * a gap (it opens "Two honest gaps remain"), not as a new capability.
 */
import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";

const PAGE = path.resolve(__dirname, "..", "app", "methodology", "page.tsx");

/** The replaced sentence as rendered (312 UTF-8 bytes). */
const OLD_SENTENCE =
  "First, cross-edition procurement comparisons stop at the PB2024 boundary: PB2017–PB2023 procurement lines are keyed within their own edition (the underlying account/line identity is unstable across those years), so book diffs for the era editions cover RDT&E only — a wrong lineage would be worse than a gap.";

/** Rendered text of the JSX between two markers: {" "} is a space, tags drop,
 *  whitespace collapses, &amp; is &. */
function visible(start: string, end: string): string {
  const src = fs.readFileSync(PAGE, "utf8");
  const a = src.indexOf(start);
  const b = src.indexOf(end, a + start.length);
  expect(a, `marker not found: ${start}`).toBeGreaterThan(-1);
  expect(b, `marker not found: ${end}`).toBeGreaterThan(a);
  return src
    .slice(a, b)
    .replaceAll('{" "}', " ")
    .replace(/<[^>]+>/g, "")
    .replace(/\s+/g, " ")
    .replaceAll("&amp;", "&")
    .trim();
}

describe("/methodology/ era procurement sentence", () => {
  const sentence = visible("Two honest gaps remain. First,", "Second, program elements").replace(
    /^Two honest gaps remain\. /,
    "",
  );

  it("states the gap: era procurement joins a program only by a reviewed decision on the printed code", () => {
    expect(sentence).toContain(
      "PB2017–PB2023 procurement lines join a program only by a dated, reviewed decision on the code their P-1 printed, never by title",
    );
    expect(sentence).toContain("(renames too; published in p1_era_line_map)");
    expect(sentence).toContain("the rest stay data only");
  });

  it("keeps the two statements that stay true", () => {
    expect(sentence).toContain("book diffs for the era editions still cover RDT&E only");
    expect(visible("Second, program elements", "</p>")).toContain(
      "never fuzzy-matches renamed programs across editions",
    );
  });

  it("no longer says comparisons stop at the PB2024 boundary", () => {
    expect(sentence).not.toContain("PB2024 boundary");
  });

  it("is exactly as long as the sentence it replaced", () => {
    expect(Buffer.byteLength(OLD_SENTENCE)).toBe(312);
    expect(Buffer.byteLength(sentence)).toBe(312);
  });

  it("links the map dataset the way the page's other dataset link does", () => {
    const src = fs.readFileSync(PAGE, "utf8");
    expect(src).toContain('<a href="/data/" className="underline hover:text-foreground">p1_era_line_map</a>);');
  });
});
