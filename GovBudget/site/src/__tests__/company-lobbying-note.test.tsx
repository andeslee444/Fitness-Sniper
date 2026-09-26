/**
 * The company page's lobbying note (decisions wave fix round 4, 2026-09-26).
 *
 * Two sentences under the Lobbying activity table were false:
 *
 *  - "This table shows lobbying activity side by side with federal
 *    obligations" — the table's columns are filing year, filings, income and
 *    expense (and a total only where a row is additive); obligations are
 *    stated elsewhere on the page, never in it. The note now says what the
 *    table gives.
 *  - "Lobbying dollar aggregates carry derived LDA citations. Each figure
 *    opens to its formula and constituent filings." — in the shipped
 *    citations every one of the 630 lobbying citations carried inputs '[]'
 *    (export_site probed lda_filings.parquet for `family_key` / `filing_url`;
 *    the lake names them `family_key_guess` / `url`). R-DEC-LDACITE fixes the
 *    exporter. The page now claims "constituent filings" only when every
 *    lobbying figure the table renders cites at least one LDA filing record,
 *    read from the page's own citation slice — so the sentence is true on an
 *    export either side of that fix.
 *
 * Both branches are forced through the page's citation slice (the real
 * collectCitationsWithInputs, with the lobbying citations' inputs rewritten),
 * so the test holds whichever export is on disk.
 */
import { describe, it, expect, vi } from "vitest";
import { cleanup, render } from "@testing-library/react";
import React from "react";

const mode = vi.hoisted(() => ({ inputs: null as null | "empty" | "filings" }));

vi.mock("@/components/citation-panel", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/components/citation-panel")>()),
  CitationPanelProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/data", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/lib/data")>();
  return {
    ...real,
    collectCitationsWithInputs: (ids: string[]) => {
      const slice = real.collectCitationsWithInputs(ids);
      if (!mode.inputs) return slice;
      const out = { ...slice };
      for (const [fid, c] of Object.entries(out)) {
        if (c.kind === "derived" && /LDA filing/.test(c.formula)) {
          out[fid] = {
            ...c,
            inputs:
              mode.inputs === "filings"
                ? JSON.stringify([`https://lda.senate.gov/api/v1/filings/${fid}/`])
                : "[]",
          };
        }
      }
      return out;
    },
  };
});

const norm = (s: string | null | undefined) => (s ?? "").replace(/\s+/g, " ").trim();

async function lobbyingNote(slug: string) {
  // One render in the document at a time: jsdom resolves "#id" through the
  // document, so a second copy of the page would hide this one's section.
  cleanup();
  const CompanyPage = (await import("@/app/company/[slug]/page")).default;
  const el = await CompanyPage({ params: Promise.resolve({ slug }) });
  const root = render(el as React.ReactElement).container;
  const section = root.querySelector("#lobbying");
  expect(section, `${slug} renders a lobbying section`).not.toBeNull();
  return norm([...section!.querySelectorAll("p")].map((p) => p.textContent).join(" "));
}

describe("company page — the lobbying note says what the table shows (fix round 4)", () => {
  it("names the table's own columns and no obligations column", async () => {
    mode.inputs = null;
    const text = await lobbyingNote("lockheed-martin");
    expect(text).not.toMatch(/side by side with federal obligations/);
    expect(text).toContain("This table gives each filing year's filings, income and expense;");
    expect(text).toContain("lobbying and contracts reflect correlation, not causation.");
  }, 60000);

  it("claims constituent filings only when every lobbying citation lists one", async () => {
    mode.inputs = "filings";
    const withFilings = await lobbyingNote("lockheed-martin");
    expect(withFilings).toContain(
      "Lobbying dollar aggregates carry derived LDA citations. Each figure opens to its formula and constituent filings.",
    );
    mode.inputs = "empty";
    const without = await lobbyingNote("lockheed-martin");
    expect(without).toContain(
      "Lobbying dollar aggregates carry derived LDA citations. Each figure opens to its formula.",
    );
    expect(without).not.toMatch(/constituent filings/);
    mode.inputs = null;
  }, 120000);
});
