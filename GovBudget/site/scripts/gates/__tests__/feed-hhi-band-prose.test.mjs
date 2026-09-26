/**
 * Gate 8 leg (q): the pages that state the HHI bands IN PROSE state the ones
 * the badges use (decisions wave fix round 2, 2026-09-26).
 *
 * The site checker found /methodology/'s concentration passage rendering, at
 * e6bc28bb, "Bands follow the DOJ/FTC Horizontal Merger Guidelines
 * convention: below 1,000 is competitive, 1,000–1,800 is moderately
 * concentrated, and 1,800 or above is highly concentrated (1,800 is the
 * "highly concentrated" floor, not a near-monopoly line — four equal-share
 * firms alone produce exactly 1,800)." — false four ways against hhi-band.mjs
 * and #132 / R-DEC-132b: (a) 1,800 is moderately concentrated (the band
 * starts ABOVE it); (b) no vintage, and the retired 2010 title; (c)
 * "competitive", the retired word; (d) four equal shares give 2,500. The same
 * page also said "a competitive pooled figure" and, in the corrections table,
 * "DOJ/FTC bands" and "it is the highly concentrated floor" of 2,500. Nothing
 * read any of it: leg (l) reads /feed/, coverage.mjs the program badge, a
 * vitest the glossary. These tests pin the checks that now do, on every
 * defect above and on the true sentences that must keep passing.
 *
 * Run via `npm test` (vitest).
 */
import { describe, it, expect } from "vitest";
import { parse } from "node-html-parser";
import {
  bandProseSegments,
  hhiBandClaims,
  hhiBandStatementFindings,
  methodologyBandsBlockFindings,
  runBandProseLeg,
} from "../feed.mjs";
import { GLOSSARY } from "../../../src/lib/glossary.ts";
import { hhiScopeNote } from "../../../src/lib/hhi-scope-note.ts";

/** /methodology/ §4's concentration_shift passage as e6bc28bb renders it. */
const HEAD_BAND_SENTENCE =
  'Bands follow the DOJ/FTC Horizontal Merger Guidelines convention: below 1,000 is competitive, ' +
  "1,000–1,800 is moderately concentrated, and 1,800 or above is highly concentrated (1,800 is the " +
  '"highly concentrated" floor, not a near-monopoly line — four equal-share firms alone produce exactly 1,800).';
/** The paragraph after it (page.tsx:1805–1810 at e6bc28bb). */
const HEAD_POOLED_SENTENCE =
  "The two are legitimately different measures: a concentrated year can sit next to a competitive pooled figure.";
/** The corrections-table row's "Now" and "Why" cells at e6bc28bb. */
const HEAD_CORRECTION_NOW = "DOJ/FTC bands";
const HEAD_CORRECTION_WHY =
  "2,500 was labelled a near-monopoly; it is the “highly concentrated” floor, and four equal firms " +
  "produce exactly 2,500. A single year's concentration also now says so, because the pooled all-years " +
  "figure on the page it links to can legitimately differ.";
/** What the integration build (pre-#132, 2010 constants) rendered. */
const BUILD_2010_SENTENCE =
  "Bands follow the DOJ/FTC Horizontal Merger Guidelines convention: below 1,500 is competitive, " +
  "1,500–2,500 is moderately concentrated, and 2,500 or above is highly concentrated (2,500 is the " +
  '"highly concentrated" floor, not a near-monopoly line — four equal-share firms alone produce exactly 2,500).';

/** A true statement of the bands, in the shapes a rewrite is likely to take. */
const TRUE_BANDS =
  "Bands follow the 2023 Merger Guidelines of the Justice Department and the FTC: an HHI from 1,000 to " +
  "1,800 is moderately concentrated, and one above 1,800 is highly concentrated (1,800 itself is " +
  "moderately concentrated; four equal-share firms produce exactly 2,500). This site calls an HHI below " +
  "1,000 unconcentrated.";

const kinds = (text) =>
  hhiBandClaims(text)
    .filter((c) => !c.ok)
    .map((c) => c.kind);

describe("hhiBandStatementFindings — e6bc28bb's /methodology/ band sentence, four ways false", () => {
  const findings = hhiBandStatementFindings(HEAD_BAND_SENTENCE);

  it("(a) 1,800 is moderately concentrated: neither 'or above' nor 'the floor' holds", () => {
    expect(findings.some((f) => /"1,800 or above"/.test(f))).toBe(true);
    expect(findings.some((f) => /1,800 is the "highly concentrated" floor/.test(f))).toBe(true);
  });

  it("(b) names the agencies' bands with no vintage, and the retired 2010 title without its year", () => {
    expect(findings.some((f) => /without a vintage/.test(f) && /2023 Merger Guidelines/.test(f))).toBe(true);
    expect(findings.some((f) => /Horizontal Merger Guidelines/.test(f) && /2010/.test(f))).toBe(true);
  });

  it("(c) says 'competitive', the word R-DEC-132b retired", () => {
    expect(findings.some((f) => /"competitive"/.test(f) && /Unconcentrated/.test(f))).toBe(true);
  });

  it("(d) four equal shares give 2,500, not 1,800", () => {
    expect(findings.some((f) => /four equal-share firms/.test(f) && /2,500/.test(f))).toBe(true);
  });

  it("reports exactly those claims, and passes the one true one (1,000–1,800 moderately concentrated)", () => {
    expect(kinds(HEAD_BAND_SENTENCE).sort()).toEqual(
      ["competitive", "equal-shares", "floor", "or-above", "retired-title", "vintage"].sort(),
    );
    const moderate = hhiBandClaims(HEAD_BAND_SENTENCE).filter((c) => c.kind === "moderate-range");
    expect(moderate).toHaveLength(1);
    expect(moderate[0].ok).toBe(true);
  });
});

describe("hhiBandStatementFindings — the other stale sentences on e6bc28bb's /methodology/", () => {
  it("'a competitive pooled figure' (the paragraph after the band sentence)", () => {
    expect(kinds(HEAD_POOLED_SENTENCE)).toEqual(["competitive"]);
  });

  it("the corrections row: 'DOJ/FTC bands' has no year", () => {
    expect(kinds(HEAD_CORRECTION_NOW)).toEqual(["vintage"]);
  });

  it("a date is not a vintage: the year must be a guidelines edition's", () => {
    expect(kinds("DOJ/FTC bands, as applied on 2026-09-25.")).toEqual(["vintage"]);
    expect(kinds("DOJ/FTC bands (2023 Merger Guidelines).")).toEqual([]);
  });

  it("the corrections row: 2,500 is no longer the highly-concentrated floor; four equal firms DO give 2,500", () => {
    expect(kinds(HEAD_CORRECTION_WHY)).toEqual(["floor"]);
    const eq = hhiBandClaims(HEAD_CORRECTION_WHY).filter((c) => c.kind === "equal-shares");
    expect(eq).toHaveLength(1);
    expect(eq[0].ok).toBe(true);
  });

  it("the integration build's 2010 sentence fails on its thresholds as well", () => {
    expect(kinds(BUILD_2010_SENTENCE).sort()).toEqual(
      ["competitive", "floor", "moderate-range", "or-above", "retired-title", "vintage"].sort(),
    );
  });
});

