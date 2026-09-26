/**
 * Decisions wave fix round 2 (2026-09-26): the RENDERED prose that states
 * the HHI bands, run through gate 8 leg (q)'s own checks
 * (scripts/gates/feed.mjs: hhiBandClaims, runBandProseLeg).
 *
 * The site checker found /methodology/'s concentration passage rendering, at
 * e6bc28bb, "Bands follow the DOJ/FTC Horizontal Merger Guidelines
 * convention: below 1,000 is competitive, 1,000–1,800 is moderately
 * concentrated, and 1,800 or above is highly concentrated (1,800 is the
 * "highly concentrated" floor, not a near-monopoly line — four equal-share
 * firms alone produce exactly 1,800)." — false four ways — with no test or
 * gate reading it. Leg (q) now reads it off the built page. This file reads
 * it off the rendered component, so the defect shows at `npm test`, before
 * any build:
 *
 *   - /glossary/, the /feed/ section sentence and the program-badge tooltip
 *     are true today and must stay so (plain `it`).
 *   - /methodology/ is NOT true at e6bc28bb, and its prose belongs to the
 *     decisions wave's stage-2 writer, not to the lane that added this file.
 *     Its binding assertion is therefore `it.fails`: green while the page is
 *     false, and it turns RED the moment the page is fixed — the writer then
 *     changes `it.fails` to `it`, and the binding stays for good. A render
 *     that throws cannot hide behind `it.fails`: the plain test above it
 *     renders the same page and fails on a throw.
 */
import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render } from "@testing-library/react";
import { parse } from "node-html-parser";
import MethodologyPage from "@/app/methodology/page";
import GlossaryPage from "@/app/glossary/page";
import FeedPage from "@/app/feed/page";
import { ProgramConcentration } from "@/components/program-concentration";
import type { ProgramHHI } from "@/lib/data";
import { hhiBandClaims, runBandProseLeg } from "../../scripts/gates/feed.mjs";

afterEach(() => cleanup());

const rendered = (el: React.ReactElement) => {
  const { container } = render(el);
  const root = parse(container.innerHTML, { comment: false });
  cleanup();
  return root;
};

/** Leg (q) over the rendered pages, as the gate runs it on out/. */
function legQ() {
  const pages: Record<string, ReturnType<typeof parse>> = {
    "/methodology/": rendered(<MethodologyPage />),
    "/glossary/": rendered(<GlossaryPage />),
    "/feed/": rendered(<FeedPage />),
  };
  const errors: string[] = [];
  const notes: string[] = [];
  runBandProseLeg(errors, notes, (route: string) => pages[route] ?? null);
  return { errors, notes, pages };
}

describe("band prose that is true at e6bc28bb stays true", () => {
  it("/glossary/: every band claim agrees with hhi-band.mjs, and it makes them", () => {
    const { errors, pages } = legQ();
    expect(errors.filter((e) => e.includes("/glossary/"))).toEqual([]);
    const kinds = pages["/glossary/"]
      .querySelectorAll("dd, p, li")
      .flatMap((el) => hhiBandClaims(el.text).map((c) => c.kind));
    expect(new Set(kinds)).toEqual(new Set(["vintage", "moderate-range", "high-line", "below"]));
  });

  it("/feed/'s concentration section sentence: its thresholds, not only its words", () => {
    const { errors, pages } = legQ();
    expect(errors.filter((e) => e.includes("/feed/"))).toEqual([]);
    const p = pages["/feed/"].querySelector("#feed-concentration_shift div p");
    expect(p, "no concentration_shift description rendered").not.toBeNull();
    const claims = hhiBandClaims(p!.text);
    expect(claims.filter((c) => !c.ok).map((c) => c.finding)).toEqual([]);
    expect(new Set(claims.map((c) => c.kind))).toEqual(
      new Set(["vintage", "moderate-range", "high-line", "below"]),
    );
  });

  it("the program badge's Index tooltip", () => {
    // program-concentration.test.tsx's fixture A: a published high-basis badge.
    const hhi: ProgramHHI = {
      hhi_all: 1400.4, hhi_all_fact_id: "a".repeat(16),
      program_dollars_all: 500_000_000, program_dollars_all_fact_id: "b".repeat(16),
      top_family_all: "LOCKHEED MARTIN", family_count_all: 12, award_count_all: 40,
      hhi_high: 9800.2, hhi_high_fact_id: "c".repeat(16),
      program_dollars_high: 300_000_000, program_dollars_high_fact_id: "d".repeat(16),
      top_family_high: "BOEING", family_count_high: 2, award_count_high: 5,
    };
    const root = rendered(<ProgramConcentration hhi={hhi} />);
    const title = root.querySelector("span[title^='Herfindahl']")?.getAttribute("title") ?? "";
    const claims = hhiBandClaims(title);
    expect(claims.filter((c) => !c.ok).map((c) => c.finding)).toEqual([]);
    expect(new Set(claims.map((c) => c.kind))).toEqual(
      new Set(["vintage", "moderate-range", "high-line", "below"]),
    );
  });
});

describe("/methodology/ — the stage-2 binding", () => {
  it("renders, and leg (q) finds its concentration_shift passage and band claims to check", () => {
    const { pages } = legQ();
    const root = pages["/methodology/"];
    expect(root.querySelector("#feed-concentration_shift")).not.toBeNull();
    const claims = root
      .querySelectorAll("#feed-concentration_shift p")
      .flatMap((el) => hhiBandClaims(el.text));
    expect(claims.length).toBeGreaterThan(0);
  });

  /**
   * RED UNTIL STAGE 2 FIXES THE PROSE — then change `it.fails` to `it`.
   * Measured at e6bc28bb, leg (q) reports 13 errors on this page: in
   * #feed-concentration_shift, the band sentence (no vintage; the 2010 title
   * without "2010"; "competitive"; "1,800 or above"; "1,800 is the floor";
   * four equal shares = 1,800) and "a competitive pooled figure", plus the
   * passage lacking the vintage, "unconcentrated", its attribution and where
   * unconcentrated ends; in the corrections table, "DOJ/FTC bands" (no year)
   * and "it is the highly concentrated floor" of 2,500.
   */
  it.fails("states the HHI bands the badges use (leg q clean on /methodology/)", () => {
    const { errors } = legQ();
    expect(errors.filter((e) => e.includes("/methodology/"))).toEqual([]);
  });
});
