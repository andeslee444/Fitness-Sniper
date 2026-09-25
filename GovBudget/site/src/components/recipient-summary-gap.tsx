import Link from "next/link";

/**
 * The link from a WHO GETS IT answer that states no recipient total to the
 * page's own Related Awards table (#program-awards). program-skeleton leg (j)
 * holds every "none"-tier answer on a page with award records to carrying it,
 * and holds its count to the sidecar's awards. Shared by this component and
 * the two #80/#82 withheld-concentration answers on the program page
 * (integration 2026-09-25), so the wording cannot drift between them.
 */
export function LinkedAwardRecordsLink({ awardCount }: { awardCount: number }) {
  return (
    <Link href="#program-awards" className="underline decoration-dotted hover:text-foreground">
      {awardCount} linked award {awardCount === 1 ? "record is" : "records are"} listed below
    </Link>
  );
}

/** Missing aggregate dollars must not imply that the page has no award links. */
export function RecipientSummaryGap({ awardCount }: { awardCount: number }) {
  return (
    <span data-who-tier="none" className="text-muted-foreground">
      {awardCount > 0 ? (
        <>
          <LinkedAwardRecordsLink awardCount={awardCount} />
          . No program-wide recipient total is available.
        </>
      ) : (
        <>
          No company is linked to this line. Award records do not carry the
          program element, so the crosswalk is silent here —{" "}
          <Link href="/coverage/#crosswalk" className="underline decoration-dotted hover:text-foreground">
            why
          </Link>.
        </>
      )}
    </span>
  );
}
