/**
 * ROADMAP #208 (families piece-1 follow-ups design §3.5): getProgramDecadeCells
 * keys its map by `slug ?? pe_bli`, one entry per /years/ row, so a page that
 * looks a program up by its bare pe_bli finds nothing for the 27 rows of the
 * 13 shared budget-line codes. /agency/[org]/ did, and rendered "—" for the
 * FY24 figure on all 27 (measured on the 2026-10-04 build of /agency/N/,
 * /agency/DCSA/, /agency/DTRA/, /agency/OSD/, /agency/DMACT/, /agency/DHRA/
 * and /agency/DLA/). /programs/ has looked up by slug since Sprint E.
 *
 * Read from the page sources: the pages need data/site to render, and the
 * defect is the lookup key itself.
 */
import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";

const APP = path.resolve(__dirname, "..", "app");
const READERS = ["agency/[org]/page.tsx", "programs/page.tsx"];

/** Every argument passed to `<map>.get(…)` on the getProgramDecadeCells() map. */
function lookupKeys(file: string): string[] {
  const src = fs.readFileSync(path.join(APP, file), "utf8");
  const bound = /const (\w+) = getProgramDecadeCells\(\);/.exec(src);
  expect(bound, `${file} no longer binds getProgramDecadeCells()`).not.toBeNull();
  const name = bound![1];
  return [...src.matchAll(new RegExp(`\\b${name}\\.get\\(([^)]*)\\)`, "g"))].map((m) =>
    m[1].trim(),
  );
}

describe("decade-cell lookups key on the page slug (ROADMAP #208)", () => {
  it.each(READERS)("%s looks every program up by its slug", (file) => {
    const keys = lookupKeys(file);
    expect(keys.length).toBeGreaterThan(0);
    for (const key of keys) expect(key).toMatch(/^\w+\.slug$/);
  });
});
