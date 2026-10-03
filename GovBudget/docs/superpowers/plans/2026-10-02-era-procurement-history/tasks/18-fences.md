<!-- Part of the families piece-1 plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; ../notes.md has background. -->

### Task 18: Fences — lineage funding lines, /years/, the F-15 browser

**Spec:** §6.2 rows "/families/f-15/", "Lineage funding lines", "/years/" (the `/methodology/` row is Task 19's); §1 success criterion "`json/f15_funding_history.json` is byte-identical through the data changes"; §10 "Unchanged: … `/families/f-15/`, lineage funding lines, `years_matrix.json`"; V8 "years-matrix (unchanged)", "page weight (F-15 unchanged)"; S4 step "fences (§6.2)".
**Files:**
- Modify: `src/govbudget/export_site.py` — base lines `:3518-3523`, `:10601-10605`, `:10740-10743`, `:10870-10874`, `:10902-10907`, `:10923-10927`, `:12864-12868`, `:14283-14285`, `:17122-17125`, `:17170-17173` (post-Task-17 lines are given per edit)
- Modify: `site/src/lib/f15-family-data.ts:80-112`
- Create: `site/src/__tests__/f15-family-era-fence.test.ts`
- Modify (test): `tests/jbooks/test_export_lineage.py` (append after line 277), `tests/test_export_years_matrix.py:216-230` and append after line 743, `tests/jbooks/test_export_site_pg.py` (append at the end of the file)

Line numbers cited in this task are hints (anchor on the quoted text; line numbers are approximate): earlier tasks shift them.

**Interfaces:** Consumes: `era_grain_fids: frozenset[str]` from `_build_decade_citation_rows` (Task 17); the sidecar `decade_series` point shape `{fy, v, fid, edition, basis, measure}` (unchanged). / Produces: `_emit_lineage(..., era_grain_fids: frozenset[str] = frozenset())`, `_emit_years_matrix(..., era_grain_fids: frozenset[str] = frozenset())`, `_emit_json_sidecars(..., era_grain_fids: frozenset[str] = frozenset())`, `_write_all_sidecars(..., era_grain_fids: frozenset[str] = frozenset())`; TS `export const F15_FIRST_P1_DECADE_EDITION = 2024`, `export function isF15ShownDecadePoint(exhibit: string, point: { edition: number }): boolean`, and `loadRecord(slug: string): FamilyFundingRecord` becomes exported.

Fence design: the marker is out of band. `era_grain_fids` travels
`export_site` → `_emit_json_sidecars` → `_write_all_sidecars` → `_emit_lineage`
and `_emit_years_matrix`, each of which drops those fids before reading
anything; nothing is serialized, so `decade_grains` and the sidecar points keep
their shape. The F-15 browser cannot see the marker (it reads the sidecar), so
it fences by edition instead: P-1 records show PB2024 onward — exactly what they
showed before, because before this piece a P-1 code had no decade grain before
PB2024 (era rows were keyed by era key) — and R-1 records show every edition.

- [ ] **Step 1: Write the failing lineage fence test**

Append to the end of `tests/jbooks/test_export_lineage.py` (after line 277; the
file already imports `_emit_lineage` and defines `_series` and `_chain_edges`):

```python
def test_funding_line_skips_era_grains():
    """Families piece 1 (spec 2026-10-02 §6.2): an era point on a chain
    member's request series (837170's FY2018-20 requests, once era
    procurement history exists) stays off the funding line — the line is
    byte-identical to the one built without it. The marker is out of band
    (era_grain_fids); the point itself carries no era field."""
    edges = _chain_edges()
    families = {"PRED": 7, "MID": 7, "SUCC": 7, "DANGLE": 7}
    universe = {"PRED", "MID", "SUCC"}
    titles = {"PRED": "Predecessor", "MID": "Middle", "SUCC": "Successor"}
    native = {
        "PRED": _series((2023, 100.0, "fidPRED2023"), (2024, 50.0, "fidPRED2024")),
        "MID": _series((2024, 40.0, "fidMID2024")),
    }
    with_era = {
        "PRED": _series((2019, 70.0, "fidPREDera19"), (2023, 100.0, "fidPRED2023"),
                        (2024, 50.0, "fidPRED2024")),
        "MID": _series((2024, 40.0, "fidMID2024")),
    }
    cited = {"factPRED", "factMID", "factSUCC", "fidPRED2023", "fidPRED2024",
             "fidMID2024", "fidPREDera19"}

    def build(series, era):
        return _emit_lineage(
            edges=edges, families=families, all_pe_blis=universe,
            rollup_pes=set(), titles_by_pe=titles, decade_series_by_pe=series,
            cited_fact_ids=cited, era_grain_fids=frozenset(era),
        )

    unfenced = build(with_era, set())
    assert (2019, "PRED", 70.0, "fidPREDera19") in [
        (p["fy"], p["pe"], p["v"], p["fid"])
        for p in unfenced["PRED"]["family"]["funding_line"]
    ]
    assert build(with_era, {"fidPREDera19"}) == build(native, set())
```

- [ ] **Step 2: Run it and watch it fail**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_export_lineage.py -q
```

Expected: `1 failed, 12 passed`, the failure being
`TypeError: _emit_lineage() got an unexpected keyword argument 'era_grain_fids'`.

- [ ] **Step 3: Write the failing /years/ fence tests**

First let the test helper pass the fence and extra cited fids:

**Edit 18.11** — `tests/test_export_years_matrix.py:216-230`. Replace this exact text:

```python
def _emit(tmp_path: Path, decade_grains: list | None = None) -> dict:
    db_path = _make_duckdb_with_trajectory(tmp_path)
    json_dir = tmp_path / "json"
    json_dir.mkdir(exist_ok=True)
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        payload = _emit_years_matrix(
            json_dir=json_dir,
            con=con,
            all_prog_rows=_all_prog_rows(),
            detail_rows=_detail_rows(),
            bl_rows=_bl_rows(),
            cited_fact_ids=_cited_fact_ids(),
            decade_grains=decade_grains,
        )
```

with:

```python
def _emit(
    tmp_path: Path,
    decade_grains: list | None = None,
    *,
    era_grain_fids: frozenset[str] = frozenset(),
    extra_cited: frozenset[str] = frozenset(),
) -> dict:
    db_path = _make_duckdb_with_trajectory(tmp_path)
    json_dir = tmp_path / "json"
    json_dir.mkdir(exist_ok=True)
    # Passed only when set, so every other test drives the emitter's default.
    fence = {"era_grain_fids": era_grain_fids} if era_grain_fids else {}
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        payload = _emit_years_matrix(
            json_dir=json_dir,
            con=con,
            all_prog_rows=_all_prog_rows(),
            detail_rows=_detail_rows(),
            bl_rows=_bl_rows(),
            cited_fact_ids=_cited_fact_ids() | set(extra_cited),
            decade_grains=decade_grains,
            **fence,
        )
```


Then append to the end of `tests/test_export_years_matrix.py` (after line 743):

```python
# ---------------------------------------------------------------------------
# Families piece 1 (spec 2026-10-02 §6.2): era grains are fenced out of /years/
# ---------------------------------------------------------------------------

ERA_17A = "f311000000000041"  # PB2019 FY2017 actuals added through the era map
ERA_19R = "f411000000000042"  # PB2019 FY2019 request added through the era map
ERA_FIDS = frozenset({ERA_17A, ERA_19R})


def _era_grains() -> list[tuple]:
    """Era grains look exactly like native ones (no era field): only the
    out-of-band era_grain_fids set marks them. fy2017a and fy2019r are
    columns the native fixture grains do not have."""
    return [
        ("0601101E", 2017, 2019, "actuals", 777.0, ERA_17A,
         "fy_2017_actuals", None, None),
        ("0602303A", 2019, 2019, "request", 888.0, ERA_19R,
         "fy_2019_total", None, None),
    ]


class TestEraFence:
    def test_era_cells_would_render_without_the_fence(self, tmp_path):
        """Non-vacuity: unmarked, these cited grains DO become cells and
        columns, so the byte-identity below is the fence's doing."""
        payload = _emit(tmp_path, decade_grains=_decade_grains() + _era_grains(),
                        extra_cited=ERA_FIDS)
        assert _program(payload, "0601101E")["cells"]["fy2017a"] == {
            "v": 777.0, "fid": ERA_17A,
        }
        assert "fy2019r" in {c["key"] for c in payload["decade_columns"]}

    def test_era_grains_leave_years_matrix_byte_identical(self, tmp_path):
        base_dir = tmp_path / "base"
        era_dir = tmp_path / "era"
        base_dir.mkdir()
        era_dir.mkdir()
        base = _emit(base_dir, decade_grains=_decade_grains())
        fenced = _emit(era_dir, decade_grains=_decade_grains() + _era_grains(),
                       era_grain_fids=ERA_FIDS, extra_cited=ERA_FIDS)
        assert fenced == base
        assert (era_dir / "json" / "years_matrix.json").read_bytes() == (
            base_dir / "json" / "years_matrix.json"
        ).read_bytes()

    def test_era_only_grains_add_no_decade_header(self, tmp_path):
        payload = _emit(tmp_path, decade_grains=_era_grains(),
                        era_grain_fids=ERA_FIDS, extra_cited=ERA_FIDS)
        assert "decade_columns" not in payload
        assert "decade_default_columns" not in payload
```

- [ ] **Step 4: Run them and watch the two fence tests fail**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_export_years_matrix.py -q
```

Expected: `2 failed, 37 passed, 4 skipped`, or `2 failed, 41 passed` once Task 1's `data/site` link exists in the worktree (the 4 `years_matrix.json` live-file checks then run and pass instead of skipping; either form is correct, 0 other failures); both failures
(`test_era_grains_leave_years_matrix_byte_identical`,
`test_era_only_grains_add_no_decade_header`) are
`TypeError: _emit_years_matrix() got an unexpected keyword argument 'era_grain_fids'`.
`test_era_cells_would_render_without_the_fence` passes already: it proves the
fixture era grains WOULD become a `fy2017a` cell and a `fy2019r` column, so the
byte-identity test cannot pass vacuously.

- [ ] **Step 5: Write the failing plumbing test**

Append to the end of `tests/jbooks/test_export_site_pg.py` (it reuses that
file's `_run_decade_export`, which Task 17 gave a program table):

```python
def test_era_grain_fids_reach_the_fenced_emitters(pg_dsn, tmp_path, monkeypatch):
    """Families piece 1 (spec 2026-10-02 §6.2): export_site hands the decade
    tier's out-of-band era marker to the lineage and /years/ emitters, the
    only two readers of it. A sentinel set stands in for the tier's own."""
    import govbudget.export_site as es

    sentinel = frozenset({"e0a0000000000001"})
    real_tier = es._build_decade_citation_rows
    seen: dict[str, frozenset | None] = {}

    def tier(**kwargs):
        bl, cit, grains, side, _era = real_tier(**kwargs)
        return bl, cit, grains, side, sentinel

    def spy(name, real):
        def wrapper(**kwargs):
            seen[name] = kwargs.get("era_grain_fids")
            return real(**kwargs)
        return wrapper

    monkeypatch.setattr(es, "_build_decade_citation_rows", tier)
    monkeypatch.setattr(es, "_emit_lineage", spy("lineage", es._emit_lineage))
    monkeypatch.setattr(
        es, "_emit_years_matrix", spy("years_matrix", es._emit_years_matrix))
    _run_decade_export(pg_dsn, tmp_path)
    assert seen == {"lineage": sentinel, "years_matrix": sentinel}
```

Run (Task 1's cluster):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_export_site_pg.py -q -k era_grain_fids
```

Expected: `1 failed, 43 deselected` with
`AssertionError: assert {'lineage': None, 'years_matrix': None} == {'lineage': frozenset({'e0a0000000000001'}), 'years_matrix': frozenset({'e0a0000000000001'})}`.

- [ ] **Step 6: Implement the Python fences and the plumbing in `src/govbudget/export_site.py`**

**Edit 18.1 `_emit_lineage` signature** — `src/govbudget/export_site.py:10839-10843` after Task 17 (base `10fb4585`: 10601-10605). Replace this exact text:

```python
    titles_by_pe: dict[str, str],
    decade_series_by_pe: dict[str, dict],
    cited_fact_ids: set[str],
) -> dict[str, dict]:
    """Build the per-program ``lineage`` sidecar block (program-lineage Task 6).
```

with:

```python
    titles_by_pe: dict[str, str],
    decade_series_by_pe: dict[str, dict],
    cited_fact_ids: set[str],
    era_grain_fids: frozenset[str] = frozenset(),
) -> dict[str, dict]:
    """Build the per-program ``lineage`` sidecar block (program-lineage Task 6).

    era_grain_fids (families piece 1, spec 2026-10-02 §6.2): the decade
    grains the tier added through the reviewed era map. They are SKIPPED in
    every funding line: an era point's citation names the printed code while
    its row identity is an era key, which verify-lineage leg d would reject,
    and this piece changes no funding line. Funding lines stay byte-identical.
```

**Edit 18.2 `_emit_lineage` funding loop** — `src/govbudget/export_site.py:10978-10981` after Task 17 (base `10fb4585`: 10740-10743). Replace this exact text:

```python
            for pt in decade_series_by_pe.get(member, {}).get("request", []):
                fid = pt.get("fid")
                if fid is None or fid not in cited_fact_ids:
                    continue  # only resolving fids (they already are — belt & braces)
```

with:

```python
            for pt in decade_series_by_pe.get(member, {}).get("request", []):
                fid = pt.get("fid")
                if fid is None or fid not in cited_fact_ids:
                    continue  # only resolving fids (they already are — belt & braces)
                if fid in era_grain_fids:
                    continue  # spec §6.2 fence: era points stay off funding lines
```

**Edit 18.3 `_emit_json_sidecars` signature** — `src/govbudget/export_site.py:11108-11112` after Task 17 (base `10fb4585`: 10870-10874). Replace this exact text:

```python
    decade_side_meta: dict | None = None,
    summary_by_pe: dict | None = None,
    fy26_split_by_pe: dict | None = None,
) -> int:
    """Emit all JSON sidecars to out_dir/json/.
```

with:

```python
    decade_side_meta: dict | None = None,
    summary_by_pe: dict | None = None,
    fy26_split_by_pe: dict | None = None,
    era_grain_fids: frozenset[str] = frozenset(),
) -> int:
    """Emit all JSON sidecars to out_dir/json/.
```

**Edit 18.4 `_emit_json_sidecars` → `_write_all_sidecars` call** — `src/govbudget/export_site.py:11140-11145` after Task 17 (base `10fb4585`: 10902-10907). Replace this exact text:

```python
            decade_side_meta=decade_side_meta,
            summary_by_pe=summary_by_pe,
            fy26_split_by_pe=fy26_split_by_pe,
        )
    finally:
        con.close()
