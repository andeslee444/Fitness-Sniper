/**
 * Gate 24 leg (l) — two structural checks added by Task 29 fix round 1.
 *
 * 1. THE CENSUS COVERS THE PUBLISHED SET. familylabel-recompute.py skips a
 *    published family whose dominant member has no parent registration or a
 *    zero top registration, but still reports `published: 200`. Leg l built
 *    its census from the families it MEASURED, so one skip turned a true page
 *    sentence ("Among the 200 families we publish…") into a confusing
 *    "…199…" mismatch, and the skipped family never met the 15% rule. The
 *    leg now names the skipped keys instead.
 *
 * 2. NO TWO PUBLISHED FAMILIES RENDER ONE NAME. The Brown & Root holding
 *    family publishes as "KBR Wyle Services LLC" (its recipients' own
 *    registered name; the live branch's label, ruling R-INT-4 — it was
 *    "KBR Wyle Services, LLC"), and a separate registry family, KBR WYLE
 *    SERVICES (rank 488 on 2026-09-25), carries that name as "KBR WYLE
 *    SERVICES, LLC". Outside the top 200 it has no company page and no
 *    /companies/ row; if it ever enters the published set, two rows would
 *    read the same, so the leg fails until one is qualified. The comparison
 *    ignores case, spacing and punctuation: without the comma the two
 *    strings differ only in it, and a case/space-only key missed the pair.
 *
 * Pure helpers, fixtures only — no recompute, no build.
 */

import { describe, it, expect } from "vitest";
import {
  familyCoverageFindings,
  publishedNameCollisions,
} from "../datatruth.mjs";

const fam = (family_key, display_name, margin = 1) => ({
  family_key,
  display_name,
  margin,
  total_obligation: 1e9,
});

describe("familyCoverageFindings — the census counts the whole published set", () => {
  it("is silent when every published family was measured", () => {
    const truth = { families: [fam("A", "A INC"), fam("B", "B INC")], published: 2 };
    expect(familyCoverageFindings(truth)).toEqual([]);
  });

  it("names the families the recompute skipped", () => {
    const truth = {
      families: [fam("A", "A INC")],
      published: 2,
      unmeasured: [{ family_key: "B", reason: "no parent registration" }],
    };
    const findings = familyCoverageFindings(truth);
    expect(findings).toHaveLength(1);
    expect(findings[0]).toContain("measured 1 of 2 published families");
    expect(findings[0]).toContain("B (no parent registration)");
  });

  it("still fails when an older recompute does not name them", () => {
    const findings = familyCoverageFindings({ families: [fam("A", "A INC")], published: 2 });
    expect(findings).toHaveLength(1);
    expect(findings[0]).toContain("not named by the recompute");
  });

  it("fails when the recompute reports no published count at all", () => {
    expect(familyCoverageFindings({ families: [fam("A", "A INC")] })).toHaveLength(1);
  });
});

describe("publishedNameCollisions — one name, one published family", () => {
  const aliases = new Map([
    ["BROWN ROOT INDUSTRIAL SERVICES HOLDINGS", { label: "KBR Wyle Services LLC", evidence: "measured" }],
  ]);

  it("is silent while the registry family holding the same string is unpublished", () => {
    const published = [
      fam("BROWN ROOT INDUSTRIAL SERVICES HOLDINGS", "BROWN & ROOT INDUSTRIAL SERVICES HOLDINGS, LLC"),
      fam("KBR", "KBR, INC."),
    ];
    expect(publishedNameCollisions(published, aliases)).toEqual([]);
  });

  it("FAILS when that family enters the published set: a relabel and a registry string that read the same", () => {
    const published = [
      fam("BROWN ROOT INDUSTRIAL SERVICES HOLDINGS", "BROWN & ROOT INDUSTRIAL SERVICES HOLDINGS, LLC"),
      fam("KBR WYLE SERVICES", "KBR WYLE SERVICES, LLC"),
    ];
    const findings = publishedNameCollisions(published, aliases);
    expect(findings).toHaveLength(1);
    expect(findings[0]).toContain("BROWN ROOT INDUSTRIAL SERVICES HOLDINGS");
    expect(findings[0]).toContain("KBR WYLE SERVICES");
    expect(findings[0]).toContain('"KBR Wyle Services LLC"');
  });

  it("FAILS on a relabel and a registry string that differ only in punctuation", () => {
    // The pair above, isolated: the seed label drops the comma the registry
    // string keeps ("KBR Wyle Services LLC" vs "KBR WYLE SERVICES, LLC").
    const findings = publishedNameCollisions(
      [fam("ACME HOLDINGS", "ACME HOLDINGS INC"), fam("ACME", "ACME CORP., L.L.C.")],
      new Map([["ACME HOLDINGS", { label: "Acme Corp LLC", evidence: "measured" }]]),
    );
    expect(findings).toHaveLength(1);
    expect(findings[0]).toContain('"Acme Corp LLC"');
  });

  it("FAILS on two registry strings that differ only in case or spacing", () => {
    const findings = publishedNameCollisions(
      [fam("ACME ONE", "ACME CORP"), fam("ACME TWO", "Acme  Corp")],
      new Map(),
    );
    expect(findings).toHaveLength(1);
  });
});
