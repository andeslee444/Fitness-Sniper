import "server-only";
import { getF15Knowledge } from "./f15-knowledge";

import { collectCitationsWithInputs, getCitation, getProgramDetails, getPrograms, type SummaryCard } from "./data";
import { documentTitleFromUrl } from "./footnote";
import { F15_RECORD_SLUGS, type F15FamilyPayload, type F15Variant, type FamilyFundingFact, type FamilyFundingRecord, type FamilyRecordLink, type FamilySource, type FamilyTopic, type FundingPurpose, type VariantId } from "./f15-family";

/** Curated associations are editorial links, never allocations of a program's dollars. */
const RECORD_CONFIG: Record<string, { purpose: FundingPurpose; purposeLabel: string; scopeNote: string; variantIds: VariantId[] }> = {
  "0207134F": { purpose: "develop", purposeLabel: "Software, integration & testing", variantIds: ["C", "D", "E", "EX"], scopeNote: "Shared across C, D, E and EX: the software narrative explicitly names all four. The program total is not allocated among variants." },
  "0207146F": { purpose: "develop", purposeLabel: "F-15EX development", variantIds: ["EX"], scopeNote: "F-15EX research, development, integration and test funding. Separate from aircraft procurement." },
  "0207171F": { purpose: "develop", purposeLabel: "EPAWSS development", variantIds: ["E", "EX"], scopeNote: "Related EPAWSS system development. E and EX use the system; this record does not allocate development funding between variants. No FY2025 or FY2026 TOA figure is published here." },
  F01500: { purpose: "upgrade", purposeLabel: "Fleet modifications & tooling", variantIds: ["C", "D", "E"], scopeNote: "Shared C, D and E modifications and support equipment. The BLI total is not a variant-specific price or allocation." },
  F015EX: { purpose: "buy", purposeLabel: "Aircraft, modifications & support", variantIds: ["EX"], scopeNote: "This procurement BLI combines aircraft, modifications and support across budget activities. It is broader than the price of new aircraft alone." },
  F15EWS: { purpose: "upgrade", purposeLabel: "F-15E EPAWSS installation", variantIds: ["E"], scopeNote: "The procurement narrative describes EPAWSS installation and related support for F-15E aircraft. This amount is not assigned to F-15EX." },
};

const EDITORIAL_SOURCES: FamilySource[] = [
  { id: "usaf-eagle", title: "U.S. Air Force · F-15 Eagle fact sheet", officialUrl: "https://www.af.mil/About-Us/Fact-Sheets/Display/Article/104501/f-15-eagle/", receiptUrl: "https://www.af.mil/About-Us/Fact-Sheets/Display/Article/104501/f-15-eagle/", locator: "Background and crew · fact sheet dated April 2019", retrievedAt: "2026-09-09", kind: "official-history" },
  { id: "usaf-strike-eagle", title: "U.S. Air Force · F-15E Strike Eagle fact sheet", officialUrl: "https://www.af.mil/About-Us/Fact-Sheets/Display/Article/104499/f-15e-strike-eagle/", receiptUrl: "https://www.af.mil/About-Us/Fact-Sheets/Display/Article/104499/f-15e-strike-eagle/", locator: "Mission, crew and background · fact sheet dated April 2019", retrievedAt: "2026-09-09", kind: "official-history" },
  { id: "usaf-ex-delivery", title: "U.S. Air Force · Air Force receives first F-15EX", officialUrl: "https://www.af.mil/News/Features/Article/2534008/air-force-receives-first-f-15ex/", receiptUrl: "https://www.af.mil/News/Features/Article/2534008/air-force-receives-first-f-15ex/", locator: "March 11, 2021 · delivery and aircraft configuration", retrievedAt: "2026-09-09", kind: "official-history" },
  { id: "usaf-ex-name", title: "U.S. Air Force · F-15EX Eagle II unveiled", officialUrl: "https://www.af.mil/News/Article/2564394/f-15ex-eagle-ii-unveiled-as-newest-fighter/", receiptUrl: "https://www.af.mil/News/Article/2564394/f-15ex-eagle-ii-unveiled-as-newest-fighter/", locator: "April 7, 2021 · naming ceremony", retrievedAt: "2026-09-09", kind: "official-history" },
];

