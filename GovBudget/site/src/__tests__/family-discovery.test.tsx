import React from "react";
import { describe, expect, it } from "vitest";
import { render, within } from "@testing-library/react";
import { F15FamilyFeature, ProgramFamilyEntry } from "@/components/family-entry";
import ExplorePage from "@/app/explore/page";
import { getF15FamilyData } from "@/lib/f15-family-data";

const family = getF15FamilyData();

describe("F-15 family discovery", () => {
  it.each([
    ["0207134F", "E"],
    ["0207146F", "EX"],
    ["0207171F", "EX"],
    ["F01500", "E"],
    ["F015EX", "EX"],
    ["F15EWS", "E"],
  ])("preserves the %s budget record when entering the family browser", (slug, variant) => {
    const { container } = render(<ProgramFamilyEntry programSlug={slug} />);
    const link = within(container).getByRole("link", { name: "Open the family browser" });
    const url = new URL(link.getAttribute("href")!, "https://fiscalreceipts.com");
    // Next Link normalizes the slash without the build-time trailingSlash flag.
    expect(url.pathname.replace(/\/$/, "")).toBe("/families/f-15");
    expect(url.searchParams.get("record")).toBe(slug);
    expect(url.searchParams.get("variant")).toBe(variant);
    const record = family.records.find((item) => item.slug === slug)!;
    expect(url.searchParams.get("purpose")).toBe(record.purpose);
    expect(record.variantIds).toContain(variant);
    expect(family.variants.find((item) => item.id === variant)!.recordLinks.some((link) => link.slug === slug)).toBe(true);
  });

  it("does not infer family membership from a similar program code", () => {
    for (const slug of ["F01500-other-account", "F015", "0207146N", "ATA000"]) {
      const { container } = render(<ProgramFamilyEntry programSlug={slug} />);
      expect(container).toBeEmptyDOMElement();
    }
  });

  it("offers one clear family destination without loading an interactive model", () => {
    const { container } = render(<F15FamilyFeature />);
    expect(within(container).getByRole("link", { name: "Explore the F-15 family" })).toHaveAttribute("href", expect.stringMatching(/^\/families\/f-15\/?$/));
    expect(within(container).getByText("F-15EX")).toBeVisible();
    expect(within(container).getByText(/Conceptual silhouette/)).toBeVisible();
    expect(container.querySelector("model-viewer, canvas, iframe")).toBeNull();
  });

  it("makes the family discoverable from Explore alongside the existing program exhibits", () => {
    const { container } = render(<ExplorePage />);
    expect(within(container).getByRole("link", { name: "Explore the F-15 family" })).toHaveAttribute("href", expect.stringMatching(/^\/families\/f-15\/?$/));
    expect(container.querySelectorAll('a[href$="#exhibit"]')).toHaveLength(3);
    // "More programs to inspect" is a .t-label kicker, not a heading (the
    // label spec is not a heading role — iteration-8 type system).
    expect(within(container).getByText("More programs to inspect")).toBeVisible();
  });
});
