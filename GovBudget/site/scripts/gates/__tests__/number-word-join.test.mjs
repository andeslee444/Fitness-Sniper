/**
 * Unit tests for gate 2 leg (nw) — number-word-join.mjs (ROADMAP #106).
 *
 * THE DEFECT. /methodology/ rendered "plus 553whose cited record" under a
 * green gate 2: the source-level leg (sp) modelled a cleaner the compiler
 * does not use, and no leg read the built prose for the shape itself. This
 * is the built-HTML half. Every allow rule below is a shape the corpus
 * actually renders; every "must catch" is a shape it rendered broken.
 *
 * Run via `npm test` (vitest).
 */

import { describe, it, expect } from "vitest";
import { parse } from "node-html-parser";
import {
  findNumberWordJoins,
  isDeliberateJoin,
  joinsInRun,
} from "../number-word-join.mjs";

const scan = (html) => findNumberWordJoins(parse(html, { comment: false }));
const tokens = (html) => scan(html).hits.map((h) => h.token);
const runTokens = (run) => joinsInRun(run).map((h) => h.token);

describe("joinsInRun — the shapes it must catch", () => {
  it("a number glued to the lowercase word after it", () => {
    expect(runTokens("plus 553whose cited record")).toEqual(["553whose"]);
    expect(runTokens("ingested for 1,936of them")).toEqual(["1,936of"]);
    expect(runTokens("dollars (240at high confidence)")).toEqual(["240at"]);
    expect(runTokens("of OSD’s 128programs carry")).toEqual(["128programs"]);
  });

  it("a number glued to a capitalised word, possessive included", () => {
    expect(runTokens("cited to 7President’s Budget editions")).toEqual([
      "7President’s",
    ]);
  });

  it("a letter-prefixed number glued to a word — the a2637af2 species", () => {
    expect(runTokens("It last appears in the PB2023workbook")).toEqual(["2023workbook"]);
  });

  it("a decimal glued to a word", () => {
    expect(runTokens("in the amount of $1.594million for Project DU2")).toEqual([
      "1.594million",
    ]);
  });

  it("carries a snippet a reader can find on the page", () => {
    const [h] = joinsInRun(
      "the elements the FY2026 workbooks name, plus 553whose cited record stops",
    );
    expect(h.snippet).toContain("plus 553whose cited record");
  });
});

describe("joinsInRun — the shapes it must not invent", () => {
  it("ordinals", () => {
    expect(runTokens("into the 21st century; the 3rd Fleet; the 118th Congress; 1st, 2nd")).toEqual([]);
  });

  it("a single letter after a number is a code, not a word", () => {
    expect(
      runTokens("0605230F and 3010F-AF-L1, 5G, the 1990s, $20.8B, C-130Js, MQ-8Cs, 3D"),
    ).toEqual([]);
  });

  it("hex identifiers, colour hashes and UUIDs", () => {
    expect(
      runTokens(
        "fact ae4f1bee, 885c3adb, e3c199bc, ca5a0cdd, #dc8ba5a6, 5f29754f-87fc-4690-abbb-c0a2a1c84337",
      ),
    ).toEqual([]);
  });

  it("L3Harris", () => {
    expect(runTokens("L3Harris Technologies and L3Harris’s filings")).toEqual([]);
  });

  it("a number followed by a space and a word — the correct shape", () => {
    expect(
      runTokens("plus 553 whose cited record; 1,936 of them; 240 at high confidence"),
    ).toEqual([]);
  });
});

describe("isDeliberateJoin", () => {
  it("names each measured allowance and nothing else", () => {
    expect(isDeliberateJoin("21st")).toBe(true);
    expect(isDeliberateJoin("1bee", "ae4f1bee")).toBe(true);
    expect(isDeliberateJoin("3Harris", "L3Harris")).toBe(true);
    expect(isDeliberateJoin("553whose", "553whose")).toBe(false);
    // units are not an allowance: none is site-authored, and "in" would
    // mask "1,936in the corpus"
    expect(isDeliberateJoin("24hr", "24hr")).toBe(false);
    expect(isDeliberateJoin("5in", "5in")).toBe(false);
    // a short a-f word is not an id: hex needs eight characters
    expect(isDeliberateJoin("553fed", "553fed")).toBe(false);
  });
});

describe("findNumberWordJoins — React text runs", () => {
  it("sees the join across React's <!-- --> text-node boundary", () => {
    expect(
      tokens("<p>plus<!-- --> <!-- -->553<!-- -->whose cited record</p>"),
    ).toEqual(["553whose"]);
  });

  it("decodes entities before scanning", () => {
    expect(tokens("<p>7<!-- -->President&apos;s Budget</p>")).toEqual(["7President's"]);
  });

  it("an element boundary ends a run — not this leg's species", () => {
    expect(tokens("<p>plus <b>553</b>whose</p>")).toEqual([]);
  });

  it("counts the correct shape as a twin, never as a hit", () => {
    const r = scan("<p>plus 553 whose cited record</p><p>no numbers here</p>");
    expect(r.hits).toEqual([]);
    expect(r.runs).toBe(2);
    expect(r.twins).toBe(1);
  });

  it("skips head/script/style/noscript/template, scans the body", () => {
    expect(
      tokens(
        "<head><title>1abc</title></head><body><script>x=1abc</script><style>a{b:2px}</style><template><p>4abc</p></template><p>3abc</p></body>",
      ),
    ).toEqual(["3abc"]);
  });

  it("exempts quoted source kinds whose notation is the source's — and only those", () => {
    expect(tokens('<p data-source-text="narrative">$1.594million for Project DU2</p>')).toEqual([]);
    expect(
      tokens('<p data-source-text="lda-filing">H.R. 7586American Families First Act</p>'),
    ).toEqual([]);
    // exporter-composed headlines are ours to get right
    expect(tokens('<p data-source-text="headline">$1.594million</p>')).toEqual(["1.594million"]);
    // an unclassified marker buys nothing
    expect(tokens('<p data-source-text="made-up">553whose</p>')).toEqual(["553whose"]);
  });

  it("exempts official titles under [data-program-name] — the marker does the work", () => {
    expect(tokens('<td data-program-name="true">2112: Lightweight 155mm Howitzer</td>')).toEqual([]);
    expect(tokens('<span data-program-name="">0167: 5in Rolling Airframe Missile</span>')).toEqual([]);
    expect(tokens("<td>2112: Lightweight 155mm Howitzer</td>")).toEqual(["155mm"]);
  });
});
