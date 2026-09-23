import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { F15KnowledgeBrowser } from "@/components/f15-knowledge-browser";
import { getF15Knowledge } from "@/lib/f15-knowledge";
import type { F15Knowledge } from "@/lib/f15-knowledge-types";

const knowledge = getF15Knowledge();
afterEach(cleanup);

function mount(data: F15Knowledge = knowledge) {
  const copy = vi.fn();
  const result = render(
    <F15KnowledgeBrowser
      knowledge={data}
      variant="EX"
      onCopy={copy}
      onInteract={vi.fn()}
    />,
  );
  return { ...result, copy };
}

describe("F-15 field notes", () => {
  it("finds an award by its contract identifier even when the ID is in the amount basis", () => {
    mount();
    fireEvent.click(screen.getByRole("button", { name: "Orders & requests" }));
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "FA8634-26-C-B002" } });
    const articles = screen.getAllByRole("article");
    expect(articles).toHaveLength(1);
    expect(articles[0]).toHaveTextContent("FA8634-26-C-B002");
    expect(articles[0]).toHaveTextContent("South Korea");
  });
  it("searches countries and retains their dated quantities and evidence links", () => {
    mount();
    fireEvent.change(
      screen.getByRole("searchbox", { name: "Search field notes" }),
      { target: { value: "Japan" } },
    );
    const country = knowledge.operators.find(
      (item) => item.country === "Japan",
    )!;
    expect(screen.getByRole("heading", { level: 3, name: "Japan" })).toBeVisible();
    expect(screen.getByText(country.quantityNote)).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Singapore" })).toBeNull();
    const source = knowledge.sources.find(
      (item) => item.id === country.sourceIds[0],
    )!;
    expect(
      screen.getByRole("link", { name: source.title, hidden: true }),
    ).toHaveAttribute("href", source.url);
  });

  it("separates contracts from requests and never calculates a per-aircraft price", () => {
    mount();
    fireEvent.click(screen.getByRole("button", { name: "Orders & requests" }));
    fireEvent.change(screen.getByLabelText("Acquisition stage"), {
      target: { value: "request" },
    });
    const articles = screen.getAllByRole("article");
    expect(articles.length).toBeGreaterThan(0);
    for (const article of articles) {
      const event = knowledge.procurement.find(
        (item) => item.id === article.getAttribute("data-context-id"),
      )!;
      expect(event.status).toBe("request");
      expect(within(article).getByText("Budget request")).toBeVisible();
      if (event.amount) expect(article).toHaveTextContent(event.amountBasis!);
      expect(article.querySelectorAll("strong")).toHaveLength(
        Number(event.quantity != null) + Number(Boolean(event.amount)),
      );
    }
    expect(
      screen.getByText(/Newer requests below remain separate/),
    ).toBeVisible();
  });

  it("filters supplier applicability and keeps manufacturer statements distinct", () => {
    mount();
    fireEvent.click(
      screen.getByRole("button", { name: "Suppliers & systems" }),
    );
    fireEvent.click(screen.getByLabelText("Applies to F-15EX"));
    for (const article of screen.getAllByRole("article")) {
      expect(
        knowledge.systems.find(
          (item) => item.id === article.getAttribute("data-context-id"),
        )!.usVariants,
      ).toContain("EX");
    }
    fireEvent.click(screen.getByLabelText("All sources are government records"));
    for (const article of screen.getAllByRole("article")) {
      expect(
        within(article).queryAllByText("Manufacturer statement"),
      ).toHaveLength(0);
    }
  });

  it("keeps unconfirmed claims out by default and labels them after explicit inclusion", () => {
    const data: F15Knowledge = {
      ...knowledge,
      sources: [
        ...knowledge.sources,
        {
          id: "test-rumor",
          title: "An attributed unconfirmed report",
          publisher: "Test outlet",
          url: "https://example.org/report",
          evidence: "unconfirmed",
          accessed: "2026-09-09",
          published: "2026-09-01",
        },
      ],
      systems: [
        ...knowledge.systems,
        {
          id: "test-rumor-card",
          category: "development",
          title: "Unconfirmed test claim",
          organization: "Test outlet",
          variants: ["F-15EX"],
          usVariants: ["EX"],
          summary:
            "This is an unconfirmed claim used only in the test fixture.",
          asOf: "2026-09-01",
          sourceIds: ["test-rumor"],
        },
      ],
    };
    mount(data);
    fireEvent.click(
      screen.getByRole("button", { name: "Programs & developments" }),
    );
    expect(
      screen.queryByRole("heading", { name: "Unconfirmed test claim" }),
    ).toBeNull();
    fireEvent.click(screen.getByLabelText("Include unconfirmed reports"));
    expect(
      screen.getByRole("heading", { name: "Unconfirmed test claim" }),
    ).toBeVisible();
    expect(screen.getAllByText("Unconfirmed report").length).toBeGreaterThan(0);
  });

  it("copies citation metadata and offers a useful filter reset", () => {
    const { copy } = mount();
    const article = screen.getAllByRole("article")[0];
    const country = knowledge.operators.find(
      (item) => item.id === article.getAttribute("data-context-id"),
    )!;
    fireEvent.click(
      within(article).getByRole("button", { name: "Copy sources" }),
    );
    const source = knowledge.sources.find(
      (item) => item.id === country.sourceIds[0],
    )!;
    expect(copy).toHaveBeenCalledWith(
      expect.stringContaining(source.url),
      expect.any(String),
    );
    expect(copy).toHaveBeenCalledWith(
      expect.stringContaining(source.accessed),
      expect.any(String),
    );
    fireEvent.change(screen.getByRole("searchbox"), {
      target: { value: "zzzzmissing" },
    });
    expect(screen.getByRole("heading", { level: 3, name: "No entries match these filters." })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Reset filters" }));
    expect(screen.getAllByRole("article").length).toBe(
      knowledge.operators.length,
    );
  });
});
