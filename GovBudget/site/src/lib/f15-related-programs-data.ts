import "server-only";

import { readFileSync } from "fs";
import { join } from "path";
import { isDeepStrictEqual } from "node:util";
import { getCitation, getProgramDetails, getPrograms, type CitationsMap } from "./data";
import { F15_RECORD_SLUGS } from "./f15-family";
import type { F15RelatedProgram } from "./f15-related-programs";
import seed from "./f15-related-programs.seed.json";

const dedicated = new Set<string>(F15_RECORD_SLUGS);
// Historical passages were reviewed in imported books but have no registry
// entry. Pin that distinction so a missing current receipt cannot pass as old.
const historical = new Map(seed.filter(row => row.factId === null).map(row => [row.identifier, row]));
const normalize = (text: string) => text.replace(/\s+/g, " ").trim();
const platform = /(?:^|[^a-z0-9])F[-‐‑– ]?15(?!\d)/i;

function fail(identifier: string, reason: string): never {
  throw new Error(`[f15-related-programs] ${identifier}: ${reason}`);
}

function readShard(prefix: string): CitationsMap {
  try {
    return JSON.parse(readFileSync(join(process.cwd(), "..", "data", "site", "json", "cite-shards", `${prefix}.json`), "utf8")) as CitationsMap;
  } catch {
    return fail(prefix, "published receipt shard is unavailable");
  }
}

/** Build-time evidence checks also accept a shard reader for isolated failure tests. */
export function validateF15RelatedPrograms(
  rows: readonly F15RelatedProgram[],
  getShard: (prefix: string) => CitationsMap = readShard,
): void {
  const programs = new Map(getPrograms().map(program => [program.slug, program]));
  const identifiers = new Set<string>();
  const facts = new Set<string>();
  const shards = new Map<string, CitationsMap>();
  for (const row of rows) {
    const id = row.identifier;
    if (!id || identifiers.has(id)) fail(id, "duplicate or missing program identity");
    identifiers.add(id);
    if (dedicated.has(id) || (row.slug && dedicated.has(row.slug))) fail(id, "dedicated family record cannot enter shared context");
    const program = row.slug ? programs.get(row.slug) : undefined;
    if (row.slug && (!program || program.pe_bli !== id || program.title !== row.title)) fail(id, "canonical program identity differs from the reviewed source");
    if (!row.title.trim() || !row.association.trim() || !row.locator.trim() || !platform.test(row.excerpt) || row.excerpt.length > 400) fail(id, "missing or unbounded relationship evidence");
    if (!Number.isInteger(row.sourceEdition) || row.sourceEdition < 2000 || row.sourceEdition > 2099) fail(id, "invalid source edition");
    let url: URL;
    try { url = new URL(row.officialUrl); } catch { return fail(id, "invalid official PDF URL"); }
    if (url.protocol !== "https:" || !/\.(?:gov|mil)$/i.test(url.hostname) || !/\.pdf$/i.test(url.pathname) || url.username || url.password) fail(id, "source must be a direct government PDF");
    const editions = [...decodeURIComponent(url.pathname).matchAll(/\b(?:FY|PB)[\s_-]*(20\d{2}|\d{2})(?!\d)/gi)].map(match => match[1].length === 2 ? 2000 + Number(match[1]) : Number(match[1]));
    if (!editions.length || editions.some(edition => edition !== row.sourceEdition)) fail(id, "source edition disagrees with the government document");
    if (row.pageNumber !== null && (!Number.isInteger(row.pageNumber) || row.pageNumber < 1)) fail(id, "invalid PDF page");
    if (url.hash && url.hash !== `#page=${row.pageNumber}`) fail(id, "PDF fragment disagrees with its page");

    if (row.factId === null) {
      const reviewed = historical.get(id);
      if (!reviewed) fail(id, "published narrative receipt is missing");
      for (const key of ["slug", "sourceEdition", "officialUrl", "pageNumber", "locator", "excerpt"] as const) {
        if (row[key] !== reviewed[key]) fail(id, "historical source identity differs from the reviewed import");
      }
      if (!row.association.includes(`PB${row.sourceEdition}`)) fail(id, "historical evidence must state its source edition");
      // These six rows intentionally lack receipts; never manufacture a link.
      continue;
    }
    if (historical.has(id)) fail(id, "historical evidence has no published receipt");
    if (!row.slug || !/^[a-f0-9]{16}$/.test(row.factId) || facts.has(row.factId)) fail(id, "missing or duplicate published receipt identity");
    facts.add(row.factId);
    const matches = getProgramDetails(row.slug).narratives.filter(narrative => narrative.fact_id === row.factId);
    if (matches.length !== 1) fail(id, "receipt is not a narrative of this exact program");
    const narrative = matches[0];
    if (!normalize(narrative.body).includes(normalize(row.excerpt))) fail(id, "reviewed excerpt is absent from its narrative");
    const citation = getCitation(row.factId);
    if (citation?.kind !== "jbook_narrative") fail(id, "published narrative receipt is missing");
    if (citation.official_url !== row.officialUrl || citation.page_number !== row.pageNumber || citation.xml_path !== row.locator || narrative.xml_path !== row.locator) fail(id, "receipt URL, page or XML identity differs from the reviewed evidence");
    const prefix = row.factId.slice(0, 2);
    if (!shards.has(prefix)) shards.set(prefix, getShard(prefix));
    if (!isDeepStrictEqual(shards.get(prefix)?.[row.factId], citation)) fail(id, "published receipt is missing or changed in its citation shard");
  }
}

let cached: F15RelatedProgram[] | null = null;

/** Compact, separately cited context. No monetary values or full passages ship. */
export function getF15RelatedPrograms(): F15RelatedProgram[] {
  if (cached) return cached;
  const rows: F15RelatedProgram[] = [...seed].sort((a, b) => b.sourceEdition - a.sourceEdition || a.title.localeCompare(b.title) || a.identifier.localeCompare(b.identifier));
  validateF15RelatedPrograms(rows);
  cached = rows;
  return cached;
}
