/**
 * program-tier.ts — pure helpers for the two program-page tiers (Phase 5F §2a).
 *
 *   full   — programs in programs.json with R-2/P-40 J-book detail (~1,741
 *            after the Phase 5G Army/AF/SF archive round; grows as books land).
 *   rollup — sidecars carrying only R-1/P-1 workbook figures + trajectory
 *            (tier:'rollup', service_org, title on the sidecar).
 *   decade — ROADMAP #28: sidecars carrying only the CITED pre-PB2026
 *            decade series (tier:'decade'). No FY2026 workbook row exists
 *            for these elements at all, so budget_lines/details/narratives
 *            are empty and `trajectory` is null. 553 pages.
 *
 * Universal module (no fs, no server-only): data.ts, sitemap.ts, and the
 * program page all consume these; unit tests construct sidecar objects
 * directly. The build/skeleton gates recompute the same predicates
 * independently in scripts/gates/.
 */

import type {
  ProgramDetails,
  ProgramRow,
} from "@/lib/data";

/** Service workbook org code → service name (rollup J-book note wording). */
export function serviceOrgName(code: string): string {
  switch (code) {
    case "A":
      return "Army";
    case "N":
      return "Navy";
    case "F":
      return "Air Force";
    default:
      return code;
  }
}

/**
 * Org codes (in the details.service_org / budget_lines.organization code space)
 * whose FY2026 J-book IS loaded. A rollup page for one of these is NOT
 * "awaiting ingestion" — the book is loaded, this PE simply has no matching
 * R-2/P-40 narrative in it (a procurement-only, summary, classified, or SBIR
 * line, or an R-1-only workbook remainder).
 *
 * DATA-DERIVED, NOT HARDCODED: the exporter emits the live set into
 * site_meta.ingested_service_orgs — the FY2026 jbook_documents orgs that have
 * at least one non-superseded budget_line_details row LOADED behind a
 * downloaded document, each translated through workbook_org() into this same
 * code space (so CYBERCOM→CYBER, CHIPS/DPAP→OSD line up with service_org).
 * That is 24 codes (measured 2026-09-12): the three services PLUS every
 * defense-wide agency book with loaded detail (OSD, DCSA, MDA, DISA, DARPA,
 * …). data.ts injects it at build time via setIngestedServiceOrgs. A
 * hardcoded A/N/F set previously lied on every defense-wide agency rollup
 * page ("the {org} J-book is not yet ingested"); deriving the set from a
 * DOWNLOADED file rather than loaded detail would have replaced that with the
 * mirror-image lie ("the book is ingested, this element simply has no
 * narrative") the moment a book was acquired — ROADMAP #14, and the reason
 * export_site._ingested_service_orgs joins budget_line_details.
 *
 * This module is universal (no fs / no server-only), so it cannot read the
 * payload itself; the build-time server layer (data.ts getSiteMeta) sets it.
 * The default is the three services so any consumer that never injects (unit
 * tests, a stray import) still behaves sensibly rather than seeing an empty
 * set. Single source of truth for the rollup note wording.
 */
const DEFAULT_INGESTED_SERVICE_ORGS: readonly string[] = ["A", "N", "F"];

let _ingestedServiceOrgs: ReadonlySet<string> = new Set(
  DEFAULT_INGESTED_SERVICE_ORGS,
);

/**
 * Inject the data-derived ingested-org set (from
 * site_meta.ingested_service_orgs). Called once at build time by data.ts.
 * Empty/absent input falls back to the A/N/F default rather than blanking the
 * set — a missing payload key must never silently make every service page lie.
 */
export function setIngestedServiceOrgs(orgs: readonly string[] | undefined): void {
  _ingestedServiceOrgs = new Set(
    orgs && orgs.length > 0 ? orgs : DEFAULT_INGESTED_SERVICE_ORGS,
  );
}

export function isIngestedServiceOrg(code: string): boolean {
  return _ingestedServiceOrgs.has(code);
}

/**
 * ROADMAP #14 / #111 — WHY an org has no loaded FY2026 J-book detail.
 *
 * isIngestedServiceOrg answers "is this org's book loaded"; this answers the
 * question the READER has when it is not. Until Task 17c there was one answer
 * for every unloaded org — "…J-book, which is not yet ingested" — and that
 * sentence presupposes a book exists and is merely awaiting work. Measured
 * 2026-09-12 it was FALSE on five pages (the DoD IG published no RDT&E or
 * procurement justification book at all; DEFW publishes none for its
 * reconciliation / undistributed / roll-up workbook rows) and imprecise on
 * fourteen more (the Defense Health Program book was downloaded and carries
 * no jb-2009 payload to extract, which is not the same as "not yet").
 *
 * The three rules are the vocabulary of the edition probe that records the
 * absences (jbooks.edition_probe.ORG_ABSENCE_RULES →
 * export_site._org_absences → site_meta.org_absences). Each selects ONE
 * sentence, below; no org, count or dollar figure is typed anywhere.
 */
