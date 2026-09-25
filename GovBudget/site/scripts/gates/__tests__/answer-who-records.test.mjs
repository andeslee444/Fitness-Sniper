import { describe, expect, it } from "vitest";
import { answerWhoCard, checkNoneTierAwardRecords, checkWithheldFloorSentence } from "../program-skeleton.mjs";
import { readConcentrationFloor, withheldFloorClause } from "../concentration-floor.mjs";

// program-skeleton leg (j), the honest-absence half (codex/f15-family-browser's
// "recipient total must link to its award records", kept and tightened by the
// integration of 2026-09-25), and the below-floor sentence guard.

const floor = { awards: 3, families: 2 };
const LEAD = "No single contractor is published as this line's leader.";
const REASON =
  "This line's high-confidence links do not clear the floor for a published concentration index — " +
  `${withheldFloorClause(floor)}.`;
const link = (n, text = `${n} linked award ${n === 1 ? "record is" : "records are"} listed below`) =>
  `<a class="underline" href="#program-awards">${text}</a>.<!-- --> `;

function page(answer, { anchor = true } = {}) {
  return (
    `<section><div data-testid="answer-who"><div>Who gets it</div><div>` +
    `<span data-who-tier="none">${answer}</span></div></div></section>` +
    `<nav><a href="#program-awards">Contracts &amp; influence</a></nav>` +
    `<section data-section="figures"></section>` +
    (anchor ? `<section id="program-awards" data-section="awards"></section>` : "")
  );
}
function check(html, awardCount) {
  const card = answerWhoCard(html);
  return checkNoneTierAwardRecords({ tierEl: card.querySelector("[data-who-tier]"), card, pageHtml: html, awardCount });
}

describe("leg (j): an honest absence on a page with award records", () => {
  it("passes the below-floor answer that links its records with the sidecar's count", () => {
    expect(check(page(`${LEAD} ${link(12)}${REASON}`), 12)).toEqual([]);
    expect(check(page(`${LEAD} ${link(1)}${REASON}`), 1)).toEqual([]);
  });

  it("fails an answer with no link to the records — the wayfinding nav's link does not count", () => {
    expect(check(page(`${LEAD} ${REASON}`), 12)).toEqual(["missing recipient total must link to its award records"]);
  });

  it("fails a link whose count is not the sidecar's, or that states none", () => {
    expect(check(page(`${LEAD} ${link(11)}${REASON}`), 12)[0]).toMatch(/states 11 .* lists 12/);
    expect(check(page(`${LEAD} ${link(0, "the award records")}${REASON}`), 12)[0]).toMatch(/states no count/);
  });

  it("fails a link to an anchor the page does not render", () => {
    expect(check(page(`${LEAD} ${link(12)}${REASON}`, { anchor: false }), 12)).toEqual([
      "links #program-awards, but the page renders no element with that id",
    ]);
  });

  it("still fails a denial of the links, as the live leg did", () => {
    const problems = check(page(`No company is linked to this line. ${link(4)}`), 4);
    expect(problems).toEqual(["denies award links despite 4 linked records"]);
  });
});

describe("leg (j): the below-floor sentence states the SQL floor", () => {
  it("passes the true sentence and ignores answers that state no floor", () => {
    expect(checkWithheldFloorSentence(`${LEAD} ${REASON}`, floor)).toBeNull();
    expect(checkWithheldFloorSentence("Named in the J-book: Boeing", floor)).toBeNull();
  });

  it("fails the sentence the SWC minifier fold shipped on build 42eed1e4", () => {
    const mangled = REASON.replace("at least 3 awards across 2 contractor families", "at least 32 contractor families");
    expect(checkWithheldFloorSentence(`${LEAD} ${mangled}`, floor)).toMatch(/states the concentration floor wrongly/);
  });

  it("reads the floor the warehouse applies", () => {
    expect(readConcentrationFloor()).toEqual(floor);
    expect(() => readConcentrationFloor("select 1")).toThrow(/expected the high-basis floor/);
    const drifted =
      "basis = 'high' then award_count end), 0) >= 3 basis = 'high' then award_count end), 0) >= 4 " +
      "basis = 'high' then positive_family_count end), 0) >= 2 basis = 'high' then positive_family_count end), 0) >= 2";
    expect(() => readConcentrationFloor(drifted)).toThrow();
  });
});
