/**
 * /district/{code}/ and /district/ resolve their citations through the cite
 * shards (Task 28b, 2026-09-24).
 *
 * THE DEFECT THIS PINS. Both district templates built a per-page citation
 * slice with collectCitations() and handed it to <CitationPanelProvider>, a
 * client component — so every row of that slice was serialized into the
 * page's RSC payload. On /district/VA-11/ (chain C run 2's build) the object
 * was 50,556 of the page's 171,862 raw bytes: 50 citation rows, 20 of them the
 * by-year table's derived citations. It put the page over the INITIAL ceiling
 * gate 1 pins for the /district/<code>/ class (154,000 raw / 20,000 gzip),
 * a ceiling whose provenance says it is never raised to fit new content. The
 * index shipped a 190-row slice (168,934 raw bytes) the same way.
 *
 * THE CONTRACT, the one /programs/, /feed/, /years/, /flow/ and /lineage/
 * already keep: the provider mounts with an EMPTY embedded slice; every cited
 * figure still renders as a state-A <Cite> whose fact id is in the static HTML
 * (the no-JS and render-static contracts read that attribute, never the
 * slice); and a click resolves the fact from
 * /json/cite-shards/{fact_id[:2]}.json through the panel's fetch-on-miss path
 * (lib/cite-shards.ts) — the same path a program page takes for any fact
 * outside its own slice.
 *
 * FIX ROUND 1 (ruling R-28b-4). The empty slice also emptied what the panel's
 * synchronous hasCitation() knows, so the header total's derived card — whose
 * inputs are the page's own program rows — rendered its input chips plain:
 * 674 chips on 213 cards across the 189 detail pages of that build. The
 * detail page now passes the provider `shardResolvableIds`, the ids (never the
 * bodies) of the state-A figures it renders; for a listed id hasCitation()
 * answers true and a click fetches the body through the same fetch-on-miss
 * path. The prop is opt-in: /district/ and every other page pass none, and
 * their providers behave as before.
 *
 * Same seams as district-shared-code-members.test.tsx — @/lib/data's district
 * readers and @/lib/fy-range — plus @/lib/corpus and @/lib/og, which the index
 * calls at module scope; CoverageNote still reads the shipped sidecars, as it
 * does in the other district tests. The provider is the REAL one, wrapped
 * only to record the props it was given.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, fireEvent, waitFor } from "@testing-library/react";
import React from "react";
import { readdirSync, readFileSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import type {
  Citation,
  CitationsMap,
  DistrictDetail,
  DistrictIndex,
  DistrictProgram,
} from "@/lib/data";
import { __resetCiteShardCache } from "@/lib/cite-shards";
import { CitationPanelContext } from "@/components/cite";
import { CitationPanelProvider } from "@/components/citation-panel";

// ── Fixtures ─────────────────────────────────────────────────────────────────

const FID = {
  progA: "a1a1a1a1a1a1a1a1",
  progB: "b2b2b2b2b2b2b2b2",
  // a program row with no obligation renders "—", not a Cite
  progNull: "4b4b4b4b4b4b4b4b",
  fy25Net: "c3c3c3c3c3c3c3c3",
  fy25Gross: "d4d4d4d4d4d4d4d4",
  fy26Net: "e5e5e5e5e5e5e5e5",
  fy26Gross: "f6f6f6f6f6f6f6f6",
  linkable: "0707070707070707",
  cited: "1818181818181818",
  // index only
  geoTotal: "2929292929292929",
  otherDistrict: "3a3a3a3a3a3a3a3a",
} as const;

const NULLS = {
  amount_text: null,
  amount_thousands: null,
  bottom_pt: null,
  cells: null,
  hosted_pdf_url: null,
  page_height: null,
  page_number: null,
  page_width: null,
  pe_bli: null,
  resolution: null,
  sha256: null,
  sheet: null,
  top_pt: null,
  x0: null,
  x1: null,
  xml_path: null,
};

function usaspending(value: string): Citation {
  return {
    ...NULLS,
    kind: "usaspending",
    formula: null,
    inputs: null,
    official_url: "https://api.usaspending.gov/api/v2/references/filter/",
    query_body: JSON.stringify({
      filters: { award_ids: ["N0002417C6327"] },
      version: "2020-06-01",
    }),
    recorded_value: value,
    retrieved_at: null,
    units: "USD",
  } as unknown as Citation;
}

function derived(value: string, inputs: string[]): Citation {
  return {
    ...NULLS,
    kind: "derived",
    formula: "fct_district_totals.total_obligation for pop_district='ZZ-01'",
    inputs: JSON.stringify(inputs),
    official_url: null,
    query_body: null,
    recorded_value: value,
    retrieved_at: "2026-09-19T13:00:26+00:00",
    units: "USD",
  } as unknown as Citation;
}

/** citations.json as the build sees it — what collectCitations would slice. */
const ALL: CitationsMap = {
  [FID.progA]: usaspending("8000000.000"),
  [FID.progB]: usaspending("2500000.000"),
  [FID.fy25Net]: derived("6000000.000", []),
  [FID.fy25Gross]: derived("6500000.000", []),
  [FID.fy26Net]: derived("4500000.000", []),
  [FID.fy26Gross]: derived("4500000.000", []),
  [FID.linkable]: derived("10500000.000", [FID.progA, FID.progB]),
  [FID.cited]: derived("10000000.000", [FID.progA, FID.progB]),
  [FID.geoTotal]: derived("90000000.000", []),
  [FID.otherDistrict]: derived("1000000.000", []),
};

