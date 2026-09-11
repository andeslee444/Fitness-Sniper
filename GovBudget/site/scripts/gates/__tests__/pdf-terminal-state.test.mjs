/**
 * Proof-can-fail for gate 4's PDF terminal-state sub-test.
 *
 * THE HOLE. Gate 4's Test 1 asserted `await page.$("canvas")` — and
 * pdf-view.tsx renders its <canvas> UNCONDITIONALLY (:483-494): it is in
 * the DOM while the skeleton says "Loading page 55…", it is in the DOM
 * with display:none while the degraded fallback shows, and it is in the
 * DOM when the page has rendered. So the assertion was true in all three
 * states, including the one the 2026-08-27 tri-persona review reported
 * ("Loading page 55…" forever) and deferred as unconfirmed. The gate could
 * neither confirm nor deny it.
 *
 * These tests pin the verdict function, including the case the old gate
 * called a pass.
 *
 * Run via `npm test` (vitest).
 */
import { describe, it, expect } from "vitest";
import { pdfPanelVerdict } from "../clickthrough.mjs";

describe("pdfPanelVerdict", () => {
  it("a rendered page passes", () => {
    const v = pdfPanelVerdict({ terminal: "ready", stillLoading: false });
    expect(v.ok).toBe(true);
    expect(v.reason).toMatch(/is-ready/);
  });

  it("PROOF IT CAN FAIL: a panel still showing the loading skeleton fails", () => {
    // This is the exact state the old `page.$("canvas")` check passed.
    const v = pdfPanelVerdict({ terminal: null, stillLoading: true });
    expect(v.ok).toBe(false);
    expect(v.reason).toMatch(/Loading page/);
  });

  it("the degraded fallback fails HERE — this server holds the PDFs itself", () => {
    const v = pdfPanelVerdict({ terminal: "degraded", stillLoading: false });
    expect(v.ok).toBe(false);
    expect(v.reason).toMatch(/degraded/);
  });

  it("neither terminal nor loading fails — the PDF view did not mount", () => {
    const v = pdfPanelVerdict({ terminal: null, stillLoading: false });
    expect(v.ok).toBe(false);
    expect(v.reason).toMatch(/did not mount/);
  });
});
