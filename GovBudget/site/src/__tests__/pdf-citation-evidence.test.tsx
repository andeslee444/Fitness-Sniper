import React, { useContext } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { CitationPanelProvider } from "@/components/citation-panel/panel";
import { CitationPanelContext } from "@/components/cite";
import { getCitations, type JbookPdfCitation } from "@/lib/data";
import { pagedAmountCitation } from "@/lib/citations";
import { citationSourceDocuments } from "@/lib/source-document";

vi.mock("@/components/asset-config", async (original) => ({
  ...await original<typeof import("@/components/asset-config")>(),
  AssetConfigProvider: ({ children }: { children: React.ReactNode }) => children,
  useAssetUrl: () => (path: string) => path,
}));
afterEach(cleanup);

describe("PDF amount evidence", () => {
  it("keeps the F-15 printed thousands separate from canonical million units", () => {
    const c = getCitations()["f6d6db240d3be8ba"] as JbookPdfCitation;
    expect(c.amount_text).toBe("78,345");
    expect(c.units).toBe("USD thousands");
    expect(pagedAmountCitation(c)?.page_number).toBe(20);
  });

  it("never creates a page preview from an unresolved receipt", () => {
    const c = getCitations()["90fab19bdc91648a"] as JbookPdfCitation;
    expect(c.resolution).toBe("unresolved");
    expect(pagedAmountCitation(c)).toBeNull();
    const documents = citationSourceDocuments(c);
    expect(documents).toHaveLength(1);
    expect(documents[0].url).not.toContain("#page=");
    expect(documents[0].locators).toEqual([]);
    expect(c.amount_text).toBeNull();
    expect(c.units).toBeNull();
  });

  it("shows the missing-location notice and the document link without a false amount", () => {
    const fid = "90fab19bdc91648a";
    const c = getCitations()[fid] as JbookPdfCitation;
    function Trigger() {
      const { openPanel } = useContext(CitationPanelContext);
      return <button onClick={() => openPanel(fid)}>Inspect evidence</button>;
    }
    render(<CitationPanelProvider citations={{[fid]: c}}><Trigger /></CitationPanelProvider>);
    fireEvent.click(screen.getByRole("button", {name:"Inspect evidence"}));
    expect(screen.getByRole("status")).toHaveTextContent("exact amount location");
    expect(screen.getByRole("link", {name:/Open government PDF/})).toBeVisible();
    expect(screen.queryByRole("img", {name:/Budget justification PDF/})).toBeNull();
    expect(screen.queryByText("301")).toBeNull();
  });
});
