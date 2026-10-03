#!/usr/bin/env node
/**
 * f15-page-snapshot.mjs — normalized snapshot of the built /families/f-15/ page.
 *
 * Spec 2026-10-02-era-procurement-history-design.md §6.2: the F-15 page must
 * not change while procurement history before FY2024 lands (S0–S4). A raw
 * HTML diff is useless for that proof — chunk names, CSS-module hashes and
 * the build id change with any code change anywhere — so this reduces the
 * page to what a reader and a citation check can see:
 *
 *   - every element carrying data-fact-id (count + distinct ids),
 *   - data-dataset counts,
 *   - occurrences of the family entity string "family:f-15",
 *   - every 16-hex fact-id token anywhere in the HTML, including the RSC
 *     (Flight) payload — the F-15 browser's records ship there, so an era
 *     fact leaking into loadRecord shows up here even when it is not in the
 *     initially rendered DOM,
 *   - the funding matrix: columns, the annual total row, and each program
 *     row's label and cells (fact id, display text, inputs, missing marker).
 *
 * Usage (from GovBudget/site):
 *   node scripts/f15-page-snapshot.mjs out/families/f-15/index.html
 *   node scripts/f15-page-snapshot.mjs out/families/f-15/index.html --out ../tests/fixtures/f15/page_snapshot.json
 *   node scripts/f15-page-snapshot.mjs out/families/f-15/index.html --check ../tests/fixtures/f15/page_snapshot.json
 *
 * --check exits 1 and names the first differing path when the snapshot of
 * the page differs from the committed baseline.
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { parse } from "node-html-parser";

export const SNAPSHOT_SCHEMA = 1;

// A fact id is 16 lowercase hex characters. Decimal fractions in inline
// styles ("0.6682583630407969") are excluded by the "." look-behind.
const FACT_TOKEN_RE = /(?<![0-9A-Za-z.])[0-9a-f]{16}(?![0-9A-Za-z])/g;

const attr = (el, name) => el?.getAttribute(name) ?? null;

function sortedCounts(values) {
  const counts = {};
  for (const value of values) counts[value] = (counts[value] ?? 0) + 1;
  return Object.fromEntries(Object.entries(counts).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)));
}

function cellOf(td, columnAttr) {
  const figure = td.querySelector("[data-fact-id]");
  const inputs = attr(td, "data-history-inputs");
  return {
    column: attr(td, columnAttr),
    fact_id: attr(figure, "data-fact-id"),
    dataset: attr(figure, "data-dataset"),
    text: figure ? figure.text.trim() : td.text.trim(),
    inputs: inputs ? inputs.split(",") : [],
    missing: attr(td.querySelector("[data-history-missing]"), "data-history-missing"),
  };
}

/** Reduce a built /families/f-15/ HTML document to its normalized snapshot. */
export function snapshotF15Page(html) {
  const root = parse(html);
  const section = root.querySelector('section[data-family-history="f-15"]');
  if (!section) throw new Error('f15-page-snapshot: no section[data-family-history="f-15"] in the page');
  const factElements = root.querySelectorAll("[data-fact-id]");
  const tokens = html.match(FACT_TOKEN_RE) ?? [];
  const rows = section.querySelectorAll("tr[data-history-program]").map((tr) => ({
    program_id: attr(tr, "data-history-program"),
    label: tr.querySelector("th").childNodes.filter((node) => node.nodeType === 1).map((node) => node.text.trim()),
    cells: tr.querySelectorAll("td[data-history-cell]").map((td) => cellOf(td, "data-history-cell")),
  }));
  if (rows.length === 0) throw new Error("f15-page-snapshot: the funding matrix has no program rows");
  return {
    schema: SNAPSHOT_SCHEMA,
    page: "/families/f-15/",
    data_fact_id_elements: factElements.length,
    data_fact_ids: [...new Set(factElements.map((el) => attr(el, "data-fact-id")))].sort(),
    data_dataset_counts: sortedCounts(root.querySelectorAll("[data-dataset]").map((el) => attr(el, "data-dataset"))),
    family_f15_occurrences: html.split("family:f-15").length - 1,
    page_fact_id_occurrences: tokens.length,
    page_fact_ids: [...new Set(tokens)].sort(),
    matrix: {
      columns: section.querySelectorAll("th[data-history-column]").map((th) => attr(th, "data-history-column")),
      annual: section.querySelectorAll("td[data-history-annual]").map((td) => cellOf(td, "data-history-annual")),
      rows,
    },
  };
}

/** First path at which two JSON values differ, or null when they are equal. */
export function firstDifference(a, b, at = "$") {
  if (Object.is(a, b)) return null;
  if (typeof a !== typeof b || a === null || b === null || typeof a !== "object" || Array.isArray(a) !== Array.isArray(b)) {
    return `${at}: ${JSON.stringify(a)} != ${JSON.stringify(b)}`;
  }
  const keys = Array.isArray(a)
    ? [...Array(Math.max(a.length, b.length)).keys()]
    : [...new Set([...Object.keys(a), ...Object.keys(b)])].sort();
  for (const key of keys) {
    const found = firstDifference(a[key], b[key], Array.isArray(a) ? `${at}[${key}]` : `${at}.${key}`);
    if (found) return found;
  }
  return null;
}

function main(argv) {
  const [input, flag, target] = argv;
  if (!input || (flag && !["--out", "--check"].includes(flag)) || (flag && !target)) {
    console.error("usage: node scripts/f15-page-snapshot.mjs <index.html> [--out FILE | --check FILE]");
    return 2;
  }
  const snapshot = snapshotF15Page(fs.readFileSync(input, "utf8"));
  const text = JSON.stringify(snapshot, null, 2) + "\n";
  if (flag === "--out") {
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, text);
    console.log(`f15-page-snapshot: wrote ${target} (${snapshot.data_fact_id_elements} data-fact-id elements, ${snapshot.page_fact_ids.length} distinct page fact ids, ${snapshot.matrix.rows.length} matrix rows)`);
    return 0;
  }
  if (flag === "--check") {
    const diff = firstDifference(JSON.parse(fs.readFileSync(target, "utf8")), snapshot);
    if (diff) {
      console.error(`f15-page-snapshot: FAIL — differs from ${target} at ${diff}`);
      return 1;
    }
    console.log(`f15-page-snapshot: PASS — equal to ${target}`);
    return 0;
  }
  process.stdout.write(text);
  return 0;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exit(main(process.argv.slice(2)));
}
