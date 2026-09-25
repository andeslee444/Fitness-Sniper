/**
 * gate — district_gate
 *
 * (a) 106 district pages exist (out/district/{code}/index.html)
 * (b) Each sampled district page has a disclaimer banner (coverage note)
 * (c) Program-linked dollars have [data-amount] (either cited or uncited —
 *     geography totals may be state C)
 * (d) District index (out/district/index.html) exists with state filter select
 * (e) #51 double-count fix: every district sidecar's total_linkable_dollars
 *     recomputes from the shipped fct_district_totals.parquet (via a python
 *     helper — see district-recompute.py), never from re-summing
 *     fct_district_programs; and no program row with shared_award_count > 1
 *     in its sidecar renders its dollar figure without a
 *     [data-shared-award-count] marker on the built page. Non-vacuous: fails
 *     if fewer than 100 district sidecars resolve.
 * (f) by-year truth (ROADMAP #6): every district sidecar's by_year rows sum to
 *     that sidecar's own total_linkable_dollars within a cent, every by-year
 *     row carries BOTH resolving citation ids (net and gross), and the table
 *     is non-vacuous —
 *     >=130 districts and >=800 by-year rows must be present. "Every row adds
 *     up" is satisfied by a corpus with no rows at all, which is exactly what
 *     an export against a pre-#6 warehouse produces.
 * (g) row shape (Task 27): every programs[] row in every district sidecar
 *     carries a non-empty string split_key, its program_url is exactly
 *     `/program/${split_key}/`, an account-null row's split_key is its own
 *     pe_bli, a member row's split_key starts with `${pe_bli}-`, and no two
 *     rows in one district share a split_key. Plus a floor, so an empty
 *     districts/ directory cannot pass it vacuously.
 *
 *     Noted 2026-09-19: the sidecars then under data/site/json/districts/
 *     predated Task 27 and carried no split_key at all, so this leg was
 *     expected red until a re-export. Green since chain C run 2's re-export
 *     (gate 9 PASS at e510d19d); chain C run 4 (2026-09-25) passed it on 611
 *     rows across 189 districts. Red now means the sidecars predate Task 27
 *     again — the page uses split_key as its React key and renders it as the
 *     mono code, so a build against them would ship blank code cells and
 *     duplicate keys with every other gate green. Re-run `export-site`; do
 *     not weaken the leg to fit an old payload.
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { spawnSync } from "child_process";
import { parse } from "node-html-parser";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(__dirname, "..", "..");
const repoRoot = path.resolve(siteRoot, "..");
const outDir = path.resolve(siteRoot, "out");
const jsonDir = path.resolve(siteRoot, "..", "data", "site", "json");

const EXPECTED_DISTRICTS = 106;
const SAMPLE_SIZE = 10;
const TOL_DOLLARS = 0.01;
// Re-measured 2026-09-01 (twice — the ground moved twice that day): 106
// mechanical → 41 after the hand-adjudication correction → 181 after the
// FPDS-AP expansion. The floor tracks the FINAL published corpus at ~80%
// so the leg keeps teeth: a silent collapse below 150 districts is a real
// regression, not noise. (An earlier same-day re-measure to 41 was made
// against the intermediate state — caught by a peer review before it
// could fossilize.)
const MIN_DISTRICTS_RESOLVED = 150;

/** Spawn the python recompute helper over the shipped parquet (#51 leg e). */
function recomputeDistrictTotals() {
  const res = spawnSync(
    "uv",
    ["run", "python", "site/scripts/gates/district-recompute.py"],
    { cwd: repoRoot, encoding: "utf8", timeout: 60000 }
  );
  if (res.status !== 0) {
    throw new Error(
      `district-recompute.py exited ${res.status}: ${(res.stderr || "").slice(0, 400)}`
    );
  }
  return JSON.parse(res.stdout);
}