```

with:

```python
            decade_side_meta=decade_side_meta,
            summary_by_pe=summary_by_pe,
            fy26_split_by_pe=fy26_split_by_pe,
            era_grain_fids=era_grain_fids,
        )
    finally:
        con.close()
```

**Edit 18.5 `_write_all_sidecars` signature** — `src/govbudget/export_site.py:11161-11165` after Task 17 (base `10fb4585`: 10923-10927). Replace this exact text:

```python
    decade_side_meta: dict | None = None,
    summary_by_pe: dict | None = None,
    fy26_split_by_pe: dict | None = None,
) -> int:
    """Core sidecar writer; called from _emit_json_sidecars."""
```

with:

```python
    decade_side_meta: dict | None = None,
    summary_by_pe: dict | None = None,
    fy26_split_by_pe: dict | None = None,
    era_grain_fids: frozenset[str] = frozenset(),
) -> int:
    """Core sidecar writer; called from _emit_json_sidecars.

    era_grain_fids: the decade tier's out-of-band era marker (spec 2026-10-02
    §6.1). Never serialized; only the lineage and /years/ emitters read it,
    to keep era points off the surfaces this piece fences (§6.2)."""
```

**Edit 18.6 `_write_all_sidecars` → `_emit_lineage` call** — `src/govbudget/export_site.py:13102-13106` after Task 17 (base `10fb4585`: 12864-12868). Replace this exact text (a partial-line match: both the old and the new string end mid-line at `…diagram payload.` with no trailing newline; in the file that line continues ` Built from the …`, which stays as it is):

```python
        titles_by_pe=titles_by_pe,
        decade_series_by_pe=decade_series_by_pe,
        cited_fact_ids=_cited_fact_ids,
    )

    # ROADMAP #29(c) — the /lineage/ identity diagram payload.
