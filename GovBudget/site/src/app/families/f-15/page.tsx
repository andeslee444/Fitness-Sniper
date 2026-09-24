import type { Metadata } from "next";
import { CitationPanelProvider } from "@/components/citation-panel";
import { F15FamilyBrowser } from "@/components/f15-family-browser";
import { getF15FamilyData } from "@/lib/f15-family-data";
import { SITE_URL } from "@/lib/site";
import { FamilyFundingHistory } from "@/components/family-funding-history";
import { getF15FundingHistory } from "@/lib/family-funding-history-data";

export const metadata: Metadata = {
  title: "F-15 family — aircraft, funding & receipts",
  description:
    "Inspect the F-15 aircraft family, compare variants, and follow development, procurement, and modernization records to their original budget receipts.",
  alternates: { canonical: `${SITE_URL}/families/f-15/` },
};

export default function F15FamilyPage() {
  const family = getF15FamilyData();
  const funding = getF15FundingHistory();
  return (
    <CitationPanelProvider citations={{ ...family.citations, ...funding.citations }}>
      <F15FamilyBrowser family={family} fundingLead={<FamilyFundingHistory key="family-funding-history" history={funding.history} shortName="F-15" />} />
    </CitationPanelProvider>
  );
}
