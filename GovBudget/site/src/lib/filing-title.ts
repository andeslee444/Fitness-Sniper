/**
 * filing-title.ts — one display-title source for LDA filings
 * (PM review §P1-4, Sprint 2 Task 1)
 *
 * The /filing/{uuid}/ page <title> and the Pagefind search-index title both
 * consume filingDisplayTitle(), so a deep-search hit reads
 * "Lockheed Martin Corporation — MICHAEL BEST STRATEGIES LLC, 2025 Q4"
 * instead of the raw URL path — and the two can never drift apart.
 *
 * Both names go through the §P2-4 display rule (lib/company-name.mjs), the
 * same one every other registry name on the site uses — which is why that
 * example still SHOUTS its registrant: the rule refuses on the surname
 * "BEST" rather than guessing, and a refused name renders exactly as the LDA
 * recorded it.
 */

import { displayCompanyName } from "@/lib/company-name.mjs";

export interface FilingTitleFields {
  client_name: string | null;
  registrant_name: string | null;
  filing_year: string | null;
  filing_period: string | null;
}

const PERIOD_SHORT: Record<string, string> = {
  first_quarter: "Q1",
  second_quarter: "Q2",
  third_quarter: "Q3",
  fourth_quarter: "Q4",
  mid_year: "Mid-Year",
  year_end: "Year-End",
};

/** "first_quarter" → "Q1"; unknown periods prettified ("some_other" → "Some Other"). */
export function filingPeriodShort(period: string | null): string | null {
  if (!period) return null;
  const known = PERIOD_SHORT[period];
  if (known) return known;
  return period
    .split("_")
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(" ");
}

/**
 * "Client — Registrant, YYYY QN", degrading gracefully as fields go missing:
 * no registrant (or self-filed) → "Client, YYYY QN"; no period → "…, YYYY";
 * no year → "Client — Registrant"; nothing → "Unknown client".
 */
export function filingDisplayTitle(f: FilingTitleFields): string {
  // §P2-4's rule, reused verbatim: SHOUTED names are cased, anything the rule
  // cannot case refuses and renders exactly as the LDA recorded it. 431 of the
  // 620 distinct names in this corpus case; 186 refuse (MICHAEL BEST…, AKIN
  // GUMP…, ARK STRATEGY, TCH GROUP…).
  const rawClient = f.client_name?.trim() || null;
  const rawRegistrant = f.registrant_name?.trim() || null;
  const client = rawClient ? displayCompanyName(rawClient).display : "Unknown client";
  const registrant = rawRegistrant ? displayCompanyName(rawRegistrant).display : null;
  // Self-filed is a fact about the REGISTRY strings, never about their casing.
  const selfFiled = rawRegistrant !== null && rawRegistrant === rawClient;

  let title = client;
  if (registrant && !selfFiled) title += ` — ${registrant}`;

  if (f.filing_year) {
    title += `, ${f.filing_year}`;
    const period = filingPeriodShort(f.filing_period);
    if (period) title += ` ${period}`;
  }
  return title;
}