export async function runDistrictGate() {
  const errors = [];
  const notes = [];

  const districtOutDir = path.join(outDir, "district");

  // Gracefully handle missing out/ (pre-build)
  if (!fs.existsSync(districtOutDir)) {
    notes.push("out/district/ not found — site not yet built (SKIP)");
    return { pass: true, errors, notes };
  }

  // ── (a) District page count ─────────────────────────────────────────────────
  // Count subdirectories in out/district/ (each has an index.html)
  const districtDirs = fs
    .readdirSync(districtOutDir, { withFileTypes: true })
    .filter((e) => e.isDirectory())
    .map((e) => e.name);

  // Try to get expected count from sidecar
  let expectedCount = EXPECTED_DISTRICTS;
  try {
    const districtIndex = JSON.parse(
      fs.readFileSync(path.join(jsonDir, "districts", "index.json"), "utf8")
    );
    expectedCount = districtIndex.total_districts ?? EXPECTED_DISTRICTS;
  } catch {
    // sidecar not available — use hardcoded expected
  }

  if (districtDirs.length < expectedCount) {
    errors.push(
      `district pages: found ${districtDirs.length}, expected >= ${expectedCount}`
    );
  } else {
    notes.push(`district pages: ${districtDirs.length} ✓`);
  }

  // ── (d) District index page ─────────────────────────────────────────────────
  const indexPath = path.join(districtOutDir, "index.html");
  if (!fs.existsSync(indexPath)) {
    errors.push("out/district/index.html not found");
  } else {
    const indexHtml = fs.readFileSync(indexPath, "utf8");
    const indexRoot = parse(indexHtml, { comment: false });
    // Check for a state filter <select> element
    const selects = indexRoot.querySelectorAll("select");
    const hasStateFilter = selects.some((el) => {
      const id = el.getAttribute("id") ?? "";
      const label = indexHtml;
      return id.includes("state") || label.includes("Filter by state");
    });
    if (!hasStateFilter) {
      errors.push("district index: state filter select not found");
    } else {
      notes.push("district index: state filter present ✓");
    }
  }

  // ── (b) Disclaimer banner + (c) [data-amount] — sample check ───────────────
  const sampleDirs = districtDirs
    .sort(() => 0.5 - Math.random())
    .slice(0, Math.min(SAMPLE_SIZE, districtDirs.length));

  let disclaimerOk = 0;
  let amountOk = 0;

  for (const dir of sampleDirs) {
    const pagePath = path.join(districtOutDir, dir, "index.html");
    if (!fs.existsSync(pagePath)) {
      errors.push(`district page missing: district/${dir}/index.html`);
      continue;
    }

    let pageHtml;
    try {
      pageHtml = fs.readFileSync(pagePath, "utf8");
    } catch (e) {
      errors.push(`failed to read district/${dir}/index.html: ${e.message}`);
      continue;
    }

    const pageRoot = parse(pageHtml, { comment: false });

    // (b) Disclaimer — check for the coverage note text
    const hasCoverageNote =
      pageHtml.includes("Coverage note") || pageHtml.includes("coverage note");
    if (hasCoverageNote) {
      disclaimerOk++;
    } else {
      errors.push(`district/${dir}: no disclaimer/coverage-note banner found`);
    }

    // (c) [data-amount] elements present (district has program obligation figures)
    const amountEls = pageRoot.querySelectorAll("[data-amount]");
    if (amountEls.length > 0) {
      amountOk++;
    } else {
      // Some districts may have zero programs — that's OK (no figures, no [data-amount])
      // Only fail if the page has obligation text but no data-amount wrappers.
      const hasObligationText =
        pageHtml.includes("obligation") && pageHtml.includes("linked program");
      if (hasObligationText && !pageHtml.includes("0 linked programs")) {
        errors.push(
          `district/${dir}: has obligation content but no [data-amount] elements`
        );
      } else {
        amountOk++; // zero-program district — no figures expected
      }
    }
  }

  if (sampleDirs.length > 0) {
    notes.push(
      `district sample (${sampleDirs.length}): disclaimer=${disclaimerOk}/${sampleDirs.length} ✓`
    );
    notes.push(
      `district sample (${sampleDirs.length}): [data-amount]=${amountOk}/${sampleDirs.length} ✓`
    );
  }

  // ── (e) #51 double-count fix ─────────────────────────────────────────────
  runDistrictTotalsFixLeg(districtDirs, districtOutDir, errors, notes);

  // ── (f) by-year truth (ROADMAP #6) ───────────────────────────────────────
  const sidecars = readDistrictSidecars();
  runDistrictByYearLeg({ errors, notes, sidecars });

  // ── (g) program row shape (Task 27) ──────────────────────────────────────
  runDistrictRowShapeLeg({ errors, notes, sidecars });

  return { pass: errors.length === 0, errors, notes };
}

