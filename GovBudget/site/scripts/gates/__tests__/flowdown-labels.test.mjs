/**
 * Proof-it-can-fail for gate 22 leg (h) — the label legibility leg.
 *
 * The geometry below was measured on the DEPLOYED fiscalreceipts.com/flow/ on
 * 2026-09-10 (a build ahead of this branch). It is fixture data these helpers
 * must REJECT, not a claim about this branch: a helper that passes the shipped
 * 1440 boxes and the shipped 390 scroller is not measuring anything.
 */
import { describe, it, expect } from "vitest";
import {
  platedLabelFindings,
  valueNearestNodeFindings,
  redPixelsInBox,
  subtractRects,
  RED_MIN_CHROMA,
  MIN_LABELS_WITH_VISIBLE_NODE_390,
  isDeobligationRed,
  hairlineProbeFindings,
  HAIRLINE_SAMPLES,
  HAIRLINE_NEUTRAL_TAIL,
} from "../flowdown.mjs";

describe("platedLabelFindings", () => {
  const label = { id: "b:c:N", river: "budget FY2026", left: 297, top: 400, right: 456, bottom: 416, paintIndex: 900 };

  it("fails a label with no plate at all (the pre-fix render)", () => {
    const found = platedLabelFindings([label], []);
    expect(found).toHaveLength(1);
    expect(found[0]).toContain("b:c:N");
    expect(found[0]).toContain("no plate");
  });

  it("fails a plate that does not cover its label", () => {
    const plate = { id: "b:c:N", river: "budget FY2026", left: 297, top: 400, right: 430, bottom: 416, paintIndex: 899 };
    const found = platedLabelFindings([label], [plate]);
    expect(found).toHaveLength(1);
    expect(found[0]).toContain("does not cover");
  });

  it("fails a plate painted AFTER its label (it would hide the glyphs)", () => {
    const plate = { id: "b:c:N", river: "budget FY2026", left: 295, top: 399, right: 458, bottom: 417, paintIndex: 901 };
    expect(platedLabelFindings([label], [plate])[0]).toContain("painted after");
  });

  it("fails a plate that reaches a NEIGHBOURING label", () => {
    const neighbour = { id: "b:c:F", river: "budget FY2026", left: 297, top: 418, right: 440, bottom: 434, paintIndex: 902 };
    const plate = { id: "b:c:N", river: "budget FY2026", left: 295, top: 399, right: 458, bottom: 425, paintIndex: 899 };
    const found = platedLabelFindings([label, neighbour], [plate]);
    expect(found.some((f) => f.includes("covers a neighbouring label"))).toBe(true);
  });

  it("passes a plate that covers its own label and nothing else", () => {
    const plate = { id: "b:c:N", river: "budget FY2026", left: 295, top: 399.5, right: 458, bottom: 416.5, paintIndex: 899 };
    expect(platedLabelFindings([label], [plate])).toEqual([]);
  });

  // ── the plate may not notch a DIFFERENT node's magnitude bar (R-21a-3) ──
  // Measured 2026-09-12 at 1440 on this branch: 18 of 60 plates overlapped
  // another node's bar, 4,946 px² — of which 4,458 px² was the LABEL's own
  // box, not the plate padding, so shrinking the padding could not reach 0.
  const downstreamBar = { id: "b:ba:F|3600F|05", river: "budget FY2026", left: 420, top: 300, right: 442, bottom: 500 };

  it("fails a plate that notches another node's magnitude bar", () => {
    const plate = { id: "b:c:N", river: "budget FY2026", left: 295, top: 399.5, right: 458, bottom: 416.5, paintIndex: 899 };
    const found = platedLabelFindings([label], [plate], [downstreamBar]);
    expect(found.some((f) => f.includes("notches"))).toBe(true);
    expect(found.join(" ")).toContain("b:ba:F|3600F|05");
  });

  it("passes a plate SPLIT around that bar — the bar itself covers the gap", () => {
    const parts = [
      { id: "b:c:N", river: "budget FY2026", left: 295, top: 399.5, right: 420, bottom: 416.5, paintIndex: 899 },
      { id: "b:c:N", river: "budget FY2026", left: 442, top: 399.5, right: 458, bottom: 416.5, paintIndex: 899 },
    ];
    expect(platedLabelFindings([label], parts, [downstreamBar])).toEqual([]);
  });

  it("fails a split plate whose gap is NOT filled by a bar", () => {
    const parts = [
      { id: "b:c:N", river: "budget FY2026", left: 295, top: 399.5, right: 420, bottom: 416.5, paintIndex: 899 },
      { id: "b:c:N", river: "budget FY2026", left: 442, top: 399.5, right: 458, bottom: 416.5, paintIndex: 899 },
    ];
    const found = platedLabelFindings([label], parts, []);
    expect(found).toHaveLength(1);
    expect(found[0]).toContain("does not cover");
  });

  it("never treats a label's OWN bar as the excuse for an uncovered gap", () => {
    const ownBar = { ...downstreamBar, id: "b:c:N" };
    const parts = [
      { id: "b:c:N", river: "budget FY2026", left: 295, top: 399.5, right: 420, bottom: 416.5, paintIndex: 899 },
      { id: "b:c:N", river: "budget FY2026", left: 442, top: 399.5, right: 458, bottom: 416.5, paintIndex: 899 },
    ];
    expect(platedLabelFindings([label], parts, [ownBar])[0]).toContain("does not cover");
  });
});