/**
 * Fix round 3 (2026-09-26). The re-checker of b7eaf44b found leg (q) passing
 * a sentence that puts the 2023 thresholds under the 2010 edition's name —
 * a year was present, and each threshold matched hhiBand(), so every check
 * above was satisfied. The 2010 Horizontal Merger Guidelines' bands were
 * 1,500 and 2,500 (§5.3); 1,000 / 1,800 are the 2023 Merger Guidelines'
 * (§2.1, as the DOJ Antitrust Division's HHI page states them). Two rules
 * now bind an edition's name to its numbers, per sentence:
 *   edition-bands  a sentence naming the 2010 edition states that edition's
 *                  bands, 1,500 and 2,500, or is flagged;
 *   vintage        a sentence stating the current thresholds (1,000 / 1,800)
 *                  names 2023 or the DOJ page, or is flagged — naming another
 *                  edition (2010, 1992) is not naming theirs.
 */
const RECHECK_2010_SENTENCE =
  "Bands follow the 2010 DOJ/FTC Horizontal Merger Guidelines: below 1,000 is unconcentrated (this site's word), " +
  "1,000–1,800 is moderately concentrated, and above 1,800 is highly concentrated.";
/** The re-checker's second probe: another edition's year on the current thresholds. */
const RECHECK_1992_SENTENCE =
  "Bands follow the 1992 Merger Guidelines: 1,000–1,800 is moderately concentrated and above 1,800 is highly concentrated.";

