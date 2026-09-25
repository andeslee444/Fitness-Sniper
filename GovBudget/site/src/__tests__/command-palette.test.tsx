import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CommandPalette } from "@/components/search/command-palette";
import { SiteHeader } from "@/components/site-header";

vi.mock("next/navigation", () => ({ usePathname: () => "/" }));

vi.mock("@/lib/search", () => ({
  warmIndex: vi.fn(),
  getRecents: () => [],
  addRecent: vi.fn(),
  titleForUrl: vi.fn(),
  escapeHtml: (text: string) => text,
  kindGroupLabel: (kind: string) => `${kind}s`,
  quickSearch: async () => ({
    // Scores deliberately disagree with display groups. Arrow navigation
    // must follow the visible rows rather than jumping to the company first.
    programs: [{ id: "p", title: "Research program", titleHtml: "Research program", url: "/program/example/", kind: "program", score: 10 }],
    companies: [{ id: "c", title: "Example contractor", titleHtml: "Example contractor", url: "/company/example/", kind: "company", score: 100 }],
    agencies: [{ id: "a", title: "Research agency", titleHtml: "Research agency", url: "/agency/example/", kind: "agency", score: 50 }],
    pages: [{ id: "d", title: "CO-05", titleHtml: "CO-05", url: "/district/CO-05/", kind: "district", score: 5 }],
  }),
}));

afterEach(cleanup);

function renderPalette() {
  render(<><button data-search-trigger>Open test search</button><CommandPalette /></>);
  const trigger = screen.getByRole("button", { name: "Open test search" });
  trigger.focus();
  fireEvent.click(trigger);
  return trigger;
}

describe("search dialog navigation", () => {
  it("keeps keyboard traversal in the visible group order and labels each option", async () => {
    renderPalette();
    const input = screen.getByRole("combobox");
    fireEvent.change(input, { target: { value: "zz" } });
    const program = await screen.findByRole("option", { name: "Research program, programs" });
    const company = screen.getByRole("option", { name: "Example contractor, companys" });
    const agency = screen.getByRole("option", { name: "Research agency, agencys" });
    expect(screen.getAllByTestId("search-result").slice(0, 3)).toEqual([program, company, agency]);
    expect(input).toHaveAttribute("aria-activedescendant", program.id);
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(input).toHaveAttribute("aria-activedescendant", company.id);
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(input).toHaveAttribute("aria-activedescendant", agency.id);
    fireEvent.keyDown(input, { key: "ArrowUp" });
    expect(input).toHaveAttribute("aria-activedescendant", company.id);
  });

  it("shows an exact district match once, ahead of other result groups", async () => {
    renderPalette();
    const input = screen.getByRole("combobox");
    fireEvent.change(input, { target: { value: "CO-05" } });
    const district = await screen.findByRole("option", { name: "CO-05, districts" });
    expect(screen.getAllByRole("option", { name: "CO-05, districts" })).toHaveLength(1);
    expect(screen.getAllByTestId("search-result")[0]).toBe(district);
    expect(input).toHaveAttribute("aria-activedescendant", district.id);
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(input).toHaveAttribute("aria-activedescendant", screen.getByRole("option", { name: "Research program, programs" }).id);
  });

  it("traps Tab inside the dialog and restores the actual opener on Escape", async () => {
    const trigger = renderPalette();
    const input = screen.getByRole("combobox");
    await waitFor(() => expect(input).toHaveFocus());
    const close = screen.getByRole("button", { name: "Close search" });
    close.focus();
    fireEvent.keyDown(close, { key: "Tab" });
    expect(input).toHaveFocus();
    fireEvent.keyDown(input, { key: "Tab", shiftKey: true });
    expect(close).toHaveFocus();
    fireEvent.keyDown(close, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await waitFor(() => expect(trigger).toHaveFocus());
  });

  it("hands off an open navigation menu to keyboard search without leaving a competing dialog", async () => {
    render(<><SiteHeader /><CommandPalette /></>);
    fireEvent.click(screen.getByRole("button", { name: "Open navigation menu" }));
    const closeNavigation = screen.getByRole("button", { name: "Close navigation menu" });
    closeNavigation.focus();
    fireEvent.keyDown(closeNavigation, { key: "k", metaKey: true });
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Explore Fiscal Receipts" })).not.toBeInTheDocument());
    expect(screen.getAllByRole("dialog")).toHaveLength(1);
    await waitFor(() => expect(screen.getByRole("combobox")).toHaveFocus());
    fireEvent.click(screen.getByRole("button", { name: "Close search" }));
    await waitFor(() => expect(screen.getByTestId("search-trigger")).toHaveFocus());
  });
});
