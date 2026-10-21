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
   * (ATA000) money.
   *
   * The figure is the order's NET obligation over all years, $147,027,390.49
   * (FY2022 $147,169,527.81, FY2023 −$142,137.32), rounded as printed. It is
   * the measured removal from the all-years /district/IN-07/ F-35 row and
   * from the programs.json F-35 concentration dollars (read-only dry
   * evaluations, 2026-10-21; fix-report.md Round 2 and fix-review-r2-2.md).
   * Its gross FY2022 positive obligation, $157,917,295.93, is what the flows
   * row, the IN-07 FY2022 positive figure and the FY2022 concentration shift
   * lose; the owner's rule publishes the smaller true number (controller
   * ruling on review r2 M-1), and the sentence says "net" so it is true of
   * the order as a whole.
   */
  it("states the removed share-numbered order at its net measured figure", () => {
    const PIID = "N0001922F0001";
    const MEASURED_NET_REMOVAL = 147_027_390.49;
    const printed = `$${(MEASURED_NET_REMOVAL / 1e6).toFixed(1)} million`;
    expect(printed).toBe("$147.0 million");

    const { container } = render(<AboutPage />);
    const el = container.querySelector('[data-correction="link-line-rulings"]');
    const text = (el!.textContent ?? "").replace(/\s+/g, " ").trim();
    expect(text).toContain(
      `A Rolls-Royce maintenance order (${PIID}) carrying ${printed} in net ` +
        "obligations, which shares its order number with an F-35 contract, " +
        "was removed from F-35 figures on the money-flow, district and " +
        "concentration views.",
    );
    // the gross FY2022 figure is the larger number; it is not printed
    expect(text).not.toContain("$157.9 million");
  });
});
