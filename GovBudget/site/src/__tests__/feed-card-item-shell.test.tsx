/**
 * feed-card-item-shell.test.tsx — ROADMAP #81.
 *
 * Until #81 the /feed/ card existed twice: <FeedCardItem> (server tree) and a
 * hand-copied <FeedCardItemClient> (the section-expand client tree), held
 * together only by feed-card-item-parity.test.tsx's byte-identical diff. Now
 * both render ONE <FeedCardItemShell>; the only thing the client tree still
 * reimplements is the headline segment computation (the server's
 * feedHeadlineSegments() can fall back to getPrograms() on disk).
 *
 * Two kinds of assertion:
 *   1. RUNTIME — the shell module is mocked with a pass-through spy, both
 *      trees are rendered, and what each passed AND produced is compared:
 *      the same card/companySlug/hasProgramPage, a headline whose server side
 *      is <FeedHeadline> and whose client side is not, and — for a
 *      reconciliation card — the same <Fy26SplitNote> markers out of both.
 *   2. SOURCE — the card's marker attributes are authored in exactly one
 *      component source file under src/, both trees import the shell module,
 *      fy26-split-note.tsx is imported only by the shell and by
 *      program-figures.tsx, and the client file DEFINES no *Client twin of
 *      the two extracted pieces.
 *
 * The parity test stays as the end-to-end pin of the rendered HTML; this file
 * pins the STRUCTURE that makes parity hold by construction.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render } from "@testing-library/react";
import { readdirSync, readFileSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import type { ReactElement } from "react";

vi.mock("@/components/feed-card-item-shell", async (importOriginal) => {
  const mod =
    await importOriginal<typeof import("@/components/feed-card-item-shell")>();
  return { ...mod, FeedCardItemShell: vi.fn(mod.FeedCardItemShell) };
});

import { FeedCardItem } from "@/components/feed-card-item";
import { FeedCardItemClient } from "@/components/feed-card-item-client";
import { FeedCardItemShell } from "@/components/feed-card-item-shell";
import { FeedHeadline } from "@/components/feed-headline";
import type { FeedCard, Fy26Split } from "@/lib/data";

const shell = vi.mocked(FeedCardItemShell);

/** Title-led (no getPrograms() disk read on the server side), no split. */
const PLAIN: FeedCard = {
  event_type: "concentration_shift",
  family_key: null,
  figure_fact_id: "a".repeat(16),
  figure_units: "hhi",
  figure_value: 8662.294,
  fiscal_year: 2020,
  headline: "Defense Research Sciences award concentration HHI=8662 (2020)",
  headline_segments: [
    { text: "Defense Research Sciences award concentration HHI=8662 (2020)" },
  ],
  organization: null,
  pe_bli: "0601101E",
  program_url: "/program/0601101E/",
  title: "Defense Research Sciences",
  why_url: "/methodology/#feed-concentration_shift",
  basis: null,
  fy: null,
  measure: null,
  edition: null,
  magnitude: {
    kind: "single",
    units: "dollars",
    from: null,
    to: { label: "FY2020 matched obligations", fy: 2020, value: 25_351_139_885.2, fact_id: "b".repeat(16) },
    delta: null,
    pct_change: null,
  },
};

const SPLIT: Fy26Split = {
  disc_k: 10_000,
  recon_k: 29_426,
  total_k: 39_426,
  recon_share: 0.746,
  disc_pct_change: -20.5,
  has_reconciliation: true,
  disc: {
    v: 10_000,
    units: "USD thousands",
    dataset: "budget_lines",
    fid: "1".repeat(16),
    public_id: "11111111",
    basis: "toa",
    fy: 2026,
    measure: "disc-request",
    edition: 2026,
  },
  reconciliation: {
    v: 29_426,
    units: "USD thousands",
    dataset: "budget_lines",
    fid: "2".repeat(16),
    public_id: "22222222",
    basis: "toa",
    fy: 2026,
    measure: "reconciliation-request",
    edition: 2026,
  },
};

/** yoy_swing with reconciliation money — the split note renders. */
const RECON: FeedCard = {
  event_type: "yoy_swing",
  family_key: null,
  figure_fact_id: "c".repeat(16),
  figure_units: "pct_change",
  figure_value: -61.29,
  fiscal_year: 2026,
  headline: "MEDIUM UNMANNED SURFACE VEHICLES decreased 61% FY25→26 (to $39.4M)",
  headline_segments: [
    { text: "MEDIUM UNMANNED SURFACE VEHICLES decreased 61% FY25→26 (to " },
    { amount: "$39.4M", fact_id: "d".repeat(16) },
    { text: ")" },
  ],
  organization: "N",
  pe_bli: "0605512N",
  program_url: "/program/0605512N/",
  title: "MEDIUM UNMANNED SURFACE VEHICLES",
  why_url: "/methodology/#feed-yoy_swing",
  basis: "toa",
  fy: 2026,
  measure: "change",
  edition: 2026,
  magnitude: {
    kind: "pair",
    units: "thousands_usd",
    from: { label: "FY2025", fy: 2025, value: 101_838, fact_id: "e".repeat(16) },
    to: { label: "FY2026", fy: 2026, value: 39_426, fact_id: "f".repeat(16) },
    delta: { label: "change", fy: 2026, value: -62_412, fact_id: "c".repeat(16) },
    pct_change: -61.29,
  },
  fy26_split: SPLIT,
};

