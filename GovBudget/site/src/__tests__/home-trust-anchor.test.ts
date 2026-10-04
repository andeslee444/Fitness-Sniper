/**
 * The home page's trust anchor (families piece 1 final review, T1).
 *
 * It said "every published dataset carries a citation tier", the same claim
 * /methodology/ made as "every published dataset carries a citation tier (the
 * pending ledger is empty)". Task 19 rewrote the /methodology/ twin when
 * p1_era_line_map shipped on the uncited ledger (its rows are decisions, not
 * amounts; /data/ shows it "tier pending"), but the home copy stayed, so the
 * release would have put a false provenance claim on /. The anchor now claims
 * a tier only for datasets that hold amounts, which every uncited dataset so
 * far (p1_era_line_map: no amount column) leaves true.
 */
import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";

const PAGE = path.resolve(__dirname, "..", "app", "page.tsx");

/** The trust-anchor paragraph as rendered: tags drop, whitespace collapses. */
function trustAnchor(): string {
  const src = fs.readFileSync(PAGE, "utf8");
  const a = src.indexOf("All figures are cited to their exact source document");
  expect(a, "home trust anchor not found").toBeGreaterThan(-1);
  const b = src.indexOf("</p>", a);
  return src
    .slice(a, b)
    .replaceAll('{" "}', " ")
    .replace(/<[^>]+>/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

describe("home trust anchor", () => {
  it("no longer claims a citation tier for every published dataset", () => {
    const src = fs.readFileSync(PAGE, "utf8").replace(/\s+/g, " ");
    expect(src).not.toContain("every published dataset carries a citation tier");
  });

  it("claims the tier only for datasets that hold amounts", () => {
    expect(trustAnchor()).toContain(
      "All figures are cited to their exact source document, page, API query, or derived formula — every published dataset that holds amounts carries a citation tier.",
    );
  });
});
