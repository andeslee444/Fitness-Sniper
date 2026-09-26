/**
 * ROADMAP #173 — /methodology/ §3 prints "{N} dbt data-model assertions". N
 * must be THIS checkout's dbt manifest, never the number the last
 * export-site wrote into the shared lake's site_meta.json.
 *
 * Until 2026-09-25 getSiteMeta() recounted the manifest's test nodes only
 * when dbt/target/manifest.json existed: a missing manifest kept
 * site_meta.json's build_checks.dbt_assertions through the object spread,
 * and an unreadable one copied it back in the catch. dbt/target/ is
 * gitignored, so a fresh checkout or worktree has no manifest until dbt runs
 * — and then printed another checkout's count (measured 2026-09-25: the
 * shared site_meta carried 118 while the main checkout's manifest held 100).
 * The site-gate count already failed the build in that state (integration
 * 2026-09-25); the dbt count now does the same.
 */
import { describe, it, expect } from "vitest";
import fs from "fs";
import os from "os";
import path from "path";
import { dbtAssertionCount, getSiteMeta } from "@/lib/data";

const SITE = path.resolve(__dirname, "..", "..");
const REPO_MANIFEST = path.join(SITE, "..", "dbt", "target", "manifest.json");

function tmpManifest(body: string): string {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "dbt-manifest-"));
  const p = path.join(dir, "manifest.json");
  fs.writeFileSync(p, body);
  return p;
}

describe("dbtAssertionCount — the dbt count /methodology/ prints (#173)", () => {
  it("counts the manifest's test nodes and nothing else", () => {
    const p = tmpManifest(
      JSON.stringify({
        nodes: {
          "test.a": { resource_type: "test" },
          "test.b": { resource_type: "test" },
          "model.c": { resource_type: "model" },
          "seed.d": { resource_type: "seed" },
        },
      }),
    );
    expect(dbtAssertionCount(p)).toBe(2);
  });

  it("fails — it does not fall back — when the manifest is missing", () => {
    const missing = path.join(os.tmpdir(), "no-such-dir-173", "manifest.json");
    expect(() => dbtAssertionCount(missing)).toThrow(/missing/);
    expect(() => dbtAssertionCount(missing)).toThrow(/dbt/);
  });

  it("fails when the manifest is unreadable", () => {
    expect(() => dbtAssertionCount(tmpManifest("{ not json"))).toThrow(/unreadable/);
  });

  it("fails when the manifest holds no test nodes", () => {
    expect(() => dbtAssertionCount(tmpManifest(JSON.stringify({ nodes: {} })))).toThrow(/no test nodes/);
    expect(() => dbtAssertionCount(tmpManifest(JSON.stringify({})))).toThrow(/no test nodes/);
  });

  it("getSiteMeta() carries this checkout's count, whatever site_meta.json says", () => {
    // Throws, like the gate count, in a checkout with no manifest: run dbt
    // there first (`dbt parse` writes the manifest without building).
    const nodes = JSON.parse(fs.readFileSync(REPO_MANIFEST, "utf8")).nodes ?? {};
    const want = Object.values(nodes as Record<string, { resource_type?: string }>).filter(
      (n) => n.resource_type === "test",
    ).length;
    expect(dbtAssertionCount()).toBe(want);
    expect(getSiteMeta().build_checks?.dbt_assertions).toBe(want);
  });

  it("§3 renders the derived count, never a typed number", () => {
    const page = fs
      .readFileSync(path.join(SITE, "src", "app", "methodology", "page.tsx"), "utf8")
      .replace(/\s+/g, " ");
    expect(page).toContain("{buildChecks.dbt_assertions ?? \"—\"} dbt data-model assertions");
    expect(page).not.toMatch(/\d+ dbt data-model assertions/);
  });

  it("data.ts keeps no path that copies site_meta.json's dbt count back in", () => {
    const src = fs.readFileSync(path.join(SITE, "src", "lib", "data.ts"), "utf8");
    expect(src).not.toMatch(/fallback\?\.dbt_assertions/);
  });
});
