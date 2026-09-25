import "server-only";
import { getProgramDetails, getCitations } from "@/lib/data";
import specs from "./briefing-specs.json";

export { default as briefingSpecs } from "./briefing-specs.json";

/** A changed source invalidates the dated explanation instead of silently updating it. */
export function getReviewedBriefings() {
  const citations = getCitations();
  return specs.map(spec => {
    for (const [factId, expected] of Object.entries(spec.sourceChecks)) {
      const citation = citations[factId];
      if (!citation || Object.entries(expected).some(([key, value]) => (citation[key as keyof typeof citation] ?? null) !== value)) {
        throw new Error(`Briefing needs source review: ${spec.slug} receipt ${factId}`);
      }
    }
    const details = getProgramDetails(spec.slug);
    const narrative = details.narratives.find(n => n.fact_id === spec.narrativeFactId);
    if (!narrative?.body.includes(spec.evidenceExcerpt) || !citations[spec.narrativeFactId]) {
      throw new Error(`Briefing needs source review: ${spec.slug} narrative`);
    }
    const figures = spec.figures.map(expected => {
      const card = details.summary.cards.find(c => c.fid === expected.fid);
      if (!card || !citations[expected.fid] || Object.entries(expected).some(([key, value]) => card[key as keyof typeof card] !== value)) {
        throw new Error(`Briefing needs source review: ${spec.slug} FY${expected.fy}`);
      }
      return card;
    });
    return { ...spec, figures };
  });
}
