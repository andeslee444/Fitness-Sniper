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

/** The bridge row's blocker cell as leg cm will read it once the Task 26
 *  fix wave is built: node-html-parser text, whitespace collapsed — so it
 *  opens with the mobile-only "In the way" label, a separate block span the
 *  leg's .text runs into the sentence. The words are coverage-map.ts's
 *  blocker string at db7ea6b8 (2026-09-25). Chain C run 4's build
 *  (out/coverage/index.html, git_head 71d3e053) rendered the same cell
 *  character for character except the medium clause, which then read
 *  "medium means only that the award drew on the same account and agency".
 *  The live leg reads whatever the page renders; this fixture is the dated
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
  "independent adversarial reviewers; medium means the evidence stops short " +
  "of proving this line paid. Where evidence pinned an award to a " +
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

/** The bridge row's blocker cell as coverage-map.ts renders it after the
 *  decisions wave's fix round 4 (R-DEC-COVERAGE), on run 4's census: the
 *  hand-adjudicated share is a figure read from
 *  site_meta.link_adjudication.high, not the word "Most". */
const SHIPPED_R4 =
  "In the wayAccount codes are too coarse to attribute awards to program elements. An " +
  "award record carries a Treasury account and an appropriation; one " +
  "appropriation account funds dozens to hundreds of program elements, and " +
  "nothing else on the record narrows it. High means the contract and the " +
  "program's own J-book pages name the same program; 60 of the 1,133 links " +
  "published at high were hand-adjudicated, and where a per-award " +
  "adjudication exists it was challenged by two independent adversarial " +
  "reviewers. Medium means the evidence stops short of proving this line " +
  "paid. /methodology/ states which evidence paths carry no per-link " +
  "adjudication at all. Where evidence pinned an award to a different " +
  "organization's program, the link was removed — a guess wearing a " +
  "citation is worse than an honest absence. File C, the last untested " +
  "official path, was examined and ruled out in September 2026.";

/** The same cell when the build's site_meta carries no high census: no
 *  figure, no quantifier, and the count left to /methodology/. */
const SHIPPED_R4_NO_CENSUS =
  "In the wayAccount codes are too coarse to attribute awards to program elements. An " +
  "award record carries a Treasury account and an appropriation; one " +
  "appropriation account funds dozens to hundreds of program elements, and " +
  "nothing else on the record narrows it. High means the contract and the " +
  "program's own J-book pages name the same program, and where a per-award " +
  "adjudication exists it was challenged by two independent adversarial " +
  "reviewers. Medium means the evidence stops short of proving this line " +
  "paid. /methodology/ states how many links were hand-adjudicated, and " +
  "which evidence paths carry no per-link adjudication at all. Where " +
  "evidence pinned an award to a different organization's program, the link " +
  "was removed — a guess wearing a citation is worse than an honest absence. " +
  "File C, the last untested official path, was examined and ruled out in " +
  "September 2026.";

describe("leg cm[bridge] — the shipped blocker", () => {
  it("passes on the blocker cell fix round 4 ships, with run 4's census stated from site_meta", () => {
    expect(checkCrosswalkBlockerWording(SHIPPED_R4, bridgeHighCensus(RUN4_META))).toEqual([]);
  });

  it("passes on the no-census cell when the build carries no census", () => {
    expect(checkCrosswalkBlockerWording(SHIPPED_R4_NO_CENSUS)).toEqual([]);
    expect(checkCrosswalkBlockerWording(SHIPPED_R4_NO_CENSUS, null)).toEqual([]);
  });
});

/**
 * R-DEC-COVERAGE (controller, 2026-09-26). The Task 26 blocker said "Most
 * published links were hand-adjudicated (September 2026)". Measured over the
 * chain-order scratch mart (fix3dbt), 603 of the 3,767 links published carry
 * an adjudication (16%) once #107(b) withdraws the account / sub-agency
 * tier; the gate only required /hand-adjudicated/, so chain G would have
 * shipped a false majority. The blocker now states the share as a figure
 * read from site_meta, and a majority word fails unless that share is above
 * one half.
 */
