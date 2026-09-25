/**
 * gate 24 — datatruth_gate (PM-review Sprint 2, spec §P1-5)
 *
 * "The one page built to let people check the site's work" must not lie about
 * itself. Two families of claim are verified against the BUILT artifact:
 *
 *  (a) dataset-card completeness — the set of dataset names rendered in the
 *      /data/ inventory table equals the set of Explorer parquets actually
 *      shipped in data/site/data/. Both directions: a shipped parquet with no
 *      card (budget_lines_decade was undocumented for the whole 5E era) and a
 *      card naming a parquet that does not exist are equally failures.
 *  (b) rendered row-count truth — every card's VISIBLE Rows cell equals the
 *      parquet's real row count, recomputed independently from the parquet
 *      files by datatruth-recompute.py (DuckDB). The gate reads rendered text,
 *      never a data-* attribute carrying the number, so a page that renders a
 *      stale literal cannot satisfy it by also emitting a correct attribute.
 *  (c) Explorer picker truth — the `#dataset-select` options (the actual
 *      queryable set: lib/duckdb registerDatasets) cover exactly the same
 *      parquets, and each option's rendered "(N rows)" matches the same
 *      recompute. A dataset documented in the table but unregistered in the
 *      engine is a lie of a different shape.
 *  (d) corpus statement — [data-corpus-statement] renders on /programs/,
 *      /years/, /methodology/ and /data/; every instance states the SAME two
 *      numbers in the canonical sentence shape; those numbers equal the
 *      program_details sidecar count (browsable pages) and programs.json
 *      length (detail-grade), recomputed here from data/site/json; and the
 *      §P0-5 scope tail is present on each.
 *  (e) /methodology/ §3's per-build check counts equal the artifacts that
 *      DEFINE them (dbt manifest, the verify.mjs gate registry, the eval set),
 *      recomputed here rather than read back from site_meta.
 *  (f) table sort determinism (§P1-7) — every data table declares its order
 *      via [data-sort-table]/[data-sort-order] and renders monotonically in
 *      it. An enumerated contract set (incl. the lobbying table that shipped
 *      2024, 2026, 2025) plus a sweep of ~400 built pages. See leg f's own
 *      block at the bottom of this file.
 *  (g) curated entity-family merge (§P1-3) — /companies/ split Raytheon
 *      ($43.7B, #4) from RTX ($24.6B, #6): one company, two rows. This leg
 *      asserts on the BUILT page that the merge held (no curated family
 *      appears in two rows) and that every curated event's source_url renders
 *      as an external reference on /companies/families/. See leg g's own
 *      block at the bottom of this file.
 *  (h) feed claim-vs-data consistency (Sprint 3 Task 1b) — /feed/ published 87
 *      cards reading "<program> zeroed out in FY2026 (had $0 in FY25)" when the
 *      program had $293.1M in FY2025 and the corpus held no FY2026 figure for it
 *      at all. Legs a-g and gate 23 all verify that a DISPLAYED NUMBER matches
 *      its CITED FACT — which is exactly why this shipped: the citation was
 *      valid and the number really was 0, and the lie lived in the SENTENCE
 *      WRAPPED AROUND it. This leg reads feed prose as CLAIMS and checks them
 *      against budget_lines.parquet. See leg h's own block at the bottom.
 *  (i) SYNDICATED feed magnitudes (Sprint 3 Task 2, §P1-8) — the same claims
 *      leave the site a second way, as RSS/Atom files a subscriber's reader
 *      keeps and we cannot recall. This leg re-derives every published
 *      magnitude from the SAME corpus recompute leg h uses (one subprocess,
 *      one derivation — the page and the feed must not be checked against two
 *      truths) and against each endpoint's own cited fact. See leg i's block.
 *  (j) COUNT NOTATION, SWEPT (Sprint 3 Task 5, §P1-5) — leg d pins the
 *      corpus statement's two numbers; this sweeps every OTHER cardinality
 *      the site renders. "/years/ … 1741 of 1741 programs" and "/company/…
 *      LDA Filing Mentions (1296)" shipped ungrouped beside a corpus
 *      statement reading "1,741 of them": two notations for one number reads
 *      as two numbers. The unit of scanning is the LEAF ELEMENT — an element
 *      with no element children — because React splits `{n} filings` into
 *      three text nodes separated by `<!-- -->` comments (a per-text-node
 *      scan is blind to exactly the shape this leg exists to catch), while a
 *      whole-subtree scan glues "CO-05" and "10 programs" from sibling cells
 *      into a fictitious "0510 programs". Quoted source text is skipped —
 *      J-book prose carries the source's notation, not ours — but ONLY for
 *      the marker kinds that earn it (source-text-kinds.mjs, backlog #38):
 *      the attribute's presence used to delete the subtree outright, which is
 *      how /methodology/ removed its whole page from this sweep. Site-authored
 *      prose is swept, /methodology/ specifically must contribute numbers, and
 *      fiscal years are excluded by value. See leg j's own block at the bottom.
 *  (k) CORPUS-COUNT PROVENANCE (tri-persona Wave 4, item 4). Leg (d) pins ONE
 *      sentence stating TWO of the five ways this site counts itself; leg (j)
 *      pins how counts are punctuated. Neither asks whether a corpus number
 *      on a page is a DERIVED figure or a literal somebody typed. This leg
 *      recomputes all five from the artifacts that define them (sitemap.xml,
 *      the sidecars, programs.json, datasets.json), requires /coverage/'s
 *      reconciliation table to publish each one correctly, and requires every
 *      corpus-shaped claim on the singleton pages to equal one of them. Same
 *      class as the stale `measured:` annotation and the outlived docstring.
 *      See leg k's own block at the bottom.
 *  (l) FAMILY LABELS THAT WON A COIN FLIP (ROADMAP #10, option A). A family's
 *      published name is `dim_entities.display_name` — an argmax over its
 *      dominant member's registered parent names. `ROCKWELL COLLINS AUSTRALIA
 *      PTY LIMITED` titled a family that is 97.3% RAYTHEON COMPANY because
 *      that registration beat `RAYTHEON COMPANY` by 3.1%, and RTX had already
 *      reverted it in FY2026 — so the site published a label the registrant
 *      had corrected. Nothing in the pipeline knew, because `confidence`
 *      grades MERGE risk and no gate graded LABEL risk. This leg recomputes
 *      the margin for every published family from the lake
 *      (familylabel-recompute.py, mirroring entity_graph._PICK_SQL) and FAILS
 *      when one that won by less than 15% carries no row in
 *      data-seeds/entity_display_aliases.csv. It then checks the built pages
 *      render exactly the label the seed authored. Generalised on purpose:
 *      the rule catches the 16th such family the next data drop adds, which
 *      is how this one arrived. See leg l's own block at the bottom.
 *  (m) DECLARED CADENCE vs. MEASURED INGEST AGE (ROADMAP #8). Every leg above
 *      asks whether a number on the page matches the data. This one asks
 *      whether the page's account of HOW OLD the data is matches when we
 *      actually fetched it. /methodology/ ended a paragraph whose subject is
 *      "we" ("We download bulk archive ZIP files… convert them… record the
 *      SHA-256 of every file") with "Update cadence: monthly", while the
 *      newest record in data/manifest.jsonl was 2026-06-11 — 81 days old,
 *      from a 2026-05-06 source snapshot. Nothing was wrong: the sentence is
 *      true of USAspending, every figure derived from that corpus is true and
 *      cited, and all 24 gates passed. The falsehood is the reading, and it is
 *      the same species as the 87 "zeroed FY2026" cards and the entity_xwalk
 *      understatement. Gate 23 leg d3 already fails a derived parquet older
 *      than a partition it reads — INTERNAL staleness. This is the external
 *      one: partitions against the cadence the site publishes. The leg reads
 *      data/manifest.jsonl and the BUILT pages, never site_meta, and it
 *      requires the rendered date to EQUAL the manifest's, so a literal
 *      cannot satisfy it. See leg m's own block at the bottom.
 *  (n) HELD-OUT LINK-PRECISION STUDY (ROADMAP #72). The new link tiers
 *      (FPDS acquisition-program mapping, defense.gov announcement matching,
 *      FSRS subaward matching) rely on an adversarial refute pass at
 *      CREATION time as their precision control; scripts/precision_study.py
 *      draws a stratified sample per method and a two-reviewer adjudication
 *      MEASURES it independently, landing in link_precision_samples.
 *      export_site.py mirrors the tally into site_meta.link_precision. This
 *      leg recomputes that tally from data/site/json/site_meta.json and
 *      requires /methodology/'s [data-link-precision] paragraph to state
 *      every method's exact confirmed/sampled pair — and, symmetrically, to
 *      render NOTHING when site_meta carries no measured methods yet (a
 *      stale or partial paragraph is as much a lie as a rotted literal). See
 *      leg n's own block at the bottom.
 *  (o) PER-AWARD HAND-ADJUDICATION COVERAGE (ROADMAP #109, 2026-09-11). Leg
 *      (n) grades the SAMPLED measurement of the link tiers; this one grades
 *      the section's opening claim about the CENSUS. /methodology/ opened
 *      "As of September 2026, every published link was individually
 *      hand-adjudicated … a link is published as high only if neither
 *      [adversarial reviewer] could refute it." Measured: 9,587 of the 12,595
 *      links the crosswalk grades high or medium carry an adjudication row at
 *      all, three of the five published methods carry NONE, 8,474 of the
 *      adjudications that exist could not pin the work to any one program
 *      element, and 60 rows in the whole table record both lenses — 57 of
 *      them on a link the crosswalk grades high or medium. The
 *      sentence held no number, so no number could disagree with it — the
 *      same blind spot leg h found in feed prose. The sentence is now
 *      rendered from site_meta.link_adjudication and this leg binds it: every
 *      figure stated, NO figure the block does not hold, every unadjudicated
 *      path named, and the passage present iff the block is. See leg o's own
 *      block at the bottom.
 *  (p) CROSSWALK-COUNT PROVENANCE (PM-S3 leftover, ROADMAP.md:34). Leg (k)
 *      does this for corpus SIZE. "Crosswalked" is the site's other
 *      self-describing number and it shipped with two denominators — /flow/
 *      "384 of 444 crosswalked PEs" beside /district/ "200 of 1,938 programs
 *      currently crosswalkable" — with nothing saying they were different
 *      questions (34 of the 200 are not in the 384 at all). (p1) recomputes
 *      all five declared counts from the shipped artifacts and requires
 *      /coverage/#crosswalk to publish each one IN THE DERIVED ORDER, slot
 *      for slot, the way leg (o) binds the adjudication passage; (p2) sweeps
 *      every page that states a crosswalk ratio and rejects a number that is
 *      neither a declared crosswalk count, a declared corpus count, nor a
 *      figure one of the derived site_meta blocks already publishes — those
 *      are READ, never re-derived here, because leg (n) and leg (o) own
 *      them; (p3) recomputes the ORGANIZATION MIX of the flow sidecars and
 *      rejects prose that attributes linkage to one organization while that
 *      organization holds under half of it — the "DARPA crosswalk" sentences
 *      survived on /district/ and /methodology/ long after the sidecars
 *      became 92 Navy / 59 Air Force / 22 Army against 14 DARPA. Vacuity
 *      fails four ways: no artifact, no built claim page, fewer sidecars
 *      than the dated floor, fewer swept claims than the dated floor.
 *  (q) ANNOUNCEMENT LLM-PASS SCOPE (findings log :118-119, 2026-09-19).
 *      /methodology/ disclosed the scope of the LLM-alias pass as four
 *      literals typed 2026-09-02 ("3,840 … about 88% … 12,811 … ~12%"),
 *      describing a residue whose selection code was never committed. This leg
 *      recomputes every figure in that paragraph from
 *      site_meta.announcement_llm_scope and requires the rendered
 *      [data-announcement-scope] text to state each one IN ITS OWN CLAUSE —
 *      anchored to the words around it, in render order, with no number the
 *      block does not carry — so two figures swapped between clauses fail
 *      even though both still appear. The same slots carry the pass's OWN
 *      held-out precision: leg (n)'s tier figure is pinned to the 2026-09-04
 *      stratified draw over the whole announcement tier, which was sampled
 *      before this pass's most recent round existed, so the round is measured
 *      by its own sample and the leg fails either direction of confusion — a
 *      rendered pair the block does not hold, or a measured round the
 *      paragraph calls unmeasured. It also binds the FRAME: the tier's draw
 *      predates the links this pass added to the tier, and
 *      [data-announcement-draw-gap] must say how many. An empty block after
 *      2026-09-19 is a stale export, not an empty corpus, and fails. See leg
 *      q's own block at the bottom.
 *  (r) DISTRICT BY-YEAR CELLS vs THE LAKE (ROADMAP #6). Gate 9 leg f proves
 *      the by-year rows are INTERNALLY consistent — they sum to the headline
 *      the page renders above them. An exporter that read the wrong mart, or a
 *      mart that silently changed its predicate, satisfies that perfectly
 *      while publishing the wrong ten numbers. This leg takes a deterministic
 *      sample of (district, fiscal year) cells from the sidecars, recomputes
 *      each one from fct_award_transactions joined to the high-confidence
 *      fct_budget_to_awards links (districtyear-recompute.py — never from
 *      fct_district_totals_by_year, the artifact under test), and requires
 *      BOTH the sidecar value and the figure RENDERED on the built page to
 *      match it — for the NET cell always, and for the gross "Before
 *      deobligations" cell whenever the page renders one (a cell whose own
 *      gross exceeds its net MUST render one). Non-vacuous: fails if fewer
 *      than 12 cells are published or if
 *      any sampled cell has no rows in the lake. (The brief called this leg
 *      (o); that letter was taken by the hand-adjudication leg above and
 *      (p)/(q) are reserved, so the by-year leg is (r).)
 *
 * WHY a built-artifact gate and not an export-time assertion: the defect this
 * closes was NEVER an export defect — the exporter's counts were correct and
 * the parquets were fresh; the /data/ page hardcoded literals that had drifted
 * from them. An export-time assertion cannot see rendered HTML and so cannot
 * catch it. This gate reads out/ and the parquets and compares the two.
 *
 * Export: runDataTruthGate() → { pass, errors, notes }
 */

import fs from "fs";
import path from "path";
import { spawnSync } from "child_process";
import { fileURLToPath } from "url";
import { parse } from "node-html-parser";
import { createRequire } from "module";
import { feedGuid, FR_NS } from "../../src/lib/feed-model.mjs";
import { exemptFromNotationSweep } from "./source-text-kinds.mjs";
import { displayCompanyName } from "../../src/lib/company-name.mjs";
import {
  NEAR_TIE_MARGIN,
  isNearTie,
  labelCensusFindings,
  labelMarginCensus,
} from "../../src/lib/entity-label-margins.mjs";
import { normalizeAmount, valuesAgree } from "./basis.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(__dirname, "..", "..");
const repoRoot = path.resolve(siteRoot, "..");
const outDir = path.resolve(siteRoot, "out");
const jsonDir = path.resolve(repoRoot, "data", "site", "json");
const parquetDir = path.resolve(repoRoot, "data", "site", "data");

/** Pages that must carry the canonical corpus statement (§P1-5). */
const CORPUS_PAGES = ["/programs/", "/years/", "/methodology/", "/data/"];

/** Canonical corpus sentence shape — the two numbers are read from HERE. */
const CORPUS_RE =
  /([\d,]+)\s+browsable program pages;\s*([\d,]+)\s+of them carry detail-grade/i;

/**
 * §P0-5 scope tail — same language as the hero qualifier.
 *
 * Backlog #49 MIRROR: this must change together with
 * export_site.py's `_CORPUS_SCOPE_TAIL` (same lesson as basis.mjs's
 * BASIS_LABEL mirror in #48) — the old text ("appropriations not covered by
 * the R-1/P-1 rollups") was false; COLUMBIA Class Submarine is a P-1 line
 * and still absent from the corpus. Change one, change both.
 */
const CORPUS_SCOPE_TAIL =
  "excludes personnel, o&m, and r-1/p-1 lines that lack r-2/p-40 project detail";

/** A page with fewer cards than this is a parse failure, not a pass. */
const MIN_DATASET_CARDS = 10;

function htmlFor(url) {
  return path.join(outDir, ...url.split("/").filter(Boolean), "index.html");
}

function readHtml(url) {
  const p = htmlFor(url);
  if (!fs.existsSync(p)) return null;
  return parse(fs.readFileSync(p, "utf8"));
}

/** Rendered text → integer. "8,549" → 8549; anything else → null. */
function parseCount(text) {
  const m = String(text ?? "").trim().match(/^([\d,]+)$/);
  if (!m) return null;
  const n = Number(m[1].replace(/,/g, ""));
  return Number.isFinite(n) ? n : null;
}

function norm(s) {
  return String(s ?? "")
    .replace(/&amp;/g, "&")
    .replace(/\s+/g, " ")
    .trim();
}

/** Independent parquet recompute (DuckDB, via uv run python). */
function recomputeParquets() {
  const script = path.join(__dirname, "datatruth-recompute.py");
  const res = spawnSync("uv", ["run", "python", script], {
    cwd: repoRoot,
    encoding: "utf8",
    timeout: 300000,
    maxBuffer: 32 * 1024 * 1024,
  });
  if (res.status !== 0) {
    throw new Error(
      `datatruth-recompute.py failed (status ${res.status}): ${
        (res.stderr || "").slice(-800)
      }`,
    );
  }
  const parsed = JSON.parse(res.stdout);
  if (parsed.__error__) throw new Error(parsed.__error__);
  return parsed;
}

