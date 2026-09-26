import type { Metadata } from "next";
import Link from "next/link";
import { getDistrictIndex, getDistrictDetail } from "@/lib/data";
import { districtDisplayLabel, formatAmountNoCurrency } from "@/lib/format";
import { SITE_NAME, SITE_URL } from "@/lib/site";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { PageIntro } from "@/components/page-intro";
import { CitationPanelProvider } from "@/components/citation-panel";
import { Cite } from "@/components/cite";
import { CoverageNote } from "@/components/coverage-note";
import { ScopeNote } from "@/components/notes";
import { FyRange } from "@/components/fy-range";
import { getAwardFyRange } from "@/lib/fy-range";

// No fallback pages beyond what generateStaticParams returns (SSG export).
export const dynamicParams = false;

interface Props {
  params: Promise<{ district: string }>;
}

export function generateStaticParams(): { district: string }[] {
  try {
    const index = getDistrictIndex();
    return index.districts.map((d) => ({ district: d.pop_district }));
  } catch {
    return [];
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { district } = await params;
  let state = "";
  try {
    const detail = getDistrictDetail(district);
    state = detail.pop_state ? ` (${detail.pop_state})` : "";
  } catch {
    // ignore
  }
  return {
    title: `District ${district}${state}`,
    description: `Defense contract awards in congressional district ${district}${state} — high-confidence program links via USAspending crosswalk.`,
    alternates: { canonical: `${SITE_URL}/district/${district}/` },
    openGraph: {
      title: `District ${district}${state} — ${SITE_NAME}`,
      description: `Defense contract awards in congressional district ${district}${state}.`,
      url: `${SITE_URL}/district/${district}/`,
      siteName: SITE_NAME,
    },
  };
}

export default async function DistrictDetailPage({ params }: Props) {
  const { district } = await params;
  const detail = getDistrictDetail(district);

  // #51: the attribution basis + the sitewide linked-slice ratio, hoisted from
  // the /district/ index onto the detail page — this is what search lands
  // on, so the context that makes "$209.3M" honest cannot live only one
  // click upstream. Sitewide, not per-district: the ratio describes how
  // small a slice the crosswalk covers of ALL award dollars recorded with a
  // district, which is a fact about the METHOD, not about this one district.
  const districtIndex = getDistrictIndex();
  const sitewideLinkable = districtIndex.districts.reduce(
    (sum, d) => sum + d.total_linkable_dollars,
    0,
  );
  const sitewideRatioPct =
    districtIndex.geo_grand_total && districtIndex.geo_grand_total > 0
      ? (sitewideLinkable / districtIndex.geo_grand_total) * 100
      : null;

  // ROADMAP #6, partial-year honesty. site_meta.award_fy_range.max_partial is
  // true on the run-4 export (latest action 2026-09-04, before FY2026's Sep 30
  // close), and a final row that ends on a half-collected year without saying
  // so publishes a collapse that did not happen. DERIVED, never authored — the
  // same source <FyRange/> reads, so the two can never disagree.
  const byYear = detail.by_year ?? [];
  const awardFyRange = getAwardFyRange();
  const partialFy = awardFyRange?.maxPartial ? awardFyRange.fyMax : null;
  // ...but the NOTE about the partial year belongs only on a page whose table
  // actually reaches it. max_partial is SITEWIDE and true on every page, while
  // only 67 of 153 districts had an FY2026 row (measured 2026-09-11; 110 of
  // 189 on the 2026-09-25 run-4 export); on the others the note asserted a
  // figure that is not in the table (fix round 1, Critical 2). The inline "partial year" row label was already derived per
  // row and is unchanged.
  const showsPartialFy =
    partialFy !== null && byYear.some((r) => r.fiscal_year === partialFy);
  // The gross column earns its space only where it differs from the net one.
  const hasDeobligations = byYear.some(
    (r) => r.positive_obligation > r.total_obligation + 0.005,
  );

  const stateLabel = detail.pop_state ? ` — ${detail.pop_state}` : "";

  // The organizations actually present below — DERIVED, never authored, so
  // the coverage note cannot outlive the data it describes (§P1-5).
  const linkedOrgs = [
    ...new Set(detail.programs.map((p) => p.organization).filter(Boolean)),
  ].sort();
  const orgPhrase =
    linkedOrgs.length === 1
      ? `Every program below is a ${linkedOrgs[0]} line`
      : `The programs below come from ${linkedOrgs.join(", ")}`;

  // Special pop_district codes (00 at-large, 90/98/99 undistricted) render a
  // plain-language label instead of the raw code — display only; the URL and
  // sidecar data keep the raw code (e.g. /district/DC-98/).
  const displayLabel = districtDisplayLabel(district);
  const isSpecialCode = displayLabel !== district;
  const heading = isSpecialCode
    ? displayLabel
    : `District ${district}${stateLabel}`;

  // §P1-6 (CO-05): "linkable obligations" and "cited (USAspending)" are two
  // genuinely different measures — everything the crosswalk links, versus the
  // subset whose citation row actually resolves — but in the current corpus
  // EVERY linked row carries a resolving citation, so both cards rendered the
  // same $1.14B under two labels and read as a duplication bug.
  //
  // The honest resolution is not to delete a measure: it is to show one card
  // while they coincide and say so, and to split back into two the moment they
  // diverge (a crosswalk row whose citation does not resolve). Deciding this
  // per district from the data means neither state can be a lie.
  //
  // Compared in whole CENTS (2026-09-25 final review #5). Both totals are
  // float sums of per-program obligations and the exporter's clamp does not
  // round, so an exact === split 14 districts on float noise alone — AL-02
  // shipped cited 4,589,898,661.98 against linkable 4,589,898,661.9800005 and
  // rendered a second, identical "$4.59B of which cited" tile — and each
  // re-export picked a different set. A dollar amount is equal to the cent or
  // it is not; CA-51's real $340,858 gap still splits.
  const cents = (usd: number) => Math.round(usd * 100);
  const citedEqualsLinkable =
    cents(detail.total_cited_dollars) === cents(detail.total_linkable_dollars);

  // R-28b-4: the fact id of every state-A <Cite> this page renders, and no
  // other — each entry carries the condition its <Cite> renders under below
  // (a program row with no obligation renders "—", not a Cite). Ids only:
  // the provider fetches a body from the shards when it is opened.
  const renderedFactIds = [
    ...new Set(
      [
        detail.total_linkable_fact_id,
        citedEqualsLinkable ? null : detail.total_cited_fact_id,
        ...byYear.flatMap((row) => [
          row.total_fact_id,
          hasDeobligations ? row.positive_fact_id : null,
        ]),
        ...detail.programs.map((prog) =>
          prog.total_obligation !== null ? prog.fact_id : null,
        ),
      ].filter((id): id is string => Boolean(id)),
    ),
  ];

  return (
    // §P2-1 page weight (Task 28b): citations resolve LAZILY through
    // cite-shards (/json/cite-shards/{fact_id[:2]}.json), so the provider
    // mounts with an EMPTY embedded slice — the treatment /programs/, /feed/,
    // /years/, /flow/ and /lineage/ already use, and the same fetch-on-miss
    // path a program page takes for any fact outside its own slice. The slice
    // this page used to build (collectCitations over the page's fact ids) was
    // serialized whole into the RSC payload: 50,556 of /district/VA-11/'s
    // 171,862 raw bytes on chain C run 2's build, which put the page class
    // over its INITIAL gate-1 ceiling. Every cited figure is still a state-A
    // <Cite> with its fact id in the static HTML; a click resolves that fact
    // from its shard, showing the panel's loading state while it does and its
    // degraded state if the shard cannot be reached.
    //
    // The drill-down an empty slice would have cost, and how it is kept
    // (fix round 1, ruling R-28b-4): the header total (and the cited total,
    // where it renders) is a derived citation whose inputs are this page's
    // own program rows — on all 189 pages of that build. Its input chips are
    // clickable only when the panel's synchronous hasCitation() answers true,
    // and with an empty slice alone it knows only facts already resolved on
    // this page view. So the provider is also handed renderedFactIds — the
    // ids, never the bodies — and treats each as resolvable: its chip is
    // clickable, and a click fetches its body through the same shard path.
    // On /district/VA-11/ of that build that is 49 ids, 1,054 raw bytes.
    <CitationPanelProvider citations={{}} shardResolvableIds={renderedFactIds}>
      <div className="spine py-8">
        <Breadcrumbs
          items={[
            { label: "Home", href: "/" },
            { label: "Districts", href: "/district/" },
            { label: heading },
          ]}
        />

        {/* 2026-09-25 integration: the editorial redesign's masthead. The
            coverage note moved under the summary stats, its long form behind
            a <details> (the redesign's order), and keeps this branch's
            reviewed wording (Task 26's mechanism sentence; the
            high-confidence-linked slice). The redesign's rewrite of that
            sentence ("Each published link has been hand-adjudicated; high-
            confidence links also underwent adversarial review") was not
            carried: /methodology/ §4 publishes a measured adjudication
            coverage, not a universal. */}
        <PageIntro eyebrow="District dossier" title={heading}
          description="The documented connections between this place, defense programs and contract awards."
          actions={<><a href="#linked-programs">Linked programs</a><Link href="/district/">Find another district</Link></>}>
          {isSpecialCode && <p className="t-id mb-3">District code {district}</p>}
          <p className="text-muted-foreground text-sm">
            {detail.program_count} linked program
            {detail.program_count !== 1 ? "s" : ""} via high-confidence
            USAspending crosswalk.
          </p>
          {/* Scope note — same coverage contract as the district index */}
          <CoverageNote id="districts" className="mt-1" />

          {/* Summary stats */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 mt-4">
            <div className="rounded-lg border border-border bg-card p-4">
              <p className="t-figure t-figure--5">
                {detail.program_count}
              </p>
              <p className="text-muted-foreground text-xs mt-1">
                linked programs
              </p>
            </div>
            <div className="rounded-lg border border-border bg-card p-4">
              <p className="t-figure t-figure--5">
                {/* Derived 'district' aggregate citation — the award-DISTINCT
                    total for this district, from fct_district_totals (#51).
                    fct_district_programs is per (district, pe_bli, account)
                    and NOT summable: an award matched to N program elements
                    appears N times with the same dollars there. State A when the
                    citation resolves; honest state C otherwise. */}
                <Cite
                  value={detail.total_linkable_dollars}
                  units="USD"
                  dataset="fct_district_totals"
                  factId={detail.total_linkable_fact_id}
                />
              </p>
              <p className="text-muted-foreground text-xs mt-1">
                linkable obligations <FyRange separator="· " /> ·{" "}
                {detail.award_count} distinct award
                {detail.award_count !== 1 ? "s" : ""}
              </p>
              {citedEqualsLinkable && (
                <p className="text-muted-foreground text-xs mt-1">
                  every linked dollar carries a USAspending citation
                </p>
              )}
            </div>
            {!citedEqualsLinkable && (
              <div className="rounded-lg border border-border bg-card p-4">
                <p className="t-figure t-figure--5">
                  {/* #51: capped at total_linkable_dollars by construction —
                      see the matching clamp in export_site.py. */}
                  <Cite
                    value={detail.total_cited_dollars}
                    units="USD"
                    dataset="fct_district_totals"
                    factId={detail.total_cited_fact_id}
                  />
                </p>
                <p className="text-muted-foreground text-xs mt-1">
                  of which cited (USAspending) <FyRange separator="· " />
                </p>
              </div>
            )}
          </div>
          {/* §P2-6: this was an amber banner ABOVE the <h1> — the page opened
              with what read as a warning before the reader knew what page they
              were on. It is not a warning: it is an honest account of what
              district coverage means here, which is a credibility asset. Calm
              register, and after the heading. */}
          <ScopeNote className="mt-4" label="Coverage note">
            <p className="text-sm font-medium text-foreground">These are high-confidence program links, not a total of defense spending in this district.</p>
            <details className="mt-2">
              <summary className="cursor-pointer text-sm font-medium underline decoration-dotted underline-offset-4">How this evidence is linked and how much it covers</summary>
              <div className="mt-3 text-sm leading-6">
            {/* Until 2026-09 this explained the gap by one organization's
                account structure, on a page whose sidecars were 92 Navy /
                59 Air Force / 22 Army against 14 DARPA sitewide (measured
                2026-09-18; run 4: 139 / 88 / 56 against 14). It names the
                mechanism now — gate 24 leg (p3) recomputes that mix.

                Task 26 (final review): the mechanism sentence said "A link is
                published only where something firmer says so: a contract
                announcement that names the program, or an account plus
                program-specific tokens". Unscoped that is false sitewide (the
                crosswalk publishes 11,315 links, at high or medium, on neither
                path), and in this page's scope — it counts only confidence='high'
                (fct_district_programs) — it omitted the 25 adjudicator-pinned
                account / account+subagency links of the 1,133 high on run 4,
                and "names the program" claims more than /methodology/ §4 does
                for an announcement link whose match basis went unrecorded (326
                of 1,074). It now states the page's own scope and points at §4
                for what the evidence is, rather than enumerating paths that
                the next tier change would silently falsify. */}
            <p>
              {orgPhrase}, and that is a limit of the method rather than a
              fact about this district. An award record carries a Treasury
              account, and one account funds dozens to hundreds of program
              elements — so an account code alone cannot say which line paid
              for a contract. This page counts only links the crosswalk grades
              high, where more than an account code ties the award to the
              program;{" "}
              <Link
                href="/methodology/#crosswalk-confidence"
                className="underline hover:text-foreground"
              >
                methodology §4
              </Link>{" "}
              says what does. Everything else is absent here rather than
              approximated.
            </p>
            <p className="mt-2">
              Aggregate totals are derived from USAspending award transaction
              data. Each figure opens to its formula and query.
              Recipients and transaction counts are USAspending&rsquo;s own;
              no additional verification applied.
            </p>
            {/* #51: the ratio that keeps the headline figure from reading as
                bigger than it is. Sitewide (see the note above the field
                definition) — computed from the same index totals the
                /district/ reconciliation line uses, so the two pages can
                never disagree about what fraction of all district-attributed
                award dollars this crosswalk actually reaches. */}
            {sitewideRatioPct !== null && (
              <p className="mt-2">
                This crosswalk only resolves for a small slice of all award
                dollars recorded with a district — sitewide, the{" "}
                {formatAmountNoCurrency(sitewideLinkable, "USD")} linked to a
                budget program is roughly{" "}
                <strong className="text-foreground">
                  {sitewideRatioPct.toFixed(2)}%
                </strong>{" "}
                of the{" "}
                {districtIndex.geo_grand_total !== null
                  ? formatAmountNoCurrency(districtIndex.geo_grand_total, "USD")
                  : "—"}{" "}
                in award obligations recorded across every U.S. district.
                Ranking districts by this figure would rank them by the
                high-confidence-linked slice, not by total defense spending —
                see{" "}
                <Link href="/district/" className="underline hover:text-foreground">
                  the district index
                </Link>{" "}
                for that comparison in full.
              </p>
            )}
              </div>
            </details>
          </ScopeNote>

        </PageIntro>

        {/* ── Obligations by fiscal year (ROADMAP #6) ────────────────────────
            No chart library, by design: ten rows of a table is the whole
            dataset, it is readable without JavaScript, every figure is
            clickable to its own citation, and a canvas would hide the numbers
            behind a hover. The <caption> is the "view as table" affordance —
            it names what the table is for a screen reader without adding a
            visible heading duplicate, and no [data-chart] is emitted, so gate
            6's chart-table leg has nothing to check here. */}
        {byYear.length > 0 && (
          <section className="mb-8" aria-labelledby="district-by-year-heading">
            <h2 id="district-by-year-heading" className="mb-2">
              Obligations by fiscal year
            </h2>
            <p className="text-muted-foreground text-sm mb-3">
              The same linkable obligations as the total above, split by the
              fiscal year each award transaction was recorded in. The years add
              up to that total, though the figures here are rounded for
              display, so adding them by eye need not land on it exactly. Award
              counts do not add up: an award active in two years appears in
              both.
            </p>
            <div className="rounded-lg border border-border overflow-x-auto bg-card">
              <table
                className="w-full text-sm"
                data-sort-table="district-years"
                data-sort-order="fiscal_year:asc"
              >
                <caption className="sr-only">
                  High-confidence linkable obligations for {heading} by fiscal
                  year, oldest first, each figure carrying its own citation.
                </caption>
                <thead className="bg-muted/50">
                  <tr>
                    <th scope="col" className="px-4 py-3 text-left t-label">
                      Fiscal year
                    </th>
                    <th scope="col" className="px-4 py-3 text-right t-label">
                      Obligations
                    </th>
                    {hasDeobligations && (
                      <th scope="col" className="px-4 py-3 text-right t-label hidden sm:table-cell">
                        Before deobligations
                      </th>
                    )}
                    <th scope="col" className="px-4 py-3 text-right t-label hidden md:table-cell">
                      Awards active
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {byYear.map((row) => (
                    <tr
                      key={row.fiscal_year}
                      className="hover:bg-muted/40 transition-colors"
                      data-district-year={row.fiscal_year}
                      data-sort-value={String(row.fiscal_year)}
                      data-fy-partial={
                        row.fiscal_year === partialFy ? "" : undefined
                      }
                    >
                      <td className="t-id px-4 py-3">
                        FY{row.fiscal_year}
                        {row.fiscal_year === partialFy && (
                          <span className="ml-2 font-sans text-xs text-muted-foreground">
                            partial year
                          </span>
                        )}
                      </td>
                      <td className="t-figure t-figure--2 px-4 py-3 text-right">
                        <Cite
                          value={row.total_obligation}
                          units="USD"
                          dataset="fct_district_totals_by_year"
                          factId={row.total_fact_id}
                          chip={false}
                        />
                      </td>
                      {hasDeobligations && (
                        <td className="t-figure t-figure--2 px-4 py-3 text-right text-muted-foreground hidden sm:table-cell">
                          <Cite
                            value={row.positive_obligation}
                            units="USD"
                            dataset="fct_district_totals_by_year"
                            factId={row.positive_fact_id}
                            chip={false}
                          />
                        </td>
                      )}
                      <td className="px-4 py-3 text-right text-muted-foreground hidden md:table-cell">
                        {row.award_count.toLocaleString("en-US")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {/* Task 26: this said "FY{partialFy} is still open — it does not
                close until September 30", a claim about the calendar that is
                false from Oct 1 while max_partial (a claim about the data)
                stays true for this corpus. It now states where the corpus's
                data ends — site_meta.award_fy_range.latest_action_date — which
                is true on every date. */}
            {showsPartialFy && (
              <p className="mt-2 text-xs text-muted-foreground">
                {awardFyRange?.latestActionDate
                  ? `FY${partialFy} runs only through ${awardFyRange.latestActionDate} in this corpus — a part-year total`
                  : `FY${partialFy} is a part-year total in this corpus`}
                , not comparable to the full years above it.
              </p>
            )}
            {hasDeobligations && (
              <p className="mt-2 text-xs text-muted-foreground">
                &ldquo;Obligations&rdquo; is the net figure: money obligated in
                that year minus money deobligated from earlier awards, which is
                why a year can be smaller than the gross column beside it, or
                negative. We publish the net number as the headline and show the
                gross so the difference is visible rather than implied.
              </p>
            )}
          </section>
        )}

        <div id="linked-programs" className="scroll-mt-24 mb-4">
          <p className="t-label mb-2">Program connections</p>
          <h2>Follow a program to its receipts.</h2>
          <p className="mt-2 text-sm text-muted-foreground">Amounts below are linked award obligations over <FyRange />. Shared awards may appear against more than one program; the district total counts each award once.</p>
        </div>
        {/* Program table */}
        {/* §P1-7 sort contract (gate 24 leg f): exporter-declared order —
            fct_district_programs is queried `order by pop_state, pop_district,
            total_obligation desc nulls last`. */}
        <div className="rounded-lg border border-border overflow-hidden bg-card">
          <table
            className="w-full text-sm"
            data-sort-table="district-programs"
            data-sort-order="total_obligation:desc"
          >
            <thead className="bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left t-label">
                  Program
                </th>
                <th className="px-4 py-3 text-left t-label hidden sm:table-cell">
                  Org
                </th>
                <th className="px-4 py-3 text-right t-label">
                  Obligations
                </th>
                <th className="px-4 py-3 text-right t-label hidden md:table-cell">
                  Recipients
                </th>
                <th className="px-4 py-3 text-right t-label hidden md:table-cell">
                  Transactions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {detail.programs.map((prog) => (
                <tr
                  // Task 27: the split key, not the pe_bli — a district can
                  // hold one row per member of a shared budget-line code.
                  key={prog.split_key}
                  className="hover:bg-muted/40 transition-colors"
                  data-program-key={prog.split_key}
                  data-program-account={prog.account ?? undefined}
                  data-sort-value={String(prog.total_obligation ?? -Infinity)}
                >
                  <td className="px-4 py-3">
                    <Link
                      href={prog.program_url}
                      className="font-medium text-primary hover:underline"
                    >
                      {prog.title}
                    </Link>
                    {/* The MEMBER's code: '0145-APN' / '0145-PANMC' where two
                        programs share '0145', the bare code everywhere else.
                        Printing the bare code on both rows would name neither
                        member (Task 27). */}
                    <span className="t-id ml-2">
                      {prog.split_key}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground hidden sm:table-cell">
                    {prog.organization}
                  </td>
                  <td
                    className="t-figure t-figure--2 px-4 py-3 text-right"
                    // #51: when this row's award is ALSO matched to other
                    // program elements, the dollar figure is one award
                    // attributed whole to each of them, not N awards' worth
                    // of money — data-shared-award-count is the DOM contract
                    // the district gate checks (leg e) so this can never
                    // silently regress to implying separate awards. React
                    // omits the attribute entirely when the value is
                    // undefined, so it is simply absent for count <= 1.
                    data-shared-award-count={
                      prog.shared_award_count > 1
                        ? prog.shared_award_count
                        : undefined
                    }
                  >
                    {prog.total_obligation !== null ? (
                      <Cite
                        value={prog.total_obligation}
                        units="USD"
                        dataset="fct_district_programs"
                        factId={prog.fact_id}
                      />
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                    {prog.shared_award_count > 1 && (
                      <span className="block text-xs font-sans font-normal text-muted-foreground mt-0.5">
                        same award, matched to {prog.shared_award_count}{" "}
                        programs
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right text-muted-foreground hidden md:table-cell">
                    {prog.recipient_count.toLocaleString("en-US")}
                  </td>
                  <td className="px-4 py-3 text-right text-muted-foreground hidden md:table-cell">
                    {prog.transaction_count.toLocaleString("en-US")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="mt-4 text-xs text-muted-foreground">
          Obligations are high-confidence USAspending award links only. Cited
          figures (underlined) open a USAspending citation with the API query
          used to verify the amount. See{" "}
          <Link href="/methodology/" className="underline hover:text-foreground">
            methodology
          </Link>{" "}
          for crosswalk details.
        </p>
      </div>
    </CitationPanelProvider>
  );
}
