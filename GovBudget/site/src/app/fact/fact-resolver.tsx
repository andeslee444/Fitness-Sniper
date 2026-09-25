"use client";

/**
 * fact-resolver.tsx — client resolver for /fact/{id} permalinks
 * (PM Sprint 1 Task 5, spec §P0-4.1).
 *
 * Design (locked): the deployed route is a Vercel rewrite (`/fact/:id` →
 * `/fact/`, site/public/vercel.json) in front of this single static page;
 * the id is parsed back out of location.pathname (`?id=` fallback works
 * without the rewrite) and resolved from the SAME cite-shard files the
 * citation panel uses (/json/cite-shards/{id[:2]}.json). Full per-fact SSG
 * is deferred. Accepts 8-hex public ids (prefix scan; ALL matches render
 * when a prefix collides — 2 colliding fid8 pairs exist in today's corpus)
 * and 16-hex full ids (exact lookup).
 *
 * Renders exactly what the citation payload provides — value with unit,
 * document title, locator, full SHA-256, retrieval date, official-source
 * link, hosted-PDF link, derived formula + input permalinks, and (when the
 * payload carries pe_bli) an "Appears on" /program/{pe}/#fact-{id} parent
 * link. Fields the payload lacks are omitted, never guessed.
 *
 * SEMANTIC HEADER (visual-judge M2): when the payload carries pe_bli, the
 * card ALSO fetches the program sidecar the site already serves
 * (/json-lite/program_details/{pe}.json) plus search_quick.json (the
 * program title), locates the figure whose fid/public_id matches, and
 * renders `F-35 (ATA000) · FY2024 · Actuals · P-40 detail · PB2026` above
 * the value — plus the drawer's compact-USD equivalence ("(= $5.25B)",
 * lib/format usdEquivalence). No sidecar figure match → the citation
 * payload alone renders (no fabrication).
 *
 * PERMALINK ORIGIN (visual-judge M3): the rendered/copied permalink pins to
 * the canonical SITE_URL, never window.location — a permalink is an
 * identifier, and 127.0.0.1 permalinks were leaking into copied footnotes.
 *
 * SUPERSEDE DISPLAY (spec §P0-4.5): deliberately ABSENT. Citation payloads
 * carry no superseded flag today — superseded warehouse rows are fenced out
 * of the export entirely (export_site.py `where not … superseded`), so a
 * resolvable fact id is by construction current. When the exporter starts
 * shipping superseded facts WITH a marker + successor pointer, render the
 * correction + link here; until then there is nothing honest to show.
 */

import React, { useContext, useEffect, useState } from "react";
import { ExternalLink } from "lucide-react";
import { CopyButton } from "@/components/copy-button";
import { SourceDocumentLinks } from "@/components/source-document-links";
import { useBudgetPdfReceipt } from "@/components/use-budget-pdf-receipt";
import { pagedAmountCitation } from "@/lib/citations";
import { PageIntro } from "@/components/page-intro";
import styles from "./fact-resolver.module.css";
import { CitationPanelProvider } from "@/components/citation-panel";
import { CitationPanelContext, basisChipText } from "@/components/cite";
import { exhibitFamilyFromSheet, type ExhibitFamily } from "@/lib/basis";
import { useAssetUrl } from "@/components/asset-config";
import { fetchCitationShard, shardPrefix } from "@/lib/cite-shards";
import {
  findSidecarFigure,
  parseFactPermalinkId,
  programTitleFromQuick,
  resolveFactMatches,
  type FactMatch,
  type SidecarFigureContext,
} from "@/lib/fact-resolver";
import {
  footnoteInputFromCitation,
  type FootnoteInput,
} from "@/lib/footnote";
import { usdEquivalence, formatCount } from "@/lib/format";
import type { Citation } from "@/lib/citations";
import { SITE_NAME, SITE_URL } from "@/lib/site";

// ── Resolution state machine ────────────────────────────────────────────────

type ResolverState =
  | { status: "idle" } // no id in the URL — explainer only (also the SSG state)
  | { status: "loading"; id: string }
  | { status: "resolved"; id: string; matches: FactMatch[] }
  | { status: "error"; id: string }; // shard unreachable — degraded, never fake

