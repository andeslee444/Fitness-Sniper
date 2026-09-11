/**
 * Proof-can-fail for gate 13 leg (j) — the glossary is in the HEADER nav.
 *
 * THE DEFECT (tri-persona Wave 3, the layman review): /glossary/ was
 * linked twice on every page and BOTH links were in the footer, under
 * thousands of pixels of the jargon it defines — "the cure, hidden below
 * the disease". layout.tsx and mobile-nav.tsx fixed it; nothing pinned it.
 *
 * Leg (a) cannot pin it: leg (a) reads the whole home page, footer
 * included, so a footer-only glossary satisfies it. That blindness IS the
 * defect. These tests pin the scoped reader instead — including the
 * footer-only document, which leg (a) calls a pass.
 *
 * Run via `npm test` (vitest).
 */
import { describe, it, expect } from "vitest";
import { headerNavHrefs } from "../linkgraph.mjs";

// React renders `<nav data-site-nav>` as a valueless/empty attribute; the
// deployed redesign renders data-site-nav="true". Both must match.
const WITH_GLOSSARY = `<header><nav data-site-nav aria-label="Main navigation">` +
  `<a href="/programs/">Programs</a><a href="/glossary/">Glossary</a></nav></header>` +
  `<footer><a href="/glossary/">Glossary</a></footer>`;

const FOOTER_ONLY = `<header><nav data-site-nav="" aria-label="Main navigation">` +
  `<a href="/programs/">Programs</a></nav></header>` +
  `<footer><a href="/glossary/">Glossary</a></footer>`;

const VALUED_ATTR = `<header><nav data-site-nav="true">` +
  `<a href="/programs/">Programs</a><a href="/glossary/">Glossary</a></nav></header>`;

describe("headerNavHrefs", () => {
  it("returns the header nav's own hrefs, in order", () => {
    expect(headerNavHrefs(WITH_GLOSSARY)).toEqual(["/programs/", "/glossary/"]);
  });

  it("matches data-site-nav=\"true\" as well as the valueless form", () => {
    expect(headerNavHrefs(VALUED_ATTR)).toContain("/glossary/");
  });

  it("PROOF IT CAN FAIL: a footer-only glossary is not in the header nav", () => {
    expect(headerNavHrefs(FOOTER_ONLY)).not.toContain("/glossary/");
  });

  it("returns null when the <nav data-site-nav> contract is gone", () => {
    expect(
      headerNavHrefs(`<header><nav><a href="/programs/">Programs</a></nav></header>`)
    ).toBeNull();
  });
});
