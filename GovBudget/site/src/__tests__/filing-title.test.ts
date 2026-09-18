/**
 * filing-title.test.ts — readable filing titles (PM review §P1-4, Sprint 2 Task 1)
 *
 * Expectations below were restated 2026-09-18 when the title started going
 * through the §P2-4 display rule (PM-S3 leftover, "filing pages keep their
 * source ALL-CAPS registrant names"). Only the SPELLING moved: every case
 * these tests cover — self-filed collapse, the missing-field degradations —
 * still asserts exactly what it asserted before. "MICHAEL BEST STRATEGIES
 * LLC" and "SOME FIRM" still SHOUT here, because the rule refuses on "BEST"
 * and "SOME" rather than guess at a surname.
 *
 * PM repro: searching "Lockheed" returned four results titled
 * `/filing/813b1886-…/`. Filing search results (and the /filing/ page <title>)
 * must read "Client — Registrant, YYYY QN". Both consume the same
 * filingDisplayTitle() source so they can never drift.
 */

import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import type React from "react";
import { filingDisplayTitle, filingPeriodShort, isSelfFiled } from "@/lib/filing-title";
import { displayCompanyName } from "@/lib/company-name.mjs";

describe("filingPeriodShort", () => {
  it("maps LDA quarters to QN", () => {
    expect(filingPeriodShort("first_quarter")).toBe("Q1");
    expect(filingPeriodShort("second_quarter")).toBe("Q2");
    expect(filingPeriodShort("third_quarter")).toBe("Q3");
    expect(filingPeriodShort("fourth_quarter")).toBe("Q4");
  });

  it("maps half-year periods", () => {
    expect(filingPeriodShort("mid_year")).toBe("Mid-Year");
    expect(filingPeriodShort("year_end")).toBe("Year-End");
  });

  it("passes through unknown periods prettified, null → null", () => {
    expect(filingPeriodShort(null)).toBeNull();
    expect(filingPeriodShort("some_other")).toBe("Some Other");
  });
});

describe("filingDisplayTitle", () => {
  it("full form: Client — Registrant, YYYY QN", () => {
    expect(
      filingDisplayTitle({
        client_name: "LOCKHEED MARTIN CORPORATION",
        registrant_name: "MICHAEL BEST STRATEGIES LLC",
        filing_year: "2025",
        filing_period: "fourth_quarter",
      }),
    ).toBe("Lockheed Martin Corporation — MICHAEL BEST STRATEGIES LLC, 2025 Q4");
  });

  it("no registrant → Client, YYYY QN", () => {
    expect(
      filingDisplayTitle({
        client_name: "LOCKHEED MARTIN CORPORATION",
        registrant_name: null,
        filing_year: "2024",
        filing_period: "third_quarter",
      }),
    ).toBe("Lockheed Martin Corporation, 2024 Q3");
  });

  it("self-filed (registrant === client) → no duplicate name", () => {
    expect(
      filingDisplayTitle({
        client_name: "LOCKHEED MARTIN CORPORATION",
        registrant_name: "LOCKHEED MARTIN CORPORATION",
        filing_year: "2025",
        filing_period: "first_quarter",
      }),
    ).toBe("Lockheed Martin Corporation, 2025 Q1");
  });

  it("no period → Client — Registrant, YYYY", () => {
    expect(
      filingDisplayTitle({
        client_name: "BOEING",
        registrant_name: "SOME FIRM",
        filing_year: "2023",
        filing_period: null,
      }),
    ).toBe("Boeing — SOME FIRM, 2023");
  });

  it("no year → Client — Registrant", () => {
    expect(
      filingDisplayTitle({
        client_name: "BOEING",
        registrant_name: "SOME FIRM",
        filing_year: null,
        filing_period: null,
      }),
    ).toBe("Boeing — SOME FIRM");
  });

  it("nothing known → Unknown client", () => {
    expect(
      filingDisplayTitle({
        client_name: null,
        registrant_name: null,
        filing_year: null,
        filing_period: null,
      }),
    ).toBe("Unknown client");
  });
});

