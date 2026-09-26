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
      "The 2023 Merger Guidelines' bands (1,000 and 1,800) replaced the 2010 Horizontal Merger Guidelines' (1,500 and 2,500).",
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
