/**
 * Why most company profiles show no budget-linked awards — R-DEC-PRIMES
 * (final-review rulings, 2026-09-27; final review finding #4).
 *
 * THE DEFECT. /methodology/ said the budget→award crosswalk "currently
 * contains R&D performers rather than primes", and every company page with
 * no awards said "The crosswalk mart contains R&D performers, not primes."
 * Once #107(b) withdrew the account / sub-agency tier the published mart was
 * 61% procurement-line links and its largest recipients were the largest
 * primes (Lockheed Martin, Raytheon, Boeing, Northrop Grumman Systems) — the
 * sentence was false, and it was never the reason anyway: a company page
 * lists a crosswalk link only when the award's recipient name EQUALS the
 * family's registered name (export_site.py, `awards_by_display.get(
 * display_name, [])`). Measured read-only on the chain-G lake, 2026-09-27: 32
 * of the top 200 show links; of the other 168, 49 have published links under
 * a member's own name (NORTHROP GRUMMAN SYSTEMS CORPORATION, BATH IRON WORKS
 * CORPORATION, LOCKHEED-style spelling variants) and 119 have none at all.
 *
 * WHAT THIS PINS. The count renders from the build (entity_details), the
 * reason is the rule the exporter applies, and the rule itself is bound to the
 * exporter source — so a family-level join landing there fails this file
 * until the prose is rewritten with it. The retired claims ("R&D performers",
 * "not primes", "Approximately", a roadmap promise no ROADMAP entry backs)
 * cannot come back on any of the three surfaces.
 *
 * PROGRAM PAGES (R-DEC-PRIMES-b, final-review rulings 2026-09-27). The same
 * premise survived as a label: every program page whose Related awards table
 * is truncated said "Showing 25 of N award records (R&D performer crosswalk —
 * see methodology)" — 33 pages on the chain-G build, most of them procurement
 * lines (/program/2122/ is DDG-51) whose crosswalk links name primes. What
 * the table lists is this program's own published crosswalk links
 * (export_site.py _awards_for: its fct_budget_to_awards rows, high and medium
 * only), so the label now says that. The RETIRED patterns are checked on the
 * component for every truncated page in the export, on one built program
 * page, and on the site's source text outside comments.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { cleanup, render } from "@testing-library/react";
import React from "react";
import fs from "fs";
import path from "path";

vi.mock("@/components/citation-panel", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/components/citation-panel")>()),
  CitationPanelProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

import {
  getCompaniesCount,
  getCompaniesWithAwardsCount,
  getEntitiesTop,
  getEntityDetails,
  getProgramDetails,
  getProgramPeBlis,
} from "@/lib/data";
import { formatCount } from "@/lib/format";
import MethodologyPage from "@/app/methodology/page";
import { ProgramAwards } from "@/components/program-awards";

afterEach(() => cleanup());

const norm = (s: string | null | undefined) =>
  (s ?? "").replace(/\s+/g, " ").replace(/[‘’]/g, "'").trim();

/** The rule, word for word, on every surface that explains the gap. */
const RULE =
  "A profile lists a budget→award crosswalk link only when the award's " +
  "recipient name is exactly the family's registered name in the award data.";
const REASONS =
  "A profile shows none when no member's award is linked to a budget line, " +
  "or when the links carry a member's own, different name.";

const RETIRED = [
  /R&D performers?/,
  /not primes/,
  /rather than primes/,
  /[Aa]pproximately \d/,
  /family-level awards mart is on the roadmap/,
];

describe("company page — the empty awards state says why (R-DEC-PRIMES)", () => {
  async function awardsText(slug: string) {
    cleanup();
    const CompanyPage = (await import("@/app/company/[slug]/page")).default;
    const el = await CompanyPage({ params: Promise.resolve({ slug }) });
    const root = render(el as React.ReactElement).container;
    const section = root.querySelector("#awards");
    expect(section, `${slug} renders an #awards section`).not.toBeNull();
    return norm(section!.textContent);
  }

  it("states the build's count and the exact-name rule, and none of the retired claims", async () => {
    const empty = getEntitiesTop().find((e) => getEntityDetails(e.slug).awards.length === 0);
    expect(empty, "the export has at least one profile without awards").toBeDefined();
    const text = await awardsText(empty!.slug);
    const n = formatCount(getCompaniesWithAwardsCount());
    const m = formatCount(getCompaniesCount());
    expect(text).toContain(`${n} of the top ${m} contractor families show linked awards.`);
    expect(text).toContain("No crosswalk-linked award rows carry this family's registered name");
    expect(text).toContain(RULE);
    expect(text).toContain(REASONS);
    for (const re of RETIRED) expect(text).not.toMatch(re);
  }, 60000);
});

describe("/methodology/ — company award linkage (R-DEC-PRIMES)", () => {
  it("names the count, the rule and both reasons, and no retired claim", () => {
    const { container } = render(<MethodologyPage />);
    const section = container.querySelector("#coverage-company-awards");
    expect(section).not.toBeNull();
    const text = norm(section!.textContent);
    const n = formatCount(getCompaniesWithAwardsCount());
    const m = formatCount(getCompaniesCount());
    expect(text).toContain(`Company award linkage — ${n} of ${m} profiled companies`);
    expect(text).toContain(
      `Company profiles cover the top ${m} contractor families by DoD obligations, and ${n} of ${m} show linked awards.`,
    );
    expect(text).toContain(RULE);
    expect(text).toContain(REASONS);
    expect(text).not.toMatch(/still carry obligation totals and lobbying activity/);
    for (const re of RETIRED) expect(text).not.toMatch(re);
    // the page as a whole, not only this section
    const whole = norm(container.textContent);
    expect(whole).not.toMatch(/R&D performers? rather than primes/);
  }, 30000);
});

