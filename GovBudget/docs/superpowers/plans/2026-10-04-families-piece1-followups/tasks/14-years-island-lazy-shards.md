<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. -->

### Task 14: /years/ island — the core on open, each shard when a reader asks, the gap tooltip and edition legend restated, /agency/ looks decade cells up by slug (#193, #208, Q12–Q14)

**Spec:** `docs/superpowers/specs/2026-10-04-families-piece1-followups-design.md` §3.4 (island), §3.5 "/agency/[org]/ lookup" (ROADMAP #208), §3.7 (tooltip, edition legend), §3.3 "No stale shards" (the `prepare-assets.mjs` 5d mirror); owner answers Q10, Q12, Q13 (its copy half is Task 15's), Q14.
**Files:**
- Create: `site/src/lib/years-matrix-shards.mjs`, `site/src/lib/years-matrix-shards.d.mts`, `site/src/__tests__/years-matrix-shards.test.ts`, `site/src/__tests__/decade-cells-slug-lookup.test.ts`
- Modify: `site/src/components/years-matrix.tsx` (header comment, imports, types, `defaultSortKey`'s parameter, the load state, the component's state, fetch and column logic, both picker chip maps, the edition legend, the table's markers, the expand caret, `ProgramCellTd`; anchor on the quoted text — base lines `:3-44`, `:56`, `:83-152`, `:387`, `:575-578`, `:621-622`, `:698`, `:707-766`, `:817-838`, `:975-1024`, `:1043-1045`, `:1179`, `:1402`, `:1489`, `:1585-1646`)
- Modify (test): `site/src/__tests__/years-matrix.test.tsx` (header, imports, the fetch harness, four fetch mocks, the two piece-1 fence tests, two decade-view tests that now wait for a shard, plus a new `describe` block)
- Modify: `site/src/app/agency/[org]/page.tsx` (`:91-92`, `:115`, `:361-367`), `site/scripts/prepare-assets.mjs` (step 5d, `:189-195`), `site/scripts/gates/__tests__/fetch-targets.test.mjs` (`:122-136`)

**Interfaces:**
- Consumes: Task 13's file contract — `json/years_matrix.json` (`schema_version` 2, `build_id`, `shards: [{name, path, columns, bytes, sha256}]`, rows `{pe_bli, title, slug?, family_id?, np, cells}`) and `json/years_matrix/{decade,detail}.json` (`{schema_version, build_id, shard, columns, rows}`, rows keyed by `slug ?? pe_bli`, detail rows `{cells?, projects?}`); its fixtures `tests/fixtures/years_matrix_split/{basic,split_keys}/`.
- Produces:
  - `site/src/lib/years-matrix-shards.mjs`: `YEARS_SHARD_NAMES` (`["decade", "detail"]`), `yearsRowKey(program) -> string`, `shardOfColumns(core) -> Map<string, "decade" | "detail">`, `mergeYearsMatrix(core, shards = []) -> YearsMatrixData` (throws on a shard with another `build_id`; a schema-1 payload passed as the core merges to itself), typed by `years-matrix-shards.d.mts` (`YearsShardName`, `YearsShardManifestEntry`, `YearsShardRow`, `YearsMatrixShard`, `YearsCoreProgram`, `YearsMatrixCore`). Task 15's gate loader imports `mergeYearsMatrix` and `YEARS_SHARD_NAMES` from it.
  - The island's DOM contract for Task 15's live legs: `table[data-testid="years-matrix"]` carries `data-shards` (`"core"`, `"core decade"`, `"core detail"`, `"core decade detail"`) and `aria-busy` (`"true"` while a column the reader chose, or an expanded row's projects, has not merged); a picker chip whose shard is loading carries `data-shard-state="loading"` and `aria-busy="true"`, one whose shard failed `data-shard-state="error"` and the text `(unavailable)`. On open the island requests `/json/years_matrix.json` only (when the default columns are decade columns, as on every export since 5E).
  - Static fetch targets `/json/years_matrix/decade.json` and `/json/years_matrix/detail.json` in `site/src` (six in all; Task 15 raises linkgraph's floor to 6).
  - `site/scripts/prepare-assets.mjs` copies `json/years_matrix/` (mirror) when the core's `schema_version >= 2`.

The island fetches the core on mount and asks for a shard only from an event:
the core's own load callback (the opening view's columns, which on a decade
payload need no shard), a picker chip that turns on a column the shard holds,
or an expand caret (project rows ship in `detail.json`). Nothing loads from an
effect — the project's React lint (`react-hooks/set-state-in-effect`) rejects
a `setState` there, and "a shard loads because a reader asked for what it
holds" is the design's rule anyway. A chosen column joins the grid only once
its shard has merged: a "—" in an unloaded column would claim the book has no
figure. If a shard's `build_id` is not the core's (a deploy landed between the
two fetches), the core is fetched once more past the HTTP cache; a matching
fresh core moves the grid to that build, anything else shows a per-column
error. A schema-1 payload (an export from before Task 13's split, which is
what `data/site` holds until the release export) renders whole, with no shard
request, so a site build made between this task and Task 22 still works;
`prepare-assets.mjs` copies the shard directory only for a split export.

With the fence gone (Task 13), every decade gap is an absence from that
edition's book, so the piece-1 tooltip "Any PB20XX procurement history is on
the program page, not yet in this grid" reverts to "Not in the PB20XX edition"
(Q12) and the legend's PB2024 sentence becomes the Q14 sentence. On the
2026-10-04 build all 27 split-key rows on `/agency/N/`, `/agency/DCSA/`,
`/agency/DTRA/`, `/agency/OSD/`, `/agency/DMACT/`, `/agency/DHRA/` and
`/agency/DLA/` render "—" for FY24 (counted in `site/out/agency/*/index.html`,
built 2026-10-04 15:54): the page looks the slug-keyed map up by bare
`pe_bli`. The rows still link to `/program/<pe_bli>/` (the shared-code page
that lists both members); this task changes the lookups only, as §3.5 says.

- [ ] **Step 1: Write the failing merge test**

Create `site/src/__tests__/years-matrix-shards.test.ts`:

```ts
/**
 * ROADMAP #193 — the JS merge inverts the Python split.
 *
 * tests/fixtures/years_matrix_split/<name>/ is written by the Python split
 * (export_site.split_years_matrix) and held current by
 * tests/test_export_years_matrix.py::TestCrossLanguageFixture. Here the JS
 * merge — what the /years/ island and the yearsmatrix gate run — must turn
 * those files back into the payload they were split from. Hermetic: the
 * fixtures are committed, nothing reads data/site.
 */
import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";
import {
  mergeYearsMatrix,
  shardOfColumns,
  yearsRowKey,
  YEARS_SHARD_NAMES,
  type YearsMatrixCore,
  type YearsMatrixShard,
} from "@/lib/years-matrix-shards.mjs";
import type { YearsMatrixData } from "@/components/years-matrix";

const FIXTURES = path.resolve(
  __dirname, "..", "..", "..", "tests", "fixtures", "years_matrix_split",
);

function read<T>(...parts: string[]): T {
  return JSON.parse(fs.readFileSync(path.join(FIXTURES, ...parts), "utf8")) as T;
}

/** A payload or merged view without the keys the split adds (design §3.3:
 *  merge(split(p)) == p ignoring schema_version, build_id, shards and np). */
const SPLIT_KEYS = new Set(["schema_version", "build_id", "shards"]);
function strip(view: YearsMatrixData): unknown {
  const without = (obj: object, drop: (k: string) => boolean) =>
    Object.fromEntries(Object.entries(obj).filter(([k]) => !drop(k)));
  return {
    ...without(view, (k) => SPLIT_KEYS.has(k)),
    orgs: view.orgs.map((o) => ({
      ...o,
      programs: o.programs.map((p) => without(p, (k) => k === "np")),
    })),
  };
}

describe.each(["basic", "split_keys"])("the %s split fixture", (name) => {
  const core = read<YearsMatrixCore>(name, "years_matrix.json");
  const shards = YEARS_SHARD_NAMES.map((s) =>
    read<YearsMatrixShard>(name, "years_matrix", `${s}.json`),
  );
  const payload = read<YearsMatrixData>(name, "payload.json");

  it("merges back into the payload it was split from", () => {
    expect(strip(mergeYearsMatrix(core, shards))).toEqual(strip(payload));
  });

  it("keeps each row's np equal to its merged project count", () => {
    for (const o of mergeYearsMatrix(core, shards).orgs) {
      for (const p of o.programs) expect(p.np).toBe(p.projects.length);
    }
  });

  it("maps every shard column to its shard and no default column to any", () => {
    const of = shardOfColumns(core);
    for (const k of core.decade_default_columns ?? []) expect(of.has(k)).toBe(false);
    for (const s of shards) for (const c of s.columns) expect(of.get(c)).toBe(s.shard);
  });

  it("leaves a not-yet-loaded column's cells absent, never zero", () => {
    const of = shardOfColumns(core);
    for (const o of mergeYearsMatrix(core, []).orgs) {
      for (const p of o.programs) {
        for (const k of Object.keys(p.cells)) expect(of.has(k)).toBe(false);
        expect(p.projects).toEqual([]);
      }
    }
  });

  it("refuses a shard from another build", () => {
    const stale = { ...shards[0], build_id: "0".repeat(64) };
    expect(() => mergeYearsMatrix(core, [stale])).toThrow(/build_id/);
  });

  it("merges a pre-split payload (schema 1, one file) to itself", () => {
    const asCore = payload as unknown as YearsMatrixCore;
    expect(strip(mergeYearsMatrix(asCore, []))).toEqual(strip(payload));
  });
});

describe("split-key rows", () => {
  it("are keyed by slug in the core and in the shards", () => {
    const core = read<YearsMatrixCore>("split_keys", "years_matrix.json");
    const keys = core.orgs.flatMap((o) => o.programs.map(yearsRowKey));
    expect(keys).toEqual(expect.arrayContaining(["20-DCSA", "20-DTRA"]));
    const detail = read<YearsMatrixShard>("split_keys", "years_matrix", "detail.json");
    expect(Object.keys(detail.rows).sort()).toEqual(["20-DCSA", "20-DTRA"]);
  });
});
```

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site && npx vitest run src/__tests__/years-matrix-shards.test.ts
```

Expected: `FAIL  src/__tests__/years-matrix-shards.test.ts` with
`Error: Failed to resolve import "@/lib/years-matrix-shards.mjs"`.

- [ ] **Step 2: Write the shard module and its types**

Create `site/src/lib/years-matrix-shards.mjs`:

```js
/**
 * years-matrix-shards.mjs — the /years/ core and its lazy shards
 * (families piece-1 follow-ups design §3.2–3.4, ROADMAP #193).
 *
 * export_site.py writes json/years_matrix.json (the CORE: the header, every
 * row with its project count `np`, and the cells of decade_default_columns)
 * and two shards, json/years_matrix/decade.json (the other decade columns)
 * and json/years_matrix/detail.json (the PB2026 amount-type, Δ and %Δ cells
 * and the project sub-rows). Every file carries the same build_id.
 *
 * mergeYearsMatrix puts loaded shards back on the core's rows. It is the JS
 * mirror of export_site.merge_years_matrix, key for key, and
 * tests/fixtures/years_matrix_split/ pins the pair from both sides
 * (tests/test_export_years_matrix.py and
 * src/__tests__/years-matrix-shards.test.ts). The client island merges
 * incrementally (the core first, then whichever shard a reader asks for);
 * the yearsmatrix gate merges all three.
 *
 * Plain .mjs (typed by years-matrix-shards.d.mts) so the gate scripts can
 * import it without a TypeScript step.
 */

/** The lazy shards, in the core manifest's order. */
export const YEARS_SHARD_NAMES = ["decade", "detail"];

/** A row's identity across the core and its shards: `slug ?? pe_bli`. */
export function yearsRowKey(program) {
  return program.slug ?? program.pe_bli;
}

/** column key → the shard that holds it, read from the core's manifest. A
 *  key in no shard (a default decade column) is in the core itself. */
export function shardOfColumns(core) {
  const out = new Map();
  for (const entry of core.shards ?? []) {
    for (const col of entry.columns ?? []) out.set(col, entry.name);
  }
  return out;
}

/**
 * The core with each shard's cells, and the detail shard's project rows, put
 * back on their rows. Rows a shard does not name keep what the core gave
 * them (a core row has no projects, so they default to []; a pre-split,
 * schema-1 payload passed as the core therefore merges to itself, and the
 * island still renders an export from before the split). Throws when a
 * shard carries another build_id: a shard from one export never fills a
 * core from another.
 */
export function mergeYearsMatrix(core, shards = []) {
  for (const shard of shards) {
    if (shard.build_id !== core.build_id) {
      throw new Error(
        `years_matrix shard ${JSON.stringify(shard.shard)} carries build_id ` +
          `${shard.build_id} but the core carries ${core.build_id}: files from two exports`,
      );
    }
  }
  const { orgs, ...header } = core;
  return {
    ...header,
    orgs: orgs.map((org) => ({
      ...org,
      programs: org.programs.map((program) => {
        const key = yearsRowKey(program);
        const cells = { ...program.cells };
        let projects = program.projects ?? [];
        for (const shard of shards) {
          const row = shard.rows?.[key];
          if (!row) continue;
          if (row.cells) Object.assign(cells, row.cells);
          if (row.projects !== undefined) projects = row.projects;
        }
        return { ...program, cells, projects };
      }),
    })),
  };
}
```

Create `site/src/lib/years-matrix-shards.d.mts`:

```ts
import type {
  YearsCell,
  YearsMatrixData,
  YearsProgram,
  YearsProject,
} from "../components/years-matrix";

/** The two lazy /years/ shards (ROADMAP #193). */
export type YearsShardName = "decade" | "detail";

/** One entry of the core's `shards` manifest. */
export interface YearsShardManifestEntry {
  name: YearsShardName;
  /** Relative to /json/: "years_matrix/decade.json", "years_matrix/detail.json". */
  path: string;
  columns: string[];
  bytes: number;
  sha256: string;
}

/** A shard's row: only what that row has in the shard's columns. */
export interface YearsShardRow {
  cells?: Record<string, YearsCell>;
  projects?: YearsProject[];
}

export interface YearsMatrixShard {
  schema_version: number;
  build_id: string;
  shard: YearsShardName;
  columns: string[];
  /** Keyed by `slug ?? pe_bli` (yearsRowKey). */
  rows: Record<string, YearsShardRow>;
}

/** A core row: no project rows (detail.json has them), their count in `np`. */
export type YearsCoreProgram = Omit<YearsProgram, "projects" | "np"> & { np: number };

/** json/years_matrix.json, schema_version 2: the header, every row and the
 *  default decade columns' cells. */
export interface YearsMatrixCore extends Omit<YearsMatrixData, "orgs" | "build_id" | "shards"> {
  build_id: string;
  shards: YearsShardManifestEntry[];
  orgs: { org: string; programs: YearsCoreProgram[] }[];
}

export const YEARS_SHARD_NAMES: readonly YearsShardName[];
export function yearsRowKey(program: { pe_bli: string; slug?: string }): string;
export function shardOfColumns(
  core: Pick<YearsMatrixCore, "shards">,
): Map<string, YearsShardName>;
export function mergeYearsMatrix(
  core: YearsMatrixCore,
  shards?: YearsMatrixShard[],
): YearsMatrixData;
```

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site && npx vitest run src/__tests__/years-matrix-shards.test.ts
```

Expected: `Tests  13 passed (13)` (six per fixture, one for split-key rows).

- [ ] **Step 3: Write the failing island tests**

**Edit T14.1** — header — `site/src/__tests__/years-matrix.test.tsx`. Replace this exact text:

```tsx
 *   - expand caret reveals project sub-rows; org header collapses its section
 *   - sorting flattens the grouped view (global ordering, missing-last)
 */
```

with:

```tsx
 *   - expand caret reveals project sub-rows; org header collapses its section
 *   - sorting flattens the grouped view (global ordering, missing-last)
 *
 * ROADMAP #193: the island loads json/years_matrix.json (the core) and each
 * lazy shard only when a reader asks for what it holds; the fixtures below
 * are whole matrices, served split the way the exporter splits them.
 */
```

**Edit T14.2** — imports — `site/src/__tests__/years-matrix.test.tsx`. Replace this exact text:

```tsx
  YearsMatrix,
  type YearsMatrixData,
} from "@/components/years-matrix";
```

with:

```tsx
  YearsMatrix,
  type YearsCell,
  type YearsMatrixData,
} from "@/components/years-matrix";
import type {
  YearsMatrixCore,
  YearsMatrixShard,
  YearsShardName,
  YearsShardRow,
} from "@/lib/years-matrix-shards.mjs";
```

**Edit T14.3** — fetch harness — `site/src/__tests__/years-matrix.test.tsx`. Replace this exact text:

```tsx
let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn((url: string) => {
    if (String(url) === "/json/years_matrix.json") {
      return Promise.resolve(jsonResponse(MATRIX));
    }
    return Promise.reject(new Error(`unmocked fetch ${url}`));
  });
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

async function renderMatrix() {
  const utils = render(<YearsMatrix />);
  await waitFor(() => {
    expect(screen.getByTestId("years-matrix")).toBeInTheDocument();
  });
  return utils;
}
```

with:

```tsx
/**
 * Split a whole fixture matrix the way export_site.split_years_matrix does:
 * the core keeps the header, every row (with np) and the default decade
 * columns' cells; decade.json the other decade columns; detail.json the
 * amount-type, Δ and %Δ cells and the projects. (The real split and the real
 * merge are pinned against each other by years-matrix-shards.test.ts.)
 */
function splitForTest(v1: YearsMatrixData, buildId = "build-1") {
  const defaults = new Set(v1.decade_default_columns ?? []);
  const lazy = (v1.decade_columns ?? [])
    .map((c) => c.key)
    .filter((k) => !defaults.has(k));
  const detailCols = [...v1.amount_types, ...v1.delta_columns];
  const decadeRows: Record<string, YearsShardRow> = {};
  const detailRows: Record<string, YearsShardRow> = {};
  const orgs = v1.orgs.map((o) => ({
    org: o.org,
    programs: o.programs.map((p) => {
      const key = p.slug ?? p.pe_bli;
      const { cells, projects, ...rest } = p;
      const coreCells: Record<string, YearsCell> = {};
      const decadeCells: Record<string, YearsCell> = {};
      const detailCells: Record<string, YearsCell> = {};
      for (const [k, c] of Object.entries(cells)) {
        if (!c) continue;
        if (defaults.has(k)) coreCells[k] = c;
        else if (lazy.includes(k)) decadeCells[k] = c;
        else detailCells[k] = c;
      }
      if (Object.keys(decadeCells).length) decadeRows[key] = { cells: decadeCells };
      const detail: YearsShardRow = {};
      if (Object.keys(detailCells).length) detail.cells = detailCells;
      if (projects.length) detail.projects = projects;
      if (Object.keys(detail).length) detailRows[key] = detail;
      return { ...rest, np: projects.length, cells: coreCells };
    }),
  }));
  const shard = (
    name: YearsShardName,
    columns: string[],
    rows: Record<string, YearsShardRow>,
  ): YearsMatrixShard => ({ schema_version: 2, build_id: buildId, shard: name, columns, rows });
  const core: YearsMatrixCore = {
    ...v1,
    schema_version: 2,
    build_id: buildId,
    orgs,
    shards: [
      { name: "decade", path: "years_matrix/decade.json", columns: lazy, bytes: 0, sha256: "" },
      { name: "detail", path: "years_matrix/detail.json", columns: detailCols, bytes: 0, sha256: "" },
    ],
  };
  return {
    core,
    decade: shard("decade", lazy, decadeRows),
    detail: shard("detail", detailCols, detailRows),
  };
}

const CORE_URL = "/json/years_matrix.json";
const DECADE_URL = "/json/years_matrix/decade.json";
const DETAIL_URL = "/json/years_matrix/detail.json";

let fetchMock: ReturnType<typeof vi.fn>;

/** Serve a whole fixture as the core and its two shards. `routes` overrides a
 *  URL: a body, or a function called per request (a body that changes, or a
 *  promise the test resolves itself). */
function serveMatrix(v1: YearsMatrixData, routes: Record<string, unknown> = {}) {
  const files = splitForTest(v1);
  const table: Record<string, unknown> = {
    [CORE_URL]: files.core,
    [DECADE_URL]: files.decade,
    [DETAIL_URL]: files.detail,
    ...routes,
  };
  fetchMock.mockImplementation((url: string) => {
    const route = table[String(url)];
    if (route === undefined) return Promise.reject(new Error(`unmocked fetch ${url}`));
    const body = typeof route === "function" ? (route as () => unknown)() : route;
    return Promise.resolve(body).then(jsonResponse);
  });
  return files;
}

/** Every URL fetched so far, in order. */
const fetched = () => fetchMock.mock.calls.map((call) => String(call[0]));

beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  serveMatrix(MATRIX);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

/** Render, then wait until every column the grid opens with has merged. */
async function renderMatrix() {
  const utils = render(<YearsMatrix />);
  await waitFor(() => {
    expect(screen.getByTestId("years-matrix").getAttribute("aria-busy")).toBe("false");
  });
  return utils;
}
```

**Edit T14.4** — default sort key mock — `site/src/__tests__/years-matrix.test.tsx`. Replace this exact text:

```tsx
  it("the default sort key is the payload's, not a hardcoded column", async () => {
    fetchMock.mockImplementation((url: string) =>
      String(url) === "/json/years_matrix.json"
        ? Promise.resolve(jsonResponse(MATRIX_DECADE))
        : Promise.reject(new Error(`unmocked fetch ${url}`)),
    );
    await renderMatrix();
```

with:

```tsx
  it("the default sort key is the payload's, not a hardcoded column", async () => {
    serveMatrix(MATRIX_DECADE);
    await renderMatrix();
```

**Edit T14.5** — decade view mock — `site/src/__tests__/years-matrix.test.tsx`. Replace this exact text:

```tsx
describe("YearsMatrix — decade view (Phase 5E)", () => {
  beforeEach(() => {
    fetchMock.mockImplementation((url: string) => {
      if (String(url) === "/json/years_matrix.json") {
        return Promise.resolve(jsonResponse(MATRIX_DECADE));
      }
      return Promise.reject(new Error(`unmocked fetch ${url}`));
    });
  });
```

with:

```tsx
describe("YearsMatrix — decade view (Phase 5E)", () => {
  beforeEach(() => {
    serveMatrix(MATRIX_DECADE);
  });
```

**Edit T14.6** — tooltip and legend (Q12, Q14) — `site/src/__tests__/years-matrix.test.tsx`. Replace this exact text:

```tsx
  // Families piece 1 final review T4. /years/ keeps procurement rows from
  // PB2024 on (the ROADMAP #193 fence) while their program pages now carry
  // the PB2017–PB2023 era history, so a P-1 row's earlier gap must not claim
  // the line was missing from that edition. R-1 rows (PE-shaped codes) and
  // every PB2024+ gap keep "Not in the PB… edition".
  it("a procurement row's pre-PB2024 gap points at the program page, not at the edition", async () => {
    const withP1: YearsMatrixData = {
      ...MATRIX_DECADE,
      orgs: [
        ...MATRIX_DECADE.orgs,
        {
          org: "N",
          programs: [
            {
              pe_bli: "2013",
              title: "Virginia Class Submarine",
              // fence: no cell before PB2024; fy2025e (PB2026) is a plain gap
              cells: { fy2026r: { fid: "dd00000000000008", v: 10000000 } },
              projects: [],
            },
          ],
        },
      ],
    };
    fetchMock.mockImplementation((url: string) =>
      String(url) === "/json/years_matrix.json"
        ? Promise.resolve(jsonResponse(withP1))
        : Promise.reject(new Error(`unmocked fetch ${url}`)),
    );
    await renderMatrix();
    const title = (pe: string, col: string) =>
      (document.querySelector(`tr[data-pe="${pe}"] td[data-col="${col}"]`) as HTMLElement)
        .getAttribute("title");
    expect(title("2013", "fy2015a")).toBe(
      "Any PB2017 procurement history is on the program page, not yet in this grid",
    );
    expect(title("2013", "fy2020a")).toBe(
      "Any PB2022 procurement history is on the program page, not yet in this grid",
    );
    expect(title("2013", "fy2025e")).toBe("Not in the PB2026 edition");
    // the R-1 rows beside it are unchanged
    expect(title("0602702E", "fy2015a")).toBe("Not in the PB2017 edition");
    expect(title("0603882C", "fy2020a")).toBe("Not in the PB2022 edition");
  });

  it("the edition legend says where procurement history before PB2024 lives", async () => {
    await renderMatrix();
    const legend = document.querySelector('[data-testid="edition-legend"]') as HTMLElement;
    expect(legend.textContent).toContain(
      "Procurement rows here start at PB2024; any PB2017–PB2023 history is on the program page.",
    );
  });
```

with:

```tsx
  // ROADMAP #193 lifted piece 1's /years/ fence: a procurement row carries
  // exactly its program page's decade points, era editions included, so every
  // gap is a true absence from that edition's book (Q12) — final review T4's
  // "on the program page, not yet in this grid" tooltip is retired with it.
  it("every decade gap reads 'Not in the PB… edition', procurement rows included", async () => {
    const withP1: YearsMatrixData = {
      ...MATRIX_DECADE,
      orgs: [
        ...MATRIX_DECADE.orgs,
        {
          org: "N",
          programs: [
            {
              pe_bli: "2013",
              title: "Virginia Class Submarine",
              // an era point (PB2017, joined by a reviewed decision) and a
              // PB2026 one; fy2020a and fy2025e are gaps
              cells: {
                fy2015a: { fid: "dd00000000000009", v: 5000000 },
                fy2026r: { fid: "dd00000000000008", v: 10000000 },
              },
              projects: [],
            },
          ],
        },
      ],
    };
    serveMatrix(withP1);
    await renderMatrix();
    const td = (pe: string, col: string) =>
      document.querySelector(`tr[data-pe="${pe}"] td[data-col="${col}"]`) as HTMLElement;
    expect(td("2013", "fy2015a").getAttribute("data-v")).toBe("5000000");
    expect(td("2013", "fy2020a").getAttribute("title")).toBe("Not in the PB2022 edition");
    expect(td("2013", "fy2025e").getAttribute("title")).toBe("Not in the PB2026 edition");
    expect(td("0602702E", "fy2015a").getAttribute("title")).toBe("Not in the PB2017 edition");
    expect(document.body.textContent).not.toContain("not yet in this grid");
  });

  it("the edition legend says what a procurement row shows before PB2024", async () => {
    await renderMatrix();
    const legend = document.querySelector('[data-testid="edition-legend"]') as HTMLElement;
    expect(legend.textContent).toContain(
      "Before PB2024, a procurement row shows only lines a reviewed decision joined to it.",
    );
    expect(legend.textContent).not.toContain("start at PB2024");
  });
```

**Edit T14.7** — picker groups waits for detail — `site/src/__tests__/years-matrix.test.tsx`. Replace this exact text:

```tsx
    // The PB2026-detail chips still work
    fireEvent.click(
      screen.getByRole("button", { name: /show fy2025 total column/i }),
    );
    expect(document.querySelector('th[data-col="fy_2025_total"]')).not.toBeNull();
  });
```

with:

```tsx
    // The PB2026-detail chips still work (the column joins once detail.json
    // has merged)
    fireEvent.click(
      screen.getByRole("button", { name: /show fy2025 total column/i }),
    );
    await waitFor(() => {
      expect(document.querySelector('th[data-col="fy_2025_total"]')).not.toBeNull();
    });
  });
```

**Edit T14.8** — project sub-rows wait — `site/src/__tests__/years-matrix.test.tsx`. Replace this exact text:

```tsx
  it("project sub-rows map PB2026-edition decade columns to project cells", async () => {
    await renderMatrix();
    fireEvent.click(document.querySelector("[data-expand]") as HTMLElement);
    // fy2026r (edition 2026) maps to the project fy2026 scenario cell — but
    // the fixture project has no fy2026 cell, so check fy2024a → fy2024.
    // First bring fy2024a into view via the picker.
    fireEvent.click(
      screen.getByRole("button", { name: /show fy2024a column/i }),
    );
    const projCell = document.querySelector(
      'tr[data-project-row] td[data-col="fy2024"]',
    );
    expect(projCell).not.toBeNull();
```

with:

```tsx
  it("project sub-rows map PB2026-edition decade columns to project cells", async () => {
    await renderMatrix();
    fireEvent.click(document.querySelector("[data-expand]") as HTMLElement);
    // fy2026r (edition 2026) maps to the project fy2026 scenario cell — but
    // the fixture project has no fy2026 cell, so check fy2024a → fy2024.
    // First bring fy2024a into view via the picker. The projects arrive with
    // detail.json and fy2024a with decade.json (ROADMAP #193).
    fireEvent.click(
      screen.getByRole("button", { name: /show fy2024a column/i }),
    );
    await waitFor(() => {
      expect(
        document.querySelector('tr[data-project-row] td[data-col="fy2024"]'),
      ).not.toBeNull();
    });
    const projCell = document.querySelector(
      'tr[data-project-row] td[data-col="fy2024"]',
    );
```

**Edit T14.9** — family mock — `site/src/__tests__/years-matrix.test.tsx`. Replace this exact text:

```tsx
describe("YearsMatrix — family-thread affordance (program-lineage)", () => {
  beforeEach(() => {
    fetchMock.mockImplementation((url: string) => {
      if (String(url) === "/json/years_matrix.json") {
        return Promise.resolve(jsonResponse(MATRIX_FAMILY));
      }
      return Promise.reject(new Error(`unmocked fetch ${url}`));
    });
  });
```

with:

```tsx
describe("YearsMatrix — family-thread affordance (program-lineage)", () => {
  beforeEach(() => {
    serveMatrix(MATRIX_FAMILY);
  });
```

**Edit T14.10** — lazy shard tests — `site/src/__tests__/years-matrix.test.tsx`. Replace this exact text:

```tsx
describe("§P2-7 — 0 vs <0.05 vs — are three different facts", () => {
```

with:

```tsx
// ── ROADMAP #193 — the core first, each shard when a reader asks ──────────

describe("YearsMatrix — lazy shards (ROADMAP #193)", () => {
  beforeEach(() => {
    serveMatrix(MATRIX_DECADE);
  });

  it("opens on the core alone: no shard is fetched until a reader asks", async () => {
    await renderMatrix();
    expect(fetched()).toEqual([CORE_URL]);
    expect(screen.getByTestId("years-matrix").getAttribute("data-shards")).toBe("core");
    // the expand caret is there before detail.json: np comes with the core
    expect(
      document.querySelector('tr[data-pe="0601101E"] [data-expand]'),
    ).not.toBeNull();
  });

  it("a non-default decade column loads decade.json once, then joins the grid", async () => {
    const files = splitForTest(MATRIX_DECADE);
    let release: () => void = () => {};
    serveMatrix(MATRIX_DECADE, {
      [DECADE_URL]: () =>
        new Promise((resolve) => {
          release = () => resolve(files.decade);
        }),
    });
    await renderMatrix();
    fireEvent.click(screen.getByRole("button", { name: /show fy2020e column/i }));
    // asked for, not merged: the chip says so, the table is busy, and the
    // column is not drawn as a column of "—" (which means "not in the book")
    const chip = screen.getByRole("button", { name: /hide fy2020e column/i });
    expect(chip.getAttribute("data-shard-state")).toBe("loading");
    expect(screen.getByTestId("years-matrix").getAttribute("aria-busy")).toBe("true");
    expect(document.querySelector('th[data-col="fy2020e"]')).toBeNull();
    release();
    await waitFor(() => {
      expect(document.querySelector('th[data-col="fy2020e"]')).not.toBeNull();
    });
    expect(chip.hasAttribute("data-shard-state")).toBe(false);
    expect(screen.getByTestId("years-matrix").getAttribute("data-shards")).toBe("core decade");
    expect(
      document
        .querySelector('tr[data-pe="0601101E"] td[data-col="fy2020e"]')
        ?.getAttribute("data-v"),
    ).toBe("94000");
    // another column from the same shard needs no second fetch
    fireEvent.click(screen.getByRole("button", { name: /show fy2024a column/i }));
    expect(document.querySelector('th[data-col="fy2024a"]')).not.toBeNull();
    expect(fetched().filter((u) => u === DECADE_URL)).toHaveLength(1);
  });

  it("expanding a row loads detail.json, then shows its project rows", async () => {
    await renderMatrix();
    fireEvent.click(
      document.querySelector('tr[data-pe="0601101E"] [data-expand]') as HTMLElement,
    );
    await waitFor(() => {
      expect(document.querySelectorAll("tr[data-project-row]").length).toBeGreaterThan(0);
    });
    expect(fetched()).toEqual([CORE_URL, DETAIL_URL]);
    expect(screen.getByTestId("years-matrix").getAttribute("data-shards")).toBe("core detail");
  });

  it("a shard from another build refetches the core once; still stale, its columns show an error", async () => {
    const files = splitForTest(MATRIX_DECADE);
    serveMatrix(MATRIX_DECADE, {
      [DECADE_URL]: { ...files.decade, build_id: "build-0" },
    });
    await renderMatrix();
    fireEvent.click(screen.getByRole("button", { name: /show fy2020e column/i }));
    const chip = screen.getByRole("button", { name: /hide fy2020e column/i });
    await waitFor(() => {
      expect(chip.getAttribute("data-shard-state")).toBe("error");
    });
    expect(chip.textContent).toContain("(unavailable)");
    expect(document.querySelector('th[data-col="fy2020e"]')).toBeNull();
    expect(fetched()).toEqual([CORE_URL, DECADE_URL, CORE_URL]);
    expect(fetchMock.mock.calls[2][1]).toEqual({ cache: "no-cache" });
    // nothing else changes: the opening columns stay, the table is not busy
    expect(document.querySelector('th[data-col="fy2020a"]')).not.toBeNull();
    expect(screen.getByTestId("years-matrix").getAttribute("aria-busy")).toBe("false");
  });

  it("a redeploy between the two fetches moves the grid to the new build", async () => {
    const v2: YearsMatrixData = {
      ...MATRIX_DECADE,
      orgs: MATRIX_DECADE.orgs.map((o, i) =>
        i !== 0
          ? o
          : {
              ...o,
              programs: o.programs.map((p, j) =>
                j !== 0
                  ? p
                  : { ...p, cells: { ...p.cells, fy2020a: { fid: "dd00000000000002", v: 96000 } } },
              ),
            },
      ),
    };
    const before = splitForTest(MATRIX_DECADE, "build-1");
    const after = splitForTest(v2, "build-2");
    let coreRequests = 0;
    serveMatrix(MATRIX_DECADE, {
      [CORE_URL]: () => (coreRequests++ === 0 ? before.core : after.core),
      [DECADE_URL]: after.decade,
    });
    await renderMatrix();
    fireEvent.click(screen.getByRole("button", { name: /show fy2020e column/i }));
    await waitFor(() => {
      expect(document.querySelector('th[data-col="fy2020e"]')).not.toBeNull();
    });
    expect(
      document
        .querySelector('tr[data-pe="0601101E"] td[data-col="fy2020a"]')
        ?.getAttribute("data-v"),
    ).toBe("96000");
    expect(fetched()).toEqual([CORE_URL, DECADE_URL, CORE_URL]);
  });

  it("an export from before the split (schema 1, one file) still renders whole", async () => {
    fetchMock.mockImplementation((url: string) =>
      String(url) === CORE_URL
        ? Promise.resolve(jsonResponse(MATRIX_DECADE))
        : Promise.reject(new Error(`unmocked fetch ${url}`)),
    );
    await renderMatrix();
    fireEvent.click(screen.getByRole("button", { name: /show fy2020e column/i }));
    expect(document.querySelector('th[data-col="fy2020e"]')).not.toBeNull();
    fireEvent.click(
      document.querySelector('tr[data-pe="0601101E"] [data-expand]') as HTMLElement,
    );
    expect(document.querySelectorAll("tr[data-project-row]").length).toBeGreaterThan(0);
    expect(fetched()).toEqual([CORE_URL]);
    expect(screen.getByTestId("years-matrix").getAttribute("aria-busy")).toBe("false");
  });
});

describe("§P2-7 — 0 vs <0.05 vs — are three different facts", () => {
```

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site && npx vitest run src/__tests__/years-matrix.test.tsx
```

Expected: `Tests  37 failed | 23 passed (60)` (measured on the scratch copy).
The 23 pure-helper tests pass. Of the 37 that render the island, 36 are
served a split core whose rows carry `np` and no `projects`, and the island
crashes on `program.projects.length` (`TypeError: Cannot read properties of
undefined (reading 'length')`, then `Unable to find an element by:
[data-testid="years-matrix"]`); the pre-split test renders but waits in vain
for `aria-busy` (`AssertionError: expected null to be 'false'`).

- [ ] **Step 4: Rebuild the island on the core and its shards**

**Edit 14.1** — header — `site/src/components/years-matrix.tsx` (anchor on the quoted text). Replace this exact text:

```tsx
 * Client island: lazily fetches /json/years_matrix.json (exporter sidecar,
 * copied to public/json/ by prepare-assets) and renders every program element
 * as a row, fiscal-year amount types as columns:
```

with:

```tsx
 * Client island: fetches /json/years_matrix.json (the core: the header,
 * every row and the default decade columns' cells) on mount, and each lazy
 * shard (/json/years_matrix/decade.json, /json/years_matrix/detail.json)
 * only when a reader turns on a column it holds or, for detail, expands a
 * row (ROADMAP #193; prepare-assets copies all three to public/json/). It
 * renders every program element as a row, fiscal-year amount types as
 * columns:
```

**Edit 14.2** — DOM contract — `site/src/components/years-matrix.tsx` (anchor on the quoted text). Replace this exact text:

```tsx
 *   [data-testid="years-csv"], [data-sticky-col].
 */
```

with:

```tsx
 *   [data-testid="years-csv"], [data-sticky-col],
 *   table[data-shards="core[ decade][ detail]"] (the files merged so far)
 *   with aria-busy="true" while a column the reader asked for is loading.
 */
```

**Edit 14.3** — imports — `site/src/components/years-matrix.tsx` (anchor on the quoted text). Replace this exact text:

```tsx
import { EXTENDED_MEASURE_LABEL } from "@/lib/basis";
import { isPeCode } from "@/lib/pe-link";

// ── Sidecar types (years_matrix.json schema_version 1) ──────────────────────
```

with:

```tsx
import { EXTENDED_MEASURE_LABEL } from "@/lib/basis";
import {
  mergeYearsMatrix,
  shardOfColumns,
  YEARS_SHARD_NAMES,
  type YearsMatrixCore,
  type YearsMatrixShard,
  type YearsShardManifestEntry,
  type YearsShardName,
} from "@/lib/years-matrix-shards.mjs";

// ── Sidecar types: the merged view of years_matrix.json (schema_version 2)
//    and whichever of its shards have loaded (years-matrix-shards.mjs) ──────
```

**Edit 14.4** — program np — `site/src/components/years-matrix.tsx` (anchor on the quoted text). Replace this exact text:

```tsx
  /** Keyed by amount_type + delta columns. */
  cells: Record<string, YearsCell | undefined>;
  projects: YearsProject[];
```

with:

```tsx
  /** Keyed by amount_type + delta columns. */
  cells: Record<string, YearsCell | undefined>;
  /** [] until detail.json has loaded (ROADMAP #193). */
  projects: YearsProject[];
  /** The row's project count, from the core: the expand caret reads it so it
   *  can render before detail.json (which holds the projects) has loaded. */
  np?: number;
```

**Edit 14.5** — matrix data — `site/src/components/years-matrix.tsx` (anchor on the quoted text). Replace this exact text:

```tsx
  /** Phase 5E: present only when the exporter minted decade grains. */
  decade_columns?: DecadeColumn[];
  decade_default_columns?: string[];
  orgs: YearsOrg[];
}
```

with:

```tsx
  /** Phase 5E: present only when the exporter minted decade grains. */
  decade_columns?: DecadeColumn[];
  decade_default_columns?: string[];
  /** ROADMAP #193: the export's content hash, shared by the core and shards. */
  build_id?: string;
  /** ROADMAP #193: the core's manifest of its two lazy shards. */
  shards?: YearsShardManifestEntry[];
  orgs: YearsOrg[];
}
```

**Edit 14.6** — defaultSortKey signature — `site/src/components/years-matrix.tsx` (anchor on the quoted text). Replace this exact text:

```tsx
export function defaultSortKey(matrix: YearsMatrixData): string | null {
```

with:

```tsx
export function defaultSortKey(
  matrix: Pick<YearsMatrixData, "decade_default_columns" | "default_columns" | "delta_columns">,
): string | null {
```

**Edit 14.7** — load state and shard helpers — `site/src/components/years-matrix.tsx` (anchor on the quoted text). Replace this exact text:

```tsx
type LoadState =
  | { s: "loading" }
  | { s: "error" }
  | { s: "ready"; matrix: YearsMatrixData };
```

with:

```tsx
type LoadState =
  | { s: "loading" }
  | { s: "error" }
  | { s: "ready"; core: YearsMatrixCore };

/** One lazy shard: never asked for, in flight, merged, or failed. */
type ShardStatus = "idle" | "loading" | "ready" | "error";
const NO_SHARDS: Record<YearsShardName, ShardStatus> = {
  decade: "idle",
  detail: "idle",
};

/**
 * The shards' paths under /json/, which the core's manifest must name. The
 * fetches below are string literals on purpose: linkgraph leg i reads every
 * statically named fetch() target out of site/src and asserts the file
 * ships under out/, and a computed `/json/${path}` would hide both from it.
 */
const SHARD_PATH: Record<YearsShardName, string> = {
  decade: "years_matrix/decade.json",
  detail: "years_matrix/detail.json",
};

function fetchShard(name: YearsShardName): Promise<Response> {
  return name === "decade"
    ? fetch("/json/years_matrix/decade.json")
    : fetch("/json/years_matrix/detail.json");
}

async function jsonOf<T>(response: Promise<Response>, what: string): Promise<T> {
  const res = await response;
  if (!res.ok) throw new Error(`${what} HTTP ${res.status}`);
  return (await res.json()) as T;
}

/**
 * Fetch one shard for `core`. Its build_id must be the core's. If a deploy
 * landed between the two fetches, the core is fetched again, once, past the
 * HTTP cache: a fresh core that matches the shard is returned with it (the
 * grid moves to that build); anything else throws, and the shard's columns
 * show an error and nothing else.
 */
async function fetchShardFor(
  core: YearsMatrixCore,
  name: YearsShardName,
): Promise<{ core: YearsMatrixCore; shard: YearsMatrixShard }> {
  const entry = core.shards?.find((s) => s.name === name);
  if (!entry || entry.path !== SHARD_PATH[name]) {
    throw new Error(`the core's manifest does not list ${SHARD_PATH[name]}`);
  }
  const shard = await jsonOf<YearsMatrixShard>(fetchShard(name), SHARD_PATH[name]);
  if (shard.build_id === core.build_id) return { core, shard };
  const fresh = await jsonOf<YearsMatrixCore>(
    fetch("/json/years_matrix.json", { cache: "no-cache" }),
    "years_matrix.json",
  );
  if (fresh.build_id !== shard.build_id) {
    throw new Error(`${SHARD_PATH[name]} is from another build`);
  }
  return { core: fresh, shard };
}

/** The island's shard bookkeeping: which shards have been asked for under
 *  the current core, and the state setters that report on them. */
interface ShardLoader {
  requested: Set<YearsShardName>;
  setLoad: (state: LoadState) => void;
  setShards: React.Dispatch<
    React.SetStateAction<Partial<Record<YearsShardName, YearsMatrixShard>>>
  >;
  setShardStatus: React.Dispatch<
    React.SetStateAction<Record<YearsShardName, ShardStatus>>
  >;
}

/**
 * Ask for shards, each at most once per core. Called only from the core's
 * load callback and from event handlers (a column chip, an expand caret),
 * never from an effect: a shard loads because a reader asked for what it
 * holds. When a shard comes back with a newer core, the grid moves to that
 * build, and every other shard asked for so far is fetched again for it.
 */
function requestShards(
  loader: ShardLoader,
  current: YearsMatrixCore,
  names: Iterable<YearsShardName>,
): void {
  for (const name of names) {
    // A pre-split export (schema 1) lists no shards: nothing to fetch.
    if (!current.shards?.some((s) => s.name === name)) continue;
    if (loader.requested.has(name)) continue;
    loader.requested.add(name);
    loader.setShardStatus((prev) => ({ ...prev, [name]: "loading" }));
    fetchShardFor(current, name)
      .then(({ core, shard }) => {
        if (core === current) {
          loader.setShards((prev) => ({ ...prev, [name]: shard }));
          loader.setShardStatus((prev) => ({ ...prev, [name]: "ready" }));
          return;
        }
        const again = [...loader.requested].filter((n) => n !== name);
        loader.requested.clear();
        loader.requested.add(name);
        loader.setLoad({ s: "ready", core });
        loader.setShards({ [name]: shard });
        loader.setShardStatus({ ...NO_SHARDS, [name]: "ready" });
        requestShards(loader, core, again);
      })
      .catch(() => {
        loader.setShardStatus((prev) => ({ ...prev, [name]: "error" }));
      });
  }
}

/** The shards holding any of `columns` under `core`'s manifest. */
function shardsHolding(core: YearsMatrixCore, columns: string[]): Set<YearsShardName> {
  const of = shardOfColumns(core);
  const out = new Set<YearsShardName>();
  for (const c of columns) {
    const s = of.get(c);
    if (s) out.add(s);
  }
  return out;
}
```

**Edit 14.8** — component state — `site/src/components/years-matrix.tsx` (anchor on the quoted text). Replace this exact text:

```tsx
export function YearsMatrix() {
  const [load, setLoad] = useState<LoadState>({ s: "loading" });
```

with:

```tsx
export function YearsMatrix() {
  const [load, setLoad] = useState<LoadState>({ s: "loading" });
  // ROADMAP #193: the lazy shards merged so far, and where each one is.
  const [shards, setShards] = useState<
    Partial<Record<YearsShardName, YearsMatrixShard>>
  >({});
  const [shardStatus, setShardStatus] =
    useState<Record<YearsShardName, ShardStatus>>(NO_SHARDS);
  const [loader] = useState<ShardLoader>(() => ({
    requested: new Set(),
    setLoad,
    setShards,
    setShardStatus,
  }));
```

**Edit 14.9** — scroll effect deps — `site/src/components/years-matrix.tsx` (anchor on the quoted text). Replace this exact text:

```tsx
    if (snapped === null) snapped = th.offsetLeft - stickyW;
    const maxScroll = box.scrollWidth - box.clientWidth;
    box.scrollLeft = Math.max(0, Math.min(snapped, maxScroll));
    setScrollToCol(null);
  }, [scrollToCol, load]);
```

with:

```tsx
    if (snapped === null) snapped = th.offsetLeft - stickyW;
    const maxScroll = box.scrollWidth - box.clientWidth;
    box.scrollLeft = Math.max(0, Math.min(snapped, maxScroll));
    setScrollToCol(null);
    // shardStatus: a sort column held by a shard only gets its <th> once the
    // shard has merged, so the scroll waits for it.
  }, [scrollToCol, load, shardStatus]);
```

**Edit 14.10** — core fetch and merged view — `site/src/components/years-matrix.tsx` (anchor on the quoted text). Replace this exact text:

```tsx
  useEffect(() => {
    let cancelled = false;
    fetch("/json/years_matrix.json")
      .then((res) => {
        if (!res.ok) throw new Error(`years_matrix.json HTTP ${res.status}`);
        return res.json() as Promise<YearsMatrixData>;
      })
      .then((matrix) => {
        if (cancelled) return;
        setLoad({ s: "ready", matrix });
        // §P2-2: open on substance, not on a screenful of em-dashes.
        const key = defaultSortKey(matrix);
        if (key) {
          setSort({ key, dir: "desc" });
          setScrollToCol(key);
        }
      })
      .catch(() => {
        if (!cancelled) setLoad({ s: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const matrix = load.s === "ready" ? load.matrix : null;
```

with:

```tsx
  useEffect(() => {
    let cancelled = false;
    jsonOf<YearsMatrixCore>(fetch("/json/years_matrix.json"), "years_matrix.json")
      .then((core) => {
        if (cancelled) return;
        setLoad({ s: "ready", core });
        // §P2-2: open on substance, not on a screenful of em-dashes.
        const key = defaultSortKey(core);
        if (key) {
          setSort({ key, dir: "desc" });
          setScrollToCol(key);
        }
        // The opening view's shards: none when the defaults are decade
        // columns, which the core holds (ROADMAP #193).
        const opening = core.decade_default_columns?.length
          ? core.decade_default_columns
          : core.default_columns;
        requestShards(loader, core, shardsHolding(core, opening));
      })
      .catch(() => {
        if (!cancelled) setLoad({ s: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, [loader]);

  const core = load.s === "ready" ? load.core : null;
  // column key → the shard holding it; a key in no shard is in the core.
  const shardOf = useMemo(
    () => (core ? shardOfColumns(core) : new Map<string, YearsShardName>()),
    [core],
  );
  // The grid's data: the core plus every shard merged so far. A shard is
  // stored only once its build_id matches the core's (loadShard).
  const matrix = useMemo(
    () =>
      core
        ? mergeYearsMatrix(
            core,
            YEARS_SHARD_NAMES.flatMap((n) => (shards[n] ? [shards[n]!] : [])),
          )
        : null,
    [core, shards],
  );
```

**Edit 14.11** — wanted vs visible columns — `site/src/components/years-matrix.tsx` (anchor on the quoted text). Replace this exact text:

```tsx
  const visibleCols = useMemo(() => {
    if (!matrix) return [];
    const chosen = new Set(chosenCols ?? defaultCols);
    return allColumns.filter((c) => chosen.has(c));
  }, [matrix, chosenCols, allColumns, defaultCols]);
```

with:

```tsx
  // The columns the reader asked for…
  const wantedCols = useMemo(() => {
    if (!matrix) return [];
    const chosen = new Set(chosenCols ?? defaultCols);
    return allColumns.filter((c) => chosen.has(c));
  }, [matrix, chosenCols, allColumns, defaultCols]);
  // …and the ones on screen: a column joins the grid only once its shard has
  // merged. Until then a "—" in it would claim the book has no figure.
  const visibleCols = useMemo(
    () =>
      wantedCols.filter((c) => {
        const s = shardOf.get(c);
        return s === undefined || shardStatus[s] === "ready";
      }),
    [wantedCols, shardOf, shardStatus],
  );
  // A shard is wanted when a chosen column lives in it, or (detail) when a
  // row is expanded: the project sub-rows ship in detail.json. The chip and
  // caret handlers ask for it (requestShards); this only drives aria-busy.
  const wantedShards = useMemo(() => {
    const out = new Set<YearsShardName>();
    for (const c of wantedCols) {
      const s = shardOf.get(c);
      if (s) out.add(s);
    }
    const listsDetail = (core?.shards ?? []).some((s) => s.name === "detail");
    if (expandedPrograms.size > 0 && listsDetail) out.add("detail");
    return out;
  }, [core, wantedCols, shardOf, expandedPrograms]);

  // aria-busy: some column the reader asked for has not merged yet.
  const busy = [...wantedShards].some(
    (s) => shardStatus[s] === "idle" || shardStatus[s] === "loading",
  );
  // The gates' marker: which files the grid is showing, in a fixed order.
  const loadedFiles = [
    "core",
    ...YEARS_SHARD_NAMES.filter((s) => shardStatus[s] === "ready"),
  ].join(" ");

  /** A picker chip's loading state: "loading" or "error" while the reader
   *  has it on and its shard has not merged; undefined otherwise. */
  function chipShardState(key: string): "loading" | "error" | undefined {
    const s = shardOf.get(key);
    if (s === undefined || !wantedCols.includes(key)) return undefined;
    if (shardStatus[s] === "error") return "error";
    return shardStatus[s] === "ready" ? undefined : "loading";
  }
```

**Edit 14.12** — decade chip — `site/src/components/years-matrix.tsx` (anchor on the quoted text). Replace this exact text:

```tsx
        {decadeKeys.map((key) => {
          const col = decadeMeta.get(key)!;
          const on = visibleCols.includes(key);
          const label = decadeColumnLabel(col);
          return (
            <button
              key={key}
              type="button"
              aria-pressed={on}
              aria-label={`${on ? "Hide" : "Show"} ${label} column`}
              title={decadeColumnTitle(col)}
              onClick={() => toggleColumn(key)}
              className={`rounded-full border px-2 py-0.5 text-xs transition-colors ${
                on
                  ? "border-primary bg-primary font-semibold text-primary-foreground"
                  : "border-border font-medium text-muted-foreground hover:text-foreground"
              }`}
            >
              {label}
            </button>
          );
        })}
```

with:

```tsx
        {decadeKeys.map((key) => {
          const col = decadeMeta.get(key)!;
          const on = wantedCols.includes(key);
          const label = decadeColumnLabel(col);
          const pending = chipShardState(key);
          return (
            <button
              key={key}
              type="button"
              aria-pressed={on}
              aria-label={`${on ? "Hide" : "Show"} ${label} column`}
              aria-busy={pending === "loading" || undefined}
              data-shard-state={pending}
              title={
                pending === "error"
                  ? `${decadeColumnTitle(col)}: could not be loaded; reload the page to try again`
                  : decadeColumnTitle(col)
              }
              onClick={() => toggleColumn(key)}
              className={`rounded-full border px-2 py-0.5 text-xs transition-colors ${
                on
                  ? "border-primary bg-primary font-semibold text-primary-foreground"
                  : "border-border font-medium text-muted-foreground hover:text-foreground"
              }`}
            >
              {label}
              {pending === "loading" && <span aria-hidden="true"> …</span>}
              {pending === "error" && <span> (unavailable)</span>}
            </button>
          );
        })}
```

**Edit 14.13** — detail chip — `site/src/components/years-matrix.tsx` (anchor on the quoted text). Replace this exact text:

```tsx
          (key) => {
            const on = visibleCols.includes(key);
            return (
              <button
                key={key}
                type="button"
                aria-pressed={on}
                aria-label={`${on ? "Hide" : "Show"} ${columnLabel(key)} column`}
                onClick={() => toggleColumn(key)}
```

with:

```tsx
          (key) => {
            const on = wantedCols.includes(key);
            const pending = chipShardState(key);
            return (
              <button
                key={key}
                type="button"
                aria-pressed={on}
                aria-label={`${on ? "Hide" : "Show"} ${columnLabel(key)} column`}
                aria-busy={pending === "loading" || undefined}
                data-shard-state={pending}
                title={
                  pending === "error"
                    ? `${columnLabel(key)}: could not be loaded; reload the page to try again`
                    : undefined
                }
                onClick={() => toggleColumn(key)}
```

**Edit 14.14** — detail chip label — `site/src/components/years-matrix.tsx` (anchor on the quoted text). Replace this exact text:

```tsx
                {columnLabel(key)}
              </button>
            );
          },
        )}
```

with:

```tsx
                {columnLabel(key)}
                {pending === "loading" && <span aria-hidden="true"> …</span>}
                {pending === "error" && <span> (unavailable)</span>}
              </button>
            );
          },
        )}
```

**Edit 14.15** — legend (Q14) — `site/src/components/years-matrix.tsx` (anchor on the quoted text). Replace this exact text:

```tsx
          Actuals for FY N come from the PB(N+2) book; each column states its
          edition. Procurement rows here start at PB2024; any PB2017–PB2023
          history is on the program page.{" "}
```

with:

```tsx
          Actuals for FY N come from the PB(N+2) book; each column states its
          edition. Before PB2024, a procurement row shows only lines a
          reviewed decision joined to it.{" "}
```

**Edit 14.16** — table markers — `site/src/components/years-matrix.tsx` (anchor on the quoted text). Replace this exact text:

```tsx
          data-sorted-col={sort?.key ?? ""}
```

with:

```tsx
          data-sorted-col={sort?.key ?? ""}
          // ROADMAP #193: the files merged so far ("core", "core decade", …)
          // and whether a column the reader asked for is still loading. The
          // yearsmatrix gate waits on these instead of on timeouts.
          data-shards={loadedFiles}
          aria-busy={busy}
```

**Edit 14.17** — caret reads np — `site/src/components/years-matrix.tsx` (anchor on the quoted text). Replace this exact text:

```tsx
  const { org, program } = entry;
  const hasProjects = program.projects.length > 0;
```

with:

```tsx
  const { org, program } = entry;
  // np comes with the core; the projects themselves arrive with detail.json.
  const hasProjects = (program.np ?? program.projects.length) > 0;
```

**Edit 14.18** — cell call site — `site/src/components/years-matrix.tsx` (anchor on the quoted text). Replace this exact text:

```tsx
            decade={decadeMeta.get(key)}
            peBli={program.pe_bli}
          />
```

with:

```tsx
            decade={decadeMeta.get(key)}
          />
```

**Edit 14.19** — fence constant removed — `site/src/components/years-matrix.tsx` (anchor on the quoted text). Replace this exact text:

```tsx
/** The first edition /years/ carries procurement (P-1) rows in: the
 *  families piece 1 fence (spec 2026-10-02 §6.2, ROADMAP #193). */
const PROCUREMENT_GRID_FIRST_EDITION = 2024;

```

with nothing (delete it, including the blank line that follows it).

**Edit 14.20** — cell tooltip (Q12) — `site/src/components/years-matrix.tsx` (anchor on the quoted text). Replace this exact text:

```tsx
function ProgramCellTd({
  colKey,
  cell,
  decade,
  peBli,
}: {
  colKey: string;
  cell: YearsCell | undefined;
  /** Phase 5E: set when colKey is a decade column ('fy{yyyy}{a|e|r}'). */
  decade?: DecadeColumn;
  /** The row's code: a PE-shaped one is an R-1 row, any other a P-1 row. */
  peBli: string;
}) {
  if (!cell) {
    // Decade gaps are edition-honest absences (spec §2 rule 4): the PE has
    // no entry in that column's book — the tooltip says which edition.
    // Except a procurement row before PB2024 (families piece 1 final review
    // T4): /years/ keeps P-1 rows from PB2024 on (the ROADMAP #193 fence)
    // while the program page carries the era history a reviewed decision
    // matched, so that gap is this grid's, not the edition's. "Any": not
    // every P-1 row has era history (S5: 4,995 of the 6,027 default-view
    // pre-PB2024 P-1 gaps have a point on the program page).
    const procurementBeforeGrid =
      decade !== undefined &&
      decade.edition < PROCUREMENT_GRID_FIRST_EDITION &&
      !isPeCode(peBli);
    return (
      <td
        data-col={colKey}
        data-cell-state="absent"
        title={
          decade
            ? procurementBeforeGrid
              ? `Any PB${decade.edition} procurement history is on the program page, not yet in this grid`
              : `Not in the PB${decade.edition} edition`
            : "No figure for this program in this column's source"
        }
```

with:

```tsx
function ProgramCellTd({
  colKey,
  cell,
  decade,
}: {
  colKey: string;
  cell: YearsCell | undefined;
  /** Phase 5E: set when colKey is a decade column ('fy{yyyy}{a|e|r}'). */
  decade?: DecadeColumn;
}) {
  if (!cell) {
    // Decade gaps are edition-honest absences (spec §2 rule 4): the row has
    // no entry in that column's book, and the tooltip says which edition.
    // Procurement rows included since ROADMAP #193 lifted piece 1's fence:
    // a /years/ row carries exactly its program page's decade points, so a
    // P-1 gap before PB2024 is a code that edition did not print, a line
    // joined to the sibling account's row, or a reused code an owner
    // decision excluded (Q12, measured on the default view: 985, 41 and 6
    // of 1,032), never a point the grid left out.
    return (
      <td
        data-col={colKey}
        data-cell-state="absent"
        title={
          decade
            ? `Not in the PB${decade.edition} edition`
            : "No figure for this program in this column's source"
        }
```

**Edit 14.21** — expanding a row asks for detail.json — `site/src/components/years-matrix.tsx` (anchor on the quoted text). Replace this exact text:

```tsx
  function toggleProgram(peBli: string) {
    setExpandedPrograms((prev) => {
```

with:

```tsx
  function toggleProgram(peBli: string) {
    // Project sub-rows ship in detail.json (ROADMAP #193).
    if (core && !expandedPrograms.has(peBli)) {
      requestShards(loader, core, ["detail"]);
    }
    setExpandedPrograms((prev) => {
```

**Edit 14.22** — turning a column on asks for its shard — `site/src/components/years-matrix.tsx` (anchor on the quoted text). Replace this exact text:

```tsx
    } else {
      current.add(key);
    }
    setChosenCols(allColumns.filter((c) => current.has(c)));
```

with:

```tsx
    } else {
      current.add(key);
      // A column held by a shard appears once the shard merges (ROADMAP #193).
      const shard = shardOf.get(key);
      if (core && shard) requestShards(loader, core, [shard]);
    }
    setChosenCols(allColumns.filter((c) => current.has(c)));
```

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site || exit 1
npx vitest run src/__tests__/years-matrix.test.tsx src/__tests__/years-matrix-shards.test.ts src/__tests__/years-totals-chart.test.tsx
npx tsc --noEmit -p tsconfig.json
npx eslint src/components/years-matrix.tsx src/lib/years-matrix-shards.mjs src/__tests__/years-matrix.test.tsx src/__tests__/years-matrix-shards.test.ts
```

Expected: `Tests  80 passed (80)` (60 + 13 + 7); tsc and eslint print nothing
(exit 0).

- [ ] **Step 5: /agency/ looks decade cells up by slug (#208)**

Create `site/src/__tests__/decade-cells-slug-lookup.test.ts`:

```ts
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
```

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site && npx vitest run src/__tests__/decade-cells-slug-lookup.test.ts
```

Expected: `Tests  1 failed | 1 passed (2)` — `agency/[org]/page.tsx looks every
program up by its slug` with `AssertionError: expected 'a.pe_bli' to match
/^\w+\.slug$/`; `/programs/` already passes.

**Edit 14.23** — agency sort lookups — `site/src/app/agency/[org]/page.tsx`. Replace this exact text:

```tsx
    .sort((a, b) => {
      const av = decadeCells.get(a.pe_bli)?.fy26?.v ?? -Infinity;
      const bv = decadeCells.get(b.pe_bli)?.fy26?.v ?? -Infinity;
      return bv - av;
    });
```

with:

```tsx
    .sort((a, b) => {
      // ROADMAP #208: the cells are keyed by page slug (one per /years/ row),
      // as /programs/ looks them up. By bare pe_bli the 27 rows of the 13
      // shared budget-line codes found nothing and rendered "—".
      const av = decadeCells.get(a.slug)?.fy26?.v ?? -Infinity;
      const bv = decadeCells.get(b.slug)?.fy26?.v ?? -Infinity;
      return bv - av;
    });
```

**Edit 14.24** — agency citation slice lookup — `site/src/app/agency/[org]/page.tsx`. Replace this exact text:

```tsx
    const fid = decadeCells.get(p.pe_bli)?.fy24?.fid;
```

with:

```tsx
    const fid = decadeCells.get(p.slug)?.fy24?.fid;
```

**Edit 14.25** — agency row lookups — `site/src/app/agency/[org]/page.tsx`. Replace this exact text:

```tsx
                  {decadeCells.get(p.pe_bli)?.fy24 != null ? (
                    <>
                      <Cite
                        value={decadeCells.get(p.pe_bli)!.fy24!.v}
                        units="USD thousands"
                        dataset="fct_decade_series"
                        factId={decadeCells.get(p.pe_bli)!.fy24!.fid}
```

with:

```tsx
                  {decadeCells.get(p.slug)?.fy24 != null ? (
                    <>
                      <Cite
                        value={decadeCells.get(p.slug)!.fy24!.v}
                        units="USD thousands"
                        dataset="fct_decade_series"
                        factId={decadeCells.get(p.slug)!.fy24!.fid}
```

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site && npx vitest run src/__tests__/decade-cells-slug-lookup.test.ts
```

Expected: `Tests  2 passed (2)`.

- [ ] **Step 6: Ship the shards in the build, and re-measure the static fetch targets**

The island now names two more static fetch targets, so the scanner test that
lists them goes red first:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site && npx vitest run scripts/gates/__tests__/fetch-targets.test.mjs
```

Expected: `Tests  1 failed | 31 passed (32)` — `finds the four statically named
targets the client depends on`, whose list lacks
`/json/years_matrix/decade.json` and `/json/years_matrix/detail.json`.

**Edit 14.27** — fetch targets — `site/scripts/gates/__tests__/fetch-targets.test.mjs`. Replace this exact text:

```js
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
```

with:

```js
  it("finds the six statically named targets the client depends on", () => {
    const found = scanFetchTargets(srcDir);
    // Measured 2026-09-04 at five; RE-MEASURED 2026-09-05 (ROADMAP #88):
    // /json/feed.json left this list when FeedSectionExpand moved to the
    // directory-templated /json/feed-sections/${eventType}.json, which the
    // templated sweep below counts. RE-MEASURED again for ROADMAP #193 at
    // six: the /years/ island fetches its two lazy shards by literal URL.
    // This is the population MIN_STATIC_FETCH_TARGETS floors. Adding a
    // target is fine; losing one without re-measuring is the regression the
    // floor exists to catch.
    expect([...found.keys()].sort()).toEqual([
      "/config.json",
      "/json-lite/search_quick.json",
      "/json/flow_chart.json",
      "/json/years_matrix.json",
      "/json/years_matrix/decade.json",
      "/json/years_matrix/detail.json",
    ]);
```

**Edit 14.26** — prepare-assets 5d — `site/scripts/prepare-assets.mjs`. Replace this exact text:

```js
// ── 5d. Copy the years matrix sidecar (Phase 5D — /years/ grid) ──────────────
copyFile(
  path.join(jsonDir, "years_matrix.json"),
  path.join(jsonDestDir, "years_matrix.json")
);
console.log("✓  years_matrix.json → public/json/");
```

with:

```js
// ── 5d. Copy the years matrix (Phase 5D — /years/ grid) ──────────────────────
// ROADMAP #193: years_matrix.json is the CORE and its two lazy shards sit in
// years_matrix/ (decade.json, detail.json). The shard directory is MIRRORED
// (copyDir removes the destination first), so no shard the core does not
// list can ship beside it, and a split core without its directory is fatal.
// An export from before the split (schema_version 1, one file) ships alone.
const yearsCorePath = path.join(jsonDir, "years_matrix.json");
copyFile(yearsCorePath, path.join(jsonDestDir, "years_matrix.json"));
const yearsShardDest = path.join(jsonDestDir, "years_matrix");
if (JSON.parse(fs.readFileSync(yearsCorePath, "utf8")).schema_version >= 2) {
  copyDir(path.join(jsonDir, "years_matrix"), yearsShardDest);
  console.log("✓  years_matrix.json + years_matrix/ (decade, detail) → public/json/");
} else {
  fs.rmSync(yearsShardDest, { recursive: true, force: true });
  console.log("✓  years_matrix.json (pre-split export, no shards) → public/json/");
}
```

`prepare-assets.mjs` runs only inside `npm run build`, against a whole
`data/site`; its copy is proven by Task 21's build of the B export, where
linkgraph leg i (floor raised to 6 in Task 15) fails on any statically named
fetch target missing under `out/` and gate 20's loader refuses a core whose
shards are absent or stale.

- [ ] **Step 7: Run every touched suite, typecheck and lint**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site || exit 1
npx vitest run src/__tests__/years-matrix.test.tsx src/__tests__/years-matrix-shards.test.ts src/__tests__/years-totals-chart.test.tsx src/__tests__/decade-cells-slug-lookup.test.ts src/__tests__/citation-affordance.test.ts scripts/gates/__tests__/fetch-targets.test.mjs
npx tsc --noEmit -p tsconfig.json
npx eslint src/components/years-matrix.tsx src/lib/years-matrix-shards.mjs "src/app/agency/[org]/page.tsx" scripts/prepare-assets.mjs src/__tests__/years-matrix.test.tsx src/__tests__/years-matrix-shards.test.ts src/__tests__/decade-cells-slug-lookup.test.ts scripts/gates/__tests__/fetch-targets.test.mjs
```

Expected: `Test Files  6 passed (6)`, `Tests  140 passed (140)` (60 + 13 + 7 + 2 +
26 + 32; `citation-affordance.test.ts` reads the island's legend tags and
still passes); tsc and eslint print nothing.

- [ ] **Step 8: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/site/src/lib/years-matrix-shards.mjs GovBudget/site/src/lib/years-matrix-shards.d.mts GovBudget/site/src/components/years-matrix.tsx GovBudget/site/src/__tests__/years-matrix.test.tsx GovBudget/site/src/__tests__/years-matrix-shards.test.ts GovBudget/site/src/__tests__/decade-cells-slug-lookup.test.ts "GovBudget/site/src/app/agency/[org]/page.tsx" GovBudget/site/scripts/prepare-assets.mjs GovBudget/site/scripts/gates/__tests__/fetch-targets.test.mjs && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(site): /years/ opens on the core and loads each shard when asked; gap tooltip and legend restated; /agency/ looks decade cells up by slug (#193, #208)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
