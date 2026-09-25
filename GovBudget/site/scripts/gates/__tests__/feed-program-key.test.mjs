/**
 * The page a feed card addresses — ONE key in two languages, and a gate that
 * holds the shipped files to it (Task 28 fix round 1, B2).
 *
 * `feedProgramKey` (src/lib/feed-model.mjs) and export_site.py's
 * `_feed_program_key` are mirrors: /feed/, the RSS/Atom item links and the
 * program watch feeds resolve a card's page with the first; the exporter
 * pre-resolves the section sidecars' `has_program_page` — what "Show all"
 * renders a card's "view program" link from — with the second. Until this
 * round each had its own hand-kept four-row table and nothing compared them.
 *
 *   1. THE SHARED TABLE. fixtures/feed-program-key.json is read here AND by
 *      tests/test_feed_program_key_mirror.py; both sides must give every
 *      case's key and has_program_page.
 *   2. GATE 8 LEG (p). On a build, every feed.json card, every section-sidecar
 *      card and every rendered /feed/ card must address one page key: a
 *      program_url that is `/program/${feedProgramKey(card)}/` or null, a
 *      has_program_page equal to feedCardHasProgramPage over the SHIPPED
 *      program_details listing, and a rendered link exactly where that answer
 *      says so. The proof-it-can-fail cases below are the ways the mirror
 *      breaks.
 *
 * Run via `npm test` (vitest).
 */

import fs from "fs";
import os from "os";
import path from "path";
import { fileURLToPath } from "url";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { parse } from "node-html-parser";
import { runProgramKeyLeg } from "../feed.mjs";
import {
  feedProgramKey,
  feedCardHasProgramPage,
} from "../../../src/lib/feed-model.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FIXTURE = path.join(HERE, "fixtures", "feed-program-key.json");
const TABLE = JSON.parse(fs.readFileSync(FIXTURE, "utf8"));
const PAGES = new Set(TABLE.program_pages);

// ── 1. the shared table ─────────────────────────────────────────────────────

describe("the shared page-key table (feedProgramKey ↔ _feed_program_key)", () => {
  it.each(TABLE.cases.map((c) => [c.name, c]))("%s", (_name, c) => {
    expect(feedProgramKey(c.card)).toBe(c.key);
    expect(feedCardHasProgramPage(c.card, PAGES)).toBe(c.has_program_page);
  });

  it("is the table the Python side reads — one file, not two copies", () => {
    const pytest = fs.readFileSync(
      path.resolve(HERE, "..", "..", "..", "..", "tests", "test_feed_program_key_mirror.py"),
      "utf8",
    );
    expect(pytest).toContain('"fixtures" / "feed-program-key.json"');
    expect(pytest).toMatch(/import _emit_feed_section_sidecars, _feed_program_key/);
  });

  it("covers every card shape (a table trimmed to easy cases would still agree)", () => {
    const member = TABLE.cases.filter((c) => c.key && c.key !== c.card.pe_bli);
    expect(member.length).toBeGreaterThan(0);
    expect(member.every((c) => c.has_program_page)).toBe(true);
    const starts = (p) => TABLE.cases.filter((c) => c.name.startsWith(p)).length;
    expect(starts("bare stub")).toBeGreaterThan(0);
    expect(starts("ordinary code")).toBeGreaterThan(0);
    expect(starts("company card")).toBeGreaterThan(0);
    expect(starts("malformed url")).toBeGreaterThanOrEqual(3);
  });
});

// ── 2. gate 8 leg (p) ───────────────────────────────────────────────────────

const ORDINARY = {
  event_type: "concentration_shift",
  pe_bli: "0601102A",
  program_url: "/program/0601102A/",
  family_key: null,
  fiscal_year: 2021,
};
const MEMBER = {
  event_type: "concentration_shift",
  pe_bli: "2292",
  program_url: "/program/2292-WPN/",
  family_key: null,
  fiscal_year: 2023,
};
const NO_PAGE = {
  event_type: "concentration_shift",
  pe_bli: "0605999X",
  program_url: "/program/0605999X/",
  family_key: null,
  fiscal_year: 2020,
};
const COMPANY = {
  event_type: "new_entrant",
  pe_bli: null,
  program_url: null,
  family_key: "ACME",
  fiscal_year: 2025,
};

let dir;
beforeEach(() => {
  dir = fs.mkdtempSync(path.join(os.tmpdir(), "feed-leg-p-"));
});
afterEach(() => {
  fs.rmSync(dir, { recursive: true, force: true });
});

