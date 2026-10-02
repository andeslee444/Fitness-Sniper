<!-- Part of the families piece-1 plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; ../notes.md has background. -->

### Task 4: F-15 hermetic fixtures, sha pin, golden test, page snapshot

**Spec:** §8 V5 (golden; fresh state with injected `decade_era_map` receipts; allowed-formula sensitivity), §9 S0 (hermetic F-15 fixtures and sha pin; normalized F-15 page snapshot from a fresh build at the base commit, never `site/out`), §6.2 (the F-15 fence's proof artifact), §6.5 (the re-pin procedure S5 will use), §1 success criterion 3 (`f15_funding_history.json` byte-identical S0–S4).

**Files:**
- Create: `tests/test_f15_era_identity.py`
- Create: `scripts/era/capture_f15_fixtures.py`
- Create (captured, never hand-edited): `tests/fixtures/f15/history.json`, `tests/fixtures/f15/history.sha256`, `tests/fixtures/f15/builder_inputs.json.gz`, `tests/fixtures/f15/page_snapshot.json`
- Create: `tests/fixtures/f15/README.md`
- Create: `site/scripts/f15-page-snapshot.mjs`
- Test: `site/scripts/gates/__tests__/f15-page-snapshot.test.mjs`
- Read only (no change): `src/govbudget/f15_funding_history.py:120-199` (`build_history`), `:202-302` (`build_program_matrix`; reuse allow-list `:271-278`, candidate choice `:279-296`), `:305-454` (`export_f15_funding_history`: series query `:321`, source query `:337-344`, previews `:354`, staging/writes `:395-451`); call site `src/govbudget/export_site.py:3589-3592`; `site/src/components/family-funding-history.tsx:29-108` (matrix markup); `site/src/lib/f15-family-data.ts:84-137` (`loadRecord`)
- Environment only (never committed): symlink `data/site` in the worktree

**Interfaces:**
Consumes: Task 1's environment (`uv sync` in `GovBudget/`, real `node_modules` from `npm ci` in `GovBudget/site/`). Existing code, unchanged: `govbudget.f15_funding_history.{build_history, build_program_matrix, member_row, _json_bytes}`, `govbudget.export_site.{fact_id_derived, _stage_parquet_path}`, `govbudget.workbook_cells.build_workbook_previews`, `govbudget.config.{SITE_DIR, DUCKDB_PATH}`, site devDependencies `node-html-parser` 7.1.0 and `vitest` 3. Spec §6.1's `decade_era_map` key and formula (minted later by Task 17).
Produces:
- `tests/fixtures/f15/history.sha256` = `9f70c770eb7c91e33919fd66e6f316a1461035cdfcfa446a725f063d593c8800\n` (read by Task 20 leg f; re-pinned by Task 22)
- `tests/fixtures/f15/history.json` (138,486 bytes, byte copy of the S0 export's `json/f15_funding_history.json`)
- `tests/fixtures/f15/builder_inputs.json.gz`: gzip of `_json_bytes({schema: 1, captured_from: {site_built_at, history_sha256, citations_json_sha256}, retrieved_at, source_rows: [467], series: [195], current_fact_ids: [20], previews: {207}, registry: {150}})`
- `tests/fixtures/f15/page_snapshot.json` (the S0 page baseline Tasks 18, 21 compare against; re-pinned by Task 22)
- `scripts/era/capture_f15_fixtures.py`: `capture(*, site_dir: Path, duckdb_path: Path) -> tuple[dict, bytes]`, `main(argv: list[str] | None = None) -> int`; CLI `python scripts/era/capture_f15_fixtures.py --expect-sha256 HEX [--site-dir DIR] [--duckdb PATH] [--out-dir DIR]`
- `tests/test_f15_era_identity.py`: `test_pin_matches_committed_history`, `test_golden_rebuild_from_fixtures_is_byte_identical`, `test_fresh_state_with_decade_era_map_receipts_keeps_every_byte`, `test_allowed_formula_competitor_changes_exactly_one_cell`
- `site/scripts/f15-page-snapshot.mjs`: `export const SNAPSHOT_SCHEMA = 1`, `export function snapshotF15Page(html: string): object`, `export function firstDifference(a, b, at = "$"): string | null`; CLI `node scripts/f15-page-snapshot.mjs <index.html> [--out FILE | --check FILE]` — `--check` prints `f15-page-snapshot: PASS — equal to FILE` (exit 0) or `f15-page-snapshot: FAIL — differs from FILE at <path>: <baseline> != <page>` (exit 1)

Measured for this task (read-only, 2026-10-02, export `built_at` 2026-10-02T01:30:21.066005+00:00):
- `shasum -a 256 data/site/json/f15_funding_history.json` → `9f70c770eb7c91e33919fd66e6f316a1461035cdfcfa446a725f063d593c8800`; `wc -c` → 138486.
- `export_f15_funding_history`'s own queries over the live lake: 142,933 P-1/R-1 source rows, 467 F-15 member rows, 195 `fct_decade_series` rows on member grains, 207 workbook leaves (20 of them already in `data/budget_lines.parquet`), 30 annual points. The member-only rebuild equals the full-lake rebuild; previews rebuilt from `data/site/workbooks` equal the shipped `workbook-cells` entries; the rebuild with the 150-citation registry subset equals the rebuild with the full 125,409-citation registry equals the shipped bytes.
- 168 matrix cells, 38 with two or more inputs: 27 era cells (all carrying F-15's own `family_program_history` receipt) and 11 modern/R-1 cells reusing program-page receipts with allowed formulas; no cell mixes amount types. The registry subset holds 57 of F-15's own receipts (30 annual + 27 cell; the cumulative's inputs are annual IDs, so it is not in the subset).
- Sensitivity target: `points[2]` (PB2018, FY2016 actuals), `program_cells[2]` = `P-1:3010F:AF:F01500`, fact ID `a0231f5a75a7ad52` = `fact_id_derived("family_program_history", "P-1:3010F:AF:F01500|2018|2016", "actuals")`, inputs `28f53c8d681494cc`, `cce72b42a96bfcb7`, both `fy_2016_base_oco`, 596,932.000.
- The spec reviewer's reproduction (`/private/tmp/claude-501/-Users-andeslee-Documents-Cursor-Projects-GovBudget/f2419a45-061b-4164-84f1-612181faeb7b/scratchpad/specreview/v5neg.py`, re-run read-only for this draft) still holds: fresh-state bytes equal the shipped bytes; an era-map competitor does not change them; an allowed-formula competitor does.
- Live `https://fiscalreceipts.com/families/f-15/` (saved 2026-10-02 03:03Z, after the aa714d7f deploy) reduces to: 107 `data-fact-id` elements, 92 distinct; `data-dataset` counts budget_lines 23, budget_lines_decade 39, f15_funding_history 29, fct_decade_series 16; `family:f-15` 14 times; 223 distinct page fact IDs in 1,196 occurrences (all 223 are `citations.json` keys); 8 matrix rows × 12 columns. The site code is identical between the deployed commit and the base (`git diff --stat aa714d7f 10fb4585 -- GovBudget/site GovBudget/src` is empty).
- The main checkout's `site/out` is a 2026-09-29 build at `eb28b124` whose F-15 page has 81 `data-fact-id` elements, not 107 — the reason the baseline must come from a fresh build.
- `tests/test_f15_funding_history.py`: 30 passed.

- [ ] **Step 1: Write the failing V5 identity tests**

Create `tests/test_f15_era_identity.py`:

```python
"""V5 — F-15 family history identity, on hermetic fixtures (no lake, no data/site).

Spec 2026-10-02-era-procurement-history-design.md §8 V5, §9 S0, §6.2. The
fixtures under tests/fixtures/f15/ are captured once, at S0, by
scripts/era/capture_f15_fixtures.py and re-pinned only by the owner-approved
F-15 correction (S5, §6.5). These tests FAIL, never skip, when they are absent.

1. Golden: build_history + build_program_matrix over the captured inputs
   reproduce the pinned json/f15_funding_history.json byte for byte.
2. Fresh state: with F-15's own family_history / family_program_history
   receipts removed from the registry, and a `decade_era_map` receipt with
   identical inputs and amount injected for every multi-input matrix cell (what
   the era decade tier will mint, §6.1), the bytes are unchanged.
3. Sensitivity: a competitor whose formula IS on the matrix's reuse list,
   with identical inputs and amount, changes exactly one cell's fact ID — so
   the formula allow-list, not luck, is what keeps F-15 stable in (2).
"""
from __future__ import annotations

import functools
import gzip
import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pytest

from govbudget.export_site import fact_id_derived
from govbudget.f15_funding_history import _json_bytes, build_history, build_program_matrix

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "f15"

# The sensitivity target (verified against the pinned history at S0): PB2018,
# FY2016 actuals, BLI F01500 — two era leaves (PB2018 lines 23 and 79), both
# fy_2016_base_oco, $596,932K. Its own receipt is family_program_history.
TARGET_POINT, TARGET_CELL = 2, 2
TARGET_PROGRAM = "P-1:3010F:AF:F01500"
TARGET_OWN_FID = "a0231f5a75a7ad52"
TARGET_INPUTS = ["28f53c8d681494cc", "cce72b42a96bfcb7"]
COMPETITOR_FID = "0" * 16


def _fixture_path(name: str) -> Path:
    path = FIXTURES / name
    if not path.is_file():
        pytest.fail(f"F-15 identity fixture missing: {path.relative_to(ROOT)} "
                    "(capture it with scripts/era/capture_f15_fixtures.py; spec §9 S0)", pytrace=False)
    return path


@functools.lru_cache(maxsize=1)
def _inputs() -> dict:
    with gzip.open(_fixture_path("builder_inputs.json.gz"), "rt", encoding="utf-8") as handle:
        return json.load(handle)


def _pinned_bytes() -> bytes:
    return _fixture_path("history.json").read_bytes()


def _payload():
    """build_history over the captured rows: (payload, workbook leaf ids)."""
    inputs = _inputs()
    payload, _, workbook_rows, _ = build_history(
        inputs["source_rows"], inputs["series"], retrieved_at=inputs["retrieved_at"],
        current_fact_ids=set(inputs["current_fact_ids"]))
    return payload, set(workbook_rows)


def _matrix_bytes(payload, registry) -> tuple[bytes, dict, dict]:
    out, additions, breakdowns = build_program_matrix(
        payload, _inputs()["previews"], existing_citations=registry, retrieved_at=_inputs()["retrieved_at"])
    return _json_bytes(out), additions, breakdowns


def _own_receipt_ids(history: dict) -> set[str]:
    """Every receipt F-15's own builder mints: annual, cumulative, multi-input cells."""
    ids = {history["cumulative"]["fact_id"]}
    for point in history["points"]:
        ids.add(fact_id_derived("family_history", f"f-15|{point['edition']}|{point['fy']}", point["kind"]))
        for cell in point["program_cells"]:
            if len(cell["input_fact_ids"]) > 1:
                ids.add(fact_id_derived("family_program_history",
                                        f"{cell['program_id']}|{point['edition']}|{point['fy']}", point["kind"]))
    return ids


def _fresh_registry(history: dict) -> dict:
    own = _own_receipt_ids(history)
    registry = _inputs()["registry"]
    # The captured subset holds the 30 annual receipts and the 27 era
    # multi-input cell receipts (the cumulative's inputs are annual ids, not
    # workbook leaves, so it is not in the subset).
    assert len(own & set(registry)) == 57
    return {fid: citation for fid, citation in registry.items() if fid not in own}


def _diff(a, b, at=()):
    """Every leaf path at which two JSON values differ, as (path, a, b)."""
    if isinstance(a, dict) and isinstance(b, dict):
        return [d for key in sorted(set(a) | set(b)) for d in _diff(a.get(key), b.get(key), (*at, key))]
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [d for index, (x, y) in enumerate(zip(a, b)) for d in _diff(x, y, (*at, index))]
    return [] if a == b else [(at, a, b)]


def test_pin_matches_committed_history():
    data = _pinned_bytes()
    pin = _fixture_path("history.sha256").read_text().strip()
    assert len(pin) == 64 and pin == hashlib.sha256(data).hexdigest()
    assert _inputs()["captured_from"]["history_sha256"] == pin


def test_golden_rebuild_from_fixtures_is_byte_identical():
    payload, leaves = _payload()
    assert len(leaves) == 207 and len(payload["points"]) == 30
    assert set(_inputs()["previews"]) == leaves
    data, _, _ = _matrix_bytes(payload, _inputs()["registry"])
    assert data == _pinned_bytes()


def test_fresh_state_with_decade_era_map_receipts_keeps_every_byte():
    history = json.loads(_pinned_bytes())
    registry = _fresh_registry(history)
    injected = 0
    era_cells = 0
    for point in history["points"]:
        components = {row["fact_id"]: row for row in point["components"]}
        for cell in point["program_cells"]:
            ids = sorted(cell["input_fact_ids"])
            if len(ids) < 2:
                continue
            amount_types = {components[fid]["amount_type"] for fid in ids}
            assert len(amount_types) == 1, cell["fact_id"]
            amount_type = amount_types.pop()
            code = cell["program_id"].rsplit(":", 1)[1]
            amount = sum((Decimal(str(components[fid]["amount_thousands"])) for fid in ids), Decimal(0))
            # §6.1: surface "decade_era_map", key "{program_key}|{account}|{organization}|{edition}"
            # (blank account/organization for a non-collision code), inputs sorted by fact ID.
            fid = fact_id_derived("decade_era_map", f"{code}|||{point['edition']}", amount_type)
            registry[fid] = dict(
                kind="derived", units="USD thousands", recorded_value=f"{amount:.3f}",
                formula=(f"sum(budget_lines.amount_thousands where era_line_map='{code}' "
                         f"and amount_type={amount_type} and edition={point['edition']})"),
                inputs=json.dumps(ids), retrieved_at="2026-10-02T00:00:00+00:00")
            injected += 1
            era_cells += all(components[f]["pe_bli"].startswith("3010F-AF-L") for f in ids)
    assert (injected, era_cells) == (38, 27)
    payload, _ = _payload()
    data, _, _ = _matrix_bytes(payload, registry)
    assert data == _pinned_bytes()


def test_allowed_formula_competitor_changes_exactly_one_cell():
    history = json.loads(_pinned_bytes())
    point = history["points"][TARGET_POINT]
    cell = point["program_cells"][TARGET_CELL]
    assert (point["edition"], point["fy"], point["kind"]) == (2018, 2016, "actuals")
    assert (cell["program_id"], cell["fact_id"], sorted(cell["input_fact_ids"])) == (TARGET_PROGRAM, TARGET_OWN_FID, TARGET_INPUTS)
    assert TARGET_OWN_FID == fact_id_derived("family_program_history", f"{TARGET_PROGRAM}|2018|2016", "actuals")
    competitor = dict(
        kind="derived", units="USD thousands", recorded_value="596932.000",
        formula="sum(budget_lines.amount_thousands where amount_type=fy_2016_base_oco and edition=2018)",
        inputs=json.dumps(TARGET_INPUTS), retrieved_at="2026-10-02T00:00:00+00:00")
    payload, _ = _payload()

    # Fresh state: nothing outranks the allowed competitor, so it takes the cell.
    data, additions, breakdowns = _matrix_bytes(payload, {**_fresh_registry(history), COMPETITOR_FID: competitor})
    changed = json.loads(data)
    assert _diff(history, changed) == [
        (("points", TARGET_POINT, "program_cells", TARGET_CELL, "fact_id"), TARGET_OWN_FID, COMPETITOR_FID)]
    assert additions[COMPETITOR_FID] == competitor and TARGET_OWN_FID not in additions
    assert COMPETITOR_FID in breakdowns and TARGET_OWN_FID not in breakdowns

    # Today's registry: F-15's own receipt (allowed index 0) outranks it.
    data, _, _ = _matrix_bytes(payload, {**_inputs()["registry"], COMPETITOR_FID: competitor})
    assert data == _pinned_bytes()
```

- [ ] **Step 2: Run the tests and watch them fail on the missing fixtures**

Run (from `GovBudget/` in the worktree):

```bash
uv run --project . pytest tests/test_f15_era_identity.py -q
```

Expected: `4 failed`. Each failure body reads `F-15 identity fixture missing: tests/fixtures/f15/<file> (capture it with scripts/era/capture_f15_fixtures.py; spec §9 S0)` — `history.json` for three tests, `builder_inputs.json.gz` for the golden test. They fail; none skips.

- [ ] **Step 3: Write the capture script**

Create `scripts/era/capture_f15_fixtures.py` (the `scripts/era/` directory is new; no `__init__.py`):

```python
#!/usr/bin/env python3
"""Capture the hermetic F-15 identity fixtures (spec 2026-10-02 era procurement, §8 V5, §9 S0).

Reads, never writes, the live export and lake:
  - fct_decade_series from the DuckDB file (read_only=True),
  - the staged jbooks budget_lines/documents parquets beside it,
  - data/site: manifest.json, data/budget_lines.parquet, json/citations.json,
    json/f15_funding_history.json, json/workbook-cells/*, workbooks/*.xlsx.

Writes only into --out-dir (default tests/fixtures/f15/):
  history.json            byte copy of data/site/json/f15_funding_history.json
  history.sha256          its sha256 as 64 hex characters plus a newline
  builder_inputs.json.gz  exactly what build_history/build_program_matrix read:
                          the F-15 member workbook rows, their fct_decade_series
                          rows, the member fact ids already in budget_lines,
                          the 207 workbook-cell previews, and every derived
                          citation with at least one F-15 workbook leaf among
                          its inputs (a superset of what the matrix may reuse).

Nothing is written unless all of these hold: the member-only rebuild equals
the full-lake rebuild; the previews rebuilt from the sha-named workbooks equal
the shipped workbook-cells entries; the rebuild from the captured inputs is
byte-identical to the shipped history; and that history's sha256 equals
--expect-sha256 (the value the owner-approved record pins).

Usage (from GovBudget/):
  S0 capture, from the live export:
  GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data \\
    uv run --project . python scripts/era/capture_f15_fixtures.py \\
    --expect-sha256 9f70c770eb7c91e33919fd66e6f316a1461035cdfcfa446a725f063d593c8800
  S5 re-pin, from the proof clone (never the live lake; tests/fixtures/f15/README.md):
  uv run --project . python scripts/era/capture_f15_fixtures.py \\
    --site-dir /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s5/site \\
    --duckdb /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s5/duckdb/govbudget.duckdb \\
    --out-dir tests/fixtures/f15 --expect-sha256 <S5 sha>
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path

import duckdb

from govbudget import config
from govbudget.export_site import _stage_parquet_path
from govbudget.f15_funding_history import _json_bytes, build_history, build_program_matrix, member_row
from govbudget.workbook_cells import build_workbook_previews

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_SCHEMA = 1
SERIES_SQL = ("select pe_bli, fy, edition_year as edition, amount_type_kind as kind, amount, amount_type, n_source_rows "
              "from fct_decade_series")
# The exact projection export_f15_funding_history reads (f15_funding_history.py:337-344).
SOURCE_SQL = """select b.exhibit, cast(b.fiscal_year as integer) as edition,
    b.account, b.account_title, b.organization, b.budget_activity,
    b.budget_activity_title, b.pe_bli, b.title, b.amount_type,
    cast(b.amount_thousands as double) as amount_thousands,
    d.sha256, b.source_sheet as sheet, b.source_cells as cells,
    d.source_url as official_url, d.downloaded_at as retrieved_at
    from read_parquet(?) b join read_parquet(?) d on b.source_document_id=d.id
    where b.exhibit in ('P-1','R-1')"""


def _rows(cursor) -> list[dict]:
    names = [d[0] for d in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def capture(*, site_dir: Path, duckdb_path: Path) -> tuple[dict, bytes]:
    """Return (fixture, shipped history bytes); raise when any proof fails."""
    con = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        series = _rows(con.execute(SERIES_SQL))
    finally:
        con.close()
    lake = _stage_parquet_path(duckdb_path, "jbooks", "budget_lines.parquet")
    documents = _stage_parquet_path(duckdb_path, "jbooks", "documents.parquet")
    if not lake or not documents:
        raise SystemExit(f"capture_f15_fixtures: no staged jbooks parquets beside {duckdb_path}")
    con = duckdb.connect()
    try:
        source_rows = _rows(con.execute(SOURCE_SQL, [str(lake), str(documents)]))
        current_fact_ids = {row[0] for row in con.execute(
            "select fact_id from read_parquet(?)", [str(site_dir / "data" / "budget_lines.parquet")]).fetchall()}
    finally:
        con.close()
    retrieved_at = json.loads((site_dir / "manifest.json").read_text())["built_at"]

    members = sorted((row for row in source_rows if member_row(row)),
                     key=lambda r: (r["edition"], r["exhibit"], r["pe_bli"], r["budget_activity"] or "", r["amount_type"]))
    grains = {(r["pe_bli"], r["edition"], r["amount_type"]) for r in members}
    member_series = sorted((p for p in series if (p["pe_bli"], p["edition"], p["amount_type"]) in grains),
                           key=lambda p: (p["edition"], p["pe_bli"], p["fy"], p["kind"], p["amount_type"]))

    payload, citations, workbook_rows, _ = build_history(
        members, member_series, retrieved_at=retrieved_at, current_fact_ids=current_fact_ids)
    full_payload, _, _, _ = build_history(
        source_rows, series, retrieved_at=retrieved_at, current_fact_ids=current_fact_ids)
    if _json_bytes(payload) != _json_bytes(full_payload):
        raise SystemExit("capture_f15_fixtures: the member-only rebuild differs from the full-lake rebuild")
    leaves = set(workbook_rows)

    previews = build_workbook_previews(workbook_dir=site_dir / "workbooks",
                                       citations={fid: citations[fid] for fid in sorted(leaves)})
    shipped_previews = {}
    for prefix in sorted({fid[:2] for fid in leaves}):
        shard = json.loads((site_dir / "json" / "workbook-cells" / f"{prefix}.json").read_text())
        shipped_previews.update({fid: obj for fid, obj in shard.items() if fid in leaves})
    if set(previews) != leaves or _json_bytes(previews) != _json_bytes(shipped_previews):
        raise SystemExit("capture_f15_fixtures: rebuilt workbook previews differ from the shipped workbook-cells entries")

    registry = json.loads((site_dir / "json" / "citations.json").read_text())
    subset = {}
    for fid, citation in sorted(registry.items()):
        if citation.get("kind") != "derived":
            continue
        try:
            inputs = json.loads(citation.get("inputs") or "null")
        except (TypeError, ValueError):
            continue
        if isinstance(inputs, list) and leaves & {item for item in inputs if isinstance(item, str)}:
            subset[fid] = citation

    shipped = (site_dir / "json" / "f15_funding_history.json").read_bytes()
    for label, existing in (("full registry", registry), ("captured registry subset", subset)):
        rebuilt, _, _ = build_program_matrix(payload, previews, existing_citations=existing, retrieved_at=retrieved_at)
        if _json_bytes(rebuilt) != shipped:
            raise SystemExit(f"capture_f15_fixtures: rebuild with the {label} differs from the shipped history")

    fixture = dict(
        schema=FIXTURE_SCHEMA,
        captured_from=dict(
            site_built_at=retrieved_at,
            history_sha256=_sha256(shipped),
            citations_json_sha256=_sha256((site_dir / "json" / "citations.json").read_bytes()),
        ),
        retrieved_at=retrieved_at,
        source_rows=members,
        series=member_series,
        current_fact_ids=sorted(leaves & current_fact_ids),
        previews=previews,
        registry=subset,
    )
    return fixture, shipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--site-dir", type=Path, default=config.SITE_DIR)
    parser.add_argument("--duckdb", type=Path, default=config.DUCKDB_PATH)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "tests" / "fixtures" / "f15")
    parser.add_argument("--expect-sha256", required=True)
    args = parser.parse_args(argv)

    fixture, shipped = capture(site_dir=args.site_dir, duckdb_path=args.duckdb)
    actual = fixture["captured_from"]["history_sha256"]
    if actual != args.expect_sha256:
        print(f"capture_f15_fixtures: shipped history sha256 {actual} != expected {args.expect_sha256}", file=sys.stderr)
        return 1
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "history.json").write_bytes(shipped)
    (args.out_dir / "history.sha256").write_text(actual + "\n")
    (args.out_dir / "builder_inputs.json.gz").write_bytes(gzip.compress(_json_bytes(fixture), mtime=0))
    print(json.dumps(dict(
        history_sha256=actual, history_bytes=len(shipped), source_rows=len(fixture["source_rows"]),
        series=len(fixture["series"]), previews=len(fixture["previews"]), registry=len(fixture["registry"]),
        current_fact_ids=len(fixture["current_fact_ids"]),
    ), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Capture the fixtures (reads the live lake and export; writes only `tests/fixtures/f15/`)**

Run (from `GovBudget/` in the worktree):

```bash
GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data \
  uv run --project . python scripts/era/capture_f15_fixtures.py \
  --expect-sha256 9f70c770eb7c91e33919fd66e6f316a1461035cdfcfa446a725f063d593c8800
```

Expected (one line; `registry` is the count at the 2026-10-02T01:30:21Z export):

```
{"current_fact_ids": 20, "history_bytes": 138486, "history_sha256": "9f70c770eb7c91e33919fd66e6f316a1461035cdfcfa446a725f063d593c8800", "previews": 207, "registry": 150, "series": 195, "source_rows": 467}
```

The script writes nothing if any proof fails; it then exits with one of its `capture_f15_fixtures: ...` messages, or with `shipped history sha256 <x> != expected 9f70…` (exit 1) if the export moved. A DuckDB `Could not set lock on file` error means another session holds the lake open for writing; wait for it to finish and re-run (the script opens it `read_only=True`).

Then check the pin:

```bash
shasum -a 256 tests/fixtures/f15/history.json && cat tests/fixtures/f15/history.sha256 && wc -c < tests/fixtures/f15/history.json && ls -l tests/fixtures/f15/
```

Expected: `9f70c770eb7c91e33919fd66e6f316a1461035cdfcfa446a725f063d593c8800  tests/fixtures/f15/history.json`, then the same 64 hex characters alone, then `138486`; `builder_inputs.json.gz` is about 146 KB (146,360 bytes when measured).

- [ ] **Step 5: Write the fixture README**

Create `tests/fixtures/f15/README.md`:

```markdown
# F-15 identity fixtures

Spec: `docs/superpowers/specs/2026-10-02-era-procurement-history-design.md` §8 V5,
§9 S0, §6.2, §6.5. Captured once at S0; re-pinned only by the owner-approved F-15
correction (S5).

| File | Content | Written by |
|---|---|---|
| `history.json` | Byte copy of `data/site/json/f15_funding_history.json` at the pin | `scripts/era/capture_f15_fixtures.py` |
| `history.sha256` | Its sha256: 64 lowercase hex characters and a newline. `verify-era-map` leg f compares the live export to it | same |
| `builder_inputs.json.gz` | What `build_history` and `build_program_matrix` read: the F-15 member workbook rows, their `fct_decade_series` rows, the member fact IDs already in `budget_lines`, the 207 workbook-cell previews, and every derived citation with an F-15 workbook leaf among its inputs | same |
| `page_snapshot.json` | Normalized `/families/f-15/` page from a fresh site build at the pin | `site/scripts/f15-page-snapshot.mjs --out` |

`tests/test_f15_era_identity.py` rebuilds the history from `builder_inputs.json.gz`
with no lake and no `data/site`, and fails (never skips) when a file is missing.

## Re-pin (S5 only, after the owner approves the exact F-15 changes)

S5 does not write the live `data/site`. The S5 history is produced on a proof
clone of the S4 export, `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s5/data`
(`site/`, `duckdb/`, `parquet/`; plan Task 22 Step 12). The live export changes
only at the release (plan Task 23). Re-pin from the clone, never from the main lake.

History, sha pin and builder inputs, from `GovBudget/`, once the S5 history diff
check has passed (plan Task 22 Step 14). The `<S5 sha>` is the digest the
first command prints:

    P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs
    shasum -a 256 $P/s5/data/site/json/f15_funding_history.json
    uv run --project . python scripts/era/capture_f15_fixtures.py \
      --site-dir $P/s5/data/site --duckdb $P/s5/data/duckdb/govbudget.duckdb \
      --out-dir tests/fixtures/f15 --expect-sha256 <S5 sha>

Page snapshot, from a fresh build against the same clone. From `GovBudget/`,
point the worktree's lake links at the clone, build, snapshot, then put the
links and the regenerated `llms.txt` back:

    P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs
    for d in site duckdb parquet; do ln -sfn $P/s5/data/$d data/$d; done
    (cd site && NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run build \
      && node scripts/f15-page-snapshot.mjs out/families/f-15/index.html \
           --out ../tests/fixtures/f15/page_snapshot.json)
    for d in site duckdb parquet; do ln -sfn /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/$d data/$d; done
    git checkout -- site/public/llms.txt

Do not set `GOVBUDGET_DATA` to the main lake for a re-pin: its `data/site` keeps
the pre-release export until the release. Never capture from the main checkout's
`site/out` (it can be a stale build).
```

- [ ] **Step 6: Run the identity tests and the existing F-15 tests**

```bash
uv run --project . pytest tests/test_f15_era_identity.py tests/test_f15_funding_history.py -q
```

Expected: `34 passed` (4 new, 30 existing).

- [ ] **Step 7: Prove the fresh-state test is what catches a widened allow-list (then revert)**

Confirm the builder is clean first:

```bash
git diff --quiet -- src/govbudget/f15_funding_history.py && echo clean
```

Expected: `clean`.

Temporarily edit `src/govbudget/f15_funding_history.py:275-278`. Before:

```python
                    allowed.extend([
                        f"sum(budget_lines.amount_thousands where amount_type={amount_type} and edition={edition})",
                        f"sum(budget_lines.amount_thousands where amount_type={amount_type})",
                    ])
```

After (one line added):

```python
                    allowed.extend([
                        f"sum(budget_lines.amount_thousands where amount_type={amount_type} and edition={edition})",
                        f"sum(budget_lines.amount_thousands where amount_type={amount_type})",
                        f"sum(budget_lines.amount_thousands where era_line_map='{program['code']}' and amount_type={amount_type} and edition={edition})",
                    ])
```

Run:

```bash
uv run --project . pytest tests/test_f15_era_identity.py -q
```

Expected: `1 failed, 3 passed`; the failure is `test_fresh_state_with_decade_era_map_receipts_keeps_every_byte` with an `AssertionError` on the byte comparison (measured: first difference at byte 11226).

Revert and confirm:

```bash
git checkout -- src/govbudget/f15_funding_history.py && git diff --quiet -- src/govbudget/f15_funding_history.py && echo clean && uv run --project . pytest tests/test_f15_era_identity.py -q
```

Expected: `clean`, then `4 passed`.

- [ ] **Step 8: Commit the Python fixtures and tests**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/tests/test_f15_era_identity.py GovBudget/scripts/era/capture_f15_fixtures.py GovBudget/tests/fixtures/f15/history.json GovBudget/tests/fixtures/f15/history.sha256 GovBudget/tests/fixtures/f15/builder_inputs.json.gz GovBudget/tests/fixtures/f15/README.md && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "test(f15): hermetic F-15 identity fixtures, sha pin and V5 golden/fresh-state/sensitivity tests (S0)" -m "Pins json/f15_funding_history.json at 9f70c770 (138,486 B) from the 2026-10-02T01:30:21Z export. The fixtures hold what build_history/build_program_matrix read (467 member rows, 195 series rows, 207 previews, 150 derived citations touching F-15 leaves), so the tests need no lake and fail when a fixture is missing." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: one commit with 6 files changed.

- [ ] **Step 9: Write the failing page-snapshot tests**

Create `site/scripts/gates/__tests__/f15-page-snapshot.test.mjs`:

```js
/**
 * f15-page-snapshot.mjs — the normalized /families/f-15/ snapshot that proves
 * the F-15 page does not change while era procurement history lands
 * (spec 2026-10-02-era-procurement-history-design.md §6.2, §9 S0).
 *
 * Fixture HTML only — no build. The markup mirrors
 * src/components/family-funding-history.tsx (section[data-family-history],
 * th[data-history-column], td[data-history-annual], tr[data-history-program],
 * td[data-history-cell] with data-history-inputs, data-history-missing) and a
 * Flight payload string the way Next serializes record facts.
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { describe, it, expect } from "vitest";
import { snapshotF15Page, firstDifference } from "../../f15-page-snapshot.mjs";

const BASELINE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../../tests/fixtures/f15/page_snapshot.json");
// f15_funding_history.py PROGRAMS, in row order.
const PROGRAM_IDS = [
  "R-1:3600F:AF:0207134F", "R-1:3600F:AF:0207146F", "R-1:3600F:AF:0207171F",
  "P-1:3010F:AF:F01500", "P-1:3010F:AF:F015EX", "P-1:3010F:AF:F15EWS",
  "P-1:3010F:AF:F0150P", "P-1:3010F:AF:F015E0",
];

const A = "a0231f5a75a7ad52";
const B = "28f53c8d681494cc";
const C = "cce72b42a96bfcb7";
const T = "e2a8baadbe15c1e5";
const R = "3bd9c921b2397209";

const PAGE = `<!DOCTYPE html><html><body>
<div data-entity="family:f-15"></div>
<section class="x__overview" data-family-history="f-15">
  <span data-fact-id="${T}" data-dataset="f15_funding_history" data-entity="family:f-15" style="flex-grow:0.6682583630407969">$771.1M</span>
  <table><thead><tr><th>Program / budget line</th>
    <th scope="col" data-history-column="fy2015a">FY2015</th><th scope="col" data-history-column="fy2016a">FY2016</th></tr></thead>
  <tbody>
    <tr><th scope="row">F-15 family total</th>
      <td data-history-annual="fy2015a"><span data-fact-id="${T}" data-dataset="f15_funding_history">$771.1M</span></td>
      <td data-history-annual="fy2016a"><span data-fact-id="${A}" data-dataset="f15_funding_history">$984.6M</span><span>Partial</span></td></tr>
    <tr data-history-program="P-1:3010F:AF:F01500"><th scope="row"><span class="x__programCode">BLI<!-- --> <!-- -->F01500</span><a href="/program/F01500/">F-15</a><span class="x__rowMeta">Procurement</span></th>
      <td data-history-cell="fy2015a" data-history-inputs="${R}"><span data-fact-id="${R}" data-dataset="budget_lines_decade">$498.3M</span></td>
      <td data-history-cell="fy2016a" data-history-inputs="${B},${C}"><span data-fact-id="${A}" data-dataset="f15_funding_history">$596.9M</span></td></tr>
    <tr data-history-program="P-1:3010F:AF:F015E0"><th scope="row"><span>BLI F015E0</span><span>F-15e (legacy line)</span><span>Procurement · Historical code</span></th>
      <td data-history-cell="fy2015a"><span data-history-missing="F015E0">Missing</span></td>
      <td data-history-cell="fy2016a"><span>—</span></td></tr>
  </tbody></table>
</section>
<script>self.__next_f.push([1,"{\\"factId\\":\\"${B}\\",\\"entity\\":\\"family:f-15\\"}"])</script>
</body></html>`;

describe("snapshotF15Page", () => {
  it("reduces the page to fact ids, datasets, entity count and the matrix", () => {
    const snap = snapshotF15Page(PAGE);
    expect(snap.schema).toBe(1);
    expect(snap.page).toBe("/families/f-15/");
    expect(snap.data_fact_id_elements).toBe(5);
    expect(snap.data_fact_ids).toEqual([R, A, T].sort());
    expect(snap.data_dataset_counts).toEqual({ budget_lines_decade: 1, f15_funding_history: 4 });
    expect(snap.family_f15_occurrences).toBe(3);
    // B and C appear only in data-history-inputs / the Flight payload; the
    // style fraction "0.6682583630407969" is not a fact id.
    expect(snap.page_fact_ids).toEqual([A, B, C, R, T].sort());
    expect(snap.page_fact_id_occurrences).toBe(9);
    expect(snap.matrix.columns).toEqual(["fy2015a", "fy2016a"]);
    expect(snap.matrix.annual).toEqual([
      { column: "fy2015a", fact_id: T, dataset: "f15_funding_history", text: "$771.1M", inputs: [], missing: null },
      { column: "fy2016a", fact_id: A, dataset: "f15_funding_history", text: "$984.6M", inputs: [], missing: null },
    ]);
    expect(snap.matrix.rows).toEqual([
      {
        program_id: "P-1:3010F:AF:F01500",
        label: ["BLI F01500", "F-15", "Procurement"],
        cells: [
          { column: "fy2015a", fact_id: R, dataset: "budget_lines_decade", text: "$498.3M", inputs: [R], missing: null },
          { column: "fy2016a", fact_id: A, dataset: "f15_funding_history", text: "$596.9M", inputs: [B, C], missing: null },
        ],
      },
      {
        program_id: "P-1:3010F:AF:F015E0",
        label: ["BLI F015E0", "F-15e (legacy line)", "Procurement · Historical code"],
        cells: [
          { column: "fy2015a", fact_id: null, dataset: null, text: "Missing", inputs: [], missing: "F015E0" },
          { column: "fy2016a", fact_id: null, dataset: null, text: "—", inputs: [], missing: null },
        ],
      },
    ]);
  });

  it("sees a fact that leaks only into the Flight payload", () => {
    const leaked = PAGE.replace("</body>", `<script>self.__next_f.push([1,"{\\"factId\\":\\"0123456789abcdef\\"}"])</script></body>`);
    const diff = firstDifference(snapshotF15Page(PAGE), snapshotF15Page(leaked));
    expect(diff).toMatch(/^\$\.page_fact_id_occurrences: 9 != 10$/);
  });

  it("refuses a page without the F-15 funding section", () => {
    expect(() => snapshotF15Page("<html><body></body></html>")).toThrow(/no section\[data-family-history="f-15"\]/);
  });
});

describe("firstDifference", () => {
  it("is null for equal snapshots and names the first differing path otherwise", () => {
    const snap = snapshotF15Page(PAGE);
    expect(firstDifference(snap, JSON.parse(JSON.stringify(snap)))).toBeNull();
    const relabeled = snapshotF15Page(PAGE.replace("F-15e (legacy line)", "F-15e (FY2020 F-15EX Lot 1 aircraft)"));
    expect(firstDifference(snap, relabeled)).toBe(
      '$.matrix.rows[1].label[1]: "F-15e (legacy line)" != "F-15e (FY2020 F-15EX Lot 1 aircraft)"');
  });
});

describe("committed S0 baseline (tests/fixtures/f15/page_snapshot.json)", () => {
  it("is present and well-formed", () => {
    expect(fs.existsSync(BASELINE), `missing ${BASELINE}: capture it from a fresh build (Task 4)`).toBe(true);
    const snap = JSON.parse(fs.readFileSync(BASELINE, "utf8"));
    expect(snap.schema).toBe(1);
    expect(snap.page).toBe("/families/f-15/");
    expect(snap.matrix.rows.map((row) => row.program_id)).toEqual(PROGRAM_IDS);
    expect(snap.matrix.columns).toHaveLength(12);
    expect(snap.matrix.annual.map((cell) => cell.column)).toEqual(snap.matrix.columns);
    for (const row of snap.matrix.rows) expect(row.cells.map((cell) => cell.column)).toEqual(snap.matrix.columns);
    expect(snap.data_fact_ids.length).toBeGreaterThan(0);
    for (const id of snap.page_fact_ids) expect(id).toMatch(/^[0-9a-f]{16}$/);
    expect(snap.data_fact_ids.filter((id) => !snap.page_fact_ids.includes(id))).toEqual([]);
  });
});
```

- [ ] **Step 10: Run them and watch them fail**

Run (from `GovBudget/site`):

```bash
npx vitest run scripts/gates/__tests__/f15-page-snapshot.test.mjs
```

Expected: `Test Files  1 failed (1)` with `Error: Cannot find module '../../f15-page-snapshot.mjs' imported from '.../scripts/gates/__tests__/f15-page-snapshot.test.mjs'`.

- [ ] **Step 11: Write the snapshot tool**

Create `site/scripts/f15-page-snapshot.mjs`:

```js
#!/usr/bin/env node
/**
 * f15-page-snapshot.mjs — normalized snapshot of the built /families/f-15/ page.
 *
 * Spec 2026-10-02-era-procurement-history-design.md §6.2: the F-15 page must
 * not change while procurement history before FY2024 lands (S0–S4). A raw
 * HTML diff is useless for that proof — chunk names, CSS-module hashes and
 * the build id change with any code change anywhere — so this reduces the
 * page to what a reader and a citation check can see:
 *
 *   - every element carrying data-fact-id (count + distinct ids),
 *   - data-dataset counts,
 *   - occurrences of the family entity string "family:f-15",
 *   - every 16-hex fact-id token anywhere in the HTML, including the RSC
 *     (Flight) payload — the F-15 browser's records ship there, so an era
 *     fact leaking into loadRecord shows up here even when it is not in the
 *     initially rendered DOM,
 *   - the funding matrix: columns, the annual total row, and each program
 *     row's label and cells (fact id, display text, inputs, missing marker).
 *
 * Usage (from GovBudget/site):
 *   node scripts/f15-page-snapshot.mjs out/families/f-15/index.html
 *   node scripts/f15-page-snapshot.mjs out/families/f-15/index.html --out ../tests/fixtures/f15/page_snapshot.json
 *   node scripts/f15-page-snapshot.mjs out/families/f-15/index.html --check ../tests/fixtures/f15/page_snapshot.json
 *
 * --check exits 1 and names the first differing path when the snapshot of
 * the page differs from the committed baseline.
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { parse } from "node-html-parser";

export const SNAPSHOT_SCHEMA = 1;

// A fact id is 16 lowercase hex characters. Decimal fractions in inline
// styles ("0.6682583630407969") are excluded by the "." look-behind.
const FACT_TOKEN_RE = /(?<![0-9A-Za-z.])[0-9a-f]{16}(?![0-9A-Za-z])/g;

const attr = (el, name) => el?.getAttribute(name) ?? null;

function sortedCounts(values) {
  const counts = {};
  for (const value of values) counts[value] = (counts[value] ?? 0) + 1;
  return Object.fromEntries(Object.entries(counts).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)));
}

function cellOf(td, columnAttr) {
  const figure = td.querySelector("[data-fact-id]");
  const inputs = attr(td, "data-history-inputs");
  return {
    column: attr(td, columnAttr),
    fact_id: attr(figure, "data-fact-id"),
    dataset: attr(figure, "data-dataset"),
    text: figure ? figure.text.trim() : td.text.trim(),
    inputs: inputs ? inputs.split(",") : [],
    missing: attr(td.querySelector("[data-history-missing]"), "data-history-missing"),
  };
}

/** Reduce a built /families/f-15/ HTML document to its normalized snapshot. */
export function snapshotF15Page(html) {
  const root = parse(html);
  const section = root.querySelector('section[data-family-history="f-15"]');
  if (!section) throw new Error('f15-page-snapshot: no section[data-family-history="f-15"] in the page');
  const factElements = root.querySelectorAll("[data-fact-id]");
  const tokens = html.match(FACT_TOKEN_RE) ?? [];
  const rows = section.querySelectorAll("tr[data-history-program]").map((tr) => ({
    program_id: attr(tr, "data-history-program"),
    label: tr.querySelector("th").childNodes.filter((node) => node.nodeType === 1).map((node) => node.text.trim()),
    cells: tr.querySelectorAll("td[data-history-cell]").map((td) => cellOf(td, "data-history-cell")),
  }));
  if (rows.length === 0) throw new Error("f15-page-snapshot: the funding matrix has no program rows");
  return {
    schema: SNAPSHOT_SCHEMA,
    page: "/families/f-15/",
    data_fact_id_elements: factElements.length,
    data_fact_ids: [...new Set(factElements.map((el) => attr(el, "data-fact-id")))].sort(),
    data_dataset_counts: sortedCounts(root.querySelectorAll("[data-dataset]").map((el) => attr(el, "data-dataset"))),
    family_f15_occurrences: html.split("family:f-15").length - 1,
    page_fact_id_occurrences: tokens.length,
    page_fact_ids: [...new Set(tokens)].sort(),
    matrix: {
      columns: section.querySelectorAll("th[data-history-column]").map((th) => attr(th, "data-history-column")),
      annual: section.querySelectorAll("td[data-history-annual]").map((td) => cellOf(td, "data-history-annual")),
      rows,
    },
  };
}

/** First path at which two JSON values differ, or null when they are equal. */
export function firstDifference(a, b, at = "$") {
  if (Object.is(a, b)) return null;
  if (typeof a !== typeof b || a === null || b === null || typeof a !== "object" || Array.isArray(a) !== Array.isArray(b)) {
    return `${at}: ${JSON.stringify(a)} != ${JSON.stringify(b)}`;
  }
  const keys = Array.isArray(a)
    ? [...Array(Math.max(a.length, b.length)).keys()]
    : [...new Set([...Object.keys(a), ...Object.keys(b)])].sort();
  for (const key of keys) {
    const found = firstDifference(a[key], b[key], Array.isArray(a) ? `${at}[${key}]` : `${at}.${key}`);
    if (found) return found;
  }
  return null;
}

function main(argv) {
  const [input, flag, target] = argv;
  if (!input || (flag && !["--out", "--check"].includes(flag)) || (flag && !target)) {
    console.error("usage: node scripts/f15-page-snapshot.mjs <index.html> [--out FILE | --check FILE]");
    return 2;
  }
  const snapshot = snapshotF15Page(fs.readFileSync(input, "utf8"));
  const text = JSON.stringify(snapshot, null, 2) + "\n";
  if (flag === "--out") {
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, text);
    console.log(`f15-page-snapshot: wrote ${target} (${snapshot.data_fact_id_elements} data-fact-id elements, ${snapshot.page_fact_ids.length} distinct page fact ids, ${snapshot.matrix.rows.length} matrix rows)`);
    return 0;
  }
  if (flag === "--check") {
    const diff = firstDifference(JSON.parse(fs.readFileSync(target, "utf8")), snapshot);
    if (diff) {
      console.error(`f15-page-snapshot: FAIL — differs from ${target} at ${diff}`);
      return 1;
    }
    console.log(`f15-page-snapshot: PASS — equal to ${target}`);
    return 0;
  }
  process.stdout.write(text);
  return 0;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exit(main(process.argv.slice(2)));
}
```

- [ ] **Step 12: Run the tests: the tool passes, the baseline is still missing**

Run (from `GovBudget/site`):

```bash
npx vitest run scripts/gates/__tests__/f15-page-snapshot.test.mjs
```

Expected: `Tests  1 failed | 4 passed (5)`; the failure is `committed S0 baseline (tests/fixtures/f15/page_snapshot.json) > is present and well-formed` with `missing .../tests/fixtures/f15/page_snapshot.json: capture it from a fresh build (Task 4): expected false to be true`.

- [ ] **Step 13: Give the worktree a `data/site` for the build, and check that the build will read the S0 export**

The build reads `site/../data/site` (CONTRACT ISSUE 1). Run (from `GovBudget/` in the worktree):

```bash
[ -e data/site ] || ln -s /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site data/site
git check-ignore -q data/site || echo 'GovBudget/data/site' >> "$(git rev-parse --path-format=absolute --git-common-dir)/info/exclude"
ls -ld data/site && git check-ignore -v data/site && git status --short -- data/ && git diff --stat 10fb4585 HEAD -- site/
```

Expected: `data/site -> /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site` (or the link Task 1 already placed there); then `/Users/andeslee/Documents/Cursor-Projects/.git/info/exclude:26:GovBudget/data/site	data/site` (the shared exclude already lists it, measured 2026-10-02); then no `git status` output and no `git diff` output (no site code has changed since the base commit `10fb4585`, whose `site/` equals the deployed `aa714d7f`).

Then confirm the export is the one the Python fixtures were captured from:

```bash
uv run --project . python -c "import gzip,hashlib,json; d=json.load(gzip.open('tests/fixtures/f15/builder_inputs.json.gz','rt')); c=hashlib.sha256(open('data/site/json/citations.json','rb').read()).hexdigest(); h=hashlib.sha256(open('data/site/json/f15_funding_history.json','rb').read()).hexdigest(); print(c == d['captured_from']['citations_json_sha256'], h == open('tests/fixtures/f15/history.sha256').read().strip(), json.load(open('data/site/json/site_meta.json'))['built_at'])"
```

Expected: `True True 2026-10-02T01:30:21.066005+00:00`. Anything else means the export moved after Step 4: re-run Step 4 (the F-15 sha must still be `9f70c770…`, or the capture refuses) and Step 6, commit the re-captured `builder_inputs.json.gz` with the Step 8 command and message `test(f15): re-capture F-15 builder inputs from the current export`, then repeat this check before building.

- [ ] **Step 14: Fresh production build of the site in the worktree**

Run (from `GovBudget/site`; a full production build takes tens of minutes):

```bash
NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run build && node -e "const m=require('./out/.build-meta.json'); console.log(m.git_head)" && git rev-parse HEAD && ls -l out/families/f-15/index.html
```

Expected: exit 0 (prebuild prints `✓  site_meta.json OK (schema_version=1, built_at=2026-10-02T01:30:21.066005+00:00)` and `✓  f15_funding_history.json → public/json/`; postbuild runs pagefind), the two SHA lines are identical, and `out/families/f-15/index.html` exists (the live page it should match is 701,363 bytes).

Then re-run the Step 13 export check command (from `GovBudget/`); expected again `True True 2026-10-02T01:30:21.066005+00:00` (the export did not move during the build). And, from `GovBudget/site`:

```bash
git status --short -- .
```

Expected exactly the two files this task has not committed yet:

```
?? scripts/f15-page-snapshot.mjs
?? scripts/gates/__tests__/f15-page-snapshot.test.mjs
```

In particular `public/llms.txt` is not modified: it regenerates to the committed text because the export still has 125,409 citations.

- [ ] **Step 15: Capture the S0 page baseline from the fresh build**

Run (from `GovBudget/site`):

```bash
node scripts/f15-page-snapshot.mjs out/families/f-15/index.html --out ../tests/fixtures/f15/page_snapshot.json
```

Expected: `f15-page-snapshot: wrote ../tests/fixtures/f15/page_snapshot.json (107 data-fact-id elements, 223 distinct page fact ids, 8 matrix rows)`.

Sanity check against the live page (one command, so the temp path survives):

```bash
LIVE="$(mktemp -d)/live-f15.html" && curl -sfL https://fiscalreceipts.com/families/f-15/ -o "$LIVE" && node scripts/f15-page-snapshot.mjs "$LIVE" --check ../tests/fixtures/f15/page_snapshot.json
```

Expected: `f15-page-snapshot: PASS — equal to ../tests/fixtures/f15/page_snapshot.json`. A FAIL means the fresh build and production disagree about the F-15 page (a redeploy or re-export since 2026-10-02); do not commit — report the printed path and stop.

- [ ] **Step 16: Run the page-snapshot tests and lint**

Run (from `GovBudget/site`):

```bash
npx vitest run scripts/gates/__tests__/f15-page-snapshot.test.mjs && npx eslint scripts/f15-page-snapshot.mjs scripts/gates/__tests__/f15-page-snapshot.test.mjs
```

Expected: `Tests  5 passed (5)`, then eslint exits 0 with no errors.

- [ ] **Step 17: Commit the snapshot tool, its tests and the S0 baseline**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/site/scripts/f15-page-snapshot.mjs GovBudget/site/scripts/gates/__tests__/f15-page-snapshot.test.mjs GovBudget/tests/fixtures/f15/page_snapshot.json && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "test(f15): normalized /families/f-15/ page snapshot tool and the S0 baseline from a fresh build" -m "Built in the worktree at the base site code over the 2026-10-02T01:30:21Z export (f15 history 9f70c770); never from the main checkout's site/out. Baseline: 107 data-fact-id elements (92 distinct), 223 page fact ids, 8 matrix rows x 12 columns; equal to the live page." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: one commit with 3 files changed. `git status --short` from `GovBudget/` shows nothing from this task (the `data/site` link is excluded).
