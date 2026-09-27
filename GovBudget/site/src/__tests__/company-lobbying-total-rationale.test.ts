/**
 * The company page's reason for rendering no lobbying "Total" column, bound
 * to the ruling that decides it and to the exporter's note that states it.
 * This is a cross-owner binding, added by the final-fix2 suites pass on
 * 2026-09-26.
 *
 * THE DEFECT. company/[slug]/page.tsx justified hiding the column in two
 * comments by quoting /data/'s fct_influence note: "alternative disclosures —
 * non-additive, never summed". R-DEC-LDATOTAL (final-review rulings,
 * 2026-09-27) rewrote that note in export_site.py's
 * _DATASET_SCOPES["fct_influence"]. After the re-export, /data/ reads "Income
 * and expense are non-additive: a self-filer's expense can include its
 * outside firms' income, so lobbying_total_usd, a plain sum, can
 * double-count." The quoted words then exist nowhere a reader can see them.
 * The Explorer preset's comment had the same defect
 * (explorer-influence-preset.test.ts).
 *
 * WHAT THIS PINS:
 *  - both comments rest on the ruling (R-DEC-LDATOTAL), not on a quote of a
 *    note that another change can rewrite;
 *  - the withdrawn quote is gone from the file;
 *  - the exporter's note still says the one thing the page relies on, that
 *    income and expense are non-additive. The page's suppression and the data
 *    dictionary cannot drift apart silently.
 */
import fs from "fs";
import path from "path";
import { describe, it, expect } from "vitest";

const siteSrc = path.resolve(__dirname, "..");
const repoRoot = path.resolve(siteSrc, "..", "..");
const page = fs.readFileSync(
  path.join(siteSrc, "app", "company", "[slug]", "page.tsx"),
  "utf8",
);

/** The exporter's fct_influence scope, joined from its Python literal pieces. */
function fctInfluenceScope(): string {
  const py = fs.readFileSync(
    path.join(repoRoot, "src", "govbudget", "export_site.py"),
    "utf8",
  );
  const table = py.indexOf("_DATASET_SCOPES: dict[str, str] = {");
  expect(table, "export_site.py must define _DATASET_SCOPES").toBeGreaterThan(-1);
  const m = py.slice(table).match(/^ {4}"fct_influence": \(\n([\s\S]*?)\n {4}\),$/m);
  expect(m, "_DATASET_SCOPES must carry an fct_influence entry").not.toBeNull();
  return [...m![1].matchAll(/"((?:[^"\\]|\\.)*)"/g)].map((x) => x[1]).join("");
}

/** The source between two markers, both required, in order. */
function between(start: string, end: string): string {
  const a = page.indexOf(start);
  expect(a, `company page must contain ${JSON.stringify(start)}`).toBeGreaterThan(-1);
  const b = page.indexOf(end, a);
  expect(b, `company page must contain ${JSON.stringify(end)} after it`).toBeGreaterThan(a);
  return page.slice(a, b);
}

describe("company page — the lobbying Total column's stated reason", () => {
  const blocks: Array<[string, string]> = [
    [
      "the showLobbyingTotal comment",
      between("// Resolve family_obligations_usd from influence rows", "const showLobbyingTotal"),
    ],
    [
      "the suppressed Total header comment",
      between('{/* The "Total" column is SUPPRESSED', "{showLobbyingTotal && ("),
    ],
  ];

  it.each(blocks)("%s cites R-DEC-LDATOTAL, not the rewritten /data/ note", (_name, block) => {
    expect(block).toContain("R-DEC-LDATOTAL");
    expect(block).not.toMatch(/never summed/);
    expect(block).not.toMatch(/alternative disclosures/);
  });

  it("the withdrawn /data/ quote appears nowhere in the file", () => {
    expect(page).not.toMatch(/never summed/);
  });

  it("the exporter's fct_influence note still says income and expense are non-additive", () => {
    const scope = fctInfluenceScope();
    expect(scope).toContain("Income and expense are non-additive");
    expect(scope).not.toMatch(/never summed/);
  });
});
