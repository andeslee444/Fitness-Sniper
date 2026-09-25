/** Client-safe contracts for a curated aircraft family above canonical budget records. */
import type { CitationsMap } from "./data";
import type { F15Knowledge } from "./f15-knowledge-types";

export type VariantId = "A" | "B" | "C" | "D" | "E" | "EX";
export type FundingPurpose = "develop" | "buy" | "upgrade";
export type F15TopicId = "airframe" | "cockpit" | "sensors" | "support";

export interface FamilySource {
  id: string;
  factId?: string;
  title: string;
  officialUrl: string | null;
  receiptUrl: string;
  locator: string | null;
  retrievedAt: string | null;
  kind: string;
}

export interface FamilyRecordLink {
  slug: string;
  scope: "variant" | "shared";
  note: string;
  evidenceFactId: string;
  /** Additional official evidence for a relationship, distinct from its funding fact. */
  evidenceSourceIds?: string[];
}

export interface F15Variant {
  id: VariantId;
  name: string;
  nickname: string;
  role: string;
  crew: string;
  era: string;
  description: string;
  changes: string[];
  sourceIds: string[];
  recordLinks: FamilyRecordLink[];
  coverageNote: string;
}

export interface FamilyFundingFact {
  factId: string;
  publicId: string;
  recordSlug: string;
  amountThousands: number;
  units: "USD thousands";
  fy: number;
  measure: string;
  status: string;
  basis: string;
  dataset: string;
  exhibit: string;
  edition: number;
  source: FamilySource;
  /** Canonical rollup and its source rows are separate collections, never add both. */
  entity?: string;
  label?: string;
}

export interface FamilyNarrative {
  factId: string;
  title: string;
  body: string;
  kind: string;
  source: FamilySource;
}

export interface FamilyFundingRecord {
  slug: string;
  title: string;
  identifierKind: "PE" | "BLI";
  purpose: FundingPurpose;
  purposeLabel: string;
  scopeNote: string;
  variantIds: VariantId[];
  /** One canonical fact per fiscal year/status, with separate split measures. */
  facts: FamilyFundingFact[];
  /** Exact exporter SummaryCard choice, which takes precedence over generic status ordering. */
  preferredFactIds: Record<number, string>;
  /** Underlying R-1/P-1 rows for inspection. Not additional to canonical facts. */
  componentRows: FamilyFundingFact[];
  narratives: FamilyNarrative[];
  change:
    | (FamilyFundingFact & {
        percent: number | null;
        fromFactId: string;
        toFactId: string;
      })
    | null;
  absenceNotes: { fy: number; text: string }[];
}

export interface FamilyTopic {
  id: F15TopicId;
  label: string;
  text: string;
  recordSlugs: string[];
  variantIds: VariantId[];
  factId: string;
  evidenceContains: string;
  source: FamilySource;
}

export interface FamilyMilestone {
  year: number;
  label: string;
  variantIds: VariantId[];
  sourceId: string;
}

export interface F15FamilyPayload {
  id: "f-15";
  title: string;
  intro: string;
  variants: F15Variant[];
  records: FamilyFundingRecord[];
  topics: FamilyTopic[];
  sources: FamilySource[];
  milestones: FamilyMilestone[];
  years: number[];
  citations: CitationsMap;
  coverageNote: string;
  /** Only inspection context ships initially. Full research loads near its section. */
  knowledge: Pick<F15Knowledge, "reviewed" | "contexts" | "sources">;
}

export const F15_VARIANT_IDS: VariantId[] = ["A", "B", "C", "D", "E", "EX"];
export const F15_RECORD_SLUGS = [
  "0207134F",
  "0207146F",
  "0207171F",
  "F01500",
  "F015EX",
  "F15EWS",
] as const;
export const FUNDING_PURPOSE_LABELS: Record<FundingPurpose, string> = {
  develop: "Develop",
  buy: "Buy",
  upgrade: "Upgrade",
};

export function isF15VariantId(
  value: string | null | undefined,
): value is VariantId {
  return F15_VARIANT_IDS.some((id) => id === value);
}

