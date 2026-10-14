import type {
  YearsCell,
  YearsMatrixData,
  YearsProgram,
  YearsProject,
} from "../components/years-matrix";

/** The two lazy /years/ shards (ROADMAP #193). */
export type YearsShardName = "decade" | "detail";

/** One entry of the core's `shards` manifest. */
export interface YearsShardManifestEntry {
  name: YearsShardName;
  /** Relative to /json/: "years_matrix/decade.json", "years_matrix/detail.json". */
  path: string;
  columns: string[];
  bytes: number;
  sha256: string;
}

/** A shard's row: only what that row has in the shard's columns. */
export interface YearsShardRow {
  cells?: Record<string, YearsCell>;
  projects?: YearsProject[];
}

export interface YearsMatrixShard {
  schema_version: number;
  build_id: string;
  shard: YearsShardName;
  columns: string[];
  /** Keyed by `slug ?? pe_bli` (yearsRowKey). */
  rows: Record<string, YearsShardRow>;
}

/** A core row: no project rows (detail.json has them), their count in `np`. */
export type YearsCoreProgram = Omit<YearsProgram, "projects" | "np"> & { np: number };

/** json/years_matrix.json, schema_version 2: the header, every row and the
 *  default decade columns' cells. */
export interface YearsMatrixCore extends Omit<YearsMatrixData, "orgs" | "build_id" | "shards"> {
  build_id: string;
  shards: YearsShardManifestEntry[];
  orgs: { org: string; programs: YearsCoreProgram[] }[];
}

export const YEARS_SHARD_NAMES: readonly YearsShardName[];
export function yearsRowKey(program: { pe_bli: string; slug?: string }): string;
export function shardOfColumns(
  core: Pick<YearsMatrixCore, "shards">,
): Map<string, YearsShardName>;
export function mergeYearsMatrix(
  core: YearsMatrixCore,
  shards?: YearsMatrixShard[],
): YearsMatrixData;