export type OrgAbsenceRule =
  | "no-justification-book-published"
  | "summary-line-only"
  | "book-carries-no-embedded-xml";

export interface OrgAbsence {
  rule: OrgAbsenceRule;
  /** The edition the absence was recorded for (export_site._org_absences,
   *  from config.JBOOK_FY). Every sentence below names it — "No FY2026 …" —
   *  and it comes from the payload precisely so that no year is typed into
   *  this module, where nothing would re-derive it at rollover. */
  fy: number;
  /** ISO date the probe read the source. Rendered: an absence is an
   *  observation, and an observation carries its date. */
  checked_on: string;
  /** What the probe read. Shipped so the claim is traceable in the payload;
   *  not rendered (the note links to /methodology/, as it always has). */
  checked_url: string;
}

const ORG_ABSENCE_RULES: readonly OrgAbsenceRule[] = [
  "no-justification-book-published",
  "summary-line-only",
  "book-carries-no-embedded-xml",
];

let _orgAbsences: ReadonlyMap<string, OrgAbsence> = new Map();

/**
 * Inject site_meta.org_absences ({org: {rule, checked_on, checked_url}}).
 * Called once at build time by data.ts, beside setIngestedServiceOrgs.
 *
 * The default is EMPTY, unlike the ingested set's A/N/F fallback, and the
 * asymmetry is deliberate: inventing an absence would be inventing a reason
 * to print, while an empty map just leaves the org on the generic
 * "not yet ingested" wording — the pre-17c behaviour, which is honest for an
 * org nobody has probed. An entry whose rule this module has no sentence for
 * is DROPPED for the same reason; gate 21 leg (o) then fails on the page,
 * because the payload named an org the page did not explain.
 */
export function setOrgAbsences(
  payload: Record<string, Partial<OrgAbsence>> | undefined,
): void {
  const next = new Map<string, OrgAbsence>();
  for (const [org, raw] of Object.entries(payload ?? {})) {
    const rule = raw?.rule;
    if (!org || !rule || !ORG_ABSENCE_RULES.includes(rule)) continue;
    // A missing `fy` is neither dropped nor thrown on HERE. Dropping would
    // restore the generic "not yet ingested" on the org's pages — the defect
    // this payload ended — and throwing would take down the whole build from
    // one call data.ts makes once, including the ~2,500 pages that render no
    // absence at all. The year is needed only where a sentence is built, so
    // orgAbsenceWording refuses there: an export older than the field fails
    // exactly the pages that would print a yearless "FY", and gate 21 leg (o)
    // names the payload itself.
    next.set(org, {
      rule,
      // THE CAST IS A DEBT, AND ORG ABSENCE WORDING IS WHERE IT IS PAID.
      // `OrgAbsence.fy` is declared `number` because every consumer wants a
      // year; a payload written before the field carries none, so this entry
      // can hold `undefined` behind a `number`. That is tolerable only while
      // orgAbsenceWording is the ONLY reader of `.fy` (grep: it is — the
      // throw at the top of it is the check), so a new reader either goes
      // through the wording or repeats the Number.isInteger refusal. Widening
      // the field instead would hand every call site an `| undefined` that
      // `Number.isInteger` cannot narrow, which buys a cast at each of them.
      fy: raw.fy as number,
      checked_on: raw.checked_on ?? "",
      checked_url: raw.checked_url ?? "",
    });
  }
  _orgAbsences = next;
}

/** The recorded absence for an org code, or null when none is recorded. */
export function getOrgAbsence(code: string): OrgAbsence | null {
  return _orgAbsences.get(code) ?? null;
}

/** The four surfaces a program page states the absence on. */
export interface OrgAbsenceWording {
  /** Description-section note, minus the " See roadmap." the note appends. */
  description: string;
  /** Justification-section empty state, whole sentence. */
  justification: string;
  /** WHAT-IT-IS card tail (rollup tier), whole sentence. */
  cardTail: string;
  /** <meta name="description"> clause (rollup tier), trailing space included. */
  metaTail: string;
}

