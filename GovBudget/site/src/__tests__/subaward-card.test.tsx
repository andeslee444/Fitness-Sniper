import React, { useContext } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { SubawardCard, parseSubawardEvidence } from "@/components/citation-panel/subaward-card";
import { CitationPanelProvider } from "@/components/citation-panel/panel";
import { CitationPanelContext } from "@/components/cite";
import { getCitations, type SubawardCitation } from "@/lib/data";
import { citationSourceDocuments } from "@/lib/source-document";
import { footnoteInputFromCitation } from "@/lib/footnote";

vi.mock("@/components/asset-config", async (importOriginal) => ({
  ...await importOriginal<typeof import("@/components/asset-config")>(),
  AssetConfigProvider: ({ children }: { children: React.ReactNode }) => children,
  useAssetUrl: () => (path: string) => path,
  useAssetConfig: () => ({ assetsBaseUrl: "/assets", loaded: true, error: null }),
}));

afterEach(cleanup);
const fid = "4fe505d824c9f9aa";
const citation = getCitations()[fid] as SubawardCitation;

describe("subaward link evidence", () => {
  it("identifies the source and confidence without treating prime-award context as the subaward receipt", () => {
    render(<SubawardCard citation={citation} />);
    expect(screen.getByText("10977 REL 1")).toBeVisible();
    expect(screen.getByText("VT MILCOM INC.")).toBeVisible();
    expect(screen.getByText(/medium-confidence inference/)).toBeVisible();
    expect(screen.getByText(/does not establish the amount/)).toBeVisible();
    expect(screen.getByText(/description excerpt are not included/)).toBeVisible();
    const link = screen.getByRole("link", { name: /Open prime award on USAspending/ });
    expect(link).toHaveAttribute("href", citation.official_url);
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(screen.getByText(/not a permalink to the subaward description/)).toBeVisible();
    expect(citationSourceDocuments(citation)).toEqual([]);
  });

  it("supports every currently published subaward identity", () => {
    const rows = Object.values(getCitations()).filter(row => row.kind === "subaward");
    expect(rows.length).toBeGreaterThan(0);
    for (const row of rows) expect(parseSubawardEvidence(row), row.official_url).not.toBeNull();
  });

  it.each([
    { query_body: "{" }, { query_body: "null" },
    { query_body: JSON.stringify({ subaward_number: "", subawardee: "ACME", match_basis: "subaward-description-exact" }) },
    { query_body: JSON.stringify({ subaward_number: "1", subawardee: "ACME", match_basis: "llm-alias" }) },
    { official_url: "https://www.usaspending.gov.evil.example/award/CONT_AWD_N0017818F3011_9700_/" },
    { official_url: "https://www.usaspending.gov/award/CONT_AWD_OTHER_9700_/" },
    { official_url: "https://www.usaspending.gov/award/CONT_AWD_N0017818F3011_9700_/?x=1" },
    { official_url: "https://username@www.usaspending.gov/award/CONT_AWD_N0017818F3011_9700_/" },
    { recorded_value: "100" }, { amount_text: "$100" }, { amount_thousands: 1 }, { units: "USD" },
    { formula: citation.formula.replace("confidence='medium'", "confidence='high'") },
  ])("fails visibly for malformed evidence %j", changes => {
    const malformed = { ...citation, ...changes } as SubawardCitation;
    expect(parseSubawardEvidence(malformed)).toBeNull();
    render(<SubawardCard citation={malformed} />);
    expect(screen.getByRole("alert")).toHaveTextContent("could not be read");
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("opens the typed evidence reader through the ordinary receipt panel", () => {
    function Trigger() {
      const { openPanel } = useContext(CitationPanelContext);
      return <button onClick={() => openPanel(fid)}>Inspect link</button>;
    }
    render(<CitationPanelProvider citations={{ [fid]: citation }}><Trigger /></CitationPanelProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Inspect link" }));
    expect(screen.getByText("Subaward Link Evidence")).toBeVisible();
    expect(screen.getByText("10977 REL 1")).toBeVisible();
    expect(screen.queryByText("Unknown citation kind.")).toBeNull();
    expect(screen.queryByTestId("official-source")).toBeNull();
  });

  it("keeps the inference and prime-award distinction in copied footnotes", () => {
    const input = footnoteInputFromCitation(citation, fid, {});
    expect(input.sourceLabel).toContain("medium-confidence program-link inference");
    expect(input.sourceLabel).toContain("prime-award context");
    expect(input.valueText).toBeFalsy();
  });
});
