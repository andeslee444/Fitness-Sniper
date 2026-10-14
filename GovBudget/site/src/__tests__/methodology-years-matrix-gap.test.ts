/**
 * /methodology/ #coverage-years-matrix — what a "–" on /years/ means
 * (families piece-1 follow-ups design §3.7, owner Q13; ROADMAP #193, #206 T4).
 *
 * The clause said an absent cell meant "the trajectory workbook simply has no
 * row for that program and column". For a decade column the source is the
 * edition workbook the column states, and since the era fence lifted every
 * /years/ row carries exactly its program page's decade points (gate 20 leg j),
 * so the clause names the edition workbook — at the replaced clause's exact
 * length (69 bytes, no ' or &, so the escaped HTML is as long too):
 * /methodology/ sits near its gate-1 ceiling.
 */
import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";

const PAGE = path.resolve(__dirname, "..", "app", "methodology", "page.tsx");

const OLD_CLAUSE = "the trajectory workbook simply has no row for that program and column";
const NEW_CLAUSE = "the edition workbook simply holds no line for that program and column";

/** Rendered text of the JSX between two markers: {" "} is a space, tags drop,
 *  whitespace collapses, &amp; is &. */
function visible(start: string, end: string): string {
  const src = fs.readFileSync(PAGE, "utf8");
  const a = src.indexOf(start);
  const b = src.indexOf(end, a + start.length);
  expect(a, `marker not found: ${start}`).toBeGreaterThan(-1);
  expect(b, `marker not found: ${end}`).toBeGreaterThan(a);
  return src
    .slice(a, b)
    .replaceAll('{" "}', " ")
    .replace(/<[^>]+>/g, "")
    .replace(/\s+/g, " ")
    .replaceAll("&amp;", "&")
    .trim();
}

describe("/methodology/ #coverage-years-matrix absent-cell clause", () => {
  const clause = visible("is <em>absent</em>:", "(most");

  it("names the edition workbook as the source an absent cell is silent in", () => {
    expect(clause).toBe(`is absent: ${NEW_CLAUSE}`);
  });

  it("no longer names the trajectory workbook", () => {
    expect(fs.readFileSync(PAGE, "utf8").replace(/\s+/g, " ")).not.toContain(OLD_CLAUSE);
  });

  it("is exactly as long as the clause it replaced, and needs no escaping", () => {
    expect(Buffer.byteLength(OLD_CLAUSE)).toBe(69);
    expect(Buffer.byteLength(NEW_CLAUSE)).toBe(69);
    expect(NEW_CLAUSE).not.toMatch(/['&"<>]/);
  });
});
