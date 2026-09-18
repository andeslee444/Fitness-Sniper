/**
 * filings-table.test.tsx — fix round 1, item 1
 * (.superpowers/sdd/2026-09-05-roadmap-completion/task-21c-fix-round-1.md)
 *
 * Review finding: the filter's haystack called companyDisplay() twice per
 * row INSIDE the filter callback of a useMemo keyed on [filings, query,
 * year], so every keystroke re-ran the casing rule ~10,786 times over 5,393
 * rows (13.47 ms/keystroke vs 0.45 ms — 30x). Fix (repo precedent:
 * companies-table.tsx haystacks memo, :285-307): precompute the per-row
 * haystack in a useMemo keyed on [filings] only; the filter is a bare
 * `includes`.
 *
 * Two things to prove:
 *   1. Behaviour is unchanged — a query that matches ONLY the DISPLAY
 *      spelling (not merely a different case of the same substring — the
 *      display rule can also insert whitespace: "AARCORP" -> "AAR Corp",
 *      lib/company-name.mjs's CASED map) still hits.
 *   2. The haystack is not rebuilt per query — companyDisplay's call count
 *      does not grow across query changes.
 *
 * companyDisplay is mocked (spread over the real module) so calls made
 * THROUGH THE companyDisplay IMPORT BINDING are counted. filings-table.tsx
 * is the only file under test that imports companyDisplay directly — table
 * cells go through CompanyName -> companyLabel/displayCompanyName instead
 * (company-name.tsx), a separate, un-mocked binding, so rendering visible
 * rows does not touch this spy. The queries used to test point 2 below
 * still deliberately match zero rows, so no cell renders at all while the
 * count is read — the assertion is about the FILTER path alone.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import type { FilingIndexRow } from "@/lib/data";

const spy = vi.hoisted(() => ({ calls: 0 }));

vi.mock("@/lib/company-name.mjs", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("@/lib/company-name.mjs")>();
  return {
    ...actual,
    companyDisplay: (raw: string) => {
      spy.calls += 1;
      return actual.companyDisplay(raw);
    },
  };
});

import { FilingsTable } from "@/components/filings-table";

function makeFilings(n: number): FilingIndexRow[] {
  // Row 0's raw client_name is "AARCORP" (no space) — the CASED map in
  // lib/company-name.mjs substitutes the spelling entirely, to "AAR Corp"
  // (with a space). A query of "AAR Corp" is therefore NOT a case-only
  // variant of the raw string: it cannot substring-match "AARCORP" at all,
  // only the display spelling. The rest are distinct filler rows so the
  // haystack build has real work to do at the sizes below.
  return Array.from({ length: n }, (_, i) => ({
    client_name: i === 0 ? "AARCORP" : `FILLER CLIENT ${i}`,
    registrant_name: `FILLER REGISTRANT ${i}`,
    filing_uuid: `uuid-${i}`,
    filing_year: "2025",
    filing_type: "Q1",
    has_mentions: false,
    mention_count: 0,
  }));
}

describe("FilingsTable haystack memoization (fix round 1, item 1)", () => {
  beforeEach(() => {
    spy.calls = 0;
  });

  it("a query matching only the DISPLAY spelling (not the raw string) still hits the row", () => {
    const filings = makeFilings(20);
    const { container } = render(<FilingsTable filings={filings} />);
    const input = screen.getByLabelText("Search filings by client or registrant");

    fireEvent.change(input, { target: { value: "AAR Corp" } });

    const rows = container.querySelectorAll("tbody tr[data-sort-value]");
    expect(rows.length).toBe(1);
    expect(rows[0]!.textContent).toContain("AAR Corp");
  });

  it("does not rebuild the haystack across query changes — companyDisplay's call count does not grow", () => {
    const filings = makeFilings(300);
    render(<FilingsTable filings={filings} />);
    const input = screen.getByLabelText("Search filings by client or registrant");

    // Two distinct, zero-match queries — no row renders, so no cell-level
    // rendering could contribute calls either way, and the comparison is
    // purely about the FILTER path across two query changes (the reviewer's
    // method). The mount count itself is not asserted: the pre-fix filter's
    // `if (!q) return true` fast path means an EMPTY initial query calls
    // companyDisplay zero times, so "does it grow at all" only shows up once
    // a query goes non-empty — which is exactly what these two changes do.
    fireEvent.change(input, { target: { value: "zzz-no-match-one" } });
    const afterFirstQuery = spy.calls;
    expect(screen.getByText("No filings match.")).toBeTruthy();

    fireEvent.change(input, { target: { value: "zzz-no-match-two" } });
    const afterSecondQuery = spy.calls;
    expect(screen.getByText("No filings match.")).toBeTruthy();

    // Fixed behaviour: the haystack useMemo is keyed on [filings] only, built
    // once at mount, so neither keystroke calls companyDisplay again — both
    // counts hold at whatever the mount build already produced. Unfixed,
    // EACH non-empty-query keystroke re-filters all 300 rows and calls
    // companyDisplay per row all over again, so the second query's count
    // would be strictly greater than the first's (roughly double).
    expect(afterSecondQuery).toBe(afterFirstQuery);
  });
});
