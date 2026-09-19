/**
 * ROADMAP #111 / Task 17c — the coverage note's THREE branches, on both of
 * the surfaces that render them.
 *
 * "Detailed justification for this program lives in the IG J-book, which is
 * not yet ingested" presupposes a book exists. Measured 2026-09-12 the FY2026
 * budget published no RDT&E or procurement justification book for the DoD IG
 * at all, and none for DEFW's reconciliation / undistributed / roll-up rows —
 * five pages, each saying it twice (the description note and the Justification
 * empty state). The DHA book WAS downloaded and carries no jb-2009 payload,
 * which is a different thing from "not yet".
 *
 * These cases pin, for each branch: the sentence the reader sees, that the
 * two surfaces agree, and that the generic wording survives ONLY where it is
 * true — an org with no loaded book and no recorded probe.
 */
import { describe, it, expect, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

import {
  ServiceBooksNote,
  ServiceBooksJustificationNote,
} from "@/components/service-books-note";
import {
  setIngestedServiceOrgs,
  setOrgAbsences,
  type OrgAbsence,
} from "@/lib/program-tier";

const ABSENCES: Record<string, OrgAbsence> = {
  DHA: {
    rule: "book-carries-no-embedded-xml",
    fy: 2026,
    checked_on: "2026-09-12",
    checked_url: "https://comptroller.war.gov/…/00-DHP_Vols_I_and_II_PB26.pdf",
  },
  DEFW: {
    rule: "summary-line-only",
    fy: 2026,
    checked_on: "2026-09-12",
    checked_url: "https://comptroller.war.gov/Budget-Materials/",
  },
  IG: {
    rule: "no-justification-book-published",
    fy: 2026,
    checked_on: "2026-09-12",
    checked_url: "https://comptroller.war.gov/Budget-Materials/",
  },
};

function noteText(org: string): string {
  render(<ServiceBooksNote serviceOrg={org} />);
  const el = document.querySelector('[data-coverage="service-books"]');
  return (el?.textContent ?? "").replace(/\s+/g, " ").trim();
}

function justificationText(org: string): string {
  const { container } = render(
    <ServiceBooksJustificationNote serviceOrg={org} />,
  );
  return container.textContent!.replace(/\s+/g, " ").trim();
}

afterEach(() => {
  setOrgAbsences(undefined);
  setIngestedServiceOrgs(["A", "N", "F"]);
  document.body.innerHTML = "";
});

describe("ServiceBooksNote — the recorded-absence branch", () => {
  it("says no book was published for IG, and never that one is awaited", () => {
    setOrgAbsences(ABSENCES);
    expect(noteText("IG")).toBe(
      "No FY2026 RDT&E or procurement justification book was published for IG" +
        " (justification index checked 2026-09-12), so this corpus carries no" +
        " detailed justification for this program. See roadmap.",
    );
    expect(noteText("IG")).not.toContain("not yet ingested");
  });

  it("says DEFW's rows are summary lines with no DEFW-specific book", () => {
    setOrgAbsences(ABSENCES);
    const text = noteText("DEFW");
    expect(text).toContain(
      "No DEFW-specific FY2026 justification book is published",
    );
    // Disjunctive, because the rule is: DEFW's rows are all three today, a
    // future org recorded under the same rule may have only one.
    expect(text).toContain("reconciliation, undistributed or roll-up summary lines");
    expect(text).not.toContain("not yet ingested");
  });

  it("says DHA's book was downloaded and carries no payload", () => {
    setOrgAbsences(ABSENCES);
    const text = noteText("DHA");
    expect(text).toContain(
      "The DHA FY2026 justification book was downloaded, but its PDF carries" +
        " no embedded data payload (checked 2026-09-12)",
    );
    expect(text).not.toContain("not yet ingested");
  });

  it("keeps the roadmap link on the absence branch", () => {
    setOrgAbsences(ABSENCES);
    render(<ServiceBooksNote serviceOrg="IG" />);
    const link = screen.getByRole("link", { name: "roadmap" });
    expect(link.getAttribute("href")).toContain("#coverage-service-books");
  });

  it("wins over the ingested branch, so a stale ingestion cannot re-hide it", () => {
    // Contradictory payloads: the page renders the absence and gate 21 leg (o)
    // fails on the contradiction itself — the page never silently picks the
    // wording that would be wrong if the absence record is the fresher one.
    setOrgAbsences(ABSENCES);
    setIngestedServiceOrgs(["A", "N", "F", "IG"]);
    expect(noteText("IG")).toContain("was published for IG");
  });
});

describe("ServiceBooksNote — the branches that did not change", () => {
  it("says a loaded book carries no narrative for this line", () => {
    setIngestedServiceOrgs(["A", "N", "F"]);
    expect(noteText("A")).toBe(
      "The Army FY2026 J-books are ingested, but this program element carries" +
        " no R-2/P-40 narrative in them — only its cited R-1/P-1 workbook" +
        " figures are shown. See roadmap.",
    );
  });

  it("keeps 'not yet ingested' for an org with no loaded book and no probe", () => {
    setOrgAbsences(ABSENCES);
    setIngestedServiceOrgs(["A", "N", "F"]);
    expect(noteText("SDA")).toBe(
      "Detailed justification for this program lives in the SDA J-book, which" +
        " is not yet ingested — see roadmap.",
    );
  });

  it("keeps the generic 'service' wording for the empty org code", () => {
    // 9999999999 "Classified Programs": the one rollup sidecar with an empty
    // service_org. It has no org to probe, so nothing about it moves.
    setOrgAbsences(ABSENCES);
    expect(noteText("")).toBe(
      "Detailed justification for this program lives in the service J-book," +
        " which is not yet ingested — see roadmap.",
    );
  });
});

describe("ServiceBooksJustificationNote — the second render site", () => {
  it("states the same case as the note, per branch", () => {
    setOrgAbsences(ABSENCES);
    expect(justificationText("IG")).toBe(
      "No FY2026 RDT&E or procurement justification book was published for IG," +
        " so there are no accomplishments or planned-program narratives to" +
        " show — see the description note above.",
    );
    expect(justificationText("DEFW")).toContain(
      "No DEFW-specific FY2026 justification book is published",
    );
    expect(justificationText("DHA")).toContain(
      "no accomplishments or planned-program narratives could be extracted" +
        " from it",
    );
  });

  it("never says 'not yet ingested' about an org with a recorded absence", () => {
    setOrgAbsences(ABSENCES);
    for (const org of Object.keys(ABSENCES)) {
      expect(justificationText(org)).not.toContain("not yet ingested");
    }
  });

  it("keeps both pre-existing branches", () => {
    setIngestedServiceOrgs(["A", "N", "F"]);
    expect(justificationText("A")).toContain(
      "The Army FY2026 J-book is ingested, but this program element carries no" +
        " matching R-2/P-40 accomplishments or planned-program narrative",
    );
    expect(justificationText("SDA")).toContain(
      "Accomplishments and planned-program narratives live in the SDA J-book," +
        " which is not yet ingested",
    );
  });
});
