/**
 * /company/{slug}/ resolves its citations through the cite shards
 * (decisions wave fix round 5, 2026-09-26 — R-DEC-LDACITE's page weight).
 *
 * THE DEFECT THIS PINS. The company page built its citation slice with
 * collectCitationsWithInputs() and handed it to <CitationPanelProvider>, a
 * client component, so every body in it was serialized into the page's RSC
 * payload: the entity total, the family-obligations figure and every
 * lobbying income / expense / total citation. R-DEC-LDACITE made each
 * lobbying citation list the filings it counts (no cap; 285 on the heaviest
 * family-year). Embedded, those lists put 12 company pages over gate 1's
 * 25,000-gzip ceiling for the /company/*\/ class (aerospace 41,964, boeing
 * 29,663 — decisions-fix4-export.md), a ceiling that is never raised to fit
 * new content.
 *
 * THE CONTRACT, the one /district/{code}/ keeps since Task 28b
 * (district-cite-shards.test.tsx): the provider mounts with an EMPTY embedded
 * slice; every cited figure still renders as a state-A <Cite> whose fact id is
 * in the static HTML; a click resolves the body from
 * /json/cite-shards/{fact_id[:2]}.json through the panel's fetch-on-miss path;
 * and the provider is handed `shardResolvableIds` — ids, never bodies — so a
 * derived card's input chips stay clickable. The list is the key set of the
 * slice the page used to embed, restricted to the figures it renders: what
 * hasCitation() answered true for before still answers true (a fact-id input
 * of a rendered derived figure included), and nothing it answered false for
 * now answers true.
 *
 * Real payloads throughout: the page reads the shipped entity sidecars and
 * citations.json, and the fetch seam serves the shipped cite-shard files. The
 * post-chain-G cases rewrite the lobbying citations IN the loaded citations
 * map (the object the page's own collectCitations reads) and overlay the same
 * rows on the shards, so the page and the shards stay one export.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { cleanup, render, fireEvent, waitFor } from "@testing-library/react";
import React from "react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import type { Citation, CitationsMap, EntitySamRegistration } from "@/lib/data";
import { getCitations, getEntityDetails, getEntityTopMap } from "@/lib/data";
import { __resetCiteShardCache } from "@/lib/cite-shards";

const SHARD_DIR = resolve(__dirname, "../../../data/site/json/cite-shards");
const FACT_ID = /^[0-9a-f]{16}$/;

/**
 * The 12 pages that measured over the ceiling with the lists embedded
 * (decisions-fix4-export.md, zlib 9 on the integration build).
 */
const HEAVIEST = [
  "aerospace",
  "lockheed-martin",
  "general-atomics",
  "boeing",
  "general-dynamics",
  "microsoft",
  "general-electric",
  "honeywell-international",
  "science-applications-international",
  "pfizer",
  "fedex",
  "eli-lilly-and",
] as const;

// ── Seams ────────────────────────────────────────────────────────────────────

const seen = vi.hoisted(() => ({
  providerCitations: [] as unknown[],
  providerResolvable: [] as unknown[],
  /** Rows the shard seam serves in place of the shipped ones. */
  overlay: {} as Record<string, unknown>,
}));

vi.mock("@/components/citation-panel", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/components/citation-panel")>();
  function RecordingProvider(
    props: React.ComponentProps<typeof real.CitationPanelProvider>,
  ) {
    seen.providerCitations.push(props.citations);
    seen.providerResolvable.push(props.shardResolvableIds);
    return <real.CitationPanelProvider {...props} />;
  }
  return { ...real, CitationPanelProvider: RecordingProvider };
});

const shardCache = new Map<string, CitationsMap>();
function shippedShard(prefix: string): CitationsMap {
  let s = shardCache.get(prefix);
  if (!s) {
    s = JSON.parse(readFileSync(resolve(SHARD_DIR, `${prefix}.json`), "utf8")) as CitationsMap;
    shardCache.set(prefix, s);
  }
  return s;
}

let fetchMock: ReturnType<typeof vi.fn>;
/** Citations rewritten in the loaded map, restored after each test. */
const restore: [string, Citation][] = [];

