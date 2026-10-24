/**
 * The correction label for the 2026-10-21 contract-link withdrawal
 * (R-DEC-LINK-2026-10-21 and R-DEC-LINK-2026-10-21-B; owner rule "publish
 * the smaller true number" — shrink the claim AND label it a correction).
 *
 * /about/'s corrections policy states the correction in one paragraph. Its
 * figures are typed in the page, so this test binds each to the ruling seed
 * the withdrawal actually runs on (dbt/seeds/link_line_rulings.csv): the
 * withdrawn total and one count per withdrawn species — the production and
 * long-lead contracts, the F-35 production-support contracts and orders (the
 * B ruling), and the O&M task order's count of awards and lines. A seed that
 * gains or loses a withdrawal, or a species, fails here until the sentence
 * is re-argued.
 *
 * Placed on /about/, not /methodology/ §6: /methodology/ runs within about
 * 40 gzip bytes of a ceiling the next sentence there has to argue a raise
 * for (build gate 1), and the owner's brief rules out raising it.
 */
import fs from "fs";
import path from "path";
import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render } from "@testing-library/react";
import AboutPage from "@/app/about/page";
import { makeProseAllowlist } from "../../scripts/gates/prose-allowlist.mjs";

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
    const support = withdrawn.filter((r) => r.species === "production_associated_support");
    const om = withdrawn.filter((r) => r.species === "om_task_order_on_mod_line");
    // every withdrawn row is one of the three species the sentence names
    expect(production.length + support.length + om.length).toBe(withdrawn.length);
    const omAwards = new Set(om.map((r) => r.award_piid)).size;
    const omLines = new Set(om.map((r) => r.pe_bli)).size;
    // R-DEC-LINK-2026-10-21-B: one award per link, all on F03500, whose
    // programs.json title is "F-35 Modifications" (gate 21 leg q holds the
    // built page's line name to that title)
    expect(new Set(support.map((r) => r.award_piid)).size).toBe(support.length);
    expect([...new Set(support.map((r) => r.pe_bli))]).toEqual(["F03500"]);
    // Review r3-1b M-1: the 10 are 7 definitive contracts and 3 delivery
    // orders (FPDS award type, contracts lake, read 2026-10-21). A DoD PIID
    // carries its instrument type in its 9th character (DFARS 204.1603:
    // C a contract, F an order), so the seed itself says which words are
    // true: "contract or order" while both kinds are among the 10.
    const instruments = [...new Set(support.map((r) => r.award_piid[8]))].sort();
    expect(instruments).toEqual(["C", "F"]);

    const { container } = render(<AboutPage />);
    const el = container.querySelector('[data-correction="link-line-rulings"]');
    expect(el).not.toBeNull();
    const text = (el!.textContent ?? "").replace(/\s+/g, " ").trim();
    // Review r3-1b M-1: the date is the owner rulings' date, said as such.
    // "Correction issued <date>" read as the day readers saw the correction,
    // which is the deploy day, not the day the owner ruled. The date and the
    // plural are the seed's own: one ruled_on over every withdrawal, under
    // more than one ruling id.
    const ruledOn = [...new Set(withdrawn.map((r) => r.ruled_on))];
    expect(ruledOn).toEqual(["2026-10-21"]);
    expect(new Set(withdrawn.map((r) => r.ruling_id)).size).toBeGreaterThan(1);
    expect(text).toContain(
      `Correction (owner rulings of ${ruledOn[0]}): ` +
        `${withdrawn.length} budget-to-contract links were withdrawn`,
    );
    expect(text).not.toContain("Correction issued");
    expect(text).toContain(
      `${production.length} had attributed a production or long-lead contract`,
    );
    // each kind of award the sentence names is one an FPDS description in
    // the B ruling's evidence names
    const kinds: [string, RegExp][] = [
      ["sustainment", /SUSTAINMENT/],
      ["foreign military sales", /\bFMS\b/],
      ["a parts redesign", /REDESIGN/],
      ["helmet displays", /\bHMDS\b/],
      ["long-lead items", /LONG LEAD/],
    ];
    for (const [words, fpds] of kinds) {
      expect(support.some((r) => fpds.test(r.evidence)), words).toBe(true);
    }
    // Review r3-1b M-3: the parenthetical is exactly these kinds, so a kind
    // added to the sentence without its evidence row above fails here
    const named = kinds.map(([words]) => words);
    const parenthetical = `(such as ${named.slice(0, -1).join(", ")} or ${named.at(-1)})`;
    expect(parenthetical).toBe(
      "(such as sustainment, foreign military sales, a parts redesign, helmet displays or long-lead items)",
    );
    expect(text).toContain(
      `${support.length} had attributed an F-35 production-support contract or order ` +
        `${parenthetical} to the F-35 Modifications line;`,
    );
    expect(text).toContain(
      `the other ${om.length} had attributed ${WORDS[omAwards]} operations-and-maintenance ` +
        `support task order to ${WORDS[omLines]} aircraft-modification lines`,
    );
    // the brief's rule 6: nothing was moved onto another line
    expect(text).toContain("No link was moved to another line in their place.");
  });

  /**
   * Review r3-1b M-3: "No link was moved to another line in their place" is
   * true only while nothing that builds, exports or renders the site reads
   * the seed's correct-line column (named below, so that this file is not a
   * hit of its own). 36 of the 41 first-ruling rows fill it, so a model that
   * started re-attributing on it would make the sentence false with every
   * other test green. The seed, its column type in
   * dbt_project.yml and the dbt/Python tests may name the column; the trees
   * that publish may not. A hit here means the sentence must be re-argued.
   */
  it("binds 'No link was moved' to code that never reads the correct-line column", () => {
    const column = ["correct", "line"].join("_");
    const root = path.resolve(__dirname, "../../..");
    const trees = ["dbt/models", "dbt/macros", "src/govbudget", "site/src"];
    const text = /\.(sql|py|ts|tsx|mts|mjs|js|jsx|yml|yaml|json|md|txt|csv)$/;
    const hits: string[] = [];
    const walk = (dir: string) => {
      for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
        const p = path.join(dir, e.name);
        if (e.isDirectory()) {
          if (e.name !== "node_modules" && e.name !== "__pycache__") walk(p);
        } else if (text.test(e.name) && fs.readFileSync(p, "utf8").includes(column)) {
          hits.push(path.relative(root, p));
        }
      }
    };
    for (const t of trees) {
      expect(fs.existsSync(path.join(root, t)), t).toBe(true);
      walk(path.join(root, t));
    }
    expect(hits).toEqual([]);
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

  /**
   * The release proof's P12 build (2026-10-24) failed build gate 2
   * (render-static (b)): "$147.0 " sat outside any [data-amount], and no
   * prose-allowlist entry covered it. It had since review r2 M-1 (4504be40);
   * no full `npm run verify` ran on a build of the page in between, and no
   * unit test applied the gate's rule. This applies it to the rendered page:
   * every currency token outside a cite is a page-scoped allowlist entry for
   * /about/, with the gate's own regex (pinned to render-static.mjs below).
   */
  it("every dollar token outside a cite is allowlisted for /about/, as gate 2 requires", () => {
    const CURRENCY_RE = /\$[\d,]+(\.\d+)?\s*[TBMK]?/g;
    const gate = fs.readFileSync(path.resolve(__dirname, "../../scripts/gates/render-static.mjs"), "utf8");
    expect(gate).toContain(`const CURRENCY_RE = ${CURRENCY_RE.toString()};`);

    const entries = JSON.parse(
      fs.readFileSync(path.resolve(__dirname, "../../scripts/gates/prose-allowlist.json"), "utf8"),
    );
    const allow = makeProseAllowlist(entries);
    expect(allow.shapeErrors).toEqual([]);

    const { container } = render(<AboutPage />);
    const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
    const tokens: string[] = [];
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      if ((n.parentElement as Element | null)?.closest("[data-amount], [data-prose-cite]")) continue;
      tokens.push(...((n.textContent ?? "").match(CURRENCY_RE) ?? []));
    }
    // non-vacuity: the correction's own figure is among the tokens scanned
    expect(tokens.map((t) => t.trim())).toContain("$147.0");
    expect(tokens.filter((t) => !allow.isAllowed("/about/", t))).toEqual([]);
  });
});