export async function runDataTruthGate() {
  const errors = [];
  const notes = [];

  // ── Independent truth: the parquets themselves ────────────────────────────
  let truth;
  try {
    truth = recomputeParquets();
  } catch (e) {
    return {
      pass: false,
      errors: [`parquet recompute: ${e.message}`],
      notes,
    };
  }
  const parquetNames = Object.keys(truth).sort();
  if (parquetNames.length < MIN_DATASET_CARDS) {
    errors.push(
      `parquet recompute: only ${parquetNames.length} parquets found in ${parquetDir} — expected ≥${MIN_DATASET_CARDS} (non-vacuous check)`,
    );
  }
  notes.push(
    `parquet recompute: ${parquetNames.length} Explorer parquets read from data/site/data/ ✓`,
  );

  const dataRoot = readHtml("/data/");
  if (!dataRoot) {
    return {
      pass: false,
      errors: [`missing built page: ${htmlFor("/data/")} — run npm run build`],
      notes,
    };
  }

  // ── leg a: dataset-card completeness ──────────────────────────────────────
  const cardEls = dataRoot.querySelectorAll("[data-dataset-card]");
  const cardNames = cardEls.map((el) => el.getAttribute("data-dataset-card"));
  const cardSet = new Set(cardNames);

  if (cardEls.length < MIN_DATASET_CARDS) {
    errors.push(
      `leg a (/data/): only ${cardEls.length} [data-dataset-card] rows found — expected ≥${MIN_DATASET_CARDS} (the inventory table must expose one row per shipped parquet)`,
    );
  }
  const missingCards = parquetNames.filter((n) => !cardSet.has(n));
  if (missingCards.length > 0) {
    errors.push(
      `leg a (/data/): ${missingCards.length} shipped parquet(s) have NO dataset card: ${missingCards.join(", ")}`,
    );
  }
  const phantomCards = [...cardSet].filter((n) => !(n in truth));
  if (phantomCards.length > 0) {
    errors.push(
      `leg a (/data/): ${phantomCards.length} dataset card(s) name a parquet that is not shipped: ${phantomCards.join(", ")}`,
    );
  }
  if (missingCards.length === 0 && phantomCards.length === 0 && cardEls.length >= MIN_DATASET_CARDS) {
    notes.push(
      `leg a: /data/ documents all ${parquetNames.length} shipped parquets, no phantoms ✓`,
    );
  }

  // ── leg b: rendered row-count truth ───────────────────────────────────────
  const countMismatches = [];
  for (const el of cardEls) {
    const name = el.getAttribute("data-dataset-card");
    const cell = el.querySelector("[data-dataset-rowcount]");
    if (!cell) {
      countMismatches.push(`${name}: no [data-dataset-rowcount] cell rendered`);
      continue;
    }
    const rendered = parseCount(cell.text);
    if (rendered === null) {
      countMismatches.push(
        `${name}: rows cell text ${JSON.stringify(norm(cell.text))} is not an integer`,
      );
      continue;
    }
    const actual = truth[name]?.rows;
    if (actual === undefined) continue; // already reported as a phantom card
    if (rendered !== actual) {
      countMismatches.push(
        `${name}: page renders ${rendered.toLocaleString("en-US")}, parquet has ${actual.toLocaleString("en-US")}`,
      );
    }
  }
  if (countMismatches.length > 0) {
    errors.push(
      `leg b (/data/): ${countMismatches.length} dataset card row-count(s) disagree with the shipped parquet — ${countMismatches.join("; ")}`,
    );
  } else if (cardEls.length > 0) {
    notes.push(
      `leg b: all ${cardEls.length} rendered row counts match the parquets exactly ✓`,
    );
  }

  // ── leg c: Explorer picker truth ──────────────────────────────────────────
  const select = dataRoot.querySelector("#dataset-select");
  if (!select) {
    errors.push(
      "leg c (/data/): no #dataset-select rendered — the Explorer picker is the queryable dataset set",
    );
  } else {
    const options = select.querySelectorAll("option");
    const optNames = options.map((o) => o.getAttribute("value"));
    const optSet = new Set(optNames);
    const unregistered = parquetNames.filter((n) => !optSet.has(n));
    if (unregistered.length > 0) {
      errors.push(
        `leg c (/data/): ${unregistered.length} shipped parquet(s) are NOT selectable in the Explorer: ${unregistered.join(", ")}`,
      );
    }
    const optMismatches = [];
    for (const o of options) {
      const name = o.getAttribute("value");
      const m = norm(o.text).match(/\(([\d,]+)\s+rows\)/);
      if (!m) {
        optMismatches.push(`${name}: option text ${JSON.stringify(norm(o.text))} states no row count`);
        continue;
      }
      const rendered = Number(m[1].replace(/,/g, ""));
      const actual = truth[name]?.rows;
      if (actual === undefined) {
        optMismatches.push(`${name}: option names a parquet that is not shipped`);
        continue;
      }
      if (rendered !== actual) {
        optMismatches.push(
          `${name}: option says ${rendered.toLocaleString("en-US")} rows, parquet has ${actual.toLocaleString("en-US")}`,
        );
      }
    }
    if (optMismatches.length > 0) {
      errors.push(
        `leg c (/data/): ${optMismatches.length} Explorer option(s) disagree with the shipped parquet — ${optMismatches.join("; ")}`,
      );
    } else if (unregistered.length === 0) {
      notes.push(
        `leg c: all ${options.length} Explorer options registered and row-count-true ✓`,
      );
    }
  }

  // ── leg d: one canonical corpus statement ─────────────────────────────────
  // Independent recompute of the two corpus numbers from the data sidecars.
  //
  // BACKLOG #35 (Sprint 3 round 3): the detail-grade recompute used to be
  // programs.json's LENGTH, which is the /programs/ index — and since backlog
  // #17 that index also carries trajectory-only programs with no J-book detail
  // at all. So the gate agreed with the page while both overstated the tier by
  // two against dim_programs.parquet, which /data/ publishes on the same site.
  // "Detail-grade" is defined by the detail rows, so that is what is counted
  // now, and the parquet's own published row count is checked against it: two
  // artifacts, one number, and a FAIL if they diverge.
  let expectedPages = null;
  let expectedDetail = null;
  let expectedNoDetailGap = 0;
  const pdDir = path.join(jsonDir, "program_details");
  if (fs.existsSync(pdDir)) {
    // Sprint E, Task E3 (ROADMAP #67): dim_programs' row count can now
    // legitimately exceed the detail-grade sidecar count — E1's re-grain
    // added a SYNTHETIC (no-detail) dim_programs row for the non-detail
    // side of each of the 8 appropriation-account collisions (dbt/models/
    // marts/dim_programs.sql's `synth` branch: "there is no R-2/P-40
    // exhibit behind these rows"). programs.json's `account` field is
    // non-null on exactly those 16 split rows, so a sidecar with no detail
    // whose slug carries an account is an EXPECTED gap member, not a
    // divergence.
    const programsPath = path.join(jsonDir, "programs.json");
    const slugsWithAccount = new Set(
      fs.existsSync(programsPath)
        ? JSON.parse(fs.readFileSync(programsPath, "utf8"))
            .filter((p) => p.account !== null && p.account !== undefined)
            .map((p) => p.slug)
        : [],
    );
    const files = fs.readdirSync(pdDir).filter((f) => f.endsWith(".json"));
    expectedPages = files.length;
    let withDetail = 0;
    for (const f of files) {
      let raw;
      try {
        raw = fs.readFileSync(path.join(pdDir, f), "utf8");
      } catch {
        continue;
      }
      const slug = f.slice(0, -".json".length);
      if (!raw.includes('"details"') || /"details":\s*\[\]/.test(raw)) {
        if (slugsWithAccount.has(slug)) expectedNoDetailGap++;
        continue;
      }
      try {
        const d = JSON.parse(raw).details;
        if (Array.isArray(d) && d.length > 0) {
          withDetail++;
        } else if (slugsWithAccount.has(slug)) {
          expectedNoDetailGap++;
        }
      } catch {
        // skip malformed
      }
    }
    expectedDetail = withDetail;
  }
  if (expectedPages === null || expectedDetail === null) {
    errors.push(
      "leg d: cannot recompute corpus numbers — data/site/json/program_details/ missing",
    );
  } else {
    // Cross-check against the parquet inventory /data/ renders. Two shipped
    // artifacts that both claim to describe the detail-grade tier must agree
    // — modulo the known, independently-derived split-key synthetic gap.
    const dsPath = path.join(jsonDir, "datasets.json");
    let declared;
    if (fs.existsSync(dsPath)) {
      declared = (JSON.parse(fs.readFileSync(dsPath, "utf8")).datasets ?? []).find(
        (d) => d.name === "dim_programs",
      )?.row_count;
    }
    if (declared !== undefined && declared !== expectedDetail + expectedNoDetailGap) {
      errors.push(
        `leg d: ${expectedDetail} sidecars carry J-book detail rows and only ` +
          `${expectedNoDetailGap} of the remainder are accounted for by a known ` +
          `split-key synthetic (no-detail) row, but datasets.json publishes ` +
          `dim_programs at ${declared} rows — /data/ and the corpus statement ` +
          `would describe the same tier two different ways`,
      );
    }
    notes.push(
      `leg d: corpus recompute — ${expectedPages} program pages, ${expectedDetail} detail-grade ` +
        `+ ${expectedNoDetailGap} split-key synthetic (dim_programs parquet: ${declared ?? "n/a"}) ✓`,
    );
  }

  const seen = [];
  for (const url of CORPUS_PAGES) {
    const root = readHtml(url);
    if (!root) {
      errors.push(`leg d (${url}): built page missing at ${htmlFor(url)}`);
      continue;
    }
    const els = root.querySelectorAll("[data-corpus-statement]");
    if (els.length === 0) {
      errors.push(
        `leg d (${url}): no [data-corpus-statement] — the canonical corpus block must render on every page that states corpus size`,
      );
      continue;
    }
    for (const el of els) {
      const text = norm(el.text);
      const m = text.match(CORPUS_RE);
      if (!m) {
        errors.push(
          `leg d (${url}): corpus statement does not match the canonical shape — got ${JSON.stringify(text.slice(0, 160))}`,
        );
        continue;
      }
      const pages = Number(m[1].replace(/,/g, ""));
      const detail = Number(m[2].replace(/,/g, ""));
      seen.push({ url, pages, detail });
      if (expectedPages !== null && pages !== expectedPages) {
        errors.push(
          `leg d (${url}): corpus statement says ${pages.toLocaleString("en-US")} browsable program pages, sidecars have ${expectedPages.toLocaleString("en-US")}`,
        );
      }
      if (expectedDetail !== null && detail !== expectedDetail) {
        errors.push(
          `leg d (${url}): corpus statement says ${detail.toLocaleString("en-US")} detail-grade, programs.json has ${expectedDetail.toLocaleString("en-US")}`,
        );
      }
      if (!text.toLowerCase().includes(CORPUS_SCOPE_TAIL)) {
        errors.push(
          `leg d (${url}): corpus statement is missing the §P0-5 scope tail ("${CORPUS_SCOPE_TAIL}")`,
        );
      }
    }
  }
  // Cross-page agreement — the whole point of "one canonical statement".
  const distinct = new Set(seen.map((s) => `${s.pages}/${s.detail}`));
  if (distinct.size > 1) {
    errors.push(
      `leg d: corpus size is stated ${distinct.size} different ways across pages — ${seen
        .map((s) => `${s.url} ${s.pages}/${s.detail}`)
        .join(", ")}`,
    );
  } else if (seen.length === CORPUS_PAGES.length && distinct.size === 1) {
    notes.push(
      `leg d: one corpus statement (${[...distinct][0]}) on all ${CORPUS_PAGES.length} pages ✓`,
    );
  }

  // ── leg e: /methodology/ per-build check counts ───────────────────────────
  // §P1-5, same defect class as the dataset row counts: §3 used to author
  // "197 automated test functions across 42 test modules ... 21 dbt
  // data-model assertions ... 45 question-answer pairs ... ≥41 correct".
  // Every literal had rotted. Each number is now derived at export; this leg
  // recomputes it INDEPENDENTLY from the artifact that defines it (never from
  // site_meta — that is the thing under test) and compares against the
  // rendered text.
  const methodRoot = readHtml("/methodology/");
  if (!methodRoot) {
    errors.push("leg e: built /methodology/ missing");
  } else {
    const el = methodRoot.querySelector("[data-build-checks]");
    if (!el) {
      errors.push(
        "leg e (/methodology/): no [data-build-checks] — §3's per-build check counts must render from build-derived values",
      );
    } else {
      const text = norm(el.text);

      // Independent recomputes from the defining artifacts.
      const expected = {};
      const dbtManifest = path.join(repoRoot, "dbt", "target", "manifest.json");
      if (fs.existsSync(dbtManifest)) {
        const nodes = JSON.parse(fs.readFileSync(dbtManifest, "utf8")).nodes ?? {};
        expected.dbt = Object.values(nodes).filter(
          (n) => n.resource_type === "test",
        ).length;
      }
      const verifyMjs = path.join(__dirname, "..", "verify.mjs");
      if (fs.existsSync(verifyMjs)) {
        expected.gates = (
          fs.readFileSync(verifyMjs, "utf8").match(/gateResults\.push\(\{\s*n:\s*\d+/g) ?? []
        ).length;
      }
      const evalYaml = path.join(repoRoot, "evals", "phase5_questions.yaml");
      if (fs.existsSync(evalYaml)) {
        expected.evalQs = (
          fs.readFileSync(evalYaml, "utf8").match(/^- id:/gm) ?? []
        ).length;
      }
      const vp5 = path.join(repoRoot, "src", "govbudget", "verify_phase5.py");
      if (fs.existsSync(vp5)) {
        const m = fs.readFileSync(vp5, "utf8").match(/^ACCURACY_THRESHOLD\s*=\s*(\d+)/m);
        if (m) expected.evalThreshold = Number(m[1]);
      }

      const checks = [
        [expected.dbt, /([\d,]+)\s+dbt data-model assertions/, "dbt assertions"],
        [expected.gates, /([\d,]+)\s+site verification gates/, "site verification gates"],
        [expected.evalQs, /([\d,]+)\s+question-answer pairs/, "eval questions"],
        [expected.evalThreshold, /at least\s+([\d,]+)\s+correct answers/, "eval threshold"],
      ];
      let checked = 0;
      for (const [want, re, label] of checks) {
        if (want === undefined) continue;
        const m = text.match(re);
        if (!m) {
          errors.push(
            `leg e (/methodology/): §3 states no ${label} — expected ${want} from the defining artifact`,
          );
          continue;
        }
        const got = Number(m[1].replace(/,/g, ""));
        checked += 1;
        if (got !== want) {
          errors.push(
            `leg e (/methodology/): §3 says ${got.toLocaleString("en-US")} ${label}, the defining artifact has ${want.toLocaleString("en-US")}`,
          );
        }
      }
      if (checked === 0) {
        errors.push(
          "leg e: no per-build count could be recomputed (vacuous) — the defining artifacts were all unreadable",
        );
      }
      // The literals this leg exists to prevent must never come back.
      for (const rotted of ["197 automated test", "42 test modules", "45 question-answer"]) {
        if (norm(methodRoot.text).includes(rotted)) {
          errors.push(
            `leg e (/methodology/): the rotted literal "${rotted}" is rendered again — per-build counts must be build-derived`,
          );
        }
      }
      if (errors.every((e) => !e.startsWith("leg e"))) {
        notes.push(
          `leg e: /methodology/ per-build counts match their defining artifacts (${checked} checked) ✓`,
        );
      }
    }
  }

  // ── leg f: table sort determinism ─────────────────────────────────────────
  runSortLeg(errors, notes);

  // ── leg g: curated entity-family merge (§P1-3) ────────────────────────────
  runFamilyMergeLeg(errors, notes);

  // ── leg h: feed claim-vs-data consistency (Sprint 3 Task 1b) ──────────────
  // Returns the corpus recompute so leg i can reuse it: ONE derivation, so
  // the page's prose and the feed's XML are checked against the same truth.
  const feedTruth = runFeedClaimLeg(errors, notes);

  // ── leg i: syndicated feed magnitudes (Sprint 3 Task 2, §P1-8) ────────────
  runFeedFileLeg(errors, notes, feedTruth);

  // ── leg j: count notation swept site-wide (Sprint 3 Task 5, §P1-5) ────────
  runCountNotationLeg(errors, notes);

  // ── leg k: corpus-count provenance (tri-persona Wave 4, item 4) ───────────
  runCorpusCountLeg(errors, notes);

  // ── leg n: held-out link-precision study (ROADMAP #72) ────────────────────
  runLinkPrecisionLeg(errors, notes);

  // ── leg o: hand-adjudication coverage (ROADMAP #109) ──────────────────────
  runLinkAdjudicationLeg(errors, notes);

  // ── leg l: family labels that won a coin flip (ROADMAP #10 A) ─────────────
  runFamilyLabelLeg(errors, notes);

  // ── leg m: declared cadence vs. measured ingest age (ROADMAP #8) ──────────
  runSourceCadenceLeg(errors, notes);

  // ── leg p: crosswalk-count provenance (PM-S3 leftover) ────────────────────
  runCrosswalkCountLeg(errors, notes);

  // ── leg q: announcement LLM-pass scope (findings log :118-119) ────────────
  runAnnouncementScopeLeg(errors, notes);

  // ── leg r: district by-year cells vs the lake (ROADMAP #6) ────────────────
  runDistrictYearLeg(errors, notes);

  return { pass: errors.length === 0, errors, notes };
}

// ═══════════════════════════════════════════════════════════════════════════
// leg j — count notation, swept (§P1-5)
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Nouns whose preceding integer is a CARDINALITY the site is stating about
 * itself. Deliberately not "every number": the corpus is full of budget codes
 * and fiscal years, and a sweep that flags those is a sweep nobody keeps.
 */
const COUNT_NOUNS =
  "programs?|program elements?|companies|districts?|filings?|mentions?|" +
  "awards?|award records?|facts?|datasets?|rows?|records?|signals?|pages?|" +
  "citations?|line items?|event types?|entries|elements?";
const BARE_BEFORE_NOUN = new RegExp(
  String.raw`(?<![\d,.])(\d{4,})(?![\d,.])\s+(?:of\s+[\d,]+\s+)?(?:${COUNT_NOUNS})\b`,
  "gi",
);
/** "N of M" in either position — the /years/ filter summary's exact shape. */
const BARE_IN_OF = new RegExp(
  String.raw`(?<![\d,.])(\d{4,})(?![\d,.])\s+of\s+|(?:\bof\s+)(?<![\d,.])(\d{4,})(?![\d,.])`,
  "gi",
);

/** A fiscal/calendar year is not a cardinality. */
function isYear(n) {
  return n >= 1900 && n <= 2099;
}

/**
 * Pages whose numbers this leg MUST actually reach. /methodology/ carried
 * data-source-text on its whole container, so the sweep deleted the entire
 * page before scanning it (backlog #38) — and a sweep that silently scans
 * nothing on the page arguing for the site's rigour is worse than no sweep.
 * The page is site-authored prose, so its count notation is ours to get right.
 *
 * The guard is COVERAGE, not a count: the numeric leaves the sweep reaches,
 * over the numeric leaves the page renders. A bare ">= 1" would have been
 * satisfied by the site chrome alone (the header and footer sit outside the
 * page container and carry one), which is to say it would have passed the
 * exact defect it exists to catch.
 */
const MUST_BE_SWEPT = ["methodology/index.html"];
/** Share of a MUST_BE_SWEPT page's numeric leaves the sweep has to reach. */
const MIN_SWEEP_COVERAGE = 0.9;

function runCountNotationLeg(errors, notes) {
  const files = [...walkHtml(outDir)];
  if (files.length === 0) {
    errors.push(`leg j: no built HTML under ${outDir} — the sweep is vacuous`);
    return;
  }
  const failures = [];
  let textNodes = 0;
  let groupedSeen = 0;
  /** @type {Map<string, number>} numeric leaf elements reached, per page */
  const sweptPerFile = new Map();
  /** @type {Map<string, number>} numeric leaf elements the page RENDERS */
  const totalPerFile = new Map();
  const mustBeSwept = new Set(MUST_BE_SWEPT);

  /** Numeric leaf elements under `el` — the sweep's own unit of scanning. */
  const countNumericLeaves = (el) => {
    const kids = el.childNodes.filter((c) => c.nodeType === 1);
    if (kids.length === 0) {
      const t = el.text;
      return t && /\d/.test(t) ? 1 : 0;
    }
    let n = 0;
    for (const c of kids) n += countNumericLeaves(c);
    return n;
  };

  for (const file of files) {
    let root;
    try {
      root = parse(fs.readFileSync(file, "utf8"), { comment: false });
    } catch {
      continue;
    }
    for (const el of root.querySelectorAll("script, style, noscript, template")) {
      el.remove();
    }
    // Denominator for the coverage guard, taken BEFORE any source-text
    // subtree is removed, on the pages that must not be able to hide.
    const relForTotal = path.relative(outDir, file);
    if (mustBeSwept.has(relForTotal)) {
      totalPerFile.set(relForTotal, countNumericLeaves(root));
    }
    // Quoted source text is skipped — but only the KINDS that earn it. Until
    // backlog #38 the marker's presence alone deleted the subtree, which is
    // how /methodology/ (site-authored prose, quoted from nothing) vanished
    // from this sweep entirely. source-text-kinds.mjs decides, and both this
    // leg and render-static's currency scan read the same table.
    for (const el of root.querySelectorAll("[data-source-text]")) {
      if (exemptFromNotationSweep(el.getAttribute("data-source-text"))) {
        el.remove();
      }
    }
    const rel = path.relative(outDir, file);
    // Per LEAF ELEMENT — see the leg's header for why neither a per-text-node
    // nor a per-subtree scan works.
    const walk = (el) => {
      const childEls = el.childNodes.filter((c) => c.nodeType === 1);
      if (childEls.length === 0) {
        const t = el.text;
        if (!t || !/\d/.test(t)) return;
        textNodes += 1;
        sweptPerFile.set(rel, (sweptPerFile.get(rel) ?? 0) + 1);
        if (/\d,\d{3}/.test(t)) groupedSeen += 1;
        for (const re of [BARE_BEFORE_NOUN, BARE_IN_OF]) {
          re.lastIndex = 0;
          let m;
          while ((m = re.exec(t))) {
            const raw = m[1] ?? m[2];
            if (!raw) continue;
            const n = Number(raw);
            if (isYear(n)) continue;
            // Equipment designators are names, not counts: "DDG 1000 award
            // concentration" (Zumwalt class) must not be rewritten "DDG
            // 1,000". Exempt a number immediately preceded by a 2-4 letter
            // uppercase hull/type prefix (DDG, SSN, CVN, LPD, KC, CH…).
            // Added 2026-09-01 when the FPDS-AP expansion put ship-class
            // program titles into feed headlines for the first time.
            const before = t.slice(Math.max(0, m.index - 6), m.index);
            if (/(^|[^A-Za-z])[A-Z]{2,4}[- ]$/.test(before)) continue;
            failures.push({
              file: rel,
              snippet: t
                .slice(Math.max(0, m.index - 45), m.index + m[0].length + 15)
                .replace(/\s+/g, " ")
                .trim(),
              want: n.toLocaleString("en-US"),
              got: raw,
            });
          }
        }
        return;
      }
      for (const c of childEls) walk(c);
    };
    walk(root);
    if (failures.length > 60) break;
  }

  // Per-page non-vacuity: a page that re-hides itself behind a wholesale
  // marker contributes zero numeric leaves and fails here, rather than
  // passing as "no violations". Only checked when the sweep ran to completion
  // (the failure cap below can stop it early, and failures fail the leg anyway).
  const unswept =
    failures.length === 0
      ? MUST_BE_SWEPT.map((f) => ({
          file: f,
          reached: sweptPerFile.get(f) ?? 0,
          total: totalPerFile.get(f) ?? 0,
        })).filter(
          (s) => s.total === 0 || s.reached / s.total < MIN_SWEEP_COVERAGE,
        )
      : [];

  if (failures.length > 0) {
    errors.push(
      `leg j: ${failures.length} ungrouped count(s) rendered — §P1-5 says one ` +
        `notation for one number (first 10):`,
    );
    for (const f of failures.slice(0, 10)) {
      errors.push(`  ${f.file}: "${f.snippet}" — write ${f.want}, not ${f.got}`);
    }
    if (failures.length > 10) {
      errors.push(`  ... and ${failures.length - 10} more`);
    }
  } else if (unswept.length > 0) {
    for (const s of unswept) {
      errors.push(
        `leg j reached ${s.reached} of ${s.total} numeric leaf element(s) on ` +
          `${s.file} — under the ${Math.round(MIN_SWEEP_COVERAGE * 100)}% this ` +
          `page must be swept at. Its numbers are hiding behind a ` +
          `[data-source-text] marker again (or the page stopped building). ` +
          `backlog #38 is the history here.`,
      );
    }
  } else if (groupedSeen === 0) {
    errors.push(
      `leg j is VACUOUS: ${textNodes} text node(s) carrying digits, but not one ` +
        `grouped figure anywhere — the sweep would pass an empty site`,
    );
  } else {
    notes.push(
      `leg j count notation: ${files.length} page(s), ${textNodes} numeric text ` +
        `node(s), ${groupedSeen} grouped — 0 bare 4+-digit cardinalities ` +
        `(/methodology/ coverage ${sweptPerFile.get(MUST_BE_SWEPT[0]) ?? 0}/` +
        `${totalPerFile.get(MUST_BE_SWEPT[0]) ?? 0} numeric leaves) ✓`,
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// leg f — table sort determinism (§P1-7)
// ═══════════════════════════════════════════════════════════════════════════
//
// `/company/lockheed-martin/` rendered its Lobbying Activity years as
// 2024, 2026, 2025. fct_influence had no ORDER BY, so the table showed
// whatever order the query returned; 33 of the 66 families with filings were
// out of order, and the same class of defect ran through mentions, awards,
// linked-program chips and filing sub-lists. On a site whose entire claim is
// "check our work", a visibly unsorted table invites doubt about the numbers
// in it.
//
// The contract every data table now ships, and this leg enforces:
//   [data-sort-table="<name>"] [data-sort-order="<key>:asc|desc"]   container
//   [data-sort-value="<v>"]                                          each row
// data-sort-value is the COMPARATOR'S OWN INPUT, serialized — not a rendered
// cell — so what is checked is the order the sort actually produced.
//
// Two halves, because either alone is toothless:
//   (1) REQUIRED: an enumerated set of (page, table) pairs must be present
//       with the exact declared order. Deleting an attribute, or quietly
//       flipping a table to `asc`, fails — it cannot pass by vanishing.
//   (2) SWEEP: across a large page sample, EVERY [data-sort-table] found must
//       be monotonic in its declared direction. New tables are covered the
//       day they ship the contract.

/** (page, table, declared order, min rows) pairs that MUST exist. */
const SORT_CONTRACTS = [
  // The reported repro. Lockheed has three filing years — 2026, 2025, 2024.
  ["/company/lockheed-martin/", "lobbying-activity", "filing_year:desc", 3],
  ["/companies/", "companies", "total_obligation:desc", 100],
  ["/programs/", "programs", "fy2026_total:desc", 100],
  ["/filings/", "filings", "mentions_then_year_desc_then_client:asc", 25],
  // CO-05 dropped out of the built district set in the 2026-09-01
  // hand-adjudication correction; VA-11 is a surviving district with 3 rows.
  ["/district/VA-11/", "district-programs", "total_obligation:desc", 3],
];

/** Directories under out/ swept for the monotonicity check, and how many. */
const SORT_SWEEP = [
  ["company", 200],
  ["district", 120],
  ["program", 80],
];

/**
 * Compare two data-sort-value strings the way the page's comparator does:
 * numerically when BOTH parse as numbers (including the ±Infinity sentinels
 * the tables emit for missing values), else by localeCompare — which is what
 * the string-keyed sorts use, evaluated in this same Node/ICU during SSG.
 */
function sortCmp(a, b) {
  const an = Number(a);
  const bn = Number(b);
  const aNum = a.trim() !== "" && !Number.isNaN(an);
  const bNum = b.trim() !== "" && !Number.isNaN(bn);
  if (aNum && bNum) return an === bn ? 0 : an < bn ? -1 : 1;
  return a.localeCompare(b);
}

/**
 * Check one container. Returns null when monotonic, else a description of the
 * FIRST violating adjacent pair (the shape a human can act on).
 */
function checkSortedContainer(el) {
  const order = el.getAttribute("data-sort-order") ?? "";
  const m = order.match(/^([A-Za-z0-9_]+):(asc|desc)$/);
  if (!m) {
    return `declares data-sort-order=${JSON.stringify(order)}, which is not "<key>:asc|desc"`;
  }
  const dir = m[2];
  const rows = el.querySelectorAll("[data-sort-value]");
  const values = rows.map((r) => r.getAttribute("data-sort-value") ?? "");
  for (let i = 1; i < values.length; i++) {
    const cmp = sortCmp(values[i - 1], values[i]);
    const bad = dir === "desc" ? cmp < 0 : cmp > 0;
    if (bad) {
      return (
        `${order} is violated at rows ${i}→${i + 1}: ` +
        `${JSON.stringify(values[i - 1])} then ${JSON.stringify(values[i])}` +
        ` (rendered ${values.length} rows)`
      );
    }
  }
  return null;
}

/** Every built .html under out/, recursively. */
function* walkHtml(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, entry.name);
    if (entry.isDirectory()) yield* walkHtml(p);
    else if (p.endsWith(".html")) yield p;
  }
}

/** Every built index.html under out/<dir>/, capped at `limit`, sorted. */
function sampleBuiltPages(dir, limit) {
  const root = path.join(outDir, dir);
  if (!fs.existsSync(root)) return [];
  return fs
    .readdirSync(root, { withFileTypes: true })
    .filter((e) => e.isDirectory())
    .map((e) => path.join(root, e.name, "index.html"))
    .filter((p) => fs.existsSync(p))
    .sort()
    .slice(0, limit);
}

function runSortLeg(errors, notes) {
  // ── (1) the enumerated contracts ────────────────────────────────────────
  let contractsOk = 0;
  for (const [url, table, expectOrder, minRows] of SORT_CONTRACTS) {
    const root = readHtml(url);
    if (!root) {
      errors.push(`leg f (${url}): built page missing at ${htmlFor(url)}`);
      continue;
    }
    const el = root.querySelector(`[data-sort-table="${table}"]`);
    if (!el) {
      errors.push(
        `leg f (${url}): no [data-sort-table="${table}"] — every data table must declare its default sort`,
      );
      continue;
    }
    const declared = el.getAttribute("data-sort-order");
    if (declared !== expectOrder) {
      errors.push(
        `leg f (${url} ${table}): declares data-sort-order=${JSON.stringify(
          declared,
        )}, expected ${JSON.stringify(expectOrder)}`,
      );
      continue;
    }
    const nRows = el.querySelectorAll("[data-sort-value]").length;
    if (nRows < minRows) {
      errors.push(
        `leg f (${url} ${table}): only ${nRows} row(s) carry data-sort-value — expected ≥${minRows} (a table that renders nothing cannot prove it is sorted)`,
      );
      continue;
    }
    const violation = checkSortedContainer(el);
    if (violation) {
      errors.push(`leg f (${url} ${table}): ${violation}`);
      continue;
    }
    contractsOk += 1;
  }
  if (contractsOk === SORT_CONTRACTS.length) {
    notes.push(
      `leg f: all ${SORT_CONTRACTS.length} declared table sorts present and monotonic (incl. lobbying-activity year desc) ✓`,
    );
  }

  // ── (2) the sweep ───────────────────────────────────────────────────────
  const sweepViolations = [];
  let sweptPages = 0;
  let sweptTables = 0;
  for (const [dir, limit] of SORT_SWEEP) {
    const pages = sampleBuiltPages(dir, limit);
    if (pages.length === 0) {
      errors.push(
        `leg f sweep: no built pages under out/${dir}/ — the sweep would be vacuous`,
      );
      continue;
    }
    for (const p of pages) {
      sweptPages += 1;
      const root = parse(fs.readFileSync(p, "utf8"));
      for (const el of root.querySelectorAll("[data-sort-table]")) {
        // Containers with 0-1 rows are trivially sorted; still counted, so a
        // build that renders every table empty cannot inflate the tally.
        sweptTables += 1;
        const violation = checkSortedContainer(el);
        if (violation) {
          sweepViolations.push(
            `${path.relative(outDir, p)} [${el.getAttribute("data-sort-table")}]: ${violation}`,
          );
        }
      }
    }
  }
  if (sweptTables < 100) {
    errors.push(
      `leg f sweep: only ${sweptTables} declared tables found across ${sweptPages} pages — expected ≥100 (non-vacuous check)`,
    );
  }
  if (sweepViolations.length > 0) {
    errors.push(
      `leg f sweep: ${sweepViolations.length} table(s) render out of their declared order — ${sweepViolations
        .slice(0, 5)
        .join(" | ")}`,
    );
  } else if (sweptTables >= 100) {
    notes.push(
      `leg f sweep: ${sweptTables} declared tables across ${sweptPages} pages, all monotonic ✓`,
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// leg g — the curated entity-family merge held (§P1-3)
// ═══════════════════════════════════════════════════════════════════════════
//
// The defect: `/companies/` listed RAYTHEON COMPANY $43.7B at #4 and RTX CORP
// $24.6B at #6. One company — Raytheon renamed to RTX in 2023 — split across
// two rows, understating the combined position by roughly half and misordering
// the top ten.
//
// Two assertions, both on the BUILT artifact, both recomputed from the SEED
// (data-seeds/entity_family_events.csv) rather than from the payload the page
// was rendered from — so an exporter that dropped or mangled a curated family
// cannot satisfy this leg by also mangling its own output:
//
//   (1) THE MERGE HELD. Every row of /companies/ declares the registry family
//       keys it renders in [data-family-keys]. No two rows may carry keys that
//       the curated seed assigns to the same family; and every seed family with
//       ≥2 keys present on the page must be on exactly ONE row. This is the
//       double-count/split check in its rendered form.
//   (2) EVERY SOURCE IS AN EXTERNAL REFERENCE. Each curated event's source_url
//       must render on /companies/families/ as an <a href> to that exact URL,
//       opening off-site. These rows cite documents outside the lake; if one
//       ever rendered as a warehouse citation chip (or lost its link), the page
//       would be claiming provenance it does not have.
//
// Vacuity guards: the seed must parse, must carry ≥10 events, and must resolve
// ≥1 multi-member family against the page — a leg that checks nothing passes
// nothing.

const FAMILY_EVENTS_SEED = path.resolve(
  repoRoot,
  "data-seeds",
  "entity_family_events.csv",
);
const MIN_CURATED_EVENTS = 10;

/** Minimal RFC-4180 CSV reader (quoted fields with embedded commas). */
function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i++;
        } else {
          quoted = false;
        }
      } else {
        field += c;
      }
      continue;
    }
    if (c === '"') quoted = true;
    else if (c === ",") {
      row.push(field);
      field = "";
    } else if (c === "\n") {
      row.push(field);
      field = "";
      if (row.some((f) => f.trim() !== "")) rows.push(row);
      row = [];
    } else if (c !== "\r") {
      field += c;
    }
  }
  row.push(field);
  if (row.some((f) => f.trim() !== "")) rows.push(row);
  const header = rows.shift() ?? [];
  return rows.map((r) => Object.fromEntries(header.map((h, i) => [h.trim(), r[i] ?? ""])));
}

/**
 * Independent recompute of govbudget.entities.normalize_name — the normalizer
 * that MINTED the warehouse family keys. Deliberately reimplemented here so a
 * change to the Python side that silently stops matching shows up as a gate
 * failure rather than as a quietly unmerged table.
 */
const LEGAL_SUFFIXES = new Set([
  "INC", "INCORPORATED", "LLC", "LLP", "LP", "LTD", "LIMITED", "CORP",
  "CORPORATION", "CO", "COMPANY", "PLC", "GMBH", "SA", "AG", "PTY",
  "JV", "TRUST", "FOUNDATION", "REALTY",
]);

function normalizeName(name) {
  let up = (name || "").toUpperCase();
  up = up.replace(/(?<=[A-Z])\.(?=[A-Z])/g, "");
  up = up.replace(/[^A-Z0-9 ]+/g, " ");
  let tokens = up.split(/\s+/).filter(Boolean);
  if (tokens[0] === "THE") tokens.shift();
  let changed = true;
  while (changed && tokens.length) {
    changed = false;
    while (tokens.length && LEGAL_SUFFIXES.has(tokens[tokens.length - 1])) {
      tokens.pop();
      changed = true;
    }
    while (tokens.length && tokens[tokens.length - 1] === "THE") {
      tokens.pop();
      changed = true;
    }
    while (tokens.length && tokens[0] === "THE") {
      tokens.shift();
      changed = true;
    }
  }
  return tokens.join(" ");
}

function runFamilyMergeLeg(errors, notes) {
  if (!fs.existsSync(FAMILY_EVENTS_SEED)) {
    errors.push(
      `leg g: curated seed missing at ${FAMILY_EVENTS_SEED} — /companies/ would go ` +
        `back to splitting renamed companies with nothing to notice it`,
    );
    return;
  }
  const events = parseCsv(fs.readFileSync(FAMILY_EVENTS_SEED, "utf8"));
  if (events.length < MIN_CURATED_EVENTS) {
    errors.push(
      `leg g: curated seed has ${events.length} events, expected ≥${MIN_CURATED_EVENTS} ` +
        `(a near-empty table cannot be the publishable asset it is meant to be)`,
    );
    return;
  }

  // seed → family label → the set of normalized endpoint names it claims.
  const seedFamilies = new Map();
  for (const ev of events) {
    const label = (ev.family || "").trim();
    if (!label) continue;
    if (!seedFamilies.has(label)) seedFamilies.set(label, new Set());
    const keys = seedFamilies.get(label);
    for (const name of [label, ev.from_name, ev.to_name]) {
      const n = normalizeName(name);
      if (n) keys.add(n);
    }
  }

  // ── (1) the merge held, on the rendered page ─────────────────────────────
  const companies = readHtml("/companies/");
  if (!companies) {
    errors.push("leg g: built /companies/ missing");
  } else {
    const rows = companies.querySelectorAll("[data-family-keys]");
    if (rows.length < 50) {
      errors.push(
        `leg g (/companies/): only ${rows.length} rows carry [data-family-keys] — ` +
          `every row must declare the registry families it renders`,
      );
    }
    // rendered key → the row that rendered it
    const rowOfKey = new Map();
    const keysOfRow = [];
    rows.forEach((tr, i) => {
      const keys = (tr.getAttribute("data-family-keys") || "")
        .split("|")
        .map((k) => k.trim())
        .filter(Boolean);
      keysOfRow.push(keys);
      for (const k of keys) {
        if (rowOfKey.has(k)) {
          errors.push(
            `leg g (/companies/): registry family ${k} is rendered on two rows ` +
              `(${rowOfKey.get(k)} and ${i}) — its obligations are counted twice`,
          );
        }
        rowOfKey.set(k, i);
      }
    });

    let checkedFamilies = 0;
    for (const [label, keys] of seedFamilies) {
      const present = [...keys].filter((k) => rowOfKey.has(k));
      if (present.length < 2) continue; // nothing on this page to merge
      checkedFamilies++;
      const rowIds = new Set(present.map((k) => rowOfKey.get(k)));
      if (rowIds.size !== 1) {
        errors.push(
          `leg g (/companies/): curated family "${label}" is SPLIT across ` +
            `${rowIds.size} rows — ${present
              .map((k) => `${k}→row ${rowOfKey.get(k)}`)
              .join(", ")}. One company must be one line (§P1-3).`,
        );
      }
    }
    if (checkedFamilies === 0) {
      errors.push(
        "leg g (/companies/): no curated family has ≥2 members on the page — " +
          "the merge check is vacuous, which means the merge is not happening",
      );
    } else if (errors.every((e) => !e.startsWith("leg g"))) {
      notes.push(
        `leg g: ${checkedFamilies} curated families each on exactly one of ` +
          `${rows.length} /companies/ rows ✓`,
      );
    }

    // The Raytheon/RTX repro by name, so this leg names the reported defect.
    const rtxKeys = ["RAYTHEON", "RTX"].filter((k) => rowOfKey.has(k));
    if (rtxKeys.length === 2 && rowOfKey.get("RAYTHEON") !== rowOfKey.get("RTX")) {
      errors.push(
        "leg g (/companies/): RAYTHEON and RTX are still on separate rows — " +
          "the reported §P1-3 defect",
      );
    }
  }

  // ── (2) every curated source renders as an external reference ────────────
  const familiesPage = readHtml("/companies/families/");
  if (!familiesPage) {
    errors.push(
      "leg g: built /companies/families/ missing — the curated table is the " +
        "publishable asset and must have its own page",
    );
    return;
  }
  const hrefs = new Set(
    familiesPage.querySelectorAll("a[href]").map((a) => a.getAttribute("href")),
  );
  const missing = [];
  for (const ev of events) {
    const url = (ev.source_url || "").trim();
    if (!url) continue;
    if (!url.startsWith("https://")) {
      errors.push(`leg g: curated source is not https — ${url}`);
      continue;
    }
    if (!hrefs.has(url)) missing.push(url);
  }
  if (missing.length > 0) {
    errors.push(
      `leg g (/companies/families/): ${missing.length} curated event source(s) do ` +
        `not render as an external reference — ${missing.slice(0, 3).join(", ")}`,
    );
  }
  // …and they must be real off-site links, not internal chips.
  const externals = familiesPage.querySelectorAll("a[data-external-source]");
  const badTarget = externals.filter(
    (a) => a.getAttribute("target") !== "_blank" || !(a.getAttribute("rel") || "").includes("noopener"),
  );
  if (badTarget.length > 0) {
    errors.push(
      `leg g (/companies/families/): ${badTarget.length} source link(s) are not ` +
        `off-site links (target=_blank rel=noopener) — these are external ` +
        `references, not warehouse citations`,
    );
  }
  // The page must SAY so, in its own words.
  const methodText = (
    familiesPage.querySelector("[data-method-statement]")?.text ?? ""
  ).toLowerCase();
  for (const phrase of [
    "hand-curated",
    "external references, not warehouse citations",
    "nothing on it is",
  ]) {
    if (!methodText.includes(phrase)) {
      errors.push(
        `leg g (/companies/families/): the method statement does not say ` +
          `"${phrase}" — the page must state its method plainly (§P1-3)`,
      );
    }
  }
  if (errors.every((e) => !e.startsWith("leg g"))) {
    notes.push(
      `leg g: all ${events.length} curated sources render as external ` +
        `references on /companies/families/ ✓`,
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// leg h — feed claim-vs-data consistency (PM-review Sprint 3 Task 1b)
// ═══════════════════════════════════════════════════════════════════════════
//
// /feed/ published 87 cards reading "<program> zeroed out in FY2026 (had $0 in
// FY25)". Both halves were false. 0601101E "Defense Research Sciences" had
// $293.1M in FY2025, and the corpus holds no FY2026 figure for it at all —
// the mart's `coalesce(fy2026_total, 0) = 0` turned absence into a zeroing.
//
// WHY every existing gate missed it. Gates 23/24 verify that a DISPLAYED
// NUMBER matches its CITED FACT. Here the citation was valid and the number
// really was 0 — the falsehood lived in the SENTENCE WRAPPED AROUND the
// number. No gate read the prose as a claim. This leg does: it parses what
// each card ASSERTS and checks that assertion against the corpus.
//
// The rule, stated as narrowly as it can honestly be stated:
//
//   A card may claim a program was zeroed/ended/eliminated in FY N only when
//   the corpus holds a figure for that PE in FY N and that figure is zero.
//   Absence of a figure FAILS. A non-zero figure FAILS.
//
// Absence failing is the load-bearing half — it is the exact live defect, and
// it is why this leg cannot be satisfied by a mart that simply coalesces.
//
// Truth comes from budget_lines.parquet via feedclaims-recompute.py: the raw
// workbook grain, upstream of fct_feed_events (which generated the claims) and
// of feed.json (which rendered them). The leg reads RENDERED HTML, never the
// sidecar, so a page cannot pass by shipping correct JSON alongside false prose.
//
// h2 additionally re-derives every yoy_swing card's stated direction and
// percentage from the same parquet. That is what keeps this leg non-vacuous
// while the zeroed class is empty, and it is a direct guard against the
// second defect of Sprint 3 Task 1b — the exporter formatting the WRONG
// variable (comparison_value instead of headline_value), a swap that no test
// caught because both variables were legitimately present on the row.

/** Claims of termination. Group 1 = the fiscal year asserted. */
const TERMINATION_RE =
  /\b(?:zeroed out|zeroed|ended|eliminated|terminated|cancelled|canceled)\b[^.]*?\bFY\s?(\d{4})\b/i;

/** "had $293.1M in FY25" — the money clause on a termination card. */
const HAD_MONEY_RE = /\bhad\s+(\$[\d.]+[KMBT]?)\s+in\s+FY\s?(\d{2,4})\b/i;

/** "increased 3053%" / "decreased 64%" — yoy_swing's assertion. */
const SWING_RE = /\b(increased|decreased)\s+([\d.]+)%/i;

/** data-xml-path="site:feed/{event_type}/{pe_bli|family_key}" */
const XMLPATH_RE = /^site:feed\/([^/]+)\/(.+)$/;

/** A feed with fewer cards than this is a parse failure, not a pass. */
const MIN_FEED_CARDS = 30;

/** yoy percentages are rendered with 0 decimals; allow rounding slack. */
const PCT_TOLERANCE = 1.0;

/** Independent corpus recompute (DuckDB over budget_lines.parquet). */
function recomputeFeedClaims() {
  const script = path.join(__dirname, "feedclaims-recompute.py");
  const res = spawnSync("uv", ["run", "python", script], {
    cwd: repoRoot,
    encoding: "utf8",
    timeout: 300000,
    maxBuffer: 64 * 1024 * 1024,
  });
  if (res.status !== 0) {
    throw new Error(
      `feedclaims-recompute.py failed (status ${res.status}): ${
        (res.stderr || "").slice(-800)
      }`,
    );
  }
  const parsed = JSON.parse(res.stdout);
  if (parsed.__error__) throw new Error(parsed.__error__);
  return parsed;
}

/** "$293.1M" → 293100 (USD thousands), mirroring export_site._fmt_thousands. */
function parseCompactThousands(s) {
  const m = String(s).match(/^\$([\d.]+)([KMBT]?)$/);
  if (!m) return null;
  const n = Number(m[1]);
  if (!Number.isFinite(n)) return null;
  const mult = { "": 1e-3, K: 1, M: 1e3, B: 1e6, T: 1e9 }[m[2]];
  return n * mult;
}

/** Render a thousands figure the way the exporter would, for comparison. */
function fmtThousands(v) {
  const raw = Number(v) * 1000;
  const a = Math.abs(raw);
  if (a >= 1e12) return `$${(raw / 1e12).toFixed(1)}T`;
  if (a >= 1e9) return `$${(raw / 1e9).toFixed(1)}B`;
  if (a >= 1e6) return `$${(raw / 1e6).toFixed(1)}M`;
  if (a >= 1e3) return `$${(raw / 1e3).toFixed(1)}K`;
  return `$${raw.toFixed(0)}`;
}

function runFeedClaimLeg(errors, notes) {
  let truth;
  try {
    truth = recomputeFeedClaims();
  } catch (e) {
    errors.push(`leg h: corpus recompute failed — ${e.message}`);
    return null;
  }

  const feed = readHtml("/feed/");
  if (!feed) {
    errors.push(
      `leg h: built /feed/ missing at ${htmlFor("/feed/")} — run npm run build`,
    );
    return truth;
  }

  const cardEls = feed.querySelectorAll("[data-feed-card]");
  if (cardEls.length < MIN_FEED_CARDS) {
    errors.push(
      `leg h (/feed/): only ${cardEls.length} [data-feed-card] elements — ` +
        `expected ≥${MIN_FEED_CARDS} (a feed that renders nothing cannot ` +
        `prove its claims are true)`,
    );
    return truth;
  }

  let terminationClaims = 0;
  let swingClaims = 0;
  let moneyClaims = 0;

  for (const el of cardEls) {
    const headEl = el.querySelector('[data-source-text="headline"]');
    if (!headEl) {
      errors.push(
        `leg h (/feed/): a card renders no [data-source-text="headline"] — ` +
          `every claim must be readable as prose to be checkable`,
      );
      continue;
    }
    const headline = norm(headEl.text);
    const xmlPath = headEl.getAttribute("data-xml-path") ?? "";
    const pathMatch = xmlPath.match(XMLPATH_RE);
    if (!pathMatch) {
      errors.push(
        `leg h (/feed/): card headline carries unparseable data-xml-path ` +
          `${JSON.stringify(xmlPath)} — the gate cannot bind the claim to a program`,
      );
      continue;
    }
    const [, eventType, entity] = pathMatch;
    const corpus = truth[entity];

    // ── h1: termination claims need positive evidence ────────────────────
    const term = headline.match(TERMINATION_RE);
    if (term) {
      terminationClaims += 1;
      const fy = term[1];
      if (fy !== "2026") {
        errors.push(
          `leg h1 (/feed/ ${entity}): claims termination in FY${fy}, but the ` +
            `corpus recompute only covers FY2026 — extend ` +
            `feedclaims-recompute.py before publishing this claim: ${JSON.stringify(headline)}`,
        );
        continue;
      }
      if (!corpus) {
        errors.push(
          `leg h1 (/feed/ ${entity}): claims "${fy} zeroed" but the corpus ` +
            `holds NO budget lines for this PE at all — a claim about a ` +
            `program we have no data for: ${JSON.stringify(headline)}`,
        );
        continue;
      }
      const fy26 = corpus.fy2026_total ?? { present: false, value: null };
      const fy26any = corpus.fy2026_any ?? { present: false, value: null };
      if (!fy26.present && !fy26any.present) {
        errors.push(
          `leg h1 (/feed/ ${entity}): claims the program was zeroed in FY${fy}, ` +
            `but the corpus holds NO FY2026 figure for it — absence of ` +
            `evidence is not evidence of zero (the source workbook cell is ` +
            `BLANK, which commonly means a program-element restructuring, ` +
            `not a termination): ${JSON.stringify(headline)}`,
        );
        continue;
      }
      // Prefer fy2026_total — the single canonical TOA figure. fy2026_any is
      // a SUM across fy_2026_* amount types (disc request + reconciliation +
      // total) and so double-counts; it is sound for "is this zero?" (a sum of
      // zeros is zero, any non-zero makes it non-zero) but must not be quoted
      // as if it were one figure.
      const observed = fy26.present ? fy26.value : fy26any.value;
      if (observed !== 0) {
        const shown = fy26.present
          ? `${fmtThousands(observed)} of FY2026 money`
          : `FY2026 money for it (no fy_2026_total row, but its fy_2026_* ` +
            `rows are not all zero)`;
        errors.push(
          `leg h1 (/feed/ ${entity}): claims the program was zeroed in FY${fy}, ` +
            `but the corpus holds ${shown}: ${JSON.stringify(headline)}`,
        );
        continue;
      }
      // ── money clause on a termination card ──────────────────────────────
      const money = headline.match(HAD_MONEY_RE);
      if (money) {
        moneyClaims += 1;
        const stated = parseCompactThousands(money[1]);
        const yr = money[2].length === 2 ? `20${money[2]}` : money[2];
        if (yr !== "2025") {
          errors.push(
            `leg h1 (/feed/ ${entity}): money clause names FY${yr}, outside ` +
              `the recompute's FY2025 coverage: ${JSON.stringify(headline)}`,
          );
          continue;
        }
        const base = corpus.fy2025_total?.present
          ? corpus.fy2025_total
          : corpus.fy2025_enacted ?? { present: false, value: null };
        if (!base.present) {
          errors.push(
            `leg h1 (/feed/ ${entity}): states it "had ${money[1]} in FY${money[2]}" ` +
              `but the corpus holds no FY2025 figure for it: ${JSON.stringify(headline)}`,
          );
          continue;
        }
        if (stated === null || fmtThousands(base.value) !== money[1]) {
          errors.push(
            `leg h1 (/feed/ ${entity}): states it "had ${money[1]} in FY${money[2]}", ` +
              `the corpus says ${fmtThousands(base.value)} — the sentence is ` +
              `formatting the wrong variable: ${JSON.stringify(headline)}`,
          );
        }
      }
      continue;
    }

    // ── h2: yoy_swing direction + magnitude re-derived from the parquet ───
    if (eventType === "yoy_swing") {
      const swing = headline.match(SWING_RE);
      if (!swing) continue;
      if (!corpus) {
        errors.push(
          `leg h2 (/feed/ ${entity}): yoy_swing card for a PE with no budget ` +
            `lines in the corpus: ${JSON.stringify(headline)}`,
        );
        continue;
      }
      const fy26 = corpus.fy2026_total ?? { present: false, value: null };
      const fy25 = corpus.fy2025_total?.present
        ? corpus.fy2025_total
        : corpus.fy2025_enacted ?? { present: false, value: null };
      if (!fy26.present || !fy25.present || !fy25.value) {
        errors.push(
          `leg h2 (/feed/ ${entity}): asserts a FY25→FY26 change but the ` +
            `corpus is missing one side (FY2025 present=${fy25.present}, ` +
            `FY2026 present=${fy26.present}) — a change between a number and ` +
            `a blank is not a change: ${JSON.stringify(headline)}`,
        );
        continue;
      }
      swingClaims += 1;
      const pct = (100.0 * (fy26.value - fy25.value)) / fy25.value;
      const statedDir = swing[1].toLowerCase();
      const actualDir = pct >= 0 ? "increased" : "decreased";
      if (statedDir !== actualDir) {
        errors.push(
          `leg h2 (/feed/ ${entity}): says "${statedDir}" but the corpus shows ` +
            `${actualDir} (FY25 ${fmtThousands(fy25.value)} → FY26 ` +
            `${fmtThousands(fy26.value)}): ${JSON.stringify(headline)}`,
        );
        continue;
      }
      const statedPct = Number(swing[2]);
      if (Math.abs(statedPct - Math.abs(pct)) > PCT_TOLERANCE) {
        errors.push(
          `leg h2 (/feed/ ${entity}): states ${statedPct}% but the corpus ` +
            `recomputes ${Math.abs(pct).toFixed(1)}% (FY25 ` +
            `${fmtThousands(fy25.value)} → FY26 ${fmtThousands(fy26.value)}): ` +
            `${JSON.stringify(headline)}`,
        );
      }
    }
  }

  // Non-vacuity: h2 must actually have checked something, or the leg is
  // asleep. h1 legitimately checks zero cards while the zeroed class is empty
  // (that IS the fix), so it is not required to be non-empty — h2 carries the
  // non-vacuity burden.
  if (swingClaims === 0) {
    errors.push(
      `leg h: no yoy_swing claim could be re-derived from the corpus — the ` +
        `leg is vacuous and would not catch a regression`,
    );
  }

  if (errors.every((e) => !e.startsWith("leg h"))) {
    notes.push(
      `leg h: ${cardEls.length} feed cards checked as CLAIMS against ` +
        `budget_lines.parquet — ${terminationClaims} termination claim(s) ` +
        `(each requiring a literal FY2026 zero, ${moneyClaims} with a money ` +
        `clause), ${swingClaims} yoy_swing direction+magnitude re-derived ✓`,
    );
  }

  // Handed to leg i so the syndicated feed is checked against the SAME
  // corpus recompute this leg checked the page's prose against.
  return truth;
}

// ═══════════════════════════════════════════════════════════════════════════
// leg i — syndicated feed magnitudes (PM-review Sprint 3 Task 2, §P1-8)
// ═══════════════════════════════════════════════════════════════════════════
//
// §P1-8 had two halves. The first — no subscription at all (/rss.xml 404) —
// is a build-output problem, checked structurally by gate 8 legs f-j. The
// second is a TRUTH problem, and it belongs here:
//
//   "/feed/ items read 'Minuteman Squadrons increased 79% FY25→26' with +79%
//    as the only figure. A +79% swing on a $50M line and on a $5B line are
//    different stories."
//
// Cards now carry the dollars, and those dollars go out over RSS/Atom into
// readers we cannot correct after the fact. So every published magnitude is
// verified TWICE, against two independent things:
//
//   i1 AGAINST ITS OWN CITED FACT — each endpoint's value must equal the
//      recorded value of the fact its /fact/{id} permalink points at, and the
//      `display` string must be that same number formatted. A feed that
//      prints one number and links a receipt for another is the P0-1 defect
//      with a wider blast radius.
//   i2 AGAINST THE CORPUS — yoy_swing endpoints are re-derived from
//      budget_lines.parquet through the SAME recompute leg h uses (passed in,
//      not re-run: the page's prose and the feed's XML must be checked
//      against one truth, or they can drift apart while both "pass"). The
//      recompute reports the (pe_bli, organization) grain the trajectory mart
//      pivots on, which is the grain the card's pair is stated at.
//   i3 INTERNAL COHERENCE — delta == to − from, and the pair reproduces the
//      percentage the item's own title states. That last one is what ties
//      this leg to leg h: leg h verified that percentage against the parquet,
//      so a pair that reproduces it cannot be telling a different story.
//
// Absolute tolerance is 0.01 USD thousands (= $10) — the values are exact
// sums of workbook cells, so this is a float-representation allowance, not a
// rounding budget.

const FEED_VALUE_TOL = 0.01;
/** The title's percentage is printed with 0 decimals; allow rounding slack. */
const FEED_PCT_TOL = 1.0;
const FR_NS_URI = FR_NS;

/** Recorded value of a citation, whichever tier it is. */
function citationValue(c) {
  if (!c) return null;
  if (c.recorded_value !== null && c.recorded_value !== undefined) {
    return Number(c.recorded_value);
  }
  if (c.amount_thousands !== null && c.amount_thousands !== undefined) {
    return Number(c.amount_thousands);
  }
  return null;
}

/** The compact ladder the feed renders with (mirror of lib/format.ts). */
function fmtCompact(value, units) {
  const raw = value * (units === "thousands_usd" ? 1000 : 1);
  const abs = Math.abs(raw);
  const sign = raw < 0 ? "-" : "";
  const rungs = [
    [1e12, "T"],
    [1e9, "B"],
    [1e6, "M"],
    [1e3, "K"],
  ];
  for (let i = 0; i < rungs.length; i++) {
    const [limit, suffix] = rungs[i];
    if (abs < limit) continue;
    const v = abs / limit;
    const dec = v < 10 ? 2 : 1;
    if (i > 0 && Number(v.toFixed(dec)) >= 1000) {
      const [ulimit, usuffix] = rungs[i - 1];
      const uv = abs / ulimit;
      return `${sign}$${uv.toFixed(uv < 10 ? 2 : 1)}${usuffix}`;
    }
    return `${sign}$${v.toFixed(dec)}${suffix}`;
  }
  return `${sign}$${Math.round(abs).toLocaleString("en-US")}`;
}

function runFeedFileLeg(errors, notes, truth) {
  const rssPath = path.join(outDir, "rss.xml");
  if (!fs.existsSync(rssPath)) {
    errors.push(
      `leg i: ${rssPath} was not emitted — §P1-8's headline defect was that ` +
        `/rss.xml 404s; run npm run build (prebuild writes the feeds)`,
    );
    return;
  }

  let doc;
  try {
    const { JSDOM } = require_jsdom();
    const dom = new JSDOM(fs.readFileSync(rssPath, "utf8"), {
      contentType: "application/xml",
    });
    doc = dom.window.document;
  } catch (e) {
    errors.push(
      `leg i: out/rss.xml is not well-formed XML — ${e.message} ` +
        `(every subscriber's reader sees this file, not the page)`,
    );
    return;
  }

  let citations;
  try {
    citations = JSON.parse(
      fs.readFileSync(path.join(jsonDir, "citations.json"), "utf8"),
    );
  } catch (e) {
    errors.push(`leg i: could not read citations.json — ${e.message}`);
    return;
  }

  const cards = JSON.parse(
    fs.readFileSync(path.join(jsonDir, "feed.json"), "utf8"),
  ).cards;
  // feedGuid() is the generator's own identity function — imported, not
  // re-implemented, so this leg cannot bind items to the wrong cards after a
  // future change to the guid shape.
  const cardByGuid = new Map(cards.map((c) => [feedGuid(c), c]));

  const items = [...doc.getElementsByTagName("item")];
  if (items.length < MIN_FEED_CARDS) {
    errors.push(
      `leg i: out/rss.xml carries only ${items.length} items (expected ` +
        `≥${MIN_FEED_CARDS}) — a feed that publishes nothing cannot prove ` +
        `its magnitudes`,
    );
    return;
  }

  let checkedPoints = 0;
  let reDerivedSwings = 0;
  for (const item of items) {
    const title = item.getElementsByTagName("title")[0]?.textContent ?? "";
    const guid = item.getElementsByTagName("guid")[0]?.textContent ?? "";
    const card = cardByGuid.get(guid);
    const mag = item.getElementsByTagNameNS(FR_NS_URI, "magnitude")[0];
    if (!mag) continue; // structural absence is gate 8 leg h's error to raise
    const units = mag.getAttribute("units");
    const pts = new Map();
    for (const p of mag.getElementsByTagNameNS(FR_NS_URI, "point")) {
      pts.set(p.getAttribute("role"), {
        value: Number(p.getAttribute("value")),
        display: p.getAttribute("display"),
        fact: p.getAttribute("fact"),
        label: p.getAttribute("label"),
      });
    }

    // ── i1: each endpoint against its own cited fact ──────────────────────
    for (const [role, p] of pts) {
      checkedPoints += 1;
      const recorded = citationValue(citations[p.fact]);
      if (recorded === null) {
        errors.push(
          `leg i1 (${guid}): the "${role}" endpoint cites ${p.fact}, which ` +
            `carries no recorded value — the published dollar figure has no receipt`,
        );
        continue;
      }
      if (Math.abs(recorded - p.value) > FEED_VALUE_TOL) {
        errors.push(
          `leg i1 (${guid}): publishes ${p.value} for "${p.label}" but its ` +
            `cited fact ${p.fact} records ${recorded} — the feed prints one ` +
            `number and links the receipt for another`,
        );
      }
      const expectedDisplay = fmtCompact(p.value, units);
      if (p.display !== expectedDisplay) {
        errors.push(
          `leg i1 (${guid}): "${p.label}" displays ${JSON.stringify(p.display)} ` +
            `for value ${p.value} ${units}, which formats to ` +
            `${JSON.stringify(expectedDisplay)}`,
        );
      }
    }

    // ── i3: internal coherence of a pair ──────────────────────────────────
    if (mag.getAttribute("kind") === "pair") {
      const from = pts.get("from");
      const to = pts.get("to");
      const delta = pts.get("delta");
      if (from && to && delta) {
        if (Math.abs(to.value - from.value - delta.value) > FEED_VALUE_TOL) {
          errors.push(
            `leg i3 (${guid}): publishes ${from.value} → ${to.value} with a ` +
              `stated change of ${delta.value}, but ${to.value} − ${from.value} ` +
              `= ${to.value - from.value}`,
          );
        }
      }
      const pctInTitle = title.match(/\(([+−-])\$[^,]*,\s*([+−-])([\d.]+)%\)/);
      if (from && to && from.value !== 0 && pctInTitle) {
        const stated =
          Number(pctInTitle[3]) * (pctInTitle[2] === "+" ? 1 : -1);
        const derived = (100 * (to.value - from.value)) / from.value;
        if (Math.abs(stated - derived) > FEED_PCT_TOL) {
          errors.push(
            `leg i3 (${guid}): the item states ${stated}% but its own pair ` +
              `${from.value} → ${to.value} recomputes ${derived.toFixed(1)}% ` +
              `— the dollars and the percentage tell different stories`,
          );
        }
      }
    }

    // ── i2: yoy_swing endpoints re-derived from the corpus ────────────────
    if (card?.event_type === "yoy_swing" && truth) {
      const pe = card.pe_bli;
      const corpus = truth[pe];
      if (!corpus) {
        errors.push(
          `leg i2 (${guid}): publishes a FY25→FY26 pair for a PE with no ` +
            `budget lines in the corpus`,
        );
        continue;
      }
      // Prefer the (pe_bli, organization) grain — the grain the trajectory
      // mart pivots on and the card's pair is stated at.
      const scope =
        (card.organization && corpus.by_org?.[card.organization]) || corpus;
      const from = pts.get("from");
      const to = pts.get("to");
      const pairs = [
        ["from", from, scope.fy2025_total, "FY2025"],
        ["to", to, scope.fy2026_total, "FY2026"],
      ];
      let ok = true;
      for (const [role, p, measured, label] of pairs) {
        if (!p) continue;
        if (!measured?.present) {
          errors.push(
            `leg i2 (${guid}): publishes a ${label} figure of ${p.value} but ` +
              `the corpus holds no ${label} row for ${pe}` +
              `${card.organization ? `/${card.organization}` : ""} — a ` +
              `published dollar figure with nothing behind it`,
          );
          ok = false;
          continue;
        }
        if (Math.abs(measured.value - p.value) > FEED_VALUE_TOL) {
          errors.push(
            `leg i2 (${guid}): publishes ${label} ${p.value} for the "${role}" ` +
              `endpoint, the corpus recomputes ${measured.value} from ` +
              `budget_lines.parquet`,
          );
          ok = false;
        }
      }
      if (ok && from && to) reDerivedSwings += 1;
    }
  }

  // Non-vacuity: the yoy_swing re-derivation is the substantive half of this
  // leg (i1 would still pass if every card carried a self-consistent lie
  // minted from the same wrong source).
  if (reDerivedSwings === 0) {
    errors.push(
      `leg i: no published yoy_swing pair could be re-derived from ` +
        `budget_lines.parquet — the leg is vacuous and would not catch a regression`,
    );
  }

  if (errors.every((e) => !e.startsWith("leg i"))) {
    notes.push(
      `leg i: ${items.length} syndicated items — ${checkedPoints} magnitude ` +
        `endpoints match their cited facts, ${reDerivedSwings} yoy_swing pairs ` +
        `re-derived from budget_lines.parquet (leg h's recompute), deltas and ` +
        `stated percentages internally coherent ✓`,
    );
  }
}

/**
 * jsdom is a devDependency used here only to PARSE XML with a real parser.
 * Loaded through createRequire so this ESM gate does not pay for it on the
 * paths that never reach leg i.
 */
function require_jsdom() {
  return createRequire(import.meta.url)("jsdom");
}

// ═══════════════════════════════════════════════════════════════════════════
// leg k — CORPUS-COUNT PROVENANCE (tri-persona review Wave 4, item 4)
// ═══════════════════════════════════════════════════════════════════════════
//
// The site states its own size five ways — 2,016 in sitemap.xml, 2,005
// browsable pages, 1,755 index rows, 1,753 dim_programs rows, 1,743
// detail-grade. Every one is right for its own denominator and nothing said
// so, which from outside is indistinguishable from the site disagreeing with
// itself on the one page built to let people check its work.
//
// Leg (d) already pins two of them, in one canonical sentence, on four pages.
// This leg generalises the rule to the class:
//
//   A CORPUS COUNT RENDERED ON ANY PAGE MUST BE ONE OF THE DECLARED COUNTS.
//
// which is the same defect shape as the stale `measured:` page-weight
// annotation and the docstring that outlived its function: a number that was
// true when it was typed and is nobody's job to re-derive. A hard-coded
// "1,750 program elements" is caught here even though it is plausible, well
// formatted and beside no citation at all.
//
// FIVE INDEPENDENT RECOMPUTES, from the artifacts that DEFINE each count, not
// from lib/corpus (which is the thing under test):
//
//   sitemap-urls       <loc> entries under /program/ in the SHIPPED sitemap.xml
//   program-pages      program_details sidecars on disk
//   index-rows         programs.json rows
//   dim-programs-rows  datasets.json's dim_programs row_count (leg d already
//                      ties that to the sidecars and the parquet)
//   detail-pages       sidecars carrying a non-empty details array
//
// The one deliberate exemption is [data-historical-figures] — /methodology/'s
// corrections table, whose "Was" column records superseded figures on
// purpose. Scoped to that container and nowhere else: a superseded corpus
// figure anywhere else IS the defect.

/**
 * A number that PRESENTS ITSELF as a corpus count: a comma-grouped integer
 * whose head noun IS the corpus — "N programs", "N program elements",
 * "N (browsable) program pages".
 *
 * Comma-grouped by design — an agency page's "519 programs" is a true
 * statement about that agency, not a claim about the corpus, and every corpus
 * count here is four digits.
 *
 * The noun phrase must be COMPLETE, which is what keeps "program" as a
 * modifier out. A first cut allowed a bare singular "program" and flagged
 * /methodology/'s "12,448 program mentions" — a mention count, correctly
 * derived from fct_program_lobbying, that happens to have "program" as an
 * adjective. Likewise "10,091 program-award links" (hyphen, no match).
 */
const CORPUS_CLAIM_RE = new RegExp(
  String.raw`\b(\d{1,3}(?:,\d{3})+)\s+(?:browsable\s+)?` +
    String.raw`(?:programs\b|program\s+elements?\b|program\s+pages?\b)(?![\w-])`,
  "gi",
);

/**
 * Pages scanned. The singleton, hand-written-prose pages — the templated
 * detail pages (~2,000 of them) state per-program facts, never corpus size,
 * and share one template that this list's members already exercise.
 */
const CORPUS_CLAIM_PAGES = [
  "/", "/programs/", "/years/", "/methodology/", "/data/", "/coverage/",
  "/downloads/", "/about/", "/glossary/", "/agency/", "/feed/", "/flow/",
  "/lineage/", "/companies/", "/district/", "/filings/",
];

/** The five declared counts, recomputed from the shipped artifacts. */
function recomputeCorpusCounts() {
  const out = {};
  const errs = [];

  // sitemap-urls — the SHIPPED xml, so this is the number a crawler is given.
  const smPath = path.join(outDir, "sitemap.xml");
  if (fs.existsSync(smPath)) {
    const xml = fs.readFileSync(smPath, "utf8");
    const locs = xml.match(/<loc>[^<]*\/program\/[^<]*<\/loc>/g) ?? [];
    out["sitemap-urls"] = locs.length;
  } else {
    errs.push("leg k: out/sitemap.xml missing — cannot recompute sitemap-urls");
  }

  // program-pages / detail-pages — the sidecars themselves.
  const pdDir = path.join(jsonDir, "program_details");
  if (fs.existsSync(pdDir)) {
    const files = fs.readdirSync(pdDir).filter((f) => f.endsWith(".json"));
    out["program-pages"] = files.length;
    let withDetail = 0;
    for (const f of files) {
      let raw;
      try {
        raw = fs.readFileSync(path.join(pdDir, f), "utf8");
      } catch {
        continue;
      }
      if (!raw.includes('"details"') || /"details":\s*\[\]/.test(raw)) continue;
      try {
        const d = JSON.parse(raw).details;
        if (Array.isArray(d) && d.length > 0) withDetail++;
      } catch {
        /* malformed — leg d reports it */
      }
    }
    out["detail-pages"] = withDetail;
  } else {
    errs.push("leg k: program_details/ missing — cannot recompute page counts");
  }

  // index-rows — programs.json.
  const progPath = path.join(jsonDir, "programs.json");
  if (fs.existsSync(progPath)) {
    try {
      out["index-rows"] = JSON.parse(fs.readFileSync(progPath, "utf8")).length;
    } catch {
      errs.push("leg k: programs.json unparseable");
    }
  } else {
    errs.push("leg k: programs.json missing — cannot recompute index-rows");
  }

  // dim-programs-rows — the shipped manifest.
  const dsPath = path.join(jsonDir, "datasets.json");
  if (fs.existsSync(dsPath)) {
    try {
      const row = (JSON.parse(fs.readFileSync(dsPath, "utf8")).datasets ?? []).find(
        (d) => d.name === "dim_programs",
      );
      if (row) out["dim-programs-rows"] = row.row_count;
      else errs.push("leg k: datasets.json has no dim_programs entry");
    } catch {
      errs.push("leg k: datasets.json unparseable");
    }
  } else {
    errs.push("leg k: datasets.json missing");
  }

  return { counts: out, errs };
}

function runCorpusCountLeg(errors, notes) {
  const { counts: expected, errs } = recomputeCorpusCounts();
  for (const e of errs) errors.push(e);
  const ids = Object.keys(expected);
  if (ids.length < 5) {
    errors.push(
      `leg k: only ${ids.length} of 5 corpus counts could be recomputed — ` +
        `the sweep below would pass vacuously`,
    );
    return;
  }
  const allowed = new Map();
  for (const [id, v] of Object.entries(expected)) {
    if (!allowed.has(v)) allowed.set(v, []);
    allowed.get(v).push(id);
  }

  // ── (k1) /coverage/ publishes all five, each equal to its recompute ──
  const covPath = htmlFor("/coverage/");
  if (!fs.existsSync(covPath)) {
    errors.push("leg k1: /coverage/ not built — the reconciliation is unverifiable");
  } else {
    const root = parse(fs.readFileSync(covPath, "utf8"), { comment: false });
    for (const el of root.querySelectorAll("script, style, noscript, template")) {
      el.remove();
    }
    const rows = root.querySelectorAll("[data-corpus-count]");
    const seen = new Set();
    for (const row of rows) {
      const id = row.getAttribute("data-corpus-count");
      seen.add(id);
      if (!(id in expected)) {
        errors.push(
          `leg k1: /coverage/ publishes an undeclared corpus count "${id}" — ` +
            `every row must name one of ${ids.join(", ")}`,
        );
        continue;
      }
      const valueEl = row.querySelector("[data-corpus-value]") ?? row;
      const shown = parseInt(norm(valueEl.text).replace(/,/g, ""), 10);
      if (shown !== expected[id]) {
        errors.push(
          `leg k1: /coverage/ row "${id}" renders ${shown} but the shipped ` +
            `artifact holds ${expected[id]}`,
        );
      }
    }
    const missing = ids.filter((id) => !seen.has(id));
    if (missing.length > 0) {
      errors.push(
        `leg k1: /coverage/'s corpus reconciliation omits ${missing.join(", ")} — ` +
          `a count the site publishes and the reconciliation does not explain is ` +
          `exactly the defect this table exists to close`,
      );
    }
  }

  // ── (k2) every corpus-shaped claim on a singleton page is a declared count ──
  let scanned = 0;
  let claims = 0;
  const bad = [];
  for (const url of CORPUS_CLAIM_PAGES) {
    const p = htmlFor(url);
    if (!fs.existsSync(p)) continue;
    scanned++;
    const root = parse(fs.readFileSync(p, "utf8"), { comment: false });
    // The RSC flight payload lives in <script>. Reading it instead of the
    // rendered page is how a previous leg in this project passed while the
    // page was broken — strip them, and the historical-figures container.
    for (const el of root.querySelectorAll(
      "script, style, noscript, template, [data-historical-figures]",
    )) {
      el.remove();
    }
    // WHOLE-PAGE TEXT, not leg j's leaf-element unit. The two legs need
    // different units: leg j reads a number's NOTATION, which a leaf split
    // ("CO-05" + "10 programs") would fabricate, so it must scan leaves.
    // This leg reads a number's NOUN, and the noun routinely sits in a
    // sibling node — React renders `{n} program` + `s` as two text nodes,
    // and a leaf-joined scan that inserted separators would read "program s"
    // and match nothing. Concatenation cannot fabricate a match here because
    // the leading \b refuses a number glued to a preceding word character
    // ("$2.60B" + "1,755 programs" does not match) — a glue can only cost a
    // finding, never invent one, and the claims===0 guard below is what
    // stops that degrading silently.
    const text = norm(root.text);
    for (const m of text.matchAll(CORPUS_CLAIM_RE)) {
      claims++;
      const n = Number(m[1].replace(/,/g, ""));
      if (allowed.has(n)) continue;
      bad.push({ url, phrase: m[0].trim(), n });
    }
  }
  if (scanned === 0) {
    errors.push("leg k2: no singleton page built — the sweep is vacuous");
    return;
  }
  if (claims === 0) {
    errors.push(
      `leg k2: ${scanned} pages scanned and NOT ONE corpus claim matched — ` +
        `the site states its size on at least four pages, so a zero here means ` +
        `the scan is broken, not that the site went quiet`,
    );
  }
  for (const b of bad) {
    errors.push(
      `leg k2 (${b.url}): "${b.phrase}" states a corpus size of ${b.n.toLocaleString("en-US")}, ` +
        `which is none of the declared counts (` +
        ids.map((id) => `${id}=${expected[id].toLocaleString("en-US")}`).join(", ") +
        `). Either it is a literal that has rotted, or it is a sixth ` +
        `denominator that has to be declared in lib/corpus getCorpusCounts() ` +
        `and explained on /coverage/`,
    );
  }
  if (bad.length === 0) {
    notes.push(
      `leg k: ${claims} corpus claim(s) across ${scanned} page(s) all resolve to a ` +
        `declared count (` +
        ids.map((id) => `${id}=${expected[id].toLocaleString("en-US")}`).join(", ") +
        `) ✓`,
    );
  }
}


// ═══════════════════════════════════════════════════════════════════════════
// leg p — crosswalk-count provenance (PM-S3 leftover)
// ═══════════════════════════════════════════════════════════════════════════

/** Pages that state a crosswalk ratio in their own prose. */
const CROSSWALK_CLAIM_PAGES = ["/flow/", "/district/", "/coverage/", "/methodology/", "/programs/"];

/**
 * MIRROR of lib/corpus CROSSWALK_COUNT_IDS — the order /coverage/ renders and
 * the order (p1) binds.
 *
 * A HAND COPY, PINNED AT GATE TIME BY (p1). A gate file cannot import from the
 * site's TypeScript, so this list is typed out rather than imported — but it is
 * not unenforced. Leg (p1) below reads the `data-crosswalk-count` ids off the
 * built /coverage/ page, which emits one `<li data-crosswalk-count={c.id}>` per
 * getCrosswalkCounts() row (coverage/page.tsx:71, :354), and compares them to
 * this array BY LENGTH and ELEMENT-WISE, erroring by name on any divergence.
 * Add, remove or reorder an id in lib/corpus without editing this list and
 * (p1) fails on the next build.
 *
 * `src/lib/__tests__/corpus.test.ts` ("declares every crosswalk count the site
 * publishes") is the SITE-SIDE half of the same pairing: it asserts
 * getCrosswalkCounts()'s ids ARE CROSSWALK_COUNT_IDS, in order. Both sides of
 * that assertion live in lib/corpus (corpus.test.ts:132-135), so it cannot see
 * this file and stays green on a divergence here — it keeps the registry
 * honest, (p1) keeps this copy honest.
 */
const CROSSWALK_COUNT_IDS = [
  "link-universe",
  "bridged-request",
  "high-confidence-links",
  "district-linkable",
  "district-linkable-unbridged",
];

/**
 * A crosswalk CLAIM is a ratio with a program-or-link noun: "384 of 444
 * crosswalked PEs", "200 of 1,938 programs", "9,587 of the 12,595 links".
 *
 * Noun-anchored, like leg (k2)'s CORPUS_CLAIM_RE, and for the same reason: a
 * whole-sentence scan cannot work on rendered text, where adjacent elements
 * concatenate with no space between them. On the 2026-09-12 build the first
 * "sentence" of /district/ is the entire nav plus the lede, and /coverage/
 * glues "…what the chart omits." to "Company award linkage32 of 200 profiled
 * companies…" — a sentence-shaped sweep reads four unrelated figures out of
 * each and reports them all.
 *
 * `(?<![\d,.])` is not decoration: without it the engine finds a word
 * boundary INSIDE a glued "pages1,936" and matches "936 of 2,562", a number
 * the page never states.
 */
const CROSSWALK_CLAIM_RE = new RegExp(
  String.raw`(?<![\d,.])\b(\d{1,3}(?:,\d{3})*)\s+of\s+(?:the\s+)?(\d{1,3}(?:,\d{3})*)\s+` +
    String.raw`(?:crosswalked\s+|published\s+|linked\s+|browsable\s+)?` +
    String.raw`(?:PEs?|program\s+elements?|programs?|links?)\b`,
  "gi",
);

/** A ratio is ABOUT the crosswalk when one of these sits beside it. */
const CROSSWALK_CUE = /crosswalk|follow-the-dollar|bridge/i;

/** Characters either side of the ratio that the cue may sit in. Re-measured
 *  2026-09-18 over the built pages, the sampled /program/ page included: all
 *  TEN real claims are cued at 60, 80 and 120 alike, and nothing else becomes
 *  cued at any of the three, so the window is not load-bearing at this value. */
const CROSSWALK_CUE_WINDOW = 80;

/** Non-vacuity floor for the LIVE sweep — passed in as `minClaims`, so the
 *  pure function stays testable at both settings (re-measured 2026-09-18 at TEN
 *  crosswalk ratios across /flow/ 1, /district/ 3, /coverage/ 1, /methodology/ 4
 *  and the sampled /program/ page 1 — nine before that page joined the sweep).
 *  Below
 *  this the matcher has stopped matching — a noun reword, a notation change —
 *  and (p2) would pass on an empty set, which is the shape leg (k2)'s own
 *  claims===0 guard exists for. RE-MEASURE if the pages change; do not lower
 *  it to fit. */
const MIN_CROSSWALK_CLAIMS = 6;

/** Non-vacuity floor for the sidecar census (measured 2026-09-18 at 200
 *  files in data/site/json/flows). (p1)'s district-linkable row and (p3)'s
 *  whole org mix are counted off that directory; a pruned-but-not-re-emitted
 *  export would otherwise make both pass on almost nothing. Do not lower. */
const MIN_FLOW_SIDECARS = 120;

/**
 * The leaf fields of the two derived link blocks that the swept passages
 * actually render. READ, never re-derived: leg (n) owns link_precision and leg
 * (o) owns link_adjudication, and re-deriving either here is how one number
 * acquires two sources. (p2) admits these so a /methodology/ sentence that
 * states a block's own figure — "9,587 of the 12,595 links the crosswalk grades
 * high or medium" — is not reported as a sixth undeclared denominator.
 *
 * ENUMERATED, NOT WALKED. What shipped walked both blocks and admitted every
 * finite number anywhere inside them: 22 distinct integers on the 2026-09-18
 * artifact, against the THREE the live claims cite (12,595 and 9,587 from here,
 * 384 from the declared counts). Every one of the other nineteen — `unpinned`
 * 8,474, every `by_method.*` counter, every `high.by_path.*` counter — was a
 * standing free pass for a rotted literal that happened to collide with it, on
 * a leg whose whole job is to catch exactly that.
 *
 * WHAT IS LEFT, MEASURED. Not all nineteen went: re-measured 2026-09-18
 * against data/site/json/site_meta.json, the walk admitted 22 distinct
 * integers and this enumeration admits TEN — 0, 51, 53, 54, 60, 94, 120, 768,
 * 9,587 and 12,595 — so twelve of the 22 are gone and eight of the nineteen
 * are not. The eight are not free passes any more, though: they are admitted
 * because /methodology/ §4 RENDERS them, as the four precision ratios
 * ("account+subagency 0/60; announcement+lexicon 51/54; fpds-ap 94/120;
 * subaward+lexicon 53/60") and "60 of the 768 links published at high". The
 * crosswalk matcher below reads neither as a claim — "0/60" is not an
 * `N of M <noun>` ratio, and the high-tier sentence matches but carries no
 * crosswalk cue inside CROSSWALK_CUE_WINDOW — so on this build only 9,587 and
 * 12,595 of the ten are cited by one of the ten matched claims. All ten were
 * checked against the text of out/methodology/index.html on 2026-09-18.
 *
 * (The first cut of this enumeration also kept `by_method.*.published` and
 * stopped at fifteen. Those five — 113, 527, 708, 1,910, 9,337 — are rendered
 * on no page at all, `by_method` has one reader in site/src and it is a type
 * declaration, and 1,910 sat 28 away from the corpus denominator 1,938 that
 * /district/ and /methodology/ really do state.)
 *
 * What is admitted, and which passage renders it:
 *   link_adjudication.published            12,595  /methodology/ §4, "9,587 of the 12,595 links" (page.tsx:809)
 *   link_adjudication.adjudicated           9,587  that sentence's numerator
 *   link_adjudication.high.published_high     768  §4's "60 of the 768 links published at high" (page.tsx:843)
 *   link_adjudication.high.adjudicated_high    60  THAT sentence's numerator (page.tsx:311 → :844)
 *   link_adjudication.high.two_lens_high       60  its trailing "all 60 challenged by two…" clause
 *   link_precision.methods.*.confirmed             §4's precision ratios, rendered "51/54" (page.tsx:163-167 → :977)
 *   link_precision.methods.*.sampled               their denominators
 *
 * adjudicated_high and two_lens_high are BOTH listed on purpose: they are 60
 * and 60 on today's artifact, so admitting only one would pass by coincidence
 * and stop passing the day adjudication pins a link two lenses have not both
 * seen.
 *
 * ADD A FIELD HERE when a passage starts rendering one — with the passage named
 * above — rather than widening this back into a walk.
 */
export function publishedLinkFigures(meta) {
  const out = [];
  const take = (v) => {
    if (typeof v === "number" && Number.isFinite(v)) out.push(v);
  };
  const adj = meta?.link_adjudication ?? {};
  take(adj.published);
  take(adj.adjudicated);
  take(adj.high?.published_high);
  take(adj.high?.adjudicated_high);
  take(adj.high?.two_lens_high);
  for (const m of Object.values(meta?.link_precision?.methods ?? {})) {
    take(m?.confirmed);
    take(m?.sampled);
  }
  return out;
}

/**
 * (p2) Every number in a crosswalk ratio must be a declared crosswalk count,
 * a declared corpus count, a figure one of the derived blocks publishes, or
 * the one complement the pages actually compute. `pages` is [{url, text}].
 */
export function crosswalkClaimFindings(
  pages,
  declared,
  corpus,
  published = [],
  minClaims = 1,
) {
  const allowed = new Set([...Object.values(declared), ...Object.values(corpus), ...published]);
  // /district/ states "N of M program elements have no district-level
  // linkage" — M minus the linkable tier, computed in the page from those two
  // and therefore incapable of rotting on its own.
  if (
    typeof corpus["index-rows"] === "number" &&
    typeof declared["district-linkable"] === "number"
  ) {
    allowed.add(corpus["index-rows"] - declared["district-linkable"]);
  }
  const found = [];
  let claims = 0;
  for (const p of pages) {
    const text = p.text;
    for (const m of text.matchAll(CROSSWALK_CLAIM_RE)) {
      const from = Math.max(0, m.index - CROSSWALK_CUE_WINDOW);
      const to = m.index + m[0].length + CROSSWALK_CUE_WINDOW;
      if (!CROSSWALK_CUE.test(text.slice(from, to))) continue;
      claims++;
      for (const raw of [m[1], m[2]]) {
        const n = Number(raw.replace(/,/g, ""));
        if (allowed.has(n)) continue;
        found.push(
          `leg p2 (${p.url}): "${m[0].trim()}" states ${n.toLocaleString("en-US")}, ` +
            `which is none of the declared crosswalk counts (` +
            Object.entries(declared).map(([k, v]) => `${k}=${v}`).join(", ") +
            `), none of the declared corpus counts, and none of the figures ` +
            `site_meta's link blocks publish. Either it is a literal that has ` +
            `rotted, or it is a sixth denominator that has to be declared in ` +
            `lib/corpus getCrosswalkCounts() and explained on /coverage/#crosswalk`,
        );
      }
    }
  }
  if (claims < minClaims) {
    found.push(
      claims === 0
        ? `leg p2: ${pages.length} page(s) scanned and not one crosswalk claim ` +
            `matched — /flow/ and /district/ both state one, so a zero here ` +
            `means the scan is broken, not that the site went quiet`
        : `leg p2: ${pages.length} page(s) scanned and only ${claims} crosswalk ` +
            `claim(s) matched — below the do-not-lower floor of ${minClaims} ` +
            `measured 2026-09-18 at 10. RE-MEASURE if the pages change; do not ` +
            `lower it to fit`,
    );
  }
  return found;
}

/** Characters of context either side of the org name the (p3) finding quotes.
 *  A rendered "sentence" is often the whole nav glued to the lede, so slicing
 *  from its start quoted the page head and never the clause under complaint. */
const ORG_QUOTE_WINDOW = 120;

/** `s` as a literal inside a RegExp. Org names are sidecar data. */
function escapeRe(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** A +/- `window` slice of `text` around `at`, elided where it was cut. */
function quoteAround(text, at, window) {
  const from = Math.max(0, at - window);
  const to = Math.min(text.length, at + window);
  return `${from > 0 ? "…" : ""}${text.slice(from, to).trim()}${to < text.length ? "…" : ""}`;
}

/**
 * (p3) Prose may not hand the crosswalk to one organization while the shipped
 * sidecars say otherwise. `orgMix` is {org: sidecar count}, recomputed.
 *
 * Sentence-shaped on purpose, unlike (p2): the unit here is an assertion
 * about a name, and glue can only widen the window a name is read in — it
 * cannot invent the name. RE-MEASURED 2026-09-18 against the built site/out,
 * over the SEVEN pages this leg now sweeps (the five index pages plus the
 * first /district/ and the first /program/ detail page): exactly three
 * findings — the /district/ lede, /district/AL-02/'s account-structure
 * explanation and /methodology/'s "concentrated in DARPA lines" — out of 61
 * DARPA mentions on those pages (/flow/ 0, /district/ 5, /coverage/ 0,
 * /methodology/ 4, /programs/ 50, /district/AL-02/ 2, /program/000042/ 0).
 * The other 58 sit in no crosswalk-or-attribution sentence, which is what the
 * cue filter below is for; the earlier "five pages carrying 122 DARPA
 * mentions" predates both the /program/ sample and this build.
 */
export function orgAttributionFindings(pages, orgMix) {
  const total = Object.values(orgMix).reduce((a, v) => a + v, 0);
  if (total === 0) {
    return ["leg p3: no flow sidecars could be tallied — the attribution check would be vacuous"];
  }
  const found = [];
  for (const p of pages) {
    for (const sentence of p.text.split(/(?<=[.;])\s+/)) {
      if (!CROSSWALK_CUE.test(sentence) && !/account structure|attribut/i.test(sentence)) continue;
      for (const [org, n] of Object.entries(orgMix)) {
        if (org.length < 3) continue;                     // 'N', 'F', 'A' are codes, not prose
        // Org names come off the sidecars' own `header.org`, so they are data,
        // not a pattern: an "OSD (R&E)" or an "A+" would otherwise be spliced
        // into the source of a RegExp and either throw or match the wrong text.
        // The anchors are LOOKAROUNDS, not `\b`, for the same names: `\b` is a
        // transition between a word and a non-word character, so a trailing
        // `\b` after the `)` of "OSD (R&E)" can only match when a word
        // character follows — never in prose, where a closing paren is followed
        // by a space or a stop. That turns a wrong match into a NEVER match,
        // and (p3) goes silent on the one org instead of reporting it. Same
        // form as program-skeleton.mjs titleCarriesTerm(), which fixed this
        // first. (All 8 shipped header.org values are word-char-only today, so
        // nothing about the live sweep changes: A, DARPA, DISA, F, MDA, N, OSD,
        // SOCOM, re-read 2026-09-18.)
        const hit = new RegExp(
          `(?<![A-Za-z0-9])${escapeRe(org)}(?![A-Za-z0-9])`,
          "i",
        ).exec(sentence);
        if (!hit) continue;
        if (n * 2 >= total) continue;                      // it really is the majority
        found.push(
          `leg p3 (${p.url}): "${quoteAround(sentence, hit.index, ORG_QUOTE_WINDOW)}" attributes the ` +
            `crosswalk to ${org}, which holds ${n} of ${total} flow sidecars. Name the mechanism (an ` +
            `announcement that names the program, or account plus program tokens), not an organization`,
        );
      }
    }
  }
  return found;
}

function runCrosswalkCountLeg(errors, notes) {
  // ── recompute the five declared counts from the shipped artifacts ────────
  const declared = {};
  const flowsDir = path.join(jsonDir, "flows");
  const flowPath = path.join(jsonDir, "flow_chart.json");
  const orgMix = {};
  if (!fs.existsSync(flowsDir) || !fs.existsSync(flowPath)) {
    errors.push("leg p: flows/ or flow_chart.json missing — the crosswalk counts cannot be recomputed");
    return;
  }
  const sidecars = fs.readdirSync(flowsDir).filter((f) => f.endsWith(".json"));
  if (sidecars.length < MIN_FLOW_SIDECARS) {
    errors.push(
      `leg p: ${sidecars.length} flow sidecar(s) on disk — below the ` +
        `do-not-lower floor of ${MIN_FLOW_SIDECARS} measured 2026-09-18 at ` +
        `200. The district-linkable count and the whole org mix are counted ` +
        `off this directory. Re-run export-site; do not lower the floor`,
    );
  }
  declared["district-linkable"] = sidecars.length;
  for (const f of sidecars) {
    try {
      const org = JSON.parse(fs.readFileSync(path.join(flowsDir, f), "utf8"))?.header?.org;
      if (org) orgMix[org] = (orgMix[org] ?? 0) + 1;
    } catch {
      /* gate 22 leg (a) reports malformed payloads */
    }
  }
  const bridge = JSON.parse(fs.readFileSync(flowPath, "utf8")).budget.bridge;
  declared["link-universe"] = bridge.crosswalk_universe_pe_count;
  declared["bridged-request"] = bridge.crosswalked_pe_count;
  declared["high-confidence-links"] = bridge.high_confidence_pe_count;
  const bridged = new Set((bridge.programs ?? []).map((p) => p.pe_bli));
  declared["district-linkable-unbridged"] = sidecars.filter(
    (f) => !bridged.has(f.slice(0, -".json".length)),
  ).length;
  for (const id of CROSSWALK_COUNT_IDS) {
    if (typeof declared[id] !== "number") {
      errors.push(
        `leg p: "${id}" could not be recomputed from the shipped artifacts — ` +
          `flow_chart.json's bridge band has changed shape and every check ` +
          `below would compare against undefined`,
      );
      return;
    }
  }

  // ── (p1) /coverage/ publishes all five, in the derived order ─────────────
  //
  // Slot-bound, the way leg (o) binds the adjudication passage: a row-by-id
  // lookup passes on a list that renders the right five numbers against the
  // wrong five sentences, which is the same species of defect as a passage
  // that permutes its own figures.
  const covPath = htmlFor("/coverage/");
  if (!fs.existsSync(covPath)) {
    errors.push("leg p1: /coverage/ not built — the crosswalk reconciliation is unverifiable");
  } else {
    const root = parse(fs.readFileSync(covPath, "utf8"), { comment: false });
    for (const el of root.querySelectorAll("script, style, noscript, template")) el.remove();
    const rows = root.querySelectorAll("[data-crosswalk-count]");
    const gotIds = rows.map((r) => r.getAttribute("data-crosswalk-count"));
    if (
      gotIds.length !== CROSSWALK_COUNT_IDS.length ||
      CROSSWALK_COUNT_IDS.some((id, i) => id !== gotIds[i])
    ) {
      errors.push(
        `leg p1: /coverage/#crosswalk renders the rows ${gotIds.join(", ") || "(none)"} ` +
          `but the registry derives ${CROSSWALK_COUNT_IDS.join(", ")}, in that order. ` +
          `A crosswalk count the site publishes and the reconciliation does not ` +
          `explain is the defect this list exists to close, and a row in the wrong ` +
          `slot states its neighbour's sentence about its own number`,
      );
    } else {
      rows.forEach((row, i) => {
        const id = CROSSWALK_COUNT_IDS[i];
        const shown = parseInt(
          norm((row.querySelector("[data-crosswalk-value]") ?? row).text).replace(/,/g, ""),
          10,
        );
        if (shown !== declared[id]) {
          errors.push(
            `leg p1: /coverage/ row "${id}" renders ${shown} but the shipped artifact holds ${declared[id]}`,
          );
        }
      });
    }
  }

  // ── (p2) + (p3) the prose sweep ─────────────────────────────────────────
  const pages = [];
  for (const url of CROSSWALK_CLAIM_PAGES) {
    const p = htmlFor(url);
    if (!fs.existsSync(p)) continue;
    const root = parse(fs.readFileSync(p, "utf8"), { comment: false });
    for (const el of root.querySelectorAll("script, style, noscript, template, [data-historical-figures]")) {
      el.remove();
    }
    pages.push({ url, text: norm(root.text) });
  }
  // Two DETAIL pages as well, each the alphabetically first of its kind, and
  // each carrying crosswalk prose the index pages do not:
  //   /district/<first>/ — its own organization-attribution paragraph, which is
  //     the only place (p3)'s target sentence lives outside the indexes.
  //   /program/<first>/  — the follow-the-dollar emptyNote, "flows cover 200 of
  //     1,938 programs", which renders on ~1,700 program pages and was entirely
  //     outside the sweep until 2026-09-18. It is ONE template, so one sample
  //     covers all of them; the note below prints which page was read.
  for (const [dir, label] of [["district", "district"], ["program", "program"]]) {
    const detailDir = path.join(outDir, dir);
    if (!fs.existsSync(detailDir)) continue;
    const first = fs.readdirSync(detailDir, { withFileTypes: true }).filter((e) => e.isDirectory()).map((e) => e.name).sort()[0];
    if (!first) continue;
    const dp = path.join(detailDir, first, "index.html");
    if (!fs.existsSync(dp)) continue;
    const root = parse(fs.readFileSync(dp, "utf8"), { comment: false });
    for (const el of root.querySelectorAll("script, style, noscript, template, [data-historical-figures]")) {
      el.remove();
    }
    pages.push({ url: `/${label}/${first}/`, text: norm(root.text) });
  }
  if (pages.length === 0) {
    errors.push("leg p: no crosswalk-claim page built — the sweep is vacuous");
    return;
  }
  const corpus = recomputeCorpusCounts().counts;
  let meta = {};
  const metaPath = path.join(jsonDir, "site_meta.json");
  if (fs.existsSync(metaPath)) {
    try {
      meta = JSON.parse(fs.readFileSync(metaPath, "utf8"));
    } catch {
      /* leg n reports an unparseable site_meta */
    }
  }
  errors.push(
    ...crosswalkClaimFindings(
      pages,
      declared,
      corpus,
      publishedLinkFigures(meta),
      MIN_CROSSWALK_CLAIMS,
    ),
  );
  errors.push(...orgAttributionFindings(pages, orgMix));
  notes.push(
    `leg p: ${Object.entries(declared).map(([k, v]) => `${k}=${v}`).join(", ")}; ` +
      `sidecar org mix ${Object.entries(orgMix).sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k}:${v}`).join(" ")} ` +
      `across ${pages.length} page(s)`,
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// leg n — held-out link-precision study (ROADMAP #72)
// ═══════════════════════════════════════════════════════════════════════════
//
// site_meta.link_precision ({rubric, sample_id, sampled_at, methods, unmeasured},
// or {} while no study has verdicts yet) is the recomputed source of truth here
// — this leg reads data/site/json/site_meta.json directly (unlike leg e,
// which never trusts site_meta for the artifact it is derived from; here
// site_meta IS the artifact under test, produced by an inlined Postgres query
// in export_site.py that this leg does not re-run — the DB tally is scripts/
// precision_study.py's own job, exercised by tests/test_precision_study.py
// and tests/test_export_site_link_precision.py).
//
// FIVE directions, all failures:
//   - link_precision names a method the /methodology/ paragraph omits or
//     states wrong numbers for (a stale/partial paragraph reads as more
//     confidence than was measured);
//   - the paragraph renders while link_precision carries nothing (leftover
//     text with no numbers behind it — or numbers for a method site_meta
//     no longer knows about);
//   - (2026-09-04, final review C1) link_precision carries a figure for a
//     method the CORPUS DOES NOT PUBLISH. This is the defect that shipped:
//     `fpds-ap+account` was withdrawn hours after the sample was drawn, the
//     study table still remembered it, and /methodology/ printed 34/60 as
//     "measured precision of the published tiers" for a tier with zero rows
//     — while the tier that absorbed its links printed a flattering 60/60.
//     Every number matched its source; the population was wrong;
//   - (2026-09-04, final review C1/C2) a published method with no figure is
//     SILENT. `account+subagency` (the largest tier) and `account+tokens`
//     carry no measured number, and silence reads as "nothing to report".
//     Every published tier must be either measured or named unmeasured in the
//     rendered paragraph.
//   - (2026-09-11, ROADMAP #79) every figure must answer ONE question and the
//     paragraph must name it. `account+subagency 60/60` was judged on whether
//     the linking RULE had fired, the other strata on program ATTRIBUTION,
//     and the two were printed as one "precision". The exporter now reads the
//     study table by rubric (migration 015) and publishes only 'attribution';
//     this leg fails a site_meta block carrying any other rubric — or none —
//     and a paragraph that prints figures without saying which question
//     they answer.
//
// The published-tier universe is read from citations.json's crosswalk
// formulas ("… via method='X', confidence='Y'"), which is the same artifact
// leg i already reads and the same rows the site renders — one citation per
// published link, so the method set is exactly the set a reader can meet.
/** Every crosswalk method the corpus PUBLISHES — i.e. carries at least one
 *  high- or medium-confidence citation. citations.json mints exactly one row
 *  per published budget→award link, and every one of them states its method
 *  and tier in its `formula` sentence, so this set is the set of tiers a
 *  reader can actually meet. */
export function publishedLinkMethods(citations) {
  const found = new Set();
  const re = /via method='([^']+)', confidence='([^']+)'/;
  for (const row of Object.values(citations ?? {})) {
    const m = re.exec(row?.formula ?? "");
    if (m && (m[2] === "high" || m[2] === "medium")) found.add(m[1]);
  }
  return found;
}

/** True when `text` names `method` as a whole token — so "account" is not
 *  found inside "account+subagency", which would let the largest published
 *  tier go unnamed while the leg reported it named. */
function namesMethodToken(text, method) {
  const esc = method.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`(^|[^a-z0-9+_-])${esc}([^a-z0-9+_-]|$)`, "i").test(text);
}

/** Non-vacuity floor for the published-tier universe (measured 2026-09-04
 *  from data/site/json/citations.json: SIX methods publish at high or medium
 *  — account, account+subagency, account+tokens, announcement+lexicon,
 *  fpds-ap, subaward+lexicon). Below this the formula regex has stopped
 *  matching (a formula-sentence reword, a citations.json shape change) and
 *  the two directions that compare against the published universe would pass
 *  on an empty set — which is exactly how the `fpds-ap+account` figure
 *  survived. RE-MEASURE if the corpus changes; do not lower it to fit. */
const MIN_PUBLISHED_LINK_METHODS = 4;

/** The only rubric the exporter publishes (scripts/precision_study.py
 *  RUBRICS; export_site._link_precision_block's default). */
const PUBLISHED_RUBRIC = "attribution";

/** Published tier -> the study run its /methodology/ figure MUST come from:
 *  the gate-side twin of export_site._PINNED_PRECISION_SAMPLES, bound against
 *  the shipped artifact.
 *
 *  WHY (fix round 1, item 3). The pin is passed by the export call site, and
 *  the test that claimed to protect it only asserted the constant's value —
 *  deleting the kwarg left every test green and would have republished the
 *  announcement tier's precision from the wave-4 sample, a draw over ONE
 *  wave's links, under the tier's name. The unpinned block measures 48/55
 *  against the pinned 56/60. This check reads what actually shipped, so the
 *  edit fails a gate as well as a unit test. Change it only with a fresh draw
 *  over the tier itself, and change both sides together. */
const PINNED_PRECISION_SAMPLES = { "announcement+lexicon": "2026-09-04" };

/** The paragraph must name the question in the words the packets ask the
 *  adjudicator: "program attribution" and "execute this program element",
 *  in that order, within one sentence. */
const RUBRIC_PHRASE = /program attribution[^.]*execute this program element/i;

/** `injected` is passed only by the leg's unit test
 *  (__tests__/link-precision.test.mjs), which has to hand the leg corpora the
 *  build does not contain — a direction that has never been seen to fail is
 *  not a check. The gate itself always passes undefined and reads the shipped
 *  site_meta.json, citations.json and built /methodology/. */
export function runLinkPrecisionLeg(errors, notes, injected) {
  let siteMeta;
  let citations;
  let paragraphText = null;
  let paragraphExists = false;
  let methodologyBuilt = true;

  if (injected) {
    siteMeta = injected.siteMeta ?? {};
    citations = injected.citations ?? {};
    paragraphExists = injected.paragraphText != null;
    paragraphText = injected.paragraphText ?? null;
    methodologyBuilt = injected.methodologyBuilt ?? true;
  } else {
    const siteMetaPath = path.join(jsonDir, "site_meta.json");
    if (!fs.existsSync(siteMetaPath)) {
      errors.push(`leg n: ${siteMetaPath} missing — cannot recompute link_precision`);
      return;
    }
    try {
      siteMeta = JSON.parse(fs.readFileSync(siteMetaPath, "utf8"));
    } catch (e) {
      errors.push(`leg n: site_meta.json unparseable — ${e.message}`);
      return;
    }
    const citationsPath = path.join(jsonDir, "citations.json");
    if (!fs.existsSync(citationsPath)) {
      errors.push(
        `leg n: ${citationsPath} missing — cannot establish which link tiers ` +
          `the corpus publishes`,
      );
      return;
    }
    try {
      citations = JSON.parse(fs.readFileSync(citationsPath, "utf8"));
    } catch (e) {
      errors.push(`leg n: citations.json unparseable — ${e.message}`);
      return;
    }
    const methodRoot = readHtml("/methodology/");
    methodologyBuilt = methodRoot != null;
    const el = methodRoot?.querySelector("[data-link-precision]");
    paragraphExists = el != null;
    paragraphText = el ? norm(el.text) : null;
  }

  const linkPrecision = siteMeta.link_precision ?? {};
  // Pre-2026-09-04 exports carried {method: {confirmed, sampled}} at the top
  // level. That shape cannot answer "which tier does this link publish under
  // today", so it is a stale export, not a legacy dialect to tolerate.
  if (
    Object.keys(linkPrecision).length > 0 &&
    !Object.prototype.hasOwnProperty.call(linkPrecision, "methods")
  ) {
    errors.push(
      `leg n: site_meta.link_precision carries the pre-2026-09-04 flat shape ` +
        `(${Object.keys(linkPrecision).sort().join(", ")}) — re-run export-site; ` +
        `the flat shape tallied each link under the tier it carried when the ` +
        `sample was DRAWN, which published a figure for a withdrawn tier`,
    );
    return;
  }
  const figures = linkPrecision.methods ?? {};
  const methods = Object.keys(figures).sort();
  const unmeasured = [...(linkPrecision.unmeasured ?? [])].sort();

  // A pinned tier publishes its OWN draw's figure or none at all. (A tier the
  // pin left unmeasured is not an error here — `_link_precision_block` reports
  // it in `unmeasured`, and the sweep below makes the page name it.)
  for (const [method, run] of Object.entries(PINNED_PRECISION_SAMPLES)) {
    const got = figures[method];
    if (!got) continue;
    if (got.sample_id !== run) {
      errors.push(
        `leg n: site_meta.link_precision publishes "${method}" ` +
          `${got.confirmed}/${got.sampled} from sample ` +
          `${JSON.stringify(got.sample_id)}, and that tier is pinned to the ` +
          `${run} draw over the tier itself. A later run is a narrower ` +
          `population under the tier's name — the species leg n exists for. ` +
          `Re-run export-site (the call site passes ` +
          `export_site._PINNED_PRECISION_SAMPLES), or, if the tier was ` +
          `genuinely re-drawn, move the pin on both sides`,
      );
    }
  }

  if (methods.length === 0) {
    if (paragraphExists) {
      errors.push(
        "leg n (/methodology/): [data-link-precision] renders while " +
          "site_meta.link_precision is empty — the paragraph must stay " +
          "absent until a study has verdicts",
      );
    } else {
      notes.push(
        "leg n: link_precision is empty and /methodology/ renders no " +
          "paragraph (nothing published yet) ✓",
      );
    }
    return;
  }

  if (!methodologyBuilt) {
    errors.push("leg n: built /methodology/ missing");
    return;
  }
  if (!paragraphExists) {
    errors.push(
      `leg n (/methodology/): site_meta.link_precision has ${methods.length} ` +
        `method(s) but no [data-link-precision] paragraph renders`,
    );
    return;
  }

  // ── the rubric (ROADMAP #79) ─────────────────────────────────────────────
  const rubric = linkPrecision.rubric ?? null;
  if (rubric !== PUBLISHED_RUBRIC) {
    errors.push(
      `leg n: site_meta.link_precision.rubric is ${JSON.stringify(rubric)} — the ` +
        `exporter publishes only strata judged on '${PUBLISHED_RUBRIC}' ` +
        `(migration 015, ROADMAP #79); a block with another rubric, or none, is a ` +
        `stale or mis-filtered export — re-run export-site`,
    );
    return;
  }
  if (!RUBRIC_PHRASE.test(paragraphText ?? "")) {
    errors.push(
      `leg n (/methodology/): [data-link-precision] never names the rubric — the ` +
        `paragraph must say the figures measure program attribution ("does this ` +
        `award execute this program element?"), or a reader takes "the rule fired" ` +
        `and "the award paid for this program" for the same measurement`,
    );
  }

  const text = paragraphText ?? "";
  const rendered = new Map();
  for (const m of text.matchAll(/([a-z0-9][a-z0-9+_-]*)\s+([\d,]+)\/([\d,]+)/gi)) {
    rendered.set(m[1], {
      confirmed: Number(m[2].replace(/,/g, "")),
      sampled: Number(m[3].replace(/,/g, "")),
    });
  }

  let checked = 0;
  for (const method of methods) {
    const want = figures[method];
    const got = rendered.get(method);
    if (!got) {
      errors.push(
        `leg n (/methodology/): [data-link-precision] states no figure for ` +
          `"${method}" (site_meta has ${want.confirmed}/${want.sampled})`,
      );
      continue;
    }
    checked++;
    if (got.confirmed !== want.confirmed || got.sampled !== want.sampled) {
      errors.push(
        `leg n (/methodology/): "${method}" renders ${got.confirmed}/${got.sampled}, ` +
          `site_meta.link_precision has ${want.confirmed}/${want.sampled}`,
      );
    }
  }
  for (const rm of rendered.keys()) {
    if (!methods.includes(rm)) {
      errors.push(
        `leg n (/methodology/): [data-link-precision] states a figure for ` +
          `"${rm}", which is not in site_meta.link_precision`,
      );
    }
  }

  // ── the published-tier universe (final review C1/C2) ─────────────────────
  const published = publishedLinkMethods(citations);
  if (published.size < MIN_PUBLISHED_LINK_METHODS) {
    errors.push(
      `leg n: only ${published.size} published link method(s) recovered from ` +
        `citations.json (floor ${MIN_PUBLISHED_LINK_METHODS}, measured ` +
        `2026-09-04 at 6). The crosswalk formula sentence has changed shape, ` +
        `so the two directions below compare against an empty universe and ` +
        `pass on anything — which is how a withdrawn tier's figure shipped. ` +
        `Re-derive the parse; do not lower the floor`,
    );
    return;
  }
  for (const method of methods) {
    if (!published.has(method)) {
      errors.push(
        `leg n (/methodology/): "${method}" is published as measured precision ` +
          `of a tier the corpus does NOT publish — no high- or ` +
          `medium-confidence link carries method='${method}'. A withdrawn tier ` +
          `keeps its verdicts; it must not keep its figure`,
      );
    }
  }
  for (const method of [...published].sort()) {
    if (methods.includes(method)) continue;
    if (!unmeasured.includes(method)) {
      errors.push(
        `leg n: the corpus publishes method='${method}' at high/medium but ` +
          `site_meta.link_precision neither measures it nor lists it in ` +
          `\`unmeasured\` — an unmeasured tier that says nothing reads as one ` +
          `that passed`,
      );
      continue;
    }
    if (!namesMethodToken(text, method)) {
      errors.push(
        `leg n (/methodology/): "${method}" is listed unmeasured in site_meta ` +
          `but [data-link-precision] never names it — the paragraph must say ` +
          `which published tiers carry no measured figure`,
      );
    }
  }

  if (errors.every((e) => !e.startsWith("leg n"))) {
    notes.push(
      `leg n: [data-link-precision] states all ${checked} measured method(s) ` +
        `from site_meta.link_precision (values match, rubric '${rubric}' named) ` +
        `and names all ${unmeasured.length} unmeasured published tier(s); ` +
        `${published.size} published method(s) in citations.json, all accounted for ✓`,
    );
  }
}




// ═══════════════════════════════════════════════════════════════════════════
// leg o — per-award hand-adjudication coverage (ROADMAP #109, 2026-09-11)
// ═══════════════════════════════════════════════════════════════════════════
//
// THE DEFECT. /methodology/ §Budget-to-contract links opened: "As of September
// 2026, every published link was individually hand-adjudicated: each award's
// contract descriptions were investigated against the program's J-book
// narratives and project titles, and every proposed program-level link was
// then challenged by two independent adversarial reviewers — a link is
// published as high only if neither could refute it." Measured 2026-09-11
// against Postgres: of 12,595 links the crosswalk grades high or medium,
// 9,587 carry an `award_pe_adjudications` row AT ALL — three of the five
// published methods (announcement+lexicon, fpds-ap, subaward+lexicon) carry
// ZERO; 8,474 of the adjudications that exist say the work could not be
// pinned to any one program element; and 60 rows in the whole table record
// `refuter_lenses_passed = 2` — 57 of them on a link the crosswalk grades
// high or medium. Every other number on the page was derived and gated. This
// sentence was authored, universal, and false — and no leg could see it,
// because there was nothing for a number to disagree with.
//
// THE RULE. The sentence is now rendered from site_meta.link_adjudication
// (export_site._link_adjudication_block), and this leg binds it:
//   - each of `published`, `adjudicated`, `unpinned` appears in the passage
//     formatted the way lib/format formatCount formats a count;
//   - BOTH dates appear, each on its own clause: `measured_on` (when the
//     census was taken) before `as_of` (when the last adjudication was made).
//     Fix round 1, C1 — the passage used to open "As of {as_of}" over counts
//     taken 10 days later, and this leg REQUIRED that. On 2026-09-01 the
//     corpus held 9,864 published links, not 12,595: the other 2,731 were
//     created 2026-09-04, which is exactly why they carry no adjudication.
//     A leg that binds a date to the wrong clause cements the wrong date;
//   - the passage carries NO number the block does not hold — a figure typed
//     back into the prose (the species this whole leg exists for) fails here
//     even when it is plausible;
//   - the passage is present iff the block is non-empty — a corpus with no
//     adjudication renders nothing rather than the old claim;
//   - every method the block says carries NO adjudication is NAMED — silence
//     about an unadjudicated path reads as a path that passed (the same
//     direction leg n enforces for unmeasured precision tiers);
//   - the block agrees with itself (per-method sums, adjudicated ≤ published,
//     unpinned ≤ adjudicated), so a mis-shaped export cannot supply numbers
//     the prose then faithfully renders;
//   - it is non-vacuous: `by_method` names at least MIN_ADJUDICATION_METHODS
//     paths. With `by_method = {}` and self-consistent headline counts the
//     sum check, the unadjudicated-path naming and the completeness check all
//     silently skip — leg n carries MIN_PUBLISHED_LINK_METHODS for the same
//     failure mode;
//   - the HIGH sub-block (fix round 1, R-6c-4) is bound the same way, in its
//     own [data-link-adjudication-high] passage. Four surfaces graded the
//     High tier "verified adversarially"; measured over the mart, 60 of the
//     768 links published at high carry a per-award adjudication and 708
//     `announcement+lexicon` links carry none;
//   - each figure is bound to its SLOT, not to the passage (fix round 2,
//     R-6c-6). Presence plus a stray-number check still passes a sentence
//     assembled out of the block's own figures in the wrong order — "12,595
//     of the 9,587 links … carry a per-award hand adjudication", or the
//     High passage's "768 of the 768 … all 768 of them challenged by two
//     independent adversarial reviewers". Both scored zero errors. The
//     numbers are now read in document order and the sequence must be the
//     derived one;
//   - the `high` sub-block must EXIST whenever the block grades links (fix
//     round 2, R-6c-7, dated). A block with no `high` and a page with no
//     High passage used to be a clean pass, so any export-time failure
//     reading the mart deleted the entire High-tier census with every leg
//     green.
/** The three counts the opening passage must state, in the order the page
 *  states them. Keyed by the block field so an error names the field to
 *  re-derive. */
const ADJUDICATION_COUNTS = ["adjudicated", "published", "unpinned"];

/** The three counts the High-tier passage must state. */
const HIGH_COUNTS = ["adjudicated_high", "published_high", "two_lens_high"];

/** Non-vacuity floor on `by_method` (fix round 1, M4). MEASURED 2026-09-11
 *  at FIVE: account+subagency, account+tokens, announcement+lexicon, fpds-ap
 *  and subaward+lexicon all carry rows the crosswalk grades high or medium.
 *  The floor sits below that with headroom for ordinary corpus movement.
 *  Below it the export has stopped reporting per-path coverage and three of
 *  this leg's directions pass on an empty set — which is how a sentence that
 *  names no unadjudicated path would read as a corpus with none. RE-MEASURE
 *  if the corpus changes; never lower it to fit a red run. */
const MIN_ADJUDICATION_METHODS = 4;

export function runLinkAdjudicationLeg(errors, notes, injected) {
  let siteMeta;
  let passageText = null;
  let passageExists = false;
  let highText = null;
  let highExists = false;
  let methodologyBuilt = true;

  if (injected) {
    siteMeta = injected.siteMeta ?? {};
    passageExists = injected.passageText != null;
    passageText = injected.passageText ?? null;
    highExists = injected.highText != null;
    highText = injected.highText ?? null;
    methodologyBuilt = injected.methodologyBuilt ?? true;
  } else {
    const siteMetaPath = path.join(jsonDir, "site_meta.json");
    if (!fs.existsSync(siteMetaPath)) {
      errors.push(`leg o: ${siteMetaPath} missing — cannot check link_adjudication`);
      return;
    }
    try {
      siteMeta = JSON.parse(fs.readFileSync(siteMetaPath, "utf8"));
    } catch (e) {
      errors.push(`leg o: site_meta.json unparseable — ${e.message}`);
      return;
    }
    const methodRoot = readHtml("/methodology/");
    methodologyBuilt = methodRoot != null;
    const el = methodRoot?.querySelector("[data-link-adjudication]");
    passageExists = el != null;
    passageText = el ? norm(el.text) : null;
    const highEl = methodRoot?.querySelector("[data-link-adjudication-high]");
    highExists = highEl != null;
    highText = highEl ? norm(highEl.text) : null;
  }

  const block = siteMeta.link_adjudication ?? {};
  if (Object.keys(block).length === 0) {
    if (passageExists || highExists) {
      errors.push(
        "leg o (/methodology/): [data-link-adjudication] renders while " +
          "site_meta.link_adjudication is empty — the hand-adjudication " +
          "sentence must stay absent until an adjudication touches a " +
          "published link, never fall back to a claim about one",
      );
    } else {
      notes.push(
        "leg o: link_adjudication is empty and /methodology/ renders no " +
          "hand-adjudication sentence (nothing adjudicated yet) ✓",
      );
    }
    return;
  }

  if (!methodologyBuilt) {
    errors.push("leg o: built /methodology/ missing");
    return;
  }
  // A block exported before `measured_on` existed cannot date its own census,
  // so the page renders no passage at all — which would otherwise surface
  // below as the much less useful "the block has coverage and nothing renders".
  if (typeof block.measured_on !== "string") {
    errors.push(
      "leg o: site_meta.link_adjudication carries coverage but no " +
        "`measured_on` — the artifact predates the field that dates the " +
        "census (fix round 1, C1), so /methodology/ renders nothing for it. " +
        "Re-run export-site; do not re-date the counts by `as_of`",
    );
    return;
  }
  if (!passageExists) {
    errors.push(
      "leg o (/methodology/): site_meta.link_adjudication carries coverage " +
        `(${block.adjudicated} of ${block.published} links adjudicated) but no ` +
        "[data-link-adjudication] passage renders — the section would open " +
        "with the inference and never say how much of it was reviewed",
    );
    return;
  }

  const text = passageText ?? "";
  const allowed = new Set();
  for (const field of ADJUDICATION_COUNTS) {
    const value = block[field];
    if (typeof value !== "number") {
      errors.push(
        `leg o: site_meta.link_adjudication.${field} is ` +
          `${JSON.stringify(value)}, not a count — re-run export-site`,
      );
      continue;
    }
    const rendered = value.toLocaleString("en-US");
    allowed.add(rendered);
    if (!text.includes(rendered)) {
      errors.push(
        `leg o (/methodology/): [data-link-adjudication] never states ` +
          `${field} = ${rendered} — the sentence must render every figure it ` +
          `claims from site_meta.link_adjudication, not around it`,
      );
    }
  }
  // Both dates, each on its own clause (fix round 1, C1). `measured_on` is
  // when the census was taken and `as_of` when the last adjudication was
  // made; they are ten days apart on the live corpus and the counts belong to
  // the first. Requiring `measured_on` to come FIRST is what stops the
  // passage sliding back to "As of {as_of}, {today's counts}".
  for (const field of ["measured_on", "as_of"]) {
    if (typeof block[field] !== "string" || !text.includes(block[field])) {
      errors.push(
        `leg o (/methodology/): the passage does not carry ${field} ` +
          `${JSON.stringify(block[field] ?? null)} — an undated coverage ` +
          `claim reads as a standing one, and a claim dated by the wrong ` +
          `event reads as one measured then`,
      );
    }
  }
  if (
    typeof block.measured_on === "string" &&
    typeof block.as_of === "string" &&
    block.measured_on !== block.as_of &&
    text.includes(block.measured_on) &&
    text.includes(block.as_of) &&
    text.indexOf(block.as_of) < text.indexOf(block.measured_on)
  ) {
    errors.push(
      `leg o (/methodology/): the passage dates itself ${block.as_of} (the ` +
        `last adjudication) before ${block.measured_on} (when the counts ` +
        `were taken) — the census clause must carry measured_on. On ` +
        `${block.as_of} the corpus was smaller than the one these counts ` +
        `describe, so that ordering states a ratio that never held`,
    );
  }

  // No number the block does not hold. ISO dates go first (both dates are
  // checked above and their 2026 / 09 / 11 must not read as stray figures).
  const undated = (s) => s.replace(/\d{4}-\d{2}-\d{2}/g, " ");
  const reportStrays = (label, body, allowedSet) => {
    for (const m of undated(body).matchAll(/\d[\d,]*/g)) {
      if (!allowedSet.has(m[0])) {
        errors.push(
          `leg o (/methodology/): [${label}] states "${m[0]}", ` +
            `which is not a figure in site_meta.link_adjudication ` +
            `(${[...allowedSet].join(", ")}) — every number in this sentence ` +
            `is derived; a typed one is the defect it was rewritten for`,
        );
      }
    }
  };
  reportStrays("data-link-adjudication", text, allowed);

  // ── the slot binding (fix round 2, R-6c-6) ───────────────────────────────
  //
  // The `includes` check above asks only whether a figure appears SOMEWHERE
  // in the passage, and `reportStrays` only whether a number is allowed. Both
  // pass on a passage that PERMUTES the block's own figures: "12,595 of the
  // 9,587 links … carry a per-award hand adjudication" is built entirely out
  // of allowed numbers and states a ratio that never held, and on the High
  // passage "768 of the 768 links published at high … all 768 of them
  // challenged by two independent adversarial reviewers" is exactly the claim
  // R-6c-4 exists to bound — it passed this leg with zero errors.
  //
  // So the numbers are read IN DOCUMENT ORDER and the whole sequence must be
  // the one the block derives, slot for slot. That is wording-independent: a
  // rewrite may say anything it likes between the figures, but it may not
  // move one into another's place, drop one, or add one.
  const reportSlots = (label, body, slots) => {
    const got = [...undated(body).matchAll(/\d[\d,]*/g)].map((m) => m[0]);
    const want = slots.map(([, v]) => v.toLocaleString("en-US"));
    if (got.length === want.length && want.every((v, i) => v === got[i])) return;
    errors.push(
      `leg o (/methodology/): [${label}] states its figures in the order ` +
        `${got.join(", ") || "(none)"} but the block derives ` +
        `${want.join(", ")} — ${slots.map(([f]) => f).join(", ")}, in that ` +
        `order. Every figure must sit in the slot it was derived for; a ` +
        `passage that permutes its own numbers states a ratio that never ` +
        `held while passing both the presence check and the stray-number ` +
        `check above`,
    );
  };
  if (ADJUDICATION_COUNTS.every((f) => typeof block[f] === "number")) {
    reportSlots(
      "data-link-adjudication",
      text,
      ADJUDICATION_COUNTS.map((f) => [f, block[f]]),
    );
  }

  const unadjudicated = block.unadjudicated_methods ?? [];
  for (const method of unadjudicated) {
    if (!namesMethodToken(text, method)) {
      errors.push(
        `leg o (/methodology/): "${method}" publishes links and carries NO ` +
          `adjudication row, but the passage never names it — an unreviewed ` +
          `evidence path that says nothing reads as one that was reviewed`,
      );
    }
  }

  // The block against itself: prose rendered faithfully from a mis-shaped
  // export is still a false sentence.
  const byMethod = block.by_method ?? {};
  const sum = (field) =>
    Object.values(byMethod).reduce((t, v) => t + (v?.[field] ?? 0), 0);
  if (Object.keys(byMethod).length < MIN_ADJUDICATION_METHODS) {
    errors.push(
      `leg o: site_meta.link_adjudication.by_method names ` +
        `${Object.keys(byMethod).length} path(s) — below the do-not-lower ` +
        `floor of ${MIN_ADJUDICATION_METHODS} measured 2026-09-11 at 5. The ` +
        `per-method sum check, the unadjudicated-path naming and the ` +
        `completeness check all pass on an empty by_method, so this is the ` +
        `leg losing its teeth, not a clean run. Re-derive the export; do not ` +
        `lower the floor`,
    );
  }
  if (Object.keys(byMethod).length > 0) {
    for (const field of ["published", "adjudicated"]) {
      if (sum(field) !== block[field]) {
        errors.push(
          `leg o: site_meta.link_adjudication.${field} is ${block[field]} but ` +
            `by_method sums to ${sum(field)} — re-run export-site`,
        );
      }
    }
    const silent = Object.entries(byMethod)
      .filter(([m, v]) => (v?.adjudicated ?? 0) === 0 && !unadjudicated.includes(m))
      .map(([m]) => m);
    if (silent.length > 0) {
      errors.push(
        `leg o: ${silent.join(", ")} carr${silent.length === 1 ? "ies" : "y"} ` +
          `no adjudication but ${silent.length === 1 ? "is" : "are"} missing ` +
          `from unadjudicated_methods — the page names that list, so a path ` +
          `left off it goes unnamed`,
      );
    }
  }
  if (block.adjudicated > block.published || block.unpinned > block.adjudicated) {
    errors.push(
      `leg o: site_meta.link_adjudication is inverted (${block.adjudicated} ` +
        `adjudicated of ${block.published} published, ${block.unpinned} ` +
        `unpinned) — a coverage claim cannot exceed its own universe`,
    );
  }

  // ── the High tier's own census (fix round 1, R-6c-4) ─────────────────────
  // `high` is absent on a warehouse with no mart, and the High-tier sentence
  // then states no census at all — never one counted against
  // budget_line_awards, which does not know which links dbt demoted.
  const high = block.high ?? null;
  if (!high) {
    if (highExists) {
      errors.push(
        "leg o (/methodology/): [data-link-adjudication-high] renders while " +
          "site_meta.link_adjudication carries no `high` census — the " +
          "High-tier grading may state the evidence it has, never a count " +
          "nothing measured",
      );
    } else {
      // The dated non-vacuity companion (fix round 2, R-6c-7). A block with
      // NO high census and a page with no High passage used to be a clean
      // pass, which made the whole High-tier grading disappear-able: any
      // mart-side failure at export time returned null from
      // _published_high_links, the block omitted `high`, the page rendered
      // no census and every leg stayed green. That is the vacuity shape M4
      // closed for `by_method`, one sub-block over. The exporter now raises
      // on anything but a missing mart; this is the half of the direction a
      // gate can see: if the crosswalk grades links at all, the tier they
      // are graded INTO publishes, and its census is owed.
      //
      // DATED 2026-09-11: 768 links publish at high (measured over
      // fct_budget_to_awards), and the tier has published continuously since
      // 2026-09-01. Never remove or weaken this to make a red run go green —
      // the run is red because the page lost a measurement.
      errors.push(
        "leg o (/methodology/): site_meta.link_adjudication grades links " +
          `(${block.adjudicated} of ${block.published}) but carries no ` +
          "`high` sub-block — the High tier publishes and no census was " +
          "exported. `_published_high_links` returns null only for a " +
          "warehouse with no mart; every other failure now raises. " +
          "Re-run export-site against a built warehouse (768 links published " +
          "at high, measured 2026-09-11; the tier has published since " +
          "2026-09-01). Do not drop this check to clear the run",
      );
    }
  } else if (!highExists) {
    errors.push(
      `leg o (/methodology/): site_meta.link_adjudication.high carries a ` +
        `census (${high.adjudicated_high} of ${high.published_high} links ` +
        `published at high hand-adjudicated) but no ` +
        `[data-link-adjudication-high] passage renders — the tier would be ` +
        `graded without saying how much of it was reviewed`,
    );
  } else {
    const highAllowed = new Set();
    for (const field of HIGH_COUNTS) {
      const value = high[field];
      if (typeof value !== "number") {
        errors.push(
          `leg o: site_meta.link_adjudication.high.${field} is ` +
            `${JSON.stringify(value)}, not a count — re-run export-site`,
        );
        continue;
      }
      const rendered = value.toLocaleString("en-US");
      highAllowed.add(rendered);
      if (!highText.includes(rendered)) {
        errors.push(
          `leg o (/methodology/): [data-link-adjudication-high] never states ` +
            `${field} = ${rendered} — the High tier's grading must render ` +
            `every figure it claims from site_meta.link_adjudication.high`,
        );
      }
    }
    // Every per-path figure is derived too, plus the remainder the sentence
    // names ("the other N"), so stating either is not a typed number.
    const byPath = high.by_path ?? {};
    for (const entry of Object.values(byPath)) {
      for (const v of Object.values(entry ?? {})) {
        if (typeof v === "number") highAllowed.add(v.toLocaleString("en-US"));
      }
    }
    if (
      typeof high.published_high === "number" &&
      typeof high.adjudicated_high === "number"
    ) {
      highAllowed.add(
        (high.published_high - high.adjudicated_high).toLocaleString("en-US"),
      );
    }
    reportStrays("data-link-adjudication-high", highText, highAllowed);

    // The paths whose high links are not all adjudicated — the remainder the
    // sentence must name (below), and the reason its "the other N" clause
    // renders at all. page.tsx derives both from this same set.
    const unreviewedPaths = Object.entries(byPath)
      .filter(([, v]) => (v?.high ?? 0) > (v?.adjudicated ?? 0))
      .map(([m]) => m);
    // The High passage's slots, in the order page.tsx renders them
    // (fix round 2, R-6c-6). Two are conditional, and the condition is the
    // page's own:
    //   * the adversarial clause ("all N of them challenged by two
    //     independent adversarial reviewers") renders only while something
    //     at high IS adjudicated — asserting a review over an empty set
    //     would be a false sentence the moment a corpus published a high
    //     tier with no adjudication (rider ii);
    //   * the remainder clause ("the other N rest on …") renders only while
    //     some path publishes at high unadjudicated.
    // Their ABSENCE is accepted; their presence in the wrong case is not,
    // because the sequence would then be one figure too long.
    if (HIGH_COUNTS.every((f) => typeof high[f] === "number")) {
      const slots = [
        ["adjudicated_high", high.adjudicated_high],
        ["published_high", high.published_high],
      ];
      if (high.adjudicated_high > 0) {
        slots.push(["two_lens_high", high.two_lens_high]);
      }
      if (unreviewedPaths.length > 0) {
        slots.push([
          "published_high − adjudicated_high",
          high.published_high - high.adjudicated_high,
        ]);
      }
      reportSlots("data-link-adjudication-high", highText, slots);
    }

    const pathSum = (field) =>
      Object.values(byPath).reduce((t, v) => t + (v?.[field] ?? 0), 0);
    for (const [field, path_field] of [
      ["published_high", "high"],
      ["adjudicated_high", "adjudicated"],
      ["two_lens_high", "two_lens"],
    ]) {
      if (
        Object.keys(byPath).length > 0 &&
        pathSum(path_field) !== high[field]
      ) {
        errors.push(
          `leg o: site_meta.link_adjudication.high.${field} is ` +
            `${high[field]} but by_path sums to ${pathSum(path_field)} — ` +
            `re-run export-site`,
        );
      }
    }
    if (
      high.adjudicated_high > high.published_high ||
      high.two_lens_high > high.adjudicated_high
    ) {
      errors.push(
        `leg o: site_meta.link_adjudication.high is inverted ` +
          `(${high.adjudicated_high} adjudicated and ${high.two_lens_high} ` +
          `two-lens of ${high.published_high} published at high) — the ` +
          `adversarially reviewed set cannot exceed the adjudicated one`,
      );
    }
    // The claim the four surfaces used to make of the WHOLE tier. It may be
    // made of the two-lens population and no larger one, so the passage must
    // name the evidence paths the remainder rests on instead.
    for (const method of unreviewedPaths) {
      if (!namesMethodToken(highText, method)) {
        errors.push(
          `leg o (/methodology/): "${method}" publishes ` +
            `${byPath[method].high - byPath[method].adjudicated} link(s) at ` +
            `HIGH with no per-award adjudication, but the tier's grading ` +
            `never names it — "verified adversarially" over an unnamed ` +
            `remainder is the claim this leg exists to bound`,
        );
      }
    }
  }

  if (errors.every((e) => !e.startsWith("leg o"))) {
    notes.push(
      `leg o: [data-link-adjudication] states ${block.adjudicated.toLocaleString("en-US")} ` +
        `of ${block.published.toLocaleString("en-US")} links adjudicated ` +
        `(${block.unpinned.toLocaleString("en-US")} unpinned; measured ` +
        `${block.measured_on}, latest adjudication ${block.as_of}) ` +
        `from site_meta.link_adjudication, carries no undeclared figure, and names ` +
        `all ${unadjudicated.length} unadjudicated path(s)` +
        (high
          ? `; [data-link-adjudication-high] states ${high.adjudicated_high.toLocaleString("en-US")} ` +
            `of ${high.published_high.toLocaleString("en-US")} published at high ` +
            `hand-adjudicated (${high.two_lens_high.toLocaleString("en-US")} two-lens)`
          : "") +
        ` ✓`,
    );
  }
}


// ═══════════════════════════════════════════════════════════════════════════
// leg l — family labels that won a coin flip (ROADMAP #10, option A)
// ═══════════════════════════════════════════════════════════════════════════
//
// THE DEFECT. `/companies/families/` and `/company/{slug}/` publish
// `dim_entities.display_name`, which is the registered `recipient_parent_name`
// of the family member holding the most money — chosen by an argmax that has
// no notion of "close" and no notion of "current". `ROCKWELL COLLINS AUSTRALIA
// PTY LIMITED` was the <h1> of a family that is 97.3% RAYTHEON COMPANY
// ($18.93B of $19.47B, all 15 members sharing parent UEI EGAVSJTA2D81); it won
// by 3.1% over `RAYTHEON COMPANY`, and RTX reverted that registration in
// FY2026. The site was publishing a label the registrant had already
// corrected. Every existing gate passed: the grouping was right, the dollars
// were right, the citation was right. Only the string was wrong, and nothing
// graded strings — `confidence` grades whether a family spans two parent UEIs,
// which is a different question.
//
// THE RULE, stated so it catches the NEXT one rather than this one:
//
//   A PUBLISHED FAMILY WHOSE LABEL WON ITS PARENT-REGISTRATION ARGMAX BY LESS
//   THAN 15% MUST CARRY A ROW IN data-seeds/entity_display_aliases.csv.
//
// The row may RELABEL the family or merely PIN the argmax winner — the seed's
// `evidence` column types which — but a near-tie must have been looked at by a
// human, and the looking must be written down. 15 published families ($255.2B,
// 9.7% of published family dollars) were inside the threshold when this leg
// was written (2026-09-01); the live count is in this leg's note.
//
// Everything is recomputed rather than read back:
//   * the margins come from familylabel-recompute.py (DuckDB over the award
//     lake, mirroring entity_graph._PICK_SQL's parent_pick ranking). It never
//     reads the seed, entities_top.json or the built HTML;
//   * the labels come from the SEED, parsed here;
//   * what the site SHOWS comes from the built HTML.
// A pipeline that dropped an alias cannot satisfy this leg by also dropping it
// from the payload, and a page that hand-typed a name cannot satisfy it at all.
//
// Vacuity guards, all structural — no pinned literals, because a literal here
// would have to be updated by the same person who broke the thing it pins:
// the recompute must cover ≥100 families, at least one must be inside the
// threshold, and the seed must resolve ≥1 relabel onto a built page.
//
// Task 29S: the threshold, the near-tie predicate and the census live in ONE
// module, src/lib/entity-label-margins.mjs, which /methodology/ imports too.
// The page used to TYPE the census ("15 of the 200 …") and this leg read the
// literal back; the 2026-09-06 FY2026 refresh made it false before anyone
// retyped it. The page now renders labelCensusSentence() of its own census
// (entities_top.json + the labels the exporter resolved from the seed), and
// part (4) below requires the built page to contain exactly the sentence
// this leg's census renders (the lake recompute + the seed parsed here).

const DISPLAY_ALIAS_SEED = path.resolve(
  repoRoot,
  "data-seeds",
  "entity_display_aliases.csv",
);

// NEAR_TIE_MARGIN (15%) is imported from src/lib/entity-label-margins.mjs —
// the one copy, shared with the page that states it (Task 29S). Lowering it
// to make a family pass is the one edit it must never see.

/** Slug for a warehouse family_key — export_site.py's own derivation. */
function familySlug(familyKey) {
  return familyKey.toLowerCase().replace(/ /g, "-");
}

function familyLabelMargins() {
  const script = path.resolve(__dirname, "familylabel-recompute.py");
  const res = spawnSync("uv", ["run", "python", script], {
    cwd: repoRoot,
    encoding: "utf8",
    timeout: 600000,
    maxBuffer: 32 * 1024 * 1024,
  });
  if (res.status !== 0) {
    throw new Error(
      `familylabel-recompute.py failed (status ${res.status}): ${
        (res.stderr || "").slice(-800)
      }`,
    );
  }
  const parsed = JSON.parse(res.stdout);
  if (parsed.__error__) throw new Error(parsed.__error__);
  return parsed;
}

function runFamilyLabelLeg(errors, notes) {
  // ── the seed ────────────────────────────────────────────────────────────
  //
  // A missing or empty seed is an error, but NOT an early return: with no
  // aliases every near-tie family is unreviewed, which is precisely the
  // pre-fix state, and a reader of this gate's output needs to be told WHICH
  // families and by what margin. A leg that answers "seed missing" and stops
  // hides the very finding it exists to surface.
  const seedRows = fs.existsSync(DISPLAY_ALIAS_SEED)
    ? parseCsv(fs.readFileSync(DISPLAY_ALIAS_SEED, "utf8"))
    : (errors.push(
        `leg l: display-alias seed missing at ${DISPLAY_ALIAS_SEED} — every ` +
          `near-tie family below is unreviewed`,
      ),
      []);
  const aliases = new Map();
  for (const r of seedRows) {
    const key = (r.family_key || "").trim();
    const label = (r.display_name || "").trim();
    const evidence = (r.evidence || "").trim();
    if (!key || !label || !evidence) {
      errors.push(
        `leg l: seed row ${JSON.stringify(r.family_key ?? "")} is missing ` +
          `family_key, display_name or evidence`,
      );
      continue;
    }
    if (aliases.has(key)) {
      errors.push(`leg l: seed aliases ${key} twice`);
      continue;
    }
    aliases.set(key, { label, evidence });
  }
  if (aliases.size === 0 && seedRows.length > 0) {
    errors.push("leg l: the display-alias seed resolved no rows");
  }

  // ── the recompute ───────────────────────────────────────────────────────
  let truth;
  try {
    truth = familyLabelMargins();
  } catch (e) {
    errors.push(`leg l: ${e.message}`);
    return;
  }
  const families = truth.families ?? [];
  if (families.length < 100) {
    errors.push(
      `leg l: the margin recompute covered only ${families.length} published ` +
        `families — under 100, so the leg would pass by seeing nothing`,
    );
    return;
  }

  // ── THE RULE ────────────────────────────────────────────────────────────
  const nearTies = families.filter(isNearTie);
  let census;
  try {
    census = labelMarginCensus(families, aliases.keys());
  } catch (e) {
    errors.push(`leg l: ${e.message}`);
    return;
  }
  if (nearTies.length === 0) {
    errors.push(
      `leg l: no published family is inside the ${(NEAR_TIE_MARGIN * 100).toFixed(0)}% ` +
        `margin (vacuous) — the recompute is not measuring what this leg checks`,
    );
    return;
  }
  const nearTieDollars = nearTies.reduce((n, f) => n + f.total_obligation, 0);
  for (const f of nearTies.sort((a, b) => a.margin - b.margin)) {
    if (aliases.has(f.family_key)) continue;
    errors.push(
      `leg l: ${f.family_key} publishes "${f.display_name}" ` +
        `($${(f.total_obligation / 1e9).toFixed(2)}B), a label that won its ` +
        `parent-registration argmax by only ${(f.margin * 100).toFixed(1)}% — ` +
        `$${(f.won_dollars / 1e9).toFixed(3)}B as "${f.won}" over ` +
        `$${(f.runner_up_dollars / 1e9).toFixed(3)}B as "${f.runner_up}" on its ` +
        `dominant member ${f.dominant_name} (${f.dominant_uei}). A label decided ` +
        `by that margin is not a fact the pipeline read; it must be reviewed and ` +
        `recorded in data-seeds/entity_display_aliases.csv (relabel it, or pin ` +
        `the winner with evidence=pin) before it is published`,
    );
  }

  // ── the seed points at real published families ──────────────────────────
  const byKey = new Map(families.map((f) => [f.family_key, f]));
  for (const [key, a] of aliases) {
    const f = byKey.get(key);
    if (!f) {
      errors.push(
        `leg l: the seed aliases ${key} to "${a.label}", but no published ` +
          `family has that key — the row relabels nothing and ships looking ` +
          `like it had`,
      );
      continue;
    }
    // A `pin` asserts the argmax winner IS the label; it must therefore change
    // nothing the casing rule would not already have produced. A `pin` that
    // moves the string is a relabel wearing the wrong evidence kind.
    const derived = displayCompanyName(f.display_name).display;
    if (a.evidence === "pin" && a.label !== derived) {
      errors.push(
        `leg l: ${key} is seeded evidence=pin with label "${a.label}", but the ` +
          `casing rule renders "${derived}" — a pin records that the argmax ` +
          `winner is right, so it cannot change what is on screen`,
      );
    }
    if (a.evidence !== "pin" && a.label === derived) {
      errors.push(
        `leg l: ${key} is seeded evidence=${a.evidence} with label "${a.label}", ` +
          `which is exactly what the casing rule already renders — that is a ` +
          `pin, and typing it as a relabel overstates what the row did`,
      );
    }
  }

  // ── what the built pages actually show ──────────────────────────────────
  const relabelled = [...aliases.entries()].filter(
    ([key, a]) =>
      byKey.has(key) &&
      a.label !== displayCompanyName(byKey.get(key).display_name).display,
  );
  const seedLabels = new Set([...aliases.values()].map((a) => a.label));

  // (1) No page may publish a company label the seed did not author. Swept
  //     site-wide: gate 2 leg (tc) checks a label element against its OWN
  //     attribute, which a hand-typed name would satisfy.
  let labelled = 0;
  for (const file of walkHtml(outDir)) {
    const html = fs.readFileSync(file, "utf8");
    if (!html.includes("data-company-label")) continue;
    const root = parse(html);
    for (const el of root.querySelectorAll("[data-company-label]")) {
      labelled += 1;
      const value = el.getAttribute("data-company-label") ?? "";
      if (!seedLabels.has(value)) {
        errors.push(
          `leg l (${path.relative(outDir, file)}): renders the company label ` +
            `${JSON.stringify(value)}, which no row of ` +
            `data-seeds/entity_display_aliases.csv authored`,
        );
      }
    }
  }

  // (2) Every relabelled family's own page must publish the label AND keep the
  //     registry string visible. The relabel is only honest with both.
  let pagesChecked = 0;
  for (const [key, a] of relabelled) {
    const f = byKey.get(key);
    const url = `/company/${familySlug(key)}/`;
    const root = readHtml(url);
    if (!root) {
      errors.push(`leg l (${url}): built page missing for a relabelled family`);
      continue;
    }
    pagesChecked += 1;
    const h1 = root.querySelector("h1");
    const shown = (h1?.text ?? "").replace(/\s+/g, " ").trim();
    if (shown !== a.label) {
      errors.push(
        `leg l (${url}): <h1> renders ${JSON.stringify(shown)}, but the seed ` +
          `publishes ${JSON.stringify(a.label)} for ${key}`,
      );
    }
    const note = root.querySelector("[data-registry-note]");
    if (!note || !note.text.includes(f.display_name)) {
      errors.push(
        `leg l (${url}): the registry string ${JSON.stringify(f.display_name)} ` +
          `is not visible on the page that stopped using it as its heading — a ` +
          `relabel without the registered name is a name the reader cannot check`,
      );
    }
  }

  // (3) /companies/ must agree with the page it links to.
  const companies = readHtml("/companies/");
  if (!companies) {
    errors.push("leg l: built /companies/ missing");
  } else {
    const rendered = new Set(
      companies
        .querySelectorAll("[data-company-label]")
        .map((el) => el.getAttribute("data-company-label") ?? ""),
    );
    for (const [key, a] of relabelled) {
      if (!rendered.has(a.label)) {
        errors.push(
          `leg l (/companies/): ${key} is relabelled to ${JSON.stringify(a.label)} ` +
            `on its own page but that label is not rendered on the index — one ` +
            `company spelled two ways is the defect this seed exists to close`,
        );
      }
    }
  }

  if (relabelled.length === 0) {
    errors.push(
      "leg l: the seed relabels nothing (vacuous) — every row is a pin, so no " +
        "built page exercises the render path this leg checks",
    );
  }

  // (4) /methodology/ states the size of this problem in prose. A true
  //     sentence that has rotted is the Sprint-3 defect species — a real
  //     number carrying a claim that stopped being true — so the sentence is
  //     not read back and trusted: the page renders labelCensusSentence() of
  //     ITS census, and the built text must contain exactly the sentence of
  //     THIS leg's census (threshold, published families, seeded families —
  //     from the recompute and the seed, never from entities_top.json).
  const method = readHtml("/methodology/");
  if (!method) {
    errors.push("leg l: built /methodology/ missing");
  } else {
    for (const finding of labelCensusFindings(method.text, census)) {
      errors.push(`leg l (/methodology/): ${finding}`);
    }
  }

  if (errors.every((e) => !e.startsWith("leg l"))) {
    notes.push(
      `leg l: ${nearTies.length} of ${families.length} published families ` +
        `($${(nearTieDollars / 1e9).toFixed(1)}B) carry a label that won its ` +
        `argmax by <${(NEAR_TIE_MARGIN * 100).toFixed(0)}%; all are curated in ` +
        `entity_display_aliases.csv (${relabelled.length} relabelled, ` +
        `${aliases.size - relabelled.length} pinned), ${labelled} rendered ` +
        `label element(s) all match the seed, ${pagesChecked} company page(s) ` +
        `publish it beside their registry string; /methodology/ states the ` +
        `census exactly (${census.curated} of ${census.published} seeded, ` +
        `under ${census.thresholdPct}%) ✓`,
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// leg m — declared cadence vs. measured ingest age (ROADMAP #8)
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Cadence words the site is allowed to publish, in days.
 *
 * The gate owns this table on purpose. The PAGE states the cadence, the
 * MANIFEST states when we last fetched, and this leg is the only place the
 * two meet — if the exporter also owned the word→days map, the leg would be
 * checking one mirror against another (the exporter/gate/test triple that
 * shipped a note false on 179 of 319 pages here).
 */
const CADENCE_DAYS = {
  monthly: 31,
  quarterly: 92,
  annual: 366,
  biennial: 731,
};

/**
 * How far past one cadence period an ingest may drift before the page has to
 * say when it was actually fetched. 1.5 periods — a monthly source may run
 * 46 days behind before the claim needs a date beside it. Not zero, because
 * "monthly" never means "on the 1st"; not generous, because the corpus this
 * leg was written against was 81 days old under a monthly claim.
 */
const CADENCE_SLACK = 1.5;

/** Marker value meaning: no download-manifest record backs this cadence. */
const UNMETERED = "unmetered";

/**
 * Per-dataset freshness, read from data/manifest.jsonl — the same file the
 * ingestion CLIs append to, never from site_meta. site_meta.source_freshness
 * is what the PAGE renders from; checking the page against it would only
 * prove the exporter copied its own field forward.
 */
function manifestFreshness() {
  const p = path.join(repoRoot, "data", "manifest.jsonl");
  if (!fs.existsSync(p)) {
    return { err: `leg m: data/manifest.jsonl missing at ${p} — the ingest ages are unknowable`, byDataset: {}, records: 0 };
  }
  const byDataset = {};
  let records = 0;
  for (const line of fs.readFileSync(p, "utf8").split("\n")) {
    if (!line.trim()) continue;
    let rec;
    try {
      rec = JSON.parse(line);
    } catch {
      return { err: `leg m: data/manifest.jsonl has an unparseable line — refusing to guess ingest ages`, byDataset: {}, records: 0 };
    }
    const ds = rec.dataset;
    const at = rec.downloaded_at;
    if (!ds || !at) continue;
    records += 1;
    const t = Date.parse(at);
    if (!Number.isFinite(t)) continue;
    const cur = byDataset[ds];
    if (!cur || t > cur.t) {
      byDataset[ds] = { t, iso: at, file: rec.file_name ?? "", n: (cur?.n ?? 0) + 1 };
    } else {
      cur.n += 1;
    }
  }
  return { err: null, byDataset, records };
}

/** ISO date (YYYY-MM-DD) of a manifest timestamp. */
function isoDay(iso) {
  return String(iso).slice(0, 10);
}

function runSourceCadenceLeg(errors, notes) {
  const { err, byDataset, records } = manifestFreshness();
  if (err) {
    errors.push(err);
    return;
  }
  if (records === 0) {
    errors.push(
      "leg m: data/manifest.jsonl holds no download records — every check " +
        "below would pass vacuously",
    );
    return;
  }

  // Site-wide, not a page list. A cadence claim is a claim wherever it is
  // written, and pinning a roster of pages here would let the next one be
  // written somewhere else. Cheap: a substring test on the raw file, and
  // only files that hit get parsed.
  const hits = [];
  for (const file of walkHtml(outDir)) {
    const raw = fs.readFileSync(file, "utf8");
    if (raw.includes("cadence:") || raw.includes("cadence: ")) {
      hits.push([path.relative(outDir, file), raw]);
    }
  }
  if (hits.length === 0) {
    errors.push(
      "leg m: no built page states an update cadence at all — either the " +
        "build is broken or /methodology/ stopped describing its sources. " +
        "Both are failures; a silent pass is not available here.",
    );
    return;
  }

  let markers = 0;
  let measured = 0;
  const covered = new Set();

  for (const [rel, raw] of hits) {
    const root = parse(raw, { comment: false });
    // The RSC flight payload repeats the page's prose inside <script>. Read
    // the rendered document, the way a reader does.
    for (const el of root.querySelectorAll("script, style, noscript, template")) {
      el.remove();
    }

    const pageText = norm(root.text);
    const totalClaims = (pageText.match(/\bcadence:/gi) ?? []).length;
    if (totalClaims === 0) continue; // "cadence:" lived only in a script

    const marked = root.querySelectorAll("[data-source-freshness]");
    let coveredClaims = 0;
    for (const el of marked) {
      coveredClaims += (norm(el.text).match(/\bcadence:/gi) ?? []).length;
    }
    if (coveredClaims < totalClaims) {
      errors.push(
        `leg m (/${rel.replace(/index\.html$/, "")}): ${totalClaims - coveredClaims} of ` +
          `${totalClaims} cadence claim(s) sit outside any [data-source-freshness] ` +
          `element. A cadence the site publishes without naming the datasets it ` +
          `describes cannot be checked against when we last fetched them — which ` +
          `is how "Update cadence: monthly" sat over an 81-day-old corpus.`,
      );
    }

    for (const el of marked) {
      const text = norm(el.text);
      const cad = /\bcadence:\s*([a-z-]+)/i.exec(text);
      if (!cad) {
        errors.push(
          `leg m (/${rel.replace(/index\.html$/, "")}): a [data-source-freshness] ` +
            `element states no cadence — got ${JSON.stringify(text.slice(0, 120))}`,
        );
        continue;
      }
      markers += 1;
      const word = cad[1].toLowerCase();
      if (!(word in CADENCE_DAYS)) {
        errors.push(
          `leg m (/${rel.replace(/index\.html$/, "")}): unknown cadence "${word}" — ` +
            `this leg can only age-check ${Object.keys(CADENCE_DAYS).join(", ")}`,
        );
        continue;
      }

      const attr = norm(el.getAttribute("data-source-freshness"));
      const isoDates = [...text.matchAll(/\b(\d{4}-\d{2}-\d{2})\b/g)].map((m) => m[1]);

      if (attr === UNMETERED) {
        // No manifest record backs this line, so it may not imply one.
        if (isoDates.length > 0) {
          errors.push(
            `leg m (/${rel.replace(/index\.html$/, "")}): a cadence line marked ` +
              `"${UNMETERED}" renders an as-of date (${isoDates.join(", ")}). ` +
              `A date with nothing in data/manifest.jsonl behind it is exactly ` +
              `the literal this leg exists to stop.`,
          );
        }
        continue;
      }

      const names = attr.split(",").map((s) => s.trim()).filter(Boolean);
      if (names.length === 0) {
        errors.push(
          `leg m (/${rel.replace(/index\.html$/, "")}): [data-source-freshness] is ` +
            `empty — name the manifest dataset(s) this cadence describes, or "${UNMETERED}"`,
        );
        continue;
      }
      const unknown = names.filter((n) => !(n in byDataset));
      if (unknown.length > 0) {
        errors.push(
          `leg m (/${rel.replace(/index\.html$/, "")}): cadence line names dataset(s) ` +
            `absent from data/manifest.jsonl: ${unknown.join(", ")}`,
        );
        continue;
      }
      for (const n of names) covered.add(n);

      // The group is only as current as its STALEST member: the oldest of the
      // members' newest downloads. Taking the newest would let one fresh
      // dataset vouch for two stale ones — publish the smaller true number.
      let oldest = null;
      for (const n of names) {
        const d = byDataset[n];
        if (!oldest || d.t < oldest.t) oldest = { ...d, name: n };
      }
      const ageDays = (Date.now() - oldest.t) / 86400000;
      const windowDays = CADENCE_DAYS[word] * CADENCE_SLACK;
      const asOf = isoDay(oldest.iso);

      if (ageDays <= windowDays) {
        measured += 1;
        continue;
      }

      if (isoDates.length === 0) {
        errors.push(
          `leg m: ${names.join("+")} declares a ${word} cadence on ` +
            `/${rel.replace(/index\.html$/, "")}; the newest ingest in ` +
            `data/manifest.jsonl is ${oldest.iso} (${oldest.name}, ` +
            `${oldest.file}), ${Math.floor(ageDays)} days ago, and no built ` +
            `page states an as-of date. Either re-ingest or publish the date ` +
            `the corpus was actually fetched.`,
        );
        continue;
      }
      // SECOND TEETH: a date is not enough — it has to be THE date. A leg
      // satisfied by "some date is rendered" is the /years/ leg that once
      // passed on a column of em-dashes.
      const wrong = isoDates.filter((d) => d !== asOf);
      if (wrong.length > 0) {
        errors.push(
          `leg m: ${names.join("+")} renders as-of date(s) ${wrong.join(", ")} on ` +
            `/${rel.replace(/index\.html$/, "")}, but the newest ingest in ` +
            `data/manifest.jsonl is ${asOf} (${oldest.name}, ${oldest.file}). ` +
            `A hardcoded date rots; this one already has.`,
        );
        continue;
      }
      measured += 1;
    }
  }

  if (markers === 0) {
    errors.push(
      "leg m: not one [data-source-freshness] marker was found on any built " +
        "page carrying a cadence claim — the leg checked nothing",
    );
    return;
  }
  if (measured === 0) {
    errors.push(
      `leg m: all ${markers} cadence marker(s) are "${UNMETERED}" — no cadence ` +
        `claim on this site is checked against data/manifest.jsonl, which makes ` +
        `this leg decorative`,
    );
    return;
  }

  const uncovered = Object.keys(byDataset).filter((d) => !covered.has(d)).sort();
  notes.push(
    `leg m: ${measured} of ${markers} cadence claim(s) checked against ` +
      `data/manifest.jsonl (${records} download records, ` +
      `${Object.keys(byDataset).length} datasets) ✓` +
      (uncovered.length > 0
        ? ` — ${uncovered.length} manifest dataset(s) publish no cadence: ${uncovered.join(", ")}`
        : ""),
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// leg r — district by-year cells recomputed from the lake (ROADMAP #6)
// ═══════════════════════════════════════════════════════════════════════════

/** Sample size and floor. 12 cells over the 924 published is a ~1.3% sample;
 *  the point is a tripwire on the derivation, not coverage (gate 9 leg f checks
 *  every row for internal consistency, and assert_district_by_year_reconciles
 *  checks every row against the all-years mart in dbt). DETERMINISTIC stride,
 *  never Math.random: a failing gate must reproduce on the next run. */
const DISTRICT_YEAR_SAMPLE = 12;
const TOL_DISTRICT_YEAR = 0.01;

/** formatAmount renders a negative as "-$4.2M", and normalizeAmount's regex
 *  only accepts a leading '$'. 53 of the 924 published cells are net-negative,
 *  so without stripping and reapplying the sign the leg would report every one
 *  of them as unparseable. */
function parseSignedAmount(text) {
  const t = (text ?? "").trim();
  const neg = t.startsWith("-") || t.startsWith("−");
  const v = normalizeAmount(neg ? t.slice(1).trim() : t);
  return v === null ? null : neg ? -v : v;
}

/** Does the RENDERED figure agree with the lake, given the rounding the page
 *  actually applied? formatAmount is not uniform: |v| >= $1,000 becomes three
 *  significant digits ("$124.4M"), below that it becomes INTEGER dollars
 *  (compactFormat's `Math.round(abs)` branch). valuesAgree's granularity is the
 *  3-significant-digit one at EVERY magnitude, so a cell at $4.37 renders "$4"
 *  and would be reported as a disagreement by rounding alone. No such cell
 *  exists today — the 120 sub-$10 published cells are all exactly $0.00 — but
 *  the flake is latent, not impossible (fix round 1, Minor 6; measured
 *  read-only against data/duckdb/govbudget.duckdb 2026-09-11). */
function renderedAgreesWithLake(rendered, truthValue) {
  if (rendered == null || truthValue == null) return false;
  if (Math.abs(truthValue) < 1000) {
    // Mirror compactFormat exactly: it rounds the ABSOLUTE value and reapplies
    // the sign, which differs from Math.round(v) at a negative half-dollar.
    const pageRounded =
      truthValue < 0 ? -Math.round(-truthValue) : Math.round(truthValue);
    return Math.abs(rendered - pageRounded) <= TOL_DISTRICT_YEAR;
  }
  return valuesAgree(rendered, truthValue);
}

/** One rendered figure against one lake value. Returns the failure string, or
 *  null when it checks out. `label` distinguishes the net cell from the gross
 *  one in the message. */
function checkRenderedFigure(key, label, rendered, truthValue) {
  if (!rendered.cited) {
    return (
      `${key}${label}: the rendered row carries no cited [data-amount] — a ` +
      `by-year figure must never reach the page without its receipt`
    );
  }
  if (rendered.amount === null) {
    return `${key}${label}: the rendered figure is not a single parseable currency value`;
  }
  if (!renderedAgreesWithLake(rendered.amount, truthValue)) {
    return (
      `${key}${label}: the page renders ${rendered.amount} where the lake says ` +
      `${truthValue}`
    );
  }
  return null;
}

/**
 * The pure half of leg r — exported for
 * site/scripts/gates/__tests__/district-year-lake.test.mjs, which injects all
 * three inputs so every failure mode is provable without a build.
 *
 * @param {object} args
 * @param {{district: string, fy: number, total: number,
 *        positive?: number|null}[]} args.sample
 *        cells read from the district sidecars. `positive` is the sidecar's
 *        positive_obligation — the gross figure, rendered only on districts
 *        that have a deobligation somewhere in the table.
 * @param {Record<string, {award_count:number,total_obligation:number,
 *        positive_obligation:number}|null>} args.truth
 *        the lake recompute, keyed "{district}|{fy}".
 * @param {(district: string, fy: number) =>
 *        ({amount: number|null, cited: boolean,
 *          gross?: {amount: number|null, cited: boolean}|null}|null)}
 *        args.readRendered
 *        the built page's row for that cell: null when the page or the row is
 *        missing; amount null when the rendered text is not a single
 *        parseable currency figure; `gross` null/absent when the row renders
 *        no "Before deobligations" cell.
 * @returns {{failures: string[], checked: number, grossChecked: number}}
 */
export function checkDistrictYearSample({ sample, truth, readRendered }) {
  const failures = [];
  let checked = 0;
  let grossChecked = 0;
  for (const cell of sample) {
    const key = `${cell.district}|${cell.fy}`;
    const lake = truth[key];
    if (!lake) {
      failures.push(
        `${key}: the page publishes a figure for this cell but the lake holds ` +
          `no high-confidence-linked award transactions for it at all`,
      );
      continue;
    }
    if (Math.abs(lake.total_obligation - cell.total) > TOL_DISTRICT_YEAR) {
      failures.push(`${key}: sidecar=${cell.total} lake=${lake.total_obligation}`);
      continue;
    }
    const row = readRendered(cell.district, cell.fy);
    if (!row) {
      failures.push(
        `${key}: the sidecar publishes FY${cell.fy} but the built page ` +
          `renders no [data-district-year="${cell.fy}"] row`,
      );
      continue;
    }
    const netFailure = checkRenderedFigure(key, "", row, lake.total_obligation);
    if (netFailure) {
      failures.push(netFailure);
      continue;
    }
    checked += 1;

    // ── the gross cell, whenever it is rendered (fix round 1, Important 4) ──
    // It is a second PUBLISHED figure per row — rendered on the 90 of 153
    // districts that have a deobligation — and nothing bound it to the lake or
    // to the built page. When the column is absent there is nothing to check,
    // which is not the same as nothing to say: gate 9 leg f still requires the
    // citation id for it on every row.
    if (!row.gross) {
      // ...with one exception: the page renders the column for the WHOLE
      // district as soon as any one of its years has gross > net, so a row
      // whose own gross exceeds its own net cannot legitimately be missing it.
      if (cell.positive != null && cell.positive > cell.total + 0.005) {
        failures.push(
          `${key} (gross): the sidecar's positive_obligation ${cell.positive} ` +
            `exceeds its net ${cell.total}, so the page must render a "Before ` +
            `deobligations" cell on this row — it renders one [data-amount]`,
        );
      }
      continue;
    }
    if (cell.positive === null || cell.positive === undefined) {
      failures.push(
        `${key} (gross): the built page renders a "Before deobligations" cell ` +
          `but the sidecar carries no positive_obligation behind it`,
      );
      continue;
    }
    if (Math.abs(lake.positive_obligation - cell.positive) > TOL_DISTRICT_YEAR) {
      failures.push(
        `${key} (gross): sidecar=${cell.positive} lake=${lake.positive_obligation}`,
      );
      continue;
    }
    const grossFailure = checkRenderedFigure(
      key, " (gross)", row.gross, lake.positive_obligation,
    );
    if (grossFailure) {
      failures.push(grossFailure);
      continue;
    }
    grossChecked += 1;
  }
  return { failures, checked, grossChecked };
}

function runDistrictYearLeg(errors, notes) {
  const districtsDir = path.join(jsonDir, "districts");
  if (!fs.existsSync(districtsDir)) {
    errors.push(`leg r: ${districtsDir} not found — nothing to sample`);
    return;
  }

  const cells = [];
  for (const file of fs.readdirSync(districtsDir).sort()) {
    if (!file.endsWith(".json") || file === "index.json") continue;
    let sidecar;
    try {
      sidecar = JSON.parse(fs.readFileSync(path.join(districtsDir, file), "utf8"));
    } catch {
      continue;
    }
    for (const row of sidecar.by_year ?? []) {
      cells.push({
        district: sidecar.pop_district,
        fy: row.fiscal_year,
        total: row.total_obligation,
        positive: row.positive_obligation ?? null,
      });
    }
  }
  if (cells.length < DISTRICT_YEAR_SAMPLE) {
    errors.push(
      `leg r: only ${cells.length} by-year cell(s) published across every ` +
        `district sidecar — fewer than the ${DISTRICT_YEAR_SAMPLE}-cell sample ` +
        `this leg needs to be non-vacuous (924 on the 2026-09-10 corpus)`,
    );
    return;
  }
  const stride = Math.floor(cells.length / DISTRICT_YEAR_SAMPLE);
  const sample = [];
  for (let i = 0; i < DISTRICT_YEAR_SAMPLE; i++) sample.push(cells[i * stride]);

  const script = path.resolve(__dirname, "districtyear-recompute.py");
  const res = spawnSync("uv", ["run", "python", script], {
    cwd: repoRoot,
    encoding: "utf8",
    timeout: 300000,
    maxBuffer: 32 * 1024 * 1024,
    input: JSON.stringify({
      cells: sample.map((c) => ({ district: c.district, fy: c.fy })),
    }),
  });
  if (res.status !== 0) {
    errors.push(
      `leg r: districtyear-recompute.py exited ${res.status}: ` +
        `${(res.stderr || "").slice(0, 400)}`,
    );
    return;
  }
  let truth;
  try {
    truth = JSON.parse(res.stdout);
  } catch (e) {
    errors.push(`leg r: recompute helper returned unparseable JSON — ${e.message}`);
    return;
  }
  if (truth.__error__) {
    errors.push(`leg r: ${truth.__error__}`);
    return;
  }

  // Read the RENDERED figure off the built page's own [data-district-year]
  // row — so a page that renders a stale literal cannot pass by shipping a
  // correct sidecar.
  const readRendered = (district, fy) => {
    const pagePath = path.join(outDir, "district", district, "index.html");
    if (!fs.existsSync(pagePath)) return null;
    const root = parse(fs.readFileSync(pagePath, "utf8"), { comment: false });
    const row = root.querySelector(`[data-district-year="${fy}"]`);
    if (!row) return null;
    // Cell order is the table's column order: net, then the conditional gross
    // ("Before deobligations"), then the award count — which is not a
    // [data-amount] at all. Two amounts means the gross column is rendered.
    const amountEls = row.querySelectorAll("[data-amount]");
    const read = (el) => ({
      cited: Boolean(el && el.getAttribute("data-fact-id")),
      amount: el ? parseSignedAmount(el.text) : null,
    });
    return {
      ...read(amountEls[0]),
      gross: amountEls.length > 1 ? read(amountEls[1]) : null,
    };
  };

  const { failures, checked, grossChecked } = checkDistrictYearSample({
    sample,
    truth,
    readRendered,
  });
  if (failures.length > 0) {
    errors.push(
      `leg r: ${failures.length} of ${sample.length} sampled district-year ` +
        `cell(s) disagree with the lake or with the built page — ` +
        `${failures.slice(0, 5).join("; ")}`,
    );
  } else {
    notes.push(
      `leg r: ${checked} district-year cell(s) recomputed from the lake and ` +
        `matched their rendered, cited rows (${grossChecked} of them also ` +
        `rendering a gross "Before deobligations" cell, checked the same way) ✓`,
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// leg q — announcement LLM-alias pass scope (findings log :118-119)
// ═══════════════════════════════════════════════════════════════════════════

/** The date the announcement LLM-pass scope block first shipped. From here an
 *  EMPTY `site_meta.announcement_llm_scope` is not "no pass yet" — a pass is
 *  recorded — it is a stale export or a database restored without the table,
 *  and the page has silently dropped a disclosure. Same dated-floor idiom as
 *  leg p2's MIN_CROSSWALK_CLAIMS and leg p3's MIN_FLOW_SIDECARS: the shape
 *  that once passed vacuously fails after the date it stopped being possible. */
const ANNOUNCEMENT_SCOPE_FIRST_SHIPPED = "2026-09-19";

/** The SLOTS leg q requires the paragraph to state, in RENDER order — each
 *  figure anchored to the words around it, never a bare number.
 *
 *  WHY ANCHORED (fix round 1, item 4). The leg used to test
 *  `paragraphText.includes(figure)` for each figure: presence, anywhere, in
 *  any order. Swap the two percentage interpolations in the JSX and the page
 *  reads "15,604 have been through an LLM-assisted alias pass — 10.9% of the
 *  residue by announced value; the remaining 12,740 records (89.1% of that
 *  value) were not attempted" — both strings still present, leg green, claim
 *  false. Each slot below pins its figure to its own clause, and the leg
 *  additionally requires the slots to appear in this order, so a figure
 *  rendered in another figure's place fails twice over. Leg n's idiom, which
 *  anchors each pair to its method name.
 *
 *  The page renders every number through formatCount (toLocaleString("en-US"))
 *  and every share as a bare number + '%', so the formatting here has to match
 *  exactly. The precision pair stays a composite — "48" and "55" are
 *  substrings of plenty of other numbers, and a PAIR from another population
 *  is the one thing this half of the leg exists to catch. */
function announcementScopeSlots(scope) {
  const n = (v) => Number(v).toLocaleString("en-US");
  const pct = (v) => `${Number(v)}%`;
  const slots = [
    ["records_total", `covered all ${n(scope.records_total)} archived`],
    ["records_deterministic", `${n(scope.records_deterministic)} named a program`],
    ["records_residue", `Of the ${n(scope.records_residue)} that did not`],
    ["records_attempted", `${n(scope.records_attempted)} have been through`],
    ["pct_value_attempted",
     `${pct(scope.pct_value_attempted)} of the residue by announced value`],
  ];
  if (scope.records_remaining > 0) {
    slots.push(["records_remaining",
                `the remaining ${n(scope.records_remaining)} records`]);
    slots.push(["pct_value_remaining",
                `(${pct(scope.pct_value_remaining)} of that value)`]);
  }
  const p = scope.precision;
  if (p) {
    slots.push(["precision.drawn", `a random draw of ${n(p.drawn)} of its links`]);
    slots.push(["precision.sampled_at", `recorded ${p.sampled_at}`]);
    slots.push(["precision.pair", `${n(p.confirmed)} of the ${n(p.sampled)}`]);
  }
  return slots.map(([label, text]) => ({ label, text }));
}

/** Every NUMBER token the block licenses the paragraph to render, as the page
 *  formats it. The reverse direction of the slot sweep (leg n's idiom): a
 *  figure in the paragraph that the block does not carry is a literal someone
 *  typed, which is the species this leg was built for. */
function announcementScopeTokens(scope) {
  const n = (v) => Number(v).toLocaleString("en-US");
  const pct = (v) => `${Number(v)}%`;
  const out = [
    n(scope.records_total), n(scope.records_deterministic),
    n(scope.records_residue), n(scope.records_attempted),
    pct(scope.pct_value_attempted),
  ];
  if (scope.records_remaining > 0) {
    out.push(n(scope.records_remaining), pct(scope.pct_value_remaining));
  }
  const p = scope.precision;
  if (p) out.push(n(p.drawn), n(p.sampled), n(p.confirmed));
  return new Set(out);
}

/** Number-shaped tokens in `text`, with `dates` (ISO, which tokenize into
 *  three integers) removed first. */
function numericTokens(text, dates) {
  let scan = text;
  for (const d of dates) if (d) scan = scan.split(d).join(" ");
  return [...new Set(
    [...scan.matchAll(/\d[\d,]*(?:\.\d+)?%?/g)].map((m) => m[0]),
  )];
}

/** The shape the rendered precision sentence states a pair in. Used only to
 *  prove a pair is ABSENT when the block carries none — a paragraph claiming
 *  a measurement nothing measured. */
const ANNOUNCEMENT_PAIR_RE = /\d[\d,]* of the [\d,]+/;

/**
 * leg q: /methodology/'s announcement-scope paragraph states only figures that
 * site_meta.announcement_llm_scope carries, and states all of them.
 *
 * `records_total == null` is the "no pass recorded" test, the same predicate
 * methodology/page.tsx guards the paragraph with — the exporter writes all the
 * keys or none, so a partial block fails here loudly instead of silently
 * hiding the disclosure.
 *
 * `precision` is the one nullable field, and it is the one this leg guards
 * hardest in BOTH directions. The tier-wide study (leg n) sampled the
 * announcement tier on 2026-09-04, before this pass's most recent round
 * produced its links; the round's own sample is a different measurement of a
 * different population. So: a block with a pair must render that pair and its
 * judged date, a block without one must render the words that say so, and a
 * paragraph must never state a pair the block does not hold.
 *
 * `injected = {siteMeta, paragraphText, methodologyBuilt}` is passed only by
 * __tests__/announcement-scope.test.mjs — same contract as leg n. The gate
 * itself always passes undefined and reads the shipped site_meta.json and the
 * built /methodology/.
 */
export function runAnnouncementScopeLeg(errors, notes, injected) {
  let siteMeta;
  let paragraphText = null;
  let paragraphExists = false;
  let drawGapText = null;
  let methodologyBuilt = true;

  if (injected) {
    siteMeta = injected.siteMeta ?? {};
    paragraphText = injected.paragraphText ?? null;
    paragraphExists = injected.paragraphText != null;
    drawGapText = injected.drawGapText ?? null;
    methodologyBuilt = injected.methodologyBuilt ?? true;
  } else {
    const siteMetaPath = path.join(jsonDir, "site_meta.json");
    if (!fs.existsSync(siteMetaPath)) {
      errors.push(`leg q: ${siteMetaPath} missing — cannot recompute the announcement scope`);
      return;
    }
    try {
      siteMeta = JSON.parse(fs.readFileSync(siteMetaPath, "utf8"));
    } catch (e) {
      errors.push(`leg q: site_meta.json unparseable — ${e.message}`);
      return;
    }
    const methodRoot = readHtml("/methodology/");
    methodologyBuilt = methodRoot != null;
    const el = methodRoot?.querySelector("[data-announcement-scope]");
    paragraphExists = el != null;
    paragraphText = el ? norm(el.text) : null;
    const gap = methodRoot?.querySelector("[data-announcement-draw-gap]");
    drawGapText = gap ? norm(gap.text) : null;
  }

  const scope = siteMeta.announcement_llm_scope ?? {};
  if (scope.records_total == null) {
    // NOT a note. A pass has been recorded since the date below, so an empty
    // block is a stale export or a database restored without
    // announcement_llm_scope — and the page then drops the disclosure with
    // every gate green, which is the vacuity this leg exists to refuse.
    errors.push(
      "leg q (/methodology/): site_meta.announcement_llm_scope carries no " +
        `pass. One has been recorded since ${ANNOUNCEMENT_SCOPE_FIRST_SHIPPED}, ` +
        "so an empty block is a stale export or a database restored without " +
        "the table — re-run export-site against a warehouse whose Postgres " +
        "holds the scope row" +
        (paragraphExists
          ? ". [data-announcement-scope] renders anyway, from nothing"
          : ", and [data-announcement-scope] has silently disappeared"),
    );
    return;
  }
  if (!methodologyBuilt) {
    errors.push("leg q: /methodology/ not built — the scope leg would be vacuous");
    return;
  }
  if (!paragraphExists) {
    errors.push(
      "leg q (/methodology/): site_meta.announcement_llm_scope is populated " +
        "but [data-announcement-scope] is missing — the scope of the pass is a " +
        "disclosure, not an optional flourish",
    );
    return;
  }
  // All three halves or none: a block that carries a count but not the pair it
  // was counted from cannot be rendered honestly either way, so it fails here
  // rather than quietly dropping the sentence.
  const precision = scope.precision ?? null;
  if (precision && (precision.confirmed == null || precision.sampled == null ||
                    precision.drawn == null || !precision.sampled_at)) {
    errors.push(
      `leg q: site_meta.announcement_llm_scope.precision is partial ` +
        `(${JSON.stringify(precision)}) — the exporter writes confirmed, ` +
        `sampled, drawn and sampled_at together or writes null; re-run ` +
        `export-site`,
    );
    return;
  }
  // Checked before the figure sweep so the diagnosis names the disagreement
  // itself rather than the pair the paragraph is missing because of it.
  if (precision && /not yet been measured|not yet measured/i.test(paragraphText)) {
    errors.push(
      `leg q (/methodology/): the pass's most recent round IS measured ` +
        `(${precision.confirmed} of ${precision.sampled}, sample ` +
        `${precision.sample_id}) and the paragraph says it is not yet measured`,
    );
    return;
  }
  // ── every figure in its OWN clause, in render order ────────────────────
  const slots = announcementScopeSlots(scope);
  const missing = slots.filter((s) => !paragraphText.includes(s.text));
  if (missing.length) {
    errors.push(
      `leg q (/methodology/): [data-announcement-scope] does not state ` +
        `${missing.map((s) => `${s.label} ("${s.text}")`).join(", ")} — ` +
        `site_meta says ${slots.map((s) => s.text).join(" / ")} ` +
        `(as_of ${scope.as_of})`,
    );
    return;
  }
  let at = -1;
  for (const slot of slots) {
    const where = paragraphText.indexOf(slot.text);
    if (where <= at) {
      errors.push(
        `leg q (/methodology/): [data-announcement-scope] states ` +
          `${slot.label} ("${slot.text}") out of render order — the figures ` +
          `must appear in the order the block lists them, or two of them have ` +
          `been swapped between clauses and each still "appears" in the ` +
          `paragraph`,
      );
      return;
    }
    at = where;
  }
  // Diagnosed BEFORE the stray sweep: when the block holds no pair, a pair in
  // the paragraph is not just an unbacked number, it is another population's
  // precision — the one way this page could hand a reader the tier's figure
  // for the round's links, and the diagnosis worth printing.
  if (!precision && ANNOUNCEMENT_PAIR_RE.test(paragraphText)) {
    errors.push(
      "leg q (/methodology/): [data-announcement-scope] states a " +
        "confirmed/sampled pair while site_meta records no held-out sample " +
        "of this pass's own links — the tier-wide study measures a different " +
        "population and is never this figure",
    );
    return;
  }
  // …and NO figure the block does not carry (leg n's reverse direction).
  const stray = numericTokens(
    paragraphText, [precision?.sampled_at],
  ).filter((t) => !announcementScopeTokens(scope).has(t));
  if (stray.length) {
    errors.push(
      `leg q (/methodology/): [data-announcement-scope] states ` +
        `${stray.join(", ")}, which site_meta.announcement_llm_scope does not ` +
        `carry — every number in this paragraph is derived, so an extra one ` +
        `is a literal someone typed`,
    );
    return;
  }
  if (scope.records_remaining === 0 && /not attempted/i.test(paragraphText)) {
    errors.push(
      "leg q (/methodology/): the pass covers the whole residue but the " +
        "paragraph still says records were not attempted",
    );
    return;
  }
  if (scope.records_remaining > 0 && !/not attempted/i.test(paragraphText)) {
    errors.push(
      `leg q (/methodology/): ${scope.records_remaining.toLocaleString("en-US")} ` +
        `residue records are not attempted and the paragraph does not say so`,
    );
    return;
  }
  if (!precision) {
    // (the "states a pair anyway" direction is checked above, before the
    // stray sweep, so the pair gets its own diagnosis)
    if (!/not yet been measured|not yet measured/i.test(paragraphText)) {
      errors.push(
        "leg q (/methodology/): no held-out sample has measured the pass's " +
          "most recent round and the paragraph does not say so — silence " +
          "reads as measured",
      );
      return;
    }
    notes.push(
      `leg q: [data-announcement-scope] states all ${slots.length} derived ` +
        `figure(s), each in its own clause and in render order (as_of ` +
        `${scope.as_of}); the newest round is not measured and the paragraph ` +
        `says so ✓`,
    );
    return;
  }
  // ── the sampling FRAME of the tier-wide figure (fix round 1, item 2) ────
  //
  // /methodology/ publishes the announcement tier's precision from the
  // 2026-09-04 draw, pinned. That draw was made over the tier as it then
  // stood; every link this pass added to the tier afterwards is inside the
  // population the figure names and outside the one it measured. The count is
  // derived (announcement_llm_scope.links_new_this_pass), and the tier
  // paragraph has to carry it — the disclosure existed only in
  // docs/methodology.md, which a reader of the page never sees.
  const tierDraw =
    siteMeta.link_precision?.methods?.["announcement+lexicon"]?.sample_id ?? null;
  const newLinks =
    scope.links_new_this_pass != null && scope.links_new_this_pass > 0
      ? scope.links_new_this_pass
      : null;
  const gapRequired = newLinks != null && tierDraw != null;
  if (gapRequired && drawGapText == null) {
    errors.push(
      `leg q (/methodology/): the announcement tier's figure comes from the ` +
        `${tierDraw} draw and ${newLinks.toLocaleString("en-US")} of the ` +
        `tier's links post-date it (announcement_llm_scope.` +
        `links_new_this_pass), but no [data-announcement-draw-gap] clause ` +
        `renders — the reader is handed a precision figure for a population ` +
        `a third of which the draw could not reach`,
    );
    return;
  }
  if (!gapRequired && drawGapText != null) {
    errors.push(
      `leg q (/methodology/): [data-announcement-draw-gap] claims the tier's ` +
        `draw predates links this pass added, and site_meta carries no such ` +
        `count (links_new_this_pass ${JSON.stringify(scope.links_new_this_pass)}` +
        `, tier draw ${JSON.stringify(tierDraw)})`,
    );
    return;
  }
  if (gapRequired) {
    const want = `predates ${newLinks.toLocaleString("en-US")} of the links`;
    if (!drawGapText.includes(want)) {
      errors.push(
        `leg q (/methodology/): [data-announcement-draw-gap] does not state ` +
          `"${want}" — site_meta.announcement_llm_scope.links_new_this_pass ` +
          `is ${newLinks}`,
      );
      return;
    }
    if (!drawGapText.includes(`${tierDraw} draw`)) {
      errors.push(
        `leg q (/methodology/): [data-announcement-draw-gap] does not name ` +
          `the ${tierDraw} draw the announcement tier's figure is pinned to`,
      );
      return;
    }
    const gapStray = numericTokens(drawGapText, [tierDraw]).filter(
      (t) => t !== newLinks.toLocaleString("en-US"),
    );
    if (gapStray.length) {
      errors.push(
        `leg q (/methodology/): [data-announcement-draw-gap] states ` +
          `${gapStray.join(", ")}, which nothing in site_meta backs`,
      );
      return;
    }
  }
  notes.push(
    `leg q: [data-announcement-scope] states all ${slots.length} derived ` +
      `figure(s), each in its own clause and in render order (as_of ` +
      `${scope.as_of}), including this pass's own ` +
      `${precision.confirmed}/${precision.sampled} of ${precision.drawn} drawn ` +
      `from sample ${precision.sample_id}` +
      (gapRequired
        ? `; [data-announcement-draw-gap] states the ${newLinks} tier link(s) ` +
          `the ${tierDraw} draw predates`
        : "") +
      ` ✓`,
  );
}
