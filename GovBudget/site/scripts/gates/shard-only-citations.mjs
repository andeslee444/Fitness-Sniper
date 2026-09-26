/**
 * Gate 1 leg — shard-only citations (R-DEC-GATE-SHARDS, controller,
 * fix-round-5 rulings, 2026-09-26):
 *
 *   "A build-time gate leg fails any company or district page that ships a
 *    non-empty embedded citations object."
 *
 * WHY. /district/{code}/ (Task 28b, ruling R-28b-4) and, since decisions
 * fix round 5, /company/{slug}/ mount their <CitationPanelProvider> with an
 * EMPTY embedded slice (`citations={{}}`) plus the ids it may resolve
 * (`shardResolvableIds`); a click fetches the body from
 * /json/cite-shards/{fact_id[:2]}.json. That is the page-weight fix:
 * R-DEC-LDACITE's filing lists put 12 company pages over this gate's
 * 25,000-gzip ceiling while the slice was embedded (aerospace 41,964,
 * boeing 29,663 — decisions-fix4-export.md). Only vitest checked the embed,
 * against component renders; nothing read a BUILT page, so a revert would
 * have shown only as a weight failure on the heaviest page, or not at all
 * under the ceiling. This leg reads what ships.
 *
 * WHAT SHIPS. The provider is a client component, so Next serializes its
 * props into the React Server Components flight stream — in index.html as
 * `self.__next_f.push([1,"<chunk>"])` scripts (a prop may straddle chunks),
 * and again, raw, in the page directory's RSC payload files (index.txt,
 * __next._full.txt, __next.<segment>.__PAGE__.txt) that client-side
 * navigation fetches. A module row `<id>:I[…,"CitationPanelProvider"]`
 * names the component and the element `["$","$L<id>",<key>,{props}]` carries
 * `"citations":{…}`. A large object may be outlined as `"$<row>"`; the leg
 * follows the pointer and fails one it cannot resolve.
 *
 * WHAT FAILS, per page (every /company/{slug}/, every /district/{code}/, and
 * /district/):
 *   - the provider's `citations` prop, or ANY other `"citations":` map in
 *     the page's flight streams, has one key or more;
 *   - the HTML carries no readable provider payload (a page this leg cannot
 *     read cannot pass it), or a flight chunk will not decode;
 *   - the page directory has no index.html;
 *   - a page class is missing or empty (never a skip).
 * The footer's `"counts":{"citations":135737}` is a number, not a map.
 *
 * Measured 2026-09-26 on the integration build (git_head 0587f90f, built
 * 2026-09-25T23:59:41Z): every /district/ page passes; every /company/ page
 * fails — that build predates fix round 5's company-page change, and the
 * leg goes green on the chain-G rebuild. See decisions-fix6-site.md.
 */

import fs from "fs";
import path from "path";

const PROVIDER = "CitationPanelProvider";
/** How many failing pages an error lists (all are counted). */
const SAMPLE = 10;

/**
 * The flight stream a page's HTML carries: every `self.__next_f.push([1,…])`
 * string, decoded and joined in document order. `unreadable` counts chunks
 * that would not decode. Pure; exported for the unit tests.
 *
 * @param {string} html
 * @returns {{ stream: string, chunks: number, unreadable: number }}
 */
