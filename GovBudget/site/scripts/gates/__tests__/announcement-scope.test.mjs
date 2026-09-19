/**
 * Unit tests for gate 24 leg (q) — the announcement LLM-alias pass's published
 * scope and its own measured precision (ROADMAP findings log :118-119).
 *
 * THE DEFECT THIS PINS. /methodology/ stated "the 3,840 unmatched records that
 * carry about 88% of the residue by announced value; the 12,811 smaller records
 * carrying the remaining ~12% were not attempted" — four literals typed
 * 2026-09-02, describing a residue whose selection code was never committed.
 * Every gate was green. The leg below recomputes each figure from
 * site_meta.announcement_llm_scope and requires the rendered paragraph to state
 * it, and — symmetrically — requires NO paragraph when no pass is recorded.
 *
 * THE SECOND HALF (2026-09-19). The pass's newest round is measured by its OWN
 * held-out sample, not by the tier-wide study, which was drawn before those
 * links existed. The leg binds that pair in the same slot order as the counts,
 * and fails a paragraph that states a pair the block does not carry — the one
 * way a reader could be handed another population's precision.
 *
 * FULL.records_attempted is deliberately NOT equal to records_residue, so a
 * stale attempted-count is a figure the paragraph genuinely fails to contain.
 *
 * Corpora are injected (like link-precision.test.mjs), so no build is needed.
 * Run via `npm test` (vitest) from site/.
 */
import { describe, it, expect } from "vitest";
import { runAnnouncementScopeLeg } from "../datatruth.mjs";

const FULL = {
  as_of: "2026-09-19",
  records_total: 32852,
  records_deterministic: 4508,
  records_residue: 28344,
  records_attempted: 26900,
  records_remaining: 1444,
  pct_value_attempted: 97.3,
  pct_value_remaining: 2.7,
  precision: { sample_id: "2026-09-12", sampled_at: "2026-09-19", sampled: 55, confirmed: 48 },
};

const DONE = { ...FULL, records_attempted: 28344, records_remaining: 0,
               pct_value_attempted: 100, pct_value_remaining: 0 };

const UNMEASURED = { ...FULL, precision: null };

const head =
  "Scope of the announcement path: deterministic name matching covered all " +
  "32,852 archived announcement records that join the award lake; 4,508 named " +
  "a program a J-book narrative owns. Of the 28,344 that did not, ";

const measured =
  " Its most recent round carries its own measurement: two independent " +
  "reviewers judged a random draw of its links on 2026-09-19 and confirmed " +
  "48 of the 55 that publish — those links only, not the path as a whole.";

const fullText = head +
  "26,900 have been through an LLM-assisted alias pass — 97.3% of the residue " +
  "by announced value; the remaining 1,444 records (2.7% of that value) were " +
  "not attempted." + measured;

const doneText = head +
  "28,344 have been through an LLM-assisted alias pass — 100% of the residue " +
  "by announced value; none is left unattempted." + measured;

const unmeasuredText = head +
  "26,900 have been through an LLM-assisted alias pass — 97.3% of the residue " +
  "by announced value; the remaining 1,444 records (2.7% of that value) were " +
  "not attempted. Its most recent round has not yet been measured on a " +
  "held-out sample of its own.";