/** Write a shipped-out tree: feed.json, sidecars, the listing, built pages. */
function ship({ cards, sidecars, pages = ["0601102A", "2292-WPN", "2292-PMC"], built = pages }) {
  const json = path.join(dir, "json");
  fs.mkdirSync(path.join(json, "feed-sections"), { recursive: true });
  fs.writeFileSync(path.join(json, "feed.json"), JSON.stringify({ cards, section_cap: 1 }));
  for (const [etype, sc] of Object.entries(sidecars)) {
    fs.writeFileSync(
      path.join(json, "feed-sections", `${etype}.json`),
      JSON.stringify({ event_type: etype, cards: sc }),
    );
  }
  const listing = path.join(dir, "json-lite", "program_details");
  fs.mkdirSync(listing, { recursive: true });
  for (const p of pages) fs.writeFileSync(path.join(listing, `${p}.json`), "{}");
  for (const p of built) {
    fs.mkdirSync(path.join(dir, "program", p), { recursive: true });
    fs.writeFileSync(path.join(dir, "program", p, "index.html"), "<html></html>");
  }
}

/** One rendered /feed/ card, as the shell renders it. */
function cardHtml(c, href) {
  const entity = c.pe_bli ?? c.family_key ?? "unknown";
  const link = href ? `<a href="${href}">view program →</a>` : "";
  return (
    `<div data-feed-card=""><p data-source-text="headline" ` +
    `data-xml-path="site:feed/${c.event_type}/${entity}">h</p>` +
    `<div><span>${entity}</span>${link}</div>` +
    `<a href="/methodology/#feed-${c.event_type}">why flagged?</a></div>`
  );
}

function page(sections) {
  return parse(
    `<main>${Object.entries(sections)
      .map(([etype, html]) => `<section id="feed-${etype}">${html.join("")}</section>`)
      .join("")}</main>`,
    { comment: false },
  );
}

function run(root) {
  const errors = [];
  const notes = [];
  runProgramKeyLeg(errors, notes, root, {
    feedJsonPath: path.join(dir, "json", "feed.json"),
    sectionsDir: path.join(dir, "json", "feed-sections"),
    programDetailsDir: path.join(dir, "json-lite", "program_details"),
    pagesDir: dir,
  });
  return { errors, notes };
}

/** A consistent build: one rendered card per section, the rest in sidecars. */
function goodBuild() {
  ship({
    cards: [ORDINARY, MEMBER, NO_PAGE, COMPANY],
    sidecars: {
      concentration_shift: [
        { ...MEMBER, company_slug: null, has_program_page: true },
        { ...NO_PAGE, company_slug: null, has_program_page: false },
      ],
      new_entrant: [],
    },
  });
  return page({
    concentration_shift: [cardHtml(ORDINARY, "/program/0601102A/")],
    new_entrant: [cardHtml(COMPANY, null)],
  });
}

describe("gate 8 leg (p) — passes on a consistent build", () => {
  it("reports no errors and a note naming what it checked", () => {
    const { errors, notes } = run(goodBuild());
    expect(errors).toEqual([]);
    const note = notes.find((n) => n.startsWith("leg p:"));
    expect(note).toMatch(/4 feed\.json card\(s\), 2 section-sidecar card\(s\) and 2 rendered/);
    expect(note).toMatch(/1 of them .*member page/);
  });

  it("a member card rendered with its member link passes", () => {
    ship({
      cards: [MEMBER],
      sidecars: { concentration_shift: [] },
    });
    const { errors } = run(page({ concentration_shift: [cardHtml(MEMBER, "/program/2292-WPN/")] }));
    expect(errors).toEqual([]);
  });
});

