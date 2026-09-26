/**
 * Gate 1 leg — shard-only citations (R-DEC-GATE-SHARDS, controller,
 * fix-round-5 rulings, 2026-09-26): "A build-time gate leg fails any company
 * or district page that ships a non-empty embedded citations object."
 *
 * WHY. Task 28b (ruling R-28b-4) stopped /district/{code}/ embedding its
 * citation map in the page: the provider mounts with `citations={{}}` and a
 * click resolves the body from /json/cite-shards/{fact_id[:2]}.json. Fix
 * round 5 moved /company/{slug}/ onto the same path after R-DEC-LDACITE's
 * filing lists put 12 company pages over gate 1's 25,000-gzip ceiling
 * (aerospace 41,964, boeing 29,663). Only vitest (district-cite-shards,
 * company-cite-shards) checked the embed, against component renders; no
 * gate read a BUILT page, so a revert would have surfaced only as a weight
 * failure on the heaviest page — or not at all below the ceiling.
 *
 * HOW A PAGE SHIPS IT. The provider is a client component, so its props are
 * serialized into the React Server Components flight payload: in index.html
 * as `self.__next_f.push([1,"<chunk>"])` scripts, and again, raw, in the
 * page directory's RSC files (index.txt, __next._full.txt,
 * __next.<segment>.__PAGE__.txt) that client-side navigation fetches. The
 * flight stream carries a module row `<id>:I[…,"CitationPanelProvider"]` and
 * the element `["$","$L<id>",null,{"citations":{…},"shardResolvableIds":[…],…}]`.
 * On the integration build (git_head 0587f90f) /company/boeing/ embeds a
 * 191,889-byte __PAGE__ payload whose provider carries the whole slice, and
 * /district/VA-11/ carries `"citations":{}`.
 *
 * Run via `npm test` (vitest).
 */
import fs from "fs";
import os from "os";
import path from "path";
import { afterEach, describe, expect, it } from "vitest";
import {
  embeddedCitationFindings,
  flightFromHtml,
  runShardOnlyCitationsLeg,
} from "../shard-only-citations.mjs";

/** One flight chunk as Next writes it into the HTML (JSON string literal,
 *  "<" escaped). */
const push = (chunk) =>
  `<script>self.__next_f.push([1,${JSON.stringify(chunk).replace(/</g, "\\u003c")}])</script>`;
/** The module row, in the integration build's shape. */
const I_ROW = '1e:I[3306,["/_next/static/chunks/00f_35we61q6c.js"],"CitationPanelProvider"]\n';
const LINK_ROW = '7:I[22016,["/_next/static/chunks/00f_35we61q6c.js"],"default"]\n';
/** The footer's site counts carry a "citations" NUMBER — not a map. */
const FOOTER_ROW = '16:["$","$L13",null,{"counts":{"agencies":24,"citations":135737,"companies":200}}]\n';
const CITATION = {
  amount_text: null,
  amount_thousands: null,
  formula: "sum(fct_award_transactions.obligation)",
  kind: "derived",
  inputs: "[]",
};
const providerRow = (citations, rowId = "15") =>
  `${rowId}:["$","$L1e",null,{"citations":${JSON.stringify(citations)},` +
  '"shardResolvableIds":["9645f09d97474dfb","2d0283cb05ba355c"],"children":["$","div",null,{"className":"spine py-8","children":"x"}]}]\n';
/** A page: static markup plus the flight stream in `chunks` pushes. */
const html = (stream, chunks = 1) => {
  const size = Math.ceil(stream.length / chunks);
  const parts = [];
  for (let i = 0; i < stream.length; i += size) parts.push(push(stream.slice(i, i + size)));
  return `<!DOCTYPE html><html><body><main><p>Boeing</p></main>${parts.join("")}</body></html>`;
};
const EMPTY_STREAM = LINK_ROW + I_ROW + providerRow({}) + FOOTER_ROW;
const FULL_STREAM =
  LINK_ROW + I_ROW + providerRow({ b9d8454b2ebe52ca: CITATION, "9645f09d97474dfb": CITATION }) + FOOTER_ROW;

describe("flightFromHtml — the RSC stream a page's HTML carries", () => {
  it("joins every push chunk, in order, decoded", () => {
    const { stream, unreadable } = flightFromHtml(html(EMPTY_STREAM, 5));
    expect(unreadable).toBe(0);
    expect(stream).toBe(EMPTY_STREAM);
  });

  it("counts a chunk it cannot decode, rather than dropping it silently", () => {
    const bad = html(EMPTY_STREAM).replace("<main>", '<script>self.__next_f.push([1,"\\x"])</script><main>');
    expect(flightFromHtml(bad).unreadable).toBe(1);
  });
});

