"use client";

import type { SubawardCitation } from "@/lib/data";

export interface SubawardBody {
  match_basis: "subaward-description-exact";
  subaward_number: string;
  subawardee: string;
}

/** Fail closed: a prime-award URL or an amount cannot stand in for link evidence. */
export function parseSubawardEvidence(citation: SubawardCitation): SubawardBody | null {
  try {
    const body = JSON.parse(citation.query_body) as Partial<SubawardBody>;
    if (!body || body.match_basis !== "subaward-description-exact" ||
        typeof body.subaward_number !== "string" || !body.subaward_number.trim() ||
        typeof body.subawardee !== "string" || !body.subawardee.trim() ||
        citation.recorded_value != null || citation.amount_text != null ||
        citation.amount_thousands != null || citation.units != null) return null;
    const match = citation.formula?.match(/^crosswalk link: pe_bli=\S+(?: \(account [^)]+\))? matched to award PIID (\S+) via method='subaward\+lexicon', confidence='medium' \(dollars live at award grain in fct_award_transactions\)$/);
    const url = new URL(citation.official_url);
    if (!match || !["https://www.usaspending.gov", "https://usaspending.gov"].includes(url.origin) || url.username || url.password || url.search || url.hash ||
        !/^\/award\/CONT_AWD_[A-Za-z0-9_.-]+\/?$/.test(url.pathname) ||
        !url.pathname.startsWith(`/award/CONT_AWD_${match[1]}_`)) return null;
    return body as SubawardBody;
  } catch { return null; }
}

export function SubawardCard({ citation }: { citation: SubawardCitation }) {
  const body = parseSubawardEvidence(citation);
  if (!body) return <p role="alert" data-degraded="citation">This subaward link evidence could not be read.</p>;
  return <div className="space-y-3" data-cite-kind="subaward">
    <div><span className="t-label block">Evidence</span><p className="text-sm font-medium">Reported subaward description</p></div>
    <dl className="space-y-2 text-sm">
      <div><dt className="t-label">Subaward number</dt><dd className="font-mono">{body.subaward_number}</dd></div>
      <div><dt className="t-label">Subaward recipient</dt><dd>{body.subawardee}</dd></div>
      <div><dt className="t-label">Match basis</dt><dd>Exact subaward description</dd></div>
    </dl>
    <p className="text-sm">This is a medium-confidence inference linking the prime award to the program. It does not establish the amount spent on the program.</p>
    <p className="text-sm text-muted-foreground">The source record’s identity is retained above. A direct subaward page and the description excerpt are not included in this receipt.</p>
    <a href={citation.official_url} target="_blank" rel="noopener noreferrer" className="inline-flex text-sm underline underline-offset-2">
      Open prime award on USAspending<span className="sr-only"> (opens in new tab)</span>
    </a>
    <p className="text-xs text-muted-foreground">This link opens the prime award’s context page; it is not a permalink to the subaward description.</p>
    <div><span className="t-label block mb-1">Recorded link method</span><p className="t-id break-words rounded bg-muted px-2.5 py-2">{citation.formula}</p></div>
  </div>;
}
