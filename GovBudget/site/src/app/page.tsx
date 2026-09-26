import type { Metadata } from "next";
import Link from "next/link";
import styles from "./home.module.css";
import { EXHIBIT_PILOTS, PLATE_DESCS, PROGRAM_EXHIBITS } from "@/lib/program-exhibits";
import {
  getSiteMeta,
  getPrograms,
  getAgencies,
  getFeed,
  getReceiptMomentFact,
  collectCitationsWithInputs,
} from "@/lib/data";
import { SITE_NAME, SITE_URL } from "@/lib/site";
import { coreOgImages } from "@/lib/og";
import { Cite } from "@/components/cite";
import { CitationPanelProvider } from "@/components/citation-panel";
import { FeedHeadline } from "@/components/feed-headline";
import { EVENT_ORDER as FEED_EVENT_ORDER } from "@/lib/feed-model.mjs";
import { ReceiptMoment } from "@/components/receipt-moment";
import { ReceiptsIntro } from "@/components/receipts-intro";
import { Reveal } from "@/components/reveal";
import { serviceOrgName } from "@/lib/program-tier";
import { agencyDisplayName, agencyFullName } from "@/lib/agency-names";
import { COPY } from "@/lib/copy";

export const metadata: Metadata = {
  title: {
    absolute: `${SITE_NAME} — Federal Defense Budget, Contracts & Lobbying`,
  },
  description:
    "Every defense R&D and procurement program element — budget figures, awarded contracts, and lobbying filings — all traceable to their source documents.",
  alternates: { canonical: `${SITE_URL}/` },
  openGraph: {
    title: `${SITE_NAME} — Federal Defense Budget, Contracts & Lobbying`,
    description:
      "Every defense R&D and procurement program element — budget figures, awarded contracts, and lobbying filings — all traceable to their source documents.",
    url: `${SITE_URL}/`,
    siteName: SITE_NAME,
    images: coreOgImages("home"),
  },
};