const sharedSoftware: FamilyRecordLink = { slug: "0207134F", scope: "shared", note: "Shared software and integration for C, D, E and EX; no variant allocation.", evidenceFactId: "0026c924483c6624" };
const sharedModifications: FamilyRecordLink = { slug: "F01500", scope: "shared", note: "Shared modifications and tooling for C, D and E; no variant allocation.", evidenceFactId: "c9e5c28dfebc879e" };
const sharedEpawss: FamilyRecordLink = { slug: "0207171F", scope: "shared", note: "Related system development, not a variant-specific allocation. EPAWSS is described on E and EX source records.", evidenceFactId: "b30fae1fd23999e4", evidenceSourceIds: ["usaf-ex-delivery"] };

const VARIANTS: F15Variant[] = [
  { id: "A", name: "F-15A", nickname: "Eagle", role: "Air superiority", crew: "1 pilot", era: "1972 · first flight", description: "The original single-seat Eagle. Its first flight began the F-15 family in July 1972.", changes: ["Original single-seat configuration"], sourceIds: ["usaf-eagle"], recordLinks: [], coverageNote: "Historical context. No separately identified F-15A budget record is mapped in this collection." },
  { id: "B", name: "F-15B", nickname: "Eagle", role: "Two-seat trainer", crew: "2 crew", era: "1973 · first flight", description: "The two-seat trainer first flew in July 1973. It is a companion configuration to the early single-seat Eagle.", changes: ["Two-seat training configuration"], sourceIds: ["usaf-eagle"], recordLinks: [], coverageNote: "Historical context. No separately identified F-15B budget record is mapped in this collection." },
  { id: "C", name: "F-15C", nickname: "Eagle", role: "Air superiority", crew: "1 pilot", era: "1979 · entered inventory", description: "A single-seat model with production improvements, including more internal fuel and provisions for conformal fuel tanks.", changes: ["Single-seat cockpit", "Production Eagle Package improvements"], sourceIds: ["usaf-eagle"], recordLinks: [sharedSoftware, sharedModifications], coverageNote: "Linked records cover several variants. They do not provide an exclusive F-15C total." },
  { id: "D", name: "F-15D", nickname: "Eagle", role: "Two-seat air superiority", crew: "2 crew", era: "1979 · entered inventory", description: "The two-seat counterpart introduced alongside the C model, with the same generation of production improvements.", changes: ["Two-seat cockpit", "Production Eagle Package improvements"], sourceIds: ["usaf-eagle"], recordLinks: [sharedSoftware, sharedModifications], coverageNote: "Linked records cover several variants. They do not provide an exclusive F-15D total." },
  { id: "E", name: "F-15E", nickname: "Strike Eagle", role: "Air-to-air & air-to-ground", crew: "Pilot + weapon systems officer", era: "1988 · first production delivery", description: "The dual-role Strike Eagle pairs a pilot with a weapon systems officer and adds systems for air-to-ground missions.", changes: ["Dedicated weapon systems officer", "Conformal fuel tanks", "Air-to-ground mission systems"], sourceIds: ["usaf-strike-eagle"], recordLinks: [sharedSoftware, sharedModifications, sharedEpawss, { slug: "F15EWS", scope: "variant", note: "F-15E EPAWSS installation and related support.", evidenceFactId: "b3dbc6ed30814fdf" }], coverageNote: "Some records are shared with other variants. EPAWSS procurement is linked specifically to the F-15E source narrative." },
  { id: "EX", name: "F-15EX", nickname: "Eagle II", role: "Multirole-capable fighter", crew: "1 or 2 aircrew", era: "2021 · first Air Force delivery", description: "A two-seat Eagle with digital flight controls, cockpit displays and updated avionics. It can operate with one or two aircrew.", changes: ["Digital fly-by-wire flight controls", "Digital cockpit and EPAWSS", "Separate development and procurement records"], sourceIds: ["usaf-ex-delivery", "usaf-ex-name"], recordLinks: [
    { slug: "0207146F", scope: "variant", note: "Dedicated F-15EX development and testing record.", evidenceFactId: "d9982379a24ebac6" },
    { slug: "F015EX", scope: "variant", note: "Procurement BLI includes aircraft, modifications and support.", evidenceFactId: "e7d5bcfb4a30f458" },
    sharedSoftware, sharedEpawss,
  ], coverageNote: "Dedicated EX records sit alongside shared software and related EPAWSS development. Their scopes remain separate." },
];

