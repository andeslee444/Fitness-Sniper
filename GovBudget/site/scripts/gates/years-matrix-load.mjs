/**
 * years-matrix-load.mjs — the ONE loader every /years/ check reads through
 * (families piece-1 follow-ups design §3.6, ROADMAP #193).
 *
 * The exporter writes json/years_matrix.json (the core) and two lazy shards,
 * json/years_matrix/decade.json and json/years_matrix/detail.json. The
 * yearsmatrix gate's static legs (a, b, d, e, f, g, i, j) run on the MERGED
 * view, built here with the same mergeYearsMatrix the /years/ island runs, so
 * a leg checks exactly the cells a reader can reach. On the way it proves the
 * files belong together: every shard the core's manifest lists exists with
 * the manifest's byte count and sha256 and carries the core's build_id, and
 * the shard directory holds nothing else.
 *
 * loadYearsMatrix(jsonDir) → { matrix, core, files }
 *   matrix  the merged view (YearsMatrixData shape, rows keep `np`)
 *   core    the parsed core
 *   files   [{ rel, bytes, gzip }] for the core and each shard, gzip
 *           measured by gzip9 (the exporter's measure)
 * Throws with the reason on any inconsistency, or on a pre-split export
 * (schema_version 1), which the gate no longer accepts.
 */
import fs from "fs";
import path from "path";
import { createHash } from "node:crypto";
import { spawnSync } from "child_process";
import { mergeYearsMatrix, YEARS_SHARD_NAMES } from "../../src/lib/years-matrix-shards.mjs";

export const YEARS_CORE = "years_matrix.json";
export const YEARS_SHARD_DIR = "years_matrix";

/**
 * gzip -9 size of a buffer, by the system gzip (`-n`: no name or timestamp
 * in the header). This is the exporter's own measure: Python's
 * gzip.compress(level 9) and `gzip -9 -n` give 780,074 B for the deployed
 * single file, where node's bundled zlib gives 754,311 B (measured
 * 2026-10-13), so a budget checked with node's zlib would be looser than the
 * one the exporter enforces.
 */
export function gzip9(buf) {
  const res = spawnSync("gzip", ["-9", "-n", "-c"], {
    input: buf,
    maxBuffer: 64 * 1024 * 1024,
  });
  if (res.status !== 0) {
    throw new Error(`gzip -9 exited ${res.status}: ${String(res.stderr).slice(0, 200)}`);
  }
  return res.stdout.length;
}

export function loadYearsMatrix(jsonDir) {
  const corePath = path.join(jsonDir, YEARS_CORE);
  if (!fs.existsSync(corePath)) {
    throw new Error(`${YEARS_CORE} missing at ${corePath} — run export-site`);
  }
  const coreBuf = fs.readFileSync(corePath);
  const core = JSON.parse(coreBuf.toString("utf8"));
  if (core.schema_version !== 2 || !Array.isArray(core.shards)) {
    throw new Error(
      `${YEARS_CORE} is schema_version ${core.schema_version} with no shard ` +
        `manifest: an export from before the #193 split — re-run export-site`,
    );
  }
  const files = [{ rel: YEARS_CORE, bytes: coreBuf.length, gzip: gzip9(coreBuf) }];
  const shards = [];
  const listed = new Set();
  for (const entry of core.shards) {
    if (!YEARS_SHARD_NAMES.includes(entry.name)) {
      throw new Error(`${YEARS_CORE} lists an unknown shard ${JSON.stringify(entry.name)}`);
    }
    listed.add(path.basename(entry.path));
    const shardPath = path.join(jsonDir, ...entry.path.split("/"));
    if (!fs.existsSync(shardPath)) {
      throw new Error(`${entry.path} is listed by ${YEARS_CORE} but missing`);
    }
    const buf = fs.readFileSync(shardPath);
    if (buf.length !== entry.bytes) {
      throw new Error(`${entry.path} is ${buf.length} bytes; the manifest says ${entry.bytes}`);
    }
    const sha = createHash("sha256").update(buf).digest("hex");
    if (sha !== entry.sha256) {
      throw new Error(`${entry.path} sha256 ${sha} != the manifest's ${entry.sha256}`);
    }
    const shard = JSON.parse(buf.toString("utf8"));
    if (shard.shard !== entry.name) {
      throw new Error(`${entry.path} says it is shard ${JSON.stringify(shard.shard)}`);
    }
    shards.push(shard);
    files.push({ rel: entry.path, bytes: buf.length, gzip: gzip9(buf) });
  }
  const shardDir = path.join(jsonDir, YEARS_SHARD_DIR);
  const strays = fs.existsSync(shardDir)
    ? fs.readdirSync(shardDir).filter((f) => !listed.has(f))
    : [];
  if (strays.length > 0) {
    throw new Error(
      `${YEARS_SHARD_DIR}/ holds file(s) the core does not list: ${strays.join(", ")}`,
    );
  }
  // mergeYearsMatrix throws if any shard's build_id is not the core's.
  return { matrix: mergeYearsMatrix(core, shards), core, files };
}
