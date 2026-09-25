/**
 * SubawardCard tests (ROADMAP #84 — subaward as a first-class kind).
 *
 * Links found via an FSRS subaward description used to cite a generic
 * derived crosswalk row; they now carry the record itself: the prime award's
 * USAspending page (USAspending has no subaward-level page), the subaward
 * number, the subawardee, and the basis in words — plus the caveat that the
 * evidence is one hop removed from the award.
 *
 * Integration 2026-09-25: the codex/f15-family-browser branch built the same
 * kind independently ("subaward link evidence"). Its cases are kept below,
 * adapted to this card's props and wording: the fail-closed
 * parseSubawardEvidence guard in front of the card, the panel's degraded
 * state for malformed rows, the panel dispatch with no second official-source
 * link, and the copied footnote's inference / prime-award-context tail.
 */

import React, { useContext } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import {
  SubawardCard,
  parseSubawardEvidence,
} from "@/components/citation-panel/subaward-card";
import {
  CitationPanelProvider,
  parseSubawardBody,
} from "@/components/citation-panel/panel";
import { CitationPanelContext } from "@/components/cite";
import { isSubaward, isAnnouncement } from "@/lib/citations";
import { getCitations, type SubawardCitation, type Citation } from "@/lib/data";
import { citationSourceDocuments } from "@/lib/source-document";
import { footnoteInputFromCitation } from "@/lib/footnote";

vi.mock("@/components/asset-config", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/components/asset-config")>()),
  AssetConfigProvider: ({ children }: { children: React.ReactNode }) => children,
  useAssetUrl: () => (path: string) => path,
  useAssetConfig: () => ({ assetsBaseUrl: "/assets", loaded: true, error: null }),
}));

afterEach(cleanup);

/** The copied-footnote label for this kind (lib/footnote.ts genericSourceLabel). */
const SUBAWARD_SOURCE_LABEL =
  "FSRS subaward record via USAspending; medium-confidence program-link " +
  "inference (URL is prime-award context)";

const KEY = "CONT_AWD_N6833517C0392_9700_-NONE-_-NONE-";
const PRIME_URL = `https://www.usaspending.gov/award/${KEY}/`;
const NUMBER = "000000821";
const SUBAWARDEE = "INTERNATIONAL COMPUTER SCIENCE INSTITUTE";
const FORMULA =
  "crosswalk link: pe_bli=0605502N matched to award PIID N6833517C0392" +
  " via method='subaward+lexicon', confidence='medium'" +
  " (dollars live at award grain in fct_award_transactions)";

const BODY = {
  subaward_number: NUMBER,
  subawardee: SUBAWARDEE,
  match_basis: "subaward-description-exact",
};