/**
 * Leg (e) (#51): every district sidecar's total_linkable_dollars must equal
 * the fct_district_totals value recomputed from the shipped Parquet (never
 * from re-summing fct_district_programs — that is exactly the bug), and no
 * built page may render a per-program dollar figure without a
 * [data-shared-award-count] marker when the sidecar's shared_award_count for
 * that program exceeds 1. Non-vacuous: fails outright if fewer than
 * MIN_DISTRICTS_RESOLVED sidecars resolve.
 */
function runDistrictTotalsFixLeg(districtDirs, districtOutDir, errors, notes) {
  const districtsJsonDir = path.join(jsonDir, "districts");
  if (!fs.existsSync(districtsJsonDir)) {
    errors.push(`leg e: ${districtsJsonDir} not found`);
    return;
  }

  let truth;
  try {
    truth = recomputeDistrictTotals();
  } catch (e) {
    errors.push(`leg e: recompute helper failed: ${e.message}`);
    return;
  }

  const sidecarFiles = fs
    .readdirSync(districtsJsonDir)
    .filter((f) => f.endsWith(".json") && f !== "index.json");

  let resolved = 0;
  let mismatches = 0;
  let sharedAwardChecked = 0;
  let sharedAwardOk = 0;
  const mismatchDetails = [];
  const sharedAwardFailures = [];

  for (const file of sidecarFiles) {
    const pop_district = file.replace(/\.json$/, "");
    let sidecar;
    try {
      sidecar = JSON.parse(
        fs.readFileSync(path.join(districtsJsonDir, file), "utf8")
      );
    } catch {
      continue;
    }

    const truthRow = truth[pop_district];
    if (!truthRow) {
      // A district with linked program rows but no fct_district_totals row
      // would itself be a bug (same base join, coarser group-by) — but this
      // gate's job is the dollar-agreement check, not schema completeness,
      // so skip rather than double-report.
      continue;
    }
    resolved++;

    const diff = Math.abs(
      (sidecar.total_linkable_dollars ?? NaN) - truthRow.total_obligation
    );
    if (!(diff <= TOL_DOLLARS)) {
      mismatches++;
      if (mismatchDetails.length < 5) {
        mismatchDetails.push(
          `${pop_district}: sidecar=${sidecar.total_linkable_dollars} shipped-parquet=${truthRow.total_obligation}`
        );
      }
    }

    // ── shared_award_count rendering check ──────────────────────────────
    const sharedPrograms = (sidecar.programs || []).filter(
      (p) => (p.shared_award_count ?? 1) > 1
    );
    if (sharedPrograms.length === 0) continue;

    const pagePath = path.join(districtOutDir, pop_district, "index.html");
    let pageHtml = null;
    try {
      pageHtml = fs.readFileSync(pagePath, "utf8");
    } catch {
      // Page not built — counted as a failure below, not silently skipped.
    }
    const pageRoot = pageHtml ? parse(pageHtml, { comment: false }) : null;
    const markers = pageRoot
      ? pageRoot.querySelectorAll("[data-shared-award-count]")
      : [];
    const markerValues = new Set(
      markers.map((el) => el.getAttribute("data-shared-award-count"))
    );

    for (const prog of sharedPrograms) {
      sharedAwardChecked++;
      if (markerValues.has(String(prog.shared_award_count))) {
        sharedAwardOk++;
      } else if (sharedAwardFailures.length < 5) {
        sharedAwardFailures.push(
          // Task 27: the SPLIT KEY names the member — a district can hold one
          // row per member of a shared budget-line code, so "${pop_district}/0145"
          // would name two rows and send the reader to the wrong one.
          `${pop_district}/${prog.split_key ?? prog.pe_bli}: shared_award_count=${prog.shared_award_count} but no matching [data-shared-award-count] on the built page`
        );
      }
    }
  }

  if (resolved < MIN_DISTRICTS_RESOLVED) {
    errors.push(
      `leg e: only ${resolved} district sidecars resolved against the shipped parquet (<${MIN_DISTRICTS_RESOLVED}) — non-vacuity check failed`
    );
  }
  if (mismatches > 0) {
    errors.push(
      `leg e: ${mismatches} district(s) where sidecar total_linkable_dollars != shipped fct_district_totals.parquet: ${mismatchDetails.join("; ")}`
    );
  }
  if (sharedAwardFailures.length > 0 || sharedAwardChecked > sharedAwardOk) {
    const nBad = sharedAwardChecked - sharedAwardOk;
    errors.push(
      `leg e: ${nBad} shared-award program row(s) rendered without a [data-shared-award-count] marker: ${sharedAwardFailures.join("; ")}`
    );
  }
  if (mismatches === 0 && resolved >= MIN_DISTRICTS_RESOLVED) {
    notes.push(
      `leg e: ${resolved} district sidecars match fct_district_totals.parquet exactly (±${TOL_DOLLARS}) ✓`
    );
  }
  if (sharedAwardChecked > 0) {
    notes.push(
      `leg e: shared_award_count rendered on ${sharedAwardOk}/${sharedAwardChecked} sampled program rows ✓`
    );
  }
}


