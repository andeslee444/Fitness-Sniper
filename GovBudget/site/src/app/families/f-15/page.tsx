import type { Metadata } from "next";
import { CitationPanelProvider } from "@/components/citation-panel";
import { F15FamilyBrowser } from "@/components/f15-family-browser";
import { getF15FamilyData } from "@/lib/f15-family-data";
import { SITE_URL } from "@/lib/site";
import { FamilyFundingLead, loadFamilyLead } from "@/components/family-funding-lead";
import { F15_RECORD_SLUGS } from "@/lib/f15-family";

export const metadata: Metadata = {
  title: "F-15 family — aircraft, funding & receipts",
  description:
    "Inspect the F-15 aircraft family, compare variants, and follow development, procurement, and modernization records to their original budget receipts.",
  alternates: { canonical: `${SITE_URL}/families/f-15/` },
};

export default function F15FamilyPage() {
  const family = getF15FamilyData();
  const lead = loadFamilyLead(F15_RECORD_SLUGS, "F-15");
  return (
    <CitationPanelProvider citations={family.citations}>
      <F15FamilyBrowser family={family} fundingLead={<FamilyFundingLead lead={lead} shortName="F-15" recordSlugs={F15_RECORD_SLUGS} />} />
    </CitationPanelProvider>
  );
}
