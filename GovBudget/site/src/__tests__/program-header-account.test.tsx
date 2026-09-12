/**
 * ProgramHeader's appropriation line — ROADMAP #82.
 *
 * Ten pe_bli codes are shared by two programs that differ only by
 * appropriation account ('3010' is LPD Flight II in 1611N and Shipboard
 * Tactical Communications in 1810N). Both members' pages carried the same
 * org ("Navy"), the same exhibit badge and the same code; the ONE thing that
 * tells them apart — the appropriation — appeared nowhere in the title
 * block. These tests hold:
 *   1. an account-split member names its own appropriation title and code
 *      in a single [data-program-account] element, and never its sibling's;
 *   2. an ordinary program (account null) renders no such element;
 *   3. an organization-split member ('20-DTRA' / '20-DCSA', one account
 *      0300D) renders none either — the org link is the discriminator and
 *      the account would read the same on both pages;
 *   4. the prop defaults to off, so every pre-#82 caller is unchanged;
 *   5. the h1 stays the bare title — the account sits beside it, not in it.
 */

import { describe, it, expect, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/react";
import React from "react";

import { ProgramHeader } from "@/components/program-header";
import type { ProgramRow } from "@/lib/data";

const SCN: ProgramRow = {
  award_count: 5,
  exhibit_family: "procurement",
  fully_reconciled: false,
  reconciled_in_scope: true,
  fy2024_actual_millions: 500,
  fy2024_fact_id: null,
  fy2024_xml_path: null,
  hhi: null,
  narrative_count: 4,
  org: "N",
  pe_bli: "3010",
  project_count: 0,
  title: "LPD Flight II",
  trajectory: null,
  trajectory_fact_ids: null,
  slug: "3010-SCN",
  account: "1611N",
  account_title: "Shipbuilding and Conversion, Navy",
};

function accountEl(program: ProgramRow, accountSplit?: boolean) {
  const { container } = render(
    <ProgramHeader program={program} orgHasPage={false} accountSplit={accountSplit} />,
  );
  return container.querySelector("[data-program-account]") as HTMLElement | null;
}

afterEach(cleanup);

describe("ProgramHeader appropriation line (ROADMAP #82)", () => {
  it("names the member's own appropriation title and code on an account-split page", () => {
    const el = accountEl(SCN, true);
    expect(el).not.toBeNull();
    expect(el!.getAttribute("data-program-account")).toBe("1611N");
    expect(el!.textContent).toContain("Shipbuilding and Conversion, Navy");
    expect(el!.textContent).toContain("1611N");
    expect(el!.textContent).not.toContain("Other Procurement, Navy");
  });

  it("renders exactly one such element", () => {
    const { container } = render(
      <ProgramHeader program={SCN} orgHasPage={false} accountSplit />,
    );
    expect(container.querySelectorAll("[data-program-account]")).toHaveLength(1);
  });

  it("renders nothing for an ordinary program (account null)", () => {
    expect(
      accountEl(
        { ...SCN, slug: "0601101E", pe_bli: "0601101E", account: null, account_title: null },
        false,
      ),
    ).toBeNull();
  });

  it("renders nothing when the page says the key is account-split but the row has no account_title", () => {
    expect(accountEl({ ...SCN, account_title: null }, true)).toBeNull();
  });

  it("renders nothing on an organization-split member even though its account is populated", () => {
    expect(
      accountEl(
        {
          ...SCN,
          slug: "20-DTRA",
          pe_bli: "20",
          org: "DTRA",
          title: "Vehicles",
          account: "0300D",
          account_title: "Procurement, Defense-Wide",
        },
        false,
      ),
    ).toBeNull();
  });

  it("defaults to no appropriation line — pre-#82 callers are unchanged", () => {
    expect(accountEl(SCN)).toBeNull();
  });

  it("keeps the h1 as the bare title; the account is beside it, not in it", () => {
    const { container } = render(
      <ProgramHeader program={SCN} orgHasPage={false} accountSplit />,
    );
    expect(container.querySelector("h1[data-program-name]")!.textContent).toBe("LPD Flight II");
  });
});
