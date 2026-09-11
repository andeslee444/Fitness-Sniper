/**
 * Unit tests for gate 21 leg (l) — the successor clause checked against the
 * page's OWN narratives (ROADMAP #32(b) residue, 2026-09-05).
 *
 * Proof-it-can-fail, on synthetic sidecars: the retired corpus-wide denial
 * fails (quoting the contradicting narrative), a narrative left unpointed-at
 * fails, a pointer at nothing fails, a pointer beside a rail fails, an
 * exporter flag that contradicts its own narratives fails, and a population
 * under the floor fails. The scanner is exercised on the four REAL sentences
 * that made the old note false (2900, 2176, FET000, 0601101E) and on four
 * shapes it must NOT read as a forward pointer.
 *
 * Synthetic slugs so nothing resolves in site/out; noteTexts is injected.
 * Run via `npm test` (vitest).
 */

import { describe, it, expect } from "vitest";
import {
  FY2026_SUCCESSOR_DENIAL_RETIRED,
  FY2026_NARRATIVE_POINTER,
  MIN_NARRATIVE_FORWARD_POINTER_PAGES,
  narrativeForwardPointers,
  pageUniverse,
  runNarrativeSuccessorLeg,
} from "../program-skeleton.mjs";

const DENIAL =
  "No successor is linked for this line: this site's program-lineage layer holds no keyed edge pointing forward from here.";
const POINTER =
  "That is an absence in this site's lineage layer, not a finding about the program: if the J-book narrative on this page describes a realignment, it is quoted below in the document's own words, and this note does not restate it.";
const HEAD =
  "No FY2026 R-1/P-1 request line for this program element. The FY2026 President's Budget request workbook carries no FY2026 line for it; its last workbook figure is FY2025. An absent line is not by itself an ending — PB2026 renumbered program elements at scale across the services and defense agencies, so this work may continue under a different number. ";
const LINEAGE_POINTER =
  "Where this line's funding went is recorded under Program Lineage below.";

const NARR = (body, kind = "description") => ({ kind, body, title: "" });

function absent({ narratives = [], successors = [] } = {}) {
  return {
    budget_lines: [{ fy: 2025, amount_thousands: 1000 }],
    details: [],
    narratives,
    lineage: successors.length
      ? { rail: { successors: successors.map((pe) => ({ pe, confidence: "stated" })) } }
      : undefined,
    fy2026_absent: {
      last_fy: 2025,
      jbook_fy2026_zero: false,
      has_successor: successors.length > 0,
      has_narrative: narratives.length > 0,
    },
  };
}

/** The note the component renders for a sidecar, with optional sabotage. */
function noteFor(d, { retired = false, pointer = null } = {}) {
  const fa = d.fy2026_absent;
  let tail;
  if (fa.has_successor) tail = LINEAGE_POINTER + (pointer ? " " + POINTER : "");
  else if (retired) tail = FY2026_SUCCESSOR_DENIAL_RETIRED;
  else tail = DENIAL + ((pointer ?? fa.has_narrative) ? " " + POINTER : "");
  return { absent: HEAD + tail, decade: null };
}

/**
 * A corpus: `n` no-rail pages whose narrative names LI T9901 (in the
 * universe), 3 no-rail pages with no narrative, 1 no-rail page with a
 * narrative that names nothing, 1 rail page. Returns {sidecars, notes}.
 */
function corpus(n, sabotage = {}) {
  const sidecars = new Map();
  const notes = new Map();
  sidecars.set("T9901", {});
  sidecars.set("0699999E", {});
  const add = (slug, d) => {
    sidecars.set(slug, d);
    notes.set(slug, noteFor(d, sabotage[slug] ?? {}));
  };
  for (let i = 0; i < n; i++) {
    const slug = `NR${String(i).padStart(3, "0")}`;
    add(slug, absent({
      narratives: [NARR(`Funding has been realigned out of LI ${slug} into LI T9901 starting in FY 2026.`)],
    }));
  }
  for (const slug of ["NN000", "NN001", "NN002"]) add(slug, absent());
  add("NP000", absent({ narratives: [NARR("This program develops sensors.", "mission")] }));
  add("NRAIL0", absent({
    narratives: [NARR("Efforts were transferred to PE 0699999E.", "mission")],
    successors: ["0699999E"],
  }));
  return { sidecars, notes };
}

function run({ sidecars, notes }) {
  const errors = [];
  const out = [];
  runNarrativeSuccessorLeg({
    errors,
    notes: out,
    sidecars,
    noteTexts: (slug) => notes.get(slug) ?? null,
  });
  return { errors, notes: out };
}

// ── the scanner ─────────────────────────────────────────────────────────────