/** Read every districts/{code}.json sidecar. Returns [] when the dir is absent —
 *  leg f's floors then fail loudly rather than the read throwing. */
function readDistrictSidecars() {
  const dir = path.join(jsonDir, "districts");
  if (!fs.existsSync(dir)) return [];
  const out = [];
  for (const file of fs.readdirSync(dir)) {
    if (!file.endsWith(".json") || file === "index.json") continue;
    try {
      out.push(JSON.parse(fs.readFileSync(path.join(dir, file), "utf8")));
    } catch {
      // A sidecar that will not parse is gate 1's problem, not this leg's.
    }
  }
  return out;
}

// ── leg f — the by-year table adds up, and there is one (ROADMAP #6) ────────
//
// FLOORS MEASURED 2026-09-10 against the shipped warehouse: 153 districts in
// fct_district_totals (the live /district/ index links exactly 153) and 924
// rows in fct_district_totals_by_year. The floors sit at ~85% of that so a
// silent collapse is a failure and ordinary corpus movement is not.
// DO NOT LOWER THEM TO FIT A BUILD — if the corpus legitimately shrinks, the
// re-measure is a reviewed edit that says so in this comment, dated.
// RE-MEASURED 2026-09-11 (chain B) on the first export carrying the by-year
// sidecars: 153 districts and 924 rows, reproducing the 2026-09-10 figures
// exactly (67 of the 153 carry an FY2026 row). Floors unchanged at ~85%.
const MIN_BY_YEAR_DISTRICTS = 130;
const MIN_BY_YEAR_ROWS = 800;
const TOL_BY_YEAR = 0.01;

/**
 * Exported for site/scripts/gates/__tests__/district-by-year.test.mjs, which
 * injects synthetic sidecars — the leg must be provable without a build.
 *
 * @param {{errors: string[], notes: string[], sidecars: object[]}} args
 */
