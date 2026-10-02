/**
 * ROADMAP #10 — the /company/ SAM.gov registration line, in BOTH of its states.
 *
 * A family the extract has not reached (or found no public registration
 * for) has no `sam`. These cases pin the absence as hard as the presence,
 * because a line that renders a UEI with no citation, or a heading with no
 * registration, is exactly the cited-or-absent failure this project exists
 * to avoid.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import fs from "fs";
import path from "path";

import { SamRegistrationNote } from "@/components/sam-registration";
import { CitationPanelContext } from "@/components/cite";
import type { EntitySamRegistration } from "@/lib/data";

const sam: EntitySamRegistration = {
  uei: "ZFN2JJXBLZT3",
  legal_business_name: "LOCKHEED MARTIN CORPORATION",
  cage_code: "98897",
  registration_status: "Active",
  registration_expiration_date: "2026-05-14",
  primary_naics: "336411",
  business_types: "For Profit Organization; Manufacturer of Goods",
  retrieved_at: "2026-09-12T14:03:00+00:00",
  fact_id: "abcdef0123456789",
};

function renderNote(value: EntitySamRegistration | undefined, openPanel = vi.fn()) {
  render(
    <CitationPanelContext.Provider value={{ openPanel }}>
      <SamRegistrationNote sam={value} />
    </CitationPanelContext.Provider>,
  );
  return openPanel;
}

/**
 * R-DEC-SAMTEXT: the rule, as ONE string. Every surface that says whose
 * SAM.gov registration a company page shows states exactly this (quotes and
 * whitespace normalized; the page source spells the apostrophe \u2019, the
 * component &rsquo;, the markdown and the Python formula ').
 */
const SAM_RULE =
  "the parent UEI that the family's largest member by obligations reports on its awards" +
  " (the parent on the most of its dollars; the member's own UEI where that parent has none;" +
  " on a member tie, the highest such UEI)";

function norm(s: string): string {
  return s
    .replace(/\\u2019|\u2019|&rsquo;/g, "'")
    .replace(/\s+/g, " ");
}