describe("SubawardCard", () => {
  it("renders the prime award link under the subaward kind", () => {
    const { container } = render(<SubawardCard url={PRIME_URL} body={BODY} />);

    expect(container.querySelector('[data-cite-kind="subaward"]')).not.toBeNull();
    const link = container.querySelector<HTMLAnchorElement>(
      '[data-testid="subaward-prime-link"]',
    );
    expect(link).not.toBeNull();
    expect(link!.getAttribute("href")).toBe(PRIME_URL);
    expect(link!.textContent).toContain("USAspending");
    expect(link!.getAttribute("rel")).toContain("noopener");
    expect(link!.getAttribute("target")).toBe("_blank");
  });

  it("names the source in words and never as a DoD announcement", () => {
    const { container } = render(<SubawardCard url={PRIME_URL} body={BODY} />);
    expect(container.textContent).toContain("FSRS subaward record");
    expect(container.textContent).not.toContain("contract announcement");
  });

  it("states the subaward number and the subawardee", () => {
    const { container } = render(<SubawardCard url={PRIME_URL} body={BODY} />);
    expect(
      container.querySelector('[data-testid="subaward-number"]')!.textContent,
    ).toBe(NUMBER);
    expect(
      container.querySelector('[data-testid="subaward-subawardee"]')!.textContent,
    ).toBe(SUBAWARDEE);
  });

  it("says the subawardee was not recorded instead of rendering a blank", () => {
    const { container } = render(
      <SubawardCard url={PRIME_URL} body={{ ...BODY, subawardee: null }} />,
    );
    expect(
      container.querySelector('[data-testid="subaward-subawardee"]')!.textContent,
    ).toBe("not recorded");
  });

  it("states the match basis in words", () => {
    const { container } = render(<SubawardCard url={PRIME_URL} body={BODY} />);
    expect(
      container.querySelector('[data-testid="subaward-match-basis"]')!.textContent,
    ).toBe("Matched by: exact subaward description");
  });

  it("says an unrecorded basis is unrecorded, not exact", () => {
    const { container } = render(
      <SubawardCard url={PRIME_URL} body={{ ...BODY, match_basis: null }} />,
    );
    expect(
      container.querySelector('[data-testid="subaward-match-basis"]')!.textContent,
    ).toBe("Matched by: basis not recorded");
  });

  it("tells the reader the evidence is one hop removed and where the record is", () => {
    const { container } = render(<SubawardCard url={PRIME_URL} body={BODY} />);
    const caveat = container.querySelector('[data-testid="subaward-caveat"]')!
      .textContent!;
    expect(caveat).toContain("one hop removed");
    expect(caveat).toContain("Subawards tab");
    expect(caveat).toContain("no page for an individual subaward");
    // dollars never come from this record
    expect(caveat).toContain("award data");
  });

  it("attributes the description to the record, not to the subawardee", () => {
    // An FSRS/FFATA report is filed BY THE PRIME, so the record never
    // establishes that the subawardee described its own work. The caveat says
    // what the record says and no more.
    const { container } = render(<SubawardCard url={PRIME_URL} body={BODY} />);
    const caveat = container.querySelector('[data-testid="subaward-caveat"]')!
      .textContent!;
    expect(caveat).toContain(
      "The subaward's reported description of the work names this program," +
        " and the prime award is linked on that basis",
    );
    expect(caveat).not.toContain("subawardee's");
    expect(caveat).not.toContain("its own work");
  });

  it("makes no naming claim when no match basis was recorded", () => {
    const { container } = render(
      <SubawardCard url={PRIME_URL} body={{ ...BODY, match_basis: null }} />,
    );
    const caveat = container.querySelector('[data-testid="subaward-caveat"]')!
      .textContent!;
    expect(caveat).toContain("No basis was recorded for this match");
    expect(caveat).not.toContain("names this program");
    // the rest of the caveat is unchanged on this path
    expect(caveat).toContain("one hop removed");
    expect(caveat).toContain("Subawards tab");
    expect(caveat).toContain("award data");
  });

  /**
   * Task 26 (polish 7): the naming clause was gated on ANY non-empty basis,
   * so an LLM-judged or future basis token would have licensed "names this
   * program". Only the one basis verify_phase5b1's _SUBAWARD_MATCH_BASES
   * admits — subaward-description-exact — may make that claim.
   */
  it("makes the naming claim only on the exact-description basis", () => {
    const { container } = render(
      <SubawardCard url={PRIME_URL} body={{ ...BODY, match_basis: "llm-description" }} />,
    );
    const caveat = container.querySelector('[data-testid="subaward-caveat"]')!
      .textContent!;
    expect(caveat).not.toContain("names this program");
    // A basis WAS recorded, so the card must not say none was.
    expect(caveat).not.toContain("No basis was recorded");
    expect(caveat).toContain("not an exact description match");
    expect(caveat).toContain("one hop removed");
  });

  it("treats a blank match basis as no basis, in the caveat as in the phrase", () => {
    const { container } = render(
      <SubawardCard url={PRIME_URL} body={{ ...BODY, match_basis: "   " }} />,
    );
    expect(
      container.querySelector('[data-testid="subaward-match-basis"]')!.textContent,
    ).toBe("Matched by: basis not recorded");
    expect(
      container.querySelector('[data-testid="subaward-caveat"]')!.textContent,
    ).toContain("No basis was recorded for this match");
  });

  it("renders the link's method and confidence tier when the row carries it", () => {
    const { container } = render(
      <SubawardCard url={PRIME_URL} body={BODY} formula={FORMULA} />,
    );
    const el = container.querySelector('[data-testid="subaward-formula"]');
    expect(el).not.toBeNull();
    expect(el!.textContent).toContain("subaward+lexicon");
    expect(el!.textContent).toContain("'medium'");
  });

  it("renders no method block when the row carries no formula", () => {
    const { container } = render(<SubawardCard url={PRIME_URL} body={BODY} />);
    expect(container.querySelector('[data-testid="subaward-formula"]')).toBeNull();
  });
});

