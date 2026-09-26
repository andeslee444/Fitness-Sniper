import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { GLOSSARY } from "../glossary";

// URL-safe anchor id: lowercase letters, digits, hyphens only — matches
// what /glossary/#id and a future citation-drawer deep link can both use
// without percent-encoding.
const URL_SAFE_ID_RE = /^[a-z0-9]+(-[a-z0-9]+)*$/;

describe("GLOSSARY", () => {
  it("is non-empty", () => {
    expect(GLOSSARY.length).toBeGreaterThan(0);
  });

  it("gives every entry a non-empty term, expansion, and definition", () => {
    for (const entry of GLOSSARY) {
      expect(entry.term.trim().length, `${entry.id}: term`).toBeGreaterThan(0);
      expect(entry.expansion.trim().length, `${entry.id}: expansion`).toBeGreaterThan(0);
      expect(entry.definition.trim().length, `${entry.id}: definition`).toBeGreaterThan(0);
    }
  });

  it("gives every entry a URL-safe id", () => {
    for (const entry of GLOSSARY) {
      expect(entry.id, entry.id).toMatch(URL_SAFE_ID_RE);
    }
  });

  it("has unique ids", () => {
    const ids = GLOSSARY.map((e) => e.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("has unique terms (case-insensitive) — no two entries claim the same stamped term", () => {
    const terms = GLOSSARY.map((e) => e.term.toLowerCase());
    expect(new Set(terms).size).toBe(terms.length);
  });

  it("defines TOA (ROADMAP #60 — the term stamped on ~80,000 figures sitewide)", () => {
    const toa = GLOSSARY.find((e) => e.id === "toa");
    expect(toa).toBeDefined();
    expect(toa?.expansion.toLowerCase()).toContain("total obligational authority");
  });
});

// Decisions wave fix round 5 (#175, 2026-09-26). Fix round 4 set the program
// page's heading in sentence case ("Contractor concentration",
// program-concentration.tsx) and burned down its leg-29 exemptions; the HHI
// entry still pointed readers at the "Contractor Concentration card", a name
// no page renders. The glossary names the card by the heading a reader sees.
describe("GLOSSARY — the HHI entry names the concentration card as the page does", () => {
  const heading = (() => {
    const src = readFileSync(
      resolve(__dirname, "../../components/program-concentration.tsx"),
      "utf8",
    );
    const m = /id="concentration-heading"[^>]*>\s*([^<{]+?)\s*<\/h2>/.exec(src);
    return m?.[1].replace(/\s+/g, " ").trim();
  })();

  it("reads the heading from the component (non-vacuity)", () => {
    expect(heading).toBe("Contractor concentration");
  });

  it("calls it the Contractor concentration card, never the Title Case name", () => {
    const hhi = GLOSSARY.find((e) => e.id === "hhi");
    expect(hhi).toBeDefined();
    expect(hhi!.definition).toContain(`Each program page's ${heading} card reports`);
    expect(hhi!.definition).not.toMatch(/Contractor Concentration/);
  });
});
