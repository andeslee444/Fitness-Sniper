/**
 * gate — copy_gate (the voice, on every built page)
 *
 * docs/superpowers/VOICE.md is the house style; src/lib/copy.ts is where
 * authored copy lives; this gate is what makes the voice a SYSTEM rather than
 * one good rewrite. Nine independent critics read the site's prose as "model
 * prose" — imperative triplets, slogan headlines, "a different way into",
 * "follow every figure to its source" — and every one of those patterns is a
 * regex below. A future page written in the old voice fails here.
 *
 * What is scanned: the visible text nodes of every built page in the sample,
 * OUTSIDE <script>, <style>, <noscript>, <svg>, and every element that carries
 * cited or data-bound text — [data-source-text], [data-narrative],
 * [data-dossier], [data-prose-cite], [data-cite-fact-id], [data-amount],
 * [data-what-source], [data-copy-slot="data"], [data-absence] — because those
 * say what a number means and are read-only to the copy system. Breadcrumb
 * navs and <title> lockups are read by their own legs.
 *
 * Sample: every non-templated route, plus a bounded sample of each templated
 * route family (/program/, /company/, /filing/, /district/, /agency/) — a
 * template is proven by its instances, not by all 8,400 of them.
 *
 * Legs (each reports page · leg · snippet; PASS only at zero hits):
 *  1  invitation verb at the head of a sentence ("Explore …", "Discover …")
 *  2  "dive" constructions, "beneath the surface", "at a glance", "in one place"
 *  3  three consecutive sentences of ≤ 7 words (the tricolon)
 *  5  two consecutive sentences of ≤ 3 words (the fragment stack)
 *  6  "not just X — Y"
 *  7  "every … to its source", "follow every …", "follow the money"
 *  8  "a different way into", "a window into", "a new lens"
 *  9  marketing adjectives (seamless, powerful, comprehensive, robust, …)
 * 10  filler intensifiers (simply, just, easily, truly, very, …)
 * 11  marketing-deck arcs ("From X to Y.", "one place", "whether you're …")
 * 12  stat synonyms (stats, data points, metrics, insights, KPIs)
 * 13  em-dash pile-ups and sentence-final dashes
 * 14  question headings and colon-hook headings (h1/h2/h3)
 * 15  arrows inside headings; arrows not at the end of a link
 * 16  second person in headings, ledes, decks, captions and meta descriptions
 * 18  pointer verbs (click, tap, hit)
 * 21  bare "family" without its qualifier
 * 23  the serial comma
 * 29  Title Case h2/h3 (proper nouns and document names allowlisted)
 * 30  ellipsis or exclamation in a heading
 * 31  exposed enums (snake_case), "fact_id", "trajectory mart", "workbook-tier"
 * 36  a second spelling of a fixed action ("Read the source passage", …)
 * 38  program meta title shape "{title} ({PE|BLI} {code}) · {org}" and length
 *
 * Allowlist: copy-allowlist.json, {page|"*", leg, text, reason}; entries that
 * match nothing are stale and fail (same hygiene as the tokens gate).
 *
 * Export: runCopyGate() → { pass, errors, notes }
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { parse } from "node-html-parser";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(__dirname, "..", "..");
const outDir = path.resolve(siteRoot, "out");
const ALLOWLIST_PATH = path.join(__dirname, "copy-allowlist.json");

const TEMPLATED = ["program", "company", "filing", "district", "agency", "fact"];
const SAMPLE_PER_TEMPLATE = 25;
const SKIP_SELECTOR = [
  "script", "style", "noscript", "svg", "code", "kbd", "pre", "time", "option", "td", "dd",
  // cited / data-bound text — says what a number means; read-only to the copy system
  "[data-source-text]", "[data-narrative]", "[data-dossier]", "[data-prose-cite]", "[data-cite-fact-id]", "[data-amount]",
  "[data-what-source]", "[data-copy-slot=\"data\"]", "[data-absence]", "[data-stat]", "[data-testid=\"hero-scope-qualifier\"]",
  "[data-testid^=\"answer-\"]", "[data-program-name]",
  // entity names rendered as links, lists and headings on templated pages
  "a[href^=\"/program/\"]", "a[href^=\"/company/\"]", "a[href^=\"/filing/\"]", "a[href^=\"/agency/\"]", "a[href^=\"/district/\"]", "a[href^=\"/fact/\"]",
  "nav[aria-label=\"Breadcrumb\"]", "[aria-label=\"Breadcrumb\"]",
  // LDA filing text: activity descriptions and mention contexts are the filing's own words
  ".whitespace-pre-wrap", "#mentions p.text-muted-foreground", "[data-matched-terms]", "[data-evidence-kind]",
].join(", ");
/** On templated routes the h1 is the entity's own name (a company, a filing, a district). */
const TEMPLATED_H1_SKIP = true;
/** Reference-page body prose (methodology, coverage, about, glossary): the tells still apply; the style legs (10, 12, 23, 31) do not. */
const DOC_PROSE = "[data-doc-prose]";
const STYLE_LEGS = new Set([10, 12, 23, 31]);

