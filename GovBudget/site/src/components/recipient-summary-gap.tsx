import Link from "next/link";

/** Missing aggregate dollars must not imply that the page has no award links. */
export function RecipientSummaryGap({ awardCount }: { awardCount: number }) {
  return (
    <span data-who-tier="none" className="text-muted-foreground">
      {awardCount > 0 ? (
        <>
          <Link href="#program-awards" className="underline decoration-dotted hover:text-foreground">
            {awardCount} linked award {awardCount === 1 ? "record is" : "records are"} listed below
          </Link>
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
