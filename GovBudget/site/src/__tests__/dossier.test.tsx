/**
 * Tests for Task 8a — dossier rendering (cited-or-absent).
 *
 * - parseDossier: structural validation of the wrapped dossier shape.
 * - validateDossierCitations: fact_ids must resolve in citations.json; urls
 *   must be cached research snapshots; ANY violation throws (loud build
 *   error — the site must not render ungated content silently).
 * - dossierFactIds: warehouse fact_ids feed the page citation slice.
 * - <ProgramDossier>: claims render with their citation chips — fact chips
 *   open the citation panel via the existing context, url chips are external
 *   links with the snapshot-title tooltip + retrieved note. Empty sections
 *   render nothing (zero placeholder text).
 */

import { describe, it, expect } from "vitest";
import { render, fireEvent } from "@testing-library/react";
import React from "react";
import {
  parseDossier,
  validateDossierCitations,
  dossierFactIds,
  type DossierFile,
} from "@/lib/dossier";
import { ProgramDossier } from "@/components/program-dossier";
import { CitationPanelContext } from "@/components/cite";

// ── Fixtures ─────────────────────────────────────────────────────────────────

const FACT_ID = "abc123def4567890";
const SNAP_URL =
  "https://www.defensenews.com/2026/06/10/example-hypersonics-article/";

function fixtureDossier(): DossierFile {
  return {
    pe_bli: "0603183D8Z",
    model: "claude-opus-4-8",
    collected_at: "2026-06-13T00:00:00+00:00",
    dossier: {
      what_it_is: {
        claims: [
          {
            text: "The Joint Hypersonics Transition Office coordinates hypersonic technology development.",
            citation: { fact_id: FACT_ID },
          },
        ],
      },
      why_it_matters: {
        claims: [
          {
            text: "FY2026 funding doubles the prior year request.",
            citation: { fact_id: FACT_ID },
          },
        ],
      },
      players: {
        claims: [
          {
            text: "Lobbying filings referenced the program in 2025.",
            citation: { fact_id: FACT_ID },
          },
        ],
      },
      recent_developments: {
        claims: [
          {
            text: "A June 2026 article reported a new flight test.",
            citation: { url: SNAP_URL },
          },
        ],
      },
    },
  };
}

const CITATION_IDS = new Set([FACT_ID]);
const SNAPSHOT_URLS = new Set([SNAP_URL]);

// ── parseDossier ─────────────────────────────────────────────────────────────

describe("parseDossier", () => {
  it("accepts the wrapped fixture shape", () => {
    const raw = JSON.parse(JSON.stringify(fixtureDossier()));
    const file = parseDossier(raw, "0603183D8Z");
    expect(file.pe_bli).toBe("0603183D8Z");
    expect(file.dossier.what_it_is.claims).toHaveLength(1);
  });

  it("REJECTS a pe_bli mismatch", () => {
    const raw = JSON.parse(JSON.stringify(fixtureDossier()));
    expect(() => parseDossier(raw, "9999999999")).toThrow(/REJECTED/);
  });

  it("REJECTS a missing section", () => {
    const raw = JSON.parse(JSON.stringify(fixtureDossier())) as Record<
      string,
      Record<string, unknown>
    >;
    delete raw.dossier.players;
    expect(() => parseDossier(raw, "0603183D8Z")).toThrow(/players/);
  });

  it("REJECTS a claim with empty text", () => {
    const raw = JSON.parse(JSON.stringify(fixtureDossier()));
    raw.dossier.what_it_is.claims[0].text = "  ";
    expect(() => parseDossier(raw, "0603183D8Z")).toThrow(/empty text/);
  });

  it("REJECTS a claim with both fact_id and url", () => {
    const raw = JSON.parse(JSON.stringify(fixtureDossier()));
    raw.dossier.what_it_is.claims[0].citation = {
      fact_id: FACT_ID,
      url: SNAP_URL,
    };
    expect(() => parseDossier(raw, "0603183D8Z")).toThrow(
      /exactly one of fact_id \| url/,
    );
  });

  it("REJECTS a claim with no citation", () => {
    const raw = JSON.parse(JSON.stringify(fixtureDossier()));
    raw.dossier.what_it_is.claims[0].citation = {};
    expect(() => parseDossier(raw, "0603183D8Z")).toThrow(/REJECTED/);
  });
});

