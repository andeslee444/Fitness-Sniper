/**
 * ROADMAP #134 (decided 2026-09-25, owner delegated to the controller's
 * recommendation): the date the footer and the program print byline stamp is
 * the site BUILD's (site_meta.json built_at), not a date the data is current
 * to — on the chain C run 4 build it read 2026-09-25 while the newest
 * subawards download was 2026-06-11. "Data as of <date>" and "Site export
 * <date>" both read as a currency claim; the ruling's wording is "Built
 * <date>". The footer keeps its dataset clause ("Source dates vary by
 * dataset."), which is the true half of the old sentence. (The /methodology/
 * header is the prose integrator's, not this test's.)
 *
 * Source-level, like gate-count.test.ts's §3 check: the footer lives in the
 * root layout, which reads site_meta.json at module scope and renders <html>.
 */
import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";

const SRC = path.resolve(__dirname, "..");
const read = (rel: string) => fs.readFileSync(path.join(SRC, rel), "utf8").replace(/\s+/g, " ");

describe("the build date is stamped as a build date (#134)", () => {
  it("the footer says Built <date> and keeps the dataset clause", () => {
    const layout = read("app/layout.tsx");
    expect(layout).toMatch(/<>Built <time dateTime=\{builtAt\}>/);
    expect(layout).toContain("Source dates vary by dataset.");
    expect(layout).not.toMatch(/Site export <time|[Dd]ata as of/);
  });

  it("the program print byline says built <date>, not site export", () => {
    const page = read("app/program/[peBli]/page.tsx");
    const start = page.indexOf("<p data-print-only");
    expect(start).toBeGreaterThan(-1);
    const byline = page.slice(start, page.indexOf("</p>", start));
    expect(byline).toMatch(/— built\{" "\} \{new Date\(getSiteMeta\(\)\.built_at\)/);
    expect(byline).not.toMatch(/site export|[Dd]ata as of/);
  });
});