export function runDistrictByYearLeg({ errors, notes, sidecars }) {
  let withTable = 0;
  let rows = 0;
  // COUNT everything, cap only the DETAIL list — leg e's shape, 100 lines
  // above. Fix round 1 (Important 3): the cap used to sit inside the detection
  // condition, so a corpus with 50 broken districts reported "5 district(s)",
  // and a message that is wrong about scale is the one thing these messages
  // exist to get right.
  let mismatches = 0;
  let uncited = 0;
  const mismatchDetails = [];
  const uncitedDetails = [];
  const DETAIL_CAP = 5;

  for (const s of sidecars) {
    const byYear = Array.isArray(s.by_year) ? s.by_year : [];
    if (byYear.length === 0) continue;
    withTable += 1;
    rows += byYear.length;

    let sum = 0;
    for (const r of byYear) {
      sum += Number(r.total_obligation ?? NaN);
      // BOTH ids, not just the net one (fix round 1, Minor 9). The exporter
      // drops a by-year row unless both citations resolve, and the gross
      // figure IS rendered on every district with a deobligation — a leg that
      // only checks total_fact_id would let a half-cited row ship.
      for (const field of ["total_fact_id", "positive_fact_id"]) {
        if (r[field]) continue;
        uncited += 1;
        if (uncitedDetails.length < DETAIL_CAP) {
          uncitedDetails.push(
            `${s.pop_district} FY${r.fiscal_year} carries no ${field} — a ` +
              `by-year figure with no resolving citation must not be emitted at all`,
          );
        }
      }
    }
    const headline = Number(s.total_linkable_dollars ?? NaN);
    if (!(Math.abs(sum - headline) <= TOL_BY_YEAR)) {
      mismatches += 1;
      if (mismatchDetails.length < DETAIL_CAP) {
        mismatchDetails.push(
          `${s.pop_district}: ${byYear.length} by-year rows sum to ${sum} but the ` +
            `page's headline total_linkable_dollars is ${headline} ` +
            `(diff ${sum - headline})`,
        );
      }
    }
  }

  /** "a; b; c (+7 more)" — the count above is the true one, this is the cap. */
  const withCap = (total, details) =>
    details.join("; ") +
    (total > details.length ? ` (+${total - details.length} more)` : "");

  if (withTable < MIN_BY_YEAR_DISTRICTS) {
    errors.push(
      `leg f: only ${withTable} district(s) carry a by-year table (floor ` +
        `${MIN_BY_YEAR_DISTRICTS}, measured 2026-09-10 at 153) — the export ran ` +
        `against a warehouse without fct_district_totals_by_year, or the ` +
        `citations for it did not resolve. Fix the export; do not lower the floor.`,
    );
  }
  if (rows < MIN_BY_YEAR_ROWS) {
    errors.push(
      `leg f: ${rows} by-year row(s) (floor ${MIN_BY_YEAR_ROWS}, measured ` +
        `2026-09-10 at 924) — every district can hold one year and still have ` +
        `lost nine tenths of its table. Fix the export; do not lower the floor.`,
    );
  }
  if (mismatches > 0) {
    errors.push(
      `leg f: ${mismatches} district(s) whose by-year rows do not sum to ` +
        `the headline they sit under: ${withCap(mismatches, mismatchDetails)}`,
    );
  }
  if (uncited > 0) {
    errors.push(
      `leg f: ${uncited} uncited by-year figure(s): ` +
        `${withCap(uncited, uncitedDetails)}`,
    );
  }
  if (
    mismatches === 0 &&
    uncited === 0 &&
    withTable >= MIN_BY_YEAR_DISTRICTS &&
    rows >= MIN_BY_YEAR_ROWS
  ) {
    notes.push(
      `leg f: ${withTable} district(s), ${rows} by-year row(s), every district's ` +
        `years summing to its own headline within ${TOL_BY_YEAR} ✓`,
    );
  }
}


// ── leg g — every district program row is addressable (Task 27) ─────────────
//
// FLOORS MEASURED READ-ONLY 2026-09-19 against data/duckdb/govbudget.duckdb at
// the member grain: 608 program rows across 189 districts (the same 608 rows
// the pre-Task-27 grain held — only one district-and-code pair per member
// exists today, so the account changed addressing, not row count). The floors
// sit at ~80% so ordinary corpus movement passes and a silent collapse does
// not. DO NOT LOWER THEM TO FIT A BUILD — if the corpus legitimately shrinks,
// the re-measure is a reviewed edit that says so here, dated.
const MIN_ROW_SHAPE_DISTRICTS = 150;
const MIN_ROW_SHAPE_ROWS = 480;
const ROW_SHAPE_DETAIL_CAP = 5;

