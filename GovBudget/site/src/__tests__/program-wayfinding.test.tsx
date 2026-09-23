import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { ProgramWayfinding } from "@/components/program-wayfinding";
import { ProgramSection, SectionEmpty } from "@/components/program-section";

afterEach(cleanup);

function mount() {
  return render(<>
    <ProgramWayfinding code="ATA000" isProcurement />
    <ProgramSection id="awards"><SectionEmpty title="Related awards">No supported award links are available for this program.</SectionEmpty></ProgramSection>
    <ProgramSection id="sources"><h2>Primary sources</h2></ProgramSection>
  </>);
}

describe("program chapter navigation", () => {
  it("closes the mobile disclosure and moves focus to the selected section, including an empty one", () => {
    const { container } = mount();
    const details = container.querySelector("details")!;
    details.open = true;
    const chapter = within(details).getByRole("link", { name: /Related awards/ });
    fireEvent.click(chapter);
    expect(details.open).toBe(false);
    expect(container.querySelector('[data-section="awards"]')).toHaveFocus();
    expect(chapter).toHaveAttribute("href", "#program-awards");
    expect(chapter).toHaveAttribute("aria-current", "location");
    expect(screen.getByText("No supported award links are available for this program.")).toBeVisible();
  });

  it("lets keyboard users dismiss the chapter list without losing their position", () => {
    const { container } = mount();
    const details = container.querySelector("details")!;
    details.open = true;
    const chapter = within(details).getByRole("link", { name: /Primary sources/ });
    chapter.focus();
    fireEvent.keyDown(chapter, { key: "Escape" });
    expect(details.open).toBe(false);
    expect(details.querySelector("summary")).toHaveFocus();
  });
});