export function getVariantRecords(
  payload: F15FamilyPayload,
  variant: VariantId,
  purpose?: FundingPurpose,
): FamilyFundingRecord[] {
  const links =
    payload.variants.find((item) => item.id === variant)?.recordLinks ?? [];
  const records = new Map(
    payload.records.map((record) => [record.slug, record]),
  );
  return [...new Set(links.map((link) => link.slug))].flatMap((slug) => {
    const record = records.get(slug);
    return record && (!purpose || record.purpose === purpose) ? [record] : [];
  });
}

/** Use the exporter's exact summary choice; explicit status requests remain exact. */
export function getRecordFact(
  record: FamilyFundingRecord,
  fy: number,
  measure?: string,
): FamilyFundingFact | null {
  const candidates = record.facts.filter((fact) => fact.fy === fy);
  if (measure)
    return candidates.find((fact) => fact.measure === measure) ?? null;
  const preferred = candidates.find(
    (fact) => fact.factId === record.preferredFactIds[fy],
  );
  if (preferred) return preferred;
  // Historical years outside the exporter's summary still prefer observed
  // actuals, then a published total, enacted authority and finally a request.
  return (
    ["actuals", "total", "enacted", "request"].flatMap((status) =>
      candidates.filter((fact) => fact.measure === status),
    )[0] ?? null
  );
}

/** Resolve only the exact additive inputs named by a canonical receipt.
 * A year's component rows also contain alternative funding measures, so they
 * must never be summed merely because they share a fiscal year.
 */
export function getFundingInputs(
  record: FamilyFundingRecord,
  fact: FamilyFundingFact | null,
  citations: CitationsMap,
): FamilyFundingFact[] {
  if (!fact) return [];
  const citation = citations[fact.factId];
  if (
    citation?.kind !== "derived" ||
    !citation.formula?.startsWith("sum(") ||
    !citation.inputs
  )
    return [];
  let ids: unknown;
  try {
    ids = JSON.parse(citation.inputs);
  } catch {
    return [];
  }
  if (
    !Array.isArray(ids) ||
    ids.length < 2 ||
    ids.length > 8 ||
    ids.some((id) => typeof id !== "string") ||
    new Set(ids).size !== ids.length
  )
    return [];
  const inputs: FamilyFundingFact[] = [];
  for (const id of ids) {
    const matches = record.componentRows.filter((row) => row.factId === id);
    if (matches.length !== 1) return [];
    const row = matches[0];
    if (
      !citations[id] ||
      row.fy !== fact.fy ||
      row.units !== fact.units ||
      row.basis !== fact.basis ||
      row.edition !== fact.edition ||
      row.measure !== fact.measure ||
      !Number.isFinite(row.amountThousands)
    )
      return [];
    inputs.push(row);
  }
  return Math.abs(
    inputs.reduce((sum, row) => sum + row.amountThousands, 0) -
      fact.amountThousands,
  ) < 0.000001
    ? inputs
    : [];
}

/**
 * A transparent calculation for a selected set, not a minted warehouse fact.
 * Always pass an exact status: actuals/enacted/request may never be combined.
 * Missing members keep the sum null rather than presenting a partial family total.
 */
export function getFamilyFundingSummary(
  records: FamilyFundingRecord[],
  fy: number,
  measure: string,
) {
  const uniqueRecords = [
    ...new Map(records.map((record) => [record.slug, record])).values(),
  ];
  const missingSlugs = uniqueRecords
    .filter((record) => !getRecordFact(record, fy, measure))
    .map((record) => record.slug);
  const facts = [
    ...new Map(
      uniqueRecords.flatMap((record) => {
        const fact = getRecordFact(record, fy, measure);
        return fact ? [[fact.factId, fact] as const] : [];
      }),
    ).values(),
  ];
  const bases = new Set(
    facts.map((fact) => `${fact.basis}/${fact.units}/${fact.edition}`),
  );
  const complete =
    uniqueRecords.length > 0 && missingSlugs.length === 0 && bases.size === 1;
  return {
    amountThousands: complete
      ? facts.reduce((sum, fact) => sum + fact.amountThousands, 0)
      : null,
    facts,
    missingSlugs,
    complete,
    fy,
    measure,
    basis: bases.size === 1 ? (facts[0]?.basis ?? null) : null,
  };
}
