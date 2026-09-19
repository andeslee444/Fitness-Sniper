/**
 * ROADMAP #10 — the /company/ SAM.gov registration line, in BOTH of its states.
 *
 * The state that ships today is "nothing": no machine holds the SAM.gov key
 * that fills the extract, so every family's `sam` is undefined. These cases
 * pin the absence as hard as the presence, because a line that renders a UEI
 * with no citation, or a heading with no registration, is exactly the
 * cited-or-absent failure this project exists to avoid.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

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
  public_url: "https://sam.gov/entity/ZFN2JJXBLZT3",
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
    expect(note.textContent).toContain("expires 2026-05-14");
    // The spike's finding, said on the page: SAM is the ORIGIN of the
    // registered name, not an upgrade to how the family was resolved.
    expect(note.textContent).toMatch(/does not change how this family was resolved/i);
  });

  it("claims the dominant member with the mart's own tie-break, not the heading", () => {
    // dim_entities takes display_name from rn = 1 and the registration from
    // max(uei) filter (rk = 1): on an exact obligation tie those are two
    // different members, so the note may not say this registration is the one
    // the family's displayed name was read from (46 families tie in the lake,
    // 0 published today — the sentence has to be true before that changes).
    renderNote(sam);
    const text = document.querySelector("[data-sam-registration]")!.textContent!;
    expect(text).toContain("largest member by obligations");
    expect(text).toMatch(/where members tie, the one whose UEI sorts highest/);
    expect(text).not.toMatch(/registered name is read from/);
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
