/**
 * ROADMAP #173 — gate 24 (datatruth) leg e recounts /methodology/'s "{N} dbt
 * data-model assertions" from dbt/target/manifest.json. Until 2026-09-25 it
 * SKIPPED the dbt comparison when that file was missing (`if
 * (fs.existsSync(dbtManifest))`), so a build that printed the shared lake's
 * number — getSiteMeta's fallback, now removed — passed the leg untested.
 * dbt/target/ is gitignored: a fresh checkout has no manifest until dbt runs.
 *
 * dbtManifestRecount is the leg's recount, pure: a count, or the error the
 * leg raises. A missing, unreadable or test-free manifest is an error, never
 * a skip.
 *
 * Run via `npm test` (vitest).
 */
import { describe, it, expect } from "vitest";
import fs from "fs";
import os from "os";
import path from "path";
import { fileURLToPath } from "url";
import { dbtManifestRecount } from "../datatruth.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function tmpManifest(body) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "dt-manifest-"));
  const p = path.join(dir, "manifest.json");
  fs.writeFileSync(p, body);
  return p;
}

describe("dbtManifestRecount (gate 24 leg e, #173)", () => {
  it("counts test nodes only", () => {
    const p = tmpManifest(
      JSON.stringify({
        nodes: {
          "test.x": { resource_type: "test" },
          "model.y": { resource_type: "model" },
          "test.z": { resource_type: "test" },
          "test.w": { resource_type: "test" },
        },
      }),
    );
    expect(dbtManifestRecount(p)).toEqual({ count: 3, error: null });
  });

  it("is an error, not a skip, when the manifest is missing", () => {
    const r = dbtManifestRecount(path.join(os.tmpdir(), "no-such-dir-173", "manifest.json"));
    expect(r.count).toBeNull();
    expect(r.error).toMatch(/missing/);
    expect(r.error).toMatch(/dbt data-model assertions/);
  });

  it("is an error when the manifest is unreadable", () => {
    const r = dbtManifestRecount(tmpManifest("{"));
    expect(r.count).toBeNull();
    expect(r.error).toMatch(/unreadable/);
  });

  it("is an error when the manifest holds no test nodes", () => {
    const r = dbtManifestRecount(tmpManifest(JSON.stringify({ nodes: { "model.a": { resource_type: "model" } } })));
    expect(r.count).toBeNull();
    expect(r.error).toMatch(/no test nodes/);
  });

  it("leg e no longer guards the dbt recount behind an existsSync skip", () => {
    const src = fs.readFileSync(path.resolve(__dirname, "..", "datatruth.mjs"), "utf8");
    const legE = src.slice(src.indexOf("// ── leg e:"), src.indexOf("// ── leg f:"));
    expect(legE).toContain("dbtManifestRecount(");
    expect(legE).not.toMatch(/if \(fs\.existsSync\(dbtManifest\)\)/);
  });
});
