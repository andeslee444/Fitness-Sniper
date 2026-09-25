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
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { describe, it, expect } from "vitest";
import { headerNavHrefs, mobileNavGlossaryFindings } from "../linkgraph.mjs";

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

/**
 * Leg (j), mobile half, retargeted 2026-09-25. It read NAV_LINKS in
 * components/mobile-nav.tsx, which nothing imports since the merge, so it
 * passed against a file no reader is served. These tests pin the three
 * steps it now proves (mounted header → panel built from SITE_NAVIGATION →
 * /glossary/ in that list). Each step has a case showing it fails alone, and
 * the last test runs the helper against the shipped sources.
 */
const LAYOUT = `import { SiteHeader } from "@/components/site-header";
export default function RootLayout({ children }) {
  return (<body><SiteHeader /><main id="main-content">{children}</main></body>);
}`;

const HEADER = `import { SITE_NAVIGATION, PRIMARY_NAVIGATION } from "@/lib/site-navigation";
export function SiteHeader() {
  const menuGroups = (
    <nav data-site-nav aria-label="All sections">
      {SITE_NAVIGATION.map((group) => (<div key={group.label}>{group.label}</div>))}
    </nav>
  );
  return (
    <header>
      <nav data-site-nav>{PRIMARY_NAVIGATION.map((l) => (<a key={l.href} href={l.href}>{l.label}</a>))}</nav>
      <Dialog.Content id="mobile-nav-panel">
        <Dialog.Title>Menu</Dialog.Title>
        {menuGroups}
      </Dialog.Content>
    </header>
  );
}`;

const NAV = `export const SITE_NAVIGATION = [
  { label: "Explore", links: [
    { href: "/programs/", label: "Programs", detail: "Browse" },
  ] },
  { label: "Data & methods", links: [
    { href: "/glossary/", label: "Glossary", detail: "Translate" },
  ] },
] as const;

export const PRIMARY_NAVIGATION = [
  { href: "/programs/", label: "Programs" },
] as const;`;

const ok = { layoutSrc: LAYOUT, headerSrc: HEADER, navSrc: NAV };

describe("mobileNavGlossaryFindings", () => {
  it("passes when the mounted header builds its panel from a list that carries /glossary/", () => {
    expect(mobileNavGlossaryFindings(ok)).toEqual([]);
  });

  it("PROOF IT CAN FAIL: the old dead-file state (layout mounts a different nav) is an error", () => {
    const layoutSrc = `import { MobileNav } from "@/components/mobile-nav";
export default function RootLayout() { return <MobileNav />; }`;
    const found = mobileNavGlossaryFindings({ ...ok, layoutSrc });
    expect(found).toHaveLength(1);
    expect(found[0]).toMatch(/does not import and render SiteHeader/);
  });

  it("PROOF IT CAN FAIL: an import without a render is not mounted", () => {
    const layoutSrc = `import { SiteHeader } from "@/components/site-header";\nexport default function L() { return null; }`;
    expect(mobileNavGlossaryFindings({ ...ok, layoutSrc })[0]).toMatch(/SiteHeader/);
  });

  it("PROOF IT CAN FAIL: /glossary/ only in PRIMARY_NAVIGATION (hidden below lg) does not count", () => {
    const navSrc = NAV
      .replace('{ href: "/glossary/", label: "Glossary", detail: "Translate" },', "")
      .replace('{ href: "/programs/", label: "Programs" },', '{ href: "/programs/", label: "Programs" },\n  { href: "/glossary/", label: "Glossary" },');
    const found = mobileNavGlossaryFindings({ ...ok, navSrc });
    expect(found).toHaveLength(1);
    expect(found[0]).toMatch(/SITE_NAVIGATION .* has no \/glossary\/ entry/);
  });

  it("PROOF IT CAN FAIL: a panel that does not render the SITE_NAVIGATION groups is an error", () => {
    const headerSrc = HEADER.replace("{menuGroups}", "<p>Search only</p>");
    const found = mobileNavGlossaryFindings({ ...ok, headerSrc });
    expect(found).toHaveLength(1);
    expect(found[0]).toMatch(/not built from SITE_NAVIGATION/);
  });

  it("PROOF IT CAN FAIL: an interpolated const that does not map SITE_NAVIGATION does not count, even if another const does", () => {
    const headerSrc = HEADER
      .replace("{menuGroups}", "{shortcuts}")
      .replace("const menuGroups = (", "const shortcuts = (<p>Shortcuts</p>);\n  const menuGroups = (");
    expect(mobileNavGlossaryFindings({ ...ok, headerSrc })[0]).toMatch(/not built from SITE_NAVIGATION/);
  });

  it("PROOF IT CAN FAIL: no #mobile-nav-panel is an error", () => {
    const headerSrc = HEADER.replace(' id="mobile-nav-panel"', "");
    expect(mobileNavGlossaryFindings({ ...ok, headerSrc })[0]).toMatch(/renders no #mobile-nav-panel/);
  });

  it("PROOF IT CAN FAIL: missing sources (empty strings) fail every step rather than skip", () => {
    expect(mobileNavGlossaryFindings({ layoutSrc: "", headerSrc: "", navSrc: "" })).toHaveLength(3);
  });

  it("the shipped sources pass", () => {
    const srcDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..", "..", "src");
    const read = (...segs) => fs.readFileSync(path.join(srcDir, ...segs), "utf8");
    expect(
      mobileNavGlossaryFindings({
        layoutSrc: read("app", "layout.tsx"),
        headerSrc: read("components", "site-header.tsx"),
        navSrc: read("lib", "site-navigation.ts"),
      })
    ).toEqual([]);
  });
});