/**
 * Leg (g): the district sidecar's programs[] rows must be individually
 * addressable, because /district/{code}/ keys its table on split_key and
 * prints it as the row's mono code.
 *
 * THE RULE, decided from each row's own fields — the sidecar carries pe_bli,
 * account and split_key, so nothing here needs the warehouse:
 *
 *   1. `split_key` is a non-empty string. Before Task 27 the sidecar had no
 *      such field; an export against that payload renders an empty code cell
 *      and gives React a duplicate key, visible only as a dev-mode warning.
 *   2. `program_url` is exactly `/program/${split_key}/`. That covers both
 *      destinations without a second rule: a row that names a member
 *      addresses the member page, and a row that names none keeps split_key
 *      == pe_bli, so the same expression IS the `/program/${pe_bli}/`
 *      disambiguation stub.
 *   3. A row with a null `account` names no member, so its split_key must be
 *      its own pe_bli. (The converse is NOT a rule: an organization-split
 *      code — '20', '30', '500' — carries one account, '0300D', for BOTH of
 *      its members, so it keeps the stub with an account set. `account` is
 *      therefore not the discriminator; `split_key !== pe_bli` is.)
 *   4. A row that DOES name a member has a split_key of the form
 *      `${pe_bli}-${CODE}` — the composite slug _ProgramIdentity.slug mints.
 *   5. No two rows in one district share a split_key: one page address
 *      would carry two figures, and a reader could not tell which is that
 *      page's. (The fusion Task 27 closed is the converse — ONE bare-code
 *      row summing two members' money, latent when it landed — and dbt's
 *      assert_district_programs_single_member_high_links guards it at the
 *      mart; this leg checks addressing, not that sum.)
 *
 * Exported for site/scripts/gates/__tests__/district-row-shape.test.mjs,
 * which injects synthetic sidecars — the leg must be provable without a build.
 *
 * @param {{errors: string[], notes: string[], sidecars: object[]}} args
 */
export function runDistrictRowShapeLeg({ errors, notes, sidecars }) {
  let districts = 0;
  let rows = 0;
  let bad = 0;
  const details = [];
  const note = (msg) => {
    bad += 1;
    if (details.length < ROW_SHAPE_DETAIL_CAP) details.push(msg);
  };

  for (const s of sidecars) {
    const programs = Array.isArray(s.programs) ? s.programs : [];
    if (programs.length === 0) continue;
    districts += 1;
    const seen = new Map();
    for (const p of programs) {
      rows += 1;
      const where = `${s.pop_district}/${p.pe_bli}`;
      if (typeof p.split_key !== "string" || p.split_key === "") {
        note(
          `${where}: no split_key — this sidecar predates Task 27; re-run ` +
            `export-site before building (the page renders split_key as the ` +
            `row's code and keys the table on it)`,
        );
        continue;
      }
      const expected = `/program/${p.split_key}/`;
      if (p.program_url !== expected) {
        note(
          `${where}: program_url ${JSON.stringify(p.program_url)} does not ` +
            `address its own split_key (${expected})`,
        );
      }
      if (p.account == null && p.split_key !== p.pe_bli) {
        note(
          `${where}: account is null — the row names no member — but its ` +
            `split_key ${JSON.stringify(p.split_key)} is not the bare code`,
        );
      }
      if (p.split_key !== p.pe_bli && !p.split_key.startsWith(`${p.pe_bli}-`)) {
        note(
          `${where}: split_key ${JSON.stringify(p.split_key)} is neither the ` +
            `bare code nor a "${p.pe_bli}-CODE" member slug`,
        );
      }
      const prior = seen.get(p.split_key);
      if (prior !== undefined) {
        note(
          `${s.pop_district}: two program rows share split_key ` +
            `${JSON.stringify(p.split_key)} (${prior} and ${p.pe_bli}) — one ` +
            `address, two figures`,
        );
      } else {
        seen.set(p.split_key, p.pe_bli);
      }
    }
  }

  if (bad > 0) {
    errors.push(
      `leg g: ${bad} district program row problem(s): ` +
        details.join("; ") +
        (bad > details.length ? ` (+${bad - details.length} more)` : ""),
    );
  }
  if (districts < MIN_ROW_SHAPE_DISTRICTS) {
    errors.push(
      `leg g: only ${districts} district(s) carry a program row (floor ` +
        `${MIN_ROW_SHAPE_DISTRICTS}, measured 2026-09-19 at 189) — every row ` +
        `can be well formed and the corpus still have collapsed. Fix the ` +
        `export; do not lower the floor.`,
    );
  }
  if (rows < MIN_ROW_SHAPE_ROWS) {
    errors.push(
      `leg g: ${rows} district program row(s) (floor ${MIN_ROW_SHAPE_ROWS}, ` +
        `measured 2026-09-19 at 608). Fix the export; do not lower the floor.`,
    );
  }
  if (
    bad === 0 &&
    districts >= MIN_ROW_SHAPE_DISTRICTS &&
    rows >= MIN_ROW_SHAPE_ROWS
  ) {
    notes.push(
      `leg g: ${rows} program row(s) across ${districts} district(s), each ` +
        `with its own split_key and a program_url that addresses it ✓`,
    );
  }
}
