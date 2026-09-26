import type { Metadata } from "next";
import Link from "next/link";
import { getFilingsIndex } from "@/lib/data";
import { SITE_NAME, SITE_URL } from "@/lib/site";
import { coreOgImages } from "@/lib/og";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { PageIntro } from "@/components/page-intro";
import { FilingsTable } from "@/components/filings-table";

export const metadata: Metadata = {
  title: "Lobbying Filings",
  description:
    "Senate LDA lobbying filings cross-referenced against tracked defense programs — client, registrant, reported dollars, and program mentions.",
  alternates: { canonical: `${SITE_URL}/filings/` },
  openGraph: {
    title: `Lobbying Filings — ${SITE_NAME}`,
    description:
      "Senate LDA lobbying filings cross-referenced against tracked defense programs.",
    url: `${SITE_URL}/filings/`,
    siteName: SITE_NAME,
    images: coreOgImages("filings-index"),
  },
};

export default function FilingsIndexPage() {
  const index = getFilingsIndex();
  const withMentions = index.filings.filter((f) => f.has_mentions).length;

  return (
    <div className="spine py-8">
      <Breadcrumbs
        items={[{ label: "Home", href: "/" }, { label: "Filings" }]}
      />

      <PageIntro eyebrow="Public disclosure records" title="Read the lobbying record."
        description="Find a client, registrant, or program mention, then inspect the filing and its official source."
        actions={<><a href="#filing-directory">Search filings</a><Link href="/companies/">Contractor families</Link></>}>
        <h2 className="sr-only">Lobbying filings</h2>
        <p className="text-muted-foreground mb-2">
          {index.total.toLocaleString("en-US")} Senate LDA filings from
          registrants whose clients appear in the tracked-program corpus.{" "}
          {withMentions.toLocaleString("en-US")} filings mention at least one
          tracked program (shown first).
        </p>
        <p className="text-xs text-muted-foreground">
          Reported income/expense figures on each filing page cite the filing
          record on lda.senate.gov. See{" "}
          <Link
            href="/methodology/"
            className="underline hover:text-foreground"
          >
            methodology
          </Link>{" "}
          for how program mentions are matched.
        </p>
      </PageIntro>

      <div id="filing-directory" className="scroll-mt-24">
        <FilingsTable filings={index.filings} />
      </div>
    </div>
  );
}