```

with:

```python
        titles_by_pe=titles_by_pe,
        decade_series_by_pe=decade_series_by_pe,
        cited_fact_ids=_cited_fact_ids,
        era_grain_fids=era_grain_fids,
    )

    # ROADMAP #29(c) — the /lineage/ identity diagram payload.
```

**Edit 18.7 `_write_all_sidecars` → `_emit_years_matrix` call** — `src/govbudget/export_site.py:14521-14523` after Task 17 (base `10fb4585`: 14283-14285). Replace this exact text:

```python
        cited_fact_ids=_cited_fact_ids,
        decade_grains=decade_grains,
        # program-lineage Task 8: sparse pe_bli→family_id map (from
```

with:

```python
        cited_fact_ids=_cited_fact_ids,
        decade_grains=decade_grains,
        era_grain_fids=era_grain_fids,
        # program-lineage Task 8: sparse pe_bli→family_id map (from
```

**Edit 18.8 `_emit_years_matrix` signature** — `src/govbudget/export_site.py:17360-17363` after Task 17 (base `10fb4585`: 17122-17125). Replace this exact text:

```python
    decade_grains: list | None = None,
    families: dict[str, int] | None = None,
) -> dict:
    """Emit json/years_matrix.json — the /years/ CapIQ-style grid payload.
```

with:

```python
    decade_grains: list | None = None,
    families: dict[str, int] | None = None,
    era_grain_fids: frozenset[str] = frozenset(),
) -> dict:
    """Emit json/years_matrix.json — the /years/ CapIQ-style grid payload.

    era_grain_fids (families piece 1, spec 2026-10-02 §6.2): decade grains
    added through the reviewed era map are dropped BEFORE anything reads
    decade_grains, so the payload (cells, decade_columns, the header's
    edition map, decade_default_columns) is byte-identical to an export
    without them. Era procurement would add about 0.75 MB against the
    4 MiB cap and fail years-matrix leg g; carrying it needs the matrix
    sharded first (filed follow-up, spec §11).
