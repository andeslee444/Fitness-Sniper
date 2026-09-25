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
 * Task 26 (2026-09-25): the error message typed that 2026-09-11 census ("60
 * of the 768 … grades 708 links") and went stale when the tier moved (chain C
 * run 4: 60 of 1,133). It now prints the build's own site_meta census
 * (bridgeHighCensus), and prints no count when the build carries none.
 *
 * Run via `npm test` (vitest).
 */

import { describe, it, expect } from "vitest";
import { bridgeHighCensus, checkCrosswalkBlockerWording } from "../coverage.mjs";

/** The bridge row's blocker cell as leg cm reads it from chain C run 4's
 *  build (out/coverage/index.html, git_head 71d3e053, built 2026-09-25):
 *  node-html-parser text, whitespace collapsed — so it opens with the
 *  mobile-only "In the way" label, a separate block span the leg's .text
 *  runs into the sentence. A later rebuild may render other words; the live
 *  leg reads whatever the page renders, and this fixture stays the dated
 *  copy the unit cases mutate. */
const SHIPPED =
  "In the wayAccount codes are too coarse to attribute awards to program elements. An " +
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
  "a citation is worse than an honest absence. File C, the last untested " +
  "official path, was examined and ruled out in September 2026.";

/** site_meta.link_adjudication as chain C run 4 exported it (2026-09-25),
 *  cut to the fields the census reads. */
const RUN4_META = {
  link_adjudication: {
    measured_on: "2026-09-25",
    published: 12917,
    adjudicated: 9588,
    high: { published_high: 1133, adjudicated_high: 60, two_lens_high: 60 },
  },
};

describe("leg cm[bridge] — the shipped blocker", () => {
  it("passes on the blocker cell chain C run 4's build rendered (2026-09-25)", () => {
    expect(checkCrosswalkBlockerWording(SHIPPED, bridgeHighCensus(RUN4_META))).toEqual([]);
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
    const errors = checkCrosswalkBlockerWording(before, bridgeHighCensus(RUN4_META));
    expect(errors.join("\n")).toMatch(/adversarial step must be BOUND/);
    // The census is the build's, not a typed one: run 4's 60 of 1,133 leaves
    // 1,073 links graded by a review they never had.
    expect(errors.join("\n")).toMatch(
      /60 of the 1,133 links published at high carry one \(site_meta\.link_adjudication\.high, measured 2026-09-25\)/,
    );
    expect(errors.join("\n")).toMatch(/grades 1,073 links by a review they never had/);
    expect(errors.join("\n")).not.toMatch(/768|708/);
  });

  it("prints the census it is given — the 2026-09-11 one reproduces the old message's figures", () => {
    const before = SHIPPED.replace(
      "and where a per-award adjudication exists it was challenged by two " +
        "independent adversarial reviewers",
      "verified by two independent adversarial reviewers",
    );
    const sept11 = { published: 768, adjudicated: 60, measuredOn: "2026-09-11" };
    const msg = checkCrosswalkBlockerWording(before, sept11).join("\n");
    expect(msg).toMatch(/60 of the 768 links published at high carry one/);
    expect(msg).toMatch(/grades 708 links/);
  });

  it("with no census it still FAILS, and prints no count at all", () => {
    const before = SHIPPED.replace(
      "and where a per-award adjudication exists it was challenged by two " +
        "independent adversarial reviewers",
      "verified by two independent adversarial reviewers",
    );
    const msg = checkCrosswalkBlockerWording(before).join("\n");
    expect(msg).toMatch(/adversarial step must be BOUND/);
    expect(msg).toMatch(/carries no link_adjudication\.high census, so no count is printed/);
    expect(msg).not.toMatch(/\d/);
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

describe("bridgeHighCensus — reads the build's census or nothing", () => {
  it("reads run 4's block", () => {
    expect(bridgeHighCensus(RUN4_META)).toEqual({
      published: 1133,
      adjudicated: 60,
      measuredOn: "2026-09-25",
    });
  });

  it("an undated block keeps its counts and says it is undated", () => {
    const undated = { link_adjudication: { high: { published_high: 10, adjudicated_high: 2 } } };
    expect(bridgeHighCensus(undated)).toEqual({ published: 10, adjudicated: 2, measuredOn: null });
    const before = SHIPPED.replace("where a per-award adjudication exists it was", "it was");
    expect(checkCrosswalkBlockerWording(before, bridgeHighCensus(undated)).join("\n")).toMatch(
      /2 of the 10 links published at high carry one \(site_meta\.link_adjudication\.high, undated\)/,
    );
  });

  it("a missing or malformed block prints no figure rather than a wrong one", () => {
    for (const meta of [
      null,
      {},
      { link_adjudication: {} },
      { link_adjudication: { high: { published_high: "1133", adjudicated_high: 60 } } },
      { link_adjudication: { high: { published_high: 1133 } } },
      { link_adjudication: { high: { published_high: 50, adjudicated_high: 60 } } },
      { link_adjudication: { high: { published_high: 1133, adjudicated_high: -1 } } },
      { link_adjudication: { high: { published_high: 1133.5, adjudicated_high: 60 } } },
    ]) {
      expect(bridgeHighCensus(meta)).toBeNull();
    }
  });
});