export function FactResolver() {
  const [state, setState] = useState<ResolverState>({ status: "idle" });

  useEffect(() => {
    const id = parseFactPermalinkId(
      window.location.pathname,
      window.location.search,
    );
    if (!id) return; // stay on the explainer
    let cancelled = false;
    // Deferred one microtask so the effect body performs no synchronous
    // setState (react-hooks/set-state-in-effect); the functional updater
    // guards the race — a shard resolution that somehow lands first is never
    // clobbered back to "loading".
    queueMicrotask(() => {
      if (cancelled) return;
      setState((prev) =>
        prev.status === "idle" ? { status: "loading", id } : prev,
      );
    });
    fetchCitationShard(shardPrefix(id)).then((shard) => {
      if (cancelled) return;
      if (!shard) {
        setState({ status: "error", id });
        return;
      }
      setState({ status: "resolved", id, matches: resolveFactMatches(shard, id) });
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const matches = state.status === "resolved" ? state.matches : [];
  const citationsMap = Object.fromEntries(
    matches.map((m) => [m.factId, m.citation]),
  );

  return (
    <CitationPanelProvider citations={citationsMap}>
      <div className="spine py-10">
        <PageIntro
          eyebrow="Evidence / Permanent record"
          title="The receipt behind the number."
          description={<p>Inspect the recorded figure, its source document, and the exact location of the evidence. Every figure on {SITE_NAME} carries a permanent fact id so someone else can check your work.</p>}
          actions={<><a href="/programs/">Find a program</a><a href="/methodology/#verification">How verification works</a></>}
        />

        {state.status === "loading" && (
          <div
            data-testid="fact-loading"
            className="animate-pulse space-y-2 mb-10"
            aria-label="Resolving fact"
          >
            <div className="h-2 w-3/5 rounded bg-border" aria-hidden="true" />
            <div className="h-2 w-full rounded bg-border" aria-hidden="true" />
            <p className="pt-1 text-xs text-muted-foreground">
              Resolving fact #{state.id}…
            </p>
          </div>
        )}

        {state.status === "error" && (
          <div
            data-testid="fact-error"
            role="alert"
            className="mb-10 rounded-lg border border-destructive/40 bg-destructive/5 p-5"
          >
            <p className="text-sm font-medium">
              Couldn&apos;t load the citation data for fact{" "}
              <span className="font-mono">#{state.id}</span>.
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              Check your connection and reload to try again. The source could
              not be verified in this visit.
            </p>
          </div>
        )}

        {state.status === "resolved" && matches.length === 0 && (
          <div
            data-testid="fact-not-found"
            className="mb-10 rounded-lg border border-border bg-muted/40 p-5"
          >
            <p className="text-sm font-medium">
              No fact <span className="font-mono">#{state.id}</span> in the
              current corpus.
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              Check the id for typos (8 or 16 hex characters). Fact ids appear
              in Receipts-mode chips, the citation drawer footer, and copied
              footnotes.
            </p>
          </div>
        )}

        {state.status === "resolved" && matches.length > 1 && (
          <p
            data-testid="fact-collision-note"
            data-note-kind="caution"
            role="note"
            aria-label="Ambiguous fact id — more than one fact shares this prefix"
            className="mb-4 rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800"
          >
            {formatCount(matches.length)} facts share the 8-character prefix{" "}
            <span className="font-mono">#{state.id}</span> — all are shown
            below. Use the full 16-character id to disambiguate.
          </p>
        )}

        {matches.map((m) => (
          <FactCard key={m.factId} factId={m.factId} citation={m.citation} />
        ))}

        <Explainer />
      </div>
    </CitationPanelProvider>
  );
}

// ── Explainer (the bare-/fact/ content; also the SSG-rendered state) ────────

function Explainer() {
  return (
    <section data-testid="fact-explainer" className={styles.explainer}>
      <h2>How fact permalinks work</h2>
      <p className="text-sm text-muted-foreground leading-6">
        <span className="font-mono">/fact/{"{id}"}</span>{" "}resolves a fact id to
        the receipt behind it: the recorded value, the official source
        document, the exact page or cells, the document&apos;s SHA-256, and
        the retrieval date. Both the short public id (8 characters, shown on
        Receipts-mode chips and in the citation drawer) and the full
        16-character id resolve.
      </p>
      <p className="text-sm text-muted-foreground leading-6">
        Corrections follow a supersede-not-delete policy — see the{" "}
        <a href="/about/" className="underline underline-offset-2">
          corrections policy
        </a>{" "}
        and{" "}
        <a href="/methodology/" className="underline underline-offset-2">
          methodology
        </a>
        .
      </p>
    </section>
  );
}

// ── FactCard — one resolved fact ────────────────────────────────────────────

const KIND_LABELS: Record<string, string> = {
  jbook_pdf: "Budget Justification PDF",
  workbook: "Budget Workbook",
  lda_filing: "LDA Lobbying Filing",
  derived: "Derived Figure",
  usaspending: "USAspending Query",
  state_soql: "State Open Data Query",
  state_file: "State Source File",
  jbook_narrative: "J-book Narrative",
  announcement: "Official DoD contract announcement",
  subaward: "FSRS subaward record via USAspending",
};

/** Human labels for the core measure tokens in the semantic header. */
const CORE_MEASURE_LABELS: Record<string, string> = {
  actuals: "Actuals",
  enacted: "Enacted",
  request: "Request",
  total: "Total",
  change: "Change",
};

/**
 * `F-35 (ATA000) · FY2024 · Actuals · P-40 detail · PB2026` — every part
 * optional (absent context drops, never renders a guess). The basis+edition
 * segment reuses basisChipText, the SAME vocabulary the site's basis chips
 * render, so this page can never disagree with a chip about the basis.
 *
 * §48: `exhibitFamily` qualifies a TOA basis to the CLICKED CITATION's own
 * exhibit — the caller derives it from `citation.sheet` via
 * exhibitFamilyFromSheet, the same locator-based signal the citation drawer
 * uses (workbook-card.tsx). Omitted, this degrades to "P-1/R-1 TOA".
 */
export function semanticHeaderText(
  figure: SidecarFigureContext,
  title: string | null,
  peBli: string,
  exhibitFamily?: ExhibitFamily,
): string {
  const parts: string[] = [title ? `${title} (${peBli})` : peBli];
  if (figure.fy != null && /^\d{4}$/.test(String(figure.fy))) {
    parts.push(`FY${figure.fy}`);
  }
  const chip = figure.basis
    ? basisChipText(
        figure.basis,
        figure.measure ?? undefined,
        figure.edition ?? undefined,
        exhibitFamily,
      )
    : null;
  if (figure.measure && CORE_MEASURE_LABELS[figure.measure]) {
    parts.push(CORE_MEASURE_LABELS[figure.measure]);
  } else if (figure.measure && !chip) {
    // Extended tokens render inside the chip when one exists; chip-less
    // bases (non-budget) still show the humanized token here.
    parts.push(figure.measure.replace(/-/g, " "));
  }
  if (chip) parts.push(chip);
  else if (figure.edition) parts.push(`PB${figure.edition}`);
  return parts.join(" · ");
}

/** The resolved sidecar context for one card: figure + program title. */
interface SemanticContext {
  figure: SidecarFigureContext;
  title: string | null;
}

function FactCard({
  factId,
  citation,
}: {
  factId: string;
  citation: Citation;
}) {
  const { openPanel } = useContext(CitationPanelContext);
  const assetUrl = useAssetUrl();
  const pdfReceipt = useBudgetPdfReceipt(citation.kind === "workbook" || citation.kind === "derived" ? factId : null);
  const hasHighlightedSource = Boolean(pdfReceipt?.parts.length) || (citation.kind === "jbook_pdf" && Boolean(pagedAmountCitation(citation)));

  // One derivation for value/title/locator/permalink — the SAME builder the
  // copy-as-footnote path uses (lib/footnote.ts), so this page can never
  // disagree with the footnote about what the payload says. Canonical
  // origin (M3): never window.location.
  const input: FootnoteInput = footnoteInputFromCitation(citation, factId, {
    origin: SITE_URL,
  });

  // Parent link — ONLY when the payload itself carries pe_bli (P0-4 "appears
  // on"). Today's shards do not carry it yet; the exporter now emits it, so
  // the link lights up at the next export without a site change.
  const peBli = (citation as { pe_bli?: string | null }).pe_bli ?? null;

  // Semantic header (M2): sidecar figure + program title, fetched only when
  // the payload names its parent program. A failed fetch or an id with no
  // sidecar figure leaves `semantic` null — payload-only render, no guess.
  const [semantic, setSemantic] = useState<SemanticContext | null>(null);
  useEffect(() => {
    if (!peBli) return;
    let cancelled = false;
    const getJson = (url: string) =>
      fetch(url)
        .then((r) => (r.ok ? r.json() : null))
        .catch(() => null);
    Promise.all([
      getJson(`/json-lite/program_details/${peBli}.json`),
      getJson("/json-lite/search_quick.json"),
    ]).then(([sidecar, quick]) => {
      if (cancelled) return;
      const figure = findSidecarFigure(sidecar, factId);
      if (!figure) return;
      setSemantic({ figure, title: programTitleFromQuick(quick, peBli) });
    });
    return () => {
      cancelled = true;
    };
  }, [peBli, factId]);

  // Compact-USD equivalence — the drawer's formatter (usdEquivalence), so
  // "$5,247.070 million" reconciles with the "$5.25B" shown on cards.
  const equivalence =
    semantic && semantic.figure.value != null
      ? usdEquivalence(semantic.figure.value, semantic.figure.units)
      : null;

  const kindLabel = KIND_LABELS[citation.kind] ?? citation.kind;

  return (
    <article
      data-testid="fact-card"
      className={styles.receipt}
    >
      <header className={styles.receiptHeader}>
        <span className={styles.sourceKind}>
          {kindLabel}
        </span>
        <span className="t-id">
          fact #{factId.slice(0, 8)}
        </span>
      </header>

      <div className={styles.receiptBody}>
        {citation.kind === "jbook_pdf" && citation.resolution === "unresolved" && (
          <p role="status">The exact amount location in the source PDF has not been verified. The document link remains available.</p>
        )}
        <div className={styles.lead}>
          <p className={`t-label ${styles.recordLabel}`}>{citation.kind === "subaward" ? "Inferred program link" : citation.kind === "derived" ? "Derived from source records" : citation.kind === "jbook_pdf" && citation.resolution === "unresolved" ? "Source document" : "Recorded in the source"}</p>
      {semantic && peBli && (
        <p
          data-testid="fact-semantic-header"
          className={styles.semantic}
        >
          {semanticHeaderText(
            semantic.figure,
            semantic.title,
            peBli,
            exhibitFamilyFromSheet(citation.sheet),
          )}
        </p>
      )}

      {input.valueText && (
        <p className={`t-figure t-figure--5 ${styles.value}`}>
          {input.valueText}
          {equivalence && (
            <span className="ml-1.5 text-base font-normal text-muted-foreground">
              ({equivalence})
            </span>
          )}
        </p>
      )}

      <div className={styles.sourceActions}>
        {!hasHighlightedSource && <button
          type="button"
          data-testid="fact-view-source"
          onClick={() => openPanel(factId)}
          className={styles.openSource}
        >
          {citation.kind === "subaward" ? "View link evidence" : citation.kind === "jbook_pdf" && citation.resolution === "unresolved" ? "View source details" : "View source excerpt"}
        </button>}
        <SourceDocumentLinks citation={citation} factId={factId} program={peBli ?? undefined} surface="fact-page" compact resolveInputs />
        {citation.hosted_pdf_url && (
          <a
            href={assetUrl(citation.hosted_pdf_url)}
            target="_blank"
            rel="noopener noreferrer"
            className={styles.sourceLink}
          >
            <ExternalLink className="h-3 w-3 shrink-0" aria-hidden="true" />
            Saved PDF copy
            {citation.page_number != null ? ` (page ${citation.page_number})` : ""}
            <span className="sr-only">(opens in new tab)</span>
          </a>
        )}
      </div>
        </div>
      <dl className={styles.metadata}>
        <Row label="Full fact id">
          <span className="font-mono">{factId}</span>{" "}
          <CopyButton text={factId} label="Copy full fact id" />
        </Row>
        <Row label="Permalink">
          <span className="font-mono break-all">{input.permalink}</span>{" "}
          <CopyButton text={input.permalink} label="Copy permalink" />
        </Row>
        {input.docTitle && (
          <Row label="Document">
            {input.docTitle}
            {input.publisher ? ` — ${input.publisher}` : null}
          </Row>
        )}
        {input.locator && (input.locator.exhibit || input.locator.page != null) && (
          <Row label="Location">
            {[
              input.locator.exhibit,
              input.locator.page != null ? `p. ${input.locator.page}` : null,
            ]
              .filter(Boolean)
              .join(", ")}
          </Row>
        )}
        {input.locator && (input.locator.sheet || input.locator.cells) && (
          <Row label="Location">
            {[
              input.locator.sheet ? `sheet ${input.locator.sheet}` : null,
              input.locator.cells ? `cells ${input.locator.cells}` : null,
            ]
              .filter(Boolean)
              .join(", ")}
          </Row>
        )}
        {input.formula && <Row label="Derived as">{input.formula}</Row>}
        {(input.inputFactIds?.length ?? 0) > 0 && (
          <Row label="Inputs">
            <span className="flex flex-wrap gap-1.5">
              {input.inputFactIds!.map((fid) => (
                <a
                  key={fid}
                  href={`/fact/${fid.slice(0, 8)}`}
                  className="t-id rounded bg-muted px-1.5 py-0.5 underline underline-offset-2"
                >
                  #{fid.slice(0, 8)}
                </a>
              ))}
            </span>
          </Row>
        )}
        {citation.sha256 && (
          <Row label="SHA-256">
            <span className="t-id break-all">
              {citation.sha256}
            </span>{" "}
            <CopyButton text={citation.sha256} label="Copy SHA-256" />
          </Row>
        )}
        {input.retrievedAt && <Row label="Retrieved">{input.retrievedAt}</Row>}
        {peBli && (
          <Row label={semantic ? "Appears on" : "Program references"}>
            <a
              href={semantic ? `/program/${peBli}/#fact-${factId}` : `/programs/?q=${encodeURIComponent(peBli)}`}
              className="underline underline-offset-2"
            >
              {semantic ? `${semantic.title ?? peBli} — view this figure in context` : `Browse program references for ${peBli}`}
            </a>
          </Row>
        )}
      </dl>
      </div>
    </article>
  );
}

function Row({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className={styles.metadataRow}>
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}
