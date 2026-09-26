import type { Metadata } from "next";
import { PageIntro } from "@/components/page-intro";
import { F15FamilyFeature } from "@/components/family-entry";
import Image from "next/image";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { EXHIBIT_PILOTS, PROGRAM_EXHIBITS } from "@/lib/program-exhibits";
import { SITE_URL } from "@/lib/site";

export const metadata: Metadata = {
  title: "What the budget builds",
  description: "The F-15 aircraft family, submarines and cyber research as interactive models, with funding explanations linked to the original budget documents.",
  alternates: { canonical: `${SITE_URL}/explore/` },
};

export default function ExplorePage() {
  return <div className="spine py-10 md:py-16">
    <PageIntro eyebrow="Field guide" title="See what the budget builds." description="Drawn programs, what each one funds and the document behind each explanation." actions={<Link href="/programs/">Browse the complete program index <ArrowRight size="1em" aria-hidden /></Link>}/>
    <F15FamilyFeature />
    <p className="t-label">More programs to inspect</p>
    <div className="grid md:grid-cols-3 gap-5 mt-8">
      {EXHIBIT_PILOTS.map(slug => { const p=PROGRAM_EXHIBITS[slug];return <Link key={slug} href={`/program/${slug}/#exhibit`} className="group rounded-lg border border-border overflow-hidden bg-card hover:border-foreground/40">
        <div className="relative aspect-[1.6] bg-[#0a161f]"><Image src={`/exhibits/${p.subject}.webp`} alt={`Simplified illustration for ${p.name}`} fill sizes="(max-width:768px) 100vw, 400px" className="object-cover"/></div>
        <div className="p-6"><p className="t-id mb-4">{p.eyebrow}</p><h2>{p.name}</h2><p className="mt-3 text-sm leading-relaxed text-muted-foreground">{p.topics.map(t=>t.label).join(" · ")}</p><span className="flex items-center gap-2 mt-6 text-sm font-medium">Explore the program <ArrowRight size={16}/></span></div>
      </Link>;})}
    </div>
    <div className="border-t border-border mt-12 pt-6 grid md:grid-cols-3 gap-6 text-sm">
      <p><strong className="block mb-2">An illustration, with evidence</strong><span className="text-muted-foreground">Each selected topic opens a cited explanation. Geometry is simplified; model parts do not imply a cost allocation.</span></p>
      <p><strong className="block mb-2">One family, distinct funding</strong><span className="text-muted-foreground">Aircraft variants and budget records are separate choices. Development, procurement and upgrade records keep their own accounting context and receipts.</span></p>
      <p><strong className="block mb-2">Still illustrations first</strong><span className="text-muted-foreground">Still illustrations load first. Interactive 3D is optional, with keyboard controls and shareable views.</span></p>
    </div>
    <p className="mt-10 text-sm"><Link href="/programs/" className="underline underline-offset-4">Browse the complete program catalog <ArrowRight size="1em" aria-hidden /></Link></p>
  </div>;
}
