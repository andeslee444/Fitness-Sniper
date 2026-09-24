import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { F15RelatedPrograms } from "@/components/f15-related-programs";
import { CitationPanelContext } from "@/components/cite";
import { getF15RelatedPrograms } from "@/lib/f15-related-programs-data";

afterEach(cleanup);

describe("shared F-15 program evidence", () => {
  it("retains every source edition and direct PDF without claiming F-15 allocations", () => {
    const programs = getF15RelatedPrograms();
    const openPanel = vi.fn();
    const { container } = render(<CitationPanelContext.Provider value={{ openPanel }}><F15RelatedPrograms programs={programs} /></CitationPanelContext.Provider>);
    expect(screen.getByText(/Their budgets are excluded from the family totals/)).toBeInTheDocument();
    expect(screen.queryByRole("table")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "View all shared-program sources" }));
    const table = screen.getByRole("table", { name: "Shared programs with F-15 work" });
    expect(table.querySelectorAll("[data-shared-program]")).toHaveLength(36);
    expect(container.querySelector("[data-amount]")).toBeNull();
    for (const program of programs) {
      const row = table.querySelector(`[data-shared-program="${program.identifier}"][data-source-edition="${program.sourceEdition}"]`)!;
      expect(row.querySelector("a[target='_blank']")).toHaveAttribute("href", program.officialUrl);
      expect(row).toHaveTextContent(`PB${program.sourceEdition}`);
      expect(row).toHaveTextContent(program.locator);
      expect(row.querySelector("blockquote")?.textContent).toContain(program.excerpt);
      if (program.slug) expect([...row.querySelectorAll("a")].map(a => a.getAttribute("href")?.replace(/\/$/, "")), program.identifier).toContain(`/program/${program.slug}`);
      if (program.factId) {
        fireEvent.click(row.querySelector("[data-source-fact]")!);
        expect(openPanel).toHaveBeenLastCalledWith(program.factId);
      } else {
        expect(row.querySelector("[data-source-fact]")).toBeNull();
        expect(row).toHaveTextContent("receipt not yet published");
      }
    }
    expect(openPanel).toHaveBeenCalledTimes(30);
  });
});
