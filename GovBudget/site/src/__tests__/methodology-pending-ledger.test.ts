/**
 * /methodology/'s citation-tier paragraph names the pending ledger's one
 * dataset (families piece 1, Task 19; the owner's decision of Step 19).
 * p1_era_line_map ships on the uncited ledger (spec §4.4: its rows are
 * decisions, not money), so its /data/ row shows "tier pending" and "the
 * pending ledger is empty" stops being true when it ships. The clause is
 * replaced at its exact rendered length: /methodology/ sits near its gate-1
 * ceiling.
 */
import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";

const PAGE = path.resolve(__dirname, "..", "app", "methodology", "page.tsx");
const OLD = "every published dataset carries a citation tier (the pending ledger is empty)";
const NEW = "only p1_era_line_map is on the pending ledger, as it holds no amounts to cite";

/** The citation-tier definition as rendered: tags drop, whitespace collapses. */
function rendered(): string {
  const src = fs.readFileSync(PAGE, "utf8");
  const a = src.indexOf("<strong>Citation tier pending</strong>");
  expect(a, "citation-tier definition not found").toBeGreaterThan(-1);
  const b = src.indexOf("</p>", a);
  return src.slice(a, b).replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
}

describe("/methodology/ pending-ledger clause", () => {
  it("names p1_era_line_map as the pending ledger's only dataset", () => {
    expect(rendered()).toContain(`As of this build ${NEW}; the state remains defined`);
  });

  it("no longer says the ledger is empty", () => {
    expect(rendered()).not.toContain("the pending ledger is empty");
  });

  it("keeps the clause's rendered length", () => {
    expect(Buffer.byteLength(NEW)).toBe(Buffer.byteLength(OLD));
    expect(Buffer.byteLength(NEW)).toBe(77);
  });
});

/**
 * Task 19 fix round 1: the FAQ answer in /methodology/'s JSON-LD said the
 * pending tier is "reserved for datasets shipped before their citations
 * (currently none)", false beside the clause above once p1_era_line_map
 * ships. It names the dataset now, shorter than the answer it replaced (the
 * page sits near its gate-1 ceiling). Follow-ups T7 (ROADMAP #206, owner
 * Q16) gave it the shared definition below: 98 bytes against 102.
 */
describe("/methodology/ FAQ JSON-LD: the pending tier", () => {
  const src = fs.readFileSync(PAGE, "utf8");
  const OLD_FAQ = "Citation tier pending (⁂) — reserved for datasets shipped before their citations (currently none).";
  const NEW_FAQ = "Citation tier pending (⁂) — a dataset without row-level citations (currently p1_era_line_map).";

  it("names p1_era_line_map and no longer says none", () => {
    expect(src).toContain(NEW_FAQ);
    expect(src).not.toContain("(currently none)");
  });

  it("is no longer than the answer it replaced", () => {
    expect(Buffer.byteLength(NEW_FAQ)).toBeLessThanOrEqual(Buffer.byteLength(OLD_FAQ));
  });
});

/**
 * ROADMAP #206 T7 (families piece-1 follow-ups, design §5.3; owner sign-off
 * Q16, 2026-10-04). "Citation tier pending" had three definitions: the
 * /methodology/ body ("row-level citation linkage is not yet complete"), its
 * FAQ JSON-LD ("reserved for datasets without citations") and /about/ ("row-
 * level linkage is a work in progress"). None fits p1_era_line_map, whose
 * rows are decisions and will never carry amounts. There is one definition
 * now, and the claims around it say "dollar figure", which is what gate 2
 * (render-static.mjs) enforces, instead of "number".
 */
describe("one definition of citation tier pending (T7)", () => {
  const ABOUT = path.resolve(__dirname, "..", "app", "about", "page.tsx");
  const flat = (file: string) => fs.readFileSync(file, "utf8").replace(/\s+/g, " ");
  const SHARED = "a dataset without row-level citations";

  it("the /methodology/ body, its FAQ and /about/ share one phrase", () => {
    expect(rendered()).toContain(`(⁂): a figure from ${SHARED}.`);
    expect(flat(PAGE)).toContain(`Citation tier pending (⁂) — ${SHARED} (currently p1_era_line_map).`);
    expect(flat(ABOUT)).toContain(`citation tier pending (${SHARED}).`);
  });

  it("no older definition or unnarrowed claim is left", () => {
    for (const file of [PAGE, ABOUT]) {
      const text = flat(file);
      for (const stale of ["work in progress", "not yet complete", "reserved for datasets",
        "Every rendered number", "No number is displayed", "Every rendered figure"]) {
        expect(text.includes(stale), `${path.basename(path.dirname(file))} still says "${stale}"`).toBe(false);
      }
    }
  });

  it("narrows each claim to dollar figures", () => {
    const page = flat(PAGE);
    expect(page).toContain("Every rendered dollar figure is in one of three states.");
    expect(page).toContain("Every rendered dollar figure carries a citation state; a cited one links to the exact source document, page, or API endpoint.");
    expect(page).toContain("Dollar figures in one of three states:");
    const about = flat(ABOUT);
    expect(about).toContain("Every rendered dollar figure is in one of three citation states:");
    expect(about).toContain("No dollar figure is displayed without disclosing which state it is in.");
  });

  it("keeps the em-dash-free clause the copy gate's allowlist entry no longer covers", () => {
    expect(rendered()).toContain("the state remains defined, and gate-enforced, for future datasets");
  });
});
