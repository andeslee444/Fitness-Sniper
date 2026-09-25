/**
 * RegisteredNameNote — the line under a /company/ h1 (ROADMAP #10 A).
 *
 * Task 29 fix round 1. For a relabelled family the note said "this family's
 * registered parent name was chosen by a near-tie over obligations", on every
 * relabelled page, with no margin behind it. On the lake of the 2026-09-06
 * FY2026 refresh, RTX's registered parent name won by 27.9% and NOVETTA
 * SOLUTIONS's by 19.1% — both over the 15% line /methodology/#company-families
 * defines a near-tie by — so /company/rtx/ and /company/novetta-solutions/
 * stated a near-tie that was not there. The page has no per-family margin, so
 * the note states only what is true of every curated label: it was reviewed,
 * and the reviewed name is what we publish.
 */
import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import React from "react";

import { RegisteredNameNote } from "@/components/company-name";

function noteText(raw: string, label?: string | null) {
  const { container } = render(<RegisteredNameNote raw={raw} label={label} />);
  const note = container.querySelector("[data-registry-note]");
  return { note, text: (note?.textContent ?? "").replace(/\s+/g, " ").trim() };
}

describe("RegisteredNameNote on a relabelled family", () => {
  it("keeps the registry string and the link to the method", () => {
    const { note, text } = noteText("RTX CORP", "RTX Corporation");
    expect(text).toContain("Registered name in the award data: RTX CORP.");
    const link = note?.querySelector('a[href="/methodology/#company-families"]');
    expect(link?.textContent).toBe("curated label");
  });

  it("asserts no near-tie it cannot know — the reviewed name is what it says", () => {
    const { text } = noteText("RTX CORP", "RTX Corporation");
    expect(text).not.toMatch(/near-tie/i);
    expect(text).toContain(
      "this family’s registered parent name was reviewed by hand, and we " +
        "publish the reviewed name instead.",
    );
  });
});

describe("RegisteredNameNote on an uncurated family", () => {
  it("names the casing, and nothing about review", () => {
    const { text } = noteText("LOCKHEED MARTIN CORP");
    expect(text).toContain("this site’s casing of it, nothing else");
    expect(text).not.toMatch(/reviewed|near-tie/);
  });
});
