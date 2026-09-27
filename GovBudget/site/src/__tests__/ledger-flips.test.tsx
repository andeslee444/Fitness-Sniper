/**
 * Uncited-ledger clearance flips.
 *
 * 1. DistrictTable — linkable-dollars cells render Cite state A
 *    ([data-fact-id]) when the sidecar carries total_linkable_fact_id, and
 *    honest state C ([data-uncited]) when it is null. Dataset attribute is
 *    fct_district_totals (#51 — the award-distinct headline model, not the
 *    per-program fct_district_programs it supersedes at this grain), never a
 *    hardcoded uncited span.
 * 2. DownloadCards — the "cited" badge is manifest-driven: a dataset shows
 *    the badge IFF it is off the uncited_datasets ledger, so badges flip
 *    automatically when a dataset gains a citation tier.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, render, within } from "@testing-library/react";
import React from "react";
import { DistrictTable } from "@/components/district-table";
import { DownloadCards } from "@/components/download-cards";
import type { DownloadDataset } from "@/components/download-cards";
import type { DistrictIndexRow } from "@/lib/data";

/**
 * Wave 4 item 2: the card list is the exporter's manifest now, not a literal
 * in the component. The fixture stands in for data/site/json/datasets.json —
 * `cited: true` on every row so the flip under test is the LEDGER's, which is
 * what these two cases are about. (Gate 13 leg h checks the real manifest
 * against the built page; this checks the badge rule.)
 */
const INVENTORY: DownloadDataset[] = [
  "budget_lines",
  "dim_geography",
  "fct_budget_to_awards",
  "dim_lobbyists",
].map((name, i) => ({
  name,
  row_count: 100 + i,
  scope: `One row per thing in ${name}.`,
  cited: true,
}));

/** datasets.json's "citations" entry (final review #10(c)): the citation index card reads it. */
const CITATIONS_INDEX = {
  row_count: 9,
  scope: "One row per source citation, keyed by fact_id, in 1 kind: workbook (a President's Budget workbook cell).",
};

function districtRow(overrides: Partial<DistrictIndexRow> = {}): DistrictIndexRow {
  return {
    pop_district: "VA-08",
    pop_state: "VA",
    program_count: 2,
    award_count: 2,
    total_cited_dollars: 70000000,
    total_cited_fact_id: "b".repeat(16),
    total_linkable_dollars: 70000000,
    total_linkable_fact_id: "a".repeat(16),
    ...overrides,
  };
}

describe("DistrictTable linkable dollars — Cite states", () => {
  it("labels the cross-service linked obligations accurately and keeps the money sort and citations", () => {
    const { container } = render(<DistrictTable districts={[
      districtRow({ pop_district: "AL-02", pop_state: "AL", total_linkable_dollars: 100, total_linkable_fact_id: "c".repeat(16) }),
      districtRow({ pop_district: "VA-08", total_linkable_dollars: 200 }),
    ]} />);
    expect(container.textContent).not.toContain("DARPA");
    // Integration 2026-09-25: the merged table keeps this branch's reviewed
    // labels ("Linked place-of-performance $" / "Linked $"), which name the
    // attribution basis; the live branch's "Linked award obligations" did not.
    expect(within(container).getByRole("columnheader", { name: /Linked place-of-performance \$/ })).toBeInTheDocument();
    fireEvent.click(within(container).getByRole("button", { name: "Linked $" }));
    const table = within(container).getByRole("table");
    expect(table).toHaveAttribute("data-sort-order", "total_linkable_dollars:desc");
    const values = [...table.querySelectorAll("tbody [data-amount]")];
    expect(values.map((el) => el.getAttribute("data-fact-id"))).toEqual(["a".repeat(16), "c".repeat(16)]);
    expect(values.every((el) => el.getAttribute("data-dataset") === "fct_district_totals")).toBe(true);
  });

  it("renders state A with the sidecar fact_id and fct_district_totals dataset", () => {
    const { container } = render(
      <DistrictTable districts={[districtRow()]} />,
    );
    const el = container.querySelector("[data-amount]");
    expect(el).not.toBeNull();
    expect(el).toHaveAttribute("data-fact-id", "a".repeat(16));
    expect(el).toHaveAttribute("data-dataset", "fct_district_totals");
    expect(el).not.toHaveAttribute("data-uncited");
  });

  it("renders honest state C when the fact_id is null", () => {
    const { container } = render(
      <DistrictTable
        districts={[districtRow({ total_linkable_fact_id: null })]}
      />,
    );
    const el = container.querySelector("[data-amount]");
    expect(el).not.toBeNull();
    expect(el).toHaveAttribute("data-uncited", "true");
    expect(el).toHaveAttribute("data-dataset", "fct_district_totals");
    expect(el).not.toHaveAttribute("data-fact-id");
  });

  it("renders an em dash (no data-amount) for zero-dollar districts", () => {
    const { container } = render(
      <DistrictTable
        districts={[
          districtRow({ total_linkable_dollars: 0, total_linkable_fact_id: null }),
        ]}
      />,
    );
    expect(container.querySelector("[data-amount]")).toBeNull();
    expect(container.textContent).toContain("—");
  });
});

