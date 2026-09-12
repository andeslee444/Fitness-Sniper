/**
 * Proof-it-can-fail tests for gate 8 leg (o) — runSectionSidecarLeg
 * (ROADMAP #88). Every rendered /feed/ section must have a shipped
 * json/feed-sections/{event_type}.json whose `cards` are exactly the cards
 * the page did NOT render (total − shown), all of that event type, each
 * carrying the pre-resolved company_slug / has_program_page the client
 * twin renders from. The leg reads the static HTML's truncation note
 * (data-feed-shown / data-feed-total) and the SHIPPED sidecar directory —
 * `sectionsDir` is a parameter so these tests point it at a temp dir.
 *
 * Run via `npm test` (vitest).
 */

import fs from "fs";
import os from "os";
import path from "path";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { parse } from "node-html-parser";
import { runSectionSidecarLeg } from "../feed.mjs";

function sectionHtml(etype, rendered, note) {
  const cards = Array.from(
    { length: rendered },
    (_, i) => `<article data-feed-card="">${etype} card ${i}</article>`,
  ).join("");
  const noteHtml = note
    ? `<p data-feed-truncation-note="" data-feed-event-type="${etype}" ` +
      `data-feed-shown="${note.shown}" data-feed-total="${note.total}">` +
      `Showing the ${note.shown} largest of ${note.total}</p>`
    : "";
  return `<section id="feed-${etype}">${cards}${noteHtml}</section>`;
}

function rootFor(...sections) {
  return parse(`<main>${sections.join("")}</main>`, { comment: false });
}

function hidden(etype, n, overrides = {}) {
  return Array.from({ length: n }, (_, i) => ({
    event_type: etype,
    pe_bli: `PE${i}`,
    family_key: null,
    company_slug: null,
    has_program_page: true,
    ...overrides,
  }));
}

let dir;
beforeEach(() => {
  dir = fs.mkdtempSync(path.join(os.tmpdir(), "feed-sections-leg-o-"));
});
afterEach(() => {
  fs.rmSync(dir, { recursive: true, force: true });
});

function writeSidecar(etype, body) {
  fs.writeFileSync(path.join(dir, `${etype}.json`), JSON.stringify(body));
}

/** A page with one truncated section (2 of 5) and one complete section (3). */
function goodPage() {
  return rootFor(
    sectionHtml("yoy_swing", 2, { shown: 2, total: 5 }),
    sectionHtml("new_entrant", 3, null),
  );
}
function goodSidecars() {
  writeSidecar("yoy_swing", {
    event_type: "yoy_swing", section_cap: 2, shown: 2, total: 5, cards: hidden("yoy_swing", 3),
  });
  writeSidecar("new_entrant", {
    event_type: "new_entrant", section_cap: 2, shown: 3, total: 3, cards: [],
  });
}

function run(root) {
  const errors = [];
  const notes = [];
  runSectionSidecarLeg(errors, notes, root, dir);
  return { errors, notes };
}

describe("gate 8 leg (o) — passes on a consistent page + sidecar set", () => {
  it("reports no errors and a note naming the counts", () => {
    goodSidecars();
    const { errors, notes } = run(goodPage());
    expect(errors).toEqual([]);
    expect(notes.some((n) => /leg o: 2 section sidecar\(s\).*1 truncated/.test(n))).toBe(true);
  });
});

describe("gate 8 leg (o) — the failures it exists to catch", () => {
  it("a rendered section with no shipped sidecar", () => {
    goodSidecars();
    fs.rmSync(path.join(dir, "yoy_swing.json"));
    const { errors } = run(goodPage());
    expect(errors.some((e) => /yoy_swing\.json is missing/.test(e))).toBe(true);
  });

  it("a sidecar whose card count is not total − shown", () => {
    goodSidecars();
    writeSidecar("yoy_swing", {
      event_type: "yoy_swing", section_cap: 2, shown: 2, total: 5, cards: hidden("yoy_swing", 2),
    });
    const { errors } = run(goodPage());
    expect(errors.some((e) => /carries 2 card\(s\), page shows 2 of 5 — expected 3/.test(e))).toBe(true);
  });

  it("a sidecar whose own shown/total disagree with the page", () => {
    goodSidecars();
    writeSidecar("yoy_swing", {
      event_type: "yoy_swing", section_cap: 3, shown: 3, total: 6, cards: hidden("yoy_swing", 3),
    });
    const { errors } = run(goodPage());
    expect(errors.some((e) => /says shown=3 total=6, page says 2 of 5/.test(e))).toBe(true);
  });

  it("a card of another event type inside the sidecar", () => {
    goodSidecars();
    writeSidecar("yoy_swing", {
      event_type: "yoy_swing", section_cap: 2, shown: 2, total: 5,
      cards: [...hidden("yoy_swing", 2), ...hidden("concentration_shift", 1)],
    });
    const { errors } = run(goodPage());
    expect(errors.some((e) => /1 card\(s\) of another event type/.test(e))).toBe(true);
  });

  it("a card without the pre-resolved lookups", () => {
    goodSidecars();
    const cards = hidden("yoy_swing", 3);
    delete cards[0].has_program_page;
    delete cards[1].company_slug;
    writeSidecar("yoy_swing", { event_type: "yoy_swing", section_cap: 2, shown: 2, total: 5, cards });
    const { errors } = run(goodPage());
    expect(errors.some((e) => /2 card\(s\) without pre-resolved company_slug\/has_program_page/.test(e))).toBe(true);
  });

  it("a complete (un-truncated) section whose sidecar still carries hidden cards", () => {
    goodSidecars();
    writeSidecar("new_entrant", {
      event_type: "new_entrant", section_cap: 2, shown: 3, total: 3, cards: hidden("new_entrant", 1),
    });
    const { errors } = run(goodPage());
    expect(errors.some((e) => /new_entrant is not truncated on \/feed\/.*carries 1 hidden card\(s\)/.test(e))).toBe(true);
  });

  it("a truncation note whose shown count disagrees with the rendered cards", () => {
    goodSidecars();
    const root = rootFor(
      sectionHtml("yoy_swing", 1, { shown: 2, total: 5 }),
      sectionHtml("new_entrant", 3, null),
    );
    const { errors } = run(root);
    expect(errors.some((e) => /note says 2 shown but 1 \[data-feed-card\] rendered/.test(e))).toBe(true);
  });

  it("an unparseable sidecar", () => {
    goodSidecars();
    fs.writeFileSync(path.join(dir, "yoy_swing.json"), "{not json");
    const { errors } = run(goodPage());
    expect(errors.some((e) => /yoy_swing\.json is not parseable JSON/.test(e))).toBe(true);
  });

  it("no truncated section at all trips the non-vacuity floor", () => {
    writeSidecar("new_entrant", {
      event_type: "new_entrant", section_cap: 75, shown: 3, total: 3, cards: [],
    });
    const { errors } = run(rootFor(sectionHtml("new_entrant", 3, null)));
    expect(errors.some((e) => /0 truncated section\(s\).*floor 1/.test(e))).toBe(true);
  });

  it("no feed-* section at all is a vacuity error, not a pass", () => {
    const { errors } = run(rootFor("<section id='other'></section>"));
    expect(errors.some((e) => /no feed-\* sections rendered/.test(e))).toBe(true);
  });
});
