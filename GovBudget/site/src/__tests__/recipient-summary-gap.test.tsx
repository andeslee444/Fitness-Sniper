import { expect, test } from "vitest";
import { render } from "@testing-library/react";
import { RecipientSummaryGap } from "@/components/recipient-summary-gap";

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
