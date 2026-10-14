/**
 * direct-run.mjs (ROADMAP #201). Five scripts compared process.argv[1] with
 * their own path as strings; node resolves the main module's symlinks for
 * import.meta.url but leaves argv[1] as typed, so a run through a symlinked
 * spelling skipped the body and exited 0 having checked nothing.
 */
import fs from "fs";
import os from "os";
import path from "path";
import { spawnSync } from "child_process";
import { fileURLToPath, pathToFileURL } from "url";
import { afterEach, describe, expect, it } from "vitest";
import { isDirectRun } from "../direct-run.mjs";

const SCRIPTS = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SNAPSHOT = path.join(SCRIPTS, "f15-page-snapshot.mjs");
const GUARDED = ["f15-page-snapshot.mjs", "generate-feeds.mjs", "run-mobile-leg.mjs", "serve-static.mjs", "gates/basis.mjs"];

const dirs = [];
function linkTo(target) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "direct-run-"));
  dirs.push(dir);
  const link = path.join(dir, path.basename(target));
  fs.symlinkSync(target, link);
  return link;
}
afterEach(() => { for (const dir of dirs.splice(0)) fs.rmSync(dir, { recursive: true, force: true }); });

describe("isDirectRun", () => {
  const url = pathToFileURL(SNAPSHOT).href;

  it("is true for the module's own path and for a symlink to it", () => {
    expect(isDirectRun(url, SNAPSHOT)).toBe(true);
    expect(isDirectRun(url, linkTo(SNAPSHOT))).toBe(true);
  });

  it("is false for another file, a missing path or no argv[1]", () => {
    expect(isDirectRun(url, path.join(SCRIPTS, "verify.mjs"))).toBe(false);
    expect(isDirectRun(url, path.join(SCRIPTS, "no-such-script.mjs"))).toBe(false);
    expect(isDirectRun(url, undefined)).toBe(false);
  });
});

describe("the five guarded scripts", () => {
  it("guard their body with isDirectRun, never a string comparison of argv[1]", () => {
    for (const rel of GUARDED) {
      const src = fs.readFileSync(path.join(SCRIPTS, rel), "utf8");
      expect(src, rel).toMatch(/if \(isDirectRun\(import\.meta\.url\)\)/);
      expect(src, rel).not.toMatch(/process\.argv\[1\]\s*(===|&&)|path\.resolve\(process\.argv\[1\]\)/);
    }
  });

  it("f15-page-snapshot run through a symlink checks its arguments instead of exiting 0", () => {
    const run = spawnSync(process.execPath, [linkTo(SNAPSHOT)], { encoding: "utf8" });
    expect(run.status).toBe(2);
    expect(run.stderr).toContain("usage: node scripts/f15-page-snapshot.mjs");
  });
});