function renderBoth(card: FeedCard) {
  shell.mockClear();
  const server = render(
    <FeedCardItem card={card} companySlug={null} hasProgramPage={true} />,
  );
  const client = render(
    <FeedCardItemClient card={card} companySlug={null} hasProgramPage={true} />,
  );
  expect(shell).toHaveBeenCalledTimes(2);
  return {
    serverProps: shell.mock.calls[0][0],
    clientProps: shell.mock.calls[1][0],
    serverEl: server.container,
    clientEl: client.container,
  };
}

// ── 1. runtime: both trees render the one shell ─────────────────────────────

describe("<FeedCardItemShell> is what both /feed/ card trees render", () => {
  // Braces, not a concise body: mockClear() RETURNS the mock, and vitest
  // treats a function returned from beforeEach as a teardown callback — it
  // would call the spy with no arguments after every test, and the real
  // implementation would throw destructuring `card` off undefined.
  beforeEach(() => {
    shell.mockClear();
  });

  it("the server card and the client twin both call the shell with the same card, companySlug and hasProgramPage", () => {
    const { serverProps, clientProps } = renderBoth(PLAIN);
    expect(serverProps.card).toBe(PLAIN);
    expect(clientProps.card).toBe(PLAIN);
    expect(serverProps.companySlug).toBeNull();
    expect(clientProps.companySlug).toBeNull();
    expect(serverProps.hasProgramPage).toBe(true);
    expect(clientProps.hasProgramPage).toBe(true);
  });

  it("the headline is the one legitimate divergence: the server passes <FeedHeadline>, the client its fs-free twin — both fed the same card", () => {
    const { serverProps, clientProps } = renderBoth(PLAIN);
    const s = serverProps.headline as ReactElement<{ card: FeedCard }>;
    const c = clientProps.headline as ReactElement<{ card: FeedCard }>;
    expect(s.type).toBe(FeedHeadline);
    expect(c.type).not.toBe(FeedHeadline);
    expect(s.props.card).toBe(PLAIN);
    expect(c.props.card).toBe(PLAIN);
  });

  it("a reconciliation card renders the ONE <Fy26SplitNote>'s markers, identically, out of both trees", () => {
    const { serverEl, clientEl } = renderBoth(RECON);
    for (const el of [serverEl, clientEl]) {
      expect(el.querySelector("[data-fy26-recon-chip]")!.textContent).toBe(
        "74.6% reconciliation",
      );
      expect(
        el.querySelector("[data-fy26-disc-pct-change]")!.textContent,
      ).toContain("Discretionary change vs FY2025 enacted: -20.5%.");
    }
  });

  it("a card with no reconciliation money renders neither marker, from either tree", () => {
    const { serverEl, clientEl } = renderBoth(PLAIN);
    for (const el of [serverEl, clientEl]) {
      expect(el.querySelector("[data-fy26-recon-chip]")).toBeNull();
      expect(el.querySelector("[data-fy26-disc-pct-change]")).toBeNull();
    }
  });
});

// ── 2. source: the markup exists once ───────────────────────────────────────

const SRC = resolve(__dirname, "..");

/** Every non-test .tsx under src/ (test files quote the markers in assertions). */
function tsxFiles(dir: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === "__tests__" || entry.name === "node_modules") continue;
    const full = join(dir, entry.name);
    if (entry.isDirectory()) out.push(...tsxFiles(full));
    else if (entry.name.endsWith(".tsx") && !entry.name.endsWith(".test.tsx"))
      out.push(full);
  }
  return out;
}

function owners(needle: string): string[] {
  return tsxFiles(SRC)
    .filter((f) => readFileSync(f, "utf8").includes(needle))
    .map((f) => relative(SRC, f))
    .sort();
}

describe("the /feed/ card markup has exactly one source file", () => {
  it("the card's own markers are authored only in components/feed-card-item-shell.tsx", () => {
    // The `=""` suffix matches the JSX attribute, not prose mentions in comments.
    for (const marker of [
      'data-feed-card=""',
      'data-hhi-scope-note=""',
      'data-primary-value="feed-figure"',
    ]) {
      expect(owners(marker), marker).toEqual(["components/feed-card-item-shell.tsx"]);
    }
    for (const marker of ['data-fy26-recon-chip=""', 'data-fy26-disc-pct-change=""']) {
      expect(owners(marker), marker).toEqual(["components/fy26-split-note.tsx"]);
    }
  });

  it("both trees import the shell, only the shell and program-figures import the split note, and no hand-copied twins remain", () => {
    expect(owners('from "@/components/feed-card-item-shell"')).toEqual([
      "components/feed-card-item-client.tsx",
      "components/feed-card-item.tsx",
    ]);
    expect(owners('from "@/components/fy26-split-note"')).toEqual([
      "components/feed-card-item-shell.tsx",
      "components/program-figures.tsx",
    ]);
    // A DEFINITION, not a mention — the file's doc comment is allowed to name
    // the twins it retired.
    const client = readFileSync(join(SRC, "components/feed-card-item-client.tsx"), "utf8");
    expect(client).not.toMatch(
      /\b(?:function|const|let|var)\s+(?:hhiScopeNoteClient|Fy26SplitNoteClient)\b/,
    );
  });
});
