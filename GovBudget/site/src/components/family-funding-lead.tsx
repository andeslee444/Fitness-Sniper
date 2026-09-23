import Link from "next/link";
import { Cite } from "@/components/cite";
import { getProgramDetails, getPrograms, type SummaryCard } from "@/lib/data";
import { normalizeExhibitFamily } from "@/lib/basis";
import { isZeroContentDetails } from "@/lib/program-tier";
import { FAMILY_LEAD_COPY, familyLeadKicker, familyLedgerCaption, familyLedgerTail, selectFamilyLead, type FamilyLeadMember, type FamilyLead } from "@/lib/family-lead";
import styles from "./family-funding-lead.module.css";

/** Server-only assembly: eligibility stays in the shared family rule. */
export function loadFamilyLead(slugs: readonly string[], shortName: string): FamilyLead {
  const programs = getPrograms();
  const members: FamilyLeadMember[] = slugs.map(slug => {
    const program = programs.find(row => row.slug === slug);
    if (!program) throw new Error(`Missing family member ${slug}`);
    const details = getProgramDetails(slug);
    const exhibitFamily = normalizeExhibitFamily(program.exhibit_family);
    if (exhibitFamily !== "rdte" && exhibitFamily !== "procurement") throw new Error(`No single exhibit family for ${slug}`);
    return {
      slug, title: program.title, identifierKind: exhibitFamily === "procurement" ? "BLI" : "PE", exhibitFamily,
      tier: details.tier ?? "full", zeroContent: isZeroContentDetails(details), summary: details.summary,
      fy26Split: details.fy26_split ?? null, absenceNotes: [],
    };
  });
  return selectFamilyLead(members, shortName);
}

function Figure({ card, slug, exhibitFamily, reconciled }: {
  card: SummaryCard; slug: string; exhibitFamily: "rdte" | "procurement"; reconciled: boolean;
}) {
  return <Cite value={card.value!} units={card.units!} factId={card.fid} dataset={card.dataset!}
    basis={card.basis!} fy={card.fy} measure={card.measure} edition={card.edition} entity={slug}
    exhibitFamily={exhibitFamily} reconciled={reconciled} />;
}

/** This fixed comparison never changes with the aircraft or funding-sheet selection. */
export function FamilyFundingLead({ lead, shortName, recordSlugs }: { lead: FamilyLead; shortName: string; recordSlugs: readonly string[] }) {
  const roster = { "data-family-records": recordSlugs.join(","), "data-family-edition": lead.edition };
  if (lead.kind === "absent") return <section className={styles.overview} data-testid="family-receipt" {...roster} data-lead-absent="" aria-label={`${shortName} funding overview`}>
    <p data-absence="">{lead.text}</p>
  </section>;
  return <div className={styles.overview}>
    <section data-testid="family-receipt" {...roster} data-lead-record={lead.slug} data-lead-fact-id={lead.card.fid} data-lead-excluded={lead.excluded.join(",")} aria-label={`${shortName} funding overview`}>
      <p className={styles.kicker} data-testid="family-receipt-kicker">{familyLeadKicker(lead, shortName)}</p>
      <h2 className={styles.identity}><Link href={`/program/${lead.slug}/`}>{lead.title} · {lead.identifierKind} {lead.slug}</Link></h2>
      <div className={`t-figure t-figure--4 ${styles.figure}`} data-testid="family-receipt-figure">
        <Figure card={lead.card} slug={lead.slug} exhibitFamily={lead.exhibitFamily} reconciled={lead.reconciled} />
      </div>
      <p className={styles.scope}>{FAMILY_LEAD_COPY.scope}</p>
      {lead.reconShare !== null && <p className={styles.scope} data-fy26-recon-chip="">{(lead.reconShare * 100).toFixed(1)}% reconciliation</p>}
      {lead.reconciled && <Link className={styles.note} href={`/program/${lead.slug}/#figures-heading`}>{FAMILY_LEAD_COPY.accounting}</Link>}
    </section>
    <details className={styles.ledger} data-testid="family-ledger" aria-label={`${shortName} other funding records`}>
      <summary>{lead.ledger.length} other funding records · kept separate</summary>
      <p className={styles.caption} data-basis-declared="">{familyLedgerCaption(lead, shortName)}</p>
      <dl>
        {lead.ledger.map(row => <div key={row.slug} className={styles.row} data-ledger-row="" data-entity={row.slug} data-absence={row.card ? undefined : ""}>
          <dt><Link href={`/program/${row.slug}/`}>{row.title} <span className="t-id">{row.identifierKind} {row.slug}</span></Link></dt>
          <dd>{row.card
            ? <span className="t-figure t-figure--1"><Figure card={row.card} slug={row.slug} exhibitFamily={row.exhibitFamily} reconciled={row.reconciled} /></span>
            : <span className={styles.absence} data-fy={lead.edition} data-measure="request" data-absence-reason={row.absenceReason}>{row.absenceText}</span>}
          </dd>
        </div>)}
      </dl>
      {lead.ledgerOverflow > 0 && <p className={styles.scope} data-ledger-tail="">{familyLedgerTail(lead, shortName)}</p>}
    </details>
  </div>;
}
