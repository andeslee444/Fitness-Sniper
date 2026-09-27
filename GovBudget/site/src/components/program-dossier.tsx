import React from "react";
import type { SnapshotMeta } from "@/lib/dossier";
import {
  DOSSIER_ALL_SECTIONS,
  DOSSIER_SECTION_TITLES,
  isFactCitation,
  type DossierFile,
} from "@/lib/dossier";
import type { PeLinkIndex } from "@/lib/data";
import { DossierFactChip, DossierUrlChip } from "@/components/dossier-chips";
import { CoverageNote } from "@/components/coverage-note";
import { ScopeNote } from "@/components/notes";
import { PeText } from "@/components/pe-text";

/**
 * ProgramDossier (Task 8a) — renders a GATED dossier's four sections:
 * "What it is / Why it matters / Key players / Recent developments".
 *
 * Cited-or-absent contract: this component only ever receives a dossier that
 * passed getDossier()'s re-verification (structure + every citation
 * resolvable). Each claim renders its text followed by its citation chip —
 * fact chips open the citation panel via the existing context, url chips link
 * the live source with the snapshot title tooltip + retrieved note.
 *
 * Empty sections (recent_developments for most programs) render NOTHING —
 * zero placeholder text. Pages without a dossier never mount this component.
 */

/**
 * The Correction note's wording: one clause per drop reason, [when that
 * reason's count is 1, otherwise], each after a subject — "it"/"they" when
 * the reason covers every dropped claim, else "one" or the count.
 *
 * MIRROR: src/govbudget/dossiers/gate.py CORRECTION_CLAUSES and
 * CORRECTION_OTHER_CLAUSE. The dossier gate rebuilds this sentence from the
 * sidecar's dropped_reasons and compares it, word for word, with the built
 * page before an emptied required section may pass (R-DEC-DOSSIERDRIFT
 * round 2); tests/test_dossiers_batch.py::TestCorrectionNoteMirror reads this
 * table, so a wording change here fails pytest until the gate matches.
 */
const CORRECTION_CLAUSES = {
  // #52: the citation does not resolve at all — a fact_id not in
  // citations.json, a url with no cached snapshot, or a malformed citation.
  // Worded for that check, not for one kind of source (R-DEC-DOSSIERDRIFT
  // round 3): it used to read "cited lobbying mentions that did not meet the
  // evidence standard", false wherever the dropped claim was a J-book
  // narrative or concentration claim (/program/1000/, ATA000, B02100,
  // 0603467E).
  unresolvable_citation: [
    "cited a source the site could not resolve",
    "cited sources the site could not resolve",
  ],
  // #56: the citation resolves, but a later correction changed its value.
  stale_value: [
    "stated a figure a later correction changed",
    "stated figures a later correction changed",
  ],
  // R-DEC-DOSSIERDRIFT (2026-09-26): withheld at export, never rewritten —
  // a stated figure, concentration band or top recipient family its cited
  // fact's current value does not support, an agreeing figure given another
  // fiscal year than its cited column's, a named recipient the page's
  // linked awards do not carry, or a named lobbying filer the page's
  // lobbying mentions do not list. "Do not support", not "no longer match":
  // some of these never matched (a figure cited to the wrong cell). "Year"
  // since round 4: a fiscal-year withhold (/program/1203154SF/) states a
  // figure its cite does support, so the clause must name the year.
  // "Lobbying filer" since R-DEC-DOSSIERLDA (2026-09-27): a claim naming an
  // LDA client or registrant the page's lobbying mentions do not list is
  // withheld too (/program/2004/ and /program/1045/: FedEx after the #176
  // rematch), and FedEx is no recipient of either page's awards.
  contradicts_citation: [
    "stated a figure, year, recipient or lobbying filer its sources do not support",
    "stated figures, years, recipients or lobbying filers their sources do not support",
  ],
} as const;
/** Removals no reason above accounts for (a reason this component predates). */
const OTHER_CLAUSE = "did not meet the evidence standard";
type DroppedReason = keyof typeof CORRECTION_CLAUSES;

interface ProgramDossierProps {
  dossier: DossierFile;
  /** url → snapshot metadata (from getSnapshotMeta()) for url-citation chips. */
  snapshotMeta: Record<string, SnapshotMeta>;
  /** PE page resolver for claim-text mention linking (Phase 5F §2a). */
  peIndex?: PeLinkIndex;
}