describe("subtractRects", () => {
  const area = (rs) => rs.reduce((n, r) => n + r.w * r.h, 0);

  it("returns the rect untouched when nothing overlaps it", () => {
    const r = { x: 0, y: 0, w: 10, h: 4 };
    expect(subtractRects(r, [{ x: 50, y: 0, w: 10, h: 4 }])).toEqual([r]);
  });

  it("splits a label strip crossing a node bar into the two sides", () => {
    const parts = subtractRects({ x: 0, y: 0, w: 100, h: 14 }, [{ x: 40, y: -5, w: 20, h: 30 }]);
    expect(area(parts)).toBe(80 * 14);
    for (const p of parts) expect(p.x + p.w <= 40 || p.x >= 60).toBe(true);
  });

  it("keeps the tail beyond a bar the label crosses entirely", () => {
    // b:a:F|3600F at 1440 crosses one bar whole and clips a second: clamping
    // the plate at the first bar would leave that tail unplated.
    const parts = subtractRects({ x: 0, y: 0, w: 100, h: 14 }, [
      { x: 20, y: -5, w: 20, h: 30 },
      { x: 70, y: -5, w: 20, h: 30 },
    ]);
    expect(area(parts)).toBe(60 * 14);
    expect(parts.some((p) => p.x >= 90)).toBe(true);
  });

  it("returns nothing when a hole swallows the rect", () => {
    expect(subtractRects({ x: 10, y: 10, w: 5, h: 5 }, [{ x: 0, y: 0, w: 100, h: 100 }])).toEqual([]);
  });

  it("leaves a partial-height overlap covered above and below", () => {
    const parts = subtractRects({ x: 0, y: 0, w: 10, h: 10 }, [{ x: 4, y: 4, w: 2, h: 2 }]);
    expect(area(parts)).toBe(100 - 4);
  });
});

describe("MIN_LABELS_WITH_VISIBLE_NODE_390", () => {
  it("is the dated floor, never lowered to fit a red run", () => {
    // Measured 24 on 2026-09-12 (leg h2, this branch's payload). The floor is
    // a non-vacuity guard: a real drop below it means the leg stopped
    // measuring and needs re-basing, not a smaller number here.
    expect(MIN_LABELS_WITH_VISIBLE_NODE_390).toBe(5);
    expect(MIN_LABELS_WITH_VISIBLE_NODE_390).toBeGreaterThanOrEqual(5);
  });
});

describe("valueNearestNodeFindings", () => {
  // Real 390x844 geometry: the node bar is fully inside the scroll box
  // (278..293 against 16..374) and the value is 82px past its right edge.
  const shipbuilding = {
    id: "b:a:N|1611N",
    anchor: "s",
    node: { left: 278, right: 293 },
    name: { left: 297, right: 456 },
    value: { left: 432, right: 456 },
    visible: { left: 16, right: 374 },
  };

  it("fails the shipped 390 case BOTH ways: far-side value and off-screen value", () => {
    const found = valueNearestNodeFindings([shipbuilding]);
    expect(found).toHaveLength(2);
    expect(found.join(" ")).toContain("b:a:N|1611N");
    expect(found.join(" ")).toContain("value is not the half nearest its node");
    expect(found.join(" ")).toContain("82");
  });

  it("fails ordering alone when the whole label is on screen", () => {
    const found = valueNearestNodeFindings([
      { ...shipbuilding, visible: { left: 16, right: 900 } },
    ]);
    expect(found).toHaveLength(1);
    expect(found[0]).toContain("value is not the half nearest its node");
  });

  it("fails the cut alone when the value is the near half but still off-screen", () => {
    const found = valueNearestNodeFindings([
      {
        ...shipbuilding,
        node: { left: 340, right: 355 },
        name: { left: 359, right: 518 },
        value: { left: 359, right: 383 },
      },
    ]);
    expect(found).toHaveLength(1);
    expect(found[0]).toContain("9px of the");
  });

  it("passes value-first ordering at 390 (the fix)", () => {
    const fixed = {
      ...shipbuilding,
      value: { left: 297, right: 321 },
      name: { left: 297, right: 456 },
    };
    expect(valueNearestNodeFindings([fixed])).toEqual([]);
  });

  it("passes an end-anchored label, whose value already ends at the node face", () => {
    expect(
      valueNearestNodeFindings([
        {
          id: "s:2025:f:BOEING",
          anchor: "e",
          node: { left: 700, right: 718 },
          name: { left: 520, right: 696 },
          value: { left: 644, right: 696 },
          visible: { left: 16, right: 900 },
        },
      ]),
    ).toEqual([]);
  });
});