describe("docs/methodology.md mirrors the rule, and types no count", () => {
  const DOC = path.resolve(__dirname, "..", "..", "..", "docs", "methodology.md");
  const raw = fs.readFileSync(DOC, "utf8").replace(/[*`]/g, "");
  const doc = norm(raw);

  it("states the rule and both reasons word for word", () => {
    expect(doc).toContain(RULE);
    expect(doc).toContain(REASONS);
    for (const re of RETIRED) expect(doc).not.toMatch(re);
  });

  it("the doc's passage types no count of profiles", () => {
    const at = raw.indexOf("Company pages match award links by exact name.");
    expect(at).toBeGreaterThan(-1);
    const end = raw.indexOf("\n\n", at);
    const passage = norm(raw.slice(at, end === -1 ? undefined : end));
    expect(passage).toContain(RULE);
    expect(passage).not.toMatch(/\d/);
  });
});

describe("the rule is the exporter's rule", () => {
  // If entity_details stops joining awards on the exact registered name
  // (a family-level join by UEI, say), the sentence above is no longer the
  // reason and this fails until the prose moves with the code.
  const EXPORTER = path.resolve(
    __dirname, "..", "..", "..", "src", "govbudget", "export_site.py",
  );
  const src = fs.readFileSync(EXPORTER, "utf8");

  it("entity_details takes a family's awards by exact recipient_name == display_name", () => {
    expect(src).toMatch(/entity_awards = awards_by_display\.get\(display_name, \[\]\)/);
    expect(src).toMatch(/awards_by_display\[recipient_name\]\.append\(/);
  });
});

describe("program pages — the truncated awards table says what it lists (R-DEC-PRIMES-b)", () => {
  /** The label beside "Showing N of M award records", word for word. */
  const LABEL = "(this program's published budget→award crosswalk links — see methodology)";
  const CAP = 25;

  /** Every program page in the export whose Related awards table is truncated. */
  const truncated = () =>
    getProgramPeBlis().filter((slug) => getProgramDetails(slug).awards.length > CAP);

  function checkLabel(text: string, shown: number, total: number) {
    expect(text).toContain(
      `Showing ${formatCount(shown)} of ${formatCount(total)} award records ${LABEL}`,
    );
    for (const re of RETIRED) expect(text).not.toMatch(re);
    expect(text).not.toMatch(/performer/i);
  }

  it("renders the label, and no retired claim, for every truncated table in the export", () => {
    const slugs = truncated();
    expect(slugs.length, "the export has at least one truncated awards table").toBeGreaterThan(0);
    for (const slug of slugs) {
      cleanup();
      const awards = getProgramDetails(slug).awards;
      const { container } = render(
        <ProgramAwards initialAwards={awards.slice(0, CAP)} totalCount={awards.length} peBli={slug} />,
      );
      checkLabel(norm(container.textContent), CAP, awards.length);
      const link = container.querySelector('a[href^="/methodology/"]');
      expect(link, `${slug}: the label links to /methodology/`).not.toBeNull();
      expect(norm(link!.textContent)).toBe("methodology");
    }
  }, 60000);

  it("a built program page with a truncated table carries the same label in its awards section", async () => {
    const slug = truncated()[0];
    cleanup();
    const Page = (await import("@/app/program/[peBli]/page")).default;
    const el = await Page({ params: Promise.resolve({ peBli: slug }) });
    const root = render(el as React.ReactElement).container;
    const section = root.querySelector('section[data-section="awards"]');
    expect(section, `${slug} renders an awards section`).not.toBeNull();
    checkLabel(norm(section!.textContent), CAP, getProgramDetails(slug).awards.length);
  }, 60000);

  it("no page, component or library source states the retired premise outside a comment", () => {
    // Comments may quote the retired sentence to explain why it went (this
    // file's header, /methodology/'s and the company page's R-DEC-PRIMES
    // notes); rendered text may not. Block and line comments are stripped
    // before the sweep; the JSX-escaped spelling (R&amp;D) is covered.
    const SRC = path.resolve(__dirname, "..");
    const files: string[] = [];
    const walk = (dir: string) => {
      for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
        const p = path.join(dir, e.name);
        if (e.isDirectory()) {
          if (e.name !== "__tests__") walk(p);
        } else if (/\.tsx?$/.test(e.name)) files.push(p);
      }
    };
    for (const d of ["app", "components", "lib"]) walk(path.join(SRC, d));
    expect(files.length).toBeGreaterThan(0);
    const hits: string[] = [];
    for (const f of files) {
      const code = fs
        .readFileSync(f, "utf8")
        .replace(/\/\*[\s\S]*?\*\//g, "")
        .replace(/(^|[^:"'`])\/\/.*$/gm, "$1");
      if (/R&(?:amp;)?D performers?|performer crosswalk|rather than primes|not primes/i.test(code)) {
        hits.push(path.relative(SRC, f));
      }
    }
    expect(hits).toEqual([]);
  });
});
