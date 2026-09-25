import { expect, test } from "vitest";
import fs from "fs";
import path from "path";
import { render } from "@testing-library/react";
import { LinkedAwardRecordsLink, RecipientSummaryGap } from "@/components/recipient-summary-gap";

test("linked records survive the absence of an attributable recipient total", () => {
  const { container, getByRole } = render(<RecipientSummaryGap awardCount={5} />);
  expect(getByRole("link", { name: "5 linked award records are listed below" }).getAttribute("href")).toBe("#program-awards");
  expect(container.textContent).toContain("No program-wide recipient total is available");
  expect(container.textContent).not.toContain("No company is linked");
});

test("no-record absence stays explicit", () => {
  const { container } = render(<RecipientSummaryGap awardCount={0} />);
  expect(container.textContent).toContain("No company is linked");
  expect(container.querySelector('a')?.getAttribute('href')).toMatch(/^\/coverage\/?#crosswalk$/);
});

// Integration 2026-09-25: the program page's two withheld-concentration
// answers (#80 below the floor, #82 shared code) state no recipient total
// either, so they carry the same link (program-skeleton leg (j)).
test("the shared link states the count, in the singular too, and targets the awards table", () => {
  const one = render(<LinkedAwardRecordsLink awardCount={1} />);
  expect(one.getByRole("link", { name: "1 linked award record is listed below" }).getAttribute("href")).toBe("#program-awards");
  const many = render(<LinkedAwardRecordsLink awardCount={17} />);
  expect(many.getByRole("link", { name: "17 linked award records are listed below" }).getAttribute("href")).toBe("#program-awards");
});

test("both withheld-concentration answers on the program page render it with the page's award count", () => {
  const src = fs.readFileSync(path.resolve(__dirname, "..", "app", "program", "[peBli]", "page.tsx"), "utf8");
  const first = src.indexOf('data-who-tier="none"');
  const second = src.indexOf('data-who-tier="none"', first + 1);
  const third = src.indexOf('data-who-tier="none"', second + 1);
  expect(third).toBeGreaterThan(second);
  for (const branch of [src.slice(first, second), src.slice(second, third)]) {
    expect(branch).toContain("<LinkedAwardRecordsLink awardCount={awardCount} />");
    expect(branch).toContain("awardCount > 0 &&");
  }
  // The below-floor answer leads with the absence of a leader, then the link,
  // then the rule — the order a reader meets them.
  const belowFloor = src.slice(first, second);
  expect(belowFloor.indexOf("{WHO_GETS_IT_WITHHELD_LEAD}")).toBeLessThan(belowFloor.indexOf("<LinkedAwardRecordsLink"));
  expect(belowFloor.indexOf("<LinkedAwardRecordsLink")).toBeLessThan(belowFloor.indexOf("{CONCENTRATION_WITHHELD_REASON}"));
});
