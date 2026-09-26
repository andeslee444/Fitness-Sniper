/**
 * Gate 21 leg (m) — the in-table medium caveat (program-skeleton.mjs
 * checkMediumCaveat / MEDIUM_CAVEAT_PHRASES), proof that it can fail.
 *
 * Decisions wave fix round 4 (review, 2026-09-26). The caveat's closing
 * sentence read "Only high rows rest on the contract naming this program
 * with a recorded review upholding it." — false: audit_link_grading
 * (dbt/models/audit) demotes an announcement link that HAS an upholding
 * record when a binding reviewer rejection or adversarial refutation of the
 * article it cites, or its own precision-sample verdict, refutes it
 * (decisions-fix3-dbt measured 10 precision_sample_refuted medium links in
 * chain order, each with a pipeline uphold). /methodology/ §4: a link "stays
 * at high only while a recorded review upholds it and no recorded rejection
 * or refutation applies". The leg bound only "high rows rest on the contract
 * naming this program", so a revert to the naming-only sentence — or to the
 * uphold-only one — passed gate-green. It now binds the whole qualifier.
 *
 * Run via `npm test` (vitest).
 */
import { describe, it, expect } from "vitest";
import { parse } from "node-html-parser";
import { checkMediumCaveat, MEDIUM_CAVEAT_PHRASES } from "../program-skeleton.mjs";

/** The caveat as program-awards.tsx renders it after fix round 4. */
const CAVEAT =
  "Rows marked medium rest on evidence weaker than a program-level match, and of more than one " +
  "kind. An account-based row, where the award drew from the same appropriation account as this " +
  "program, is an association, not evidence that this program paid for the contract. Where the " +
  "evidence is instead an FPDS acquisition-program tag or a subaward description, the program is " +
  "established but which of its budget lines paid is not. An announcement link a recorded review " +
  "did not leave standing is medium too. Only high rows rest on the contract naming this program " +
  "with a recorded review upholding it and no recorded rejection or refutation applying.";

const page = (note) =>
  parse(
    `<main><section><span title="Match confidence: medium">medium</span>` +
      (note == null ? "" : `<p data-awards-tier-note="medium">${note}</p>`) +
      `</section></main>`,
  );

const run = (note) => {
  const errors = [];
  const result = checkMediumCaveat(errors, "0601101E", page(note));
  return { errors, result };
};

describe("gate 21 leg m — the medium caveat's high-tier qualifier", () => {
  it("passes on the caveat fix round 4 ships", () => {
    const { errors, result } = run(CAVEAT);
    expect(errors).toEqual([]);
    expect(result).toEqual({ checked: true, ok: true });
  });

  it("binds the WHOLE qualifier, not its first half", () => {
    expect(MEDIUM_CAVEAT_PHRASES).toContain(
      "high rows rest on the contract naming this program with a recorded review upholding it " +
        "and no recorded rejection or refutation applying",
    );
  });

  it("FAILS on a revert to the naming-only sentence", () => {
    const naming = CAVEAT.replace(
      " with a recorded review upholding it and no recorded rejection or refutation applying.",
      ".",
    );
    expect(naming).not.toBe(CAVEAT);
    const { errors, result } = run(naming);
    expect(result.ok).toBe(false);
    expect(errors.join("\n")).toMatch(/no recorded rejection or refutation applying/);
  });

  it("FAILS on the uphold-only sentence stage 2 shipped (a medium row can carry an upholding review)", () => {
    const upholdOnly = CAVEAT.replace(" and no recorded rejection or refutation applying", "");
    expect(upholdOnly).not.toBe(CAVEAT);
    const { result } = run(upholdOnly);
    expect(result.ok).toBe(false);
  });

  it("FAILS on the pre-decisions 'evidence that names this program' sentence", () => {
    const old = CAVEAT.replace(
      "Only high rows rest on the contract naming this program with a recorded review upholding it " +
        "and no recorded rejection or refutation applying.",
      "Only high rows rest on evidence that names this program.",
    );
    expect(old).not.toBe(CAVEAT);
    expect(run(old).result.ok).toBe(false);
  });

  it("a medium row with no caveat at all fails; a page with no medium row is not checked", () => {
    expect(run(null).result).toEqual({ checked: false, ok: false });
    const errors = [];
    expect(checkMediumCaveat(errors, "x", parse("<main><p>high only</p></main>"))).toEqual({
      checked: false,
      ok: true,
    });
  });
});