describe("gate 24 leg q — announcement LLM-pass scope", () => {
  it("passes when every rendered figure matches site_meta", () => {
    const errors = [], notes = [];
    runAnnouncementScopeLeg(errors, notes, {
      siteMeta: { announcement_llm_scope: FULL }, paragraphText: fullText,
    });
    expect(errors).toEqual([]);
    expect(notes.join(" ")).toContain("leg q");
  });

  it("passes on a completed pass that claims nothing is left", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: { announcement_llm_scope: DONE }, paragraphText: doneText,
    });
    expect(errors).toEqual([]);
  });

  it("FAILS when the page keeps a stale record count", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: { announcement_llm_scope: FULL },
      // the 2026-09-02 literal, left behind after a fuller pass
      paragraphText: fullText.replace("26,900 have been", "3,840 have been"),
    });
    expect(errors.join(" ")).toMatch(/26,900/);
  });

  it("FAILS when the page keeps a stale percentage", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: { announcement_llm_scope: FULL },
      paragraphText: fullText.replace("97.3% of the residue", "88% of the residue"),
    });
    expect(errors.join(" ")).toMatch(/97\.3%/);
  });

  it("FAILS when a partial pass does not say what was not attempted", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: { announcement_llm_scope: FULL },
      paragraphText: fullText
        .replace("the remaining 1,444 records (2.7% of that value) were not " +
                 "attempted.",
                 "the remaining 1,444 records (2.7% of that value) are queued."),
    });
    expect(errors.join(" ")).toMatch(/1,444/);
  });

  it("FAILS when a completed pass still says records were not attempted", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: { announcement_llm_scope: DONE },
      paragraphText: doneText.replace("none is left unattempted.",
        "the remaining records were not attempted."),
    });
    expect(errors.join(" ")).toMatch(/not attempted/i);
  });

  it("FAILS when the paragraph renders and site_meta carries no pass", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: { announcement_llm_scope: {} }, paragraphText: fullText,
    });
    expect(errors.join(" ")).toMatch(/must stay absent/);
  });

  it("passes silently when no pass is recorded and no paragraph renders", () => {
    const errors = [], notes = [];
    runAnnouncementScopeLeg(errors, notes, {
      siteMeta: {}, paragraphText: null,
    });
    expect(errors).toEqual([]);
    expect(notes.join(" ")).toMatch(/paragraph absent/);
  });

  it("FAILS when site_meta carries a pass and the paragraph is missing", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: { announcement_llm_scope: FULL }, paragraphText: null,
    });
    expect(errors.join(" ")).toMatch(/\[data-announcement-scope\]/);
  });

  it("FAILS when /methodology/ is not built, like leg n does", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: { announcement_llm_scope: FULL }, paragraphText: null,
      methodologyBuilt: false,
    });
    expect(errors.join(" ")).toMatch(/not built/);
  });

  // ── the pass's own precision pair ────────────────────────────────────────

  it("FAILS when the rendered pair is not the measured one", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: { announcement_llm_scope: FULL },
      // the tier-wide figure, which was sampled before these links existed
      paragraphText: fullText.replace("48 of the 55", "56 of the 60"),
    });
    expect(errors.join(" ")).toMatch(/48 of the 55/);
  });

  it("FAILS when the rendered judged date is not the measured one", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: { announcement_llm_scope: FULL },
      paragraphText: fullText.replace("on 2026-09-19 and", "on 2026-09-04 and"),
    });
    expect(errors.join(" ")).toMatch(/2026-09-19/);
  });

  it("passes when no sample has measured the newest round and the page says so", () => {
    const errors = [], notes = [];
    runAnnouncementScopeLeg(errors, notes, {
      siteMeta: { announcement_llm_scope: UNMEASURED }, paragraphText: unmeasuredText,
    });
    expect(errors).toEqual([]);
    expect(notes.join(" ")).toMatch(/not measured/);
  });

  it("FAILS when no sample has measured the newest round and the page states a pair anyway", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: { announcement_llm_scope: UNMEASURED }, paragraphText: fullText,
    });
    expect(errors.join(" ")).toMatch(/no held-out sample|not yet measured/i);
  });

  it("FAILS when a measured round is described as unmeasured", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: { announcement_llm_scope: FULL }, paragraphText: unmeasuredText,
    });
    expect(errors.join(" ")).toMatch(/not yet measured/i);
  });

  it("FAILS on a half-written precision block rather than skipping the pair", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: {
        announcement_llm_scope: { ...FULL, precision: { sample_id: "2026-09-12", sampled: 55 } },
      },
      paragraphText: fullText,
    });
    expect(errors.join(" ")).toMatch(/precision/i);
  });
});
