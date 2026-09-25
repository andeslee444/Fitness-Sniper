/**
 * concentration-floor.mjs — the high-only concentration floor as the
 * WAREHOUSE applies it, and the clause a withheld program page must print
 * (ROADMAP #80; integration 2026-09-25).
 *
 * WHY A GATE READS THE SQL, NOT THE SITE CONSTANT. The withheld reason is
 * site/src/lib/concentration-basis.ts CONCENTRATION_WITHHELD_REASON, built
 * from HIGH_ONLY_MIN_AWARDS / HIGH_ONLY_MIN_FAMILIES. Its unit tests read the
 * SOURCE module and pass; the PRODUCTION bundle did not say what the source
 * says. Two template literals joined by `+`, each carrying a constant
 * `${…}`, are folded by the SWC minifier Next 16.2.9 ships (reproduced with
 * next/dist/build/swc minify on 2026-09-25) into ONE string that drops
 * the first template's tail after its last expression:
 *
 *   `… at least ${3} awards across ` + `${2} contractor families …`
 *     → "… at least 32 contractor families …"
 *
 * and every withheld program page of build 42eed1e4 (472 pages) printed
 * "at least 32 contractor families". So the rendered clause is held against
 * the numbers dbt/models/marts/fct_program_concentration.sql actually
 * applies — the same literals src/__tests__/concentration-floors-bound.test.ts
 * binds the TS constants to — and against the BUILT HTML, the only place a
 * minifier defect is visible.
 *
 * Plain .mjs (gates run under plain Node).
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CONCENTRATION_SQL = path.resolve(
  __dirname, "..", "..", "..", "dbt", "models", "marts", "fct_program_concentration.sql",
);

/**
 * { awards, families } — the high-basis floor, read out of the mart. Throws
 * unless the SQL carries exactly the two copies of each literal (hhi_high and
 * top_family_high) and they agree: a floor this gate cannot read is not a
 * floor it can hold a page to.
 */
export function readConcentrationFloor(sqlText = fs.readFileSync(CONCENTRATION_SQL, "utf8")) {
  const read = (column) =>
    [...sqlText.matchAll(new RegExp(`basis = 'high' then ${column} end\\), 0\\) >= (\\d+)`, "g"))]
      .map((m) => Number(m[1]));
  const awards = read("award_count");
  const families = read("positive_family_count");
  if (awards.length !== 2 || families.length !== 2 ||
      new Set(awards).size !== 1 || new Set(families).size !== 1) {
    throw new Error(
      `fct_program_concentration.sql: expected the high-basis floor twice each ` +
        `(hhi_high, top_family_high) and in agreement — found award_count ${JSON.stringify(awards)}, ` +
        `positive_family_count ${JSON.stringify(families)}`,
    );
  }
  return { awards: awards[0], families: families[0] };
}

/**
 * The floor clause every below-floor page prints — in the Contractor
 * Concentration card ([data-concentration-withheld]) and in the WHO GETS IT
 * answer — written against whitespace-collapsed text.
 */
export function withheldFloorClause({ awards, families }) {
  return `at least ${awards} awards across ${families} contractor families holding positive obligations, with positive net linked dollars`;
}
