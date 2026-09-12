/**
 * Unit tests for gate 13 leg (i)'s source scanner (batch review 1.2).
 *
 * THE DEFECT. https://fiscalreceipts.com/json/feed.json 404'd in production
 * and nothing caught it. Leg (i) was written for exactly that bug and could
 * not see it: it reads `<a href>` out of built HTML, and no anchor anywhere
 * on this site points at /json/feed.json — the file was reached only by a
 * client-side fetch() baked into a JS bundle. Four targets are in that same
 * position today (/json/years_matrix.json, /json/flow_chart.json,
 * /config.json, /json-lite/search_quick.json): if one goes missing the
 * feature spins and errors, and every gate stays green.
 *
 * So the leg now also scans site/src for statically named fetch targets —
 * and, since ROADMAP #88 moved "Show all" to the directory-templated
 * /json/feed-sections/${eventType}.json, for that shape too. These tests
 * pin what "statically named" and "directory-templated" mean: a scanner
 * that over-reaches invents paths that never shipped, and one that
 * under-reaches is the miss it was written to close.
 *
 * Run via `npm test` (vitest).
 */

import path from "path";
import { fileURLToPath } from "url";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "fs";
import os from "os";
import {
  runJsonXmlHrefLeg,
  sameOriginJsonXmlTarget,
  scanFetchTargets,
  scanTemplatedFetchDirs,
  staticFetchTargets,
  templatedDirIsShipped,
  templatedFetchDirs,
} from "../linkgraph.mjs";

const srcDir = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
  "..",
  "..",
  "src",
);

describe("staticFetchTargets — the shapes it must catch", () => {
  it("finds a double-quoted absolute path", () => {
    expect(
      staticFetchTargets(`const resp = await fetch("/json/feed.json");`),
    ).toEqual(["/json/feed.json"]);
  });

  it("finds single-quoted and backtick literals", () => {
    expect(staticFetchTargets(`fetch('/config.json')`)).toEqual(["/config.json"]);
    expect(staticFetchTargets("fetch(`/json/flow_chart.json`)")).toEqual([
      "/json/flow_chart.json",
    ]);
  });

  it("finds a template literal whose static prefix is already a complete path", () => {
    expect(staticFetchTargets("fetch(`/json/feed.json?v=${build}`)")).toEqual([
      "/json/feed.json",
    ]);
  });

  it("strips query and hash so the target names a file", () => {
    expect(staticFetchTargets(`fetch("/json/feed.json?v=2#top")`)).toEqual([
      "/json/feed.json",
    ]);
  });

  it("survives whitespace and a multi-line call", () => {
    expect(
      staticFetchTargets(`const p = fetch(\n      "/json-lite/search_quick.json",\n    );`),
    ).toEqual(["/json-lite/search_quick.json"]);
  });

  it("de-duplicates and sorts", () => {
    expect(
      staticFetchTargets(`fetch("/b.json"); fetch("/a.json"); fetch("/b.json");`),
    ).toEqual(["/a.json", "/b.json"]);
  });
});

describe("staticFetchTargets — the shapes it must NOT invent", () => {
  it("ignores a per-row templated path (its existence is a sidecar question)", () => {
    expect(
      staticFetchTargets(
        "const r = await fetch(`/json-lite/program_details/${peBli}.json`);",
      ),
    ).toEqual([]);
  });

  it("ignores an asset-host base URL", () => {
    expect(
      staticFetchTargets(
        "const probe = await fetch(`${assetBase}/data/${probeName}.parquet`);",
      ),
    ).toEqual([]);
  });

  it("ignores a fetch whose URL comes from a helper call", () => {
    expect(
      staticFetchTargets(`fetch(assetUrl("/citations/citations.parquet"))`),
    ).toEqual([]);
    expect(staticFetchTargets("fetch(breakdownUrl(factId))")).toEqual([]);
  });

  it("ignores an absolute external URL", () => {
    expect(
      staticFetchTargets(`fetch("https://example.test/json/feed.json")`),
    ).toEqual([]);
  });

  it("does not match a word ending in fetch", () => {
    expect(staticFetchTargets(`prefetch("/json/feed.json")`)).toEqual([]);
  });
});

