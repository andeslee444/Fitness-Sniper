import type { Metadata } from "next";
import Link from "next/link";
import { getFlowChartMeta } from "@/lib/data";
import { SITE_NAME, SITE_URL } from "@/lib/site";
import { coreOgImages } from "@/lib/og";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { CitationPanelProvider } from "@/components/citation-panel";
import { CoverageNote } from "@/components/coverage-note";
import { ScopeNote } from "@/components/notes";
import { FlowChart } from "@/components/flow-chart";
import { PageIntro } from "@/components/page-intro";

/**
 * /flow/ — the two-river budget flowdown (Phase 5H; reframed PM Sprint 3
 * Task 6, §Coverage).
 *
 * WHAT CHANGED AND WHY. The page used to open on the bridge: an honest note
 * saying 98.7% of the request is not crosswalked, above the fold, before the
 * reader knew what they were looking at. Read cold, that is a page announcing
 * its own failure — and it buried the actual finding underneath.
 *
 * The finding is the two rivers themselves. What the Pentagon ASKED FOR and
 * what it PUT ON CONTRACT are recorded by two systems that do not share units,
 * fiscal-year semantics, or source documents, so the two totals cannot be
 * added, divided, or reconciled into one number — and almost every published
 * chart of "defense spending" quietly does one of those three things. Saying
 * that plainly, with both rivers drawn to their own scale and neither
 * pretending to explain the other, is the publishable result. The bridge is
 * the honest measurement of how far the two CAN be connected; it now sits in
 * its own section under the chart, keeps its number exactly as it was, and is
 * linked from the lede and from /coverage/#crosswalk.
 *
 * Server shell only: title + Experimental tag, the two-river statement, the
 * per-river unit statements, and the bridge section. The heavy precomputed
 * Sankey payload (flow_chart.json) is fetched by the client island, and
 * citations resolve lazily through cite-shards — the provider mounts with an
 * EMPTY embedded slice (same architecture as /years/).
 *
 * Gate contracts kept intact (G9 leg e): [data-flow-experimental],
 * [data-coverage="flow-bridge"] stating the not-yet-crosswalked gap, and the
 * built string "FY#### President's Budget" with its space.
 */

const _meta = getFlowChartMeta();
const _fyFirst = _meta.spendFys[0];
const _fyLast = _meta.spendFys[_meta.spendFys.length - 1];

export const metadata: Metadata = {
  title: "Flow — two rivers of defense money",
  description:
    `What the Pentagon asked for (FY${_meta.budgetFy} request, by program) and what it put on contract ` +
    `(FY${_fyFirst}–FY${_fyLast} obligations, by contractor family), drawn as two rivers that cannot be ` +
    "added together — different units, different years, different source systems. Every node cited.",
  alternates: { canonical: `${SITE_URL}/flow/` },
  openGraph: {
    title: `Flow — two rivers of defense money | ${SITE_NAME}`,
    description:
      "The budget system and the contract system are two different measurement systems, and that is the finding. Both rivers drawn to their own scale, with the bridge between them measured rather than assumed.",
    url: `${SITE_URL}/flow/`,
    siteName: SITE_NAME,
    images: coreOgImages("flow"),
  },
};