function program(over: Partial<DistrictProgram>): DistrictProgram {
  return {
    account: null,
    award_count: 1,
    fact_id: null,
    organization: "N",
    pe_bli: "0601101E",
    program_url: "/program/0601101E/",
    recipient_count: 1,
    shared_award_count: 1,
    split_key: "0601101E",
    title: "A Program",
    total_obligation: 1_000_000,
    transaction_count: 1,
    ...over,
  };
}

const DETAIL: DistrictDetail = {
  pop_district: "ZZ-01",
  pop_state: "ZZ",
  program_count: 3,
  award_count: 3,
  programs: [
    program({ fact_id: FID.progA, total_obligation: 8_000_000 }),
    program({
      fact_id: FID.progB,
      pe_bli: "0603000N",
      split_key: "0603000N",
      program_url: "/program/0603000N/",
      title: "Another Program",
      total_obligation: 2_500_000,
    }),
    program({
      fact_id: FID.progNull,
      pe_bli: "0604000A",
      split_key: "0604000A",
      program_url: "/program/0604000A/",
      title: "A Program With No Obligation",
      total_obligation: null,
    }),
  ],
  by_year: [
    {
      fiscal_year: 2025,
      award_count: 2,
      total_obligation: 6_000_000,
      total_fact_id: FID.fy25Net,
      // gross > net on one row renders the "Before deobligations" column
      positive_obligation: 6_500_000,
      positive_fact_id: FID.fy25Gross,
    },
    {
      fiscal_year: 2026,
      award_count: 1,
      total_obligation: 4_500_000,
      total_fact_id: FID.fy26Net,
      positive_obligation: 4_500_000,
      positive_fact_id: FID.fy26Gross,
    },
  ],
  by_year_programs: [],
  // cited != linkable, so BOTH header cards render
  total_cited_dollars: 10_000_000,
  total_cited_fact_id: FID.cited,
  total_linkable_dollars: 10_500_000,
  total_linkable_fact_id: FID.linkable,
};

const INDEX: DistrictIndex = {
  districts: [
    {
      pop_district: "ZZ-01",
      pop_state: "ZZ",
      program_count: 2,
      award_count: 3,
      total_cited_dollars: 10_000_000,
      total_cited_fact_id: FID.cited,
      total_linkable_dollars: 10_500_000,
      total_linkable_fact_id: FID.linkable,
    },
    {
      pop_district: "ZZ-02",
      pop_state: "ZZ",
      program_count: 1,
      award_count: 1,
      total_cited_dollars: 1_000_000,
      total_cited_fact_id: null,
      total_linkable_dollars: 1_000_000,
      total_linkable_fact_id: FID.otherDistrict,
    },
  ],
  geo_grand_total: 90_000_000,
  geo_grand_total_dataset: "dim_geography",
  geo_grand_total_fact_id: FID.geoTotal,
  total_districts: 2,
};