describe("scanFetchTargets — against the real site/src", () => {
  it("finds the four statically named targets the client depends on", () => {
    const found = scanFetchTargets(srcDir);
    // Measured 2026-09-04 at five; RE-MEASURED 2026-09-05 (ROADMAP #88):
    // /json/feed.json left this list when FeedSectionExpand moved to the
    // directory-templated /json/feed-sections/${eventType}.json, which the
    // templated sweep below counts. This is the population
    // MIN_STATIC_FETCH_TARGETS floors. Adding a target is fine; losing one
    // without re-measuring is the regression the floor exists to catch.
    expect([...found.keys()].sort()).toEqual([
      "/config.json",
      "/json-lite/search_quick.json",
      "/json/flow_chart.json",
      "/json/years_matrix.json",
    ]);
    expect(found.has("/json/feed.json")).toBe(false);
  });

  it("does not pick targets out of test files' fetch mocks", () => {
    const found = scanFetchTargets(srcDir);
    for (const sources of found.values()) {
      for (const f of sources) {
        expect(f).not.toMatch(/__tests__|\.test\.tsx?$/);
      }
    }
  });
});

describe("templatedFetchDirs — directory-templated targets (ROADMAP #88)", () => {
  it("finds a static directory prefix with one interpolated .json segment", () => {
    expect(
      templatedFetchDirs("const resp = await fetch(`/json/feed-sections/${eventType}.json`);"),
    ).toEqual(["/json/feed-sections/"]);
    expect(
      templatedFetchDirs("fetch(`/json-lite/program_details/${peBli}.json`)"),
    ).toEqual(["/json-lite/program_details/"]);
  });

  it("accepts an .xml extension and an expression inside the interpolation", () => {
    expect(templatedFetchDirs("fetch(`/feeds/${encodeURIComponent(t)}.xml`)")).toEqual([
      "/feeds/",
    ]);
  });

  it("leaves fully static literals to staticFetchTargets", () => {
    expect(templatedFetchDirs(`fetch("/json/feed.json")`)).toEqual([]);
    expect(templatedFetchDirs("fetch(`/json/feed.json?v=${build}`)")).toEqual([]);
  });

  it("ignores an asset-host base URL and helper-call URLs", () => {
    expect(templatedFetchDirs("fetch(`${assetBase}/data/${probeName}.parquet`)")).toEqual([]);
    expect(templatedFetchDirs("fetch(breakdownUrl(factId))")).toEqual([]);
  });

  it("ignores an interpolation that is not the last path segment", () => {
    // `/json/${kind}/index.json` — the DIRECTORY is dynamic; nothing static
    // enough to assert shipped.
    expect(templatedFetchDirs("fetch(`/json/${kind}/index.json`)")).toEqual([]);
  });

  it("de-duplicates and sorts", () => {
    expect(
      templatedFetchDirs("fetch(`/b/${x}.json`); fetch(`/a/${y}.json`); fetch(`/b/${z}.json`)"),
    ).toEqual(["/a/", "/b/"]);
  });
});

describe("scanTemplatedFetchDirs — against the real site/src", () => {
  it("finds the two directory-templated targets the client depends on", () => {
    const found = scanTemplatedFetchDirs(srcDir);
    // Measured 2026-09-05: program_details/ (program-awards.tsx:105,
    // program-mentions.tsx:235) and feed-sections/ (feed-section-expand.tsx).
    // This is the population MIN_TEMPLATED_FETCH_DIRS floors.
    expect([...found.keys()].sort()).toEqual([
      "/json-lite/program_details/",
      "/json/feed-sections/",
    ]);
    expect(found.get("/json/feed-sections/")).toEqual([
      "components/feed-section-expand.tsx",
    ]);
  });
});

