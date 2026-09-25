/**
 * Task 26 (final review): sentences the branch shipped that the final corpus,
 * or the calendar, makes false — pinned at the source, the way
 * methodology-doc-mirror.test.ts reads page.tsx, because each renders from a
 * branch a unit render cannot reach cheaply (the zero-SAM arm renders only on
 * the live export; /methodology/ is one 1,600-line server component).
 */
import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";

const APP = path.resolve(__dirname, "..", "app");
const read = (...p: string[]) =>
  fs.readFileSync(path.join(APP, ...p), "utf8").replace(/\s+/g, " ");

describe("/companies/ — what a SAM.gov extract would do", () => {
  // Both zero-SAM arms said promoting families to high confidence "would need
  // a SAM.gov entity extract this build does not have". The spike, dim_entities,
  // /methodology/ §4, /companies/families/ and the >0 arm of the same ternary
  // all say the opposite: the registered parent name a tier reads IS the SAM
  // registration, so an extract promotes no tier.
  const src = read("companies", "page.tsx");
  it("never says an extract would promote a family", () => {
    expect(src).not.toMatch(/would need a SAM\.gov/);
    expect(src).not.toMatch(/Promoting (them|the largest)/);
  });
  it("keeps the >0 arm's true reason", () => {
    expect(src).toContain("they promote no tier");
  });
});

describe("/companies/families/ — no universal about /companies/", () => {
  // "Every family on /companies/ still resolves by name inference." — the
  // final export publishes 149 high / 51 medium.
  const src = read("companies", "families", "page.tsx");
  it("derives the name-inferred count instead of claiming every family", () => {
    expect(src).not.toMatch(/Every family on\{" "\}/);
    expect(src).toMatch(/still resolve by name\s+inference/);
  });
});

describe("/methodology/ — sentences the final corpus or the calendar falsified", () => {
  const src = read("methodology", "page.tsx");
  it("does not place DHA's downloaded book among lines that publish no narrative", () => {
    expect(src).not.toMatch(/publish no R-2\/P-40 narrative at all/);
    expect(src).toContain("lines with no extractable R-2/P-40 narrative");
  });
  it("does not tell every page without a flow that its link could not be defended", () => {
    // 102 pages on the run-4 export carry high-confidence links whose awards
    // record no positive obligation at a place of performance.
    expect(src).not.toMatch(/we could not defend the link/);
    expect(src).toContain("Pages outside it say why in place of the flow");
  });
  it("the district lens claims neither a positive obligation nor a view count (round 2, B1)", () => {
    // GA-02 has a page on the strength of 356010's eight transactions, none
    // positive (3 deobligations, 5 at $0; net −$2,328,281.28): no link
    // places obligated dollars there,
    // and the district set spans 317 programs, not the 314 with a view.
    expect(src).not.toMatch(/places obligated dollars there/);
    expect(src).not.toMatch(/-program scope/);
    expect(src).toContain("link records an obligation there");
  });

  it("states where FY2026's data ends, never that the year has yet to close", () => {
    expect(src).not.toMatch(/does not close until September 30/);
    expect(src).toContain("FY2026 award data here runs through ${awardDataThrough}");
  });
});

describe("/program/{peBli}/ — the follow-the-dollar absence reason is the page's own (round 2, B6)", () => {
  // CoverageNote's `absence` defaults to "no-high-link"; a page that stops
  // passing it silently restores "haven't been crosswalked at high confidence"
  // on the 102 pages whose high-confidence links record no place of
  // performance. The type now requires it (coverage-note.tsx); this pins the
  // page's wiring, which vitest does not type-check.
  const page = read("program", "[peBli]", "page.tsx");
  it("derives the reason from the page's own links", () => {
    expect(page).toMatch(/const flowAbsence = flowAbsenceReason\(details\.awards\);/);
  });
  it("hands that reason to the follow-the-dollar empty note", () => {
    const m = /<CoverageNote id="follow-the-dollar" empty ([^>]*)\/>/.exec(page);
    expect(m, "the follow-the-dollar empty note").not.toBeNull();
    expect(m![1]).toContain("absence={flowAbsence}");
  });
});
