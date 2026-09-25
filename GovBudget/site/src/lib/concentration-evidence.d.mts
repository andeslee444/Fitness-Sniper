import type { CitationsMap, NormalizedProgramHHI, ProgramRow, FeedSidecar } from "./data";
/**
 * The all-link validator's ONE-series result (not the exporter's #80
 * dual-series ProgramHHI block): non-null only when the block's all-link
 * series resolves to derived citations whose recorded values and
 * scope-naming formulas match. getPrograms uses it as a fail-closed guard.
 */
export function normalizeProgramHHI(value: unknown, citations: CitationsMap): NormalizedProgramHHI | null;
export function filterSupportedConcentrationCards<T extends FeedSidecar>(feed: T, programs: Pick<ProgramRow, "slug" | "hhi">[], citations: CitationsMap): T;