```

**Edit 18.9 `_emit_years_matrix` drops era grains first** — `src/govbudget/export_site.py:17408-17411` after Task 17 (base `10fb4585`: 17170-17173). Replace this exact text:

```python
    from collections import defaultdict

    # program-lineage Task 8: sparse pe_bli→family_id overlay (UI-only badge).
    fam_map: dict[str, int] = families or {}
```

with:

```python
    from collections import defaultdict

    # spec §6.2 fence: the matrix is built as if era grains did not exist.
    decade_grains = [
        g for g in (decade_grains or []) if g[5] not in era_grain_fids
    ]

    # program-lineage Task 8: sparse pe_bli→family_id overlay (UI-only badge).
    fam_map: dict[str, int] = families or {}
```

**Edit 18.10 `export_site` → `_emit_json_sidecars` call** — `src/govbudget/export_site.py:3518-3523` after Task 17 (base `10fb4585`: 3518-3523). Replace this exact text (both the old and the new string end at `…not before` with no trailing newline: match up to there, partial-line style, and leave the file's newline and the next comment line as they are):

```python
        decade_grains=decade_grains,
        decade_side_meta=decade_side_meta,
        summary_by_pe=summary_by_pe,
        fy26_split_by_pe=fy26_split_by_pe,
    )

    # Write citations.parquet — AFTER _emit_json_sidecars(), not before