// ── Seams ────────────────────────────────────────────────────────────────────

const seen = vi.hoisted(() => ({
  providerCitations: [] as unknown[],
  providerResolvable: [] as unknown[],
  sliced: [] as string[][],
  // per-test override of the detail sidecar (null → DETAIL)
  detail: null as DistrictDetail | null,
}));

vi.mock("@/lib/fy-range", () => ({
  getAwardFyRange: () => ({
    fyMin: 2017,
    fyMax: 2026,
    maxPartial: false,
    label: "FY2017–FY2026",
  }),
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

vi.mock("@/lib/data", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/lib/data")>();
  // Both slice builders behave as they do in the build — a page that still
  // builds a slice ships a NON-empty one, and the test sees it.
  const slice = (ids: string[]): CitationsMap => {
    seen.sliced.push(ids);
    return Object.fromEntries(ids.filter((id) => id in ALL).map((id) => [id, ALL[id]]));
  };
  return {
    ...real,
    getDistrictIndex: () => INDEX,
    getDistrictDetail: () => seen.detail ?? DETAIL,
    getProgramsCount: () => 1741,
    collectCitations: slice,
    collectCitationsWithInputs: slice,
  };
});

vi.mock("@/lib/corpus", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/corpus")>()),
  getCrosswalkCounts: () => [
    { id: "district-linkable", value: 314, where: "/district/", counts: "program elements" },
  ],
}));

vi.mock("@/lib/og", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/og")>()),
  coreOgImages: () => [],
}));

function shardResponse(map: CitationsMap): Response {
  return { ok: true, status: 200, json: () => Promise.resolve(map) } as unknown as Response;
}

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  seen.providerCitations.length = 0;
  seen.providerResolvable.length = 0;
  seen.sliced.length = 0;
  seen.detail = null;
  __resetCiteShardCache();
  // A shard request returns ONLY that shard's rows, as the real files do;
  // anything else (asset-config's /config.json) rejects and falls back.
  fetchMock = vi.fn((url: string) => {
    const m = /^\/json\/cite-shards\/([0-9a-f]{2})\.json$/.exec(String(url));
    if (!m) return Promise.reject(new Error(`unmocked fetch ${url}`));
    return Promise.resolve(
      shardResponse(
        Object.fromEntries(Object.entries(ALL).filter(([id]) => id.startsWith(m[1]))),
      ),
    );
  });
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

async function renderDetail() {
  const Page = (await import("@/app/district/[district]/page")).default;
  const el = await Page({ params: Promise.resolve({ district: "ZZ-01" }) });
  return render(el as React.ReactElement).container;
}

async function renderIndex() {
  const Page = (await import("@/app/district/page")).default;
  return render(<Page />).container;
}

