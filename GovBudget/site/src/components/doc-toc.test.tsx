import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { DocToc } from "./doc-toc";

let desktop: boolean;
let resize: (() => void) | undefined;

beforeEach(() => {
  desktop = false;
  resize = undefined;
  vi.stubGlobal("IntersectionObserver", class {
    observe() {}
    disconnect() {}
  });
  vi.stubGlobal("matchMedia", () => ({
    get matches() { return desktop; },
    addEventListener: (_: string, listener: () => void) => { resize = listener; },
    removeEventListener: () => { resize = undefined; },
  }));
});

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

async function mount() {
  const view = render(<div className="doc-layout">
    <article data-doc-prose>
      <h2 id="verification">Verification</h2>
      <h2>Source coverage</h2>
      <h3>Source coverage</h3>
    </article>
    <DocToc />
  </div>);
  await waitFor(() => expect(screen.getByRole("navigation", { name: "On this page" })).toBeInTheDocument());
  const disclosure = view.container.querySelector("details")!;
  const summary = disclosure.querySelector("summary")!;
  return { ...view, disclosure, summary };
}

describe("document contents across layouts", () => {
  it("starts closed on mobile and moves focus to a stable destination after selection", async () => {
    const { container, disclosure, summary } = await mount();
    expect(disclosure.open).toBe(false);
    fireEvent.click(summary);
    expect(disclosure.open).toBe(true);
    fireEvent.click(screen.getByRole("link", { name: "Verification" }));
    expect(disclosure.open).toBe(false);
    expect(container.querySelector("h2")).toHaveAttribute("id", "verification");
    expect(container.querySelector("h2")).toHaveFocus();
    expect(container.querySelector("h3")).toHaveAttribute("id", "source-coverage-2");
  });

  it("closes on Escape and returns keyboard focus to the disclosure", async () => {
    const { disclosure, summary } = await mount();
    fireEvent.click(summary);
    const link = screen.getByRole("link", { name: "Verification" });
    link.focus();
    fireEvent.keyDown(link, { key: "Escape" });
    expect(disclosure.open).toBe(false);
    expect(summary).toHaveFocus();
  });

  it("keeps one open desktop list and resets to a compact disclosure after resizing", async () => {
    desktop = true;
    const { container, disclosure } = await mount();
    expect(disclosure.open).toBe(true);
    expect(container.querySelectorAll(".doc-toc-list")).toHaveLength(1);
    fireEvent.click(screen.getByRole("link", { name: "Verification" }));
    expect(disclosure.open).toBe(true);
    desktop = false;
    resize?.();
    expect(disclosure.open).toBe(false);
  });
});