describe("leg (q) fix round 3 — an edition's name binds that edition's numbers", () => {
  it("RED at b7eaf44b: the re-checker's 2010 sentence carrying the 2023 thresholds fails both ways", () => {
    const findings = hhiBandStatementFindings(RECHECK_2010_SENTENCE);
    expect(kinds(RECHECK_2010_SENTENCE).sort()).toEqual(["edition-bands", "vintage"]);
    expect(findings.some((f) => /2010/.test(f) && /1,500/.test(f) && /2,500/.test(f))).toBe(true);
    expect(findings.some((f) => /1,000 \/ 1,800/.test(f) && /2023/.test(f) && /DOJ/.test(f))).toBe(true);
  });

  it("RED at b7eaf44b: another edition's year (1992) on the current thresholds is not their vintage", () => {
    expect(kinds(RECHECK_1992_SENTENCE)).toEqual(["vintage"]);
    expect(hhiBandStatementFindings(RECHECK_1992_SENTENCE)[0]).toMatch(/1992/);
  });

  it("every way of naming the 2010 edition binds 1,500 and 2,500", () => {
    for (const s of [
      "Bands follow the 2010 Merger Guidelines: 1,000–1,800 is moderately concentrated.",
      "Under the Horizontal Merger Guidelines (2010), an HHI above 1,800 is highly concentrated.",
      "Under the Horizontal Merger Guidelines of 2010, an HHI above 1,800 is highly concentrated.",
      "The 2010 DOJ/FTC bands put moderately concentrated at 1,000 to 1,800.",
    ]) {
      expect(kinds(s), s).toContain("edition-bands");
      expect(kinds(s), s).toContain("vintage");
    }
    // Naming the edition without its numbers, or with only one of them.
    expect(kinds("The site's bands follow the 2010 Horizontal Merger Guidelines.")).toEqual(["edition-bands"]);
    expect(kinds("The 2010 guidelines' bands were replaced.")).toEqual(["edition-bands"]);
    expect(kinds("Under the 2010 Horizontal Merger Guidelines the highly concentrated line was 2,500.")).toEqual([
      "edition-bands",
    ]);
    expect(kinds("The site cites the 2010 edition of the Merger Guidelines.")).toEqual(["edition-bands"]);
    expect(kinds("The 2010 revision of the Horizontal Merger Guidelines set bands at 1,500 and 2,500.")).toEqual([]);
    // With its own numbers, but saying the site's bands follow it TODAY: false since #132.
    expect(kinds("Bands follow the 2010 Horizontal Merger Guidelines (1,500 and 2,500).")).toEqual(["edition-bands"]);
    expect(kinds("This site's bands use the 2010 DOJ/FTC thresholds, 1,500 and 2,500.")).toEqual(["edition-bands"]);
    expect(hhiBandStatementFindings("Bands follow the 2010 Horizontal Merger Guidelines (1,500 and 2,500).")[0]).toMatch(
      /present tense/,
    );
    // History, and a negation, are not that claim.
    expect(kinds("The site no longer follows the 2010 Horizontal Merger Guidelines' bands (1,500 and 2,500).")).toEqual([]);
    expect(kinds("Until 2026-09-25 the bands followed the 2010 Horizontal Merger Guidelines (1,500 and 2,500).")).toEqual([]);
  });

  it("a statement of 1,000 / 1,800 names 2023 or the DOJ page, whatever its shape", () => {
    expect(kinds("An HHI from 1,000 to 1,800 is moderately concentrated, and one above 1,800 is highly concentrated.")).toEqual([
      "vintage",
    ]);
    expect(kinds("The concentration bands sit at 1,000 and 1,800.")).toEqual(["vintage"]);
    expect(kinds("An index of 1,801 or above is highly concentrated.")).toEqual(["vintage"]);
    expect(kinds("The thresholds are 1,000 / 1,800 (2010 Horizontal Merger Guidelines).").sort()).toEqual([
      "edition-bands",
      "vintage",
    ]);
    // A below-1,000 statement neither naming 2023 nor saying the word is this site's.
    expect(kinds("An HHI below 1,000 is unconcentrated.")).toEqual(["vintage"]);
  });

  it("true statements of either edition keep passing", () => {
    for (const s of [
      "Per the DOJ Antitrust Division's HHI page, 1,000 to 1,800 is moderately concentrated and above 1,800 is highly concentrated.",
      "Per the Justice Department's HHI page, 1,000 to 1,800 is moderately concentrated.",
      "Merger Guidelines § 2.1 (2023): 1,000 to 1,800 is moderately concentrated, and above 1,800 is highly concentrated.",
      "The 2023 bands: 1,000 to 1,800 is moderately concentrated.",
      // Fix round 8 (R-DEC-LEGQ-b) moved "The 2023 Merger Guidelines' bands
      // (1,000 and 1,800) replaced the 2010 Horizontal Merger Guidelines'
      // (1,500 and 2,500)." out of this list: read by the nearest FOLLOWING
      // name, 1,000 / 1,800 belong to 2010, so it fails closed (fix-8 block).
      "Until 2026-09-25 this site used the 2010 Horizontal Merger Guidelines' bands, 1,500 and 2,500.",
      "In FY2010 the program's HHI of 2,100 was highly concentrated under the 2023 Merger Guidelines.",
      "This site calls an HHI below 1,000 unconcentrated.",
    ]) {
      expect(hhiBandStatementFindings(s), s).toEqual([]);
    }
  });

  it("the 2023 name does not rescue 2010's name on the wrong numbers", () => {
    const s = "The 2010 Horizontal Merger Guidelines' bands (1,000 and 1,800) were replaced by the 2023 Merger Guidelines.";
    expect(kinds(s)).toEqual(["edition-bands"]);
  });

  it("a fiscal year is not the edition: FY2010 and 2010 dollars name no guidelines", () => {
    expect(hhiBandStatementFindings("FY2010 obligations fell; the 2023 Merger Guidelines bands put 1,913 above 1,800, highly concentrated.")).toEqual([]);
  });

  it("runBandProseLeg fails /methodology/ carrying the re-checker's sentence, and names the page", () => {
    const errors = [];
    const page = `<main><div id="feed-concentration_shift"><p>${RECHECK_2010_SENTENCE}</p></div></main>`;
    const glossary = `<main><dl><dd>${GLOSSARY.find((e) => e.id === "hhi").definition}</dd></dl></main>`;
    const feed =
      '<main><section id="feed-concentration_shift"><p>Each card names its band under the 2023 Merger Guidelines: ' +
      "moderately concentrated from 1,000 to 1,800 and highly concentrated above 1,800.</p></section></main>";
    runBandProseLeg(errors, [], (route) =>
      parse({ "/methodology/": page, "/glossary/": glossary, "/feed/": feed }[route], { comment: false }),
    );
    expect(errors.some((e) => /^feed leg q \(\/methodology\/\): /.test(e) && /2010/.test(e) && /1,500/.test(e))).toBe(true);
    expect(errors.some((e) => /^feed leg q \(\/methodology\/\): /.test(e) && /1,000 \/ 1,800/.test(e))).toBe(true);
    // The passage also names the 2010 edition instead of the vintage.
    expect(errors.some((e) => /#feed-concentration_shift/.test(e) && /2023 Merger Guidelines/.test(e))).toBe(true);
    expect(errors.filter((e) => /\/glossary\/|\/feed\//.test(e))).toEqual([]);
  });
});

describe("hhiBandStatementFindings — true statements keep passing", () => {
  it("a true rewrite of the band sentence", () => {
    expect(hhiBandStatementFindings(TRUE_BANDS)).toEqual([]);
    const k = hhiBandClaims(TRUE_BANDS).map((c) => c.kind).sort();
    expect(k).toEqual(["below", "equal-shares", "high-line", "moderate-range", "vintage"].sort());
  });

  it("the glossary's HHI entry, as glossary.ts builds it", () => {
    const entry = GLOSSARY.find((e) => e.id === "hhi");
    expect(hhiBandStatementFindings(entry.definition)).toEqual([]);
    expect(hhiBandClaims(entry.definition).map((c) => c.kind).sort()).toEqual(
      ["below", "high-line", "moderate-range", "vintage"].sort(),
    );
  });

  it("every feed card scope note, in each band", () => {
    for (const v of [389.2, 999.4, 1000, 1800, 1800.4, 1913.4, 4401]) {
      const note = hhiScopeNote({ figure_units: "hhi", figure_value: v, fiscal_year: 2021 });
      expect(hhiBandStatementFindings(note.text), `HHI ${v}: ${note.text}`).toEqual([]);
    }
  });

  it("history stated as history: a year on the retired title, the old word in quotes", () => {
    const history =
      "Until 2026-09-25 the bands were the 2010 Horizontal Merger Guidelines' (1,500 and 2,500), " +
      "and an index below 1,500 was labelled “competitive”.";
    expect(hhiBandStatementFindings(history)).toEqual([]);
  });

  it("competition that is not about concentration is not this check's business", () => {
    expect(
      hhiBandStatementFindings("FPDS records offer counts and competition type; competitive awards are named."),
    ).toEqual([]);
  });

  it("whole points: 1,801 or above is the floor, and above 1,800 is the line", () => {
    expect(hhiBandStatementFindings("An HHI of 1,801 or above is highly concentrated under the 2023 Merger Guidelines.")).toEqual([]);
    expect(hhiBandStatementFindings("2023 Merger Guidelines bands: highly concentrated above 1,800.")).toEqual([]);
  });
});

describe("hhiBandStatementFindings — thresholds that are not hhi-band.mjs's fail", () => {
  it("a highly-concentrated line at 2,500", () => {
    expect(kinds("Under the 2023 Merger Guidelines, above 2,500 is highly concentrated.")).toEqual(["high-line"]);
    expect(kinds("2023 Merger Guidelines bands: highly concentrated above 2,500.")).toEqual(["high-line"]);
  });

  it("a moderate range of 1,500–2,500", () => {
    expect(kinds("Under the 2023 Merger Guidelines, 1,500 to 2,500 is moderately concentrated.")).toEqual([
      "moderate-range",
    ]);
    expect(kinds("2023 Merger Guidelines: moderately concentrated from 1,500 to 2,500.")).toEqual([
      "moderate-range",
    ]);
  });

  it("an unconcentrated band ending anywhere but 1,000", () => {
    expect(kinds("This site calls an HHI below 1,500 unconcentrated.")).toEqual(["below"]);
  });

  it("quotation marks around a band's name do not hide the claim", () => {
    expect(kinds('Under the 2023 Merger Guidelines, above 2,500 is "highly concentrated".')).toEqual(["high-line"]);
    expect(kinds('Under the 2023 Merger Guidelines, above 1,800 is “highly concentrated”.')).toEqual([]);
    expect(kinds('Under the 2023 Merger Guidelines, 1,500–2,500 is "moderately concentrated".')).toEqual([
      "moderate-range",
    ]);
  });

  it("a floor claim with no number to hold it to", () => {
    expect(kinds("It is the highly concentrated floor.")).toEqual(["floor"]);
  });

  it("equal shares other than four", () => {
    expect(kinds("Five equal-share firms produce exactly 2,000.")).toEqual([]);
    expect(kinds("Five equal-share firms produce exactly 2,500.")).toEqual(["equal-shares"]);
  });
});

describe("methodologyBandsBlockFindings — the passage that states a card's bands", () => {
  it("fails e6bc28bb's passage: no vintage, no 'unconcentrated', no attribution", () => {
    const f = methodologyBandsBlockFindings(`${HEAD_BAND_SENTENCE} ${HEAD_POOLED_SENTENCE}`);
    expect(f.some((x) => /2023 Merger Guidelines/.test(x))).toBe(true);
    expect(f.some((x) => /"unconcentrated"/.test(x))).toBe(true);
    expect(f.some((x) => /this site/.test(x))).toBe(true);
  });

  it("passes a true passage", () => {
    expect(methodologyBandsBlockFindings(`${TRUE_BANDS} ${HEAD_POOLED_SENTENCE.replace("competitive", "unconcentrated")}`)).toEqual([]);
  });

  it("fails a passage that names the bands but states none of their thresholds", () => {
    const f = methodologyBandsBlockFindings(
      "Bands follow the 2023 Merger Guidelines: moderately concentrated, highly concentrated, and — this site's label — unconcentrated.",
    );
    expect(f.some((x) => /moderately concentrated range/.test(x))).toBe(true);
    expect(f.some((x) => /highly concentrated line/.test(x))).toBe(true);
    expect(f.some((x) => /unconcentrated/.test(x) && /below/.test(x))).toBe(true);
  });

  it("fails a missing passage", () => {
    expect(methodologyBandsBlockFindings(null)).toEqual([expect.stringMatching(/no .*passage/)]);
  });
});

describe("bandProseSegments", () => {
  it("takes each outermost text block once: a list item with a paragraph inside is one segment", () => {
    const root = parse(
      "<main><p>One.</p><ul><li>Two <p>inner</p></li></ul><table><tr><td>A</td><td>B</td></tr></table></main>",
    );
    expect(bandProseSegments(root)).toEqual(["One.", "Two inner", "A", "B"]);
  });
});

describe("runBandProseLeg", () => {
  const methodologyHtml = (block, correctionNow, correctionWhy) =>
    `<main><div id="feed-concentration_shift"><h3>Award Concentration Shifts</h3><p>${block}</p></div>` +
    `<div data-historical-figures><table><tbody><tr><td>Concentration (HHI) wording</td>` +
    `<td>&ldquo;near-monopoly&rdquo;</td><td>${correctionNow}</td><td>${correctionWhy}</td></tr></tbody></table></div></main>`;
  const glossaryHtml = () =>
    `<main><dl><dt>HHI</dt><dd>${GLOSSARY.find((e) => e.id === "hhi").definition}</dd></dl></main>`;
  /** /feed/'s section sentence as feed/page.tsx builds it at e6bc28bb. */
  const FEED_SENTENCE =
    "Each card names its band under the 2023 Merger Guidelines: moderately concentrated from 1,000 to 1,800 " +
    "and highly concentrated above 1,800. Below 1,000 the card says unconcentrated, this site's label for that range.";
  const feedHtml = (sentence = FEED_SENTENCE) =>
    `<main><section id="feed-concentration_shift"><div><h2>Award Concentration Shifts</h2><p>${sentence}</p></div></section></main>`;
  const reader = (pages) => (route) => (route in pages ? parse(pages[route], { comment: false }) : null);

  it("fails e6bc28bb's /methodology/ on every stale clause, and names the page", () => {
    const errors = [];
    const notes = [];
    runBandProseLeg(
      errors,
      notes,
      reader({
        "/methodology/": methodologyHtml(
          `${HEAD_BAND_SENTENCE} ${HEAD_POOLED_SENTENCE}`,
          HEAD_CORRECTION_NOW,
          HEAD_CORRECTION_WHY,
        ),
        "/glossary/": glossaryHtml(),
        "/feed/": feedHtml(),
      }),
    );
    expect(errors.every((e) => e.startsWith("feed leg q"))).toBe(true);
    expect(errors.every((e) => /\/methodology\//.test(e))).toBe(true);
    for (const re of [/"1,800 or above"/, /without a vintage/, /"competitive"/, /four equal-share/, /DOJ\/FTC bands/, /2,500 is the "highly concentrated" floor/, /#feed-concentration_shift/]) {
      expect(errors.some((e) => re.test(e)), String(re)).toBe(true);
    }
  });

  it("passes true prose on every page", () => {
    const errors = [];
    const notes = [];
    runBandProseLeg(
      errors,
      notes,
      reader({
        "/methodology/": methodologyHtml(
          TRUE_BANDS,
          "2023 Merger Guidelines bands",
          "2,500 was labelled a near-monopoly; four equal firms produce exactly 2,500.",
        ),
        "/glossary/": glossaryHtml(),
        "/feed/": feedHtml(),
      }),
    );
    expect(errors).toEqual([]);
    expect(notes.some((n) => /^leg q: /.test(n) && /✓/.test(n))).toBe(true);
  });

  it("a page that is not built, or states no band at all, is an error, never a skip", () => {
    const errors = [];
    runBandProseLeg(errors, [], reader({ "/glossary/": "<main><p>No bands here.</p></main>" }));
    expect(errors.some((e) => /\/methodology\//.test(e) && /missing/.test(e))).toBe(true);
    expect(errors.some((e) => /\/feed\//.test(e) && /missing/.test(e))).toBe(true);
    expect(errors.some((e) => /\/glossary\//.test(e) && /vacuous/.test(e))).toBe(true);
  });

  it("a page that will not parse is an error that says so", () => {
    const errors = [];
    runBandProseLeg(errors, [], (route) => {
      if (route === "/glossary/") throw new Error("EACCES");
      return parse(route === "/feed/" ? feedHtml() : `<main><div id="feed-concentration_shift"><p>${TRUE_BANDS}</p></div></main>`);
    });
    expect(errors).toEqual([expect.stringMatching(/\/glossary\/ would not read or parse — EACCES/)]);
  });

  it("holds /feed/'s thresholds, which leg (l) reads only for words", () => {
    const errors = [];
    runBandProseLeg(
      errors,
      [],
      reader({
        "/methodology/": `<main><div id="feed-concentration_shift"><p>${TRUE_BANDS}</p></div></main>`,
        "/glossary/": glossaryHtml(),
        "/feed/": feedHtml(FEED_SENTENCE.replace("from 1,000 to 1,800", "from 1,500 to 2,500")),
      }),
    );
    expect(errors).toEqual([expect.stringMatching(/^feed leg q \(\/feed\/\): puts "moderately concentrated" at 1,500–2,500/)]);
  });

  it("a /methodology/ with no concentration_shift passage is an error", () => {
    const errors = [];
    runBandProseLeg(
      errors,
      [],
      reader({ "/methodology/": `<main><p>${TRUE_BANDS}</p></main>`, "/glossary/": glossaryHtml(), "/feed/": feedHtml() }),
    );
    expect(errors).toEqual([expect.stringMatching(/#feed-concentration_shift/)]);
  });
});

/**
 * Decisions wave fix round 4 (review, 2026-09-26). Fix round 3 bound one
 * direction: a sentence naming the 2010 edition states 2010's numbers. The
 * reviewer found the other direction open — hhiBandStatementFindings
 * returned [] for:
 *   "Bands follow the 2023 Merger Guidelines: 1,500 and 2,500."
 *   "Under the 2023 Merger Guidelines the bands sit at 1,500 and 2,500."
 *   "Under the 2023 Merger Guidelines, an HHI of 1,900 is moderately concentrated."
 * A sentence naming 2023 (or the DOJ page that states its bands) beside the
 * retired pair now fails unless it also states the current pair (a
 * comparison); and a point claim "an HHI of N is <band>" is banded with
 * hhiBand(N) — or, in a sentence naming only a retired edition, by that
 * edition's own bands.
 */
describe("leg (q) fix round 4 — the current edition's name binds the current numbers", () => {
  it("RED at 07f09f95: the 2023 name beside the retired 1,500 / 2,500 pair fails", () => {
    for (const s of [
      "Bands follow the 2023 Merger Guidelines: 1,500 and 2,500.",
      "Under the 2023 Merger Guidelines the bands sit at 1,500 and 2,500.",
      "Per the DOJ Antitrust Division's HHI page, the bands sit at 1,500 and 2,500.",
      "Merger Guidelines § 2.1 (2023) set the thresholds at 1,500 / 2,500.",
    ]) {
      expect(kinds(s), s).toContain("edition-bands");
      expect(hhiBandStatementFindings(s).some((f) => /1,500/.test(f) && /2,500/.test(f) && /2023/.test(f)), s).toBe(true);
    }
  });

  it("a comparison that states both pairs keeps passing", () => {
    // Fix round 8 (R-DEC-LEGQ-b): the two-edition form of this comparison
    // ("The 2023 Merger Guidelines' bands (1,000 and 1,800) replaced the 2010
    // Horizontal Merger Guidelines' (1,500 and 2,500).") now fails closed; a
    // sentence naming one edition is read as before.
    for (const s of [
      "The 2023 Merger Guidelines replaced 1,500 and 2,500 with 1,000 and 1,800.",
    ]) {
      expect(hhiBandStatementFindings(s), s).toEqual([]);
    }
  });

  it("RED at 07f09f95: a point claim 'an HHI of N is <band>' is banded by hhiBand(N)", () => {
    const s = "Under the 2023 Merger Guidelines, an HHI of 1,900 is moderately concentrated.";
    expect(kinds(s)).toEqual(["point"]);
    expect(hhiBandStatementFindings(s)[0]).toMatch(/1,900/);
    expect(hhiBandStatementFindings(s)[0]).toMatch(/highly concentrated/i);
    for (const bad of [
      "An HHI of 1,800 is highly concentrated.",
      "An HHI of 1,000 is unconcentrated.",
      "An HHI of 999 is moderately concentrated.",
      "The program's HHI of 2,159 is moderately concentrated.",
      "An index of 1,801 is moderately concentrated.",
      'An HHI of 1,200 reads as "highly concentrated".',
    ]) {
      expect(kinds(bad), bad).toContain("point");
    }
  });

  it("true point claims, and history, keep passing", () => {
    for (const s of [
      "An HHI of 1,800 is moderately concentrated.",
      "An HHI of 1,801 is highly concentrated.",
      "An HHI of 999 is unconcentrated, this site's word for it.",
      "The program's HHI of 2,159 is highly concentrated under the 2023 Merger Guidelines.",
      "In FY2010 the program's HHI of 2,100 was highly concentrated under the 2023 Merger Guidelines.",
      "Under the 2010 Horizontal Merger Guidelines (1,500 and 2,500) an HHI of 2,159 was moderately concentrated.",
    ]) {
      expect(hhiBandStatementFindings(s), s).toEqual([]);
    }
  });

  it("a point claim in a sentence naming only the 2010 edition is banded by 2010's bands", () => {
    // 2010 HMG § 5.3: moderately concentrated 1,500–2,500, highly above 2,500.
    expect(
      kinds("Under the 2010 Horizontal Merger Guidelines (1,500 and 2,500) an HHI of 2,159 is moderately concentrated."),
    ).toEqual([]);
    expect(
      kinds("Under the 2010 Horizontal Merger Guidelines (1,500 and 2,500) an HHI of 2,159 is highly concentrated."),
    ).toEqual(["point"]);
  });
});

/**
 * Decisions wave fix round 6 (fix-5 review, gates lens, 2026-09-26). Fix
 * round 4's "both directions" rule only asked which numbers appear SOMEWHERE
 * in the sentence: the mirror (statesCurrentPair) and the retired-edition
 * check (statesOwn) both passed once both pairs appeared anywhere, so a
 * sentence giving each edition the OTHER's bands passed both ways. The
 * reviewer's probe returned []:
 *   "Bands follow the 2023 Merger Guidelines: 1,500 and 2,500 (the 2010
 *    Horizontal Merger Guidelines used 1,000 and 1,800)."
 * Each pair of numbers is now attributed to the edition named NEAREST it in
 * its clause (a clause ends at ";" or ", and / but / while / whereas / yet";
 * a parenthetical naming an edition keeps its numbers, one naming none
 * reaches to the enclosing text), and each edition is held to the pair
 * attributed to it. The point-claim regex also missed "an HHI of 1,900 is
 * considered moderately concentrated" and "The program's HHI, 1,900, is
 * moderately concentrated"; both shapes are read now.
 */
describe("leg (q) fix round 6 — each pair belongs to the edition named nearest it", () => {
  const PROBE =
    "Bands follow the 2023 Merger Guidelines: 1,500 and 2,500 (the 2010 Horizontal Merger Guidelines used 1,000 and 1,800).";

  it("RED at fix 5: the reviewer's swapped-pairs probe FAILS", () => {
    expect(kinds(PROBE)).toContain("edition-bands");
    const f = hhiBandStatementFindings(PROBE);
    expect(f.some((x) => /1,500/.test(x) && /2,500/.test(x) && /2023/.test(x)), f.join("\n")).toBe(true);
  });

  it("RED at fix 5: the swap FAILS in every clause shape", () => {
    for (const s of [
      "The 2023 Merger Guidelines set 1,500 and 2,500; the 2010 Horizontal Merger Guidelines had set 1,000 and 1,800.",
      "Under the 2010 Horizontal Merger Guidelines the bands were 1,000 and 1,800, and the 2023 Merger Guidelines set them at 1,500 and 2,500.",
      "The 2010 Horizontal Merger Guidelines' 1,000 and 1,800 were replaced by the 2023 Merger Guidelines' 1,500 and 2,500.",
      "The 2023 Merger Guidelines' bands (1,500 and 2,500) replaced the 2010 Horizontal Merger Guidelines' (1,000 and 1,800).",
      "Per the DOJ Antitrust Division's HHI page the bands are 1,500 and 2,500 (the 2010 Horizontal Merger Guidelines had 1,000 and 1,800).",
    ]) {
      expect(kinds(s), s).toContain("edition-bands");
    }
  });

  it("comparisons that give each edition its own pair keep passing, in any order", () => {
    for (const s of [
      // Fix round 8 (R-DEC-LEGQ-b) moved two comparisons out of this list —
      // "The 2023 Merger Guidelines' bands (1,000 and 1,800) replaced the 2010
      // Horizontal Merger Guidelines' (1,500 and 2,500)." and "The 2010
      // Horizontal Merger Guidelines' 1,500 and 2,500 were replaced by the
      // 2023 Merger Guidelines' 1,000 and 1,800." — each is true, but the
      // nearest-FOLLOWING reading gives its first pair to the other edition,
      // so it fails closed (see the fix-round-8 block below).
      "The 2023 Merger Guidelines replaced 1,500 and 2,500 with 1,000 and 1,800.",
      "Under the 2023 Merger Guidelines (the 2010 Horizontal Merger Guidelines used 1,500 and 2,500) the bands are 1,000 and 1,800.",
      "Bands follow the 2023 Merger Guidelines: 1,000 and 1,800 (the 2010 Horizontal Merger Guidelines used 1,500 and 2,500).",
      // Fix round 7 (R-DEC-LEGQ) moved "The 2023 Merger Guidelines' 1,000 and
      // 1,800 replaced 1,500 and 2,500, the 2010 Horizontal Merger Guidelines'
      // bands." out of this list: the 2023 name PRECEDES 1,500 / 2,500, so the
      // ruling attributes the pair to 2023 and the sentence fails closed (see
      // the fix-round-7 block below).
      "The 2023 Merger Guidelines set 1,000 and 1,800; the 2010 Horizontal Merger Guidelines had set 1,500 and 2,500.",
      "Until 2026-09-25 the bands were the 2010 Horizontal Merger Guidelines' (1,500 and 2,500), and an index below 1,500 was labelled “competitive”.",
    ]) {
      expect(hhiBandStatementFindings(s), s).toEqual([]);
    }
  });

  it("RED at fix 5: 'considered <band>' and 'HHI, N, is <band>' are point claims", () => {
    for (const s of [
      "An HHI of 1,900 is considered moderately concentrated.",
      "The program's HHI, 1,900, is moderately concentrated.",
      "Under the 2023 Merger Guidelines, an HHI of 1,900 is considered moderately concentrated.",
      "The program's HHI, 2,159, is considered moderately concentrated under the 2023 Merger Guidelines.",
      "An HHI of 1,200 is deemed highly concentrated.",
      "An HHI of 999 is regarded as moderately concentrated.",
    ]) {
      expect(kinds(s), s).toContain("point");
    }
    expect(hhiBandStatementFindings("The program's HHI, 1,900, is moderately concentrated.")[0]).toMatch(/1,900/);
  });

  it("true point claims in the widened shapes keep passing", () => {
    for (const s of [
      "An HHI of 1,900 is considered highly concentrated.",
      "The program's HHI, 1,900, is highly concentrated.",
      "An HHI of 1,800 is considered moderately concentrated.",
      "The program's HHI, 999, is unconcentrated, this site's word for it.",
      "The program's HHI, 1,900, was considered moderately concentrated under the 2010 Horizontal Merger Guidelines (1,500 and 2,500).",
    ]) {
      expect(hhiBandStatementFindings(s), s).toEqual([]);
    }
  });
});

describe("leg (q) fix round 6 — the attribution's clause and parenthesis scoping", () => {
  it("a clause break keeps each edition's pair with it, even when the next name is nearer", () => {
    for (const s of [
      "Under the 2010 Horizontal Merger Guidelines the bands were 1,500 and 2,500, and the 2023 Merger Guidelines set them at 1,000 and 1,800.",
      "Under the 2010 Horizontal Merger Guidelines the bands were 1,500 and 2,500; the 2023 Merger Guidelines set 1,000 and 1,800.",
    ]) {
      expect(hhiBandStatementFindings(s), s).toEqual([]);
    }
  });

  it("a parenthetical naming no edition reaches to the enclosing text's name, not a nearer parenthetical's", () => {
    const s =
      "Under the 2010 Horizontal Merger Guidelines the bands were wider (1,500 and 2,500) " +
      "(the 2023 Merger Guidelines narrowed them to 1,000 and 1,800).";
    expect(hhiBandStatementFindings(s)).toEqual([]);
  });

  it("the current edition is held to the pair attributed to it even when the retired edition states its own", () => {
    const s =
      "Under the 2010 Horizontal Merger Guidelines the bands were 1,500 and 2,500 and never 1,000 and 1,800; " +
      "the 2023 Merger Guidelines use 1,500 and 2,500.";
    expect(kinds(s)).toEqual(["edition-bands"]);
    expect(hhiBandStatementFindings(s)[0]).toMatch(/2023/);
  });
});

/**
 * Decisions wave fix round 7 (fix-6 re-check, R-DEC-LEGQ, 2026-09-26). Fix
 * round 6 made two changes the ruling reverses:
 *   - it SKIPPED fix round 4/5's mirror whenever the retired pair sat nearest
 *     the 2010 name, so four sentences crediting 1,500 / 2,500 to the 2023
 *     Guidelines passed ("The 2023 Merger Guidelines keep the 2010
 *     Guidelines' bands of 1,500 and 2,500.") — fix 5 failed each of them;
 *   - it attributed each number to the NEAREST name in either direction, so
 *     two true comparisons opening with a subordinate clause failed ("Where
 *     the 2010 … used 1,500 and 2,500, the 2023 … use 1,000 and 1,800." —
 *     2,500 sits nearer the 2023 name that follows it).
 * R-DEC-LEGQ: every fix-5 check stays, and a pair belongs to the nearest
 * edition name that PRECEDES it (the following name only when none precedes),
 * inside fix 6's clause / parenthesis scoping.
 */
describe("leg (q) fix round 7 — every fix-5 check, and the nearest PRECEDING name owns a pair", () => {
  it("RED at fix 6: the re-check's sentences crediting 1,500 / 2,500 to the 2023 Guidelines FAIL", () => {
    for (const s of [
      "The 2023 Merger Guidelines keep the 2010 Guidelines' bands of 1,500 and 2,500.",
      "The 2023 Merger Guidelines retain the 2010 bands, 1,500 and 2,500.",
      "Under the 2023 Merger Guidelines, as under the 2010 Guidelines, the bands are 1,500 and 2,500.",
      "The 2023 Merger Guidelines carry over the 2010 Horizontal Merger Guidelines' thresholds of 1,500 and 2,500.",
      "Under the 2023 Merger Guidelines the bands changed; the 2010 Guidelines used 1,500 and 2,500.",
      "The 2023 Merger Guidelines replaced the 2010 Horizontal Merger Guidelines, which used 1,500 and 2,500.",
    ]) {
      expect(kinds(s), s).toContain("edition-bands");
      expect(
        hhiBandStatementFindings(s).some((f) => /1,500/.test(f) && /2,500/.test(f) && /2023/.test(f)),
        s,
      ).toBe(true);
    }
  });

  it("true comparisons that open with a subordinate clause: PASSED at fix 7, fail closed since fix 8 (R-DEC-LEGQ-b)", () => {
    // Fix round 7 passed these (the preceding-name reading gets them right);
    // R-DEC-LEGQ-b supersedes R-DEC-LEGQ's "either clause order passes": the
    // following-name reading gives 1,500 / 2,500 to the 2023 name after them,
    // so each fails closed and is rephrased (one edition per clause).
    for (const s of [
      "Where the 2010 Horizontal Merger Guidelines used 1,500 and 2,500, the 2023 Merger Guidelines use 1,000 and 1,800.",
      "Unlike the 2010 Horizontal Merger Guidelines' 1,500 and 2,500, the 2023 Merger Guidelines use 1,000 and 1,800.",
    ]) {
      expect(kinds(s), s).toEqual(["edition-bands"]);
      expect(hhiBandStatementFindings(s)[0], s).toMatch(/R-DEC-LEGQ-b/);
    }
  });

  it("swapped pairs FAIL, in the subordinate-clause shape too", () => {
    for (const s of [
      "Bands follow the 2023 Merger Guidelines: 1,500 and 2,500 (the 2010 Horizontal Merger Guidelines used 1,000 and 1,800).",
      "The 2010 Horizontal Merger Guidelines' bands (1,000 and 1,800) were replaced by the 2023 Merger Guidelines' 1,500 and 2,500.",
      "The 2023 Merger Guidelines use 1,500 and 2,500, while the 2010 Horizontal Merger Guidelines used 1,000 and 1,800.",
      "Where the 2010 Horizontal Merger Guidelines used 1,000 and 1,800, the 2023 Merger Guidelines use 1,500 and 2,500.",
      "Unlike the 2010 Horizontal Merger Guidelines' 1,000 and 1,800, the 2023 Merger Guidelines use 1,500 and 2,500.",
    ]) {
      expect(kinds(s), s).toContain("edition-bands");
    }
  });

  it("a pair before every name takes the name that follows it (the fallback)", () => {
    expect(
      hhiBandStatementFindings(
        "1,500 and 2,500 were the 2010 Horizontal Merger Guidelines' bands; the 2023 Merger Guidelines use 1,000 and 1,800.",
      ),
    ).toEqual([]);
    expect(
      kinds("1,000 and 1,800 were the 2010 Horizontal Merger Guidelines' bands; the 2023 Merger Guidelines use 1,500 and 2,500."),
    ).toContain("edition-bands");
  });

  it("a comparison under the 2023 name alone keeps passing; with the 2010 name inside it, fails closed since fix 8", () => {
    expect(hhiBandStatementFindings("The 2023 Merger Guidelines replaced 1,500 and 2,500 with 1,000 and 1,800.")).toEqual([]);
    // Fix round 7 passed these three; under R-DEC-LEGQ-b each has a reading
    // that gives a pair to the wrong edition (the preceding-name reading
    // gives 1,000 / 1,800 to the 2010 name before them, or the following-name
    // reading gives them to the 2010 name after them), so each fails closed.
    for (const s of [
      "The 2023 Merger Guidelines replaced the 2010 Horizontal Merger Guidelines' 1,500 and 2,500 with 1,000 and 1,800.",
      "The 2023 Merger Guidelines lowered the bands to 1,000 and 1,800 from the 2010 Horizontal Merger Guidelines' 1,500 and 2,500.",
      "The 2023 Merger Guidelines' bands (1,000 and 1,800) replaced the 2010 Guidelines' 1,500 and 2,500.",
    ]) {
      expect(kinds(s), s).toEqual(["edition-bands"]);
      expect(hhiBandStatementFindings(s)[0], s).toMatch(/R-DEC-LEGQ-b/);
    }
  });

  it("fails closed where the retired pair's own name FOLLOWS it after a 2023 name (R-DEC-GATE-LIMIT, documented)", () => {
    // True sentences the preceding-name rule attributes to 2023. Pinned so a
    // change to the rule is a deliberate one, never a silent widening.
    for (const s of [
      "The 2023 Merger Guidelines' 1,000 and 1,800 replaced 1,500 and 2,500, the 2010 Horizontal Merger Guidelines' bands.",
      "The 2023 Merger Guidelines use 1,000 and 1,800, not the 1,500 and 2,500 of the 2010 Horizontal Merger Guidelines.",
    ]) {
      expect(kinds(s), s).toEqual(["edition-bands"]);
    }
  });
});

/**
 * Decisions wave fix round 8 (fix-7 re-check, R-DEC-LEGQ-b, 2026-09-26). The
 * re-check ran a 512-sentence template fuzz (32 comparison shapes × both
 * edition orders × both 2010 names × the four ways of placing the two pairs)
 * and found fix 7 PASSING 26 false sentences that fix 6 failed, e.g. "The
 * bands are 1,000 and 1,800 under the 2010 Horizontal Merger Guidelines and
 * 1,500 and 2,500 under the 2023 Merger Guidelines." — fix 7 checked that each
 * edition was given its OWN pair, never that it was given ONLY its own pair —
 * and 6 more false sentences that no version failed. Which name a number
 * belongs to is grammar a regular expression does not read, so the ruling
 * makes the leg FAIL-CLOSED on a sentence that names two editions and states a
 * band pair: every occurrence of a pair's numbers is read twice, by the
 * nearest edition name BEFORE it and by the nearest name AFTER it (each
 * reading falling back to the other side when its own is empty, inside fix
 * round 6's clause and parenthesis scopes), and the sentence fails if either
 * reading gives a number to an edition that is not its pair's, or if the two
 * readings disagree. A true comparison that one reading misreads fails too,
 * and is rephrased: one edition per sentence, or each edition in its own
 * clause (";", ", and / while / but …") or its own parenthetical. Every
 * fix-7 check still runs first, unchanged. No shipped page compares editions
 * in one sentence; /methodology/'s corrections row gives each edition its
 * own table cell, and bandProseSegments reads each cell alone.
 */
describe("leg (q) fix round 8 — R-DEC-LEGQ-b: a two-edition band statement fails closed", () => {
  const E10 = "2010 Horizontal Merger Guidelines";
  const E23 = "2023 Merger Guidelines";
  const P10 = "1,500 and 2,500";
  const P23 = "1,000 and 1,800";

  it("RED at fix 7: the re-check's 26 false swapped-pair sentences (fix 6 failed them) FAIL", () => {
    // The 13 shapes, each with the 2010 edition's two names.
    const shapes = [
      (a) => `Unlike the ${a}' ${P23}, ${P10} are the ${E23}' bands.`,
      (a) => `In place of the ${a}' ${P23}, the site now applies ${P10} from the ${E23}.`,
      (a) => `The ${a}' ${P23} replaced ${P10}, the ${E23}' bands.`,
      (a) => `The bands are ${P23} under the ${a} and ${P10} under the ${E23}.`,
      (a) => `${P23} under the ${a} became ${P10} under the ${E23}.`,
      (a) => `The ${a} set the thresholds at ${P23}, down from ${P10} in the ${E23}.`,
      (a) => `The ${a}' ${P23} gave way to ${P10} in the ${E23}.`,
      (a) => `${P23} in the ${a} became ${P10} in the ${E23}.`,
      (a) => `The ${a} use ${P23}, not the ${P10} of the ${E23}.`,
      (a) => `The ${a} moved the bands from ${P10}, the ${E23}' thresholds, to ${P23}.`,
      (a) => `Having used ${P23} in the ${a}, the agencies set ${P10} in the ${E23}.`,
      (a) => `The HHI bands, ${P23} in the ${a} versus ${P10} in the ${E23}, changed.`,
      (a) => `The ${a}' thresholds are ${P23}, compared with ${P10} in the ${E23}.`,
    ];
    let n = 0;
    for (const shape of shapes) {
      for (const a of [E10, "2010 Guidelines"]) {
        const s = shape(a);
        expect(kinds(s), s).toContain("edition-bands");
        n++;
      }
    }
    expect(n).toBe(26);
  });

  it("RED at fix 7: false sentences that fix 5, fix 6 and fix 7 all passed FAIL", () => {
    for (const s of [
      `The ${E23} replaced the ${E10}' ${P23} with ${P10}.`,
      `The ${E23} replaced the 2010 Guidelines' ${P23} with ${P10}.`,
      `The ${E23} moved the bands from ${P23}, the ${E10}' thresholds, to ${P10}.`,
      `The ${E23} moved the bands from ${P23}, the 2010 Guidelines' thresholds, to ${P10}.`,
      `The ${E10} cut the bands from ${P10} (the ${E23}) to ${P23}.`,
      `The 2010 Guidelines cut the bands from ${P10} (the ${E23}) to ${P23}.`,
    ]) {
      expect(kinds(s), s).toContain("edition-bands");
    }
  });

  it("RED at fix 7: EVERY occurrence is read — a retired pair stated again under the 2023 name fails", () => {
    // Fix 5, 6 and 7 pass both: each edition owns its own pair SOMEWHERE in
    // the sentence, so no check asked about the second 1,500 / 2,500.
    for (const s of [
      `The 2010 Guidelines used ${P10}; the ${E23} keep ${P10} beside ${P23}.`,
      `The ${E10} used ${P10}, and the ${E23} use ${P23} as well as ${P10}.`,
    ]) {
      expect(kinds(s), s).toEqual(["edition-bands"]);
      expect(hhiBandStatementFindings(s)[0], s).toMatch(/R-DEC-LEGQ-b/);
    }
  });

  it("the finding names both readings, the edition each gives the pair to, and the rephrasing", () => {
    const s = `The bands are ${P23} under the ${E10} and ${P10} under the ${E23}.`;
    const f = hhiBandStatementFindings(s);
    expect(f).toHaveLength(1);
    expect(f[0]).toMatch(/R-DEC-LEGQ-b/);
    expect(f[0]).toMatch(/nearest name BEFORE/);
    expect(f[0]).toMatch(/nearest name AFTER/);
    expect(f[0]).toMatch(/1,000/);
    expect(f[0]).toMatch(/one edition per sentence/);
  });

  it("RED at fix 7: a TRUE comparison one reading misreads fails closed (the ruling: rephrase it)", () => {
    for (const s of [
      `The ${E10}' ${P10} were replaced by the ${E23}' ${P23}.`,
      `The ${E23}' bands (${P23}) replaced the ${E10}' (${P10}).`,
      `The bands are ${P10} under the ${E10} and ${P23} under the ${E23}.`,
      `The ${E10}' thresholds are ${P10}, compared with ${P23} in the ${E23}.`,
    ]) {
      expect(kinds(s), s).toEqual(["edition-bands"]);
      expect(hhiBandStatementFindings(s)[0], s).toMatch(/R-DEC-LEGQ-b/);
    }
  });

  it("a two-edition comparison both readings give the same owners keeps passing: each edition in its own clause or parenthetical", () => {
    for (const s of [
      `The ${E23} set ${P23}; the ${E10} had set ${P10}.`,
      `Under the ${E10} the bands were ${P10}, and the ${E23} set them at ${P23}.`,
      `The ${E10} used ${P10}, while the ${E23} use ${P23}.`,
      `Bands follow the ${E23}: ${P23} (the ${E10} used ${P10}).`,
      `Under the ${E23} (the ${E10} used ${P10}) the bands are ${P23}.`,
      `${P10} were the ${E10}' bands; the ${E23} use ${P23}.`,
      `Under the ${E10} the bands were wider (${P10}) (the ${E23} narrowed them to ${P23}).`,
    ]) {
      expect(hhiBandStatementFindings(s), s).toEqual([]);
    }
  });

  it("a sentence naming ONE edition is read exactly as at fix 7", () => {
    for (const s of [
      `The ${E23} replaced ${P10} with ${P23}.`,
      `Until 2026-09-25 this site used the ${E10}' bands, ${P10}.`,
      `Under the ${E10} (${P10}) an HHI of 2,159 was moderately concentrated.`,
      "In FY2010 the program's HHI of 2,100 was highly concentrated under the 2023 Merger Guidelines.",
    ]) {
      expect(hhiBandStatementFindings(s), s).toEqual([]);
    }
    expect(kinds(`Bands follow the ${E23}: ${P10}.`)).toEqual(["edition-bands"]);
  });

  it("the re-check's fuzz: every FALSE sentence of the 32 shapes fails; a true one fails only as edition-bands", () => {
    const NAMES = { 2010: [E10, "2010 Guidelines"], 2023: [E23] };
    const PAIR = { 2010: P10, 2023: P23 };
    const T = [
      "Where the {A} used {PA}, the {B} use {PB}.",
      "Unlike the {A}' {PA}, the {B} use {PB}.",
      "The {A} used {PA}, while the {B} use {PB}.",
      "The {A} use {PA}; the {B} used {PB}.",
      "The {A} replaced the {B}' {PB} with {PA}.",
      "The {A} lowered the bands to {PA} from the {B}' {PB}.",
      "Unlike the {A}' {PA}, {PB} are the {B}' bands.",
      "{PA} are the {A}' bands; {PB} were the {B}'.",
      "In place of the {A}' {PA}, the site now applies {PB} from the {B}.",
      "The {A}' bands ({PA}) replaced the {B}' {PB}.",
      "The {A}' {PA} replaced {PB}, the {B}' bands.",
      "Compared with {PA} under the {A}, the {B} set the bands at {PB}.",
      "The bands are {PA} under the {A} and {PB} under the {B}.",
      "The bands are {PA} under the {A}, and {PB} under the {B}.",
      "The {A} put the bands at {PA}, the {B} at {PB}.",
      "The {A} ({PA}) superseded the {B} ({PB}).",
      "{PA} under the {A} became {PB} under the {B}.",
      "The {A} set the thresholds at {PA}, down from {PB} in the {B}.",
      "The {A}' bands of {PA} differ from the {B}' {PB}.",
      "The {B}' {PB} gave way to {PA} in the {A}.",
      "{PB} in the {B} became {PA} in the {A}.",
      "The {A} now use {PA}, not the {B}' {PB}.",
      "The {A} use {PA}, not the {PB} of the {B}.",
      "In the {A}, the bands are {PA}; in the {B}, they were {PB}.",
      "The {A} have bands of {PA} and the {B} had bands of {PB}.",
      "The {A} moved the bands from {PB}, the {B}' thresholds, to {PA}.",
      "Having used {PB} in the {B}, the agencies set {PA} in the {A}.",
      "The HHI bands, {PA} in the {A} versus {PB} in the {B}, changed.",
      "The {A}' thresholds are {PA}, compared with {PB} in the {B}.",
      "The {A}' thresholds are {PA}, compared with the {B}' {PB}.",
      "After the {B}' {PB}, the {A} adopted {PA}.",
      "The {A} cut the bands from {PB} (the {B}) to {PA}.",
    ];
    let falseN = 0;
    let trueN = 0;
    const falsePass = [];
    const trueOtherKind = [];
    for (const t of T) {
      for (const [ya, yb] of [["2010", "2023"], ["2023", "2010"]]) {
        for (const na of NAMES[ya]) {
          for (const nb of NAMES[yb]) {
            for (const [pa, pb] of [[ya, yb], [yb, ya], [ya, ya], [yb, yb]]) {
              const s = t
                .replaceAll("{A}", na)
                .replaceAll("{B}", nb)
                .replaceAll("{PA}", PAIR[pa])
                .replaceAll("{PB}", PAIR[pb]);
              const truth = pa === ya && pb === yb;
              const bad = kinds(s);
              if (truth) {
                trueN++;
                if (bad.some((k) => k !== "edition-bands")) trueOtherKind.push(s);
              } else {
                falseN++;
                if (bad.length === 0) falsePass.push(s);
              }
            }
          }
        }
      }
    }
    expect(falseN + trueN).toBe(512);
    expect(falsePass).toEqual([]);
    expect(trueOtherKind).toEqual([]);
  });

  it("/methodology/'s corrections row passes because each edition sits in its own cell; read as one string it fails closed", () => {
    const row =
      "<main><table><tbody><tr><td>HHI bands</td><td>2010 guidelines (1,500 / 2,500)</td>" +
      "<td>2023 Merger Guidelines (1,000 / 1,800)</td><td>On the 2026-09-25 export these bands put 3 feed cards " +
      "and 4 badges one band higher; “Competitive” is now Unconcentrated.</td></tr></tbody></table></main>";
    const segs = bandProseSegments(parse(row, { comment: false }));
    expect(segs.flatMap((s) => hhiBandStatementFindings(s))).toEqual([]);
    expect(kinds("HHI bands 2010 guidelines (1,500 / 2,500) 2023 Merger Guidelines (1,000 / 1,800)")).toEqual([
      "edition-bands",
    ]);
  });
});
