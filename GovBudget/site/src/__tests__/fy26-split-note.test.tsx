/**
 * fy26-split-note.test.tsx — ROADMAP #81: <Fy26SplitNote> moved out of
 * program-figures.tsx (server-tainted via <CoverageNote> → lib/coverage.ts)
 * into its own client-safe module, so both /feed/ card trees and
 * /program/{peBli}/ render the ONE component. The #50 contract it carries is
 * still pinned end-to-end by program-figures.test.tsx ("FY2026
 * discretionary/reconciliation split"); this file pins the module itself.
 */

import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";

import { Fy26SplitNote } from "@/components/fy26-split-note";
import type { Fy26Split } from "@/lib/data";

const SPLIT: Fy26Split = {
  disc_k: 10_000,
  recon_k: 29_426,
  total_k: 39_426,
  recon_share: 0.746,
  disc_pct_change: -20.5,
  has_reconciliation: true,
  disc: {
    v: 10_000,
    units: "USD thousands",
    dataset: "budget_lines",
    fid: "1".repeat(16),
    public_id: "11111111",
    basis: "toa",
    fy: 2026,
    measure: "disc-request",
    edition: 2026,
  },
  reconciliation: {
    v: 29_426,
    units: "USD thousands",
    dataset: "budget_lines",
    fid: "2".repeat(16),
    public_id: "22222222",
    basis: "toa",
    fy: 2026,
    measure: "reconciliation-request",
    edition: 2026,
  },
};

describe("<Fy26SplitNote>", () => {
  it("renders the recon-share chip, both addends as their OWN cited figures, and the discretionary rate", () => {
    const { container } = render(<Fy26SplitNote split={SPLIT} />);
    expect(container.querySelector('[data-note-kind="scope"]')).not.toBeNull();
    expect(container.querySelector("[data-fy26-recon-chip]")!.textContent).toBe(
      "74.6% reconciliation",
    );
    const disc = container.querySelector(`[data-fact-id="${"1".repeat(16)}"]`);
    expect(disc).toHaveAttribute("data-measure", "disc-request");
    const recon = container.querySelector(`[data-fact-id="${"2".repeat(16)}"]`);
    expect(recon).toHaveAttribute("data-measure", "reconciliation-request");
    expect(container.textContent).toContain(" discretionary + ");
    expect(container.textContent).toContain(" one-time reconciliation.");
    expect(container.querySelector("[data-fy26-disc-pct-change]")!.textContent).toContain(
      "Discretionary change vs FY2025 enacted: -20.5%.",
    );
  });

  it("omits the discretionary addend and the rate sentence when the sidecar carries neither", () => {
    const { container } = render(
      <Fy26SplitNote split={{ ...SPLIT, disc: null, disc_pct_change: null }} />,
    );
    expect(container.querySelector("[data-fy26-recon-chip]")).not.toBeNull();
    expect(container.textContent).not.toContain("discretionary +");
    expect(container.querySelector("[data-fy26-disc-pct-change]")).toBeNull();
  });

  it("renders nothing at all when the reconciliation figure is missing (defensive branch)", () => {
    const { container } = render(
      <Fy26SplitNote split={{ ...SPLIT, reconciliation: null }} />,
    );
    expect(container.innerHTML).toBe("");
  });
});