// ── validateDossierCitations ─────────────────────────────────────────────────

describe("validateDossierCitations", () => {
  it("passes when every fact_id resolves and every url is a snapshot", () => {
    expect(() =>
      validateDossierCitations(fixtureDossier(), CITATION_IDS, SNAPSHOT_URLS),
    ).not.toThrow();
  });

  it("REJECTS an unresolvable fact_id (loud build error)", () => {
    const file = fixtureDossier();
    file.dossier.why_it_matters.claims[0].citation = {
      fact_id: "ffffffffffffffff",
    };
    expect(() =>
      validateDossierCitations(file, CITATION_IDS, SNAPSHOT_URLS),
    ).toThrow(/does not resolve in citations\.json/);
  });

  it("REJECTS a url that is not a cached snapshot", () => {
    const file = fixtureDossier();
    file.dossier.recent_developments.claims[0].citation = {
      url: "https://example.com/not-a-snapshot/",
    };
    expect(() =>
      validateDossierCitations(file, CITATION_IDS, SNAPSHOT_URLS),
    ).toThrow(/not a cached research snapshot/);
  });
});

// ── dossierFactIds ───────────────────────────────────────────────────────────

describe("dossierFactIds", () => {
  it("collects warehouse fact_ids across all sections (urls excluded)", () => {
    const ids = dossierFactIds(fixtureDossier());
    expect(ids).toEqual([FACT_ID, FACT_ID, FACT_ID]);
  });
});

// ── <ProgramDossier> rendering ───────────────────────────────────────────────

const SNAPSHOT_META = {
  [SNAP_URL]: {
    retrieved_at: "2026-06-13T00:55:48+00:00",
    title: "Example hypersonics article",
  },
};

