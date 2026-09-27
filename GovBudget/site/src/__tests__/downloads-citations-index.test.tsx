/**
 * /downloads/ citation index — the card and the JSON-LD node render the
 * exporter's datasets.json "citations" entry (final integration pass,
 * 2026-09-27; final-review finding #10(c)).
 *
 * THE DEFECT. The card read "All Source citations (jbook_pdf + workbook +
 * lda_filing), keyed by fact_id." and the JSON-LD "citation index mapping
 * fact_ids to source documents — J-book PDF pages, workbook cells, or LDA
 * filings", while citations.parquet holds 10 kinds (125,349 rows on chain G).
 * The final fix taught the exporter to write the index's own entry into
 * datasets.json (export_site._citations_index_entry: row_count, kinds, and a
 * scope sentence glossing every kind), but both site strings stayed
 * hand-written, so the entry reached no page.
 *
 * WHAT THIS PINS
 *  - the card's description IS the entry's scope, byte for byte, identifiers
 *    set as <code> (gate 27 leg 31), with the entry's row count;
 *  - `citationsIndexOf` fails the build on a datasets.json without the entry
 *    (as getDatasetManifest does on a wrong schema_version) instead of letting
 *    a page fall back to a hand-written list of kinds;
 *  - the page source authors no list of kinds and feeds the entry to both the
 *    JSON-LD node and the cards.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render } from "@testing-library/react";
import React from "react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { DownloadCards } from "@/components/download-cards";
import { citationsIndexOf } from "@/lib/data";
import type { CitationsIndexEntry, DatasetManifest } from "@/lib/data";

/** The exporter's shape (tests/test_export_site_datasets_manifest.py pins it). */
const ENTRY: CitationsIndexEntry = {
  file: "citations.parquet",
  row_count: 6,
  kinds: [
    { kind: "workbook", row_count: 3 },
    { kind: "lda_filing", row_count: 2 },
    { kind: "announcement", row_count: 1 },
  ],
  scope:
    "One row per source citation, keyed by fact_id, in 3 kinds: workbook (a" +
    " President's Budget workbook cell), lda_filing (a Senate LDA filing) and" +
    " announcement (a DoD contract announcement).",
};

const MANIFEST: DatasetManifest = {
  built_at: "2026-09-27T00:00:00Z",
  schema_version: 1,
  datasets: [
    { bytes: 1, cited: true, file: "budget_lines.parquet", name: "budget_lines", row_count: 1, scope: "One row per line." },
  ],
};

describe("citationsIndexOf", () => {
  it("returns the exporter's entry", () => {
    expect(citationsIndexOf({ ...MANIFEST, citations: ENTRY })).toBe(ENTRY);
  });

  it("fails the build when datasets.json carries no citations entry", () => {
    expect(() => citationsIndexOf(MANIFEST)).toThrow(/citations[\s\S]*export-site/);
  });
});

describe("DownloadCards — the citation index card", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true } as Response));
  });

  function citationsCard() {
    const { container } = render(
      <DownloadCards
        builtAt="2026-09-27T00:00:00Z"
        inventory={[]}
        citationsIndex={ENTRY}
        uncitedDatasets={[]}
      />,
    );
    const name = [...container.querySelectorAll("span")].find((s) => s.textContent === "citations");
    expect(name, "the citations card renders").toBeTruthy();
    return name!.closest("div.rounded-lg") as HTMLElement;
  }

  it("renders the entry's scope verbatim, identifiers as code", () => {
    const card = citationsCard();
    const p = [...card.querySelectorAll("p")].find((el) => el.textContent === ENTRY.scope);
    expect(p, "the description is the manifest scope").toBeTruthy();
    expect([...p!.querySelectorAll("code")].map((c) => c.textContent)).toEqual([
      "fact_id",
      "lda_filing",
    ]);
  });

  it("shows the entry's row count and no hand-written list of kinds", () => {
    const card = citationsCard();
    expect(card.textContent).toContain("6 rows");
    expect(card.textContent).not.toContain("jbook_pdf + workbook + lda_filing");
    expect(card.querySelector("a")?.getAttribute("href")).toMatch(/\/citations\/citations\.parquet$/);
  });
});

describe("/downloads/ page source", () => {
  const src = readFileSync(resolve(__dirname, "../app/downloads/page.tsx"), "utf8");
  const card = readFileSync(resolve(__dirname, "../components/download-cards.tsx"), "utf8");

  it("authors no list of citation kinds", () => {
    expect(src).not.toMatch(/J-book PDF pages, workbook cells, or LDA filings/);
    expect(card).not.toMatch(/jbook_pdf \+ workbook \+ lda_filing/);
  });

  it("reads the entry once and feeds it to the JSON-LD node and the cards", () => {
    expect(src).toMatch(/citationsIndexOf\(manifest\)/);
    expect(src).toMatch(/citationsIndex=\{citations\}/);
    expect(src).toMatch(/\$\{citations\.row_count\.toLocaleString\("en-US"\)\} rows\. \$\{citations\.scope\}/);
  });
});
