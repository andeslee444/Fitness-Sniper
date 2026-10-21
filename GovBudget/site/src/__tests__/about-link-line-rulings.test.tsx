/**
 * The correction label for the 2026-10-21 contract-link withdrawal
 * (R-DEC-LINK-2026-10-21; owner rule "publish the smaller true number" —
 * shrink the claim AND label it a correction).
 *
 * /about/'s corrections policy states the correction in one paragraph. Its
 * figures are typed in the page, so this test binds each to the ruling seed
 * the withdrawal actually runs on (dbt/seeds/link_line_rulings.csv): the
 * withdrawn total, the production species, and the O&M task order's count
 * of awards and lines. A seed that gains or loses a withdrawal fails here
 * until the sentence is re-argued.
 *
 * Placed on /about/, not /methodology/ §6: /methodology/ runs 77 gzip bytes
 * under a ceiling the next sentence there has to argue a raise for (build
 * gate 1), and the owner's brief rules out raising it.
 */
import fs from "fs";
import path from "path";
import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render } from "@testing-library/react";
import AboutPage from "@/app/about/page";

afterEach(cleanup);

const SEED = path.resolve(__dirname, "../../../dbt/seeds/link_line_rulings.csv");

/** The seed's rows (quoted fields hold commas; no field holds a newline). */
function seedRows(): Record<string, string>[] {
  const [header, ...lines] = fs.readFileSync(SEED, "utf8").trim().split("\n");
  const split = (line: string) =>
    [...line.matchAll(/("([^"]|"")*"|[^,]*)(,|$)/g)]
      .slice(0, header.split(",").length)
      .map(([, v]) => v.replace(/^"|"$/g, "").replace(/""/g, '"'));
  const cols = header.split(",");
  return lines.map((l) => Object.fromEntries(split(l).map((v, i) => [cols[i], v])));
}

const WORDS = ["zero", "one", "two", "three", "four", "five"];

describe("/about/ labels the contract-link withdrawal a correction", () => {
  it("states the seed's own counts", () => {
    const withdrawn = seedRows().filter((r) => r.ruling === "withdraw");
    const production = withdrawn.filter((r) => r.species === "production_on_modification_line");
    const om = withdrawn.filter((r) => r.species === "om_task_order_on_mod_line");
    expect(production.length + om.length).toBe(withdrawn.length);
    const omAwards = new Set(om.map((r) => r.award_piid)).size;
    const omLines = new Set(om.map((r) => r.pe_bli)).size;

    const { container } = render(<AboutPage />);
    const el = container.querySelector('[data-correction="link-line-rulings"]');
    expect(el).not.toBeNull();
    const text = (el!.textContent ?? "").replace(/\s+/g, " ").trim();
    expect(text).toContain("Correction issued 2026-10-21");
    expect(text).toContain(`${withdrawn.length} budget-to-contract links were withdrawn`);
    expect(text).toContain(
      `${production.length} had attributed a production or long-lead contract`,
    );
    expect(text).toContain(
      `the other ${om.length} had attributed ${WORDS[omAwards]} operations-and-maintenance ` +
        `support task order to ${WORDS[omLines]} aircraft-modification lines`,
    );
    // the brief's rule 6: nothing was moved onto another line
    expect(text).toContain("No link was moved to another line in their place.");
  });

  /**
   * R-DEC-LINK-2026-10-21 R4 (controller ruling on review 1 I-4): the same
   * release removes the N0001922F0001 collision from every surface. The PIID
   * is a Lockheed Martin F-35 order and an unrelated Rolls-Royce NASM
   * maintenance order; every PIID-only join published the second as F-35
   * (ATA000) money. The figure is the measured removal, rounded as printed:
   * the Rolls-Royce award's positive obligation, $157,917,295.93 (FY2022) —
   * the row flows/ATA000.json carried, the IN-07 FY2022 positive obligation
   * and the FY2022 F-35 concentration-shift dollars all lose exactly this
   * (read-only dry evaluation, 2026-10-21; fix-report.md Round 2).
   */
  it("states the removed share-numbered order at its measured figure", () => {
    const PIID = "N0001922F0001";
    const MEASURED_REMOVAL = 157_917_295.93;
    const printed = `$${(MEASURED_REMOVAL / 1e6).toFixed(1)} million`;
    expect(printed).toBe("$157.9 million");

    const { container } = render(<AboutPage />);
    const el = container.querySelector('[data-correction="link-line-rulings"]');
    const text = (el!.textContent ?? "").replace(/\s+/g, " ").trim();
    expect(text).toContain(
      `A ${printed} Rolls-Royce maintenance order (${PIID}) that shares its ` +
        "order number with an F-35 contract was removed from F-35 figures on " +
        "the money-flow, district and concentration views.",
    );
  });
});