describe("redPixelsInBox", () => {
  /** 6x4 RGBA white image with one pixel set to `rgb` at (2,1). */
  function png(rgb = [0xb9, 0x1c, 0x1c]) {
    const data = Buffer.alloc(6 * 4 * 4, 255);
    const i = (1 * 6 + 2) * 4;
    data[i] = rgb[0];
    data[i + 1] = rgb[1];
    data[i + 2] = rgb[2];
    return { width: 6, height: 4, data };
  }

  it("pins the discriminator constant the gate ships", () => {
    expect(RED_MIN_CHROMA).toBe(40);
  });

  it("finds the un-composited de-obligation red crossing a label box", () => {
    expect(redPixelsInBox(png(), { left: 1, top: 0, right: 4, bottom: 3 })).toBe(1);
  });

  it("finds the COMPOSITED hairline — the colour the renderer actually paints", () => {
    // .flow-band { opacity: 0.55 } (globals.css:833), so a single
    // de-obligation hairline never reaches #b91c1c on screen: over white it
    // renders rgb(216,130,130). A probe calibrated on the un-composited token
    // counts zero of these and passes the PRE-FIX render unchanged — the
    // 2026-09-12 review measured exactly that. r - max(g,b) = 86 here, and
    // 0.55 x (185 - 28) = 86 over ANY backdrop, which is why the rule is a
    // redness lead and not a distance to one colour.
    expect(redPixelsInBox(png([216, 130, 130]), { left: 1, top: 0, right: 4, bottom: 3 })).toBe(1);
  });

  it("returns 0 when the box is elsewhere", () => {
    expect(redPixelsInBox(png(), { left: 4, top: 0, right: 6, bottom: 4 })).toBe(0);
  });

  it("ignores a 4%-opacity tint of the same red over the plate (the fix)", () => {
    // The pixel the plate produces where a hairline runs behind it.
    expect(redPixelsInBox(png([250, 246, 246]), { left: 0, top: 0, right: 6, bottom: 4 })).toBe(0);
  });

  it("ignores the plate, the halo and the glyphs — every neutral pixel", () => {
    for (const neutral of [[255, 255, 255], [250, 250, 250], [10, 10, 12], [64, 64, 70]]) {
      expect(redPixelsInBox(png(neutral), { left: 0, top: 0, right: 6, bottom: 4 })).toBe(0);
    }
  });
});

// ── the per-river hairline probe: leg h1's positive control ────────────────
//
// WHY THIS EXISTS. The whole-canvas `warmRedOnCanvas > 0` guard cannot see the
// de-obligation hairlines at all: measured 2026-09-18 against site/out at
// 1440x900, deleting every one of the 20 hairlines moved it 218,807 -> 216,360
// (1.1 %), because --flow-class-notcomp vermillion dominates the count. A guard
// that barely moves when the thing it guards is deleted is not a control. This
// probe samples the hairline PATHS themselves, per river.
describe("isDeobligationRed", () => {
  it("accepts the composited hairline — #b91c1c at opacity 0.55 over white", () => {
    // .flow-band { opacity: 0.55 }; 0.55 x rgb(185,28,28) + 0.45 x white.
    expect(isDeobligationRed([216, 130, 130])).toBe(true);
  });

  it("rejects the not_competed vermillion that swamps the whole-canvas count", () => {
    // --flow-class-notcomp #d55e00 = rgb(213,94,0) at 0.55 over white:
    // lead 65 clears RED_MIN_CHROMA, so a lead-only probe calls a ribbon a
    // hairline. Its tail does not: |g-b| = 52 against a 0.25 x 65 = 16 budget.
    // Measured on site/out 2026-09-18: with every hairline's stroke removed,
    // a lead-only probe still found 19 of 20 hairline paths "lit" by the
    // ribbons behind them; with the tail test, 20 of 20 went blind.
    expect(isDeobligationRed([232, 166, 115])).toBe(false);
  });

  it("accepts a hairline composited over a vermillion ribbon", () => {
    // The hairlines cross the ribbons; 0.55 x #b91c1c over rgb(232,166,115).
    expect(isDeobligationRed([206, 90, 67])).toBe(true);
  });

  it("rejects the plate, the halo and every neutral pixel", () => {
    for (const c of [[255, 255, 255], [250, 246, 246], [10, 10, 12], [64, 64, 70]]) {
      expect(isDeobligationRed(c)).toBe(false);
    }
  });

  it("rejects a pixel off the edge of the PNG", () => {
    expect(isDeobligationRed(null)).toBe(false);
  });
});

