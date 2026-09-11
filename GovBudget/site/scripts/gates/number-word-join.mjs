/**
 * number-word-join.mjs — gate 2 leg (nw): a number glued to the word after it.
 *
 * THE DEFECT (ROADMAP #106). /methodology/ rendered "plus 553whose cited
 * record", "ingested for 1,936of them" and "(240at high confidence)"; nine
 * /agency/ pages rendered "OSD's 128programs carry". The JSX source had every
 * space: Next 16's Turbopack transform drops the leading space of a
 * multi-line JSX text run that carries an HTML entity. jsx-glue.mjs models
 * that at the source; this leg is the built-HTML half — the one that catches
 * the species whatever compiler quirk produces it next, on every page,
 * including prose no source rule reasons about.
 *
 * THE UNIT OF SCAN is a React TEXT RUN: the adjacent text children of one
 * element, concatenated. React separates adjacent text children with a
 * `<!-- -->` comment, node-html-parser keeps them as separate nodes, and the
 * glue lives precisely across that boundary ("553" + "whose cited …") — so a
 * per-text-node scan cannot see it, and a whole-page-text scan would glue
 * unrelated numbers from sibling elements (`<li>2023</li><li>workbook</li>`)
 * into a phantom match. An element child ends a run: `<b>553</b>whose` is a
 * layout question, not this leg's.
 *
 * WHAT IS NOT A DEFECT — measured against an 8,368-page build (2026-09-10:
 * every digit→letter token in every text run was tabulated before this regex
 * was written, then re-run with it; the survivors were exactly the 50 sites
 * in four families the sweep then fixed or marked):
 *   - exempt subtrees: quoted source prose whose notation is the source's
 *     (source-text-kinds.mjs sourceNotation — J-book narrative
 *     "$1.594million", LDA filing free text "H.R. 7586American Families
 *     First Act"), and official titles ([data-program-name] — "2112:
 *     Lightweight 155mm Howitzer"). The site does not own their typography;
 *     reformatting a quotation misquotes it;
 *   - ordinals: 21st, 3rd, 118th — the only number+lowercase-word tokens the
 *     site itself authors;
 *   - hex identifiers: fact ids (ae4f1bee), colour hashes (#dc8ba5a6), UUIDs
 *     (5f29754f-87fc-…) — a token of ≥ 8 characters made only of [0-9a-f-].
 *     Blind spot, accepted: an 8+-letter a–f-only word glued to a number;
 *   - L3Harris — the corpus's one letter-digit-Word proper noun;
 *   - structurally: one letter after a number is a code, not a word
 *     (0605230F, 5G, 1990s, $20.8B, C-130Js) — a word is ≥ 2 lowercase
 *     letters, or a capital followed by ≥ 2 lowercase ("7President's").
 *   Units (24hr, 10am, 5in) are NOT allowed: none is site-authored today, and
 *   "in" would mask "1,936in the corpus". A future one is written "24 hr" or
 *   added here with a dated measurement — never absorbed silently.
 *
 * Export: findNumberWordJoins(root) → { hits: [{ token, snippet }], runs, twins }
 *   `twins` counts runs carrying a "number word" pair with its space intact —
 *   the leg's non-vacuity signal (render-static.mjs holds the floor).
 */

import { exemptFromNotationSweep } from "./source-text-kinds.mjs";

/**
 * A number (553 / 1,936 / 1.594 / the "2023" of PB2023) immediately followed
 * by a prose word. The lookbehind stops a match starting mid-number; the
 * lookahead stops one ending mid-token (so "00aeb18d" never yields "00aeb").
 */
export const NUMBER_WORD_JOIN_RE =
  /(?<![\d.,])(\d[\d,]*(?:\.\d+)?)((?:[a-z]{2,}|[A-Z][a-z]{2,})(?:['’][a-z]+)?)(?![A-Za-z0-9])/g;

const ORDINAL_RE = /^\d[\d,]*(?:st|nd|rd|th)$/;
const HEX_TOKEN_RE = /^#?[0-9a-f]+(?:-[0-9a-f]+)*$/;
const HEX_MIN_LENGTH = 8;
const PROPER_NOUN_RE = /^L3Harris/;
/** A "number word" pair with its space — the shape the defect breaks. */
const NUMBER_SPACE_WORD_RE = /\d[\d,]*(?:\.\d+)?\s+[a-z]{2,}/;
/** Never rendered as prose. <head> for parity with leg (b); <svg> IS scanned. */
const NON_CONTENT_TAGS = new Set(["script", "style", "noscript", "template", "head"]);
const TOKEN_CHAR_RE = /[0-9A-Za-z#-]/;

/** The maximal [0-9A-Za-z#-] token around a match — what a reader sees as one word. */
function tokenAround(run, index, length) {
  let s = index;
  let e = index + length;
  while (s > 0 && TOKEN_CHAR_RE.test(run[s - 1])) s -= 1;
  while (e < run.length && TOKEN_CHAR_RE.test(run[e])) e += 1;
  return run.slice(s, e);
}

/** True when the glued token is one of the measured deliberate shapes. */
export function isDeliberateJoin(token, whole = token) {
  if (ORDINAL_RE.test(token)) return true;
  if (whole.length >= HEX_MIN_LENGTH && HEX_TOKEN_RE.test(whole)) return true;
  if (PROPER_NOUN_RE.test(whole)) return true;
  return false;
}

/** Every number/word join in one text run, minus the deliberate ones. */
export function joinsInRun(run) {
  const hits = [];
  for (const m of run.matchAll(NUMBER_WORD_JOIN_RE)) {
    const token = m[0];
    const whole = tokenAround(run, m.index, token.length);
    if (isDeliberateJoin(token, whole)) continue;
    hits.push({
      token,
      snippet: run
        .slice(Math.max(0, m.index - 45), m.index + token.length + 45)
        .replace(/\s+/g, " ")
        .trim(),
    });
  }
  return hits;
}

/**
 * Walk a parsed page (node-html-parser root, parsed with comment:false) and
 * scan every React text run.
 */
export function findNumberWordJoins(root) {
  const hits = [];
  let runs = 0;
  let twins = 0;

  const visit = (el) => {
    const tag = el.tagName ? el.tagName.toLowerCase() : "";
    if (NON_CONTENT_TAGS.has(tag)) return;
    if (el.getAttribute) {
      if (exemptFromNotationSweep(el.getAttribute("data-source-text"))) return;
      if (el.getAttribute("data-program-name") != null) return;
    }
    let run = "";
    const flush = () => {
      if (run === "") return;
      runs += 1;
      if (NUMBER_SPACE_WORD_RE.test(run)) twins += 1;
      for (const h of joinsInRun(run)) hits.push(h);
      run = "";
    };
    for (const child of el.childNodes || []) {
      if (child.nodeType === 3) {
        run += child.text || "";
      } else if (child.nodeType === 1) {
        flush();
        visit(child);
      }
      // Anything else (a comment node, if the parser kept one) is exactly the
      // boundary the defect hides behind — it neither ends nor joins the run.
    }
    flush();
  };

  visit(root);
  return { hits, runs, twins };
}