beforeEach(() => {
  seen.providerCitations.length = 0;
  seen.providerResolvable.length = 0;
  seen.overlay = {};
  __resetCiteShardCache();
  // A shard request returns that shard's shipped rows (plus any rewritten
  // row of this test); anything else (asset-config's /config.json, the
  // breakdown sidecars) rejects and the component falls back.
  fetchMock = vi.fn((url: string) => {
    const m = /^\/json\/cite-shards\/([0-9a-f]{2})\.json$/.exec(String(url));
    if (!m) return Promise.reject(new Error(`unmocked fetch ${url}`));
    const rows: CitationsMap = { ...shippedShard(m[1]) };
    for (const [id, c] of Object.entries(seen.overlay)) {
      if (id.startsWith(m[1])) rows[id] = c as Citation;
    }
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(rows),
    } as unknown as Response);
  });
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  const all = getCitations();
  while (restore.length) {
    const [id, c] = restore.pop()!;
    all[id] = c;
  }
  vi.unstubAllGlobals();
  cleanup();
});

/** Rewrite one citation in the export the page reads AND the shards serve. */
function rewrite(id: string, next: Citation) {
  const all = getCitations();
  restore.push([id, all[id]]);
  all[id] = next;
  seen.overlay[id] = next;
}

async function renderCompany(slug: string): Promise<HTMLElement> {
  // One page in the document at a time: the panel queries go through it.
  cleanup();
  seen.providerCitations.length = 0;
  seen.providerResolvable.length = 0;
  const Page = (await import("@/app/company/[slug]/page")).default;
  const el = await Page({ params: Promise.resolve({ slug }) });
  return render(el as React.ReactElement).container;
}

/** Every rendered [data-fact-id], deduplicated and sorted. */
function renderedIds(container: HTMLElement): string[] {
  return [
    ...new Set(
      Array.from(container.querySelectorAll("[data-fact-id]")).map(
        (el) => el.getAttribute("data-fact-id")!,
      ),
    ),
  ].sort();
}

/** The one list the page handed its provider (asserted, not assumed). */
function listed(): string[] {
  expect(seen.providerResolvable.length).toBeGreaterThan(0);
  const lists = seen.providerResolvable.map((l) => {
    expect(Array.isArray(l), "shardResolvableIds is an array").toBe(true);
    return [...(l as string[])].sort();
  });
  for (const l of lists) expect(l).toEqual(lists[0]);
  return lists[0];
}

function panelQueryAll(testId: string): Element[] {
  return Array.from(
    document.querySelectorAll(`[data-testid="citation-panel"] [data-testid="${testId}"]`),
  );
}

const shardOf = (id: string) => `/json/cite-shards/${id.slice(0, 2)}.json`;

function shardCalls(): string[] {
  return fetchMock.mock.calls
    .map((c) => String(c[0]))
    .filter((u) => u.includes("cite-shards"));
}

/** The lobbying figures the table renders, from the page's own payload. */
function lobbyingFigures(slug: string): { id: string; filings: number }[] {
  const details = getEntityDetails(slug);
  const showTotal = details.influence.some((r) => r.nonAdditive !== true);
  return details.influence.flatMap((r) =>
    [
      r.lobbying_income_usd != null ? r.income_fact_id : null,
      r.lobbying_expense_usd != null ? r.expense_fact_id : null,
      showTotal && r.lobbying_total_usd != null ? r.total_fact_id : null,
    ]
      .filter((id): id is string => typeof id === "string" && id !== "")
      .map((id) => ({ id, filings: Number(r.filings_count) })),
  );
}

// ── The page embeds no citation bodies ───────────────────────────────────────

describe("/company/{slug}/ citations come from the cite shards", () => {
  it.each(HEAVIEST)(
    "%s mounts the provider with an empty slice and lists exactly the figures it renders",
    async (slug) => {
      const container = await renderCompany(slug);
      expect(seen.providerCitations.length).toBeGreaterThan(0);
      for (const citations of seen.providerCitations) expect(citations).toEqual({});

      const rendered = renderedIds(container);
      // Non-vacuity: the entity total and at least one lobbying figure.
      expect(rendered).toContain(getEntityTopMap().get(slug)!.total_obligation_fact_id);
      expect(lobbyingFigures(slug).length).toBeGreaterThan(0);
      for (const { id } of lobbyingFigures(slug)) expect(rendered).toContain(id);

      const ids = listed();
      for (const id of ids) expect(id).toMatch(FACT_ID);
      expect(new Set(ids).size).toBe(ids.length);
      // On the shipped export no rendered derived figure has a fact-id input
      // (the lobbying lists are URLs), so the list is the rendered set.
      expect(ids).toEqual(rendered);
    },
    120_000,
  );

  it("every figure on the page opens its own citation, fetched from its shard", async () => {
    const container = await renderCompany("boeing");
    const ids = renderedIds(container);
    expect(ids.length).toBeGreaterThanOrEqual(3);
    // Chain G's export (2026-09-26) carries boeing's SAM registration: its
    // status renders as a prose cite, not an amount — a cited figure all
    // the same, opened the same way. Bound to the export: the prose cite is
    // on the page exactly when the family carries a rendered status.
    const sam = getEntityDetails("boeing").sam;
    const samId = sam?.registration_status ? sam.fact_id : null;
    if (samId) expect(ids).toContain(samId);
    for (const id of ids) {
      const figure =
        id === samId
          ? container.querySelector(`[data-prose-cite][data-fact-id="${id}"]`)
          : container.querySelector(`[data-amount][data-fact-id="${id}"]`);
      expect(figure, `${id} is a state-A figure`).not.toBeNull();
      fireEvent.click(figure!);
      await waitFor(() => {
        const permalink = panelQueryAll("panel-fact-permalink")[0];
        expect(permalink?.textContent).toBe(`fact #${id.slice(0, 8)}`);
        expect(panelQueryAll("derived-card")).toHaveLength(1);
        expect(panelQueryAll("citation-loading")).toHaveLength(0);
      });
      expect(shardCalls()).toContain(shardOf(id));
    }
  }, 120_000);
});

