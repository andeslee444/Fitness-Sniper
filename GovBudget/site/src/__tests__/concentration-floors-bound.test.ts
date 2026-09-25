/**
 * Task 26 (review: rejected-Important R1 and minor M66, both true and cheap):
 * the concentration floors the site PRINTS are hand copies of floors the
 * WAREHOUSE applies, and nothing tied the two.
 *
 *   - concentration-basis.ts HIGH_ONLY_MIN_AWARDS / HIGH_ONLY_MIN_FAMILIES
 *     render into every withheld program page's reason; the SQL types `>= 3`
 *     and `>= 2` twice each (hhi_high, top_family_high). Raising the SQL floor
 *     alone kept every site test green while withheld pages went on saying
 *     "at least 3 awards".
 *   - /methodology/ §4 and the glossary spell the same floor in words.
 *   - /feed/ and /methodology/ print the concentration_shift threshold as
 *     "$5M"; fct_feed_events.sql types `having sum(dollars) >= 5000000`.
 *
 * Each literal is read out of the SQL here and compared, so a change on
 * either side reds this file instead of shipping a stale sentence.
 */
import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";
import {
  HIGH_ONLY_MIN_AWARDS,
  HIGH_ONLY_MIN_FAMILIES,
} from "@/lib/concentration-basis";

const SITE = path.resolve(__dirname, "..", "..");
const MARTS = path.join(SITE, "..", "dbt", "models", "marts");
const sql = (f: string) => fs.readFileSync(path.join(MARTS, f), "utf8");
const src = (...p: string[]) =>
  fs.readFileSync(path.join(SITE, "src", ...p), "utf8").replace(/\s+/g, " ");

const WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"];

describe("the program-page concentration floor ↔ fct_program_concentration.sql", () => {
  const conc = sql("fct_program_concentration.sql");

  it("every high-basis award-count literal in the SQL is HIGH_ONLY_MIN_AWARDS", () => {
    const got = [
      ...conc.matchAll(/basis = 'high' then award_count end\), 0\) >= (\d+)/g),
    ].map((m) => Number(m[1]));
    expect(got.length).toBe(2); // hhi_high and top_family_high
    for (const n of got) expect(n).toBe(HIGH_ONLY_MIN_AWARDS);
  });

  it("every positive-family literal in the SQL is HIGH_ONLY_MIN_FAMILIES", () => {
    const got = [
      ...conc.matchAll(/basis = 'high' then positive_family_count end\), 0\) >= (\d+)/g),
    ].map((m) => Number(m[1]));
    expect(got.length).toBe(2);
    for (const n of got) expect(n).toBe(HIGH_ONLY_MIN_FAMILIES);
  });

  it("the prose copies spell the same floor", () => {
    const phrase =
      `at least ${WORDS[HIGH_ONLY_MIN_AWARDS]} such awards across ` +
      `${WORDS[HIGH_ONLY_MIN_FAMILIES]} or more contractor families`;
    expect(src("app", "methodology", "page.tsx")).toContain(phrase);
    expect(src("lib", "glossary.ts")).toContain(phrase);
  });
});

describe("the concentration_shift threshold ↔ fct_feed_events.sql", () => {
  it("the $5M the pages print is the SQL's `having sum(dollars) >=` floor", () => {
    const m = /having sum\(dollars\) >= (\d+)/.exec(sql("fct_feed_events.sql"));
    expect(m).not.toBeNull();
    const millions = Number(m![1]) / 1_000_000;
    expect(Number.isInteger(millions)).toBe(true);
    expect(src("app", "feed", "page.tsx")).toContain(
      `at least $${millions}M in matched obligations`,
    );
    expect(src("app", "methodology", "page.tsx")).toContain(
      `at least $${millions}M in positive obligations`,
    );
  });
});
