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

/**
 * datasets.json's "citations" entry in the exporter's shape
 * (export_site._citations_index_entry); the citation index card renders its
 * scope (final review #10(c), 2026-09-27).
 */
const CITATIONS_INDEX = {
  row_count: 5,
  scope:
    "One row per source citation, keyed by fact_id, in 2 kinds: jbook_pdf (a" +
    " figure printed in a J-book PDF) and lda_filing (a Senate LDA filing).",
};

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
        citationsIndex={CITATIONS_INDEX}
        uncitedDatasets={[]}
      />,
    );
    const p = [...container.querySelectorAll("p")].find((el) => el.textContent === SCOPE);
    expect(p, "the description paragraph carries the scope verbatim").toBeTruthy();
    expect(p!.querySelectorAll("code")).toHaveLength(6);
    // The citations card's own description (the manifest's citations scope,
    // final review #10(c)): verbatim, and its three identifiers are code too.
    const cit = [...container.querySelectorAll("p")].find((el) =>
      el.textContent?.includes("keyed by fact_id"),
    );
    expect(cit!.textContent).toBe(CITATIONS_INDEX.scope);
    expect([...cit!.querySelectorAll("code")].map((c) => c.textContent)).toEqual([
      "fact_id",
      "jbook_pdf",
      "lda_filing",
    ]);
  });
});

/**
 * Decisions wave fix round 5 (2026-09-26). The R-DEC-130c concentration
 * caveat names the mart's own columns (`member_keys_with_links`, and
 * `links_outside_member_keys` where a code has links under no member's key —
 * export_site._concentration_scope_caveat). The card rendered the caveat as
 * plain text, so gate 27 leg 31 read those names as exposed enums: an
 * un-allowlisted FAIL on /downloads/ (decisions-fix4-export.md). The caveat
 * now goes through withIdentifierCode, as the description already did; the
 * words are the exporter's, byte for byte.
 */
const CAVEAT =
  "7 of its 536 rows are code-level (scope = 'code'): a budget-line code two" +
  " or more programs share. On 3 of them (0145, 3010 and 3215) more than one" +
  " member's key carries links, so the row pools every member key with links" +
  " and describes no single program. On 4 (2101, 2292, 3050 and 4217) one" +
  " member's key carries every link, so the row is that member's figure:" +
  " 2101 is 2101-WPN's, 2292 is 2292-WPN's, 3050 is 3050-OPN's, 4217 is" +
  " 4217-OPN's. On 1 (5555) some links sit under no member's key" +
  " (links_outside_member_keys), so the row describes no single program." +
  " member_keys_with_links counts the member programs whose own key carries" +
  " a published link.";

const JBOOK_CAVEAT =
  "Page resolution is partial: of 17,900 rows carrying a non-zero amount," +
  " 3,407 resolve to a unique PDF page and 6,472 to the first page the amount" +
  " appears on; the remaining 8,021 (45%) resolve to no page and cite their" +
  " XML path instead.";

describe("DownloadCards caveat (fix round 5)", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true } as Response));
  });

  function caveatOf(name: string, caveat: string): HTMLElement {
    const { container } = render(
      <DownloadCards
        builtAt="2026-09-25T00:00:00Z"
        inventory={[{ name, row_count: 536, scope: SCOPE, cited: true, caveat }]}
        citationsIndex={CITATIONS_INDEX}
        uncitedDatasets={[]}
      />,
    );
    const p = container.querySelector<HTMLElement>(`[data-dataset-caveat="${name}"]`);
    expect(p, "the caveat renders").not.toBeNull();
    return p!;
  }

  it("sets the concentration caveat's column names as code, and keeps every word", () => {
    const p = caveatOf("fct_program_concentration", CAVEAT);
    expect(p.textContent).toBe(CAVEAT);
    expect([...p.querySelectorAll("code")].map((c) => c.textContent)).toEqual([
      "links_outside_member_keys",
      "member_keys_with_links",
    ]);
    // Nothing snake_case is left as bare text for leg 31 to read as an enum.
    const bare = [...p.childNodes]
      .filter((n) => n.nodeType === Node.TEXT_NODE)
      .map((n) => n.textContent ?? "")
      .join("");
    expect(bare).not.toMatch(/\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b/);
  });

  it("leaves a caveat with no identifier exactly as prose", () => {
    const p = caveatOf("jbook_details", JBOOK_CAVEAT);
    expect(p.textContent).toBe(JBOOK_CAVEAT);
    expect(p.querySelectorAll("code")).toHaveLength(0);
  });
});