export default function FlowPage() {
  const meta = getFlowChartMeta();
  return (
    <CitationPanelProvider citations={{}}>
      {/* The site spine (ROADMAP #42) — same left edge and same width as
          every other page; the chart was already sized for it. */}
      <div className="spine py-8">
        <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: "Flow" }]} />
        <PageIntro eyebrow="Research tools / Map" title="Follow the money"
          description={<p>Explore what the Pentagon requested and what it committed on contracts. Each view has its own years, units, and source receipts.</p>}
          actions={<><a href="#money-map">Explore the map ↓</a><a href="#bridge">Inspect the contractor bridge</a><Link href="/years/">Compare budget years →</Link></>}>
            <span
              data-testid="flow-experimental"
              data-flow-experimental=""
              className="research-status rounded-full border border-amber-500/50 bg-amber-500/10 px-2.5 py-0.5 text-xs font-semibold"
            >
              Experimental
            </span>

          {/* THE LEDE IS THE FINDING, not a caveat about the chart. */}
          <p className="my-3 text-sm leading-6 text-foreground">
            The two rivers use different measurement systems. Their totals
            cannot be added together, divided into each other, or reconciled
            into a single number. Click a block to inspect its source.
          </p>

          {/* The two systems, side by side. Per-river unit statements are
              always visible (the /years/ CapIQ convention, doubled) — they are
              the evidence for the claim in the lede, not fine print. */}
          <div className="mb-3 grid gap-3 sm:grid-cols-2">
            <div className="rounded-md border border-border bg-muted/30 px-3 py-2.5">
              <p className="t-label mb-1">
                Budget river — intent
              </p>
              {/* One template literal, not JSX text chunks: Turbopack drops
                  the leading space of an entity-bearing chunk after an
                  expression ("FY2026President's" regression — G9 leg e
                  asserts the built string). */}
              <p className="text-sm font-medium text-foreground">
                {`USD thousands — FY${meta.budgetFy} President's Budget (R-1 + P-1).`}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                A request for one fiscal year, as published in the justification
                books. It is a plan, not a payment.
              </p>
            </div>
            <div className="rounded-md border border-border bg-muted/30 px-3 py-2.5">
              <p className="t-label mb-1">
                Spend river — obligations
              </p>
              <p className="text-sm font-medium text-foreground">
                USD — DoD prime contract obligations for the selected fiscal
                year (FY{_fyFirst}–FY{_fyLast}
                {meta.fy2026Partial ? "; FY2026 is a partial year" : ""}).
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                Money committed on contract actions, which may pay for work
                requested in an earlier year — and often does.
              </p>
            </div>
          </div>

          <details className="mt-3 border-t border-border pt-3 text-sm">
            <summary className="cursor-pointer font-medium text-foreground">How budget years and contract years differ</summary>
          <ScopeNote className="mt-3" label={null}>
          <div data-prose>
            <p>
              A request dollar is not an obligation dollar, and a budget year is
              not an obligation year: multi-year appropriations, continuing
              resolutions and contract timing all put the two on different
              clocks. So the two rivers here are drawn to their own scales and
              neither is presented as explaining the other. Charts that show one
              total for &ldquo;defense spending&rdquo; have usually chosen one
              of these systems without saying which — the choice is the whole
              answer, and it is rarely stated.
            </p>
            <p className="mt-2">
              Where the two <em>can</em> be connected, they are — and how far
              that gets is measured, not assumed. See{" "}
              <a href="#bridge" className="underline hover:text-foreground">
                the bridge between them
              </a>{" "}
              below the chart. Click any block for its citation.
            </p>
          </div>
          </ScopeNote>
          </details>
        </PageIntro>

        <div id="money-map" className="scroll-mt-24"><FlowChart /></div>

        {/* ── The bridge: reachable, labelled, and its number unchanged ───── */}
        <section id="bridge" className="mt-10 max-w-4xl scroll-mt-20">
          <h2 className="mb-2">
            The bridge between them
          </h2>
          <p className="mb-2 text-sm leading-7 text-muted-foreground">
            The bridge records associations between budget lines and award
            records. Its coverage is measured in budget request dollars;
            it does not allocate a contract&apos;s obligations to a particular
            program line.
          </p>
          {/* Bridge honesty — G2 + G9 contract (data-coverage="flow-bridge"). */}
          <CoverageNote id="flow-bridge" className="mb-2" />
          <p className="text-sm leading-7 text-muted-foreground">
            An appropriation account can fund many program elements, so an
            account match alone cannot identify which line paid for a contract.
            Stronger links need evidence about the program itself.{" "}
            <Link
              href="/coverage/#crosswalk"
              className="underline hover:text-foreground"
            >
              See the evidence and coverage limits →
            </Link>
          </p>
        </section>

        {/* ROADMAP #29(c). The third thing that moves is the IDENTITY of the
            line itself, and it moves without a dollar figure attached — which
            is why it gets its own page and its own drawing rules rather than a
            third river here. Linked from /flow/ because a reader who has just
            been told "these two systems cannot be added" is exactly the reader
            who needs to know the labels move too. */}
        <section className="mt-8 max-w-4xl">
          <h2 className="mb-2">
            And the lines themselves move
          </h2>
          <p className="text-sm leading-7 text-muted-foreground">
            Program elements can be renamed, realigned, and merged. Before
            comparing one across two years, check its identity history.
            The separate lineage map uses equal-width links: a cited
            relationship carries no claim about the amount transferred.{" "}
            <Link href="/lineage/" className="underline hover:text-foreground">
              One funded line, all the names it wore →
            </Link>
          </p>
        </section>
      </div>
    </CitationPanelProvider>
  );
}
