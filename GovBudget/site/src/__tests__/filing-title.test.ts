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
import { filingDisplayTitle, filingPeriodShort } from "@/lib/filing-title";
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