describe("ProgramDossier", () => {
  it("renders the four section headings and claim texts", () => {
    const { container } = render(
      <ProgramDossier dossier={fixtureDossier()} snapshotMeta={SNAPSHOT_META} />,
    );
    expect(container.textContent).toContain("What it is");
    expect(container.textContent).toContain("Why it matters");
    expect(container.textContent).toContain("Key players");
    expect(container.textContent).toContain("Recent developments");
    expect(container.textContent).toContain(
      "coordinates hypersonic technology development",
    );
  });

  it("fact chips open the citation panel with the claim fact_id", () => {
    let openedWith: string | null = null;
    const { container } = render(
      <CitationPanelContext.Provider
        value={{ openPanel: (id) => { openedWith = id; } }}
      >
        <ProgramDossier
          dossier={fixtureDossier()}
          snapshotMeta={SNAPSHOT_META}
        />
      </CitationPanelContext.Provider>,
    );
    const chip = container.querySelector('[data-dossier-chip="fact"]');
    expect(chip).not.toBeNull();
    expect(chip).toHaveAttribute("data-fact-id", FACT_ID);
    fireEvent.click(chip!);
    expect(openedWith).toBe(FACT_ID);
  });

  it("url chips are external links with snapshot title tooltip + retrieved note", () => {
    const { container } = render(
      <ProgramDossier dossier={fixtureDossier()} snapshotMeta={SNAPSHOT_META} />,
    );
    const chip = container.querySelector('[data-dossier-chip="url"]');
    expect(chip).not.toBeNull();
    expect(chip).toHaveAttribute("href", SNAP_URL);
    expect(chip).toHaveAttribute("target", "_blank");
    expect(chip).toHaveAttribute("rel", expect.stringContaining("noopener"));
    const tooltip = chip!.getAttribute("title")!;
    expect(tooltip).toContain("Example hypersonics article");
    expect(tooltip).toContain("retrieved 2026-06-13");
    expect(chip!.textContent).toContain("retrieved 2026-06-13");
  });

  it("renders NOTHING for empty sections (zero placeholder text)", () => {
    const file = fixtureDossier();
    file.dossier.recent_developments.claims = [];
    const { container } = render(
      <ProgramDossier dossier={file} snapshotMeta={SNAPSHOT_META} />,
    );
    expect(container.textContent).not.toContain("Recent developments");
    expect(
      container.querySelector('[data-dossier-section="recent_developments"]'),
    ).toBeNull();
  });

  // ── #52 fallout: dropped_claims (a correction ships labelled) ──────────────
  //
  // THE REGRESSION THIS GUARDS AGAINST: the #52 evidence-tier fix orphaned 27
  // dossier "players" claims across 5 dossiers. _emit_dossier_sidecars now
  // drops the individual bad claim and keeps the dossier (never the whole
  // file, the way govbudget dossiers collect's stricter file-level rule
  // would) — these tests pin that the PAGE does the same: a dossier that
  // lost claims still renders, and says so, rather than disappearing.

  it("renders a correction note when dropped_claims > 0", () => {
    const file = fixtureDossier();
    file.dropped_claims = 2;
    const { container } = render(
      <ProgramDossier dossier={file} snapshotMeta={SNAPSHOT_META} />,
    );
    const note = container.querySelector('[data-note-kind="scope"]');
    expect(note).not.toBeNull();
    expect(note!.textContent).toContain("2 claims removed");
    expect(note!.textContent).toContain(
      "they cited sources the site could not resolve",
    );
    const hook = container.querySelector("[data-dossier-dropped-claims]");
    expect(hook).toHaveAttribute("data-dossier-dropped-claims", "2");
  });

  it("uses singular phrasing for exactly one dropped claim", () => {
    const file = fixtureDossier();
    file.dropped_claims = 1;
    const { container } = render(
      <ProgramDossier dossier={file} snapshotMeta={SNAPSHOT_META} />,
    );
    expect(container.textContent).toContain("1 claim removed");
    expect(container.textContent).toContain(
      "it cited a source the site could not resolve",
    );
  });

  it("renders no correction note when dropped_claims is 0 or absent", () => {
    const file = fixtureDossier();
    file.dropped_claims = 0;
    const { container } = render(
      <ProgramDossier dossier={file} snapshotMeta={SNAPSHOT_META} />,
    );
    expect(container.querySelector('[data-note-kind="scope"]')).toBeNull();
    expect(container.textContent).not.toContain("removed");

    delete file.dropped_claims;
    const rerendered = render(
      <ProgramDossier dossier={file} snapshotMeta={SNAPSHOT_META} />,
    );
    expect(
      rerendered.container.querySelector('[data-note-kind="scope"]'),
    ).toBeNull();
  });

  it("THE 0603896C shape: a required section emptied by the drop still renders the dossier, with the note, not nothing", () => {
    const file = fixtureDossier();
    file.dossier.players.claims = []; // every players claim was dropped
    file.dropped_claims = 6;
    const { container } = render(
      <ProgramDossier dossier={file} snapshotMeta={SNAPSHOT_META} />,
    );
    // The section disappears (zero placeholder text, same rule as any
    // naturally-empty section) — but the dossier itself, and its other
    // sections, and the correction note, must all still be there.
    expect(
      container.querySelector('[data-dossier-section="players"]'),
    ).toBeNull();
    expect(container.textContent).toContain("What it is");
    expect(container.textContent).toContain("Why it matters");
    expect(container.querySelector('[data-note-kind="scope"]')).not.toBeNull();
    expect(container.textContent).toContain("6 claims removed");
  });

  it("even a dossier with EVERY claim dropped still renders the section and the note, never silently vanishes", () => {
    const file = fixtureDossier();
    file.dossier.what_it_is.claims = [];
    file.dossier.why_it_matters.claims = [];
    file.dossier.players.claims = [];
    file.dossier.recent_developments.claims = [];
    file.dropped_claims = 4;
    const { container } = render(
      <ProgramDossier dossier={file} snapshotMeta={SNAPSHOT_META} />,
    );
    expect(container.querySelector('[data-dossier]')).not.toBeNull();
    expect(container.querySelector('[data-note-kind="scope"]')).not.toBeNull();
    expect(container.textContent).toContain("4 claims removed");
  });

  // ── #56 addendum: dropped_reasons — the note must say the TRUE reason ──────
  //
  // THE REGRESSION THIS GUARDS AGAINST: fact_id_derived() is a stable hash,
  // so a #56 program-key re-key can change WHICH value a citation resolves
  // to WITHOUT the citation ever failing to resolve — the pre-existing
  // #52-only wording ("cited lobbying mentions that did not meet the
  // evidence standard") would be FALSE for this reason (nothing to do with
  // lobbying). dropped_reasons lets the note distinguish them.

  it("says a stale-value reason accurately, not the #52 lobbying wording", () => {
    const file = fixtureDossier();
    file.dropped_claims = 2;
    file.dropped_reasons = { stale_value: 2 };
    const { container } = render(
      <ProgramDossier dossier={file} snapshotMeta={SNAPSHOT_META} />,
    );
    const note = container.querySelector('[data-note-kind="scope"]');
    expect(note).not.toBeNull();
    expect(note!.textContent).toContain("2 claims removed");
    expect(note!.textContent).toContain(
      "they stated figures a later correction changed",
    );
    expect(note!.textContent).not.toContain("lobbying");
  });

  it("singular stale-value phrasing for exactly one dropped claim", () => {
    const file = fixtureDossier();
    file.dropped_claims = 1;
    file.dropped_reasons = { stale_value: 1 };
    const { container } = render(
      <ProgramDossier dossier={file} snapshotMeta={SNAPSHOT_META} />,
    );
    expect(container.textContent).toContain("1 claim removed");
    expect(container.textContent).toContain(
      "it stated a figure a later correction changed",
    );
  });

  it("states BOTH reasons when a dossier has drops from both, each with its own count", () => {
    const file = fixtureDossier();
    file.dropped_claims = 7;
    file.dropped_reasons = { unresolvable_citation: 6, stale_value: 1 };
    const { container } = render(
      <ProgramDossier dossier={file} snapshotMeta={SNAPSHOT_META} />,
    );
    const text = container.textContent!;
    expect(text).toContain("7 claims removed");
    expect(text).toContain("6 cited sources the site could not resolve");
    expect(text).toContain("one stated a figure a later correction changed");
  });

  it("states #52's reason for every drop when dropped_reasons is absent (pre-#56 sidecar)", () => {
    const file = fixtureDossier();
    file.dropped_claims = 3;
    // dropped_reasons intentionally NOT set — a sidecar written before this
    // field existed had only #52's reason: the citation did not resolve.
    const { container } = render(
      <ProgramDossier dossier={file} snapshotMeta={SNAPSHOT_META} />,
    );
    expect(
      container.querySelector("[data-dossier-dropped-claims]")!.textContent,
    ).toBe("3 claims removed: they cited sources the site could not resolve.");
  });

  // R-DEC-DOSSIERDRIFT round 3: the unresolvable_citation clause read "cited
  // lobbying mentions that did not meet the evidence standard", but the
  // exporter drops ANY claim whose citation does not resolve — on
  // /program/1000/ five J-book narrative claims, on /program/ATA000/ and
  // /program/B02100/ one each, on /program/0603467E/ a concentration claim.
  // The note is worded for the check, true of every drop it covers.
  it("never calls an unresolvable drop a lobbying mention (the /program/1000/ shape)", () => {
    const file = fixtureDossier();
    file.dropped_claims = 5;
    file.dropped_reasons = { unresolvable_citation: 5 };
    const { container } = render(
      <ProgramDossier dossier={file} snapshotMeta={SNAPSHOT_META} />,
    );
    const note = container.querySelector("[data-dossier-dropped-claims]")!;
    expect(note.textContent).toBe(
      "5 claims removed: they cited sources the site could not resolve.",
    );
    expect(note.textContent).not.toMatch(/lobbying|evidence standard/);
  });

  // ── R-DEC-DOSSIERDRIFT round 2: contradicts_citation ─────────────────────
  //
  // export-site WITHHOLDS (never rewrites) a claim whose stated figure,
  // concentration word or top family its cited fact's current value does not
  // support, or whose named recipients the page's linked awards do not carry.
  // Before this, the note knew only #52's and #56's reasons: 0602025E would
  // have read "8 claims removed: 4 cited lobbying mentions …" with four
  // removals unexplained, and 0603941D8Z "1 claim removed: did not meet the
  // evidence standard." — no subject. The dossier gate now compares this
  // exact sentence with the sidecar (gate.expected_correction_note).

  function noteText(file: DossierFile): string {
    const { container } = render(
      <ProgramDossier dossier={file} snapshotMeta={SNAPSHOT_META} />,
    );
    const hook = container.querySelector("[data-dossier-dropped-claims]");
    expect(hook).not.toBeNull();
    return hook!.textContent!;
  }

  function withReasons(
    dropped: number,
    reasons: Record<string, number>,
  ): DossierFile {
    // Object.assign: some cases carry a reason lib/dossier.ts's type does
    // not name (the component must still count it).
    return Object.assign(fixtureDossier(), {
      dropped_claims: dropped,
      dropped_reasons: reasons,
    });
  }

  it("explains a single contradicts_citation removal in plain words", () => {
    expect(noteText(withReasons(1, { contradicts_citation: 1 }))).toBe(
      "1 claim removed: it stated a figure, year or recipient its sources do not support.",
    );
  });

  it("names the year: the clause is true of a fiscal-year withhold (1203154SF)", () => {
    // /program/1203154SF/ what_it_is[3] is withheld for its fiscal year alone
    // ("For FY2026 … about $243.3 million" on an FY 2025 glyph): its figure
    // agrees with the cite, so "stated a figure or recipient" named neither
    // thing wrong with it.
    const note = noteText(withReasons(1, { contradicts_citation: 1 }));
    expect(note).toMatch(/\byear\b/);
    expect(noteText(withReasons(2, { contradicts_citation: 2 }))).toBe(
      "2 claims removed: they stated figures, years or recipients their sources do not support.",
    );
  });

  it("explains every removal on the 0602025E shape, each reason with its own count", () => {
    expect(
      noteText(withReasons(8, { contradicts_citation: 4, unresolvable_citation: 4 })),
    ).toBe(
      "8 claims removed: 4 cited sources the site could not resolve; 4" +
        " stated figures, years or recipients their sources do not support.",
    );
  });

  it("the 0603467E shape: one unresolvable concentration claim beside four withheld claims", () => {
    expect(
      noteText(withReasons(5, { contradicts_citation: 4, unresolvable_citation: 1 })),
    ).toBe(
      "5 claims removed: one cited a source the site could not resolve; 4" +
        " stated figures, years or recipients their sources do not support.",
    );
  });

  it("never prints a clause without a subject (the old fallback's grammar break)", () => {
    expect(noteText(withReasons(1, {}))).toBe(
      "1 claim removed: it did not meet the evidence standard.",
    );
    // a reason this component has no words for is still counted, in its own
    // clause, never silently dropped from the explanation
    expect(noteText(withReasons(3, { stale_value: 1, some_new_reason: 2 }))).toBe(
      "3 claims removed: one stated a figure a later correction changed; 2" +
        " did not meet the evidence standard.",
    );
  });

  it("states #52's reason in its round-3 words and keeps #56's sentence as it was", () => {
    expect(noteText(withReasons(7, { unresolvable_citation: 6, stale_value: 1 }))).toBe(
      "7 claims removed: 6 cited sources the site could not resolve; one" +
        " stated a figure a later correction changed.",
    );
    expect(noteText(withReasons(2, { stale_value: 2 }))).toBe(
      "2 claims removed: they stated figures a later correction changed.",
    );
  });
});