/**
 * One rule, one set of sentences. Every clause restates the rule the probe
 * recorded and nothing else: no dollar figure, no page count, no claim about
 * the tier, and nothing about WHEN a book might land.
 *
 * The four surfaces exist because all four used to say "not yet ingested"
 * about these orgs — the description note, the justification empty state, the
 * WHAT-IT-IS card tail and the page's own <meta name="description">. Fixing
 * three of four would have left the sentence on the page.
 *
 * The shared opening clause is load-bearing: gate 21 leg (o) looks for it in
 * the description note AND inside the justification section, which is how one
 * marker per rule binds both render sites. Keep the two sentences' openings
 * identical, and keep "&" out of that opening (the gate reads decoded text).
 */
export function orgAbsenceWording(
  absence: OrgAbsence,
  orgCode: string,
): OrgAbsenceWording {
  const service = serviceOrgName(orgCode) || "service";
  const checked = absence.checked_on;
  // The edition comes from the payload (export_site._org_absences, from
  // config.JBOOK_FY). It was typed here as "FY2026" until the Group C polish
  // added the field: a literal that would have gone on naming 2026 the day
  // the FY2027 books landed, with nothing to notice.
  //
  // Without it, REFUSE. "No FY RDT&E or procurement justification book was
  // published for IG" is a claim about a budget year with the year missing,
  // and it would ship on four surfaces of every page the org owns. A build
  // reading an export older than the field dies here, on those pages only.
  if (!Number.isInteger(absence.fy)) {
    throw new Error(
      `[govbudget/program-tier] the recorded absence for "${orgCode}" carries` +
        ` no integer fy (got ${JSON.stringify(absence.fy)}), and every` +
        ` sentence below names the edition. Re-run "uv run python -m govbudget` +
        ` export-site": site_meta.org_absences predates this field, which was` +
        ` added after Task 17c (Group C polish, 2026-09-18) — a #111-era` +
        ` export is exactly the one that does not write it.`,
    );
  }
  const fy = `FY${absence.fy}`;
  switch (absence.rule) {
    case "summary-line-only":
      return {
        description:
          `No ${service}-specific ${fy} justification book is published` +
          (checked ? ` (justification index checked ${checked})` : "") +
          ` — its workbook rows are reconciliation, undistributed or roll-up` +
          ` summary lines — so this corpus carries no detailed justification` +
          ` for this program.`,
        justification:
          `No ${service}-specific ${fy} justification book is published, so` +
          ` there are no accomplishments or planned-program narratives to show` +
          ` — see the description note above.`,
        cardTail:
          `Summary figures only: no ${service}-specific ${fy} justification` +
          ` book is published.`,
        metaTail:
          `Workbook-tier line: no ${service}-specific ${fy} justification book` +
          ` is published. `,
      };
    case "book-carries-no-embedded-xml":
      return {
        description:
          `The ${service} ${fy} justification book was downloaded, but its PDF` +
          ` carries no embedded data payload` +
          (checked ? ` (checked ${checked})` : "") +
          `, so no R-2/P-40 detail could be extracted from it.`,
        justification:
          `The ${service} ${fy} justification book was downloaded, but its PDF` +
          ` carries no embedded data payload, so no accomplishments or` +
          ` planned-program narratives could be extracted from it — see the` +
          ` description note above.`,
        cardTail:
          `Summary figures only: the ${service} ${fy} justification book was` +
          ` downloaded and carries no embedded data payload.`,
        metaTail:
          `Workbook-tier line: the ${service} ${fy} justification book was` +
          ` downloaded and carries no embedded data payload. `,
      };
    case "no-justification-book-published":
      return {
        description:
          `No ${fy} RDT&E or procurement justification book was published for` +
          ` ${service}` +
          (checked ? ` (justification index checked ${checked})` : "") +
          `, so this corpus carries no detailed justification for this program.`,
        justification:
          `No ${fy} RDT&E or procurement justification book was published for` +
          ` ${service}, so there are no accomplishments or planned-program` +
          ` narratives to show — see the description note above.`,
        cardTail:
          `Summary figures only: no ${fy} RDT&E or procurement justification` +
          ` book was published for ${service}.`,
        metaTail:
          `Workbook-tier line: no ${fy} RDT&E or procurement justification book` +
          ` was published for ${service}. `,
      };
  }
  // A FOURTH rule is a COMPILE error here, not a silent fall-through onto the
  // "no book published" sentences — which is what the old `default:` did, and
  // it would have stated the wrong case about the new org with full
  // confidence. The throw is unreachable from a validated payload
  // (setOrgAbsences drops a rule this module has no sentence for).
  const unwritten: never = absence.rule;
  throw new Error(
    `[govbudget/program-tier] orgAbsenceWording has no sentence for rule ` +
      `${String(unwritten)}`,
  );
}

