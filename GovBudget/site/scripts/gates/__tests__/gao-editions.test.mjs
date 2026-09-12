/**
 * Unit tests for gate 21 leg (h8) — every rendered GAO assessment cites its
 * edition, and an older edition stands only on a ratified anchor for the
 * same program on the same page (ROADMAP #30, "and its predecessors").
 *
 * THE DEFECT THESE PIN. With three editions ingested, a page could render
 * GAO's 2023 paragraph about a program under a sentence that names no year,
 * cite it to the 2025 volume, or inherit the human verdict across a rename
 * (GBSD -> Sentinel) or across services (Air Force Sentinel -> Army Sentinel
 * Mods, the ROADMAP #55 species). Leg h1 only knows (product, slug) pairs a
 * person ratified; inherited items are by construction NOT in that set, so
 * without h8 they would either be refused wholesale or trusted blindly.
 *
 * Items are injected (like split-key-awards.test.mjs injects `programs`) so
 * the tests do not depend on a build.  Run via `npm test` (vitest).
 */

import { describe, it, expect } from "vitest";
import {
  checkGaoEditionItems,
  checkGaoInheritedCount,
} from "../program-skeleton.mjs";

const EDITIONS = new Map([
  ["GAO-25-107569", 2025],
  ["GAO-24-106831", 2024],
  ["GAO-23-106059", 2023],
]);
const RATIFIED = new Set(["GAO-25-107569 0101125F"]);
// What the exporter writes into gao_program_findings.json from
// gao_programs._SERVICE_FAMILY — the gate no longer keeps its own copy.
const FAMILIES = new Map([
  ["Air Force", "F"],
  ["Space Force", "F"],
  ["Army", "A"],
  ["Navy", "N"],
  ["Marine Corps", "N"],
  ["Joint", "J"],
  ["DOD", "J"],
]);

const sentence = (year) =>
  `GAO assessed LGM-35A Sentinel in its June ${year} Weapon Systems Annual ` +
  `Assessment, as an Air Force MDAP program.`;

const item = (over = {}) => ({
  kind: "assessment",
  product: "GAO-25-107569",
  program: "LGM-35A Sentinel",
  common: "Sentinel",
  service: "Air Force",
  editionYear: 2025,
  inheritedFrom: null,
  text: sentence(2025),
  ...over,
});
const prior = (over = {}) =>
  item({
    product: "GAO-24-106831",
    editionYear: 2024,
    inheritedFrom: "GAO-25-107569",
    text: sentence(2024),
    ...over,
  });

const run = (items, ratified = RATIFIED) =>
  checkGaoEditionItems({
    slug: "0101125F",
    items,
    ratified,
    editionYearByProduct: EDITIONS,
    serviceFamilies: FAMILIES,
  });

describe("gate 21 leg h8 — editions", () => {
  it("passes a ratified anchor with two inherited predecessors", () => {
    expect(
      run([
        item(),
        prior(),
        prior({ product: "GAO-23-106059", editionYear: 2023, text: sentence(2023) }),
      ]),
    ).toEqual([]);
  });

  it("fails an edition stamp that disagrees with the ingested edition of that product", () => {
    const errs = run([item({ editionYear: 2024 })]);
    expect(errs).toHaveLength(1);
    expect(errs[0]).toMatch(/h8.*stamps edition 2024.*is 2025/);
  });

  it("fails a sentence that does not name the edition", () => {
    const errs = run([
      item({ text: "GAO assessed LGM-35A Sentinel, as an Air Force MDAP program." }),
    ]);
    expect(errs).toHaveLength(1);
    expect(errs[0]).toMatch(/h8.*does not name its edition/);
  });

  it("fails a product that is not an ingested edition", () => {
    const errs = run([item({ product: "GAO-22-105230", text: sentence(2022) })]);
    expect(errs).toHaveLength(1);
    expect(errs[0]).toMatch(/h8.*not an ingested Weapon Systems Annual Assessment edition/);
  });

  it("fails an inherited item whose anchor is not ratified on this page", () => {
    const errs = run([prior()], new Set());
    expect(errs.some((e) => /h8.*no ratified crosswalk places on this page/.test(e))).toBe(true);
  });

  it("fails an inherited item with no rendered anchor for the same program", () => {
    const errs = run([prior()]); // ratified, but nothing rendered to inherit from
    expect(errs).toHaveLength(1);
    expect(errs[0]).toMatch(/h8.*no rendered anchor.*same program/);
  });

  it("fails inheritance across a rename", () => {
    const errs = run([
      item(),
      prior({ common: "GBSD", program: "Ground Based Strategic Deterrent (GBSD)" }),
    ]);
    expect(errs).toHaveLength(1);
    expect(errs[0]).toMatch(/h8.*same program/);
  });

  it("fails inheritance across services — the Sentinel Mods species", () => {
    const errs = run([item(), prior({ service: "Army" })]);
    expect(errs).toHaveLength(1);
    expect(errs[0]).toMatch(/h8.*same program/);
  });

  it("accepts Space Force inheriting from an Air Force assessment (one book family)", () => {
    expect(
      run([item({ service: "Space Force" }), prior({ service: "Air Force" })]),
    ).toEqual([]);
  });

  it("accepts DOD inheriting from Joint — GAO's two labels for one book family", () => {
    expect(run([item({ service: "Joint" }), prior({ service: "DOD" })])).toEqual(
      [],
    );
  });

  it("fails inheritance that flows forward in time", () => {
    const errs = run(
      [
        item({ product: "GAO-24-106831", editionYear: 2024, text: sentence(2024) }),
        item({ inheritedFrom: "GAO-24-106831" }),
      ],
      new Set(["GAO-24-106831 0101125F"]),
    );
    expect(errs).toHaveLength(1);
    expect(errs[0]).toMatch(/h8.*inherits from edition 2024.*newer ratified edition to older ones only/);
  });

  it("ignores report items", () => {
    expect(
      run([{ kind: "report", product: "GAO-24-106909", program: "F-35", text: "" }]),
    ).toEqual([]);
  });

  it("reads the family map from the sidecar, so a label it omits is its own family", () => {
    // The divergence this replaces: the gate's hand-copied map lacked DOD, so
    // the F-35's two labels read as two programs. With the map coming from
    // gao_programs, a label the exporter did not send cannot silently pass.
    const errs = checkGaoEditionItems({
      slug: "0101125F",
      items: [item({ service: "Joint" }), prior({ service: "DOD" })],
      ratified: RATIFIED,
      editionYearByProduct: EDITIONS,
      serviceFamilies: new Map([["Joint", "J"]]),
    });
    expect(errs).toHaveLength(1);
    expect(errs[0]).toMatch(/h8.*same program/);
  });
});

describe("gate 21 leg h8 — the inherited items actually render", () => {
  it("passes when the pages render every inherited item the sidecar counts", () => {
    expect(checkGaoInheritedCount({ rendered: 70, expected: 70 })).toEqual([]);
  });

  it("fails when the priors stop rendering while the sidecar still counts them", () => {
    const errs = checkGaoInheritedCount({ rendered: 0, expected: 70 });
    expect(errs).toHaveLength(1);
    expect(errs[0]).toMatch(/h8.*70 inherited.*render 0/);
  });

  it("fails a sidecar with no inherited_items rather than passing vacuously", () => {
    const errs = checkGaoInheritedCount({ rendered: 0, expected: NaN });
    expect(errs).toHaveLength(1);
    expect(errs[0]).toMatch(/h8.*no.*inherited_items/);
  });
});