describe("narrativeForwardPointers", () => {
  const universe = pageUniverse(
    new Map([["2361", {}], ["2136-OPN", {}], ["0303131F", {}], ["0601122E", {}], ["1203001SF", {}]]),
  );

  it("reads the four real sentences the old note was false against", () => {
    const cases = [
      ["2900", "Funding for Maritime Integrated Broadcast System (MIBS) has been realigned out of LI 2900 into LI 2361 starting in FY 2026.", "2361", "line"],
      ["2176", "NOTE: Effective FY 2026, all funding and programs within OPN Budget Line Item (BLI) 2176 moved into OPN BLI 2136 in support of the PE/BLI consolidation initiative.", "2136", "line"],
      ["FET000", "The Family of Advanced Beyond Line-of-Sight Terminals (FAB-T) Force Element Terminal (FET) program was transferred from Space Force (PE 1203001SF / WSC FET000 / Appropriation 3022 / PSF) to Air Force (PE 0303131F / WSC CVR000 / Appropriation 3010 / APAF).", "0303131F", "pe"],
      ["0601101E", "Beginning in FY 2026, efforts in this PE will be funded in PE 0601122E, Emerging Opportunities.", "0601122E", "pe"],
    ];
    for (const [slug, body, code, shape] of cases) {
      const got = narrativeForwardPointers({ narratives: [NARR(body)] }, slug, universe);
      expect(got.map((p) => p.code), slug).toEqual([code]);
      expect(got[0].shape, slug).toBe(shape);
      expect(got[0].sentence, slug).toContain(code);
    }
  });

  it("does not read this page, a source, present-tense funding, or an unknown code as a successor", () => {
    const d = (body) => ({ narratives: [NARR(body)] });
    // The destination IS this page: 0601122E is the successor, not a pointer
    // away from itself.
    expect(narrativeForwardPointers(d("IRST has been transferred to Program Element 0601122E."), "0601122E", universe)).toEqual([]);
    // "from" only — a predecessor, not a successor.
    expect(narrativeForwardPointers(d("Efforts were transferred from PE 1203001SF in FY 2024."), "X", universe)).toEqual([]);
    // Present tense "is funded in" is concurrent funding, not a move (the
    // real 0602303E sentence shape).
    expect(narrativeForwardPointers(d("Basic research for this program is funded in PE 0601122E, Project CCS-02."), "X", universe)).toEqual([]);
    // A code outside the page universe is not a pointer this site could key.
    expect(narrativeForwardPointers(d("Efforts were transferred to PE 0609999Z."), "X", universe)).toEqual([]);
    // An E3 composite member counts for its bare code.
    expect(narrativeForwardPointers(d("moved into OPN BLI 2136."), "X", universe).map((p) => p.code)).toEqual(["2136"]);
  });
});

// ── the leg ─────────────────────────────────────────────────────────────────

describe("gate 21 leg (l) — the successor clause against the page's own narratives", () => {
  it("passes a corpus whose notes claim only what the site holds and point at their prose", () => {
    const { errors, notes } = run(corpus(MIN_NARRATIVE_FORWARD_POINTER_PAGES));
    expect(errors).toEqual([]);
    expect(notes.join("\n")).toContain(`${MIN_NARRATIVE_FORWARD_POINTER_PAGES} no-rail`);
    expect(notes.join("\n")).toContain("0 retired");
  });

  it("FAILS a note that renders the retired corpus-wide denial, quoting the narrative that contradicts it", () => {
    const { errors } = run(corpus(MIN_NARRATIVE_FORWARD_POINTER_PAGES, { NR000: { retired: true } }));
    expect(errors.some((e) => e.includes("/program/NR000/") && e.includes("retired corpus-wide successor denial"))).toBe(true);
    expect(errors.some((e) => e.includes("into LI T9901"))).toBe(true);
  });

  it("FAILS the retired denial on a decade-only note too", () => {
    const c = corpus(MIN_NARRATIVE_FORWARD_POINTER_PAGES);
    c.sidecars.set("DEC00", { decade_series: {}, decade_absent: { has_successor: false } });
    c.notes.set("DEC00", { absent: null, decade: "No FY2026 R-1/P-1 workbook line. " + FY2026_SUCCESSOR_DENIAL_RETIRED });
    const { errors } = run(c);
    expect(errors.some((e) => e.includes("/program/DEC00/ decade-only note renders the retired"))).toBe(true);
  });

  it("FAILS a narrative that names a forward pointer the note does not send the reader to", () => {
    const { errors } = run(corpus(MIN_NARRATIVE_FORWARD_POINTER_PAGES, { NR001: { pointer: false } }));
    expect(errors.some((e) => e.includes("/program/NR001/") && e.includes("does not send the reader to the narrative") && e.includes("T9901"))).toBe(true);
  });

  it("FAILS a pointer at nothing, and a pointer beside a successor rail", () => {
    const { errors } = run(corpus(MIN_NARRATIVE_FORWARD_POINTER_PAGES, { NN000: { pointer: true }, NRAIL0: { pointer: true } }));
    expect(errors.some((e) => e.includes("/program/NN000/") && e.includes("points at nothing"))).toBe(true);
    expect(errors.some((e) => e.includes("/program/NRAIL0/") && e.includes("beside a successor rail"))).toBe(true);
  });

  it("FAILS an exporter flag that contradicts the sidecar's own narratives", () => {
    // leg (g) compares only last_fy between the two implementations, so
    // without this check has_narrative would reach the reader unchecked.
    const c = corpus(MIN_NARRATIVE_FORWARD_POINTER_PAGES);
    c.sidecars.get("NR002").fy2026_absent.has_narrative = false;
    const { errors } = run(c);
    expect(errors.some((e) => e.includes("/program/NR002/") && e.includes("has_narrative=false") && e.includes("ships 1 narrative(s)"))).toBe(true);
  });

  it("FAILS below the floor and says to re-measure, never to lower", () => {
    const { errors } = run(corpus(MIN_NARRATIVE_FORWARD_POINTER_PAGES - 1));
    expect(errors.some((e) => e.includes(`expected >= ${MIN_NARRATIVE_FORWARD_POINTER_PAGES}`) && /re-measure/i.test(e))).toBe(true);
  });

  it("uses the exact strings the component renders and retired", () => {
    expect(POINTER).toContain(FY2026_NARRATIVE_POINTER);
    expect(FY2026_SUCCESSOR_DENIAL_RETIRED).toBe(
      "No ingested budget document in this corpus states a successor for this line.",
    );
  });
});