```

with:

```python
        decade_grains=decade_grains,
        decade_side_meta=decade_side_meta,
        summary_by_pe=summary_by_pe,
        fy26_split_by_pe=fy26_split_by_pe,
        era_grain_fids=era_grain_fids,
    )

    # Write citations.parquet — AFTER _emit_json_sidecars(), not before
```


- [ ] **Step 7: Run the Python fence tests**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_export_lineage.py tests/test_export_years_matrix.py tests/test_export_decade_era_map.py tests/test_export_breakdowns.py -q
```

Expected: `90 passed, 4 skipped` (13 + 39 + 16 + 22; the skips are the
`live export not present` checks), or `94 passed` with 0 skipped once Task 1's `data/site`
link exists (those 4 live `years_matrix.json` checks then run and pass; measured in the
pre-flight scratch run). Either form passes; the criterion is 0 failed.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_export_basis.py tests/jbooks/test_export_site_pg.py -q
```

Expected: `61 passed` (17 + 44).

- [ ] **Step 8: Write the failing F-15 browser fence test**

Create `site/src/__tests__/f15-family-era-fence.test.ts` (hermetic: it mocks
`@/lib/data`, so it does not need `data/site`):

```ts
/**
 * Families piece 1 (spec 2026-10-02 §6.2): the /families/f-15/ page keeps
 * showing exactly the decade editions it showed before procurement history
 * reached PB2017 — every R-1 edition, P-1 from PB2024 on. Era P-1 points
 * (about 45 facts on F01500, F15EWS and F015EX) would exceed the page's
 * weight ceiling; F-15 keeps its own reviewed era history in
 * f15_funding_history.json.
 *
 * Hermetic: @/lib/data is mocked, so this runs without data/site.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Citation, DecadePoint, ProgramDetails, ProgramRow } from "@/lib/data";
import { F15_FIRST_P1_DECADE_EDITION, isF15ShownDecadePoint, loadRecord } from "@/lib/f15-family-data";

const state = vi.hoisted(() => ({ details: new Map<string, unknown>() }));

vi.mock("@/lib/data", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/lib/data")>();
  return {
    ...real,
    getPrograms: () => [...state.details.keys()].map((slug) => ({ slug, title: `Program ${slug}` }) as unknown as ProgramRow),
    getProgramDetails: (slug: string) => state.details.get(slug) as ProgramDetails,
    getCitation: (factId: string) => ({
      kind: "workbook", fact_id: factId, units: "USD thousands", amount_thousands: 1,
      sheet: "Exhibit P-1", cells: "Q9", official_url: "https://example.mil/p1.xlsx",
      retrieved_at: "2026-07-01T00:00:00",
    }) as unknown as Citation,
  };
});

const point = (fy: number, edition: number, fid: string, measure: string): DecadePoint => ({ fy, v: 1000 + fy, fid, edition, basis: "toa", measure });

function setDetails(slug: string, exhibit: "P-1" | "R-1", series: ProgramDetails["decade_series"]) {
  state.details.set(slug, {
    budget_lines: [{ exhibit, fy: null, measure: null }],
    summary: { cards: [] },
    narratives: [],
    decade_series: series,
  });
}

beforeEach(() => state.details.clear());

describe("F-15 decade edition fence", () => {
  it("shows P-1 decade points from PB2024 on and every R-1 edition", () => {
    expect(F15_FIRST_P1_DECADE_EDITION).toBe(2024);
    expect(isF15ShownDecadePoint("P-1", { edition: 2023 })).toBe(false);
    expect(isF15ShownDecadePoint("P-1", { edition: 2024 })).toBe(true);
    expect(isF15ShownDecadePoint("R-1", { edition: 2017 })).toBe(true);
  });

  it("drops era P-1 points from a BLI record and keeps its modern points", () => {
    setDetails("F01500", "P-1", {
      actuals: [point(2017, 2019, "a017000000000001", "actuals"), point(2022, 2024, "a022000000000001", "actuals")],
      request: [point(2019, 2019, "b019000000000001", "request"), point(2024, 2024, "b024000000000001", "request")],
    });
    const record = loadRecord("F01500");
    expect(record.facts.map((fact) => [fact.fy, fact.edition, fact.factId])).toEqual([
      [2022, 2024, "a022000000000001"],
      [2024, 2024, "b024000000000001"],
    ]);
  });

  it("keeps every edition of an R-1 record", () => {
    setDetails("0207134F", "R-1", {
      request: [point(2017, 2017, "c017000000000001", "request"), point(2024, 2024, "c024000000000001", "request")],
    });
    expect(loadRecord("0207134F").facts.map((fact) => fact.edition)).toEqual([2017, 2024]);
  });
});
```

Export `loadRecord` so the test can drive it (no behaviour change):

**Edit 18.12** — `site/src/lib/f15-family-data.ts:84-84`. Replace this exact text:

```ts
function loadRecord(slug: string): FamilyFundingRecord {
```

with:

```ts
export function loadRecord(slug: string): FamilyFundingRecord {
```


- [ ] **Step 9: Run it and watch the fence tests fail**

Run (from `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site`):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site && npx vitest run src/__tests__/f15-family-era-fence.test.ts
```

Expected: `Tests  2 failed | 1 passed (3)`:
`shows P-1 decade points from PB2024 on and every R-1 edition` fails with
`AssertionError: expected undefined to be 2024`, and
`drops era P-1 points from a BLI record and keeps its modern points` fails with
`AssertionError: expected [ …(4) ] to deeply equal [ …(2) ]`. The R-1 test
passes (R-1 editions were never fenced).

- [ ] **Step 10: Implement the F-15 fence**

**Edit 18.13** — `site/src/lib/f15-family-data.ts:80-82`. Replace this exact text:

```ts
function isToaCard(card: SummaryCard): card is SummaryCard & { fid: string; value: number; basis: string } {
  return card.basis === "toa" && card.units === "USD thousands" && card.fid != null && card.value != null;
}
```

with:

```ts
function isToaCard(card: SummaryCard): card is SummaryCard & { fid: string; value: number; basis: string } {
  return card.basis === "toa" && card.units === "USD thousands" && card.fid != null && card.value != null;
}

/**
 * First P-1 edition whose decade points this page shows (spec 2026-10-02
 * §6.2). The decade tier now gives P-1 program pages their PB2017–PB2023
 * points through the reviewed era map; this page keeps exactly the editions
 * it showed before (every R-1 edition, P-1 from PB2024 on). The era points
 * would add about 45 facts and break its page-weight ceiling, and F-15's
 * own reviewed era history is f15_funding_history.json.
 */
