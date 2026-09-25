import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  getFilingsIndex,
  getFilingDetail,
  collectCitations,
} from "@/lib/data";
import { humanLdaUrl } from "@/lib/citations";
import { filingDisplayTitle, isSelfFiled } from "@/lib/filing-title";
import { SITE_NAME, SITE_URL } from "@/lib/site";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { PageIntro } from "@/components/page-intro";
import { CompanyName } from "@/components/company-name";
import { displayCompanyName } from "@/lib/company-name.mjs";
import { CitationPanelProvider } from "@/components/citation-panel";
import { Cite } from "@/components/cite";
import { isTruncatedSnippet, tidySnippet } from "@/lib/snippet";
import { evidenceKindLabel, evidenceKindTitle } from "@/lib/evidence";

// ── SSG config — 5,393 filing pages, no fallback ──────────────────────────────

export const dynamicParams = false;

interface Props {
  params: Promise<{ uuid: string }>;
}

export function generateStaticParams(): { uuid: string }[] {
  try {
    return getFilingsIndex().filings.map((f) => ({ uuid: f.filing_uuid }));
  } catch {
    return [];
  }
}

// ── Metadata ──────────────────────────────────────────────────────────────────
//
// Policy (plan Task 6a, binding):
//   - canonical → the human lda.senate.gov filing page (authoritative source)
//   - robots noindex when the filing has zero program mentions (3,536 of the
//     5,393 built filing pages carry no mention and stay crawlable but
//     unindexed — re-measured 2026-09-18 over filings_index.json and the
//     filings/ sidecars; the comment said 1,170 / 4,258 from an older corpus)
//   - shared static OG image for all filings (decision 3 — no per-filing render)

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { uuid } = await params;
  let detail;
  try {
    detail = getFilingDetail(uuid);
  } catch {
    return { title: "Filing Not Found" };
  }
  const f = detail.filing;
  const hasMentions = detail.mentions.length > 0;
  // Same §P2-4 rule the title goes through (displayCompanyName, imported
  // below for the page body) — so the description beside the title never
  // shouts a name the title itself cased.
  const client = f.client_name ? displayCompanyName(f.client_name).display : "Unknown client";
  const registrant = f.registrant_name
    ? displayCompanyName(f.registrant_name).display
    : "unknown";
  const year = f.filing_year ?? "";
  // Bare title for metadata (the layout template appends the site name);
  // og keeps the full suffixed form since templates don't apply to openGraph.
  // Shared with the Pagefind title meta (§P1-4): search results and the tab
  // title both read "Client — Registrant, YYYY QN".
  const title = filingDisplayTitle(f);
  const ogTitle = `${title} | ${SITE_NAME}`;
  const description = `Senate LDA filing ${f.filing_type ?? ""} ${year} — client ${client}, registrant ${registrant}. Activities, lobbyists, and tracked program mentions.`;
  const human = humanLdaUrl(f.url);

  return {
    title,
    description,
    // Canonical points at the authoritative human LDA page, not our copy.
    alternates: { canonical: human ?? `${SITE_URL}/filing/${uuid}/` },
    robots: hasMentions ? undefined : { index: false, follow: true },
    openGraph: {
      title: ogTitle,
      description,
      url: `${SITE_URL}/filing/${uuid}/`,
      siteName: SITE_NAME,
      images: [{ url: `${SITE_URL}/og-default-filing.png`, width: 1200, height: 630 }],
    },
  };
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/** "first_quarter" → "First Quarter" (display only; raw values kept in data). */
function prettyPeriod(period: string | null): string | null {
  if (!period) return null;
  return period
    .split("_")
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(" ");
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default async function FilingPage({ params }: Props) {
  const { uuid } = await params;
  let detail;
  try {
    detail = getFilingDetail(uuid);
  } catch {
    notFound();
  }
  const f = detail.filing;
  const hasMentions = detail.mentions.length > 0;
  const human = humanLdaUrl(f.url);

  // Citation slice — filing-level lda_filing rows (income/expenses)
  const pageFactIds: string[] = [];
  if (f.income_fact_id) pageFactIds.push(f.income_fact_id);
  if (f.expenses_fact_id) pageFactIds.push(f.expenses_fact_id);
  const citationsSlice = collectCitations(pageFactIds);

  // §P2-4's rule, the one every other registry name on the site goes through:
  // it cases what it can and REFUSES rather than guess at a surname, so a
  // refused name renders exactly as the LDA recorded it.
  const clientName = f.client_name ? displayCompanyName(f.client_name) : null;
  const registrantName = f.registrant_name
    ? displayCompanyName(f.registrant_name)
    : null;
  const clientLabel = clientName ? clientName.display : "Unknown client";
  const casedAny =
    (clientName !== null && clientName.display !== clientName.registry) ||
    (registrantName !== null && registrantName.display !== registrantName.registry);
  // Raw-string fact, decided before either name is cased (filing-title.ts) —
  // a self-filed filing has one LDA string, not two, so "Filed as" below must
  // say it once ("Filed as: X.") rather than "X — X.".
  const selfFiled = isSelfFiled(f);
  // ...and the sentence AFTER those strings has to agree in number with them.
  // The collapse above fixed the strings and left "those strings"/"the names
  // above" standing on all 570 self-filed pages, where exactly one of each is
  // printed (measured 2026-09-18: 570 self-filed, 4,823 with two distinct LDA
  // strings, 0 with no registrant at all — but the condition, not the count,
  // is what decides here).
  const filedAsPlural = Boolean(registrantName && !selfFiled);

  return (
    <CitationPanelProvider citations={citationsSlice}>
      <div
        className="spine py-8"
        {...(hasMentions ? { "data-pagefind-body": true } : {})}
      >
        <Breadcrumbs
          items={[
            { label: "Home", href: "/" },
            { label: "Filings", href: "/filings/" },
            { label: clientLabel },
          ]}
        />

        {/* Header */}
        {/* The <h1> is PageIntro's title: the client through CompanyName (the
            §P2-4 casing rule, with its [data-company-name] attribute for gate
            2 leg (tc)), exactly as the old hand-rolled <h1> rendered it. */}
        <PageIntro
          eyebrow="Senate LDA lobbying filing"
          title={f.client_name ? <CompanyName raw={f.client_name} /> : "Unknown client"}
          titleProps={{ "data-pagefind-meta": "title[data-filing-title]", "data-filing-title": filingDisplayTitle(f) }}
          description="A public disclosure record: who filed, what they reported, and the program connections found in the text."
          actions={<><a href="#filing-amounts">Reported amounts</a><a href="#mentions">Program mentions</a><a href="#activities">Activity text</a><a href="#lobbyists">Lobbyists</a></>}>
          {/* data-pagefind-meta title[attr] overrides Pagefind's default
              h1-derived page title so deep-search results read
              "Client — Registrant, YYYY QN" (§P1-4) — same string as the
              page <title> via filingDisplayTitle. */}
          {/* Explicit {" "} separators between the meta spans: without them
              the rendered text nodes abut ("…LLCYear: 2025") and Pagefind
              excerpts concatenate the fragments (§P1-4 snippet bug). */}
          <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-muted-foreground">
            <span>
              Registrant:{" "}
              <span className="text-foreground font-medium">
                {f.registrant_name ? (
                  <CompanyName raw={f.registrant_name} />
                ) : (
                  "not reported"
                )}
              </span>
            </span>{" "}
            {f.filing_year && (
              <span>
                Year:{" "}
                <span className="text-foreground font-medium">{f.filing_year}</span>
              </span>
            )}{" "}
            {f.filing_period && (
              <span>
                Period:{" "}
                <span className="text-foreground font-medium">
                  {prettyPeriod(f.filing_period)}
                </span>
              </span>
            )}{" "}
            {f.filing_type && (
              <span>
                Type:{" "}
                <span className="text-foreground font-medium font-mono">
                  {f.filing_type}
                </span>
              </span>
            )}
          </div>

          {/* The LDA strings, kept visible whenever a display differs from
              them. A reader who wants to find this filing on lda.senate.gov
              needs the string the Senate recorded, not our casing of it —
              the same rule as /company/'s [data-registry-note]. */}
          {casedAny && (
            <p
              data-filed-as=""
              className="mt-2 text-xs leading-5 text-muted-foreground"
            >
              Filed as:{" "}
              <span className="font-mono text-foreground">
                {clientName ? clientName.registry : "—"}
              </span>
              {filedAsPlural ? (
                <>
                  {" — "}
                  <span className="font-mono text-foreground">
                    {registrantName!.registry}
                  </span>
                </>
              ) : null}
              . Search lda.senate.gov for{" "}
              {filedAsPlural ? "those strings" : "that string"}; the{" "}
              {filedAsPlural
                ? "names above are this site\u2019s casing of them"
                : "name above is this site\u2019s casing of it"}
              , nothing else.
            </p>
          )}

          {/* Canonical source link — always visible */}
          <p className="mt-3 text-sm">
            {human ? (
              <a
                href={human}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary underline underline-offset-2 hover:no-underline"
              >
                View on lda.senate.gov ↗
              </a>
            ) : (
              <span className="text-muted-foreground">
                Source: Senate LDA filing API
              </span>
            )}
          </p>
        </PageIntro>

        {/* Income / expenses — state A via filing-level lda citations,
            "not reported" plain text when the filing omits the amount. */}
        <div id="filing-amounts" className="scroll-mt-24 grid grid-cols-2 gap-4 max-w-2xl mb-8">
          <div className="rounded-lg border border-border bg-card p-4">
            <p className="t-label mb-1">
              Reported income
            </p>
            <p className="t-figure t-figure--4">
              {f.income_usd !== null && f.income_fact_id ? (
                <Cite
                  value={f.income_usd}
                  units="USD"
                  dataset="lda_filings"
                  factId={f.income_fact_id}
                />
              ) : (
                <span className="text-muted-foreground text-base font-normal">
                  not reported
                </span>
              )}
            </p>
          </div>
          <div className="rounded-lg border border-border bg-card p-4">
            <p className="t-label mb-1">
              Reported expenses
            </p>
            <p className="t-figure t-figure--4">
              {f.expenses_usd !== null && f.expenses_fact_id ? (
                <Cite
                  value={f.expenses_usd}
                  units="USD"
                  dataset="lda_filings"
                  factId={f.expenses_fact_id}
                />
              ) : (
                <span className="text-muted-foreground text-base font-normal">
                  not reported
                </span>
              )}
            </p>
          </div>
        </div>

        {/* Tracked program mentions */}
        <section id="mentions" className="mb-10 scroll-mt-24">
          <p className="t-label mb-2">Connections in the record</p>
          <h2 className="mb-3">
            Tracked program mentions
            <span className="ml-2 text-sm font-normal text-muted-foreground">
              {detail.mentions.length}
            </span>
          </h2>
          {/* Said ONCE for the section rather than per card: a link on every
              mention cost 3,064 bytes on the heaviest filing page and gate 1
              caught it. The ellipsis says the quote is clipped; this says
              where the whole sentence is. */}
          {hasMentions && detail.mentions.some((m) => m.description_snippet && isTruncatedSnippet(m.description_snippet)) && (
            <p className="mb-3 text-xs text-muted-foreground">
              Quoted activity text is clipped to a short extract; each
              filing&rsquo;s full description is under{" "}
              <a href="#activities" className="underline decoration-dotted hover:text-foreground">
                Lobbying activities
              </a>{" "}
              below.
            </p>
          )}
          {hasMentions ? (
            <ul className="space-y-3">
              {detail.mentions.map((m, i) => (
                <li
                  key={`${m.pe_bli}-${i}`}
                  className="rounded-lg border border-border bg-card px-4 py-3"
                >
                  <div className="flex flex-wrap items-baseline gap-2">
                    {m.program_url ? (
                      <Link
                        href={m.program_url}
                        className="font-medium text-primary hover:underline"
                        data-program-name
                      >
                        {m.program_title ?? m.pe_bli}
                      </Link>
                    ) : (
                      <span className="font-medium" data-program-name>
                        {m.program_title ?? m.pe_bli}
                      </span>
                    )}
                    <span className="t-id">
                      {m.pe_bli}
                    </span>
                    {/* ROADMAP #82: a filing names a budget line, not an
                        appropriation, so on a code two programs share the
                        link can only open the chooser. Said here, once per
                        such mention, rather than letting the reader land
                        on a page that is not the one program they expected. */}
                    {m.shared_code && (
                      <span
                        data-shared-code-note=""
                        className="text-xs text-muted-foreground"
                        title="Lobbying filings name a budget line, not an appropriation account, so this mention cannot say which of the programs sharing the code it refers to. The link opens a page listing each of them."
                      >
                        shared code — link opens a chooser
                      </span>
                    )}
                    {m.matched_term && (
                      <span className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                        matched: “{m.matched_term}”
                      </span>
                    )}
                    {/* (#52) evidence tier — the machine-checked reason this
                        row exists, not just what it matched on. A single
                        common title word is never sufficient on its own. */}
                    <span
                      data-evidence-kind={m.evidence_kind ?? ""}
                      title={evidenceKindTitle(m.evidence_kind)}
                      className="rounded border border-border px-1.5 py-0.5 text-xs text-muted-foreground"
                    >
                      {evidenceKindLabel(m.evidence_kind)}
                    </span>
                  </div>
                  {m.description_snippet && (
                    <p className="mt-1 text-sm text-muted-foreground">
                      {/* The exporter caps this at 120 characters, mid-word.
                          tidySnippet cuts back to the last whole word and
                          says so — the complete sentence is in "Lobbying
                          activities" below, on this same page. */}
                      {tidySnippet(m.description_snippet)}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">
              This filing does not mention any program tracked by {SITE_NAME}.
            </p>
          )}
        </section>

        {/* Lobbying activities */}
        <section className="mb-10 scroll-mt-24" id="activities">
          <h2 className="mb-3">
            Lobbying activities
            <span className="ml-2 text-sm font-normal text-muted-foreground">
              {detail.activities.length}
            </span>
          </h2>
          {detail.activities.length > 0 ? (
            <ul className="space-y-3">
              {detail.activities.map((a, i) => (
                <li
                  key={i}
                  className="rounded-lg border border-border bg-card px-4 py-3"
                >
                  <p className="text-sm font-medium mb-1">
                    {a.issue_display ?? a.issue_code ?? "General issue"}
                    {a.issue_code && (
                      <span className="t-id ml-2">
                        {a.issue_code}
                      </span>
                    )}
                  </p>
                  {/* #106: the filer's text, as filed — gate 2 legs (b) and
                      (nw) and datatruth leg j read the kind, and (a0) wants
                      the filing itself as the anchor. */}
                  {a.description && (
                    <p
                      className="text-sm text-muted-foreground whitespace-pre-wrap"
                      data-source-text="lda-filing"
                      data-cite-url={human ?? f.url}
                    >
                      {a.description}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">
              No activities reported on this filing.
            </p>
          )}
        </section>

        {/* Lobbyists — covered_position non-empty ⇒ revolving-door badge */}
        <section id="lobbyists" className="mb-10 scroll-mt-24">
          <h2 className="mb-3">
            Lobbyists
            <span className="ml-2 text-sm font-normal text-muted-foreground">
              {detail.lobbyists.length}
            </span>
          </h2>
          {detail.lobbyists.length > 0 ? (
            <ul className="grid gap-2 sm:grid-cols-2">
              {detail.lobbyists.map((l, i) => {
                const covered =
                  l.covered_position && l.covered_position.trim() !== ""
                    ? l.covered_position.trim()
                    : null;
                return (
                  <li
                    key={`${l.name}-${i}`}
                    className="rounded-lg border border-border bg-card px-4 py-3"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="font-medium text-sm">{l.name}</span>
                      {covered && (
                        <span
                          className="shrink-0 rounded bg-amber-100 px-1.5 py-0.5 text-xs font-semibold text-amber-700"
                          title="Previously held a covered government position (LDA §1602 disclosure)"
                        >
                          revolving door
                        </span>
                      )}
                    </div>
                    {/* #106: the filer's own covered-position string. */}
                    {covered && (
                      <p
                        className="mt-1 text-xs text-muted-foreground"
                        data-source-text="lda-filing"
                        data-cite-url={human ?? f.url}
                      >
                        {covered}
                      </p>
                    )}
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">
              No lobbyists listed on this filing.
            </p>
          )}
        </section>

        <p className="text-xs text-muted-foreground border-t border-border pt-4">
          Source: U.S. Senate Lobbying Disclosure Act database. Dollar figures
          (underlined) cite the filing record on lda.senate.gov — click to view
          the citation. Amounts shown as “not reported” are absent from the
          filing itself.
        </p>
      </div>
    </CitationPanelProvider>
  );
}
