import { describe, expect, it } from "vitest";
import { answerWhoCard } from "../program-skeleton.mjs";

describe("WHO GETS IT gate scope", () => {
  it("does not attribute a following exhibit's program funding to a recipient", () => {
    const html = `<section data-section="answer-strip"><div><div data-testid="answer-who">
      <p>Who gets it</p><div><span data-who-tier="none">No linked awards.</span></div>
      </div></div></section>
      <section id="exhibit"><div><span data-amount data-dataset="fct_budget_trajectory">$17.99M</span></div></section>
      <section data-section="figures"></section>`;
    const card = answerWhoCard(html);
    expect(card.querySelectorAll("[data-who-tier]")).toHaveLength(1);
    expect(card.querySelectorAll("[data-amount]")).toHaveLength(0);
    expect(card.text).not.toContain("$17.99M");
  });

  it("still exposes invalid dollars nested inside a non-award recipient card", () => {
    const html = `<div data-testid="answer-who"><span data-who-tier="lobbying">
      No contract award is linked. <span><span data-amount>$3M</span></span>
      </span></div><section id="exhibit"></section><section data-section="figures"></section>`;
    expect(answerWhoCard(html).querySelectorAll("[data-amount]")).toHaveLength(1);
  });

  it("retains the award figure and its dataset when one belongs in the card", () => {
    const html = `<div data-testid="answer-who"><span data-who-tier="award"><span
      data-amount data-dataset="fct_program_concentration">$4M</span></span></div>
      <section data-section="figures"><span data-amount>$30M</span></section>`;
    const card = answerWhoCard(html);
    expect(card.querySelectorAll("[data-amount]")).toHaveLength(1);
    expect(card.querySelector("[data-amount]").getAttribute("data-dataset")).toBe("fct_program_concentration");
  });

  it("reports a missing recipient card", () => {
    expect(answerWhoCard('<section id="exhibit"></section>')).toBeNull();
  });
});