// ── After chain G: the lists ship, and the page stays their weight-free ──────

describe("/company/{slug}/ after R-DEC-LDACITE: every filing list opens, none is embedded", () => {
  it("aerospace: the note claims constituent filings, the embed stays empty, each card lists every filing", async () => {
    const slug = "aerospace";
    const all = getCitations();
    const before = renderedIds(await renderCompany(slug));
    const listBefore = listed();

    // One URL per counted filing — the Filings column's own count, as the
    // exporter's recount guarantees (decisions-fix4-export.md).
    const figures = lobbyingFigures(slug);
    for (const { id, filings } of figures) {
      const urls = Array.from(
        { length: filings },
        (_, k) => `https://lda.senate.gov/api/v1/filings/${id}-${String(k).padStart(4, "0")}/`,
      );
      rewrite(id, { ...all[id], inputs: JSON.stringify(urls) } as Citation);
    }
    expect(Math.max(...figures.map((f) => f.filings))).toBeGreaterThanOrEqual(100);

    const container = await renderCompany(slug);
    for (const citations of seen.providerCitations) expect(citations).toEqual({});
    expect(renderedIds(container)).toEqual(before);
    expect(listed()).toEqual(listBefore);
    expect(container.querySelector("#lobbying")!.textContent!.replace(/\s+/g, " ")).toContain(
      "Each figure opens to its formula and constituent filings.",
    );

    for (const { id, filings } of figures) {
      fireEvent.click(container.querySelector(`[data-amount][data-fact-id="${id}"]`)!);
      await waitFor(() => {
        expect(panelQueryAll("panel-fact-permalink")[0]?.textContent).toBe(`fact #${id.slice(0, 8)}`);
        const card = panelQueryAll("derived-card");
        expect(card).toHaveLength(1);
        const links = card[0].querySelectorAll('a[href^="https://lda.senate.gov/api/v1/filings/"]');
        expect(links).toHaveLength(filings);
      });
    }
  }, 180_000);

  it("a fact-id input of a rendered derived figure stays a clickable chip and opens from its shard", async () => {
    const slug = "boeing";
    const all = getCitations();
    const figures = lobbyingFigures(slug);
    const host = figures[0].id;
    // A real citation that is not on this page — the chip's target.
    const onPage = new Set(renderedIds(await renderCompany(slug)));
    const target = Object.keys(all).find(
      (id) => all[id].kind === "usaspending" && !onPage.has(id),
    )!;
    expect(target).toMatch(FACT_ID);
    rewrite(host, { ...all[host], inputs: JSON.stringify([target]) } as Citation);

    const container = await renderCompany(slug);
    for (const citations of seen.providerCitations) expect(citations).toEqual({});
    // The input is listed (ids only) — hasCitation() knows it, as the
    // embedded slice's one level of inputs did.
    expect(listed()).toEqual([...onPage, target].sort());

    fireEvent.click(container.querySelector(`[data-amount][data-fact-id="${host}"]`)!);
    await waitFor(() => {
      expect(panelQueryAll("derived-input-chip")).toHaveLength(1);
    });
    expect(panelQueryAll("derived-input-chip-static")).toHaveLength(0);
    fireEvent.click(panelQueryAll("derived-input-chip")[0]);
    await waitFor(() => {
      expect(panelQueryAll("usaspending-card")).toHaveLength(1);
      expect(panelQueryAll("panel-fact-permalink")[0]?.textContent).toBe(`fact #${target.slice(0, 8)}`);
    });
    expect(shardCalls()).toContain(shardOf(target));
  }, 120_000);

  it("an input that resolves nowhere is not listed, so its chip stays plain (the old slice's rule)", async () => {
    const slug = "boeing";
    const all = getCitations();
    const host = lobbyingFigures(slug)[0].id;
    const onPage = renderedIds(await renderCompany(slug));
    const ghost = "0123456789abcdef";
    expect(ghost in all).toBe(false);
    rewrite(host, { ...all[host], inputs: JSON.stringify([ghost]) } as Citation);

    const container = await renderCompany(slug);
    expect(listed()).toEqual(onPage);
    fireEvent.click(container.querySelector(`[data-amount][data-fact-id="${host}"]`)!);
    await waitFor(() => {
      expect(panelQueryAll("derived-input-chip-static")).toHaveLength(1);
    });
    expect(panelQueryAll("derived-input-chip")).toHaveLength(0);
  }, 120_000);
});

