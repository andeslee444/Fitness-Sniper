import { BRIEFING_COPY } from "@/lib/copy";
import Link from "next/link";
import { Cite } from "@/components/cite";
import { getReviewedBriefings } from "@/lib/reviewed-briefings";
import { BriefingReceipt } from "@/components/briefing-receipt";

/** Dated comparisons with bounded explanations; no automated causal stories. */
export function ReviewedBriefings() {
  return <section id="budget-briefings" aria-labelledby="budget-briefings-title" className="my-8 scroll-mt-20" data-pagefind-body="">
    <h2 id="budget-briefings-title" >Budget comparisons</h2>
    <p className="mt-2 text-sm text-muted-foreground">{BRIEFING_COPY.intro}</p>
    <div className="mt-5 grid gap-4 lg:grid-cols-3">
      {getReviewedBriefings().map(brief => <article key={brief.slug} className="min-w-0 rounded-md border border-border p-5" data-briefing={brief.slug}>
        <p className="t-label text-muted-foreground">{brief.name}</p>
        <h3 className="mt-2">{brief.title}</h3>
        <p className="mt-3 text-sm">{brief.change}</p>
        <dl className="my-4 space-y-3">
          {brief.figures.map(card => <div key={card.fid}>
            <dt className="text-sm text-muted-foreground">FY{card.fy} {card.measure} · PB{card.edition}</dt>
            <dd className="t-figure t-figure--3"><Cite value={card.value!} units={card.units!} factId={card.fid} dataset={card.dataset!}
              basis={card.basis!} fy={card.fy} measure={card.measure} edition={card.edition} entity={brief.slug}
              exhibitFamily={brief.slug === "0602668D8Z" ? "rdte" : "procurement"} /></dd>
          </div>)}
        </dl>
        <p className="text-sm" data-briefing-evidence={brief.narrativeFactId}>{brief.context}</p>
        <p className="mt-3 text-sm text-muted-foreground">{brief.uncertain}</p>
        <details className="mt-4 text-sm">
          <summary className="cursor-pointer">Supporting passage</summary>
          <blockquote data-source-text="narrative" data-cite-fact-id={brief.narrativeFactId} className="my-3 border-l-2 border-border pl-3">{brief.evidenceExcerpt}</blockquote>
          <BriefingReceipt factId={brief.narrativeFactId} />
        </details>
        <p className="mt-4 text-xs text-muted-foreground">Source edition: PB{brief.edition}. Review: <time dateTime={brief.reviewedAt}>{brief.reviewedAt}</time>. {BRIEFING_COPY.dateNote}</p>
        <p className="mt-1 text-xs text-muted-foreground">{brief.reviewMethod}</p>
        <Link href={brief.slug === "F015EX" ? "/families/f-15/?variant=EX&purpose=buy&record=F015EX&fy=2026&topic=airframe#funding" : `/program/${brief.slug}/#exhibit`} className="mt-4 inline-block text-sm underline">{brief.name} →</Link>
      </article>)}
    </div>
  </section>;
}