const TOPICS: Omit<FamilyTopic, "source">[] = [
  { id: "airframe", label: "Aircraft & retrofits", text: "F-15EX procurement covers new aircraft and work on earlier production lots. The retrofit narrative describes bringing early aircraft toward a common production configuration.", recordSlugs: ["F015EX"], variantIds: ["EX"], factId: "cb4796e48126e4a7", evidenceContains: "common production configuration" },
  { id: "cockpit", label: "Software & integration", text: "The Operational Flight Program supplies software and hardware updates for C, D, E and EX aircraft. This is a shared development effort, not a separate price for each cockpit.", recordSlugs: ["0207134F"], variantIds: ["C", "D", "E", "EX"], factId: "0026c924483c6624", evidenceContains: "F-15C, F-15D, F-15E, and F-15EX" },
  { id: "sensors", label: "Electronic warfare", text: "EPAWSS replaces the earlier Tactical Electronic Warfare System. Its development record describes electronic sensing, threat awareness and countermeasures; procurement and installation are separate records.", recordSlugs: ["0207171F", "F15EWS", "0207146F"], variantIds: ["E", "EX"], factId: "b30fae1fd23999e4", evidenceContains: "Tactical Electronic Warfare System" },
  { id: "support", label: "Tooling & support", text: "The shared F-15 procurement record includes retained tooling and test equipment used to manufacture, repair and support C, D and E aircraft and their systems.", recordSlugs: ["F01500"], variantIds: ["C", "D", "E"], factId: "5711f9082a7db358", evidenceContains: "F-15C, F-15D, and F-15E support equipment and tooling" },
];

// Keep one object per source across records, topics and the source index.
// React can then send references in Flight instead of repeating provenance.
const factSources = new Map<string, FamilySource>();

function sourceForFact(factId: string): FamilySource {
  const existing = factSources.get(factId);
  if (existing) return existing;
  const citation = getCitation(factId);
  if (!citation) throw new Error(`[f15-family] Missing citation ${factId}`);
  const locator = citation.kind === "derived" ? citation.formula
    : citation.sheet && citation.cells ? `${citation.sheet} · ${citation.cells}`
      : citation.page_number != null ? `Page ${citation.page_number}` : citation.xml_path;
  const source: FamilySource = {
    id: factId, factId,
    title: documentTitleFromUrl(citation.official_url, citation.kind) ?? (citation.kind === "derived" ? "Calculation from cited source rows" : "Official budget source"),
    officialUrl: citation.official_url,
    receiptUrl: `/fact/${factId.slice(0, 8)}/`,
    locator: locator ?? null, retrievedAt: citation.retrieved_at, kind: citation.kind,
  };
  factSources.set(factId, source);
  return source;
}

function measureLabel(measure: string) {
  return ({ actuals: "Actuals", enacted: "Enacted", total: "Total", request: "Request", "disc-request": "Discretionary request", "reconciliation-request": "Reconciliation request", change: "Change" } as Record<string, string>)[measure] ?? measure.replaceAll("-", " ");
}

function fundingFact(slug: string, exhibit: string, input: { fid: string; public_id?: string | null; value: number; fy: number; measure: string; basis: string; edition: number; dataset?: string | null }): FamilyFundingFact {
  return { factId: input.fid, publicId: input.public_id ?? input.fid.slice(0, 8), recordSlug: slug, amountThousands: input.value, units: "USD thousands", fy: input.fy, measure: input.measure, status: measureLabel(input.measure), basis: input.basis, dataset: input.dataset ?? "budget_lines", exhibit, edition: input.edition, source: sourceForFact(input.fid) };
}

function isToaCard(card: SummaryCard): card is SummaryCard & { fid: string; value: number; basis: string } {
  return card.basis === "toa" && card.units === "USD thousands" && card.fid != null && card.value != null;
}