describe("templatedDirIsShipped — the directory must exist AND hold a file", () => {
  let root;
  beforeEach(() => {
    root = fs.mkdtempSync(path.join(os.tmpdir(), "leg-i-dirs-"));
  });
  afterEach(() => {
    fs.rmSync(root, { recursive: true, force: true });
  });

  it("is false for a missing directory", () => {
    expect(templatedDirIsShipped("/json/feed-sections/", root)).toBe(false);
  });

  it("is false for an empty directory (a mirror copy that never ran)", () => {
    fs.mkdirSync(path.join(root, "json", "feed-sections"), { recursive: true });
    expect(templatedDirIsShipped("/json/feed-sections/", root)).toBe(false);
  });

  it("is false when the directory holds no .json/.xml", () => {
    fs.mkdirSync(path.join(root, "json", "feed-sections"), { recursive: true });
    fs.writeFileSync(path.join(root, "json", "feed-sections", "README.txt"), "x");
    expect(templatedDirIsShipped("/json/feed-sections/", root)).toBe(false);
  });

  it("is true once one .json is present", () => {
    fs.mkdirSync(path.join(root, "json", "feed-sections"), { recursive: true });
    fs.writeFileSync(path.join(root, "json", "feed-sections", "yoy_swing.json"), "{}");
    expect(templatedDirIsShipped("/json/feed-sections/", root)).toBe(true);
  });
});

describe("sameOriginJsonXmlTarget — the href half of leg (i)", () => {
  it("keeps a relative .json/.xml path", () => {
    expect(sameOriginJsonXmlTarget("/feeds/program/000074.xml")).toBe(
      "/feeds/program/000074.xml",
    );
  });

  it("unwraps the absolute self-URL every SubscribeLinks renders", () => {
    // The bug leg (i) exists for: lib/feeds.ts's abs() emits absolute
    // self-URLs, and the other legs' `href.startsWith("http")` check dropped
    // every one of them as external.
    expect(sameOriginJsonXmlTarget("https://fiscalreceipts.com/rss.xml")).toBe(
      "/rss.xml",
    );
  });

  it("strips query and hash", () => {
    expect(sameOriginJsonXmlTarget("/rss.xml?utm=1#top")).toBe("/rss.xml");
  });

  it("ignores a genuinely external URL", () => {
    expect(sameOriginJsonXmlTarget("https://example.test/rss.xml")).toBeNull();
  });

  it("ignores same-origin links that are not .json/.xml", () => {
    expect(sameOriginJsonXmlTarget("/program/0601101E/")).toBeNull();
    expect(sameOriginJsonXmlTarget("/citations/citations.parquet")).toBeNull();
  });

  it("ignores an empty or missing href", () => {
    expect(sameOriginJsonXmlTarget("")).toBeNull();
    expect(sameOriginJsonXmlTarget(undefined)).toBeNull();
  });
});

describe("runJsonXmlHrefLeg — the href floor must not be backfilled by fetch targets", () => {
  // Regression: a `checked` counter shared by the href sweep and the
  // fetch-target sweep meant `checked === 0` could never fire once the
  // real site/src's >= MIN_STATIC_FETCH_TARGETS static fetch targets were
  // found — an href-sweep regression (broken selector, empty page set)
  // would pass green. A `pages` list that resolves to nothing built (no
  // file under site/out for any of these URLs) forces the href sweep to
  // zero while scanFetchTargets(srcDir) still runs for real and finds its
  // usual targets, proving the two counters are independent.
  const NEVER_BUILT_PAGES = ["/__leg_i_regression_test__/no-such-page/"];

  it("errors on zero hrefs even though real fetch targets are present", () => {
    const errors = [];
    const notes = [];
    runJsonXmlHrefLeg(errors, notes, NEVER_BUILT_PAGES);

    // Sanity: the fetch-target half really did find targets in this run —
    // otherwise this test would pass for the wrong reason (both zero).
    expect(scanFetchTargets(srcDir).size).toBeGreaterThan(0);

    expect(errors).toEqual(
      expect.arrayContaining([
        expect.stringContaining(
          "leg i: 0 same-origin .json/.xml hrefs found across scanned pages",
        ),
      ]),
    );
  });

  it("does not report the href sweep as a passing 'all resolve' note when it found zero", () => {
    const errors = [];
    const notes = [];
    runJsonXmlHrefLeg(errors, notes, NEVER_BUILT_PAGES);

    for (const note of notes) {
      expect(note).not.toMatch(/^leg i: \d+ same-origin target\(s\)/);
    }
  });
});
