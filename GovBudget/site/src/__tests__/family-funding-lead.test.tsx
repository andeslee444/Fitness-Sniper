import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { FamilyFundingLead, loadFamilyLead } from "@/components/family-funding-lead";
import F15FamilyPage from "@/app/families/f-15/page";
import { F15_RECORD_SLUGS } from "@/lib/f15-family";
import { familyLeadAbsence } from "@/lib/family-lead";

vi.mock("@/components/f15-model", () => ({ F15Model: () => <div /> }));
afterEach(cleanup);

describe("family funding entry", () => {
  it("renders the rule-selected exact receipt, all other records and the honest absence", () => {
    render(<FamilyFundingLead lead={loadFamilyLead(F15_RECORD_SLUGS, "F-15")} shortName="F-15" recordSlugs={F15_RECORD_SLUGS} />);
    const receipt = screen.getByTestId("family-receipt");
    expect(receipt).toHaveAttribute("data-family-records", F15_RECORD_SLUGS.join(","));
    expect(receipt).toHaveAttribute("data-family-edition", "2026");
    expect(receipt).toHaveAttribute("data-lead-record", "F015EX");
    expect(receipt).toHaveAttribute("data-lead-excluded", "0207171F");
    expect(receipt).toHaveAttribute("data-lead-fact-id", "4a9ae7cc78dcf0ba");
    expect(receipt).toHaveTextContent("Largest cited FY26 Request of 6 F-15 records");
    expect(receipt).toHaveTextContent("not added or allocated by aircraft variant");
    const figures = within(receipt).getByTestId("family-receipt-figure").querySelectorAll("[data-amount]");
    expect(figures).toHaveLength(1);
    expect(figures[0]).toHaveAttribute("data-entity", "F015EX");
    expect(figures[0]).toHaveAttribute("data-fy", "2026");
    expect(figures[0]).toHaveAttribute("data-measure", "request");
    expect(figures[0]).toHaveAttribute("data-basis", "toa");
    expect(figures[0]).toHaveAttribute("data-reconciliation");
    expect(receipt.querySelector("[data-fy26-recon-chip]")).toHaveTextContent("100.0% reconciliation");
    expect(screen.getByTestId("family-receipt-kicker")).toHaveTextContent("1 without a cited FY26 Request");
    const ledger = screen.getByTestId("family-ledger");
    expect(ledger.querySelectorAll("dt")).toHaveLength(5);
    expect(ledger.querySelectorAll("[data-amount]")).toHaveLength(4);
    expect(ledger.querySelectorAll("[data-absence]")).toHaveLength(1);
    const rows = [...ledger.querySelectorAll("[data-ledger-row]")];
    expect(rows.map(row => row.getAttribute("data-entity"))).toEqual(["F15EWS", "0207134F", "F01500", "0207146F", "0207171F"]);
    for (const row of rows.slice(0, 4)) {
      const fid = row.querySelector("[data-amount]")!.getAttribute("data-fact-id")!;
      expect(row).toHaveTextContent(`#${fid.slice(0, 8)}`);
    }
    expect(rows[4]).toHaveAttribute("data-absence");
    expect(rows[4].querySelector("[data-amount]")).toBeNull();
    expect(rows[4]).not.toHaveTextContent("$");
    expect(ledger.querySelector("[data-basis-declared]")).toHaveTextContent("PB2026");
    expect(ledger.querySelector("[data-ledger-tail]")).toBeNull();
    expect(ledger).toHaveTextContent("PE 0207171F");
    expect(ledger).toHaveTextContent("P-1/R-1 TOA");
  });

  it("keeps the server-rendered lead separate when the funding sheet changes record or aircraft", async () => {
    window.history.replaceState({}, "", "/families/f-15/");
    Object.defineProperty(window, "scrollTo", { configurable: true, value: vi.fn() });
    render(F15FamilyPage());
    await act(async () => { await new Promise<void>(resolve => requestAnimationFrame(() => resolve())); });
    fireEvent.click(within(screen.getByTestId("family-nav")).getByRole("link", { name: "Budget & receipts" }));
    fireEvent.change(screen.getByRole("combobox", { name: "Funding record" }), { target: { value: "0207146F" } });
    expect(screen.getByTestId("family-receipt")).toHaveAttribute("data-lead-fact-id", "4a9ae7cc78dcf0ba");
    const selected = screen.getByRole("article", { name: "Selected funding record" });
    expect(selected.querySelector('[data-amount][data-entity="0207146F"]')).not.toBeNull();
    fireEvent.change(screen.getByRole("combobox", { name: "Selected aircraft" }), { target: { value: "E" } });
    expect(screen.getByTestId("family-receipt")).toHaveTextContent("F-15EX · BLI F015EX");
    expect(screen.getByTestId("family-receipt")).toHaveAttribute("data-lead-fact-id", "4a9ae7cc78dcf0ba");
  });

  it("renders the missing-coverage doctrine without a substitute amount", () => {
    render(<FamilyFundingLead lead={{ kind: "absent", edition: 2026, recordCount: 1, text: familyLeadAbsence(2026, 1, "Example") }} shortName="Example" recordSlugs={["example"]} />);
    expect(screen.getByTestId("family-receipt")).toHaveAttribute("data-lead-absent");
    expect(screen.getByTestId("family-receipt")).toHaveAttribute("data-family-records", "example");
    expect(screen.getByTestId("family-receipt")).toHaveAttribute("data-family-edition", "2026");
    expect(screen.getByTestId("family-receipt").querySelector("[data-amount]")).toBeNull();
    expect(screen.getByText(/Missing coverage is not zero spending/)).toBeVisible();
  });
});
