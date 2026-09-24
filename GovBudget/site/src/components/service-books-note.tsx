/**
 * <ServiceBooksNote> — the coverage note for a page with no R-2/P-40 J-book
 * detail behind it (Phase 5F §2a, 5G §5; ROADMAP #14, #111).
 *
 * Such a page carries R-1/P-1 workbook figures and no J-book narrative. WHY
 * decides the sentence, and there are three cases, in this order:
 *
 *   • RECORDED ABSENCE (site_meta.org_absences) — the edition probe read the
 *     official index and recorded that this org has no usable FY2026 book,
 *     with a rule, a URL and a date. Each rule states its own case
 *     (program-tier.orgAbsenceWording): no RDT&E/procurement book published
 *     at all, summary workbook rows no book narrates, or a book that was
 *     downloaded and carries no embedded data payload. Checked FIRST, because
 *     the generic wording below is false for these orgs.
 *   • INGESTED org (site_meta.ingested_service_orgs) — the book IS loaded;
 *     this particular PE simply has no matching R-2/P-40 narrative in it
 *     (a procurement-only, summary, classified, or SBIR line). Saying it is
 *     "not yet ingested" would be false, so the note says so honestly.
 *   • NEITHER — an org whose book is neither loaded nor probed. This is the
 *     only state "not yet ingested" is true of, and the only one it is left
 *     for. In the shipped corpus exactly one page reaches it: 9999999999
 *     "Classified Programs", the one sidecar with an EMPTY service_org, which
 *     has no org to probe and reads "the service J-book".
 *
 * Either way the word 'roadmap' links to the methodology coverage anchor.
 *
 * data-coverage="service-books" is the G2 coverage-gate contract (the gate's
 * representative page is the first rollup-tier program page); every word of
 * the wording comes from the payload via serviceOrgName /
 * isIngestedServiceOrg / getOrgAbsence — no org is named in this file.
 * data-section-empty marks it as the description section's explained empty
 * state for the program-skeleton gate. Gate 21 leg (o) reads the rendered
 * sentence back and fails when it disagrees with either payload.
 */

import Link from "next/link";
import {
  serviceOrgName,
  isIngestedServiceOrg,
  getOrgAbsence,
  orgAbsenceWording,
} from "@/lib/program-tier";

export function ServiceBooksNote({
  serviceOrg,
  className = "",
}: {
  serviceOrg: string;
  className?: string;
}) {
  // Empty org code (1 sidecar) → the generic "service" so the sentence
  // still reads honestly.
  const service = serviceOrgName(serviceOrg) || "service";
  const absence = getOrgAbsence(serviceOrg);
  const ingested = isIngestedServiceOrg(serviceOrg);
  return (
    <p
      data-coverage="service-books"
      data-section-empty
      className={`text-sm text-muted-foreground ${className}`}
    >
      {absence ? (
        <>
          {orgAbsenceWording(absence, serviceOrg).description} See{" "}
        </>
      ) : ingested ? (
        <>
          The {service} FY2026 J-books are ingested, but this program element
          carries no R-2/P-40 narrative in them — only its cited R-1/P-1
          workbook figures are shown. See{" "}
        </>
      ) : (
        <>
          Detailed justification for this program lives in the {service}{" "}
          J-book, which is not yet ingested — see{" "}
        </>
      )}
      <Link
        href="/methodology/#coverage-service-books"
        className="underline decoration-dotted hover:text-foreground"
      >
        roadmap
      </Link>
      .
    </p>
  );
}

/**
 * The same decision for the Justification section's empty state — the second
 * place the page explains the same absence, and the second place the false
 * "not yet ingested" sentence used to render. It lives here so the two
 * sentences cannot drift apart: one file, one branch order, one payload.
 *
 * Returns a fragment for <SectionEmpty>, which supplies the heading and the
 * data-section-empty contract.
 */
export function ServiceBooksJustificationNote({
  serviceOrg,
}: {
  serviceOrg: string;
}) {
  const service = serviceOrgName(serviceOrg) || "service";
  const absence = getOrgAbsence(serviceOrg);
  if (absence) {
    return <>{orgAbsenceWording(absence, serviceOrg).justification}</>;
  }
  if (isIngestedServiceOrg(serviceOrg)) {
    return (
      <>
        The {service} FY2026 J-book is ingested, but this program element
        carries no matching R-2/P-40 accomplishments or planned-program
        narrative — see the description note above.
      </>
    );
  }
  return (
    <>
      Accomplishments and planned-program narratives live in the {service}{" "}
      J-book, which is not yet ingested — see the description note above for
      the roadmap.
    </>
  );
}