describe("embeddedCitationFindings — one flight stream", () => {
  it("passes a provider that embeds an empty citations object", () => {
    const r = embeddedCitationFindings(EMPTY_STREAM);
    expect(r.providers).toBe(1);
    expect(r.problems).toEqual([]);
  });

  it("FAILS a provider that embeds citations, and says how many", () => {
    const r = embeddedCitationFindings(FULL_STREAM);
    expect(r.providers).toBe(1);
    expect(r.problems).toHaveLength(1);
    expect(r.problems[0]).toMatch(/CitationPanelProvider/);
    expect(r.problems[0]).toMatch(/2 citation/);
    expect(r.problems[0]).toMatch(/b9d8454b2ebe52ca/);
  });

  it("FAILS whatever the chunking: a provider split across push boundaries is still read", () => {
    for (const chunks of [2, 3, 7, 40]) {
      const { stream } = flightFromHtml(html(FULL_STREAM, chunks));
      expect(embeddedCitationFindings(stream).problems, String(chunks)).toHaveLength(1);
    }
  });

  it("follows an outlined reference: citations passed as a '$<row>' pointer", () => {
    const outlined = (obj) =>
      LINK_ROW + I_ROW + `2a:${JSON.stringify(obj)}\n` + providerRow("$2a") + FOOTER_ROW;
    expect(embeddedCitationFindings(outlined({})).problems).toEqual([]);
    const r = embeddedCitationFindings(outlined({ b9d8454b2ebe52ca: CITATION }));
    expect(r.problems).toHaveLength(1);
    expect(r.problems[0]).toMatch(/1 citation/);
  });

  it("FAILS a pointer it cannot resolve — it cannot prove the object empty", () => {
    const r = embeddedCitationFindings(LINK_ROW + I_ROW + providerRow("$ff") + FOOTER_ROW);
    expect(r.problems.join("\n")).toMatch(/cannot resolve/);
  });

  it("FAILS a provider with no citations prop — reported, never read as empty", () => {
    const stream = LINK_ROW + I_ROW + '15:["$","$L1e",null,{"shardResolvableIds":[],"children":"x"}]\n';
    expect(embeddedCitationFindings(stream).problems.join("\n")).toMatch(/no citations prop/);
  });

  it("FAILS a non-empty citations map handed to ANY component, not only the provider", () => {
    const stream =
      EMPTY_STREAM + '20:["$","$L7",null,{"href":"/x/","citations":{"b9d8454b2ebe52ca":{"kind":"derived"}}}]\n';
    const r = embeddedCitationFindings(stream);
    expect(r.problems).toHaveLength(1);
    expect(r.problems[0]).toMatch(/b9d8454b2ebe52ca/);
  });

  it("the footer's citation COUNT is a number, not an embedded map", () => {
    expect(embeddedCitationFindings(FOOTER_ROW).problems).toEqual([]);
  });

  it("text rows cannot fake a provider: an escaped mention inside a string is not a module row", () => {
    const stream = '3:["$","p",null,{"children":"1e:I[1,[],\\"CitationPanelProvider\\"]"}]\n';
    expect(embeddedCitationFindings(stream).providers).toBe(0);
  });
});