describe("subaward citation kind", () => {
  // Typed as SubawardCitation so a field the exporter stops emitting shows
  // up here (same reason the announcement fixture is typed, not cast).
  const SUBAWARD_CITATION: SubawardCitation = {
    kind: "subaward",
    amount_text: null,
    amount_thousands: null,
    bottom_pt: null,
    cells: null,
    formula: FORMULA,
    hosted_pdf_url: null,
    inputs: null,
    official_url: PRIME_URL,
    page_height: null,
    page_number: null,
    page_width: null,
    query_body: JSON.stringify({
      match_basis: "subaward-description-exact",
      subaward_number: NUMBER,
      subawardee: SUBAWARDEE,
    }),
    recorded_value: null,
    resolution: null,
    retrieved_at: null,
    sha256: null,
    sheet: null,
    top_pt: null,
    units: null,
    x0: null,
    x1: null,
    xml_path: null,
  };

  it("is recognised by the type guard the panel dispatches on, and not by the announcement one", () => {
    expect(isSubaward(SUBAWARD_CITATION)).toBe(true);
    expect(isAnnouncement(SUBAWARD_CITATION)).toBe(false);
    const derived: Citation = {
      ...SUBAWARD_CITATION,
      kind: "derived",
      formula: FORMULA,
      inputs: "[]",
      recorded_value: "medium",
    };
    expect(isSubaward(derived)).toBe(false);
  });

  it("carries a footnote source label (no fall-through to an unlabelled tier)", () => {
    const input = footnoteInputFromCitation(
      SUBAWARD_CITATION,
      "abcd1234abcd1234",
      {},
    );
    expect(input.sourceLabel).toBe(SUBAWARD_SOURCE_LABEL);
    expect(input.officialUrl).toBe(PRIME_URL);
    expect(input.sha256).toBeNull();
  });
});

describe("parseSubawardBody — the unusable-body path", () => {
  it("returns null for an absent or malformed body", () => {
    expect(parseSubawardBody(null)).toBeNull();
    expect(parseSubawardBody("")).toBeNull();
    expect(parseSubawardBody("{not json")).toBeNull();
    expect(parseSubawardBody("null")).toBeNull();
    expect(parseSubawardBody("[]")).toBeNull();
  });

  it("returns null when subaward_number is missing, blank or not a string", () => {
    expect(parseSubawardBody(JSON.stringify({}))).toBeNull();
    expect(parseSubawardBody(JSON.stringify({ subaward_number: " " }))).toBeNull();
    expect(parseSubawardBody(JSON.stringify({ subaward_number: 821 }))).toBeNull();
  });

  it("parses a usable body and keeps absences absent", () => {
    expect(parseSubawardBody(JSON.stringify({ subaward_number: NUMBER }))).toEqual({
      subaward_number: NUMBER,
      subawardee: null,
      match_basis: null,
    });
    expect(parseSubawardBody(JSON.stringify(BODY))).toEqual(BODY);
  });
});

// ── From codex/f15-family-browser (b803e860), adapted to the merged card ────
//
// A live published row: the fixture is read from the shipped citations, so a
// regenerated export that stops satisfying the guard fails here, not in the
// browser.
const LIVE_FID = "4fe505d824c9f9aa";
const LIVE = getCitations()[LIVE_FID] as SubawardCitation;

function liveCard(citation: SubawardCitation = LIVE) {
  const body = parseSubawardEvidence(citation);
  expect(body).not.toBeNull();
  return render(
    <SubawardCard url={citation.official_url} body={body!} formula={citation.formula} />,
  );
}

function openInPanel(fid: string, citation: SubawardCitation) {
  function Trigger() {
    const { openPanel } = useContext(CitationPanelContext);
    return <button onClick={() => openPanel(fid)}>Inspect link</button>;
  }
  render(
    <CitationPanelProvider citations={{ [fid]: citation }}>
      <Trigger />
    </CitationPanelProvider>,
  );
  fireEvent.click(screen.getByRole("button", { name: "Inspect link" }));
}