/** True when the sidecar is a Batch-A rollup-tier export. */
export function isRollupDetails(details: ProgramDetails): boolean {
  return details.tier === "rollup";
}

/**
 * True when the sidecar is a ROADMAP #28 decade-tier export: cited
 * President's Budget history from editions BEFORE PB2026, and no PB2026
 * R-1/P-1 line at all.
 *
 * Distinct from the rollup tier in the one way that matters to every
 * sentence such a page renders: a rollup page HAS FY2026 workbook figures
 * and lacks the R-2/P-40 narrative behind them; a decade page has no FY2026
 * record of any kind. The two tiers' empty states, WHAT-IT-IS card and
 * coverage notes therefore say different things, and conflating them would
 * put the rollup tier's "the {service} FY2026 J-book is ingested, but this
 * element carries no R-2/P-40 narrative" onto a page whose element is not in
 * the FY2026 books at all.
 */
export function isDecadeDetails(details: ProgramDetails): boolean {
  return details.tier === "decade";
}

/**
 * True when a page carries FY2026 R-1/P-1 workbook figures and NO R-2/P-40
 * J-book detail of any kind — the `workbookOnly` bucket of data.ts
 * getPagesWithoutDetail (73 pages in the shipped corpus, measured
 * 2026-09-10: 71 rollup sidecars plus 2 that carry no `tier` key at all).
 *
 * TIER IS NOT THE TEST, which is the whole point (ROADMAP #14).
 * export_site._trajectory_only_feed_programs synthesizes a programs.json row
 * for every feed PE that has a trajectory but no dim_programs row, so those
 * pages resolve as tier "full" — and the full-tier empty states assert a
 * J-book detail behind the page ("The J-book detail for this line carries no
 * separate mission or description narrative", "…in this line's J-book
 * detail"). For 0603115DHA (Medical Development, org DHA) and 0708083D
 * (Assembled Chemical Weapons Alternatives, org A) there is no such detail:
 * budget_line_details holds zero rows for both, no DHA J-book was in the
 * corpus at all, and the Army chem-demil book that would carry 0708083D's
 * R-2 is excluded from it by name. Those two pages shipped the 2026-07-05
 * "ingested-orgs liar" species on a tier the 2026-07-05 fix never touched.
 *
 * `narratives` is checked as well as `details` because the sentences this
 * predicate selects are claims about narrative absence too. Measured
 * 2026-09-10 the two definitions agree exactly: 0 sidecars carry narratives
 * with no detail rows, and the 1 that carries detail rows with no narratives
 * (0607212A) keeps the full-tier sentence, which is true for it.
 *
 * `budget_lines.length > 0` keeps the decade tier out: a decade sidecar
 * ships budget_lines: [] by construction, and its element is not in the
 * FY2026 books at all — a different absence, with its own wording.
 */
export function isWorkbookOnlyDetails(details: ProgramDetails): boolean {
  return (
    details.details.length === 0 &&
    details.narratives.length === 0 &&
    details.budget_lines.length > 0
  );
}

/**
 * Exhibit family for a rollup page, derived from its workbook lines:
 * R-1 → rdte, P-1/P-1R → procurement; mixed → the family with more lines;
 * no lines → the honest generic "budget".
 */
export function deriveExhibitFamily(
  budgetLines: readonly { exhibit: string }[],
): string {
  let rdte = 0;
  let procurement = 0;
  for (const bl of budgetLines) {
    if (bl.exhibit === "R-1") rdte++;
    else if (bl.exhibit === "P-1" || bl.exhibit === "P-1R") procurement++;
  }
  if (rdte === 0 && procurement === 0) return "budget";
  return rdte >= procurement ? "rdte" : "procurement";
}

/**
 * Synthesize a ProgramRow-shaped record for a rollup-tier page so the shared
 * header / answer-strip / figures components render one honest shape.
 * Everything the rollup export doesn't carry is null/zero — never invented.
 */
