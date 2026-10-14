/**
 * years-matrix-shards.mjs — the /years/ core and its lazy shards
 * (families piece-1 follow-ups design §3.2–3.4, ROADMAP #193).
 *
 * export_site.py writes json/years_matrix.json (the CORE: the header, every
 * row with its project count `np`, and the cells of decade_default_columns)
 * and two shards, json/years_matrix/decade.json (the other decade columns)
 * and json/years_matrix/detail.json (the PB2026 amount-type, Δ and %Δ cells
 * and the project sub-rows). Every file carries the same build_id.
 *
 * mergeYearsMatrix puts loaded shards back on the core's rows. It is the JS
 * mirror of export_site.merge_years_matrix, key for key, and
 * tests/fixtures/years_matrix_split/ pins the pair from both sides
 * (tests/test_export_years_matrix.py and
 * src/__tests__/years-matrix-shards.test.ts). The client island merges
 * incrementally (the core first, then whichever shard a reader asks for);
 * the yearsmatrix gate merges all three.
 *
 * Plain .mjs (typed by years-matrix-shards.d.mts) so the gate scripts can
 * import it without a TypeScript step.
 */

/** The lazy shards, in the core manifest's order. */
export const YEARS_SHARD_NAMES = ["decade", "detail"];

/** A row's identity across the core and its shards: `slug ?? pe_bli`. */
export function yearsRowKey(program) {
  return program.slug ?? program.pe_bli;
}

/** column key → the shard that holds it, read from the core's manifest. A
 *  key in no shard (a default decade column) is in the core itself. */
export function shardOfColumns(core) {
  const out = new Map();
  for (const entry of core.shards ?? []) {
    for (const col of entry.columns ?? []) out.set(col, entry.name);
  }
  return out;
}

/**
 * The core with each shard's cells, and the detail shard's project rows, put
 * back on their rows. Rows a shard does not name keep what the core gave
 * them (a core row has no projects, so they default to []; a pre-split,
 * schema-1 payload passed as the core therefore merges to itself, and the
 * island still renders an export from before the split). Throws when a
 * shard carries another build_id: a shard from one export never fills a
 * core from another.
 */
export function mergeYearsMatrix(core, shards = []) {
  for (const shard of shards) {
    if (shard.build_id !== core.build_id) {
      throw new Error(
        `years_matrix shard ${JSON.stringify(shard.shard)} carries build_id ` +
          `${shard.build_id} but the core carries ${core.build_id}: files from two exports`,
      );
    }
  }
  const { orgs, ...header } = core;
  return {
    ...header,
    orgs: orgs.map((org) => ({
      ...org,
      programs: org.programs.map((program) => {
        const key = yearsRowKey(program);
        const cells = { ...program.cells };
        let projects = program.projects ?? [];
        for (const shard of shards) {
          const row = shard.rows?.[key];
          if (!row) continue;
          if (row.cells) Object.assign(cells, row.cells);
          if (row.projects !== undefined) projects = row.projects;
        }
        return { ...program, cells, projects };
      }),
    })),
  };
}