export function flightFromHtml(html) {
  const parts = [];
  let chunks = 0;
  let unreadable = 0;
  for (const m of String(html).matchAll(/self\.__next_f\.push\(\[1,("(?:[^"\\]|\\[\s\S])*")\]\)/g)) {
    chunks++;
    try {
      parts.push(JSON.parse(m[1]));
    } catch {
      unreadable++;
    }
  }
  return { stream: parts.join(""), chunks, unreadable };
}

/** The balanced JSON value (object or array) starting at s[i], or null. */
function balancedAt(s, i) {
  if (s[i] !== "{" && s[i] !== "[") return null;
  let depth = 0;
  let inStr = false;
  for (let j = i; j < s.length; j++) {
    const ch = s[j];
    if (inStr) {
      if (ch === "\\") j++;
      else if (ch === '"') inStr = false;
      continue;
    }
    if (ch === '"') inStr = true;
    else if (ch === "{" || ch === "[") depth++;
    else if (ch === "}" || ch === "]") {
      depth--;
      if (depth === 0) return s.slice(i, j + 1);
    }
  }
  return null;
}

/** A row's JSON value by id (`<id>:{…}` / `<id>:[…]` at a line start). */
function rowValue(stream, id) {
  const m = new RegExp(`(?:^|\\n)${id}:(?=[\\[{])`).exec(stream);
  if (!m) return undefined;
  const raw = balancedAt(stream, m.index + m[0].length);
  if (raw === null) return undefined;
  try {
    return JSON.parse(raw);
  } catch {
    return undefined;
  }
}

/**
 * A `citations` value as shipped: an object, or a `"$<row>"` pointer to one.
 * Returns { keys } or { error }.
 */
function readCitations(stream, value) {
  if (typeof value === "string") {
    const ref = /^\$([0-9a-f]+)$/.exec(value);
    const resolved = ref ? rowValue(stream, ref[1]) : undefined;
    if (resolved === undefined) {
      return { error: `passes citations as ${JSON.stringify(value)}, a pointer this leg cannot resolve to a row` };
    }
    value = resolved;
  }
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    return { error: `passes citations as ${JSON.stringify(value)?.slice(0, 40)}, not an object` };
  }
  return { keys: Object.keys(value) };
}

const describeKeys = (keys) =>
  `${keys.length.toLocaleString("en-US")} citation(s) (${keys.slice(0, 3).join(", ")}${keys.length > 3 ? ", …" : ""})`;

/**
 * Every embedded citations map one flight stream carries. `providers` is the
 * number of CitationPanelProvider elements read; `problems` lists each
 * provider whose `citations` is non-empty, missing or unreadable, and each
 * other non-empty `"citations":` map. Pure; exported for the unit tests.
 *
 * @param {string} stream
 * @returns {{ providers: number, problems: string[] }}
 */
export function embeddedCitationFindings(stream) {
  const s = String(stream ?? "");
  const problems = [];
  const ids = new Set();
  for (const m of s.matchAll(/(?:^|\n)([0-9a-f]+):I(\[[^\n]*\])/g)) {
    try {
      if (JSON.parse(m[2]).includes(PROVIDER)) ids.add(m[1]);
    } catch {
      // not a module row this leg reads
    }
  }
  let providers = 0;
  const providerSpans = [];
  for (const id of ids) {
    const re = new RegExp(`\\["\\$","\\$L${id}",(?:null|"(?:[^"\\\\]|\\\\.)*"),(?=\\{)`, "g");
    for (const m of s.matchAll(re)) {
      const at = m.index + m[0].length;
      const raw = balancedAt(s, at);
      let props;
      try {
        props = raw === null ? undefined : JSON.parse(raw);
      } catch {
        props = undefined;
      }
      if (props === undefined) {
        problems.push(`a ${PROVIDER} element whose props will not parse`);
        continue;
      }
      providers++;
      providerSpans.push([at, at + raw.length]);
      if (!Object.prototype.hasOwnProperty.call(props, "citations")) {
        problems.push(`a ${PROVIDER} element with no citations prop — the leg cannot prove it empty`);
        continue;
      }
      const r = readCitations(s, props.citations);
      if (r.error) problems.push(`${PROVIDER} ${r.error}`);
      else if (r.keys.length > 0) problems.push(`${PROVIDER} embeds ${describeKeys(r.keys)}`);
    }
  }
  // Any other component handed a citations MAP. (The provider's own key was
  // read above; the footer's count is a number and never matches `{`/`"$`.)
  for (const m of s.matchAll(/"citations":(?=[{"])/g)) {
    const at = m.index + m[0].length;
    if (providerSpans.some(([a, b]) => at > a && at < b)) continue;
    let value;
    if (s[at] === "{") {
      const raw = balancedAt(s, at);
      try {
        value = raw === null ? undefined : JSON.parse(raw);
      } catch {
        value = undefined;
      }
      if (value === undefined) {
        problems.push(`a "citations" map that will not parse`);
        continue;
      }
    } else {
      const str = /^"((?:[^"\\]|\\.)*)"/.exec(s.slice(at));
      if (!str || !/^\$[0-9a-f]+$/.test(str[1])) continue; // plain text, not a pointer
      value = str[1];
    }
    const r = readCitations(s, value);
    if (r.error) problems.push(`a component ${r.error}`);
    else if (r.keys.length > 0) problems.push(`a component is handed ${describeKeys(r.keys)}`);
  }
  return { providers, problems };
}

/**
 * The problems one built page ships: its index.html's flight stream (which
 * must carry a readable provider) and every RSC .txt payload beside it.
 *
 * @param {string} pageDir absolute path of the page's directory
 * @returns {string[]}
 */
function pageProblems(pageDir) {
  const out = [];
  const htmlPath = path.join(pageDir, "index.html");
  if (!fs.existsSync(htmlPath)) return ["has no index.html"];
  const { stream, chunks, unreadable } = flightFromHtml(fs.readFileSync(htmlPath, "utf8"));
  if (unreadable > 0) out.push(`index.html: ${unreadable} of ${chunks} flight chunk(s) will not decode`);
  const html = embeddedCitationFindings(stream);
  if (html.providers === 0) {
    out.push(`index.html: no ${PROVIDER} payload read — a page this leg cannot read cannot pass it`);
  }
  for (const p of html.problems) out.push(`index.html: ${p}`);
  for (const f of fs.readdirSync(pageDir).filter((n) => n.endsWith(".txt")).sort()) {
    const r = embeddedCitationFindings(fs.readFileSync(path.join(pageDir, f), "utf8"));
    for (const p of r.problems) out.push(`${f}: ${p}`);
  }
  return out;
}

/**
 * Gate 1 leg — see the file comment. Pushes to `errors` / `notes`.
 *
 * @param {{ outDir: string, errors: string[], notes: string[] }} args
 */
export function runShardOnlyCitationsLeg({ outDir, errors, notes }) {
  const tag = "shard-only citations (R-DEC-GATE-SHARDS)";
  const failing = [];
  const counts = {};
  for (const cls of ["company", "district"]) {
    const clsDir = path.join(outDir, cls);
    if (!fs.existsSync(clsDir)) {
      errors.push(`${tag}: out/${cls}/ missing — the /${cls}/*/ pages cannot be checked`);
      continue;
    }
    const slugs = fs
      .readdirSync(clsDir, { withFileTypes: true })
      .filter((e) => e.isDirectory())
      .map((e) => e.name)
      .sort();
    counts[cls] = slugs.length;
    if (slugs.length === 0) {
      errors.push(`${tag}: out/${cls}/ holds no /${cls}/*/ page — vacuous, never a skip`);
    }
    for (const slug of slugs) {
      const problems = pageProblems(path.join(clsDir, slug));
      if (problems.length) failing.push([`/${cls}/${slug}/`, problems]);
    }
  }
  if (fs.existsSync(path.join(outDir, "district"))) {
    const indexProblems = pageProblems(path.join(outDir, "district"));
    if (indexProblems.length) failing.push(["/district/", indexProblems]);
  }
  if (failing.length > 0) {
    errors.push(
      `${tag}: ${failing.length} page(s) ship a non-empty or unreadable embedded citations object — ` +
        `company and district pages mount CitationPanelProvider with citations={{}} and resolve ` +
        `bodies from /json/cite-shards/ (Task 28b, R-28b-4; decisions fix round 5). Embedding them ` +
        `is the page weight this leg exists to keep off`,
    );
    for (const [route, problems] of failing.slice(0, SAMPLE)) {
      errors.push(`${tag}: ${route} ${problems.slice(0, 3).join("; ")}${problems.length > 3 ? ` (+${problems.length - 3} more)` : ""}`);
    }
    if (failing.length > SAMPLE) errors.push(`${tag}: … and ${failing.length - SAMPLE} more page(s)`);
    return;
  }
  if (errors.some((e) => e.startsWith(tag))) return;
  notes.push(
    `${tag}: ${counts.company ?? 0} /company/*/ and ${counts.district ?? 0} /district/*/ pages ` +
      `(+ /district/) ship an empty embedded citations object, in the HTML and every RSC payload ✓`,
  );
}