// ── ROADMAP #10: the SAM registration line ───────────────────────────────────
//
// Each case substitutes its own registration for the family's, so it holds
// whether or not the export carries one (chain G's does for boeing): the
// page's other figures are measured with the family's own line removed.

describe("/company/{slug}/ lists the SAM registration's citation exactly when the line renders", () => {
  function withSam(slug: string, sam: EntitySamRegistration | undefined) {
    const details = getEntityDetails(slug);
    const had = Object.prototype.hasOwnProperty.call(details, "sam");
    const prior = details.sam;
    details.sam = sam;
    return () => {
      if (had) details.sam = prior;
      else delete details.sam;
    };
  }

  /** The ids the page renders with the family's own SAM line removed — the
   *  rest of the page, which a substituted registration must leave alone. */
  async function figuresWithoutSam(slug: string): Promise<string[]> {
    const own = getEntityDetails(slug).sam?.fact_id;
    const undo = withSam(slug, undefined);
    try {
      const ids = renderedIds(await renderCompany(slug));
      if (own) expect(ids).not.toContain(own);
      return ids;
    } finally {
      undo();
    }
  }

  function samFor(factId: string, status: string | null): EntitySamRegistration {
    return {
      uei: "ZZZZZZZZZZZZ",
      legal_business_name: "THE BOEING COMPANY",
      cage_code: null,
      registration_status: status,
      registration_expiration_date: null,
      primary_naics: null,
      business_types: null,
      retrieved_at: null,
      fact_id: factId,
    };
  }

  it("a rendered status is listed and opens its citation from its shard", async () => {
    const slug = "boeing";
    const all = getCitations();
    const onPage = await figuresWithoutSam(slug);
    // A real derived citation with no inputs, off this page (an input would
    // be listed too — the one-level rule the other tests pin).
    const samFact = Object.keys(all).find(
      (id) => all[id].kind === "derived" && all[id].inputs === "[]" && !onPage.includes(id),
    )!;
    expect(samFact).toMatch(FACT_ID);
    const undo = withSam(slug, samFor(samFact, "Active"));
    try {
      const container = await renderCompany(slug);
      for (const citations of seen.providerCitations) expect(citations).toEqual({});
      expect(listed()).toEqual([...onPage, samFact].sort());
      const prose = container.querySelector(`[data-prose-cite][data-fact-id="${samFact}"]`);
      expect(prose, "the status is a prose cite").not.toBeNull();
      fireEvent.click(prose!);
      await waitFor(() => {
        expect(panelQueryAll("panel-fact-permalink")[0]?.textContent).toBe(`fact #${samFact.slice(0, 8)}`);
        expect(panelQueryAll("derived-card")).toHaveLength(1);
      });
      expect(shardCalls()).toContain(shardOf(samFact));
    } finally {
      undo();
    }
  }, 120_000);

  it("no status, no line — and no listed id", async () => {
    const slug = "boeing";
    const all = getCitations();
    const onPage = await figuresWithoutSam(slug);
    // A real derived citation with no inputs, off this page (an input would
    // be listed too — the one-level rule the other tests pin).
    const samFact = Object.keys(all).find(
      (id) => all[id].kind === "derived" && all[id].inputs === "[]" && !onPage.includes(id),
    )!;
    expect(samFact).toMatch(FACT_ID);
    const undo = withSam(slug, samFor(samFact, null));
    try {
      const container = await renderCompany(slug);
      expect(container.querySelector("[data-sam-registration]")).toBeNull();
      expect(listed()).toEqual(onPage);
    } finally {
      undo();
    }
  }, 120_000);
});
