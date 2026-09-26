/**
 * ROADMAP #175 — the gate-27 (copy) allowlist burn-down, 2026-09-26.
 *
 * copy-allowlist.json exempted production's pre-existing gate-27 hits
 * (R-INT-7). The strings below were rewritten at their source per
 * docs/superpowers/VOICE.md and their entries deleted in the same change;
 * the gate fails on an entry that matches nothing, so a string that comes
 * back cannot hide behind a stale entry, and one that is rewritten again
 * cannot leave one behind. These tests hold the rewritten strings where the
 * gate can only see them after a build: the rendered page (real data, the
 * pattern of pagefind-text-separators.test.tsx), or the source text where
 * the element is the root layout (the pattern of build-stamp-wording.test.ts).
 *
 * The meta-title case is the one piece of logic: VOICE rule 28 / gate 27
 * leg 38 — a program page's <title> is "{title} ({PE|BLI} {code}) ·
 * {orgShort}", at most 60 characters before " | Fiscal Receipts", built by
 * copy.ts metaTitle() rather than typed.
 */
import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import React from "react";
import fs from "fs";
import path from "path";

vi.mock("@/components/citation-panel", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/components/citation-panel")>()),
  CitationPanelProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

const SRC = path.resolve(__dirname, "..");
const read = (rel: string) => fs.readFileSync(path.join(SRC, rel), "utf8").replace(/\s+/g, " ");
const norm = (s: string | null | undefined) => (s ?? "").replace(/\s+/g, " ").trim();
const headings = (root: HTMLElement) => [...root.querySelectorAll("h2, h3")].map((h) => norm(h.textContent));

/** Gate 27 leg 29's Title Case pattern, applied the way the gate applies it (h2/h3 text). */
const TITLE_CASE = /^(?:[A-Z][a-z]+ ){1,4}[A-Z][a-z]+$/;
/** Gate 27 leg 38's shape, on the title before the " | Fiscal Receipts" template. */
const META_TITLE_SHAPE = /^.+ \((PE|BLI) [A-Z0-9-]+\) · .+$/;

describe("header and footer: the two sitewide entries (VOICE conflicts resolved 1 and 2)", () => {
  it("the /explore/ nav item is 'Field guide' and the first nav group is 'Budget'", async () => {
    const { PRIMARY_NAVIGATION, SITE_NAVIGATION } = await import("@/lib/site-navigation");
    expect(PRIMARY_NAVIGATION.find((l) => l.href === "/explore/")?.label).toBe("Field guide");
    expect(SITE_NAVIGATION[0].label).toBe("Budget");
    expect(SITE_NAVIGATION[0].links.find((l) => l.href === "/explore/")?.label).toBe("Field guide");
    const labels = [
      ...PRIMARY_NAVIGATION.map((l) => l.label),
      ...SITE_NAVIGATION.flatMap((g) => [g.label, ...g.links.map((l) => l.label)]),
    ];
    expect(labels.filter((l) => /^Explore\b|visual field guide/i.test(l))).toEqual([]);
  });

  it("the footer (root layout, source-level) names the group 'Budget' and the link 'Field guide'", () => {
    const layout = read("app/layout.tsx");
    expect(layout).toContain('<strong className="t-label">Budget</strong><Link href="/explore/">Field guide</Link>');
    expect(layout).not.toMatch(/>Explore<|Visual field guide/);
  });

  it("the /explore/ eyebrow and the exhibit topline say 'Field guide'", () => {
    expect(read("app/explore/page.tsx")).toContain('<PageIntro eyebrow="Field guide"');
    expect(read("components/program-exhibit.tsx")).toContain("{config.eyebrow} / Field guide");
    for (const f of ["app/explore/page.tsx", "components/program-exhibit.tsx"]) {
      expect(read(f)).not.toMatch(/Visual field guide/);
    }
  });
});

describe("program page: sentence-case section headings and the evidence-path sentence", () => {
  async function renderProgram(slug: string) {
    const Page = (await import("@/app/program/[peBli]/page")).default;
    const el = await Page({ params: Promise.resolve({ peBli: slug }) });
    return render(el as React.ReactElement).container;
  }

  it("no h2/h3 on a sampled program page is Title Case, and the renamed ones read in sentence case", async () => {
    const root = await renderProgram("0101221N");
    const hs = headings(root);
    expect(hs).toEqual(expect.arrayContaining(["Budget figures", "Primary sources", "Program lineage"]));
    expect(hs.some((h) => h === "Lobbying mentions")).toBe(true);
    for (const old of ["Budget Figures", "Program Lineage", "Lobbying Mentions", "Primary Sources", "Related Awards", "Line Items"]) {
      expect(hs).not.toContain(old);
    }
    // Contractor Concentration is program-concentration.tsx's (another task's file); every other h2/h3 passes leg 29.
    expect(hs.filter((h) => TITLE_CASE.test(h) && h !== "Contractor Concentration")).toEqual([]);
  }, 60000);

  it("the evidence path names what a cited figure opens to, without a pointer verb or a serial comma", async () => {
    const root = await renderProgram("0101221N");
    const text = norm(root.textContent);
    expect(text).toContain("A cited figure opens to its source, fiscal context and a shareable footnote.");
    expect(text).not.toContain("Click a cited figure");
  }, 60000);

  it("the trajectory sparkline description states the direction without 'at a glance'", async () => {
    const root = await renderProgram("0101221N");
    const desc = norm(root.querySelector("#trajectory-spark [data-chart-desc], [data-chart='trajectory-spark'] [data-chart-desc]")?.textContent);
    expect(desc).toMatch(/^The program's \d+ summary figures for FY\d\d to FY\d\d, plotted in fiscal-year order: this line ends (higher than it starts|lower than it starts|level with where it starts)\. The points are the summary cards above/);
    expect(desc).not.toMatch(/at a glance|direction of travel/);
    expect(desc.length).toBeGreaterThanOrEqual(60); // render-static (ch) / charts P2-3 floor
  }, 60000);
});

describe("program meta title (VOICE rule 28, gate 27 leg 38)", () => {
  const programs: { slug: string; pe_bli: string; title: string; org: string; exhibit_family: string | null }[] = JSON.parse(
    fs.readFileSync(path.resolve(SRC, "..", "..", "data", "site", "json", "programs.json"), "utf8"),
  );
  // The gate samples the first 25 program directories in sorted order; add the pilots and the longest titles.
  const bySlug = [...programs].sort((a, b) => (a.slug < b.slug ? -1 : a.slug > b.slug ? 1 : 0));
  const longest = [...programs].sort((a, b) => b.title.length - a.title.length).slice(0, 5);
  const sample = [...bySlug.slice(0, 25), ...programs.filter((p) => ["2013", "0604840F"].includes(p.slug)), ...longest];

  it.each(sample.map((p) => [p.slug, p] as const))("%s: title is copy.ts metaTitle(), leg-38 shaped, ≤ 60 chars", async (slug, p) => {
    const { generateMetadata } = await import("@/app/program/[peBli]/page");
    const { metaTitle } = await import("@/lib/copy");
    const meta = await generateMetadata({ params: Promise.resolve({ peBli: slug }) });
    const title = String(meta.title);
    expect(title).toBe(metaTitle(p));
    expect(title).toMatch(META_TITLE_SHAPE);
    expect(title.length).toBeLessThanOrEqual(60);
    expect(title).not.toContain("Fiscal Receipts"); // the layout template appends it (render-static title doubling)
    expect(String(meta.openGraph?.title)).toBe(title);
  }, 60000);

  // Pages outside programs.json (rollup and decade tiers) synthesize their row
  // (program-tier.ts); these three sat in the gate's sample on 2026-09-25. A
  // decade-tier sidecar carries the older editions' service code ("AF",
  // "ARMY", "NAVY" — 293 pages); the title's org lockup names the service the
  // way it does for "F", "A" and "N".
  it.each([
    ["000079", "Cancelled Acct Adjustments (BLI 000079) · Air Force"],
    ["0101125F", "Nuclear Weapons Modernization (PE 0101125F) · Air Force"],
  ])("%s (rollup/decade tier): %s", async (slug, expected) => {
    const { generateMetadata } = await import("@/app/program/[peBli]/page");
    const meta = await generateMetadata({ params: Promise.resolve({ peBli: slug }) });
    expect(String(meta.title)).toBe(expected);
  }, 60000);

  it("0101313F (a long decade-tier title) is cut at a word, never the lockup", async () => {
    const { generateMetadata } = await import("@/app/program/[peBli]/page");
    const title = String((await generateMetadata({ params: Promise.resolve({ peBli: "0101313F" }) })).title);
    expect(title).toMatch(META_TITLE_SHAPE);
    expect(title.length).toBeLessThanOrEqual(60);
    expect(title).toBe("Integrated Strategic Planning… (PE 0101313F) · Air Force");
  }, 60000);

  it("orgLabel short names the service for the decade tier's codes too", async () => {
    const { orgLabel } = await import("@/lib/copy");
    expect(["AF", "ARMY", "NAVY", "F", "A", "N", "OSD"].map((o) => orgLabel(o, "short"))).toEqual(["Air Force", "Army", "Navy", "Air Force", "Army", "Navy", "OSD"]);
  });

  it("a shared-code stub keeps its own title (it is not a program page)", async () => {
    const { generateMetadata } = await import("@/app/program/[peBli]/page");
    expect(String((await generateMetadata({ params: Promise.resolve({ peBli: "2292" }) })).title)).toMatch(/^Budget line 2292 /);
  }, 60000);
});

describe("company page: the dossier strings", () => {
  async function renderCompany(slug: string) {
    const { default: CompanyPage } = await import("@/app/company/[slug]/page");
    const el = await CompanyPage({ params: Promise.resolve({ slug }) });
    return render(el as React.ReactElement).container;
  }

  it("lockheed-martin: deck, obligations note, lobbying headings and notes", async () => {
    const root = await renderCompany("lockheed-martin");
    const text = norm(root.textContent);
    expect(text).toContain("Contract evidence, program connections and public lobbying disclosures for this company.");
    expect(text).toContain("The total obligations figure opens to its derived USAspending citation. Confidence reflects entity resolution method");
    expect(text).toContain("Lobbying dollar aggregates carry derived LDA citations. Each figure opens to its formula and constituent filings.");
    expect(text).toContain("disclosures on an LDA filing: a registrant reports one or the other. The two are not summed here.");
    expect(headings(root)).toEqual(expect.arrayContaining(["Lobbying activity", "Budget program mentions"]));
    for (const old of ["Follow this company", "click the figure", "click a figure", "Lobbying Activity", "Budget Program Mentions", "— a registrant reports"]) {
      expect(text).not.toContain(old);
    }
  }, 60000);
});

describe("district, agency and filing pages", () => {
  it("district: deck without a serial comma, a destination link, and the totals note", async () => {
    const { default: Page } = await import("@/app/district/[district]/page");
    const root = render((await Page({ params: Promise.resolve({ district: "AL-02" }) })) as React.ReactElement).container;
    const text = norm(root.textContent);
    expect(text).toContain("The documented connections between this place, defense programs and contract awards.");
    expect(root.querySelector('a[href="#linked-programs"]')?.textContent).toBe("Linked programs");
    expect(text).toContain("Aggregate totals are derived from USAspending award transaction data. Each figure opens to its formula and query.");
    expect(text).not.toMatch(/Explore linked programs|click any figure/);
  }, 60000);

  it("agency: sentence-case portfolio heading and the two figure notes", async () => {
    const { default: Page } = await import("@/app/agency/[org]/page");
    const root = render((await Page({ params: Promise.resolve({ org: "CYBERCOM" }) })) as React.ReactElement).container;
    const text = norm(root.textContent);
    expect(headings(root)).toContain("Program elements");
    expect(text).toContain("Aggregate totals are derived sums over this agency's program figures. Each total opens to its formula and cited inputs.");
    expect(text).toMatch(/reported programs \(paymentaccuracy\.gov\)\. The figure opens to its derivation and source\./);
    expect(text).not.toMatch(/click a total|Click the figure/);
  }, 60000);

  it("filing: the source note says what an underlined figure opens to", async () => {
    const { default: Page } = await import("@/app/filing/[uuid]/page");
    const root = render((await Page({ params: Promise.resolve({ uuid: "55078848-5151-45f3-9172-a82fd75f9323" }) })) as React.ReactElement).container;
    const text = norm(root.textContent);
    expect(text).toContain("Underlined dollar figures cite the filing record on lda.senate.gov and open to that citation.");
    expect(text).not.toContain("click to view");
  }, 60000);
});
