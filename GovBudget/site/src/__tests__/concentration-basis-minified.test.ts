// @vitest-environment node
/**
 * The withheld-concentration reason survives the production minifier
 * (integration 2026-09-25).
 *
 * Every other test of CONCENTRATION_WITHHELD_REASON imports the SOURCE
 * module, and all of them passed while the built site printed "at least 32
 * contractor families" on all 472 withheld program pages of build 42eed1e4:
 * the SWC minifier Next 16.2.9 ships folds `…${3} awards across ` +
 * `${2} contractor…` into one string and drops " awards across ". This runs
 * the same SWC (next/dist/build/swc: transform, then minify) over the real
 * file and reads the constant out of the minified output — so the unit suite
 * sees what a reader sees without a site build. The built-HTML guards are
 * gate 14's feed-publication leg and gate 21 leg (j)
 * (scripts/gates/concentration-floor.mjs).
 */
import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";
import { createRequire } from "module";
import {
  CONCENTRATION_WITHHELD_REASON,
  HIGH_ONLY_MIN_AWARDS,
  HIGH_ONLY_MIN_FAMILIES,
} from "@/lib/concentration-basis";

const require = createRequire(import.meta.url);
const swc = require("next/dist/build/swc") as {
  loadBindings: () => Promise<unknown>;
  transform: (src: string, opts: object) => Promise<{ code: string }>;
  minify: (src: string, opts: object) => Promise<{ code: string }>;
};

async function minified(src: string): Promise<string> {
  await swc.loadBindings();
  const js = await swc.transform(src, {
    filename: "concentration-basis.ts",
    jsc: { parser: { syntax: "typescript" }, target: "es2022" },
    module: { type: "es6" },
  });
  return (await swc.minify(js.code, { compress: true, mangle: true, module: true })).code;
}

const SOURCE = fs.readFileSync(
  path.resolve(__dirname, "..", "lib", "concentration-basis.ts"),
  "utf8",
);

describe("CONCENTRATION_WITHHELD_REASON through the production minifier", () => {
  it("the minified bundle states the whole floor, word for word", async () => {
    const code = await minified(SOURCE);
    const clause =
      `at least ${HIGH_ONLY_MIN_AWARDS} awards across ` +
      `${HIGH_ONLY_MIN_FAMILIES} contractor families`;
    expect(CONCENTRATION_WITHHELD_REASON).toContain(clause);
    expect(code).toContain(JSON.stringify(CONCENTRATION_WITHHELD_REASON));
  });

  it("the defect it guards against is real: the split shape loses its words", async () => {
    // The pre-fix shape, verbatim. If a future SWC fixes the fold this
    // control goes red — delete the "ONE TEMPLATE LITERAL" note in
    // concentration-basis.ts with it, not the test above.
    const code = await minified(
      "const A = 3, F = 2;\n" +
        "export const R =\n" +
        "  `index — at least ${A} awards across ` +\n" +
        "  `${F} contractor families holding positive ` +\n" +
        "  `obligations.`;\n",
    );
    expect(code).toContain("at least 32 contractor families");
    expect(code).not.toContain("awards across");
  });
});