/** Dataset identifiers (site_meta.datasets keys) are data, not jargon — leg 31 ignores them. */
const DATASET_ID_RE = (() => {
  try {
    const meta = JSON.parse(fs.readFileSync(path.resolve(siteRoot, "..", "data", "site", "json", "site_meta.json"), "utf8"));
    const ids = Object.keys(meta.datasets ?? {}).concat(["citations", "program_details", "entity_details", "workbook_cells", "cite_shards"]);
    return new RegExp(`\\b(${ids.map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})(_\\w+)?\\b`, "g");
  } catch {
    return /$^/g;
  }
})();

/** Proper nouns / document names that legitimately carry Title Case or a banned token. */
const PROPER = new Set([
  "Fiscal Receipts", "Budget Justification PDF", "Budget Workbook", "Derived Figure", "USAspending Query", "State Open Data Query", "State Source File", "J-book Narrative",
  "DoD Contract Announcement", "LDA Lobbying Filing", "Virginia Class Submarine", "Eagle II", "Strike Eagle", "President's Budget", "Base Request",
]);

const LEGS = [
  { n: 1, re: /(^|[.!?]\s+)(Explore|Discover|Unlock|Dive|Delve|Uncover|Unleash|Empower|Meet|Journey|Embark|Navigate|Experience|Imagine|Unpack|Harness|Leverage)\b/, label: "invitation verb at sentence head" },
  { n: 2, re: /\b(deep[- ]dive|dive (in|into)|a (closer|deeper) look (at|into)|under the hood|beneath the surface|behind the (numbers|scenes|curtain)|at a glance|in one place|at your fingertips|the story (behind|of)|stories behind)\b/i, label: "dive / glance / one-place construction" },
  { n: 6, re: /\bnot (just|only|merely|simply)\b[^.]{0,60}(—|–|\bbut\b)/i, label: "\"not just X — Y\"" },
  { n: 7, re: /(\bevery\b[^.]{0,60}\bto (its|their|the) (source|origin|receipt)s?\b|\bfollow (every|each|all) \w+|\bfollow the money\b)/i, label: "\"every … to its source\" / \"follow the money\"" },
  { n: 8, re: /(\ba (different|new|better|fresh|smarter|simpler|clearer) (way|lens|window|look|take|path|door|angle|approach)\b|\b(way|window|door|gateway|lens) into\b)/i, label: "\"a different way into\"" },
  { n: 9, re: /\b(seamless(ly)?|powerful(ly)?|comprehensive(ly)?|robust|cutting[- ]edge|state[- ]of[- ]the[- ]art|intuitive(ly)?|effortless(ly)?|beautiful(ly)?|elegant(ly)?|innovative|unprecedented|game[- ]chang\w*|holistic|actionable|world[- ]class|best[- ]in[- ]class|next[- ]generation|revolutionary|frictionless|delightful|vibrant|curated experience|empower\w*|transformative)\b/i, label: "marketing adjective" },
  { n: 10, re: /\b(simply|easily|quickly|instantly|effortlessly|truly|really|incredibly|remarkably)\b/i, label: "filler intensifier" },
  { n: 11, re: /(^From [^.]{3,40} to [^.]{3,40}[.,]|\b(one|a) (single )?(place|stop|source of truth)\b|\bwhether you('re| are)\b)/i, label: "marketing-deck arc" },
  { n: 12, re: /\b(stats?|data ?points?|metrics?|insights?|KPIs?|numbers that matter)\b/i, label: "stat synonym" },
  { n: 13, re: /—[^.!?]*—/, label: "em-dash pile-up" },
  { n: 18, re: /\b(click|clicks|clicking|tap|taps|hit)\b/i, label: "pointer verb" },
  { n: 21, re: /(?<!corporate |aircraft |exhibit |contractor |program |lineage |F-15 |Eagle |account |product |company |parent |budget |missile |ship |vehicle |weapon |submarine |recipient |registry |merged |curated |aircraft's |program's |the )\bfamil(y|ies)\b(?! of | funding| name| register)/i, label: "bare \"family\" without its qualifier (headings and slots)", headline: true },
  { n: 23, re: /\b\w+, \w+(?: \w+)?, and \w+\b/, label: "serial comma" },
  { n: 31, re: /(\b[a-z]+_[a-z_]+\b|\bfact[_ ]?id\b|\btrajectory mart\b|\bworkbook-tier\b)/i, label: "exposed enum / internal jargon", exempt: /\bfact ids?\b/i },
  { n: 36, re: /(read the source passage|share this view|open official document|explore in 3d|visual field guide|follow the money|inspect source record)/i, label: "second spelling of a fixed action" },
];

/** Sentences of a text: split on terminal punctuation followed by space. */
function sentences(text) {
  return text.split(/(?<=[.!?])\s+/).map((s) => s.trim()).filter(Boolean);
}
const words = (s) => s.replace(/[.!?]+$/, "").split(/\s+/).filter(Boolean).length;

function sampleFiles() {
  const files = [];
  const perTemplate = Object.fromEntries(TEMPLATED.map((t) => [t, 0]));
  const walk = (dir, rel) => {
    for (const name of fs.readdirSync(dir).sort()) {
      const full = path.join(dir, name);
      const relPath = rel ? `${rel}/${name}` : name;
      if (fs.statSync(full).isDirectory()) {
        if (name === "_next" || name === "pagefind" || name === "pdfs" || name === "og") continue;
        walk(full, relPath);
      } else if (name === "index.html") {
        const top = relPath.split("/")[0];
        if (TEMPLATED.includes(top) && relPath.split("/").length > 2) {
          if (perTemplate[top] >= SAMPLE_PER_TEMPLATE) continue;
          perTemplate[top] += 1;
        }
        files.push({ full, route: "/" + relPath.replace(/index\.html$/, "") });
      }
    }
  };
  walk(outDir, "");
  return files;
}

export async function runCopyGate() {
  const errors = [];
  const notes = [];
  if (!fs.existsSync(outDir)) {
    errors.push("copy_gate: out/ not found — build first");
    return { pass: false, errors, notes };
  }
  let allow = [];
  if (fs.existsSync(ALLOWLIST_PATH)) {
    try {
      allow = JSON.parse(fs.readFileSync(ALLOWLIST_PATH, "utf8"));
    } catch (e) {
      errors.push(`copy_gate: copy-allowlist.json unreadable — ${e.message}`);
    }
  }
  const allowUsed = new Map(allow.map((e, i) => [i, 0]));
  const allowed = (route, leg, text) => {
    for (let i = 0; i < allow.length; i++) {
      const e = allow[i];
      if (!e.reason || String(e.reason).length < 12) continue;
      if ((e.page === "*" || e.page === route) && e.leg === leg && text.includes(e.text)) {
        allowUsed.set(i, allowUsed.get(i) + 1);
        return true;
      }
    }
    return false;
  };

  const files = sampleFiles();
  const hits = [];
  const hit = (route, n, label, snippet) => {
    const s = snippet.replace(/\s+/g, " ").trim().slice(0, 140);
    if (allowed(route, n, s)) return;
    hits.push({ route, n, label, s });
  };

  let textNodes = 0;
  for (const { full, route } of files) {
    const html = fs.readFileSync(full, "utf8");
    const root = parse(html, { blockTextElements: { script: true, style: true, noscript: true } });
    // strip skipped subtrees
    for (const el of root.querySelectorAll(SKIP_SELECTOR)) el.remove();
    if (TEMPLATED_H1_SKIP && TEMPLATED.some((t) => route.startsWith(`/${t}/`) && route.split("/").length > 3)) {
      for (const el of root.querySelectorAll("h1")) el.remove();
    }

    // ── text-node legs ──
    const texts = [];
    const decode = (raw) => raw.replace(/&amp;/g, "&").replace(/&#x27;|&#39;/g, "'").replace(/&quot;/g, '"').replace(/&nbsp;/g, " ").replace(/\s+/g, " ").trim();
    const walkText = (node, inDoc) => {
      for (const child of node.childNodes) {
        if (child.nodeType === 3) {
          const t = decode(child.rawText);
          if (t.length > 1) texts.push({ t, parent: node, inDoc });
        } else if (child.nodeType === 1) walkText(child, inDoc || child.getAttribute("data-doc-prose") != null);
      }
    };
    const body = root.querySelector("body") ?? root;
    walkText(body, false);
    textNodes += texts.length;

    for (const { t, parent, inDoc } of texts) {
      const ptag = parent.tagName?.toLowerCase();
      const pslot = parent.getAttribute?.("data-copy-slot") ?? "";
      const headline = ["h1", "h2", "h3"].includes(ptag) || ["h1", "h2", "h3", "eyebrow", "lede", "deck", "caption"].includes(pslot);
      for (const leg of LEGS) {
        if (inDoc && STYLE_LEGS.has(leg.n)) continue;
        if (leg.headline && !headline) continue;
        let probe = t;
        if (leg.exempt) probe = probe.replace(leg.exempt, "");
        if (leg.n === 31) probe = probe.replace(DATASET_ID_RE, "");
        const m = leg.re.exec(probe);
        if (m) hit(route, leg.n, leg.label, t);
      }
      // 3: tricolon — three consecutive sentences of ≤ 7 words
      const ss = sentences(t);
      for (let i = 0; i + 2 < ss.length; i++) {
        if (words(ss[i]) <= 7 && words(ss[i + 1]) <= 7 && words(ss[i + 2]) <= 7 && /[.!?]$/.test(ss[i]) && /[.!?]$/.test(ss[i + 1])) {
          hit(route, 3, "three short sentences in a row (the tricolon)", `${ss[i]} ${ss[i + 1]} ${ss[i + 2]}`);
          break;
        }
      }
      // 5: fragment stack — two consecutive sentences of ≤ 3 words
      for (let i = 0; i + 1 < ss.length; i++) {
        const caps = (x) => x === x.toUpperCase();
        if (words(ss[i]) <= 3 && words(ss[i + 1]) <= 3 && /\.$/.test(ss[i]) && /\.$/.test(ss[i + 1]) && /^[A-Z]/.test(ss[i]) && /^[A-Z]/.test(ss[i + 1]) && !caps(ss[i]) && !caps(ss[i + 1])) {
          hit(route, 5, "fragment stack", `${ss[i]} ${ss[i + 1]}`);
          break;
        }
      }
      // 16: second person where the reader is not being addressed by a control
      const tag = parent.tagName?.toLowerCase();
      const slot = parent.getAttribute?.("data-copy-slot") ?? "";
      const secondPersonSlot = ["h1", "h2", "h3"].includes(tag) || ["h1", "h2", "eyebrow", "lede", "deck", "caption", "meta"].includes(slot);
      if (secondPersonSlot && /\byou(r|rs|rself)?\b/i.test(t)) hit(route, 16, "second person in a heading / lede / deck / caption", t);
    }

    // 13b: a sentence-final dash, judged on the block's whole text (a text node that ends in a dash because a link follows is not one)
    for (const block of root.querySelectorAll("p, li, figcaption, h1, h2, h3, dt")) {
      const t = decode(block.text);
      if (/\s—\s*$/.test(t)) hit(route, 13, "sentence-final dash", t);
    }

    // ── heading legs (14, 15, 29, 30) ──
    for (const h of root.querySelectorAll("h1, h2, h3")) {
      const t = h.text.replace(/\s+/g, " ").trim();
      if (!t) continue;
      if (/\?\s*$/.test(t)) hit(route, 14, "question heading", t);
      if (/^[^:]{2,40}:\s+[A-Z]/.test(t)) hit(route, 14, "colon-hook heading", t);
      if (/[→›»]/.test(t)) hit(route, 15, "arrow inside a heading", t);
      if (/(\.\.\.|…|!)/.test(t)) hit(route, 30, "ellipsis or exclamation in a heading", t);
      if (h.tagName.toLowerCase() !== "h1" && /^(?:[A-Z][a-z]+ ){1,4}[A-Z][a-z]+$/.test(t) && !PROPER.has(t) && !h.closest?.("[data-copy-slot=\"data\"]")) {
        hit(route, 29, "Title Case h2/h3", t);
      }
    }
    // 15b: arrows not at the end of a link
    for (const a of root.querySelectorAll("a")) {
      const t = a.text.replace(/\s+/g, " ").trim();
      if (/[→›»](?!\s*$)/.test(t)) hit(route, 15, "arrow not at the end of a link", t);
    }
    // 16b: meta description (non-templated routes; templated metas carry entity names)
    const templated = TEMPLATED.some((t) => route.startsWith(`/${t}/`) && route.split("/").length > 3);
    const meta = root.querySelector('meta[name="description"]')?.getAttribute("content") ?? "";
    if (!templated) {
      if (/\byou(r|rs|rself)?\b/i.test(meta)) hit(route, 16, "second person in the meta description", meta);
      for (const leg of LEGS) if ([1, 2, 7, 8, 9, 11].includes(leg.n) && leg.re.test(meta)) hit(route, leg.n, `${leg.label} (meta description)`, meta);
    }

    // 38: program meta title shape
    if (/^\/program\/[^/]+\/$/.test(route)) {
      const title = (root.querySelector("title")?.text ?? "").trim();
      const before = title.replace(/\s*\|\s*Fiscal Receipts$/, "");
      if (!/^.+ \((PE|BLI) [A-Z0-9-]+\) · .+$/.test(before)) hit(route, 38, "program meta title is not \"{title} ({PE|BLI} {code}) · {org}\"", title);
      else if (before.length > 60) hit(route, 38, `program meta title is ${before.length} chars (max 60)`, title);
    }
  }

  // COPY_ALLOWLIST_EMIT=1: freeze what remains as shrink-only debt (the ladder/tokens convention)
  if (process.env.COPY_ALLOWLIST_EMIT === "1") {
    const kept = allow.filter((e, i) => allowUsed.get(i) > 0);
    const seen = new Set(kept.map((e) => `${e.page}\u0000${e.leg}\u0000${e.text}`));
    const fresh = [];
    for (const h of hits) {
      const key = `${h.route}\u0000${h.n}\u0000${h.s}`;
      if (seen.has(key)) continue;
      seen.add(key);
      fresh.push({ page: h.route, leg: h.n, text: h.s, reason: "Copy debt frozen 2026-09-12 (iteration 8, VOICE.md landed): authored text that predates the voice. Shrink only — rewrite through src/lib/copy.ts, then delete this entry." });
    }
    fs.writeFileSync(ALLOWLIST_PATH, JSON.stringify([...kept, ...fresh], null, 2) + "\n");
    notes.push(`copy: COPY_ALLOWLIST_EMIT wrote ${kept.length + fresh.length} entries (${kept.length} kept, ${fresh.length} new)`);
    return { pass: true, errors, notes };
  }

  // report
  const byLeg = new Map();
  for (const h of hits) {
    const k = `${h.n} ${h.label}`;
    const v = byLeg.get(k) ?? { n: h.n, label: h.label, count: 0, examples: [] };
    v.count += 1;
    if (v.examples.length < 3) v.examples.push(`${h.route} · "${h.s}"`);
    byLeg.set(k, v);
  }
  for (const v of [...byLeg.values()].sort((a, b) => a.n - b.n)) {
    errors.push(`copy_gate leg ${v.n} — ${v.label}: ${v.count} hit(s) — ${v.examples.join(" | ")}${v.count > 3 ? " | …" : ""} (VOICE.md; fix the string in src/lib/copy.ts or the component, or add a {page, leg, text, reason} entry to copy-allowlist.json)`);
  }
  for (const [i, used] of allowUsed) {
    if (used === 0) errors.push(`copy_gate: copy-allowlist.json[${i}] (leg ${allow[i].leg} "${allow[i].text}") matched nothing — stale exemption, delete it`);
  }
  notes.push(`scanned ${files.length} pages (${TEMPLATED.map((t) => `${t} ×≤${SAMPLE_PER_TEMPLATE}`).join(", ")}), ${textNodes.toLocaleString("en-US")} text nodes`);
  if (hits.length === 0) notes.push(`copy: no model-prose pattern on any sampled page ✓ (allowlist: ${allow.length} entr${allow.length === 1 ? "y" : "ies"})`);
  return { pass: errors.length === 0, errors, notes };
}
