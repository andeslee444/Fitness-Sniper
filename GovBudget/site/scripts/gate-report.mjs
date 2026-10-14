/**
 * gate-report.mjs — the lines `npm run verify` (scripts/verify.mjs) prints for
 * one gate result {pass, notes, errors}.
 *
 * The summary line carries the first three notes. A WARNING note is printed
 * wherever it sits in the list: gate 1's page-weight warning lands well past
 * position 3, so the near-ceiling alarm added 2026-08-14 was generated on
 * every run and shown on none of them (/coverage/ reached NINE bytes of
 * headroom that way). ROADMAP #201: every other note was still invisible —
 * gate 21 leg p's among them — so the summary now says how many it left out,
 * and VERIFY_NOTES=all prints each one on its own line.
 */

/** Notes that must surface regardless of their position in the list. */
export const WARNING_NOTE_RE = /at or above|near-ceiling|\bWARN\b/i;
const SUMMARY_NOTES = 3;

export function gateReportLines(n, name, result, { allNotes = process.env.VERIFY_NOTES === "all" } = {}) {
  const status = result.pass ? "PASS" : "FAIL";
  const more = result.notes.length - SUMMARY_NOTES;
  const details =
    result.notes.slice(0, SUMMARY_NOTES).join("; ") +
    (more > 0 ? `; +${more} more note${more === 1 ? "" : "s"}${allNotes ? "" : " (VERIFY_NOTES=all prints them)"}` : "") +
    (result.errors.length > 0 ? `; ERRORS: ${result.errors.slice(0, 5).join(" | ")}` : "");
  const lines = [`gate ${n} ${name}: ${details} → ${status}`];
  for (const note of result.notes.slice(SUMMARY_NOTES)) {
    if (WARNING_NOTE_RE.test(note)) lines.push(`  ⚠ ${note}`);
    else if (allNotes) lines.push(`  · ${note}`);
  }
  for (const e of result.errors) lines.push(`  ✗ ${e}`);
  return lines;
}
