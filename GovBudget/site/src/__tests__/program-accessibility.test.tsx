import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { CitationPanelContext } from "@/components/cite";
import { ProgramNarratives } from "@/components/program-narratives";
import { ProgramDetailsTable } from "@/components/program-details-table";
import { FollowTheDollar, getFlowData } from "@/components/follow-the-dollar";
import { getProgramDetails } from "@/lib/data";

afterEach(cleanup);

describe("program keyboard source access", () => {
  it("keeps accomplishment disclosures native and opens their exact source from the expanded body", () => {
    const openPanel = vi.fn();
    const { container } = render(<CitationPanelContext.Provider value={{ openPanel }}>
      <ProgramNarratives
        narratives={[{ kind: "accomplishment_planned_program", title: "Flight Test", body: "Flight testing continues.", fact_id: "abcdef1234567890", xml_path: "Program/Accomplishment[1]" }]}
        group="justification" peIndex={{ has: () => false, projects: () => new Set() }} selfPe="0207134F"
      />
    </CitationPanelContext.Provider>);
    const summary = container.querySelector("summary")!;
    expect(summary).toHaveTextContent("Flight Test");
    expect(summary.querySelector("button, a, [tabindex]")).toBeNull();
    fireEvent.click(summary);
    const source = screen.getByRole("button", { name: "View source citation for this passage" });
    expect(source).toBeVisible();
    expect(source).toHaveAttribute("data-fact-id", "abcdef1234567890");
    fireEvent.click(source);
    expect(openPanel).toHaveBeenCalledWith("abcdef1234567890");
    expect(container.querySelector("details")).toHaveAttribute("open");
    expect(container.querySelector('[data-source-text="narrative"]')).toHaveAttribute("data-xml-path", "Program/Accomplishment[1]");
  });

  it("exposes linked flow-chart destinations inside a named group rather than an atomic image", () => {
    const data = getFlowData("F15EWS")!;
    render(<FollowTheDollar data={data} />);
    const chart = screen.getByRole("group", { name: /Follow-the-dollar diagram for program F15EWS/ });
    expect(within(chart).getByRole("link", { name: "District page: MO-01" })).toHaveAttribute("href", "/district/MO-01/");
    const description = document.getElementById(chart.getAttribute("aria-describedby")!);
    expect(description).toHaveTextContent("Amounts inside the diagram are illustrative");
  });

  it("lets keyboard users focus the fiscal-year scroller even when every amount is XML-only", () => {
    render(<ProgramDetailsTable details={getProgramDetails("F15EWS").details} />);
    const scroller = screen.getByRole("region", { name: "Budget detail fiscal-year columns" });
    scroller.focus();
    expect(scroller).toHaveFocus();
    expect(within(scroller).getByRole("columnheader", { name: "FY26 Request" })).toBeVisible();
    expect(scroller.querySelector('[data-citation-kind="xml-path"][data-xml-path]')).not.toBeNull();
  });
});