function loadRecord(slug: string): FamilyFundingRecord {
  const config = RECORD_CONFIG[slug];
  const program = getPrograms().find((row) => row.slug === slug);
  if (!program) throw new Error(`[f15-family] Missing canonical program ${slug}`);
  const details = getProgramDetails(slug);
  const exhibit = details.budget_lines[0]?.exhibit;
  if (!exhibit) throw new Error(`[f15-family] No workbook exhibit for ${slug}`);
  const facts = new Map<string, FamilyFundingFact>();
  const preferredFactIds: Record<number, string> = {};
  const add = (fact: FamilyFundingFact) => {
    const key = `${fact.fy}/${fact.measure}`;
    // A decade series can classify a summary's FY2025 total as
    // 'enacted-total'. It is the same source cell, not another fact to render.
    if (!facts.has(key) && ![...facts.values()].some((existing) => existing.factId === fact.factId)) facts.set(key, fact);
  };
  // Exporter-selected canonical program totals come first. In particular,
  // F015EX has multiple budget activity rows; choosing its first row is wrong.
  for (const card of details.summary.cards) {
    if (card.key !== "change" && isToaCard(card)) {
      add(fundingFact(slug, exhibit, card));
      preferredFactIds[card.fy] = card.fid;
    }
  }
  for (const points of Object.values(details.decade_series ?? {})) {
    for (const point of points) {
      if (point.basis !== "toa") continue;
      add(fundingFact(slug, exhibit, { ...point, value: point.v, dataset: "fct_decade_series" }));
    }
  }
  // Explicit request components remain selectable; no zero is invented for
  // a missing discretionary or reconciliation row.
  for (const split of [details.fy26_split?.disc, details.fy26_split?.reconciliation]) {
    if (split) add(fundingFact(slug, exhibit, { ...split, value: split.v }));
  }
  const componentRows = details.budget_lines.filter((row) => row.fy != null && row.measure != null).map((row) => ({
    ...fundingFact(slug, row.exhibit, { fid: row.fact_id, value: row.amount_thousands, fy: row.fy!, measure: row.measure!, basis: row.basis, edition: row.edition }),
    entity: row.entity, label: row.title ?? program.title,
  }));
  // Where an exact status has one workbook row, preserve it (e.g. FY2025
  // enacted alongside the exporter's FY2025 total). Multiple rows need the
  // existing derived citation; they must never be silently summed here.
  const groups = new Map<string, FamilyFundingFact[]>();
  for (const row of componentRows) {
    const key = `${row.fy}/${row.measure}`;
    groups.set(key, [...groups.get(key) ?? [], row]);
  }
  for (const rows of groups.values()) if (rows.length === 1) add(rows[0]);
  const changeCard = details.summary.cards.find((card) => card.key === "change");
  const change = changeCard && isToaCard(changeCard) ? { ...fundingFact(slug, exhibit, changeCard), percent: changeCard.pct ?? null, fromFactId: preferredFactIds[changeCard.fy - 1], toFactId: preferredFactIds[changeCard.fy] } : null;
  if (change && (!change.fromFactId || !change.toFactId)) throw new Error(`[f15-family] Change ${change.factId} lacks canonical yearly endpoints`);
  const narratives = details.narratives.filter((item) => item.fact_id).map((item) => ({ factId: item.fact_id!, title: item.title, body: item.body, kind: item.kind, source: sourceForFact(item.fact_id!) }));
  const absenceNotes = details.summary.cards.filter((card) => card.key !== "change" && !isToaCard(card)).map((card) => ({ fy: card.fy, text: card.basis === "jbook-detail" ? "No TOA workbook figure in this collection. The program dossier carries a separate J-book detail figure; the accounting bases are not interchangeable." : "No cited TOA workbook figure in this collection." }));
  return { slug, title: program.title, identifierKind: exhibit === "R-1" ? "PE" : "BLI", ...config, facts: [...facts.values()].sort((a, b) => a.fy - b.fy || a.measure.localeCompare(b.measure)), preferredFactIds, componentRows, narratives, change, absenceNotes };
}

