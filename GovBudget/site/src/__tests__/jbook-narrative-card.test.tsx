/**
 * JbookNarrativeCard tests (Phase 5F §2b — narrative citation card upgrade).
 *
 * Paged narrative citations (2,449 / 2,457) render like the jbook_pdf card:
 * PDF page render + passage-start bbox highlight + "Open official source at
 * p.N". Unpaged citations (8 OCR-hostile narratives) keep the original
 * non-paged card — never a fake location. ambiguous_first surfaces the
 * existing amber ambiguity note (via the shared PdfView).
 */

import { describe, it, expect, vi, beforeAll } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import React from "react";
import type { JbookNarrativeCitation } from "@/lib/data";
import { getCitation, getProgramDetails } from "@/lib/data";
import { getF15FamilyData } from "@/lib/f15-family-data";

const { getDocumentMock } = vi.hoisted(() => ({
  getDocumentMock: vi.fn(),
}));

vi.mock("pdfjs-dist", () => ({
  GlobalWorkerOptions: { workerSrc: "" },
  getDocument: getDocumentMock,
}));

import { JbookNarrativeCard } from "@/components/citation-panel/jbook-narrative-card";

function makeFakePdf() {
  const page = {
    getViewport: ({ scale }: { scale: number }) => ({
      width: 792 * scale,
      height: 612 * scale,
    }),
    render: () => ({ promise: Promise.resolve(), cancel: () => {} }),
  };
  return { getPage: async () => page };
}

function makeNarrative(
  sha: string,
  overrides: Partial<JbookNarrativeCitation> = {},
): JbookNarrativeCitation {
  return {
    kind: "jbook_narrative",
    amount_text: null,
    amount_thousands: null,
    bottom_pt: 231.855,
    cells: null,
    formula: null,
    hosted_pdf_url: `/pdfs/${sha}.pdf#page=54`,
    inputs: null,
    official_url: "https://example.mil/jbook.pdf#page=54",
    page_height: 612,
    page_number: 54,
    page_width: 792,
    query_body: null,
    recorded_value: null,
    resolution: "unique",
    retrieved_at: "2026-06-10T12:00:00Z",
    sha256: sha,
    sheet: null,
    top_pt: 221.855,
    units: null,
    x0: 23,
    x1: 580.93,
    xml_path: "ProgramElement[3]/Project[0]",
    ...overrides,
  };
}

