/**
 * family-lead.ts — which figure leads a family page, as a rule.
 *
 * Nine design critics scored the F-15 page "chrome around one paragraph —
 * no dollar figure above the fold." The owner's constraint on the fix: it
 * must be a rule every family page inherits, never an F-15 hand-pick. This
 * module IS that rule. It is pure (no React, no server-only, no I/O) so the
 * page, the tests and the gate all compute the same answer from the same
 * exporter cards.
 *
 * THE RULE (there is no per-family override slot):
 *   1. Edition E = max(summary.edition) over the family's members.
 *   2. A member is ELIGIBLE iff it is full tier, not zero-content, and its
 *      `fy{E}` card is a state-A TOA request in USD thousands with a fid and
 *      a value, at edition E. State-B zero roots (fid null + xml_path),
 *      jbook-detail cards, absence cards and rollup/decade sidecars are not.
 *      No other key is ever consulted: there is NO fallback to fy2025 or
 *      fy2024, because at FY2025 the members carry different measures
 *      ("enacted" vs "total") and ranking those against each other would
 *      be a comparison across measures.
 *   3. The LEAD is the eligible member with the largest value — one basis,
 *      one unit, one measure: a comparison, never a sum. Ties: (a) the
 *      member with no reconciliation entry at (E, "request"); (b) code-point
 *      slug order.
 *   4. No eligible member → the family absence sentence. Never zero, never a
 *      substitute figure, never hhi/program_dollars, never a family sum
 *      (getFamilyFundingSummary mints no fid and stays test-only).
 *   5. Disclosures are inherited, never re-adjudicated: `reconciled` from
 *      summary.reconciliation; `reconShare` from fy26_split.
 *   6. The LEDGER is every other member: eligible rows by value desc then
 *      slug, then ineligible rows in declaration order with an absence
 *      sentence. Absence rows are ALWAYS rendered — they are the honesty
 *      guard. Cited rows beyond LEDGER_MAX_CITED_ROWS become a counted tail,
 *      never a silent drop.
 *
 * Every number the family page shows through this module is one exporter
 * SummaryCard, rendered by the program page's own card renderer. The family
 * mints no fid.
 */

import type { Fy26Split, ProgramSummary, SummaryCard } from "@/lib/data";
import { measureLabel, fyShort, pbLabel, absenceNote } from "@/lib/copy";

export type FamilyExhibit = "rdte" | "procurement";

/** One declared member of a family. Built by the family loader from the sidecar + programs.json row. */
export interface FamilyLeadMember {
  slug: string;
  title: string;
  identifierKind: "PE" | "BLI";
  exhibitFamily: FamilyExhibit;
  tier: "full" | "rollup" | "decade";
  zeroContent: boolean;
  summary: ProgramSummary;
  fy26Split: Fy26Split | null;
  absenceNotes: { fy: number; text: string }[];
}

export interface FamilyLedgerRow {
  slug: string;
  title: string;
  identifierKind: "PE" | "BLI";
  exhibitFamily: FamilyExhibit;
  /** The record's OWN eligible fy{E} card, or null. */
  card: SummaryCard | null;
  reconciled: boolean;
  /** Non-null iff card is null. */
  absenceText: string | null;
  absenceReason: string | null;
}

export type FamilyLead =
  | {
      kind: "lead";
      edition: number;
      key: `fy${number}`;
      slug: string;
      title: string;
      identifierKind: "PE" | "BLI";
      exhibitFamily: FamilyExhibit;
      /** State A by construction. */
      card: SummaryCard;
      reconciled: boolean;
      reconShare: number | null;
      ledger: FamilyLedgerRow[];
      ledgerOverflow: number;
      /** Members with no eligible fy{E} card, in declaration order. */
      excluded: string[];
      recordCount: number;
    }
  | { kind: "absent"; edition: number; recordCount: number; text: string };

export const LEDGER_MAX_CITED_ROWS = 5;
export const FAMILY_LEAD_COPY = {
  scope: "This line’s request. Other records are separate, not added or allocated by aircraft variant.",
  accounting: "TOA workbook and J-book accounting notes →",
};

/** The program page's own absence vocabulary (program-figures ABSENCE_LABEL) — one copy, kept identical. */
const ABSENCE_LABEL: Record<string, string> = {
  "not-published": "Not in the FY2026 J-books we ingested",
  "no-rollup": "No single program-level figure; see the line items below",
  "no-comparison": "No comparison: endpoints unavailable or on different bases",
};
const NO_TOA_FIGURE = "No cited TOA workbook figure in this collection.";

function eligibleCard(m: FamilyLeadMember, edition: number): SummaryCard | null {
  if (m.tier !== "full" || m.zeroContent) return null;
  const c = m.summary.cards.find((x) => x.key === `fy${edition}`);
  if (!c) return null;
  const ok =
    c.fy === edition &&
    c.edition === edition &&
    c.measure === "request" &&
    c.basis === "toa" &&
    c.units === "USD thousands" &&
    c.fid != null &&
    c.value != null;
  return ok ? c : null;
}

function isReconciled(m: FamilyLeadMember, edition: number): boolean {
  return (m.summary.reconciliation ?? []).some((r) => r.fy === edition && r.measure === "request");
}

