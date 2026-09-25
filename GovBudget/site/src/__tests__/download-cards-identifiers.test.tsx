/**
 * /downloads/ card descriptions: schema identifiers render as <code>, and the
 * words do not change (integration 2026-09-25, R-INT-7).
 *
 * The #80 fct_program_concentration scope must name its columns
 * (tests/test_export_site_datasets_manifest.py requires
 * "positive program_dollars_high"), and gate 27 leg 31 reads a snake_case run
 * in prose as an exposed enum. The card now sets each identifier as code. This
 * pins both halves: every identifier is inside <code>, the rendered text is
 * the exporter's scope byte for byte, and nothing that is not a lower-case
 * snake_case or `*_suffix` run leaves the copy gate's scan.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render } from "@testing-library/react";
import React from "react";
import { DownloadCards, withIdentifierCode } from "@/components/download-cards";

const SCOPE =
  "One row per program element carrying at least one published crosswalk" +
  " link, on TWO bases: *_all over every published link (high and medium" +
  " confidence), *_high over high-confidence links alone. hhi_high and" +
  " top_family_high are NULL below the floor: 3 linked awards, 2 families" +
  " holding positive dollars (positive_family_count_high), positive" +
  " program_dollars_high (ROADMAP #80).";

describe("withIdentifierCode", () => {
  it("wraps exactly the identifier runs and keeps every word", () => {
    const { container } = render(<p>{withIdentifierCode(SCOPE)}</p>);
    expect(container.textContent).toBe(SCOPE);
    expect([...container.querySelectorAll("code")].map((c) => c.textContent)).toEqual([
      "*_all",
      "*_high",
      "hhi_high",
      "top_family_high",
      "positive_family_count_high",
      "program_dollars_high",
    ]);
  });

  it("leaves prose, hyphenated words, upper case and plain words in the scan", () => {
    const text = "High-confidence links. DISTINCT awards; NULL rows. A Foo_Bar label.";
    const { container } = render(<p>{withIdentifierCode(text)}</p>);
    expect(container.querySelectorAll("code")).toHaveLength(0);
    expect(container.textContent).toBe(text);
  });
});

describe("DownloadCards description", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true } as Response));
  });

  it("renders the manifest scope with its identifiers as code", () => {
    const { container } = render(
      <DownloadCards
        builtAt="2026-09-25T00:00:00Z"
        inventory={[{ name: "fct_program_concentration", row_count: 536, scope: SCOPE, cited: true }]}
        uncitedDatasets={[]}
      />,
    );
    const p = [...container.querySelectorAll("p")].find((el) => el.textContent === SCOPE);
    expect(p, "the description paragraph carries the scope verbatim").toBeTruthy();
    expect(p!.querySelectorAll("code")).toHaveLength(6);
    // The citations card's own description: its three identifiers are code too.
    const cit = [...container.querySelectorAll("p")].find((el) =>
      el.textContent?.includes("keyed by fact_id"),
    );
    expect([...cit!.querySelectorAll("code")].map((c) => c.textContent)).toEqual([
      "jbook_pdf",
      "lda_filing",
      "fact_id",
    ]);
  });
});