describe("leg cm[bridge] — the hand-adjudicated share is a site_meta figure (R-DEC-COVERAGE)", () => {
  const census = () => bridgeHighCensus(RUN4_META);

  it("FAILS on the Task 26 blocker's 'Most published links' at run 4's 60 of 1,133", () => {
    const errors = checkCrosswalkBlockerWording(SHIPPED, census());
    const msg = errors.join("\n");
    expect(msg).toMatch(/says "Most"/);
    expect(msg).toMatch(/60 of the 1,133/);
    // …and it states no figure, so it also fails for leaving the share out.
    expect(msg).toMatch(/states no hand-adjudicated share/);
  });

  it("FAILS on every majority word while the share is not above one half", () => {
    for (const [from, to] of [
      ["60 of the 1,133 links published at high were hand-adjudicated", "the majority of the 60 of the 1,133 links published at high were hand-adjudicated"],
      ["High means the contract", "Almost all links were hand-adjudicated. High means the contract"],
      ["High means the contract", "Nearly all were hand-adjudicated. High means the contract"],
      ["High means the contract", "Most were hand-adjudicated. High means the contract"],
    ]) {
      const text = SHIPPED_R4.replace(from, to);
      expect(text, to).not.toBe(SHIPPED_R4);
      expect(checkCrosswalkBlockerWording(text, census()).join("\n"), to).toMatch(
        /majority word|says "(?:Most|majority|Almost all|Nearly all)"/i,
      );
    }
  });

  it("a majority word passes only when the share is above one half", () => {
    const text = SHIPPED_R4.replace("60 of the 1,133", "Most links published at high were hand-adjudicated: 600 of the 1,133");
    const big = { published: 1133, adjudicated: 600, twoLens: 600, measuredOn: "2026-09-25" };
    expect(checkCrosswalkBlockerWording(text, big)).toEqual([]);
    const half = { published: 1200, adjudicated: 600, twoLens: 600, measuredOn: "2026-09-25" };
    const atHalf = text.replace("600 of the 1,133", "600 of the 1,200");
    expect(checkCrosswalkBlockerWording(atHalf, half).join("\n")).toMatch(/says "Most"/);
  });

  it("'the most recent' is a superlative, not a quantifier", () => {
    const text = SHIPPED_R4.replace(
      "were hand-adjudicated,",
      "were hand-adjudicated (the most recent adjudication is dated),",
    );
    expect(checkCrosswalkBlockerWording(text, census())).toEqual([]);
  });

  it("FAILS when the census is in site_meta and the blocker states no figure", () => {
    const errors = checkCrosswalkBlockerWording(SHIPPED_R4_NO_CENSUS, census());
    expect(errors.join("\n")).toMatch(/states no hand-adjudicated share/);
    expect(errors.join("\n")).toMatch(/60 of the 1,133 links published at high/);
  });

  it("FAILS when a figure is typed instead of read from site_meta", () => {
    const errors = checkCrosswalkBlockerWording(SHIPPED_R4.replace("60 of the", "61 of the"), census());
    expect(errors.join("\n")).toMatch(/"61"/);
  });

  it("FAILS when the two figures trade places", () => {
    const errors = checkCrosswalkBlockerWording(
      SHIPPED_R4.replace("60 of the 1,133", "1,133 of the 60"),
      census(),
    );
    expect(errors.join("\n")).toMatch(/in the order 1,133, 60/);
  });

  it("FAILS when the tier is dropped: the census counts links published at HIGH, not all published links", () => {
    for (const bad of [
      SHIPPED_R4.replace("60 of the 1,133 links published at high", "60 of the 1,133 published links"),
      SHIPPED_R4.replace("links published at high were", "links published at medium were"),
    ]) {
      expect(bad).not.toBe(SHIPPED_R4);
      expect(checkCrosswalkBlockerWording(bad, census()).join("\n")).toMatch(/published at high/);
    }
  });

  it("FAILS on a stray number beside the census", () => {
    const errors = checkCrosswalkBlockerWording(
      SHIPPED_R4.replace("were hand-adjudicated,", "were hand-adjudicated (76%),"),
      census(),
    );
    expect(errors.join("\n")).toMatch(/"76"/);
  });

  it("with no census in site_meta, a stated figure or a majority word FAILS", () => {
    expect(checkCrosswalkBlockerWording(SHIPPED_R4).join("\n")).toMatch(/carries no link_adjudication\.high census/);
    const most = SHIPPED_R4_NO_CENSUS.replace("High means the contract", "Most published links were hand-adjudicated. High means the contract");
    const msg = checkCrosswalkBlockerWording(most).join("\n");
    expect(msg).toMatch(/says "Most"/);
    expect(msg).not.toMatch(/\d/);
  });

  it("the adversarial universal FAILS when not every adjudicated high link had two lenses", () => {
    const partial = { published: 1133, adjudicated: 60, twoLens: 50, measuredOn: "2026-09-25" };
    const errors = checkCrosswalkBlockerWording(SHIPPED_R4, partial);
    expect(errors.join("\n")).toMatch(/two_lens_high/);
    const bounded = SHIPPED_R4.replace(
      "and where a per-award adjudication exists it was challenged by two independent adversarial reviewers",
      "and 50 of those per-award adjudications were challenged by two independent adversarial reviewers",
    );
    expect(bounded).not.toBe(SHIPPED_R4);
    expect(checkCrosswalkBlockerWording(bounded, partial)).toEqual([]);
    // …and the bounded form must carry the two-lens figure, not another.
    expect(
      checkCrosswalkBlockerWording(bounded.replace("50 of those", "60 of those"), partial).join("\n"),
    ).toMatch(/in the order/);
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
      twoLens: 60,
      measuredOn: "2026-09-25",
    });
  });

  it("an undated block keeps its counts and says it is undated", () => {
    const undated = { link_adjudication: { high: { published_high: 10, adjudicated_high: 2 } } };
    expect(bridgeHighCensus(undated)).toEqual({ published: 10, adjudicated: 2, twoLens: null, measuredOn: null });
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

/**
 * R-DEC-COVERAGE-b (controller, fix-round-5 rulings, 2026-09-26). The fix-5
 * review imported checkCrosswalkBlockerWording with SHIPPED_R4 and run 4's
 * census (1,133 published / 60 adjudicated / 60 two-lens) and got ZERO
 * errors for each of:
 *   (a) "60 of the 1,133 links published at high or medium were hand-adjudicated"
 *   (b) "60 of the 1,133 links published at high and medium were hand-adjudicated"
 *   (c) "60 of the 1,133 links published at high were not hand-adjudicated"
 * because the tier check stopped at /links published at high\b/ and nothing
 * bound the predicate. The binding now holds the EXACT High census clause —
 * "N of the M links published at high were hand-adjudicated": the tier word
 * 'high' alone, no 'or' / 'and' widening, the predicate as stated, and no
 * negation in the sentence that carries it.
 */
describe("leg cm[bridge] — the exact High census clause (R-DEC-COVERAGE-b)", () => {
  const census = () => bridgeHighCensus(RUN4_META);
  const CLAUSE = "60 of the 1,133 links published at high were hand-adjudicated";

  it("the shipped clause is exactly the census clause (fixture sanity)", () => {
    expect(SHIPPED_R4).toContain(CLAUSE);
    expect(checkCrosswalkBlockerWording(SHIPPED_R4, census())).toEqual([]);
  });

  it("RED at fix 5: the reviewer's three rewrites each FAIL", () => {
    for (const bad of [
      "60 of the 1,133 links published at high or medium were hand-adjudicated",
      "60 of the 1,133 links published at high and medium were hand-adjudicated",
      "60 of the 1,133 links published at high were not hand-adjudicated",
    ]) {
      const text = SHIPPED_R4.replace(CLAUSE, bad);
      expect(text, bad).not.toBe(SHIPPED_R4);
      const msg = checkCrosswalkBlockerWording(text, census()).join("\n");
      expect(msg, bad).toMatch(/census clause/);
      expect(msg, bad).toMatch(/60 of the 1,133 links published at high were hand-adjudicated/);
    }
  });

  it("FAILS on any other widening of the tier word", () => {
    for (const bad of [
      "60 of the 1,133 links published at high or above were hand-adjudicated",
      "60 of the 1,133 links published at high, or medium, were hand-adjudicated",
      "60 of the 1,133 links published at high and at medium were hand-adjudicated",
      "60 of the 1,133 links published at high/medium were hand-adjudicated",
      "60 of the 1,133 links published at high-or-medium were hand-adjudicated",
      "60 of the 1,133 links published at high or better were hand-adjudicated",
    ]) {
      const text = SHIPPED_R4.replace(CLAUSE, bad);
      expect(text, bad).not.toBe(SHIPPED_R4);
      expect(checkCrosswalkBlockerWording(text, census()).join("\n"), bad).toMatch(/census clause/);
    }
  });

  it("FAILS on any negation of the clause, in the predicate or anywhere in its sentence", () => {
    for (const [from, to] of [
      [CLAUSE, "60 of the 1,133 links published at high were never hand-adjudicated"],
      [CLAUSE, "60 of the 1,133 links published at high weren't hand-adjudicated"],
      [CLAUSE, "60 of the 1,133 links published at high were not yet hand-adjudicated"],
      [CLAUSE, "it is not the case that 60 of the 1,133 links published at high were hand-adjudicated"],
      [CLAUSE, "none but 60 of the 1,133 links published at high were hand-adjudicated"],
      [`${CLAUSE},`, `${CLAUSE} — or so no reviewer found,`],
    ]) {
      const text = SHIPPED_R4.replace(from, to);
      expect(text, to).not.toBe(SHIPPED_R4);
      expect(checkCrosswalkBlockerWording(text, census()).join("\n"), to).toMatch(/census clause|negat/);
    }
  });

  it("FAILS when the predicate is widened or swapped", () => {
    for (const bad of [
      "60 of the 1,133 links published at high were hand-adjudicated or reviewed",
      "60 of the 1,133 links published at high were reviewed",
      "60 of the 1,133 links published at high were partly hand-adjudicated",
      "60 of the 1,133 links published at high are checked and hand-adjudicated",
    ]) {
      const text = SHIPPED_R4.replace(CLAUSE, bad);
      expect(text, bad).not.toBe(SHIPPED_R4);
      expect(checkCrosswalkBlockerWording(text, census()).join("\n"), bad).toMatch(/census clause/);
    }
  });

  it("FAILS when the figure is hedged into a bound", () => {
    for (const bad of [
      `at least ${CLAUSE}`,
      `more than ${CLAUSE}`,
      `nearly ${CLAUSE}`,
      `up to ${CLAUSE}`,
    ]) {
      const text = SHIPPED_R4.replace(CLAUSE, bad);
      expect(checkCrosswalkBlockerWording(text, census()).join("\n"), bad).toMatch(/census clause/);
    }
  });

  it("the bounded two-lens form keeps passing with the exact clause", () => {
    const partial = { published: 1133, adjudicated: 60, twoLens: 50, measuredOn: "2026-09-25" };
    const bounded = SHIPPED_R4.replace(
      "and where a per-award adjudication exists it was challenged by two independent adversarial reviewers",
      "and 50 of those per-award adjudications were challenged by two independent adversarial reviewers",
    );
    expect(checkCrosswalkBlockerWording(bounded, partial)).toEqual([]);
  });
});

/**
 * R-DEC-COVERAGE-b, the majority ban. The review probed four sentences beside
 * the correct census sentence (60 of 1,133, 5.3%) and each returned 0 errors:
 * "mostly", "For the most part" (the lookbehind that spares "the most recent"
 * also spared it), "More than half" and "largely". The ban now covers most /
 * mostly / largely / majority / more than half / for the most part / nearly
 * all / almost all.
 */
describe("leg cm[bridge] — the majority ban's full vocabulary (R-DEC-COVERAGE-b)", () => {
  const census = () => bridgeHighCensus(RUN4_META);

  it("RED at fix 5: the reviewer's four probes each FAIL", () => {
    for (const probe of [
      "Published links are mostly hand-adjudicated.",
      "For the most part, published links were hand-adjudicated.",
      "More than half of published links were hand-adjudicated.",
      "Published links were largely hand-adjudicated.",
    ]) {
      const text = SHIPPED_R4.replace("High means the contract", `${probe} High means the contract`);
      expect(text, probe).not.toBe(SHIPPED_R4);
      expect(checkCrosswalkBlockerWording(text, census()).join("\n"), probe).toMatch(/majority word/);
    }
  });

  it("every word the ruling names FAILS below one half", () => {
    for (const word of [
      "Most",
      "Mostly",
      "Largely",
      "The majority",
      "More than half",
      "For the most part",
      "Nearly all",
      "Almost all",
    ]) {
      const text = SHIPPED_R4.replace(
        "High means the contract",
        `${word} of what publishes is hand-adjudicated. High means the contract`,
      );
      expect(checkCrosswalkBlockerWording(text, census()).join("\n"), word).toMatch(/majority word/);
    }
  });

  it("each passes only above one half", () => {
    const big = { published: 1133, adjudicated: 600, twoLens: 600, measuredOn: "2026-09-25" };
    for (const word of ["Mostly", "Largely", "More than half", "For the most part"]) {
      const text = SHIPPED_R4.replace("60 of the 1,133", "600 of the 1,133").replace(
        "High means the contract",
        `${word} of what publishes at high is hand-adjudicated. High means the contract`,
      );
      expect(checkCrosswalkBlockerWording(text, big), word).toEqual([]);
    }
  });

  it("'the most recent' and 'at most' stay a superlative and a bound", () => {
    const text = SHIPPED_R4.replace(
      "were hand-adjudicated,",
      "were hand-adjudicated (the most recent adjudication is dated; at most one per award),",
    );
    expect(checkCrosswalkBlockerWording(text, census())).toEqual([]);
  });

  // Fix round 7 (fix-6 re-check): the lookbehind that spares "the most
  // recent" covered the whole most(?:ly)? alternative, so "the mostly
  // hand-adjudicated evidence base" passed. It now applies to "most" only.
  it("RED at fix 6: 'the mostly …' FAILS; 'the most recent' still passes", () => {
    for (const probe of [
      "The published links, the mostly hand-adjudicated evidence base, cite sources.",
      "Published links are, at mostly two reviews each, hand-adjudicated.",
    ]) {
      const text = SHIPPED_R4.replace("High means the contract", `${probe} High means the contract`);
      expect(text, probe).not.toBe(SHIPPED_R4);
      expect(checkCrosswalkBlockerWording(text, census()).join("\n"), probe).toMatch(/majority word/);
    }
    const recent = SHIPPED_R4.replace("High means the contract", "The most recent adjudication is dated. High means the contract");
    expect(recent).not.toBe(SHIPPED_R4);
    expect(checkCrosswalkBlockerWording(recent, census())).toEqual([]);
  });
});

describe("leg cm[bridge] — the census clause's boundary (R-DEC-COVERAGE-b)", () => {
  const census = () => bridgeHighCensus(RUN4_META);
  const CLAUSE = "60 of the 1,133 links published at high were hand-adjudicated";

  it("an 'or' straight after the predicate widens it, whatever the punctuation", () => {
    for (const tail of [" or reviewed,", ", or reviewed,", " (or reviewed),", " — or reviewed —", " and/or reviewed,"]) {
      const text = SHIPPED_R4.replace(`${CLAUSE},`, `${CLAUSE}${tail}`);
      expect(text, tail).not.toBe(SHIPPED_R4);
      expect(checkCrosswalkBlockerWording(text, census()).join("\n"), tail).toMatch(/census clause/);
    }
  });

  it("the shipped ', and where …' continuation is not a widening", () => {
    expect(SHIPPED_R4).toContain(`${CLAUSE}, and where a per-award adjudication exists`);
    expect(checkCrosswalkBlockerWording(SHIPPED_R4, census())).toEqual([]);
  });
});