describe("gate 8 leg (p) — the failures it exists to catch", () => {
  it("a sidecar has_program_page keyed by the bare pe_bli (the pre-28a mirror) on a member card", () => {
    const root = goodBuild();
    fs.writeFileSync(
      path.join(dir, "json", "feed-sections", "concentration_shift.json"),
      JSON.stringify({
        event_type: "concentration_shift",
        cards: [
          { ...MEMBER, company_slug: null, has_program_page: false },
          { ...NO_PAGE, company_slug: null, has_program_page: false },
        ],
      }),
    );
    const { errors } = run(root);
    expect(errors).toHaveLength(1);
    expect(errors[0]).toMatch(
      /feed leg p: .*concentration_shift\.json: concentration_shift 2292 FY2023 has_program_page=false but its page key "2292-WPN" names a program_details sidecar/,
    );
  });

  it("a sidecar that claims a page the listing does not have (a dead \"view program\" link)", () => {
    const root = goodBuild();
    fs.writeFileSync(
      path.join(dir, "json", "feed-sections", "concentration_shift.json"),
      JSON.stringify({
        event_type: "concentration_shift",
        cards: [
          { ...MEMBER, company_slug: null, has_program_page: true },
          { ...NO_PAGE, company_slug: null, has_program_page: true },
        ],
      }),
    );
    const { errors } = run(root);
    expect(errors.some((e) => /0605999X FY2020 has_program_page=true but its page key "0605999X" names no program_details sidecar/.test(e))).toBe(true);
  });

  it("a malformed program_url, in feed.json and in the sidecar that copies it", () => {
    const bad = { ...MEMBER, program_url: "/program/2292-WPN" };
    ship({
      cards: [ORDINARY, bad],
      sidecars: { concentration_shift: [{ ...bad, company_slug: null, has_program_page: false }] },
    });
    const { errors } = run(page({ concentration_shift: [cardHtml(ORDINARY, "/program/0601102A/")] }));
    expect(errors.filter((e) => /program_url "\/program\/2292-WPN", which is not \/program\/\{key\}\//.test(e))).toHaveLength(2);
  });

  it("a card whose page is listed but carries no program_url (no link on /feed/, a link in its feed item)", () => {
    const bare = { ...ORDINARY, program_url: null };
    ship({ cards: [bare], sidecars: { concentration_shift: [] } });
    const { errors } = run(page({ concentration_shift: [cardHtml(bare, null)] }));
    expect(errors.some((e) => /addresses \/program\/0601102A\/, which has a program_details sidecar, but carries no program_url/.test(e))).toBe(true);
  });

  it("a card linking a listed page that did not build — past the first 75 as much as inside them", () => {
    ship({
      cards: [ORDINARY, MEMBER],
      sidecars: { concentration_shift: [{ ...MEMBER, company_slug: null, has_program_page: true }] },
      built: ["0601102A"],
    });
    const { errors } = run(page({ concentration_shift: [cardHtml(ORDINARY, "/program/0601102A/")] }));
    expect(errors.some((e) => /2292 FY2023 links \/program\/2292-WPN\/, listed in program_details but not built/.test(e))).toBe(true);
  });

  it("/feed/ renders no link where the page exists (the page keyed by bare pe_bli again)", () => {
    ship({ cards: [MEMBER], sidecars: { concentration_shift: [] } });
    const { errors } = run(page({ concentration_shift: [cardHtml(MEMBER, null)] }));
    expect(errors).toHaveLength(1);
    expect(errors[0]).toMatch(/\/feed\/ concentration_shift card 1 \(concentration_shift 2292 FY2023\) links no program page; expected \/program\/2292-WPN\//);
  });

  it("/feed/ links the bare code's page instead of the member's", () => {
    ship({ cards: [MEMBER], sidecars: { concentration_shift: [] } });
    const { errors } = run(page({ concentration_shift: [cardHtml(MEMBER, "/program/2292/")] }));
    expect(errors.some((e) => /links \/program\/2292\/; expected \/program\/2292-WPN\//.test(e))).toBe(true);
  });

  it("/feed/ renders a link where no page exists", () => {
    ship({ cards: [NO_PAGE], sidecars: { concentration_shift: [] } });
    const { errors } = run(page({ concentration_shift: [cardHtml(NO_PAGE, "/program/0605999X/")] }));
    expect(errors.some((e) => /links \/program\/0605999X\/; expected none/.test(e))).toBe(true);
  });

  it("a rendered card that is not feed.json's card at that position is named, not silently compared", () => {
    ship({ cards: [ORDINARY, MEMBER], sidecars: { concentration_shift: [] } });
    const { errors } = run(page({ concentration_shift: [cardHtml(MEMBER, "/program/2292-WPN/")] }));
    expect(errors.some((e) => /card 1 renders site:feed\/concentration_shift\/2292 where feed\.json's card 1 is site:feed\/concentration_shift\/0601102A/.test(e))).toBe(true);
  });

  it("an empty program_details listing is vacuous, not a pass", () => {
    goodBuild();
    for (const f of fs.readdirSync(path.join(dir, "json-lite", "program_details"))) {
      fs.rmSync(path.join(dir, "json-lite", "program_details", f));
    }
    const { errors } = run(page({}));
    expect(errors.some((e) => /program_details.*is empty — the leg is vacuous/.test(e))).toBe(true);
  });

  it("no rendered card to check is vacuous, not a pass", () => {
    goodBuild();
    const { errors } = run(page({}));
    expect(errors.some((e) => /no rendered \/feed\/ card was checked/.test(e))).toBe(true);
  });
});