describe("subaward link evidence (live rows)", () => {
  it("identifies the source and confidence without treating prime-award context as the subaward receipt", () => {
    liveCard();
    expect(screen.getByText("10977 REL 1")).toBeVisible();
    expect(screen.getByText("VT MILCOM INC.")).toBeVisible();
    const caveat = screen.getByTestId("subaward-caveat").textContent!;
    expect(caveat).toMatch(/publish at\s+medium, never high/);
    expect(caveat).toContain("Contract dollars come from award data, not from this record");
    expect(caveat).toContain("description itself is not reproduced in this receipt");
    expect(caveat).toContain("no page for an individual subaward");
    const link = screen.getByRole("link", { name: /Open the prime award on USAspending/ });
    expect(link).toHaveAttribute("href", LIVE.official_url);
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(citationSourceDocuments(LIVE)).toEqual([]);
  });

  it("supports every currently published subaward identity", () => {
    const rows = Object.values(getCitations()).filter(
      (row): row is SubawardCitation => row.kind === "subaward",
    );
    expect(rows.length).toBeGreaterThan(0);
    for (const row of rows) {
      expect(parseSubawardEvidence(row), row.official_url).not.toBeNull();
      expect(parseSubawardBody(row.query_body), row.official_url).not.toBeNull();
    }
  });

  it.each([
    { query_body: "{" },
    { query_body: "null" },
    { query_body: JSON.stringify({ subaward_number: "", subawardee: "ACME", match_basis: "subaward-description-exact" }) },
    { query_body: JSON.stringify({ subaward_number: "1", subawardee: "ACME", match_basis: "llm-alias" }) },
    { query_body: JSON.stringify({ subaward_number: "1", subawardee: " ", match_basis: "subaward-description-exact" }) },
    { official_url: "https://www.usaspending.gov.evil.example/award/CONT_AWD_N0017818F3011_9700_/" },
    { official_url: "https://www.usaspending.gov/award/CONT_AWD_OTHER_9700_/" },
    { official_url: "https://www.usaspending.gov/award/CONT_AWD_N0017818F3011_9700_/?x=1" },
    { official_url: "https://username@www.usaspending.gov/award/CONT_AWD_N0017818F3011_9700_/" },
    { recorded_value: "100" },
    { amount_text: "$100" },
    { amount_thousands: 1 },
    { units: "USD" },
    { formula: null },
    { formula: LIVE.formula!.replace("confidence='medium'", "confidence='high'") },
  ])("fails visibly for malformed evidence %j", (changes) => {
    const malformed = { ...LIVE, ...changes } as unknown as SubawardCitation;
    expect(parseSubawardEvidence(malformed)).toBeNull();
    openInPanel(LIVE_FID, malformed);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "This subaward citation could not be read.",
    );
    expect(screen.queryByTestId("subaward-card")).toBeNull();
    expect(screen.queryByRole("link", { name: /prime award/i })).toBeNull();
  });

  it("opens the typed evidence reader through the ordinary receipt panel", () => {
    openInPanel(LIVE_FID, LIVE);
    expect(screen.getByText("FSRS Subaward Record")).toBeVisible();
    expect(screen.getByText("10977 REL 1")).toBeVisible();
    expect(screen.queryByText("Unknown citation kind.")).toBeNull();
    // One official-source action: the card's prime-award link, never a
    // second footer link (the receipt reader dropped the footer link).
    expect(screen.queryByTestId("official-source")).toBeNull();
    expect(screen.getAllByRole("link", { name: /prime award/i })).toHaveLength(1);
  });

  it("keeps the inference and prime-award distinction in copied footnotes", () => {
    const input = footnoteInputFromCitation(LIVE, LIVE_FID, {});
    expect(input.sourceLabel).toBe(SUBAWARD_SOURCE_LABEL);
    expect(input.sourceLabel).toContain("medium-confidence program-link inference");
    expect(input.sourceLabel).toContain("prime-award context");
    expect(input.valueText).toBeFalsy();
  });
});
