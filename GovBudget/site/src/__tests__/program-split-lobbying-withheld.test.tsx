/**
 * R-INT-9 (integration ruling, 2026-09-25) — a shared-code member page states
 * that lobbying evidence is withheld; it never answers WHO GETS IT from it.
 *
 * THE DEFECT. #82 sent every `pe_literal` lobbying row on a shared budget-line
 * code to every member page, on the premise that a bare code in a filing
 * names the line. For the numeric codes it does not: '20' matched "H.R. 20"
 * (the PRO Act), '30' matched dates ("fiscal year ending September 30")
 * and one public-law number ("P.L. 117-30"), and '500' matched "2,500
 * megahertz". The merged build then published, above the
 * fold on /program/20-DTRA/, /program/30-OSD/ and five more pages, that
 * companies "named this program in Senate lobbying filings". Production
 * (live 2c7ebbb0 / c2ac0b90) withholds: on a split member the exporter ships
 * mentions [], lobbied_by null and named_primes [], and the page's empty
 * state says why. R-INT-9 restores that; #82's per-member narratives and
 * details are unchanged.
 *
 * WHAT THIS PINS — the page half, for the payload the exporter ships:
 *   1. the Lobbying Mentions section renders the live empty state, verbatim;
 *   2. the WHO GETS IT answer never takes the lobbying tier (no badge, no
 *      names, no "named this program" sentence) and never the J-book tier;
 *   3. a page that does NOT share its code keeps the ordinary empty state —
 *      the shared-code sentence is not a blanket replacement.
 *   4. the shipped export itself withholds all three on every member of a
 *      shared code. DATA-PENDING until export-site re-runs with the R-INT-9
 *      exporter; red on an export that predates it, which is the point.
 *
 * Same seams as the /district/ page tests: the page is an async server
 * component whose data door is @/lib/data. Every member is rendered from its
 * REAL sidecar with only the three withheld fields forced, so the rest of the
 * page (awards, withheld concentration, header) is the shipped shape.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/react";
import React from "react";
import fs from "fs";
import path from "path";
import type { ProgramDetails } from "@/lib/data";

vi.mock("@/components/citation-panel", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/components/citation-panel")>()),
  CitationPanelProvider: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
}));

/** Slugs whose sidecar the test rewrites to the withheld shape. */
const WITHHELD = new Set<string>();
/** Slugs whose sidecar the test strips of mentions only (the control). */
const NO_MENTIONS = new Set<string>();

vi.mock("@/lib/data", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/lib/data")>();
  return {
    ...real,
    getProgramDetails: (slug: string): ProgramDetails => {
      const d = real.getProgramDetails(slug);
      if (WITHHELD.has(slug)) {
        return {
          ...d,
          mentions: [],
          summary: { ...d.summary, lobbied_by: null, named_primes: [] },
        };
      }
      if (NO_MENTIONS.has(slug)) return { ...d, mentions: [] };
      return d;
    },
  };
});

afterEach(() => {
  cleanup();
  WITHHELD.clear();
  NO_MENTIONS.clear();
});

const SHARED_EMPTY =
  "This code is shared by more than one budget line. No lobbying matches are assigned to this specific account or organization.";
const ORDINARY_EMPTY =
  "No Senate LDA lobbying filing in the tracked data mentions this program element by code or alias.";

const norm = (s: string | null | undefined) => (s ?? "").replace(/\s+/g, " ").trim();

async function renderProgram(slug: string) {
  const Page = (await import("@/app/program/[peBli]/page")).default;
  const el = await Page({ params: Promise.resolve({ peBli: slug }) });
  return render(el as React.ReactElement).container;
}

/**
 * The members the review measured, one per shape:
 *   30-OSD     organization split, no awards — production renders "none";
 *              the merged build rendered the lobbying tier here.
 *   20-DTRA    organization split, the "H.R. 20" rows.
 *   0145-PANMC account split, linked awards, concentration withheld (#82).
 *   2292-WPN   account split, a published concentration row, 18 rows before.
 */
const MEMBERS = ["30-OSD", "20-DTRA", "0145-PANMC", "2292-WPN"];

describe("R-INT-9: a shared-code member page withholds lobbying evidence", () => {
  it.each(MEMBERS)("%s renders the live empty state in Lobbying Mentions", async (slug) => {
    WITHHELD.add(slug);
    const c = await renderProgram(slug);
    const section = c.querySelector('section[data-section="lobbying"]');
    expect(section, "no lobbying section").not.toBeNull();
    expect(norm(section!.querySelector("[data-section-empty]")?.textContent)).toBe(SHARED_EMPTY);
    expect(norm(section!.textContent)).not.toContain(ORDINARY_EMPTY);
    expect(section!.querySelector('a[href*="lda.senate.gov"]')).toBeNull();
  });

  it.each(MEMBERS)("%s answers WHO GETS IT from neither the lobbying nor the J-book tier", async (slug) => {
    WITHHELD.add(slug);
    const c = await renderProgram(slug);
    const tiers = [...c.querySelectorAll("[data-who-tier]")].map((e) =>
      e.getAttribute("data-who-tier"),
    );
    expect(tiers).toHaveLength(1);
    expect(["award", "none"]).toContain(tiers[0]);
    expect(c.querySelector("[data-who-lobby-badge]")).toBeNull();
    expect(c.querySelector("[data-who-name]")).toBeNull();
    expect(norm(c.textContent)).not.toContain("named this program in Senate lobbying filings");
    expect(norm(c.textContent)).not.toContain("Named in the J-book");
  });

  it("a page that does not share its code keeps the ordinary empty state", async () => {
    const slug = "0601101E";
    NO_MENTIONS.add(slug);
    const c = await renderProgram(slug);
    const section = c.querySelector('section[data-section="lobbying"]');
    expect(norm(section!.querySelector("[data-section-empty]")?.textContent)).toBe(ORDINARY_EMPTY);
    expect(norm(section!.textContent)).not.toContain("shared by more than one budget line");
  });
});

describe("R-INT-9: the shipped export withholds all three on every shared-code member (DATA-PENDING until export-site re-runs)", () => {
  const json = path.resolve(__dirname, "..", "..", "..", "data", "site", "json");
  const programs = JSON.parse(
    fs.readFileSync(path.join(json, "programs.json"), "utf8"),
  ) as { pe_bli: string; slug: string }[];
  const count = new Map<string, number>();
  for (const p of programs) count.set(p.pe_bli, (count.get(p.pe_bli) ?? 0) + 1);
  const members = programs.filter((p) => (count.get(p.pe_bli) ?? 0) > 1);

  it("the corpus still has shared-code members to check (non-vacuity)", () => {
    // 27 members on 13 codes on the 2026-09-25 chain F export; gate 21 leg n
    // floors the same universe at 10 codes.
    expect(new Set(members.map((m) => m.pe_bli)).size).toBeGreaterThanOrEqual(10);
  });

  it("no member sidecar carries a mention, a lobbied_by block or a named prime", () => {
    const leaks: string[] = [];
    for (const { slug } of members) {
      const d = JSON.parse(
        fs.readFileSync(path.join(json, "program_details", `${slug}.json`), "utf8"),
      ) as ProgramDetails;
      if ((d.mentions ?? []).length) leaks.push(`${slug}: ${d.mentions.length} mention(s)`);
      if (d.summary?.lobbied_by) leaks.push(`${slug}: lobbied_by`);
      if ((d.summary?.named_primes ?? []).length) leaks.push(`${slug}: named_primes`);
    }
    expect(leaks).toEqual([]);
  });
});
