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
  /** 6x4 RGBA image with a #b91c1c pixel at (2,1). */
  function png() {
    const data = Buffer.alloc(6 * 4 * 4, 255);
    const at = (x, y) => (y * 6 + x) * 4;
    data[at(2, 1)] = 0xb9;
    data[at(2, 1) + 1] = 0x1c;
    data[at(2, 1) + 2] = 0x1c;
    return { width: 6, height: 4, data };
  }

  it("finds the de-obligation red crossing a label box", () => {
    expect(redPixelsInBox(png(), { left: 1, top: 0, right: 4, bottom: 3 }, [0xb9, 0x1c, 0x1c], 40)).toBe(1);
  });

  it("returns 0 when the box is elsewhere", () => {
    expect(redPixelsInBox(png(), { left: 4, top: 0, right: 6, bottom: 4 }, [0xb9, 0x1c, 0x1c], 40)).toBe(0);
  });

  it("ignores a 4%-opacity tint of the same red over the plate (the fix)", () => {
    const p = png();
    const i = (1 * 6 + 2) * 4;       // the red pixel, now behind an opaque plate
    p.data[i] = 250; p.data[i + 1] = 246; p.data[i + 2] = 246;
    expect(redPixelsInBox(p, { left: 0, top: 0, right: 6, bottom: 4 }, [0xb9, 0x1c, 0x1c], 40)).toBe(0);
  });
});
