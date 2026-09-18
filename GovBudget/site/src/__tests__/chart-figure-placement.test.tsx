/**
 * Task 21d fix round 1 — <figcaption> placement inside <ChartFigure>.
 *
 * Gate 16's index-fold leg (floor 2026-09-18, DO NOT LOWER) requires the
 * first data row inside [data-first-data] to start inside the initial
 * viewport at 1440x900 AND 390x844. /lineage/ failed at 390 by 205px, and
 * 384px of that was LineageFlow's own prose rendered ABOVE its diagram: the
 * ChartFigure figcaption (260px at 390) plus the legend row (108px) — the
 * same "caveat above the data" defect Task 21d exists to fix, one component
 * down.
 *
 * HTML's <figure> content model allows the <figcaption> as the FIRST or the
 * LAST child, so the fix is an opt-in prop rather than a wrapper. This file
 * pins both halves of that contract:
 *   - the default is unchanged (caption first) for every other caller;
 *   - captionPlacement="last" moves ONLY the order — same text, same id,
 *     same data-chart-desc, so gate 2 leg (ch) and gate 6 (c1) see exactly
 *     what they saw before;
 *   - LineageFlow's stated-families figure takes the opt-in. Its legend row
 *     stays ABOVE the diagram: with the caption alone moved the first ribbon
 *     lands at 781 of 844 at 390 (measured on this branch), which clears the
 *     floor, and a key belongs before the picture it decodes.
 */

import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import React from "react";

import { ChartFigure, chartDescId } from "@/components/chart-figure";
import { LineageFlow } from "@/components/lineage/lineage-flow";
import type {
  LineageFlowFamily,
  LineageFlowPayload,
} from "@/lib/lineage-flow";

const DESC = "What the picture shows and what to take from it.";

function renderFigure(props: { captionPlacement?: "first" | "last" } = {}) {
  const { container } = render(
    <ChartFigure id="demo" description={DESC} {...props}>
      <svg data-testid="the-chart" aria-describedby={chartDescId("demo")} />
    </ChartFigure>,
  );
  return container.querySelector("figure")!;
}

describe("ChartFigure caption placement", () => {
  it("puts the figcaption FIRST by default — every existing caller is unchanged", () => {
    const fig = renderFigure();
    expect(fig.firstElementChild!.tagName).toBe("FIGCAPTION");
  });

  it("puts the figcaption LAST with captionPlacement=\"last\"", () => {
    const fig = renderFigure({ captionPlacement: "last" });
    expect(fig.lastElementChild!.tagName).toBe("FIGCAPTION");
    expect(fig.firstElementChild!.tagName).not.toBe("FIGCAPTION");
  });

  it("keeps the caption text, its id and its data-chart-desc identical in both placements; DEFAULT stays byte-identical, LAST gains only a top margin", () => {
    const first = renderFigure().querySelector("figcaption")!;
    const last = renderFigure({ captionPlacement: "last" }).querySelector(
      "figcaption",
    )!;
    for (const cap of [first, last]) {
      expect(cap.textContent).toBe(DESC);
      expect(cap.id).toBe(chartDescId("demo"));
      expect(cap.hasAttribute("data-chart-desc")).toBe(true);
    }
    // The DEFAULT ("first") placement's caption is byte-identical to before
    // fix round 2 — no new class, no new margin.
    expect(first.outerHTML).toBe(
      `<figcaption id="${chartDescId("demo")}" data-chart-desc="" class="mb-2 text-xs leading-5 text-muted-foreground ">${DESC}</figcaption>`,
    );
    // Task 21d fix round 2, item 5: "last" abutted the preceding element
    // with a 0px gap (mb-2 is a BOTTOM margin). It gains `mt-3`; everything
    // else — tag, id, data-chart-desc, text — stays identical to "first",
    // so only the class attribute may differ between the two.
    expect(last.className).toBe(
      `mb-2 mt-3 text-xs leading-5 text-muted-foreground `,
    );
    const stripClass = (html: string) => html.replace(/\sclass="[^"]*"/, "");
    expect(stripClass(last.outerHTML)).toBe(stripClass(first.outerHTML));
  });

  it("keeps the chart and the table view in their existing order under both placements", () => {
    const withTable = (captionPlacement?: "first" | "last") => {
      const { container } = render(
        <ChartFigure
          id="demo2"
          description={DESC}
          captionPlacement={captionPlacement}
          table={<table data-testid="the-table" />}
        >
          <svg data-testid="the-chart" />
        </ChartFigure>,
      );
      return Array.from(
        container.querySelector("figure")!.children,
      ).map((el) => el.tagName);
    };
    expect(withTable()).toEqual(["FIGCAPTION", "svg", "TABLE"]);
    expect(withTable("last")).toEqual(["svg", "TABLE", "FIGCAPTION"]);
  });
});

// ── LineageFlow: the caller the fold measurement is about ────────────────────