describe("SamRegistrationNote (ROADMAP #10)", () => {
  it("renders nothing when the extract has not reached this family", () => {
    renderNote(undefined);
    expect(document.querySelector("[data-sam-registration]")).toBeNull();
  });

  it("renders nothing when the fact id is absent (cited-or-absent)", () => {
    renderNote({ ...sam, fact_id: null });
    expect(document.querySelector("[data-sam-registration]")).toBeNull();
  });

  it("renders nothing when the registration carries no status", () => {
    renderNote({ ...sam, registration_status: null });
    expect(document.querySelector("[data-sam-registration]")).toBeNull();
  });

  it("states the registration and denies that it regrades confidence", () => {
    renderNote(sam);
    const note = document.querySelector("[data-sam-registration]")!;
    expect(note.textContent).toContain("ZFN2JJXBLZT3");
    expect(note.textContent).toContain("LOCKHEED MARTIN CORPORATION");
    expect(note.textContent).toContain("CAGE 98897");
    expect(note.textContent).toContain("336411");
    // 2026-05-14 had passed when SAM answered (2026-09-12): "expired", and
    // the status is pinned to that day (ROADMAP #191).
    expect(note.textContent).toContain("Registration Active as of 2026-09-12");
    expect(note.textContent).toContain("expired 2026-05-14");
    expect(note.textContent).not.toContain("expires 2026-05-14");
    // The spike's finding, said on the page: SAM is the ORIGIN of the
    // registered name, not an upgrade to how the family was resolved.
    expect(note.textContent).toMatch(/does not change how this family was resolved/i);
  });

  it("says exactly whose registration it is: the parent UEI the largest member reports (R-DEC-SAMTEXT)", () => {
    // dim_entities joins SAM on max(coalesce(parent_uei, recipient_uei))
    // filter (rk = 1): the parent UEI the family's largest member REPORTS on
    // its awards, not that member's own registration. On the two pages the
    // chain-G export shipped it was never the largest member's own: Boeing's
    // largest member is JJM4FRDZJDX1 and the registration shown is its parent
    // NU2UC8MX6NK1 (itself a member at -$0.8M); Lockheed's is G4KDGE4JFFK7 and
    // the registration shown is ZFN2JJXBLZT3 ($224.0M). The note used to call
    // it "the registration of the family's largest member by obligations".
    renderNote(sam);
    const text = norm(document.querySelector("[data-sam-registration]")!.textContent!);
    expect(text).toContain(`This is the registration of ${SAM_RULE}`);
    expect(text).not.toMatch(/registration of the family's largest member/);
    // The tie-break still names WHICH UEI the max() sorts on: the tied
    // members' registration UEIs, not their own recipient UEIs (the fixture
    // that shows the two readings disagree is tests/test_sam_entities.py::
    // test_dominant_parent_ueis_breaks_an_obligation_tie_the_way_the_mart_does).
    expect(text).toContain("on a member tie, the highest such UEI");
    expect(text).not.toMatch(/registered name is read from/);
    // Still true after the rewording: SAM is joined below worst_confidence in
    // dim_entities and entity_xwalk reads no SAM column.
    expect(text).toMatch(/does not change how this family was resolved/i);
  });

  it("dates SAM's answer on the US Eastern calendar, like export_site does", () => {
    // Batches land just after 00:00 UTC: 2026-10-02T00:17Z is the evening of
    // 2026-10-01 in Washington, and a registration expiring that day had not
    // yet expired when SAM answered.
    renderNote({ ...sam, retrieved_at: "2026-10-02T00:17:58+00:00",
                 registration_expiration_date: "2026-10-01" });
    const note = document.querySelector("[data-sam-registration]")!;
    expect(note.textContent).toContain("Registration Active as of 2026-10-01");
    expect(note.textContent).toContain("expires 2026-10-01");
  });

  it("says \"expires\" only for a date still ahead when SAM answered", () => {
    renderNote({ ...sam, registration_expiration_date: "2027-01-05" });
    const note = document.querySelector("[data-sam-registration]")!;
    expect(note.textContent).toContain("expires 2027-01-05");
    expect(note.textContent).not.toContain("expired");
  });

  it("omits the fields SAM did not answer rather than inventing them", () => {
    renderNote({
      ...sam,
      cage_code: null,
      primary_naics: null,
      business_types: null,
      registration_expiration_date: null,
    });
    const note = document.querySelector("[data-sam-registration]")!;
    expect(note.textContent).toContain("Registration Active");
    expect(note.textContent).not.toMatch(/CAGE|NAICS|Business types|expires/);
  });

  it("the pick rule is one sentence on /company/, /methodology/, docs/methodology.md and the citation formula", () => {
    // The withdrawn identity had a THIRD home: /methodology/ §4 said the
    // published families "carry the SAM.gov registration that name is read
    // from", where "that name" is the family label (rn = 1). The page's
    // clause renders only while companies_with_sam > 0, and the formula is
    // Python, so this reads each source — the way
    // methodology-doc-mirror.test.ts does — and the four move together or red
    // here (R-DEC-SAMTEXT, final review 2026-09-27).
    const root = path.join(__dirname, "..", "..", "..");
    const page = norm(
      fs.readFileSync(
        path.join(__dirname, "..", "app", "methodology", "page.tsx"),
        "utf8",
      ),
    );
    const doc = norm(fs.readFileSync(path.join(root, "docs", "methodology.md"), "utf8"));
    const py = fs.readFileSync(path.join(root, "src", "govbudget", "export_site.py"), "utf8");
    const block = py.match(/^_SAM_REGISTRATION_RULE = \(\n([\s\S]*?)\n\)/m);
    expect(block, "export_site.py must define _SAM_REGISTRATION_RULE").not.toBeNull();
    const formulaRule = norm(
      [...block![1].matchAll(/"((?:[^"\\]|\\.)*)"/g)].map((m) => m[1]).join(""),
    );
    expect(formulaRule).toBe(SAM_RULE);
    for (const [where, text] of [["methodology page", page], ["docs/methodology.md", doc]]) {
      expect(text, where).toContain(`the registration of ${SAM_RULE}`);
      expect(text, where).not.toMatch(/registration that name is read from/);
      expect(text, where).not.toMatch(/registered name is read from/);
      expect(text, where).not.toMatch(/registration of the family's largest member/);
    }
    // The label and the registration are not always one member's: on a
    // tie the label is read from the LOWEST registration UEI, and a curated
    // alias is no registration at all.
    expect(page).toContain(`${SAM_RULE}, not always the one the label came from`);
  });

  it("cites the status through a prose cite, never a data-amount", () => {
    const openPanel = renderNote(sam);
    const cite = screen.getByRole("button");
    expect(cite).toHaveAttribute("data-prose-cite");
    expect(cite).toHaveAttribute("data-fact-id", "abcdef0123456789");
    expect(cite).not.toHaveAttribute("data-amount");
    fireEvent.click(cite);
    expect(openPanel).toHaveBeenCalledWith("abcdef0123456789");
  });
});