describe("hairlineProbeFindings", () => {
  /** A `w`x`h` white PNG with `paint` (a map "x,y" -> [r,g,b]) stamped on. */
  function png(w, h, paint = {}) {
    const data = Buffer.alloc(w * h * 4, 255);
    for (const [k, rgb] of Object.entries(paint)) {
      const [x, y] = k.split(",").map(Number);
      const i = (y * w + x) * 4;
      data[i] = rgb[0];
      data[i + 1] = rgb[1];
      data[i + 2] = rgb[2];
    }
    return { width: w, height: h, data };
  }
  const composited = [216, 130, 130];
  /** four sample points along one hairline */
  const points = [[1, 1], [2, 1], [3, 1], [4, 1]];

  it("passes a hairline whose sampled pixels decode as de-obligation red", () => {
    const image = png(8, 4, { "1,1": composited, "3,1": composited });
    const out = hairlineProbeFindings("spend FY2025", [{ id: "e12", points }], image);
    expect(out.findings).toEqual([]);
    expect(out.lit).toEqual([2]);
  });

  it("FINDS a hairline the PNG does not show — the path is there, the paint is not", () => {
    // The gate's own failure mode: the screenshot, the scroll or the
    // SVG->PNG transform silently stopped lining up, so every sampled pixel
    // is the white page. Nothing in the whole-canvas count would notice.
    const out = hairlineProbeFindings("spend FY2025", [{ id: "e12", points }], png(8, 4));
    expect(out.findings).toHaveLength(1);
    expect(out.findings[0]).toContain("e12");
    expect(out.findings[0]).toContain("0 of 4");
    expect(out.lit).toEqual([0]);
  });

  it("FINDS a hairline whose sampled pixels are warm red but BELOW the chroma lead", () => {
    // A 4 %-opacity ghost of the same red: rgb(250,246,246), lead 4. This is
    // what a hairline hidden behind an opaque plate leaves, and it must not
    // be accepted as proof the hairline itself rendered.
    const ghost = png(8, 4, { "1,1": [250, 246, 246], "2,1": [250, 246, 246], "3,1": [250, 246, 246], "4,1": [250, 246, 246] });
    const out = hairlineProbeFindings("spend FY2025", [{ id: "e12", points }], ghost);
    expect(out.findings).toHaveLength(1);
    expect(out.findings[0]).toContain("0 of 4");
  });

  it("FINDS a hairline lit only by the vermillion ribbon behind it", () => {
    const ribbon = png(8, 4, { "1,1": [232, 166, 115], "2,1": [232, 166, 115], "3,1": [232, 166, 115], "4,1": [232, 166, 115] });
    expect(hairlineProbeFindings("spend FY2025", [{ id: "e12", points }], ribbon).findings).toHaveLength(1);
  });

  it("reports one finding per blind hairline and names the river", () => {
    const image = png(8, 4, { "1,1": composited });
    const out = hairlineProbeFindings(
      "spend FY2025",
      [{ id: "e1", points }, { id: "e2", points: [[6, 3]] }, { id: "e3", points: [[7, 3]] }],
      image,
    );
    expect(out.findings).toHaveLength(2);
    expect(out.findings.every((f) => f.includes("spend FY2025"))).toBe(true);
    expect(out.lit).toEqual([1, 0, 0]);
  });

  it("pins the sample count and the tail ratio the gate ships", () => {
    expect(HAIRLINE_SAMPLES).toBe(48);
    expect(HAIRLINE_NEUTRAL_TAIL).toBe(0.25);
  });
});