export function rollupProgramRow(
  peBli: string,
  details: ProgramDetails,
): ProgramRow {
  return {
    pe_bli: peBli,
    title: details.title ?? peBli,
    // ProgramRow.org is an org CODE ("F"), the code space shared by
    // programs.json, agencies.json and gao_overlays.agency_code_by_org.
    // It is NOT the display name: every consumer that SHOWS it humanizes at
    // the point of display (serviceOrgName, which passes agency acronyms and
    // "DoD" through unchanged), and the consumers that LOOK IT UP need the
    // code. This field used to be humanized here, which is why 226 rollup
    // pages resolved no GAO department overlay (getGaoOverlayForOrg keys by
    // code) and rendered their own organization as dead plain text instead of
    // a link to the /agency/{code}/ page that does exist — while their header
    // tooltip claimed "Organization code Air Force". ROADMAP #30 patched that
    // silence; this is the cause.
    //
    // Empty service_org (1 sidecar) still falls back to the honest umbrella
    // "DoD" — the figures come from the DoD-wide R-1/P-1 workbooks. "DoD" is
    // deliberately not a service code: it has no agency page and no overlay,
    // which is the correct outcome for a line with no declared service.
    org: details.service_org || "DoD",
    exhibit_family: deriveExhibitFamily(details.budget_lines),
    fully_reconciled: false,
    // Rollup tier renders the "Summary figures (R-1/P-1)" badge, never a
    // reconciliation verdict — there is no R-2/P-40 detail behind this row
    // to reconcile, so null (nothing checked), not false (a failure).
    reconciled_in_scope: null,
    fy2024_actual_millions: null,
    fy2024_fact_id: null,
    fy2024_xml_path: null,
    hhi: null,
    award_count: details.awards.length,
    narrative_count: details.narratives.length,
    project_count: 0,
    trajectory: details.trajectory ?? null,
    trajectory_fact_ids: details.trajectory_fact_ids ?? null,
    // Sprint E, Task E3: a rollup-tier program is never one of the 13 shared
    // pe_bli codes (those all have a dim_programs row,
    // i.e. full tier) — slug is always its own bare pe_bli.
    slug: peBli,
    account: null,
    account_title: null,
  };
}

/**
 * ProgramRow for a ROADMAP #28 decade-tier page. Same synthesis as the
 * rollup tier — a decade sidecar carries the same title / service_org /
 * (null) trajectory fields, and for the same reason: there is no
 * programs.json row to read them from — with two departures.
 */
export function decadeProgramRow(
  peBli: string,
  details: ProgramDetails,
): ProgramRow {
  return {
    ...rollupProgramRow(peBli, details),
    // exhibit_family: deriveExhibitFamily reads budget_lines, which is empty
    // by construction on this tier (the PB2026 workbook has no row for this
    // element), so it would return the generic "budget" for all 553 of these
    // pages. The exporter derives it from the page's OWN older-edition
    // workbook rows and ships it; the fallback keeps a pre-#28 sidecar
    // rendering rather than throwing.
    exhibit_family:
      details.exhibit_family ?? deriveExhibitFamily(details.budget_lines),
    // award_count: zero for every decade page in the shipped corpus
    // (fct_budget_to_awards carries no row for any of them — verified, not
    // assumed). Spelled out rather than inherited so a future crosswalk that
    // DOES reach these lines flows through instead of being pinned to 0.
    award_count: details.awards.length,
  };
}

/**
 * noindex policy (Phase 5F §2a): a page whose ONLY content is zero-valued
 * figure line(s) — no details, narratives, awards, or mentions, and every
 * workbook, trajectory and decade value is 0 (or absent) — is built but
 * noindexed and excluded from the sitemap (same policy as zero-mention
 * filings). Pages with any non-zero figure or any prose stay indexable.
 *
 * ROADMAP #28 widened the figure set to `decade_series`. It HAD to: a
 * decade-tier page carries no budget_lines, no trajectory and no prose, so
 * on the pre-#28 predicate `figures` was the empty array, `[].every()` is
 * true, and all 553 pages would have been built, noindexed and dropped from
 * sitemap.xml — the corpus's whole pre-PB2026 history published to nobody.
 * The decade points are cited workbook grains: they are the most
 * index-worthy thing on those pages, not an absence of content.
 *
 * The pages this predicate is FOR still fail it: a sidecar with an
 * all-zero decade series (8 keys in the shipped warehouse, which #28's own
 * eligibility filter already declines to build) counts its zeros here like
 * any other zero figure.
 */
export function isZeroContentDetails(details: ProgramDetails): boolean {
  if (
    details.details.length > 0 ||
    details.narratives.length > 0 ||
    details.awards.length > 0 ||
    details.mentions.length > 0
  ) {
    return false;
  }
  const figures: number[] = details.budget_lines.map((bl) => bl.amount_thousands);
  const t = details.trajectory;
  if (t) {
    for (const v of [t.fy2024_actuals, t.fy2025_total, t.fy2026_total]) {
      if (v !== null && v !== undefined) figures.push(v);
    }
  }
  for (const points of Object.values(details.decade_series ?? {})) {
    for (const p of points ?? []) {
      if (p.v !== null && p.v !== undefined) figures.push(p.v);
    }
  }
  return figures.every((v) => v === 0);
}