/** Fail loudly when a curated link's evidence disappears during a future export. */
export function validateF15FamilyEvidence(records: FamilyFundingRecord[], variants: F15Variant[], topics: Omit<FamilyTopic, "source">[]) {
  const allNarratives = records.flatMap((record) => record.narratives);
  for (const variant of variants) for (const link of variant.recordLinks) {
    const record = records.find((item) => item.slug === link.slug);
    if (!record?.variantIds.includes(variant.id) || !record.narratives.some((item) => item.factId === link.evidenceFactId)) throw new Error(`[f15-family] Unresolved ${variant.id} → ${link.slug} evidence ${link.evidenceFactId}`);
    for (const sourceId of link.evidenceSourceIds ?? []) {
      if (!EDITORIAL_SOURCES.some((source) => source.id === sourceId)) throw new Error(`[f15-family] Missing relationship source ${sourceId}`);
    }
  }
  for (const topic of topics) {
    const source = allNarratives.find((item) => item.factId === topic.factId);
    if (!source?.body.toLowerCase().includes(topic.evidenceContains.toLowerCase())) throw new Error(`[f15-family] Missing or changed ${topic.id} evidence ${topic.factId}`);
  }
}

let cached: F15FamilyPayload | null = null;

export function getF15FamilyData(): F15FamilyPayload {
  if (cached) return cached;
  const records = F15_RECORD_SLUGS.map(loadRecord);
  validateF15FamilyEvidence(records, VARIANTS, TOPICS);
  const topics = TOPICS.map((topic) => ({ ...topic, source: sourceForFact(topic.factId) }));
  const factIds = records.flatMap((record) => [...record.facts.map((fact) => fact.factId), ...record.componentRows.map((fact) => fact.factId), ...record.narratives.map((item) => item.factId), ...(record.change ? [record.change.factId] : [])]);
  const citations = collectCitationsWithInputs(factIds);
  // A narrative may have an XML locator without a resolved PDF page. Keep
  // its actual exported text in the page-local citation so "Read passage"
  // still delivers the passage. Clone only enriched entries: getCitation's
  // shared cache and all original provenance fields must remain untouched.
  for (const narrative of records.flatMap((record) => record.narratives)) {
    const citation = citations[narrative.factId];
    if (citation?.kind === "jbook_narrative") {
      citations[narrative.factId] = { ...citation, source_passage: { title: narrative.title, body: narrative.body } };
    }
  }
  const sources = [...EDITORIAL_SOURCES, ...Object.keys(citations).map(sourceForFact)];
  const knowledge = getF15Knowledge(new Set(getPrograms().map((program) => program.slug)));
  const contextSourceIds = new Set(knowledge.contexts.flatMap((context) => context.sourceIds));
  cached = {
    id: "f-15", title: "The F-15 family", intro: "One aircraft family. Different missions, generations and funding records. Inspect a variant, follow its program elements and open the evidence behind each figure.",
    variants: VARIANTS, records, topics, sources, citations,
    knowledge: { reviewed: knowledge.reviewed, contexts: knowledge.contexts, sources: knowledge.sources.filter((source) => contextSourceIds.has(source.id)) },
    milestones: [
      { year: 1972, label: "F-15A first flight", variantIds: ["A"], sourceId: "usaf-eagle" },
      { year: 1973, label: "F-15B trainer first flight", variantIds: ["B"], sourceId: "usaf-eagle" },
      { year: 1979, label: "C and D enter Air Force inventory", variantIds: ["C", "D"], sourceId: "usaf-eagle" },
      { year: 1988, label: "First production F-15E delivered", variantIds: ["E"], sourceId: "usaf-strike-eagle" },
      { year: 2021, label: "Air Force accepts first F-15EX", variantIds: ["EX"], sourceId: "usaf-ex-delivery" },
    ],
    years: [...new Set(records.flatMap((record) => record.facts.map((fact) => fact.fy)))].sort((a, b) => b - a),
    coverageNote: "A curated U.S. F-15 family view of six canonical budget records. Shared records are shown once; budgets are not allocated by aircraft variant or model component. Historical context is separate from the available fiscal-year collection.",
  };
  return cached;
}