function factIds(container: HTMLElement): string[] {
  return Array.from(container.querySelectorAll("[data-amount][data-fact-id]"))
    .map((el) => el.getAttribute("data-fact-id")!)
    .sort();
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

const shardOf = (id: string) => `/json/cite-shards/${id.slice(0, 2)}.json`;

function panelQueryAll(testId: string): Element[] {
  return Array.from(
    document.querySelectorAll(`[data-testid="citation-panel"] [data-testid="${testId}"]`),
  );
}

/** Click a figure, wait for its derived card, return the card's chip counts. */
async function openDerived(container: HTMLElement, id: string) {
  fireEvent.click(container.querySelector(`[data-fact-id="${id}"]`)!);
  await waitFor(() => {
    expect(panelQueryAll("derived-card")).toHaveLength(1);
  });
  return {
    clickable: panelQueryAll("derived-input-chip"),
    plain: panelQueryAll("derived-input-chip-static"),
  };
}

function shardCalls(): string[] {
  return fetchMock.mock.calls
    .map((c) => String(c[0]))
    .filter((u) => u.includes("cite-shards"));
}

// ── /district/{code}/ ────────────────────────────────────────────────────────

describe("/district/{code}/ citations come from the cite shards", () => {
  it("mounts the provider with an empty slice and builds none", async () => {
    await renderDetail();
    expect(seen.providerCitations.length).toBeGreaterThan(0);
    for (const citations of seen.providerCitations) {
      expect(citations).toEqual({});
    }
    expect(seen.sliced).toEqual([]);
  });

  it("still renders every figure as a state-A Cite carrying its own fact id", async () => {
    const container = await renderDetail();
    expect(factIds(container)).toEqual(
      [
        FID.progA,
        FID.progB,
        FID.fy25Net,
        FID.fy25Gross,
        FID.fy26Net,
        FID.fy26Gross,
        FID.linkable,
        FID.cited,
      ].sort(),
    );
  });

  it("a click resolves the fact from /json/cite-shards/{fact_id[:2]}.json", async () => {
    const container = await renderDetail();
    const figure = container.querySelector(`[data-fact-id="${FID.progA}"]`)!;
    fireEvent.click(figure);
    await waitFor(() => {
      expect(
        document.querySelector('[data-testid="citation-panel"] [data-testid="usaspending-card"]'),
      ).not.toBeNull();
    });
    expect(shardCalls()).toEqual(["/json/cite-shards/a1.json"]);
  });
});

// ── /district/ ───────────────────────────────────────────────────────────────

describe("/district/ citations come from the cite shards", () => {
  it("mounts the provider with an empty slice and builds none", async () => {
    await renderIndex();
    expect(seen.providerCitations.length).toBeGreaterThan(0);
    for (const citations of seen.providerCitations) {
      expect(citations).toEqual({});
    }
    expect(seen.sliced).toEqual([]);
  });

  it("still renders the grand total and every district row as a state-A Cite", async () => {
    const container = await renderIndex();
    expect(factIds(container)).toEqual(
      [FID.geoTotal, FID.linkable, FID.otherDistrict].sort(),
    );
  });

  it("a click resolves the fact from /json/cite-shards/{fact_id[:2]}.json", async () => {
    const container = await renderIndex();
    const figure = container.querySelector(`[data-fact-id="${FID.geoTotal}"]`)!;
    fireEvent.click(figure);
    await waitFor(() => {
      expect(
        document.querySelector('[data-testid="citation-panel"] [data-testid="derived-card"]'),
      ).not.toBeNull();
    });
    expect(shardCalls()).toEqual(["/json/cite-shards/29.json"]);
  });
});

// ── R-28b-4: the detail page lists the ids it renders ────────────────────────

describe("/district/{code}/ keeps its derived cards' inputs clickable (R-28b-4)", () => {
  it("passes the provider exactly the fact ids it renders — ids only, no bodies", async () => {
    const container = await renderDetail();
    const rendered = renderedIds(container);
    expect(rendered).not.toContain(FID.progNull); // rendered "—", so not listed
    expect(seen.providerResolvable.length).toBeGreaterThan(0);
    for (const listed of seen.providerResolvable) {
      expect(Array.isArray(listed)).toBe(true);
      const ids = listed as unknown[];
      for (const id of ids) expect(id).toMatch(/^[0-9a-f]{16}$/);
      expect(new Set(ids).size).toBe(ids.length);
      expect([...(ids as string[])].sort()).toEqual(rendered);
    }
    // ...and the embedded slice stays empty: the list carries no bodies
    for (const citations of seen.providerCitations) {
      expect(citations).toEqual({});
    }
    expect(seen.sliced).toEqual([]);
  });

  it("the list follows what renders: no cited card and no gross column list neither id", async () => {
    seen.detail = {
      ...DETAIL,
      total_cited_dollars: DETAIL.total_linkable_dollars,
      by_year: DETAIL.by_year!.map((r) => ({
        ...r,
        positive_obligation: r.total_obligation,
      })),
    };
    const container = await renderDetail();
    const expected = [FID.progA, FID.progB, FID.fy25Net, FID.fy26Net, FID.linkable].sort();
    expect(renderedIds(container)).toEqual(expected);
    for (const listed of seen.providerResolvable) {
      expect([...(listed as string[])].sort()).toEqual(expected);
    }
  });

  it.each([
    ["the header (linkable) total", FID.linkable],
    ["the cited total", FID.cited],
  ])(
    "%s's derived card shows its inputs as clickable chips, and a chip opens its row from the shard",
    async (_label, id) => {
      const container = await renderDetail();
      const { clickable, plain } = await openDerived(container, id);
      expect(plain).toHaveLength(0);
      expect(clickable.map((c) => c.textContent)).toEqual([
        `#${FID.progA.slice(-8)}`,
        `#${FID.progB.slice(-8)}`,
      ]);

      fireEvent.click(clickable[0]);
      await waitFor(() => {
        expect(panelQueryAll("usaspending-card")).toHaveLength(1);
      });
      // the SAME fetch-on-miss path: one shard per fact, nothing else fetched
      expect(shardCalls()).toEqual([shardOf(id), shardOf(FID.progA)]);
    },
  );
});

// ── the list is opt-in ───────────────────────────────────────────────────────

describe("shardResolvableIds is opt-in — a provider without it is unchanged", () => {
  function Probe({ ids }: { ids: string[] }) {
    const { hasCitation } = React.useContext(CitationPanelContext);
    return (
      <ul>
        {ids.map((id) => (
          <li key={id} data-probe={id}>
            {String(hasCitation!(id))}
          </li>
        ))}
      </ul>
    );
  }

  const probe = (container: HTMLElement) =>
    Object.fromEntries(
      Array.from(container.querySelectorAll("[data-probe]")).map((el) => [
        el.getAttribute("data-probe"),
        el.textContent,
      ]),
    );

  it("without the prop, hasCitation() knows the embedded slice and nothing else", () => {
    const { container } = render(
      <CitationPanelProvider citations={{ [FID.progA]: ALL[FID.progA] }}>
        <Probe ids={[FID.progA, FID.progB, FID.linkable]} />
      </CitationPanelProvider>,
    );
    expect(probe(container)).toEqual({
      [FID.progA]: "true",
      [FID.progB]: "false",
      [FID.linkable]: "false",
    });
  });

  it("with the prop, a listed id also answers true; an unlisted one still does not", () => {
    const { container } = render(
      <CitationPanelProvider
        citations={{ [FID.progA]: ALL[FID.progA] }}
        shardResolvableIds={[FID.progB]}
      >
        <Probe ids={[FID.progA, FID.progB, FID.linkable]} />
      </CitationPanelProvider>,
    );
    expect(probe(container)).toEqual({
      [FID.progA]: "true",
      [FID.progB]: "true",
      [FID.linkable]: "false",
    });
  });

  it("/district/ passes no list, so a row's inputs (never rendered there) stay plain chips", async () => {
    const container = await renderIndex();
    expect(seen.providerResolvable.length).toBeGreaterThan(0);
    for (const listed of seen.providerResolvable) expect(listed).toBeUndefined();
    const { clickable, plain } = await openDerived(container, FID.linkable);
    expect(clickable).toHaveLength(0);
    expect(plain).toHaveLength(2);
  });

  it("only /district/{code}/ passes the list; every other provider mount passes the props it did", () => {
    const SRC = resolve(__dirname, "..");
    const tsx = (dir: string): string[] =>
      readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
        if (e.name === "__tests__" || e.name === "node_modules") return [];
        const full = join(dir, e.name);
        if (e.isDirectory()) return tsx(full);
        return e.name.endsWith(".tsx") && !e.name.endsWith(".test.tsx") ? [full] : [];
      });
    const owners = tsx(SRC)
      .filter((f) => readFileSync(f, "utf8").includes("shardResolvableIds="))
      .map((f) => relative(SRC, f))
      .sort();
    expect(owners).toEqual(["app/district/[district]/page.tsx"]);
  });
});
