/**
 * Unit tests for gate 14 leg cm[bridge]'s crosswalk-blocker wording check
 * (coverage.mjs) — ROADMAP #109 fix round 1, R-6c-4.
 *
 * THE DEFECT THESE PIN. /coverage/'s crosswalk blocker said "high means the
 * contract and the program's own J-book pages name the same program, verified
 * by two independent adversarial reviewers", and the gate leg MANDATED the
 * word "adversarial" in it with a bare /adversarial/i. Measured 2026-09-11
 * over fct_budget_to_awards: 768 links publish at high; 60 carry a per-award
 * adjudication (all 60 at refuter_lenses_passed = 2); the other 708 are
 * `announcement+lexicon` links with no adjudication row anywhere in Postgres.
 * The adversarial step is real over 60 of 768, not over the tier — and a gate
 * that mandates the unbounded sentence is how the unbounded sentence gets
 * written back after someone fixes it.
 *
 * The check now requires the adversarial clause to be BOUND to the links that
 * carry a per-award adjudication. Nothing numeric was lowered: a wording
 * check is not a floor.
 *
 * Run via `npm test` (vitest).
 */

import { describe, it, expect } from "vitest";
import { checkCrosswalkBlockerWording } from "../coverage.mjs";

/** The blocker src/lib/coverage-map.ts ships (id "bridge"), as the leg reads
 *  it — node-html-parser text, whitespace collapsed. */
const SHIPPED =
  "Account codes are too coarse to attribute awards to program elements. An " +
  "award record carries a Treasury account and an appropriation; one " +
  "appropriation account funds dozens to hundreds of program elements, and " +
  "nothing else on the record narrows it. Most published links were " +
  "hand-adjudicated (September 2026) — /methodology/ states how many, and " +
  "which evidence paths carry no per-link adjudication at all: high means " +
  "the contract and the program's own J-book pages name the same program, " +
  "and where a per-award adjudication exists it was challenged by two " +
  "independent adversarial reviewers; medium means only that the award drew " +
  "on the same account and agency. Where evidence pinned an award to a " +
  "different organization's program, the link was removed — a guess wearing " +
  "a citation is worse than an honest absence.";

describe("leg cm[bridge] — the shipped blocker", () => {
  it("passes on the sentence /coverage/ renders today", () => {
    expect(checkCrosswalkBlockerWording(SHIPPED)).toEqual([]);
  });
});

describe("leg cm[bridge] — the unbounded adversarial claim", () => {
  it("FAILS on the pre-fix sentence the gate used to mandate", () => {
    const before = SHIPPED.replace(
      "and where a per-award adjudication exists it was challenged by two " +
        "independent adversarial reviewers",
      "verified by two independent adversarial reviewers",
    );
    expect(before).not.toBe(SHIPPED);
    const errors = checkCrosswalkBlockerWording(before);
    expect(errors.join("\n")).toMatch(/adversarial step must be BOUND/);
    expect(errors.join("\n")).toMatch(/60 of the 768/);
  });

  it("FAILS when the binding is severed by a sentence break", () => {
    const split = SHIPPED.replace(
      "and where a per-award adjudication exists it was challenged by two",
      "a per-award adjudication exists on some. They were challenged by two",
    );
    expect(checkCrosswalkBlockerWording(split).join("\n")).toMatch(
      /adversarial step must be BOUND/,
    );
  });

  it("FAILS when the adversarial step is dropped altogether", () => {
    const dropped = SHIPPED.replace(
      "and where a per-award adjudication exists it was challenged by two " +
        "independent adversarial reviewers",
      "and a per-award adjudication exists on some",
    );
    const errors = checkCrosswalkBlockerWording(dropped);
    expect(errors.join("\n")).toMatch(/must name the adversarial review step/);
    // The bounded-wording error is the ELSE branch — a blocker that names no
    // adversarial step is told to name one, not told to bind one it lacks.
    expect(errors.join("\n")).not.toMatch(/must be BOUND/);
  });
});

describe("leg cm[bridge] — the two older anchors still hold", () => {
  it("FAILS when account-code coarseness stops being the stated reason", () => {
    const vague = SHIPPED.replace("too coarse to attribute", "unhelpful for attributing")
      .replace("Account codes are", "Account identifiers are");
    expect(checkCrosswalkBlockerWording(vague).join("\n")).toMatch(
      /must name account-code coarseness/,
    );
  });

  it("FAILS when hand adjudication goes unnamed", () => {
    const silent = SHIPPED.replace("Most published links were hand-adjudicated", "Most published links were reviewed");
    expect(checkCrosswalkBlockerWording(silent).join("\n")).toMatch(
      /must name hand adjudication as the method/,
    );
  });

  it("reads an empty or missing blocker as failing every anchor", () => {
    for (const empty of ["", null, undefined]) {
      const errors = checkCrosswalkBlockerWording(empty);
      expect(errors).toHaveLength(3);
    }
  });
});
