import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SiteHeader } from "@/components/site-header";

const usePathname = vi.hoisted(() => vi.fn(() => "/program/ATA000/"));
vi.mock("next/navigation", () => ({ usePathname }));
afterEach(() => { cleanup(); usePathname.mockReturnValue("/program/ATA000/"); });

describe("site navigation", () => {
  // Contract changed 2026-09-11 (design-critic round 2, iterations 1–3): the
  // family page no longer collapses the header into a "focused" mode that hid
  // the Fact IDs toggle behind the sections menu — four independent critics
  // read the two headers as "two products". The toggle is now directly
  // reachable on /families/…, and still present in the sections menu, whose
  // open/close and focus-return behaviour is unchanged.
  it("keeps the global identifier preference directly reachable on the family page", async () => {
    usePathname.mockReturnValue("/families/f-15/");
    render(<SiteHeader />);
    expect(screen.getByRole("button", { name: "Show fact IDs" })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Browse all sections" }));
    const inMenu = await screen.findAllByRole("button", { name: "Show fact IDs" });
    expect(inMenu.length).toBeGreaterThanOrEqual(1);
    fireEvent.click(screen.getByRole("button", { name: "Close all sections" }));
    await waitFor(() => expect(screen.getAllByRole("button", { name: "Show fact IDs" })).toHaveLength(1));
    expect(screen.getByRole("button", { name: "Browse all sections" })).toHaveFocus();
  });
  it("identifies the parent section on a detail page and exposes source tools in the full menu", async () => {
    render(<SiteHeader />);
    expect(screen.getByRole("link", { name: "Programs" })).toHaveAttribute("aria-current", "page");
    const trigger = screen.getByRole("button", { name: "Open navigation menu" });
    expect(trigger).not.toHaveAttribute("aria-controls");
    fireEvent.click(trigger);
    const panel = await screen.findByRole("dialog", { name: "Explore Fiscal Receipts" });
    expect(trigger).toHaveAttribute("aria-controls", panel.id);
    expect(document.getElementById("mobile-nav-panel")).toBe(panel);
    expect(screen.getByRole("link", { name: "Methodology" }).getAttribute("href")?.replace(/\/$/, "")).toBe("/methodology");
    expect(screen.getByRole("link", { name: "Coverage" }).getAttribute("href")?.replace(/\/$/, "")).toBe("/coverage");
    expect(screen.getByRole("link", { name: "Program lineage" }).getAttribute("href")?.replace(/\/$/, "")).toBe("/lineage");
    fireEvent.click(screen.getByRole("button", { name: "Close navigation menu" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(trigger).not.toHaveAttribute("aria-controls");
    await waitFor(() => expect(screen.getByRole("button", { name: "Open navigation menu" })).toHaveFocus());
  });
});
