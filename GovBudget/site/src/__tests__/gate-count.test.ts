/**
 * /methodology/ §3 prints "{N} site verification gates". N must be THIS
 * checkout's registry in scripts/verify.mjs, never the number the last
 * export-site wrote into the shared lake's site_meta.json (integration
 * 2026-09-25: the merged registry holds 27 gates; the pre-merge export's
 * site_meta says 24, the live branch's build printed 27 through the same
 * build-time recount).
 *
 * Three rules keep that number honest:
 *   1. The registry has one shape: every gate registers once, as
 *      gateResults.push({ n: N, name: "…" }), numbered 1..N with no gap or
 *      repeat — so "count the registrations" and "count the gates" are the
 *      same number (the rule the exporter, getSiteMeta and gate 24 leg e all
 *      apply).
 *   2. getSiteMeta() carries that count, whatever site_meta.json says.
 *   3. The page renders the derived value, never a typed number.
 */
import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";
import { getSiteMeta } from "@/lib/data";

const SITE = path.resolve(__dirname, "..", "..");
const verify = fs.readFileSync(path.join(SITE, "scripts", "verify.mjs"), "utf8");

/** Every registration, parsed with its number AND its name. */
const registry = [...verify.matchAll(/gateResults\.push\(\{\s*n:\s*(\d+),\s*name:\s*"([^"]+)"/g)].map(
  (m) => ({ n: Number(m[1]), name: m[2] }),
);

describe("the site-gate count on /methodology/ is the verify.mjs registry", () => {
  it("registers each gate once, numbered 1..N without a gap", () => {
    // The count rule the exporter/loader/gate share: a bare push count.
    const pushes = (verify.match(/gateResults\.push\(\{\s*n:\s*\d+/g) ?? []).length;
    expect(registry.length).toBe(pushes);
    const numbers = registry.map((g) => g.n).sort((a, b) => a - b);
    expect(numbers).toEqual(Array.from({ length: numbers.length }, (_, i) => i + 1));
    expect(new Set(registry.map((g) => g.name)).size).toBe(registry.length);
    // Measured at the 2026-09-25 integration merge: this branch registered
    // gates 1–24; the live branch added 25 tokens, 26 type and 27 copy.
    expect(registry.length).toBe(27);
  });

  it("getSiteMeta() carries the registry's count, not the exported one", () => {
    expect(getSiteMeta().build_checks?.npm_gates).toBe(registry.length);
  });

  it("§3 renders the derived count, never a typed number", () => {
    const page = fs
      .readFileSync(path.join(SITE, "src", "app", "methodology", "page.tsx"), "utf8")
      .replace(/\s+/g, " ");
    expect(page).toContain('{buildChecks.npm_gates ?? "—"} site verification gates');
    expect(page).not.toMatch(/\d+ site verification gates/);
  });
});