function makeFamily(): LineageFlowFamily {
  return {
    family_id: 1,
    root: "PE 0601101E",
    has_split: false,
    cyclic: false,
    steps: 2,
    width: 334,
    height: 80,
    nodes: [
      {
        pe: "PE 0601101E",
        title: "Defense Research Sciences",
        short: "Defense Research Sci…",
        step: 0,
        x0: 0,
        x1: 120,
        y0: 10,
        y1: 50,
        resolved: true,
      },
      {
        pe: "PE 0601102E",
        title: "Successor Line",
        short: "Successor Line",
        step: 1,
        x0: 200,
        x1: 320,
        y0: 10,
        y1: 50,
        resolved: true,
      },
    ],
    edges: [
      {
        s: 0,
        t: 1,
        relation: "realigned",
        fy: 2026,
        confidence: "stated",
        fid: "fact-1",
        g: [24, 30, 24, 30],
      },
    ],
  };
}

function makePayload(): LineageFlowPayload {
  return {
    schema_version: 1,
    ribbon_w: 6,
    node_w: 120,
    node_h: 40,
    amount_fy: 2026,
    amount_measure: "request",
    counts: {
      stated_edges: 1,
      inferred_edges: 0,
      families: 1,
      identities: 2,
      identities_linked: 2,
      identities_unresolved: 0,
      identities_with_amount: 0,
    },
    families: [makeFamily()],
    candidates: [],
  };
}

describe("LineageFlow: the stated-families figure", () => {
  it("renders its figcaption AFTER the diagrams, so the picture is what a reader meets first", () => {
    const { container } = render(
      <LineageFlow payload={makePayload()} linkablePes={["PE 0601101E"]} />,
    );
    const fig = container.querySelector('figure[data-chart="lineage-graph"]')!;
    const cap = fig.querySelector(":scope > figcaption")!;
    const diagrams = fig.querySelector('[data-lineage-diagram=""]')!;
    expect(cap).toBeTruthy();
    expect(diagrams).toBeTruthy();
    // DOCUMENT_POSITION_FOLLOWING === 4: the caption comes after the diagram.
    expect(
      diagrams.compareDocumentPosition(cap) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("keeps the caption a direct, visible child of the figure — gate 6 (c1) and gate 2 (ch)", () => {
    const { container } = render(
      <LineageFlow payload={makePayload()} linkablePes={[]} />,
    );
    const fig = container.querySelector('figure[data-chart="lineage-graph"]')!;
    const cap = fig.querySelector(":scope > figcaption")!;
    expect(cap.id).toBe(chartDescId("lineage-graph"));
    expect(cap.hasAttribute("data-chart-desc")).toBe(true);
    // Never inside a <details>: that would hide it from sighted readers.
    expect(cap.closest("details")).toBeNull();
    expect(cap.textContent).toContain("every ribbon is drawn at one");
  });

  it("keeps the LEGEND above the diagrams — the caption is the only thing that moved", () => {
    // Measured, not assumed (next dev, Playwright, 2026-09-18, this branch):
    // moving the caption alone takes /lineage/'s first ribbon from 1,049 to
    // 781 at 390x844 and from 829 to 561 at 1440x900. 63px of headroom at
    // 390 clears gate 16's floor, so the legend stays where a reader needs
    // it — above the picture whose colours and dashes it decodes. Moving it
    // too was the prepared fallback and is not needed; this test records
    // that, so a later "tidy-up" that demotes the key has to re-measure.
    const { container } = render(
      <LineageFlow payload={makePayload()} linkablePes={[]} />,
    );
    const fig = container.querySelector('figure[data-chart="lineage-graph"]')!;
    const legend = fig.querySelector('[data-testid="lineage-legend"]')!;
    const diagrams = fig.querySelector('[data-lineage-diagram=""]')!;
    const cap = fig.querySelector(":scope > figcaption")!;
    expect(legend).toBeTruthy();
    expect(
      legend.compareDocumentPosition(diagrams) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      legend.compareDocumentPosition(cap) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("leaves the CANDIDATE figure's caption first — its honesty text is read before the diagrams it labels", () => {
    const payload = makePayload();
    payload.candidates = [
      {
        basis: "same-agency RDT&E BA maturation",
        cyclic: false,
        steps: 2,
        width: 334,
        height: 80,
        nodes: makeFamily().nodes,
        edges: [
          {
            s: 0,
            t: 1,
            relation: "matured_ba",
            fy: 2026,
            confidence: "inferred",
            fid: null,
            g: [24, 30, 24, 30],
          },
        ],
      },
    ];
    payload.counts.inferred_edges = 1;
    const { container } = render(
      <LineageFlow payload={payload} linkablePes={[]} />,
    );
    const fig = container.querySelector(
      'figure[data-chart="lineage-candidates"]',
    )!;
    expect(fig.firstElementChild!.tagName).toBe("FIGCAPTION");
    // …and still outside the <details> that hides only the pictures.
    expect(fig.querySelector(":scope > figcaption")!.closest("details")).toBeNull();
  });
});