describe("runShardOnlyCitationsLeg — the built company and district pages", () => {
  const dirs = [];
  afterEach(() => {
    for (const d of dirs.splice(0)) fs.rmSync(d, { recursive: true, force: true });
  });
  /** A synthetic out/ with `company` and `district` page dirs, each page an
   *  index.html plus its RSC .txt payloads. */
  const makeOut = ({ company = {}, district = {}, districtIndex = EMPTY_STREAM } = {}) => {
    const out = fs.mkdtempSync(path.join(os.tmpdir(), "shard-only-"));
    dirs.push(out);
    const write = (rel, body) => {
      fs.mkdirSync(path.dirname(path.join(out, rel)), { recursive: true });
      fs.writeFileSync(path.join(out, rel), body);
    };
    for (const [cls, pages] of [["company", company], ["district", district]]) {
      for (const [slug, page] of Object.entries(pages)) {
        write(`${cls}/${slug}/index.html`, html(page.html ?? EMPTY_STREAM, 3));
        write(`${cls}/${slug}/index.txt`, page.txt ?? page.html ?? EMPTY_STREAM);
        write(`${cls}/${slug}/__next.${cls}.$d$slug.__PAGE__.txt`, page.pageTxt ?? page.html ?? EMPTY_STREAM);
        write(`${cls}/${slug}/__next._tree.txt`, '0:{"tree":1}\n');
      }
    }
    if (districtIndex !== null) {
      write("district/index.html", html(districtIndex, 2));
      write("district/index.txt", districtIndex);
    }
    return out;
  };
  const run = (outDir) => {
    const errors = [];
    const notes = [];
    runShardOnlyCitationsLeg({ outDir, errors, notes });
    return { errors, notes };
  };

  it("passes when every page ships an empty embedded citations object", () => {
    const out = makeOut({ company: { boeing: {}, aarcorp: {} }, district: { "VA-11": {}, "AL-02": {} } });
    const { errors, notes } = run(out);
    expect(errors).toEqual([]);
    expect(notes.join("\n")).toMatch(/2 \/company\/\*\/ and 2 \/district\/\*\/ pages \(\+ \/district\/\)/);
  });

  it("FAILS a company page whose HTML embeds its citations (the pre-fix-5 shape)", () => {
    const out = makeOut({
      company: { boeing: { html: FULL_STREAM }, aarcorp: {} },
      district: { "VA-11": {} },
    });
    const { errors } = run(out);
    expect(errors.length).toBeGreaterThan(0);
    expect(errors.join("\n")).toMatch(/\/company\/boeing\//);
    expect(errors.join("\n")).toMatch(/R-DEC-GATE-SHARDS/);
    expect(errors.join("\n")).not.toMatch(/aarcorp/);
  });

  it("FAILS a district page that goes back to embedding (the pre-Task-28b shape)", () => {
    const out = makeOut({ company: { boeing: {} }, district: { "VA-11": { html: FULL_STREAM } } });
    expect(run(out).errors.join("\n")).toMatch(/\/district\/VA-11\//);
  });

  it("FAILS the /district/ index too", () => {
    const out = makeOut({ company: { boeing: {} }, district: { "VA-11": {} }, districtIndex: FULL_STREAM });
    expect(run(out).errors.join("\n")).toMatch(/\/district\/ /);
  });

  it("FAILS when only an RSC payload file embeds — navigation fetches it", () => {
    const out = makeOut({ company: { boeing: { pageTxt: FULL_STREAM } }, district: { "VA-11": {} } });
    const msg = run(out).errors.join("\n");
    expect(msg).toMatch(/\/company\/boeing\//);
    expect(msg).toMatch(/__PAGE__\.txt/);
  });

  it("FAILS a page whose HTML carries no provider payload — it cannot be read, so it cannot pass", () => {
    const out = makeOut({ company: { boeing: { html: LINK_ROW + FOOTER_ROW } }, district: { "VA-11": {} } });
    expect(run(out).errors.join("\n")).toMatch(/no CitationPanelProvider payload/);
  });

  it("FAILS a page whose HTML carries a flight chunk that will not decode", () => {
    const out = makeOut({ company: { boeing: {} }, district: { "VA-11": {} } });
    const file = path.join(out, "company", "boeing", "index.html");
    fs.writeFileSync(
      file,
      fs.readFileSync(file, "utf8").replace("<main>", '<script>self.__next_f.push([1,"\\x"])</script><main>'),
    );
    expect(run(out).errors.join("\n")).toMatch(/\/company\/boeing\/ index\.html: 1 of 4 flight chunk\(s\) will not decode/);
  });

  it("FAILS a page directory with no index.html", () => {
    const out = makeOut({ company: { boeing: {} }, district: { "VA-11": {} } });
    fs.rmSync(path.join(out, "company", "boeing", "index.html"));
    expect(run(out).errors.join("\n")).toMatch(/\/company\/boeing\/.*index\.html/);
  });

  it("is never vacuous: a missing or empty page class is an error, not a skip", () => {
    const none = makeOut({ company: {}, district: { "VA-11": {} } });
    expect(run(none).errors.join("\n")).toMatch(/out\/company\/ missing/);
    fs.mkdirSync(path.join(none, "company"));
    expect(run(none).errors.join("\n")).toMatch(/out\/company\/ holds no \/company\/\*\/ page/);
    const missing = makeOut({ company: { boeing: {} }, district: {}, districtIndex: null });
    fs.rmSync(path.join(missing, "district"), { recursive: true, force: true });
    expect(run(missing).errors.join("\n")).toMatch(/out\/district\/ missing/);
  });

  it("counts every failing page but lists a bounded sample", () => {
    const company = {};
    for (let i = 0; i < 30; i++) company[`c${i}`] = { html: FULL_STREAM };
    const out = makeOut({ company, district: { "VA-11": {} } });
    const { errors } = run(out);
    expect(errors.join("\n")).toMatch(/30 page\(s\)/);
    expect(errors.length).toBeLessThanOrEqual(12);
  });
});
