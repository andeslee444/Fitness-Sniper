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
 *     row carries a resolving citation id, and the table is non-vacuous —
 *     >=130 districts and >=800 by-year rows must be present. "Every row adds
 *     up" is satisfied by a corpus with no rows at all, which is exactly what
 *     an export against a pre-#6 warehouse produces.
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
  runDistrictByYearLeg({
    errors,
    notes,
    sidecars: readDistrictSidecars(),
  });

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
          `${pop_district}/${prog.pe_bli}: shared_award_count=${prog.shared_award_count} but no matching [data-shared-award-count] on the built page`
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
  const mismatches = [];
  const uncited = [];

  for (const s of sidecars) {
    const byYear = Array.isArray(s.by_year) ? s.by_year : [];
    if (byYear.length === 0) continue;
    withTable += 1;
    rows += byYear.length;

    let sum = 0;
    for (const r of byYear) {
      sum += Number(r.total_obligation ?? NaN);
      if (!r.total_fact_id && uncited.length < 5) {
        uncited.push(
          `${s.pop_district} FY${r.fiscal_year} carries no total_fact_id — a ` +
            `by-year figure with no resolving citation must not be emitted at all`,
        );
      }
    }
    const headline = Number(s.total_linkable_dollars ?? NaN);
    if (!(Math.abs(sum - headline) <= TOL_BY_YEAR) && mismatches.length < 5) {
      mismatches.push(
        `${s.pop_district}: ${byYear.length} by-year rows sum to ${sum} but the ` +
          `page's headline total_linkable_dollars is ${headline} ` +
          `(diff ${sum - headline})`,
      );
    }
  }

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
  if (mismatches.length > 0) {
    errors.push(
      `leg f: ${mismatches.length} district(s) whose by-year rows do not sum to ` +
        `the headline they sit under: ${mismatches.join("; ")}`,
    );
  }
  if (uncited.length > 0) {
    errors.push(`leg f: ${uncited.length} uncited by-year figure(s): ${uncited.join("; ")}`);
  }
  if (
    mismatches.length === 0 &&
    uncited.length === 0 &&
    withTable >= MIN_BY_YEAR_DISTRICTS &&
    rows >= MIN_BY_YEAR_ROWS
  ) {
    notes.push(
      `leg f: ${withTable} district(s), ${rows} by-year row(s), every district's ` +
        `years summing to its own headline within ${TOL_BY_YEAR} ✓`,
    );
  }
}