export const F15_FIRST_P1_DECADE_EDITION = 2024;

export function isF15ShownDecadePoint(exhibit: string, point: { edition: number }): boolean {
  return exhibit !== "P-1" || point.edition >= F15_FIRST_P1_DECADE_EDITION;
}
```


**Edit 18.14** — `site/src/lib/f15-family-data.ts:108-110`. Replace this exact text:

```ts
    for (const point of points) {
      if (point.basis !== "toa") continue;
      add(fundingFact(slug, exhibit, { ...point, value: point.v, dataset: "fct_decade_series" }));
```

with:

```ts
    for (const point of points) {
      if (point.basis !== "toa") continue;
      if (!isF15ShownDecadePoint(exhibit, point)) continue;
      add(fundingFact(slug, exhibit, { ...point, value: point.v, dataset: "fct_decade_series" }));
```


- [ ] **Step 11: Run the TS test, lint and typecheck**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site || exit 1
npx vitest run src/__tests__/f15-family-era-fence.test.ts
npx eslint src/lib/f15-family-data.ts src/__tests__/f15-family-era-fence.test.ts
npx tsc --noEmit -p tsconfig.json
```

Expected: `Tests  3 passed (3)`; eslint prints nothing (exit 0); tsc prints
nothing (exit 0). The live-data F-15 suites (`f15-family-data.test.ts`,
`f15-funding-inputs.test.ts`) need `../data/site` and are re-run by Task 21 on
the S4 export, where the S0 normalized page snapshot (Task 4) is the proof that
`/families/f-15/` did not change.

- [ ] **Step 12: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/src/govbudget/export_site.py GovBudget/tests/jbooks/test_export_lineage.py GovBudget/tests/test_export_years_matrix.py GovBudget/tests/jbooks/test_export_site_pg.py GovBudget/site/src/lib/f15-family-data.ts GovBudget/site/src/__tests__/f15-family-era-fence.test.ts && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(export): fence era decade points off lineage funding lines, /years/ and the F-15 browser (families piece 1, spec §6.2)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