export function ProgramDossier({
  dossier,
  snapshotMeta,
  peIndex,
}: ProgramDossierProps) {
  const sections = DOSSIER_ALL_SECTIONS.filter(
    (key) => dossier.dossier[key].claims.length > 0,
  );
  // (#52 fallout) dropped_claims > 0 means the export-time filter removed a
  // claim whose citation no longer resolved (see _emit_dossier_sidecars).
  // Keep rendering the section — with the correction note — even in the
  // (currently hypothetical) case where every section emptied out; a
  // dossier that lost all its claims should say so, not silently vanish
  // the way an always-had-nothing dossier correctly does.
  const droppedCount = dossier.dropped_claims ?? 0;
  if (sections.length === 0 && droppedCount === 0) return null;

  // (#56 addendum) The wording depends on WHY claims were dropped — #52's
  // reason (citation no longer resolves) has nothing to do with #56's (the
  // citation still resolves, but its OWN CURRENT value no longer matches
  // what the claim's hardcoded prose says — e.g. a program-key re-key
  // changed which single account a stable fact_id now describes). Both can
  // fire on the same dossier. A sidecar this component predates (no
  // dropped_reasons field at all) states #52's reason — the only one that
  // existed before this field did — for every drop.
  // (R-DEC-DOSSIERDRIFT) The field is read as a plain count map, so a reason
  // lib/dossier.ts does not name is still counted, in its own clause below.
  const reasons: Partial<Record<string, number>> | undefined =
    dossier.dropped_reasons;
  const countFor = (reason: DroppedReason): number =>
    reasons
      ? (reasons[reason] ?? 0)
      : reason === "unresolvable_citation"
        ? droppedCount
        : 0;
  const pronoun = droppedCount === 1 ? "it" : "they";
  const subjectFor = (n: number) =>
    n === droppedCount ? pronoun : n === 1 ? "one" : `${n}`;
  const correctionParts: string[] = [];
  let explainedN = 0;
  for (const reason of Object.keys(CORRECTION_CLAUSES) as DroppedReason[]) {
    const n = countFor(reason);
    if (n > 0) {
      const [one, many] = CORRECTION_CLAUSES[reason];
      correctionParts.push(`${subjectFor(n)} ${n === 1 ? one : many}`);
      explainedN += n;
    }
  }
  // Every removal gets a clause with its own subject. The old fallback read
  // "1 claim removed: did not meet the evidence standard." — no subject —
  // and a reason it had no words for went unexplained.
  const otherN = droppedCount - explainedN;
  if (otherN > 0) {
    correctionParts.push(`${subjectFor(otherN)} ${OTHER_CLAUSE}`);
  }
  const correctionText = correctionParts.join("; ");

  return (
    <section
      className="mt-8 pt-6 border-t border-border"
      id="dossier"
      data-dossier={dossier.pe_bli}
    >
      <h2 className="mb-1">Program dossier</h2>
      <p className="text-sm text-muted-foreground mb-1">
        Every sentence below carries its citation — warehouse figures open the
        citation panel, news claims link the cached source.
      </p>
      {/* Scope note — G2 contract (data-coverage="dossiers") */}
      <CoverageNote id="dossiers" className="mb-4" />
      {/* data-dossier-dropped-claims below is the machine-checkable hook for
          the regression test (a dossier that lost a claim still renders,
          and says so) and for gate 21-style DOM assertions if one is ever
          added. */}
      {droppedCount > 0 && (
        <ScopeNote className="mb-4" label="Correction">
          <p
            className="text-sm leading-relaxed"
            data-dossier-dropped-claims={droppedCount}
          >
            {droppedCount} claim{droppedCount === 1 ? "" : "s"} removed:{" "}
            {correctionText}.
          </p>
        </ScopeNote>
      )}

      <div className="space-y-5">
        {sections.map((key) => (
          <div key={key} data-dossier-section={key}>
            <h3 className="text-base font-semibold mb-2 text-foreground">
              {DOSSIER_SECTION_TITLES[key]}
            </h3>
            {/* data-measure="prose": claims are sentences in a bare, marker-less
                list, so the BOX takes the reading measure (globals.css). Measured
                on /program/000999/ at 1440 before this: 11 claims at 117–193
                characters per line across 1,246px. Gate 3's spine leg cannot
                catch it — it samples the lowest-sorting program instance
                (000042), which carries no dossier — so the declaration is the
                whole fix for the 50 dossier pages. */}
            <ul className="space-y-2" data-measure="prose">
              {dossier.dossier[key].claims.map((claim, i) => (
                <li
                  key={`${key}-${i}`}
                  className="text-sm leading-relaxed text-foreground"
                  // Claim text may quote dollar figures from its cited source.
                  // data-source-text exempts it from the negative currency
                  // scan; the claim's own citation is the required anchor
                  // (data-cite-fact-id / data-cite-url — gate-enforced).
                  data-source-text="dossier-claim"
                  {...(isFactCitation(claim.citation)
                    ? { "data-cite-fact-id": claim.citation.fact_id }
                    : { "data-cite-url": claim.citation.url })}
                >
                  {peIndex ? (
                    // PE mentions in claim text link to their program pages
                    // (§2a); self-references stay plain.
                    <PeText
                      text={claim.text}
                      peSet={peIndex}
                      selfPe={dossier.pe_bli}
                      projectsByPe={(pe) => peIndex.projects(pe)}
                    />
                  ) : (
                    claim.text
                  )}
                  {isFactCitation(claim.citation) ? (
                    <DossierFactChip factId={claim.citation.fact_id} />
                  ) : (
                    <DossierUrlChip
                      url={claim.citation.url}
                      meta={snapshotMeta[claim.citation.url] ?? null}
                    />
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}