describe("/filing/ page metadata uses filingDisplayTitle (real data)", () => {
  // 55078848-5151-45f3-9172-a82fd75f9323 = LOCKHEED MARTIN CORPORATION /
  // MICHAEL BEST STRATEGIES LLC / 2025 / fourth_quarter (4 mentions)
  const UUID = "55078848-5151-45f3-9172-a82fd75f9323";

  it("generateMetadata title reads Client — Registrant, YYYY QN", async () => {
    const { generateMetadata } = await import("@/app/filing/[uuid]/page");
    const meta = await generateMetadata({
      params: Promise.resolve({ uuid: UUID }),
    });
    expect(meta.title).toBe(
      "Lockheed Martin Corporation — MICHAEL BEST STRATEGIES LLC, 2025 Q4",
    );
  });

  // Fix round 1, item 6: the description beside a cased title still
  // interpolated the raw client_name/registrant_name. Same UUID, same rule
  // (displayCompanyName) — the client cases, the registrant refuses on
  // "BEST", so the description must show exactly what the title shows for
  // each name, not the client's raw SHOUTED form.
  it("generateMetadata description cases the client through the same rule as the title", async () => {
    const { generateMetadata } = await import("@/app/filing/[uuid]/page");
    const meta = await generateMetadata({
      params: Promise.resolve({ uuid: UUID }),
    });
    expect(meta.description).toBe(
      "Senate LDA filing Q4 2025 — client Lockheed Martin Corporation, registrant MICHAEL BEST STRATEGIES LLC. Activities, lobbyists, and tracked program mentions.",
    );
    expect(meta.description).not.toContain("client LOCKHEED MARTIN CORPORATION");
  });
});

describe("filingDisplayTitle casing (PM-S3 leftover: filings shouted)", () => {
  it("cases both names through the shared company rule", () => {
    expect(
      filingDisplayTitle({
        client_name: "AECOM TECHNICAL SERVICES, INC.",
        registrant_name: "ELEVATE GOVERNMENT AFFAIRS, LLC",
        filing_year: "2025",
        filing_period: "fourth_quarter",
      }),
    ).toBe("AECOM Technical Services, Inc. — Elevate Government Affairs, LLC, 2025 Q4");
  });

  it("renders a REFUSED name verbatim rather than guessing, beside a cased one", () => {
    // 'BEST' is a surname the rule will not title-case, so the whole
    // registrant refuses while the client cases. Both halves of one title.
    expect(displayCompanyName("MICHAEL BEST STRATEGIES LLC").refused).toBe(true);
    expect(
      filingDisplayTitle({
        client_name: "ABBOTT LABORATORIES",
        registrant_name: "MICHAEL BEST STRATEGIES LLC",
        filing_year: "2025",
        filing_period: "fourth_quarter",
      }),
    ).toBe("Abbott Laboratories — MICHAEL BEST STRATEGIES LLC, 2025 Q4");
  });

  it("still collapses a self-filed registrant after casing", () => {
    expect(
      filingDisplayTitle({
        client_name: "ABBOTT LABORATORIES",
        registrant_name: "ABBOTT LABORATORIES",
        filing_year: "2025",
        filing_period: null,
      }),
    ).toBe("Abbott Laboratories, 2025");
  });

  it("keeps degrading gracefully", () => {
    expect(filingDisplayTitle({ client_name: null, registrant_name: null, filing_year: null, filing_period: null })).toBe("Unknown client");
  });
});