beforeAll(() => {
  globalThis.ResizeObserver = class {
    private cb: ResizeObserverCallback;
    constructor(cb: ResizeObserverCallback) {
      this.cb = cb;
    }
    observe(el: Element) {
      this.cb(
        [{ contentRect: { width: 400 } } as unknown as ResizeObserverEntry],
        this as unknown as ResizeObserver,
      );
      void el;
    }
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
});

describe("JbookNarrativeCard — paged (§2b)", () => {
  it("renders the PDF page with the passage highlight and a page-anchored source link", async () => {
    getDocumentMock.mockReturnValue({
      promise: Promise.resolve(makeFakePdf()),
      destroy: () => Promise.resolve(),
    });
    render(<JbookNarrativeCard citation={makeNarrative("aa11".repeat(16))} />);

    // Paged variant marker + PDF render path.
    expect(screen.getByTestId("jbook-narrative-card")).toHaveAttribute(
      "data-paged",
      "true",
    );
    await waitFor(() => {
      expect(document.querySelector("canvas.pdf-page-fade.is-ready")).not.toBeNull();
    });
    // Passage-start highlight (shared pdf-view contract).
    expect(screen.getByTestId("pdf-highlight")).toBeInTheDocument();
    // "open official source at p.N" wording.
    expect(
      screen.getByText(/Open official source at p\.54/i),
    ).toBeInTheDocument();
    // xml_path locator stays on the card (narrative identity).
    expect(screen.getByText("ProgramElement[3]/Project[0]")).toBeInTheDocument();
  });

  it("shows the amber ambiguity note for ambiguous_first passages", async () => {
    getDocumentMock.mockReturnValue({
      promise: Promise.resolve(makeFakePdf()),
      destroy: () => Promise.resolve(),
    });
    render(
      <JbookNarrativeCard
        citation={makeNarrative("bb22".repeat(16), {
          resolution: "ambiguous_first",
        })}
      />,
    );
    await waitFor(() => {
      expect(screen.getByTestId("ambiguous-badge")).toBeInTheDocument();
    });
  });
});

describe("JbookNarrativeCard — unpaged (8 unresolved narratives)", () => {
  it("keeps the original non-paged card with no PDF render and no fake location", () => {
    render(
      <JbookNarrativeCard
        citation={makeNarrative("cc33".repeat(16), {
          hosted_pdf_url: null,
          page_number: null,
          page_width: null,
          page_height: null,
          top_pt: null,
          bottom_pt: null,
          x0: null,
          x1: null,
          resolution: null,
        })}
      />,
    );
    const card = screen.getByTestId("jbook-narrative-card");
    expect(card).not.toHaveAttribute("data-paged", "true");
    expect(document.querySelector("canvas")).toBeNull();
    expect(screen.queryByTestId("pdf-highlight")).toBeNull();
    // Original card affordances survive.
    expect(screen.getByText("J-book narrative text")).toBeInTheDocument();
    expect(
      screen.getByTestId("jbook-narrative-source-link"),
    ).toBeInTheDocument();
  });
});

describe("JbookNarrativeCard — verbatim page-local source passages", () => {
  it("shows the actual unpaged F-15EX retrofit passage with its XML anchor and original source", () => {
    const factId = "cb4796e48126e4a7";
    const family = getF15FamilyData();
    const citation = family.citations[factId] as JbookNarrativeCitation;
    const original = getProgramDetails("F015EX").narratives.find((item) => item.fact_id === factId)!;
    expect(citation.page_number).toBeNull();
    render(<JbookNarrativeCard citation={citation} />);
    const passage = screen.getByRole("region", { name: "Source passage" });
    expect(within(passage).getByRole("heading", { name: original.title })).toBeVisible();
    expect(passage.querySelector("p")?.textContent).toBe(original.body);
    expect(passage).toHaveAttribute("data-source-text", "narrative");
    expect(passage).toHaveAttribute("data-xml-path", citation.xml_path);
    expect(passage.querySelectorAll("[data-amount]")).toHaveLength(0);
    expect(screen.getByTestId("jbook-narrative-source-link")).toHaveAttribute("href", citation.official_url);
    expect(screen.queryByTestId("pdf-highlight")).toBeNull();
    const xmlLabel = screen.getByText("XML location");
    expect(passage.compareDocumentPosition(xmlLabel) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("enriches every family narrative by exact identity without mutating shared citation objects", () => {
    const family = getF15FamilyData();
    for (const record of family.records) for (const narrative of record.narratives) {
      const enriched = family.citations[narrative.factId] as JbookNarrativeCitation;
      const original = getCitation(narrative.factId) as JbookNarrativeCitation;
      expect(enriched.source_passage).toEqual({ title: narrative.title, body: narrative.body });
      expect(enriched).not.toBe(original);
      expect(original.source_passage).toBeUndefined();
      const { source_passage, ...unchanged } = enriched;
      expect(source_passage).toBeDefined();
      expect(unchanged).toEqual(original);
    }
  });

  it("keeps the paged PDF and highlight alongside a supplied source passage", async () => {
    getDocumentMock.mockReturnValue({ promise: Promise.resolve(makeFakePdf()), destroy: () => Promise.resolve() });
    render(<JbookNarrativeCard citation={makeNarrative("dd44".repeat(16), { source_passage: { title: "Source narrative", body: "First paragraph.\n\nSecond paragraph with $10 million in the quoted source." } })} />);
    expect(screen.getByTestId("jbook-source-passage").querySelector("p")?.textContent).toBe("First paragraph.\n\nSecond paragraph with $10 million in the quoted source.");
    await waitFor(() => expect(screen.getByTestId("pdf-highlight")).toBeInTheDocument());
    expect(screen.getByText(/Open official source at p\.54/i)).toBeInTheDocument();
  });

  it("treats markup in source text as quoted text, not executable HTML", () => {
    const body = "Text <script>window.untrusted = true</script> and <b>literal markup</b>.";
    render(<JbookNarrativeCard citation={makeNarrative("ee55".repeat(16), { hosted_pdf_url: null, page_number: null, source_passage: { title: "Literal source", body } })} />);
    const passage = screen.getByTestId("jbook-source-passage");
    expect(passage.querySelector("p")?.textContent).toBe(body);
    expect(passage.querySelector("script, b")).toBeNull();
  });
});