export default function HomePage() {
  const meta = getSiteMeta();
  const programs = getPrograms();
  const agencies = getAgencies();

  // Feed signals: the three most consequential signals, in the SAME reading
  // order /feed/ and the RSS/Atom feeds use — EVENT_ORDER from feed-model.mjs
  // (the single declaration, imported rather than re-typed), and within an
  // event type the exporter's dollar-magnitude ranking (tri-persona Wave 3,
  // Task 4). It used to be `cards.slice(0, 3)` off a payload the mart had
  // ordered `by event_type, pe_bli` — three alphabetically-first PE codes.
  // Rendered as annotations on the one FY25→26 ledger below (round-3
  // critique), never as a second list.
  let feedTeaser: ReturnType<typeof getFeed>["cards"] = [];
  try {
    const rank = (t: string) => {
      const i = FEED_EVENT_ORDER.indexOf(t);
      return i === -1 ? FEED_EVENT_ORDER.length : i;
    };
    feedTeaser = [...getFeed().cards]
      // Stable sort (ES2019+): the exporter's intra-type ranking survives.
      .sort((a, b) => rank(a.event_type) - rank(b.event_type))
      .slice(0, 3);
  } catch {
    // feed sidecar not yet generated — render without teaser
  }

  // Top 5 movers by |fy2526_change| (trajectory must be non-null + change non-null)
  const topMovers = programs
    .filter((p) => p.trajectory && p.trajectory.fy2526_change !== null)
    .sort(
      (a, b) =>
        Math.abs(b.trajectory!.fy2526_change!) -
        Math.abs(a.trajectory!.fy2526_change!),
    )
    .slice(0, 5);

  // ONE ledger: signals whose programs are not top movers append as their
  // own rows in the same ledger, keeping the data-source-text /
  // data-xml-path anchors. A signal that names a mover no longer annotates
  // the row — the annotation restated the row's own figure at every width
  // (round-7: the ledger said everything twice).
  const moverPes = new Set(topMovers.map((p) => p.pe_bli));
  const extraSignals = feedTeaser
    .map((card, i) => ({ card, i }))
    .filter(({ card }) => !card.pe_bli || !moverPes.has(card.pe_bli));

  // Receipt moment: the largest FY2024-actuals figure with a jbook_pdf
  // citation — the panel renders the actual PDF page + highlight (Goal 1).
  const receiptFact = getReceiptMomentFact();

  // §P0-5: the canonical-TOA hero payload + corpus scope qualifier.
  const hero = meta.hero ?? null;
  const scopeQualifier = hero?.scope_qualifier ?? meta.scope_qualifier ?? null;

  // Citation slice: receipt-moment jbook_pdf fact_id + mover change fact_ids
  // (+ their peer inputs so the derived-card chips are clickable) + agency
  // FY24 derived fact_ids + feed teaser fact_ids.
  const pageFactIds: string[] = [];
  if (receiptFact) pageFactIds.push(receiptFact.fact_id);
  if (hero) pageFactIds.push(hero.fid);
  for (const p of topMovers) {
    if (p.trajectory_fact_ids?.fy2526_change) {
      pageFactIds.push(p.trajectory_fact_ids.fy2526_change);
    }
  }
  for (const a of agencies) {
    if (a.fy2024_fact_id_derived) pageFactIds.push(a.fy2024_fact_id_derived);
  }
  for (const card of feedTeaser) {
    if (card.figure_fact_id) pageFactIds.push(card.figure_fact_id);
  }
  const citationsSlice = collectCitationsWithInputs(pageFactIds);

  const sortedAgencies = [...agencies].sort(
    (a, b) => b.program_count - a.program_count,
  );

  return (
    <CitationPanelProvider citations={citationsSlice}>
    <div className={styles.home}>
      {/* One-time dismissible receipts-mode coach mark (home only) */}
      <ReceiptsIntro />

      <section className={styles.hero}>
        <div className={styles.stage}>
          {/* The vitrine's object: the hand-drawn Virginia-class plate,
              pulled in by REFERENCE (external <use> — inlining the ~120 KB
              source would break the homepage weight gate). The container's
              color sets the register: --plate-ink on the navy vitrine, with
              the hatch tones the plate reads on dark grounds. */}
          <div className={styles.stageImageWrap}>
            {/* The plate's register mark, the same mono stamp the field-
                guide plates carry below (`02 / AIR`, `03 / CYBER`) —
                numbering starts at 01 (six of six critics read the missing
                stamp as a bug, because it was one). */}
            <span className={styles.heroStamp} aria-hidden="true" data-plate-mark>
              01 / Sea
            </span>
            {/* Two renders of the SAME plate, exactly one visible per width
                (round-6 mobile critique #12): at ≥768 the whole yard at
                `meet`; at 390 the plate is cropped with intent —
                `xMin…slice` holds the bow and sail, not the whole yard
                shrunk to a postage stamp. */}
            <svg
              className={styles.stagePlateFull}
              viewBox="0 0 1800 960"
              role="img"
              aria-label="Conceptual submarine and shipyard illustration"
              preserveAspectRatio="xMidYMid meet"
              data-illustration=""
            >
              <desc>{PLATE_DESCS.virginia}</desc>
              <use href="/exhibits/plates/virginia.svg#virginia-plate" />
            </svg>
            <svg
              className={styles.stagePlateCrop}
              viewBox="0 0 1800 960"
              role="img"
              aria-label="Conceptual submarine and shipyard illustration, bow section"
              preserveAspectRatio="xMinYMid slice"
              data-illustration=""
            >
              <desc>
                A cropped view of the same side elevation, holding the
                submarine&apos;s bow and sail in the drydock.
              </desc>
              <use href="/exhibits/plates/virginia.svg#virginia-plate" />
            </svg>
          </div>
          <div className={styles.stageInner}>
            {/* One subject per screen (round-5 consensus): the object and
                its receipt. The eyebrow, lede, search field and persona
                line are gone — the word is the page's name, the number is
                the receipt; search lives in the site header. */}
            <div className={styles.heroCopy} data-display>
              <h1>See what your<br />tax dollars<br />build.</h1>
            </div>
            {/* The receipt is the vitrine's caption: the figure and its
                source sit beneath the hull, inside the composition. The
                element IS data-testid="receipt-moment" (G4 fold gate) —
                restyled, not moved out of the fold. */}
            {receiptFact && (
              <div className={styles.receiptDock}>
                <ReceiptMoment
                  peBli={receiptFact.pe_bli}
                  title={receiptFact.title}
                  org={receiptFact.org}
                  amountMillions={receiptFact.amount_millions}
                  factId={receiptFact.fact_id}
                  hero={hero}
                />
              </div>
            )}
          </div>
        </div>
      </section>

      {/* The field guide on PAPER (round-5: one navy→cream alternation per
          page — the hero is the only dark band). Each plate is the same
          object the hero uses: external <use>, container color = ink, mono
          corner caption, numbered callouts anchored to the measured plate
          points, the label list beside, its caption bar beneath. */}
      <section className={styles.fieldGuide}>
        <div className="spine">
          <h2 className={styles.sectionTitle}>{COPY.home.fieldGuideTitle(EXHIBIT_PILOTS.length)}</h2>
          <p className={styles.guideIntro} data-prose>
            {COPY.home.fieldGuideLede(EXHIBIT_PILOTS.length)}{" "}
            <Link href="/explore/">{COPY.home.fieldGuideLink}</Link>{" · "}
            <Link href="/feed/#budget-briefings">Budget comparisons</Link>
          </p>
          {/* The hero already owns the submarine — the gallery holds the
              other two pilots (round-4 critique: the same object rendered
              twice in 500px read as a stock asset, not a collection). */}
          <div className={styles.exhibits}>{EXHIBIT_PILOTS.filter(slug => slug !== "2013").map(slug => { const exhibit = PROGRAM_EXHIBITS[slug]; return <Link key={slug} href={`/program/${slug}/#exhibit`} className={styles.exhibitCard}>
            <div className={styles.plateGrid}>
              <div className={styles.plateFrame}>
                <span className={styles.plateStamp} data-plate-mark>{exhibit.eyebrow}</span>
                <svg viewBox="0 0 1800 960" role="img" aria-label={exhibit.caption} data-illustration="">
                  <desc>{PLATE_DESCS[exhibit.subject]}</desc>
                  <use href={`/exhibits/plates/${exhibit.subject}.svg#${exhibit.subject}-plate`} />
                </svg>
                {exhibit.topics.map((t, i) => (
                  <span
                    key={t.id}
                    aria-hidden="true"
                    className={styles.callout}
                    data-plate-mark
                    style={{ left: `${t.position[0]}%`, top: `${t.position[1]}%` }}
                  >0{i + 1}</span>
                ))}
              </div>
              <ol className={styles.plateLabels}>
                {exhibit.topics.map((t, i) => (
                  <li key={t.id}><span>0{i + 1}</span>{t.label}</li>
                ))}
              </ol>
            </div>
            <div className={styles.exhibitCaption}><h3>{exhibit.name}</h3></div>
            <p className={styles.plateCaption}>{exhibit.caption}</p>
          </Link>; })}</div>
        </div>
      </section>

      {/* Corpus totals live in the site footer now — one sentence with the
          four linked figures (the data-stat contract, linkgraph gate), not
          a stats strip (round-5 consensus). */}

      {/* ── Top movers ───────────────────────────────────────────────────── */}
      <section className="py-12 border-b border-border">
        <Reveal className="spine">
          {/* No arrow inside a heading (VOICE rule 6, gate 27 leg 15): the heading
              spells the pair the lede below names, FY2025 enacted and the
              FY2026 request; TRAJECTORY_FY_LABEL stays in chips and tables. */}
          <h2 className={styles.sectionTitle}>Largest FY2025–FY2026 changes</h2>
          <p className="text-sm text-muted-foreground mb-6">
            Programs with the biggest funding swings between FY2025 enacted and
            the FY2026 request, ranked by the size of the change in dollars with
            increases and decreases ranked together — when the list is all
            increases, that is the result, not a filter. Dollar deltas carry
            derived workbook citations. Each figure opens to its formula and
            inputs.
          </p>
          <div className={styles.ledger}>
            {topMovers.map((p) => {
              const change = p.trajectory!.fy2526_change!;
              const isPos = change >= 0;
              // §P0-2: all five of these movers are reconciliation-driven and
              // three of them have FALLING discretionary money. A reader
              // ranking "biggest funding swings" is entitled to know that the
              // swing is one-time reconciliation-bill money before they click.
              //
              // Deliberately NOT a second computation of disc_pct_change: that
              // rate is the exporter's (build_fy26_split), and two derivations
              // of one number is how this site ended up explaining $698.2M two
              // contradictory ways on one screen. What is rendered here is the
              // SHARE, and a direction — a comparison of two figures already on
              // this row. The like-for-like rate stays one click away on the
              // program page, which is where it is computed.
              const reconK = p.fy2026_reconciliation_toa_usd_thousands ?? 0;
              const discK = p.fy2026_disc_toa_usd_thousands ?? 0;
              const fy25K = p.trajectory?.fy2025_total ?? null;
              const reconShare =
                reconK > 0 && discK + reconK > 0
                  ? (reconK / (discK + reconK)) * 100
                  : null;
              const discDown = fy25K != null && reconK > 0 && discK < fy25K;
              // NOTE: the Cite (role=button) must NOT nest inside the Link —
              // axe flags nested-interactive. Title links; figure sits beside it.
              return (
                // PM Sprint 3 round-1 judging: this row used to be a single
                // `flex items-center justify-between` line whose Link was a
                // blockified flex item with `min-w-0` but no `overflow-hidden`
                // — so at 390 the inline title simply overflowed its box and
                // printed ON TOP of the dollar delta beside it. Two of the
                // five figures on the site's front page were unreadable.
                //
                // It stacks below `sm` (title above figure, so a collision is
                // impossible by construction) and keeps the one-line desktop
                // row above it. `min-w-0` alone was never enough; the Link now
                // also clips, so a long title truncates instead of escaping.
                <div
                  key={p.pe_bli}
                  data-mover-row=""
                  className={`${styles.ledgerRow} px-1 py-4 group`}
                >
                  <div className="flex flex-col items-start gap-1 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
                  <Link
                    href={`/program/${p.slug}/`}
                    data-mobile-pair-label=""
                    className="flex min-w-0 max-w-full flex-wrap items-baseline gap-x-2 overflow-hidden"
                  >
                    <span className="t-id">
                      {p.pe_bli}
                    </span>
                    <span className="text-sm font-medium group-hover:underline">
                      {p.title}
                    </span>
                    {/* §P1-E badge sweep: the human service name, never the
                        raw workbook token ("F"). */}
                    <span className="text-xs text-muted-foreground" title={`Organization code ${p.org}`}>
                      {serviceOrgName(p.org)}
                    </span>
                    {reconShare != null && (
                      <span
                        data-mover-recon={reconShare.toFixed(1)}
                        data-mover-disc-down={discDown ? "" : undefined}
                        className={styles.reconNote}
                      >
                        {reconShare.toFixed(0)}% one-time reconciliation
                        {discDown && " · discretionary down"}
                      </span>
                    )}
                  </Link>
                  <div
                    data-mobile-pair-value=""
                    data-primary-value="mover-change"
                    className={[
                      styles.moverValue,
                      "t-figure t-figure--3 shrink-0 sm:ml-4",
                      isPos ? styles.moverUp : styles.moverDown,
                    ].join(" ")}
                  >
                    <span>
                      {isPos ? "+" : ""}
                      <Cite
                        value={change}
                        units="USD thousands"
                        dataset="fct_budget_trajectory"
                        factId={p.trajectory_fact_ids?.fy2526_change}
                        basis="toa"
                        fy={2026}
                        measure="change"
                        entity={p.pe_bli}
                        edition={2026}
                        chip={false}
                      />
                    </span>
                    {/* Delta and rate together on the right — the annotation
                        sentence that restated them is gone at every width
                        (round-7: the ledger said everything twice). */}
                    {p.trajectory!.fy2526_pct_change !== null && (
                      <span className={styles.moverPct}>
                        {"· "}
                        {isPos ? "+" : "−"}
                        {Math.abs(p.trajectory!.fy2526_pct_change!).toLocaleString(
                          "en-US",
                          { maximumFractionDigits: 0 },
                        )}
                        %
                      </span>
                    )}
                  </div>
                  </div>
                </div>
              );
            })}
            {/* Signals whose programs are not top movers append as their own
                rows — the same ledger, the same hairlines. */}
            {extraSignals.map(({ card, i }) => (
              <div
                key={`feed-${i}`}
                className={`${styles.ledgerRow} flex flex-col gap-1 px-1 py-4 sm:flex-row sm:items-center sm:justify-between sm:gap-4`}
              >
                <div className="min-w-0 flex-1">
                  <p
                    className="text-sm font-medium line-clamp-2 sm:truncate"
                    data-source-text="headline"
                    data-xml-path={`site:feed/${card.event_type}/${card.pe_bli ?? card.family_key ?? i}`}
                  >
                    <FeedHeadline card={card} />
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {card.event_type.replace(/_/g, " ")}
                  </p>
                </div>
                {card.program_url && (
                  <Link
                    href={card.program_url}
                    className={`shrink-0 self-start sm:ml-4 sm:self-auto ${styles.viewLink}`}
                  >
                    view
                  </Link>
                )}
              </div>
            ))}
          </div>
          {/* ONE methodology footnote for the whole ledger (round-4 critique:
              two caveat paragraphs before the first figure and a third after
              the list read as template disclaimer-stacking). Both sentences
              moved here verbatim — scope text first.
              Backlog #49: the scope tail reads meta.corpus_scope — the SAME
              string the hero qualifier and the /programs/, /years/,
              /methodology/, /data/ corpus statement carry, so it cannot
              drift from them again. */}
          <p className="text-xs text-muted-foreground mt-2">
            Trajectory figures are derived from budget justification
            workbooks — each delta cites its FY25/FY26 inputs.
            {scopeQualifier && meta.corpus_scope && (
              <>
                {" "}
                Scope: ranked across the R&D and procurement program elements
                in our corpus ({meta.corpus_scope}).
              </>
            )}{" "}
            See{" "}
            <Link href="/methodology/" className="underline hover:text-foreground">
              methodology
            </Link>
            .
          </p>
        </Reveal>
      </section>

      {/* ── Agency index ─────────────────────────────────────────────────── */}
      <section id="agencies" className="py-12 scroll-mt-16">
        <Reveal className="spine">
          <h2 className={styles.sectionTitle}>Browse by agency</h2>
          <p className="text-sm text-muted-foreground mb-6">
            {agencies.length} defense agencies, each linked to its program
            elements.
          </p>
          {/* One register, three columns of DATA — name | programs | FY24 —
              not a three-across card grid whose rules drift out of register
              from row two down (round-4 critique). "FY24" is said once, in
              the column head, not 24 times. Cite (role=button) must not nest
              inside the Link — the org name links; the FY24 sum is a sibling
              Cite in its own cell (derived citation). */}
          <table className={styles.agencyTable}>
            <thead>
              <tr>
                <th className="t-label">Agency</th>
                <th className={`t-label ${styles.agencyNum}`}>Programs</th>
                <th className={`t-label ${styles.agencyNum}`}>FY24</th>
              </tr>
            </thead>
            <tbody>
              {sortedAgencies.map((agency, i) => (
                /* Eight rows + the "all agencies" link at ≥768; the six
                   largest + the same link on phones (round-7: desktop
                   matches mobile's already-right pattern). */
                <tr
                  key={agency.org}
                  className={
                    i >= 8
                      ? styles.agencyRowExtra
                      : i >= 6
                        ? styles.agencyRowMid
                        : ""
                  }
                >
                  {/* Tri-persona Wave 3, Task 3: the full component name is
                      the headline and the workbook code sits beside it,
                      still visible because it is the page's identity and the
                      workbook's key. */}
                  <td>
                    <Link
                      href={`/agency/${agency.org}/`}
                      className={styles.agencyName}
                      title={`Organization code ${agency.org}`}
                    >
                      {agencyDisplayName(agency.org)}
                    </Link>
                    {agencyFullName(agency.org) && (
                      <span
                        data-agency-code={agency.org}
                        className={styles.agencyCode}
                      >
                        {agency.org}
                      </span>
                    )}
                  </td>
                  <td className={`t-figure t-figure--2 ${styles.agencyNum}`}>{agency.program_count}</td>
                  <td className={`t-figure t-figure--2 ${styles.agencyNum}`}>
                    {agency.fy2024_total_millions > 0 && (
                      <Cite
                        value={agency.fy2024_total_millions}
                        units="USD millions"
                        dataset="dim_programs"
                        factId={agency.fy2024_fact_id_derived}
                        basis="jbook-detail"
                        fy={2024}
                        measure="actuals"
                        entity={agency.org}
                        edition={2026}
                        chip={false}
                      />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {/* Phones see the six largest; the full index is one tap away. */}
          <Link href="/agency/" className={styles.agencyMore}>
            All {agencies.length} agencies →
          </Link>
        </Reveal>
      </section>

      {/* ── Trust anchor ─────────────────────────────────────────────────── */}
      <section className={styles.trust}>
        <Reveal className="spine">
          <p className="text-muted-foreground text-sm">
            All figures are cited to their exact source document, page, API
            query, or derived formula — every published dataset carries a
            citation tier. See{" "}
            <Link href="/methodology/" className="underline hover:text-foreground">
              full methodology
            </Link>
            . Correlation is shown, not causation.
          </p>
          {/* §P0-5 scope qualifier — below the fold, ONCE (round-5: the
              fold's subject is the object and its receipt; the qualifier
              qualifies the superlative, it does not compete with it).
              Sentence moved verbatim. */}
          {scopeQualifier && (
            <p
              data-testid="hero-scope-qualifier"
              className={`${styles.scopeNote} mt-3`}
            >
              {"Scope: "}
              {scopeQualifier}.
            </p>
          )}
        </Reveal>
      </section>
    </div>
    </CitationPanelProvider>
  );
}