/** The ledger's absence sentence for an ineligible member, in the spec's order. */
export function ledgerAbsenceText(member: FamilyLeadMember, edition: number): string {
  const note = member.absenceNotes.find((n) => n.fy === edition)?.text;
  if (note) return note;
  const c = member.summary.cards.find((x) => x.key === `fy${edition}`);
  if (!c) return NO_TOA_FIGURE;
  if (c.absence_reason) return ABSENCE_LABEL[c.absence_reason] ?? NO_TOA_FIGURE;
  // A state-B root: the exporter found a J-book detail figure but no TOA
  // workbook row. Say which document carries what, in the one absence grammar.
  if (c.basis === "jbook-detail" || (c.fid == null && c.xml_path)) {
    return absenceNote({ basis: "TOA workbook", fy: edition, otherPlace: "The program dossier", otherBasis: "J-book detail" });
  }
  return NO_TOA_FIGURE;
}

export function familyLeadAbsence(edition: number, recordCount: number, shortName: string): string {
  return `No cited P-1/R-1 workbook figure for any of the ${recordCount} ${shortName} budget records in the ${pbLabel(edition)} workbooks. Missing coverage is not zero spending.`;
}

export function selectFamilyLead(members: FamilyLeadMember[], shortName: string): FamilyLead {
  const edition = Math.max(...members.map((m) => m.summary.edition));
  const key = `fy${edition}` as const;
  const eligible = members
    .map((m) => ({ m, card: eligibleCard(m, edition) }))
    .filter((x): x is { m: FamilyLeadMember; card: SummaryCard } => x.card !== null);
  const excluded = members.filter((m) => eligibleCard(m, edition) === null).map((m) => m.slug);

  if (eligible.length === 0) {
    return { kind: "absent", edition, recordCount: members.length, text: familyLeadAbsence(edition, members.length, shortName) };
  }

  const ranked = [...eligible].sort((a, b) => {
    const dv = (b.card.value as number) - (a.card.value as number);
    if (dv !== 0) return dv;
    const ra = isReconciled(a.m, edition) ? 1 : 0;
    const rb = isReconciled(b.m, edition) ? 1 : 0;
    if (ra !== rb) return ra - rb; // the un-reconciled member first
    return a.m.slug < b.m.slug ? -1 : a.m.slug > b.m.slug ? 1 : 0;
  });
  const lead = ranked[0];

  const citedRows: FamilyLedgerRow[] = ranked.slice(1).map(({ m, card }) => ({
    slug: m.slug,
    title: m.title,
    identifierKind: m.identifierKind,
    exhibitFamily: m.exhibitFamily,
    card,
    reconciled: isReconciled(m, edition),
    absenceText: null,
    absenceReason: null,
  }));
  const absenceRows: FamilyLedgerRow[] = members
    .filter((m) => excluded.includes(m.slug))
    .map((m) => {
      const c = m.summary.cards.find((x) => x.key === key);
      return {
        slug: m.slug,
        title: m.title,
        identifierKind: m.identifierKind,
        exhibitFamily: m.exhibitFamily,
        card: null,
        reconciled: false,
        absenceText: ledgerAbsenceText(m, edition),
        absenceReason: c?.absence_reason ?? (c?.basis === "jbook-detail" || (c && c.fid == null && c.xml_path) ? "jbook-detail" : "not-published"),
      };
    });
  const ledgerOverflow = Math.max(0, citedRows.length - LEDGER_MAX_CITED_ROWS);

  return {
    kind: "lead",
    edition,
    key,
    slug: lead.m.slug,
    title: lead.m.title,
    identifierKind: lead.m.identifierKind,
    exhibitFamily: lead.m.exhibitFamily,
    card: lead.card,
    reconciled: isReconciled(lead.m, edition),
    reconShare: lead.m.fy26Split?.has_reconciliation ? lead.m.fy26Split.recon_share : null,
    ledger: [...citedRows.slice(0, LEDGER_MAX_CITED_ROWS), ...absenceRows],
    ledgerOverflow,
    excluded,
    recordCount: members.length,
  };
}

type LeadCase = Extract<FamilyLead, { kind: "lead" }>;

/** "FY26 Request" — the card's measure label, the way the program page's tiles say it. */
export function leadCardLabel(lead: LeadCase): string {
  return `${fyShort(lead.card.fy)} ${measureLabel(lead.card.measure)}`;
}

/** `Largest cited FY26 Request of 6 F-15 records · 1 without a cited FY26 Request` */
export function familyLeadKicker(lead: LeadCase, shortName: string): string {
  const label = leadCardLabel(lead);
  const clause = lead.excluded.length ? ` · ${lead.excluded.length} without a cited ${label}` : "";
  return `Largest cited ${label} of ${lead.recordCount} ${shortName} records${clause}`;
}

/** `FY26 Request · P-1/R-1 TOA · PB2026 · 5 other F-15 records, not added` */
export function familyLedgerCaption(lead: LeadCase, shortName: string): string {
  return `${leadCardLabel(lead)} · P-1/R-1 TOA · ${pbLabel(lead.edition)} · ${lead.recordCount - 1} other ${shortName} records, not added`;
}

/** `3 more cited F-15 records under Budget & receipts` */
export function familyLedgerTail(lead: LeadCase, shortName: string): string {
  return `${lead.ledgerOverflow} more cited ${shortName} records under Budget & receipts`;
}