describe("DownloadCards — manifest-driven cited badges", () => {
  beforeEach(() => {
    // HEAD probe for the asset bundle — resolve ok so cards render enabled.
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true } as Response),
    );
  });

  function cardFor(container: HTMLElement, name: string): HTMLElement {
    const nameEl = [...container.querySelectorAll("span")].find(
      (s) => s.textContent === name,
    );
    expect(nameEl, `card for ${name}`).toBeTruthy();
    return nameEl!.closest("div.rounded-lg") as HTMLElement;
  }

  it("shows the cited badge for a dataset OFF the ledger", () => {
    const { container } = render(
      <DownloadCards
        builtAt="2026-07-01T00:00:00Z"
        inventory={INVENTORY}
        citationsIndex={CITATIONS_INDEX}
        uncitedDatasets={[]}
      />,
    );
    for (const name of ["dim_geography", "fct_budget_to_awards", "dim_lobbyists"]) {
      const card = cardFor(container, name);
      expect(card.textContent, `${name} badge`).toContain("cited");
    }
  });

  it("hides the cited badge for a dataset ON the ledger", () => {
    const { container } = render(
      <DownloadCards
        builtAt="2026-07-01T00:00:00Z"
        inventory={INVENTORY}
        citationsIndex={CITATIONS_INDEX}
        uncitedDatasets={["dim_geography", "dim_lobbyists", "fct_budget_to_awards"]}
      />,
    );
    for (const name of ["dim_geography", "fct_budget_to_awards", "dim_lobbyists"]) {
      const card = cardFor(container, name);
      expect(card.textContent, `${name} badge`).not.toContain("cited");
    }
    // …while workbook-cited datasets keep theirs
    expect(cardFor(container, "budget_lines").textContent).toContain("cited");
  });

  /**
   * Fix-wave round 2 (B4): the PDF line printed site_meta.pdf_count (204, the
   * documents the export run copied) while the shipped pdfs/ directory held
   * 225 (#164). Until the exporter counts or prunes the directory the line
   * states no count — the same "smaller true claim" applied to its size.
   */
  it("states no PDF count, whatever the export carries", () => {
    const { container } = render(
      <DownloadCards
        builtAt="2026-07-01T00:00:00Z"
        inventory={INVENTORY}
        citationsIndex={CITATIONS_INDEX}
        pdfCount={204}
        workbookCount={30}
      />,
    );
    const text = container.textContent!.replace(/\s+/g, " ");
    expect(text).toContain("pdfs/ — SHA-named J-book PDFs");
    expect(text).not.toMatch(/\d+ SHA-named/);
    expect(text).toContain("workbooks/ — 30 R-1/P-1 Excel rollup files");
  });
});