describe("isSelfFiled (fix round 1, item 7 — the raw-string notion, shared with the page body)", () => {
  it("true when client and registrant are the same raw string", () => {
    expect(
      isSelfFiled({ client_name: "ABBOTT LABORATORIES", registrant_name: "ABBOTT LABORATORIES" }),
    ).toBe(true);
  });

  it("false when they differ, even after trimming", () => {
    expect(
      isSelfFiled({ client_name: "ABBOTT LABORATORIES", registrant_name: "MICHAEL BEST STRATEGIES LLC" }),
    ).toBe(false);
  });

  it("false when registrant is null", () => {
    expect(isSelfFiled({ client_name: "ABBOTT LABORATORIES", registrant_name: null })).toBe(false);
  });

  it("is a fact about the REGISTRY string, decided before casing", () => {
    // Same registry string, differently-cased inputs would still be two
    // DIFFERENT raw strings — this function never normalises case itself.
    expect(isSelfFiled({ client_name: "Abbott Laboratories", registrant_name: "ABBOTT LABORATORIES" })).toBe(
      false,
    );
  });
});

describe("/filing/ page 'Filed as' line — self-filed collapse (fix round 1, item 7, real data)", () => {
  // 3e857be5-28c1-436f-93c8-35af921c0fa5 = ABBOTT LABORATORIES, self-filed
  // (client_name === registrant_name, raw comparison) — one of 570 such
  // filings shipped (measured 2026-09-18). The name CASES (ABBOTT
  // LABORATORIES → Abbott Laboratories), so casedAny is true and the
  // [data-filed-as] line renders. Before this fix it read
  // "Filed as: ABBOTT LABORATORIES — ABBOTT LABORATORIES." — the same LDA
  // string twice across a dash that implies two different filers.
  const SELF_FILED_UUID = "3e857be5-28c1-436f-93c8-35af921c0fa5";
  // 813b1886-… is the PM's own Lockheed repro (see this file's header): a
  // distinct client and registrant, so the "Filed as" line prints BOTH LDA
  // strings across the dash. One of the 4,823 two-string filings shipped
  // against 570 self-filed (measured 2026-09-18).
  const TWO_NAME_UUID = "813b1886-65d2-4abb-9d6f-c4a8ce7dd56c";

  async function renderSelfFiled() {
    const { default: FilingPage } = await import("@/app/filing/[uuid]/page");
    const el = await FilingPage({ params: Promise.resolve({ uuid: SELF_FILED_UUID }) });
    return render(el as React.ReactElement);
  }

  it("renders the LDA string once ('Filed as: X.'), not duplicated across a dash", async () => {
    const { container } = await renderSelfFiled();
    const note = container.querySelector("[data-filed-as]");
    expect(note).not.toBeNull();
    const text = note!.textContent ?? "";
    expect(text).not.toMatch(/ABBOTT LABORATORIES\s*—\s*ABBOTT LABORATORIES/);
    expect(text).toContain("Filed as: ABBOTT LABORATORIES.");
  }, 30000);

  // The collapse fixed the STRINGS and left the sentence after them plural:
  // "Search lda.senate.gov for those strings; the names above are this site's
  // casing of them" — on all 570 self-filed pages there is one string and one
  // name. The sentence now agrees in number with what it points at.
  it("says 'that string' and 'the name above', singular, when it printed one", async () => {
    const { container } = await renderSelfFiled();
    const text = container.querySelector("[data-filed-as]")!.textContent ?? "";
    expect(text).toContain("Search lda.senate.gov for that string");
    expect(text).toContain("the name above is this site");
    expect(text).not.toContain("those strings");
    expect(text).not.toContain("the names above");
  }, 30000);

  // 813b1886-… is the PM's own Lockheed repro: LOCKHEED MARTIN CORPORATION
  // filed by a distinct registrant, so two strings print and the plural is
  // the true form. Both branches are pinned, so neither can be "fixed" by
  // making one wording serve both.
  it("keeps the plural when it really did print two strings", async () => {
    const { default: FilingPage } = await import("@/app/filing/[uuid]/page");
    const el = await FilingPage({
      params: Promise.resolve({ uuid: TWO_NAME_UUID }),
    });
    const { container } = render(el as React.ReactElement);
    const note = container.querySelector("[data-filed-as]");
    expect(note).not.toBeNull();
    const text = note!.textContent ?? "";
    expect(text).toMatch(/Filed as:.*—/);
    expect(text).toContain("Search lda.senate.gov for those strings");
    expect(text).toContain("the names above are this site");
  }, 30000);
});
