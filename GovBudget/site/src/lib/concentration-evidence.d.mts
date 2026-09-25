import type { CitationsMap, ProgramHHI, ProgramRow, FeedSidecar } from "./data";
export function normalizeProgramHHI(value: unknown, citations: CitationsMap): ProgramHHI | null;
export function filterSupportedConcentrationCards<T extends FeedSidecar>(feed: T, programs: Pick<ProgramRow, "slug" | "hhi">[], citations: CitationsMap): T;
