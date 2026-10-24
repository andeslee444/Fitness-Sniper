/**
 * Gate 21 (program-skeleton) leg (r) — families piece 2, spec 2026-10-20 §13.
 *
 * json/families/index.json lists the published platform families. Every
 * family it lists must have its own history artifact in data/site/json and a
 * built page at out/families/<id>/index.html. A missing or empty index fails
 * closed rather than skipping (D8, K1).
 *
 * Pure helper, temporary-directory fixtures only — no export, no build.
 */

import { describe, it, expect, afterEach } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { checkFamilyIndex } from "../family-history.mjs";

const F15 = { history: "json/f15_funding_history.json", history_dataset: "f15_funding_history", members: [],
              platform_family: "f-15", route: "/families/f-15/", ruling_ids: ["R-DEC-FAM-F15-SEED"], short_name: "F-15" };
const F35 = { ...F15, history: "json/f35_funding_history.json", history_dataset: "f35_funding_history",
              platform_family: "f-35", route: "/families/f-35/", ruling_ids: ["R-DEC-FAM-F35-B1"], short_name: "F-35" };

const roots = [];

/**
 * Build <tmp>/data/site/json/… and <tmp>/out/families/<id>/index.html.
 * `index` is written as JSON when it is an object and verbatim when it is a
 * string; when it is undefined no index file is written. `histories` names
 * json/<dataset>.json files; `pages` names family ids whose page is built.
 */
function tree({ index, histories = [], pages = [] }) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "family-index-"));
  roots.push(root);
  const data = path.join(root, "data", "site");
  const out = path.join(root, "out");
  fs.mkdirSync(path.join(data, "json", "families"), { recursive: true });
  fs.mkdirSync(out, { recursive: true });
  if (index !== undefined) {
    const text = typeof index === "string" ? index : JSON.stringify(index);
    fs.writeFileSync(path.join(data, "json", "families", "index.json"), text);
  }
  for (const dataset of histories) fs.writeFileSync(path.join(data, "json", `${dataset}.json`), "{}");
  for (const id of pages) {
    fs.mkdirSync(path.join(out, "families", id), { recursive: true });
    fs.writeFileSync(path.join(out, "families", id, "index.html"), "<!doctype html>");
  }
  return { data, out };
}

afterEach(() => {
  while (roots.length) fs.rmSync(roots.pop(), { recursive: true, force: true });
});

describe("checkFamilyIndex — every listed family has its history and its built page", () => {
  it("passes when each family has both", () => {
    const { data, out } = tree({ index: { families: [F15], schema_version: 1 }, histories: ["f15_funding_history"], pages: ["f-15"] });
    expect(checkFamilyIndex(data, out)).toEqual([]);
  });
  it("fails closed when the index is missing", () => {
    const { data, out } = tree({});
    expect(checkFamilyIndex(data, out)).toEqual(["json/families/index.json is missing"]);
  });
  it("fails on an index that is not JSON", () => {
    const { data, out } = tree({ index: "{", histories: ["f15_funding_history"], pages: ["f-15"] });
    const f = checkFamilyIndex(data, out);
    expect(f).toHaveLength(1);
    expect(f[0]).toMatch(/^json\/families\/index\.json is not JSON: /);
  });
  it("fails on a schema_version other than 1", () => {
    const { data, out } = tree({ index: { families: [F15], schema_version: 2 }, histories: ["f15_funding_history"], pages: ["f-15"] });
    const f = checkFamilyIndex(data, out);
    expect(f).toEqual(["json/families/index.json schema_version is 2, not 1"]);
  });
  it("fails when the index lists no family", () => {
    const { data, out } = tree({ index: { families: [], schema_version: 1 }, histories: ["f15_funding_history"], pages: ["f-15"] });
    const f = checkFamilyIndex(data, out);
    expect(f).toEqual(["json/families/index.json lists no family"]);
  });
  it("names a family whose history artifact is missing", () => {
    const { data, out } = tree({ index: { families: [F15], schema_version: 1 }, pages: ["f-15"] });
    const f = checkFamilyIndex(data, out);
    expect(f).toEqual(["f-15: json/f15_funding_history.json is missing"]);
  });
  it("names a family whose page is not built", () => {
    const { data, out } = tree({ index: { families: [F15], schema_version: 1 }, histories: ["f15_funding_history"] });
    const f = checkFamilyIndex(data, out);
    expect(f).toEqual(["f-15: families/f-15/index.html is not built"]);
  });
  it("reads each family's own history path, not a hard-coded F-15 one", () => {
    // index [F15, F35]; only the F-15 has its history and page
    const { data, out } = tree({ index: { families: [F15, F35], schema_version: 1 }, histories: ["f15_funding_history"], pages: ["f-15"] });
    const f = checkFamilyIndex(data, out);
    expect(f).toEqual(["f-35: json/f35_funding_history.json is missing", "f-35: families/f-35/index.html is not built"]);
  });
});
