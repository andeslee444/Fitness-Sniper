import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { getF15Knowledge } from "@/lib/f15-knowledge";
import { F15KnowledgeSection } from "@/components/f15-knowledge-section";

vi.mock("next/dynamic", async () => {
  const { default: Research } =
    await import("@/components/f15-knowledge-browser");
  return { default: () => Research };
});

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
});
afterEach(cleanup);

function mount() {
  return render(
    <F15KnowledgeSection variant="EX" onCopy={vi.fn()} onInteract={vi.fn()} />,
  );
}

describe("F-15 network overview", () => {
  it("shows a real, cited preview without expanding the entire research workspace", () => {
    mount();
    const knowledge = getF15Knowledge();
    const operators = knowledge.operators.filter(
      (item) => item.status === "operator",
    );
    expect(operators).toHaveLength(7);
    const region = screen.getByRole("region", {
      name: "The wider F-15 network.",
    });
    for (const country of operators)
      expect(region).toHaveTextContent(country.country);
    expect(screen.queryByRole("searchbox")).toBeNull();
    expect(screen.queryByRole("article")).toBeNull();
    const request = knowledge.procurement.find(
      (item) => item.id === "us-fy27-request",
    )!;
    expect(
      screen.getByRole("heading", {
        name: `${request.quantity} more F-15EX aircraft.`,
      }),
    ).toBeVisible();
    expect(region).toHaveTextContent(
      "A request is a proposal, not a signed order.",
    );
    for (const link of within(region).getAllByRole("link")) {
      expect(
        knowledge.sources.some(
          (source) => source.url === link.getAttribute("href"),
        ),
      ).toBe(true);
    }
  });

  it.each([
    ["Explore countries & variants", "Countries & variants"],
    ["Examine orders & requests", "Orders & requests"],
    ["Explore suppliers & systems", "Suppliers & systems"],
    ["Related programs & developments", "Programs & developments"],
  ])(
    "opens %s directly and returns to the focused overview",
    (entry, category) => {
      mount();
      fireEvent.click(screen.getByRole("button", { name: entry }));
      expect(screen.getByRole("button", { name: category })).toHaveAttribute(
        "aria-pressed",
        "true",
      );
      expect(
        screen.getByRole("searchbox", { name: "Search field notes" }),
      ).toBeVisible();
      expect(screen.getAllByRole("article").length).toBeGreaterThan(0);
      expect(
        screen.getByRole("heading", { name: "The wider F-15 network." }),
      ).toHaveFocus();
      fireEvent.click(
        screen.getByRole("button", { name: "Back to the overview" }),
      );
      expect(screen.queryByRole("searchbox")).toBeNull();
      expect(screen.getByRole("button", { name: entry })).toBeVisible();
      expect(
        screen.getByRole("heading", { name: "The wider F-15 network." }),
      ).toHaveFocus();
    },
  );
});
