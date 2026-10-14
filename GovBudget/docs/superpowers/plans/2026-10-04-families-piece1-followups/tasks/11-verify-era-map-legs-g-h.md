<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; the approved design is ../../../specs/2026-10-04-families-piece1-followups-design.md. -->

### Task 11: verify-era-map legs g (era minters) and h (era book diffs) (#206 T11)

**Spec:** design §5.4 (T11: `LEGS` "abcdef" → "abcdefgh" with the `cli.py` default, help text and docstrings; leg g
— same_program rows have a page for `program_key` and a citation carrying `program_key`, F-15 roster rows a citation
with no `pe_bli`, era workbook citations = era decade fact IDs, live 17,502 = 17,481 + 21; leg h — every sidecar
`book_diff` resolved recursively to its `budget_lines_decade` leaves, failing when `from_edition ≤ 2023` and a leaf is
P-1/P-1R, live 1,044 R-1 era diffs and 0 procurement; the four planted failures); design §4.5 (the 0390DOM alias is
why leg g compares `program_key`, not `line_item_code`); ROADMAP #206 T11 (the two claims: the `p1_era_line_map` scope
sentence and /methodology/'s "book diffs for the era editions cover RDT&E only"); §7 W3.

**Files:**
- Modify: `src/govbudget/verify_era_map.py` (docstring after leg (f) :47-51; `import json`; `LEGS`/`LEG_NAMES` :63-67;
  legs g and h inserted before `run_verify_era_map` :484, whose default becomes "abcdefgh"; the dispatch's
  `else:  # f` :514)
- Modify: `src/govbudget/cli.py` (the `verify-era-map` parser, :3343-3351)
- Modify: `src/govbudget/verify_phase5.py` (module docstring, :35-40)
- Create: `tests/test_verify_era_map_gh.py`
- Modify: `tests/test_verify_era_map.py` (`import json`; `LEG_LINES` and `_publish_export`; the zero-argument FAIL test)
- Modify: `tests/test_verify_era_map_def.py` (leg f's failure line, pinned in `test_f_fails_when_the_history_changed` :270-272 and `test_format_report_prints_legs_d_to_f` :332-333)
- Also in `src/govbudget/verify_era_map.py`: leg f's docstring paragraph and its failure message (:479-480 at HEAD), which name only "the S5 correction" although Task 21g re-pins the history for the T9 gloss (O-4, G3-C11; it must land before Task 21's B, G5-12)

Line numbers are hints measured at `532205c9` (anchor on the quoted text; 9a–9c moved them).

**Interfaces:**
Consumes: Tasks 9a–9c's `verify_era_map.py` (`_leg`, `ERA_P1_WORKBOOK_SHA256`, `_ERA_P1_LAST_EDITION`, `Counter`,
`Mapping`; the dispatch with `else:  # f`) and `tests/test_verify_era_map.py` (`Corpus`, `pinned`, the `dataclasses`
import Task 9c added); the export layout under `config.SITE_DIR`: `data/budget_lines_decade.parquet` (`fact_id,
exhibit, fiscal_year, pe_bli, document_sha256`), `data/p1_era_line_map.parquet` (`edition, era_key,
line_item_code, decision, program_key, program_account, program_org`), `citations/citations.parquet` (`fact_id,
kind, sha256, pe_bli, inputs` — `inputs` a JSON list of fact IDs on derived rows), `json/programs.json` (`pe_bli,
slug, account, org`: a split code's page is the row whose (`pe_bli`, `account`, `org`) equals the map's
(`program_key`, `program_account`, `program_org`), e.g. ('20', '0300D', 'DCSA') → `20-DCSA`), `json/program_details/<slug>.json`
(one per program page, `book_diff` a dict with `fid` and `from_edition`, or null); `f15_funding_history.ERA_MEMBERS`,
`ERA_PROGRAM_CODES`; `era_keys.is_era_procurement_key`.
Produces: `leg_g_era_minters(*, site_dir: Path, workbooks: Mapping[int, str]) -> dict` and
`leg_h_era_book_diffs(*, site_dir: Path) -> dict`, each returning `_leg(ok, summary, failures)`; `LEGS` = a–h,
`LEG_NAMES["g"] = "era minters"`, `LEG_NAMES["h"] = "era book diffs"`; `run_verify_era_map(..., legs="abcdefgh")`;
`govbudget verify-era-map` with no arguments prints eight leg lines. `verify-phase5`'s assembly runs it with no
arguments, so it gets g and h with no change to `_ASSEMBLY_PHASES`. After the release export the expected leg g
summary grows by 0390DOM's era rows (B7, Task 10); Task 21's P1 measures them.

Verified now (read-only, 2026-10-13, on the live `data/site` built 2026-10-04, by a scratch copy of the code below):
leg g `era_rows=17502 same_program=17481 f15_roster=21 era_workbook_citations=17502 failures=0`; leg h
`era_diffs=1044 r1=1044 procurement=0 failures=0`. The 21 roster rows are the 7 history_only F0150P/F015E0 keys × 3
amount columns; every same_program row's page resolves, the 118 + 67 collision-code rows through `programs.json`.
Both legs read only the export, never the warehouse, so they run against today's `data/site` even before Task 22's
build (legs a–c cannot until then: Task 9a).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_verify_era_map_gh.py`:

```python
"""verify-era-map legs g and h (families piece-1 follow-ups, design §5.4; ROADMAP #206 T11).

(g) era minters: every PB2017–PB2023 P-1 row of the exported
    budget_lines_decade is either a same_program line whose program_key has a
    program page (the collision split's page for a pinned code) and whose
    workbook citation carries that program_key as pe_bli, or an F-15 roster
    line (ERA_MEMBERS x ERA_PROGRAM_CODES) whose citation carries no pe_bli;
    and the era P-1 workbook citations are exactly the era rows' fact ids.
(h) era book diffs: every program sidecar book_diff from an era edition
    (from_edition <= 2023) resolves, through the derived citations' inputs, to
    budget_lines_decade leaves none of which is a P-1 or P-1R row.
Each leg is shown to pass on a consistent fixture export and to fail on the
defect it exists for. Nothing reads the shared lake.
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

from govbudget.verify_era_map import leg_g_era_minters, leg_h_era_book_diffs

WORKBOOKS = {2019: "1" * 64, 2020: "2" * 64}
R1_SHA = "3" * 64
P1_2026_SHA = "4" * 64

S1, S2, F1 = "a1" * 8, "a2" * 8, "f1" * 8          # era P-1 leaves
R1, R2, M1 = "b1" * 8, "b2" * 8, "c1" * 8          # R-1 2019 / R-1 2024 / P-1 2026
D_ERA, D_MODERN = "d1" * 8, "d2" * 8               # derived book-diff sums

# (fact_id, exhibit, fiscal_year, pe_bli, document_sha256)
DECADE = [
    (S1, "P-1", 2019, "3010F-AF-L30", WORKBOOKS[2019]),
    (S2, "P-1", 2019, "0300D-DSS-L21", WORKBOOKS[2019]),
    (F1, "P-1", 2020, "3010F-AF-L3", WORKBOOKS[2020]),
    (R1, "R-1", 2019, "0207134F", R1_SHA),
    (R2, "R-1", 2024, "0207134F", R1_SHA),
    (M1, "P-1", 2026, "F15EWS", P1_2026_SHA),
]
# (edition, era_key, line_item_code, decision, program_key, program_account, program_org)
MAP = [
    (2019, "3010F-AF-L30", "F15EWS", "same_program", "F15EWS", None, None),
    (2019, "0300D-DSS-L21", "20", "same_program", "20", "0300D", "DCSA"),
    (2020, "3010F-AF-L3", "F015E0", "history_only", "F015E0", None, None),
]
# (fact_id, kind, sha256, pe_bli, inputs)
CITATIONS = [
    (S1, "workbook", WORKBOOKS[2019], "F15EWS", None),
    (S2, "workbook", WORKBOOKS[2019], "20", None),
    (F1, "workbook", WORKBOOKS[2020], None, None),
    (R1, "workbook", R1_SHA, "0207134F", None),
    (R2, "workbook", R1_SHA, "0207134F", None),
    (M1, "workbook", P1_2026_SHA, "F15EWS", None),
    (D_ERA, "derived", None, None, json.dumps([R1, R2])),
    (D_MODERN, "derived", None, None, json.dumps([M1])),
]
SIDECARS = {
    "F15EWS": {"book_diff": {"fid": D_MODERN, "from_edition": 2024, "to_edition": 2026}},
    "20-DCSA": {"book_diff": None},
    "0207134F": {"book_diff": {"fid": D_ERA, "from_edition": 2019, "to_edition": 2024}},
}
PROGRAMS = [{"pe_bli": "20", "slug": "20-DCSA", "account": "0300D", "org": "DCSA"},
            {"pe_bli": "F15EWS", "slug": "F15EWS", "account": "3010F", "org": "AF"}]


def _parquet(path: Path, ddl: str, rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"create table t ({ddl})")
    if rows:
        con.executemany(f"insert into t values ({', '.join('?' * len(rows[0]))})", rows)
    con.execute(f"copy t to '{path}' (format parquet)")
    con.close()


def _export(site: Path, *, decade=DECADE, era_map=MAP, citations=CITATIONS,
            sidecars=SIDECARS, programs=PROGRAMS) -> Path:
    _parquet(site / "data" / "budget_lines_decade.parquet",
             "fact_id varchar, exhibit varchar, fiscal_year integer, pe_bli varchar,"
             " document_sha256 varchar", list(decade))
    _parquet(site / "data" / "p1_era_line_map.parquet",
             "edition integer, era_key varchar, line_item_code varchar, decision varchar,"
             " program_key varchar, program_account varchar, program_org varchar", list(era_map))
    _parquet(site / "citations" / "citations.parquet",
             "fact_id varchar, kind varchar, sha256 varchar, pe_bli varchar, inputs varchar",
             list(citations))
    details = site / "json" / "program_details"
    details.mkdir(parents=True, exist_ok=True)
    for slug, body in sidecars.items():
        (details / f"{slug}.json").write_text(json.dumps(body))
    (site / "json" / "programs.json").write_text(json.dumps(programs))
    return site


def _g(site: Path) -> dict:
    return leg_g_era_minters(site_dir=site, workbooks=WORKBOOKS)


def _failures(result: dict) -> list[str]:
    return result["detail"]["failures"]


def _replace(rows, index, **changes):
    """rows with rows[index]'s named fields replaced (field order as in the DDL)."""
    names = {
        len(MAP[0]): ("edition", "era_key", "line_item_code", "decision", "program_key",
                      "program_account", "program_org"),
        len(CITATIONS[0]): ("fact_id", "kind", "sha256", "pe_bli", "inputs"),
    }[len(rows[index])]
    row = dict(zip(names, rows[index]))
    row.update(changes)
    return [*rows[:index], tuple(row[n] for n in names), *rows[index + 1:]]


# --- leg g -----------------------------------------------------------------

def test_g_passes_on_a_consistent_export(tmp_path):
    result = _g(_export(tmp_path))
    assert result["ok"] is True, _failures(result)
    assert result["detail"]["summary"] == (
        "era_rows=3 same_program=2 f15_roster=1 era_workbook_citations=3 failures=0")


def test_g_fails_on_a_row_minted_for_an_excluded_line(tmp_path):
    result = _g(_export(tmp_path, era_map=_replace(MAP, 1, decision="exclude_reused_code",
                                                   program_key=None, program_account=None,
                                                   program_org=None)))
    assert _failures(result) == [
        f"{S2} (2019/0300D-DSS-L21): a exclude_reused_code line (20) that is neither"
        " same_program nor on the F-15 roster minted a decade row"]


def test_g_fails_on_a_history_only_row_off_the_f15_roster(tmp_path):
    result = _g(_export(tmp_path, era_map=_replace(MAP, 1, decision="history_only")))
    assert _failures(result) == [
        f"{S2} (2019/0300D-DSS-L21): a history_only line (20) that is neither"
        " same_program nor on the F-15 roster minted a decade row"]


def test_g_fails_on_a_same_program_row_with_no_page(tmp_path):
    sidecars = {k: v for k, v in SIDECARS.items() if k != "F15EWS"}
    result = _g(_export(tmp_path, sidecars=sidecars))
    assert _failures(result) == [
        f"{S1} (2019/3010F-AF-L30): same_program line F15EWS has no program page"
        " (F15EWS, None, None)"]


def test_g_resolves_a_pinned_collision_code_to_its_split_page(tmp_path):
    sidecars = {k: v for k, v in SIDECARS.items() if k != "20-DCSA"}
    result = _g(_export(tmp_path, sidecars={**sidecars, "20": {"book_diff": None}}))
    assert _failures(result) == [
        f"{S2} (2019/0300D-DSS-L21): same_program line 20 has no program page"
        " (20, 0300D, DCSA)"]


def test_g_fails_when_a_citation_does_not_carry_the_program_key(tmp_path):
    result = _g(_export(tmp_path, citations=_replace(CITATIONS, 0, pe_bli="3010F-AF-L30")))
    assert _failures(result) == [
        f"{S1} (2019/3010F-AF-L30): citation pe_bli '3010F-AF-L30' != program_key 'F15EWS'"]


def test_g_fails_when_an_f15_roster_citation_claims_a_pe_bli(tmp_path):
    result = _g(_export(tmp_path, citations=_replace(CITATIONS, 2, pe_bli="F015E0")))
    assert _failures(result) == [
        f"{F1} (2020/3010F-AF-L3): F-15 roster line F015E0 (history_only) cites pe_bli 'F015E0'"]


def test_g_fails_when_a_row_cites_another_workbook(tmp_path):
    result = _g(_export(tmp_path, citations=_replace(CITATIONS, 0, sha256=R1_SHA)))
    assert f"{S1}: an era budget_lines_decade row with no era P-1 workbook citation" in _failures(result)
    assert (f"{S1} (2019/3010F-AF-L30): citation is workbook/{R1_SHA[:12]}, not the PB2019"
            " era P-1 workbook") in _failures(result)


def test_g_fails_on_an_era_workbook_citation_without_its_row(tmp_path):
    orphan = "e0" * 8
    result = _g(_export(tmp_path, citations=[*CITATIONS,
                                             (orphan, "workbook", WORKBOOKS[2019], "F15EWS", None)]))
    assert _failures(result) == [
        f"{orphan}: an era P-1 workbook citation with no era budget_lines_decade row"]


def test_g_fails_on_an_era_row_the_map_does_not_know(tmp_path):
    result = _g(_export(tmp_path, era_map=MAP[1:]))
    assert f"{S1} (2019/3010F-AF-L30): no p1_era_line_map row" in _failures(result)


def test_g_fails_vacuously_without_an_era_row(tmp_path):
    result = _g(_export(tmp_path, decade=DECADE[3:], citations=CITATIONS[3:]))
    assert _failures(result) == ["no era P-1 row in budget_lines_decade: the leg would pass vacuously"]


def test_g_fails_without_the_export(tmp_path):
    result = _g(tmp_path)
    assert result["ok"] is False
    assert result["detail"]["summary"] == "export incomplete"
    assert f"missing {tmp_path / 'data' / 'budget_lines_decade.parquet'}" in _failures(result)


# --- leg h -----------------------------------------------------------------

def test_h_passes_when_era_diffs_sum_rdte_only(tmp_path):
    result = leg_h_era_book_diffs(site_dir=_export(tmp_path))
    assert result["ok"] is True, _failures(result)
    assert result["detail"]["summary"] == "era_diffs=1 r1=1 procurement=0 failures=0"


def test_h_fails_on_a_p1_diff_from_pb2023(tmp_path):
    d_p1 = "d3" * 8
    result = leg_h_era_book_diffs(site_dir=_export(
        tmp_path,
        citations=[*CITATIONS, (d_p1, "derived", None, None, json.dumps([S1, M1]))],
        sidecars={**SIDECARS, "F15EWS": {"book_diff": {"fid": d_p1, "from_edition": 2023,
                                                       "to_edition": 2026}}}))
    assert result["ok"] is False
    assert _failures(result) == [
        f"F15EWS: book_diff {d_p1} from PB2023 sums P-1 rows (era book diffs are RDT&E only)"]


def test_h_follows_nested_derived_inputs(tmp_path):
    inner, outer = "d4" * 8, "d5" * 8
    result = leg_h_era_book_diffs(site_dir=_export(
        tmp_path,
        citations=[*CITATIONS, (inner, "derived", None, None, json.dumps([F1])),
                   (outer, "derived", None, None, json.dumps([inner, R1]))],
        sidecars={**SIDECARS, "0207134F": {"book_diff": {"fid": outer, "from_edition": 2020}}}))
    assert _failures(result) == [
        f"0207134F: book_diff {outer} from PB2020 sums P-1 rows (era book diffs are RDT&E only)"]


def test_h_fails_on_a_diff_that_resolves_to_nothing(tmp_path):
    ghost = "d6" * 8
    result = leg_h_era_book_diffs(site_dir=_export(
        tmp_path, sidecars={**SIDECARS, "0207134F": {"book_diff": {"fid": ghost, "from_edition": 2019}}}))
    assert f"0207134F: book_diff {ghost} (from PB2019) resolves to no budget_lines_decade row" in _failures(result)


def test_h_fails_vacuously_without_an_era_diff(tmp_path):
    result = leg_h_era_book_diffs(site_dir=_export(
        tmp_path, sidecars={**SIDECARS, "0207134F": {"book_diff": None}}))
    assert _failures(result) == ["no book_diff from an era edition: the leg would pass vacuously"]
```

In `tests/test_verify_era_map.py` (:14-17), replace:

```python
import csv
import dataclasses
import hashlib
from pathlib import Path
```

with:

```python
import csv
import dataclasses
import hashlib
import json
from pathlib import Path
```

In `tests/test_verify_era_map.py` (after `test_cli_fails_with_exit_1`), replace:

```python
LEG_LINES = ["leg a workbooks", "leg b decisions", "leg c f15",
             "leg d fact ids", "leg e published map", "leg f f15 history pin"]


def _publish_export(corpus: Corpus, monkeypatch) -> None:
    """The three artifacts legs d–f read, consistent with the corpus: one era
    P-1 row of budget_lines_decade (its fact id from fact_id_workbook), the
    warehouse map exported as data/p1_era_line_map.parquet, and an F-15
    history file with its pin."""
    from govbudget.export_site import fact_id_workbook

    k = corpus.row(2019, "3010F-AF-L30")
    ident = (k["source_document_sha256"], "P-1", 2019, k["account"], k["organization"],
             k["budget_activity"], k["era_key"], "fy_2017_base_oco")
    data = corpus.site_dir / "data"
    data.mkdir(exist_ok=True)
    con = duckdb.connect()
    con.execute("create table bld (fact_id varchar, document_sha256 varchar, exhibit varchar,"
                " fiscal_year integer, account varchar, organization varchar,"
                " budget_activity varchar, pe_bli varchar, amount_type varchar)")
    con.execute("insert into bld values (?,?,?,?,?,?,?,?,?)", [fact_id_workbook(*ident), *ident])
    con.execute(f"copy bld to '{data / 'budget_lines_decade.parquet'}' (format parquet)")
    con.execute(f"attach '{corpus.duckdb_path}' as wh (read_only)")
    con.execute("copy (select * from wh.p1_era_line_map)"
                f" to '{data / 'p1_era_line_map.parquet'}' (format parquet)")
    con.close()
    history = b'{"points": []}\n'
    (corpus.site_dir / "json").mkdir(exist_ok=True)
```

with:

```python
LEG_LINES = ["leg a workbooks", "leg b decisions", "leg c f15",
             "leg d fact ids", "leg e published map", "leg f f15 history pin",
             "leg g era minters", "leg h era book diffs"]


def _publish_export(corpus: Corpus, monkeypatch) -> None:
    """The artifacts legs d–h read, consistent with the corpus: one era P-1
    row and one PB2019 R-1 row of budget_lines_decade (fact ids from
    fact_id_workbook); their citations (the era row's workbook citation
    carrying its program_key, and a derived book diff over the R-1 row); the
    era row's program page and the R-1 page whose book_diff is that diff; the
    warehouse map exported as data/p1_era_line_map.parquet; and an F-15
    history file with its pin."""
    from govbudget.export_site import fact_id_workbook

    k = corpus.row(2019, "3010F-AF-L30")
    ident = (k["source_document_sha256"], "P-1", 2019, k["account"], k["organization"],
             k["budget_activity"], k["era_key"], "fy_2017_base_oco")
    r1 = ("e" * 64, "R-1", 2019, "3600F", "AF", "07", "0207134F", "fy_2017_actuals")
    era_fid, r1_fid, diff_fid = fact_id_workbook(*ident), fact_id_workbook(*r1), "d" * 16
    data = corpus.site_dir / "data"
    data.mkdir(exist_ok=True)
    con = duckdb.connect()
    con.execute("create table bld (fact_id varchar, document_sha256 varchar, exhibit varchar,"
                " fiscal_year integer, account varchar, organization varchar,"
                " budget_activity varchar, pe_bli varchar, amount_type varchar)")
    con.executemany("insert into bld values (?,?,?,?,?,?,?,?,?)",
                    [[era_fid, *ident], [r1_fid, *r1]])
    con.execute(f"copy bld to '{data / 'budget_lines_decade.parquet'}' (format parquet)")
    con.execute("create table cit (fact_id varchar, kind varchar, sha256 varchar,"
                " pe_bli varchar, inputs varchar)")
    con.executemany("insert into cit values (?,?,?,?,?)", [
        [era_fid, "workbook", k["source_document_sha256"], k["program_key"], None],
        [r1_fid, "workbook", r1[0], "0207134F", None],
        [diff_fid, "derived", None, None, json.dumps([r1_fid])]])
    (corpus.site_dir / "citations").mkdir(exist_ok=True)
    con.execute(f"copy cit to '{corpus.site_dir / 'citations' / 'citations.parquet'}'"
                " (format parquet)")
    con.execute(f"attach '{corpus.duckdb_path}' as wh (read_only)")
    con.execute("copy (select * from wh.p1_era_line_map)"
                f" to '{data / 'p1_era_line_map.parquet'}' (format parquet)")
    con.close()
    details = corpus.site_dir / "json" / "program_details"
    details.mkdir(parents=True)
    (details / f"{k['program_key']}.json").write_text(json.dumps({"book_diff": None}))
    (details / "0207134F.json").write_text(json.dumps(
        {"book_diff": {"fid": diff_fid, "from_edition": 2019, "to_edition": 2026}}))
    (corpus.site_dir / "json" / "programs.json").write_text("[]")
    history = b'{"points": []}\n'
    (corpus.site_dir / "json").mkdir(exist_ok=True)
```

In `tests/test_verify_era_map.py` (in `test_cli_zero_arguments_fails_without_the_export`), replace:

```python
    assert legs["leg f f15 history pin"].endswith(": f15_funding_history.json missing → FAIL")
```

with:

```python
    assert legs["leg f f15 history pin"].endswith(": f15_funding_history.json missing → FAIL")
    assert legs["leg g era minters"].endswith(": export incomplete → FAIL")
    assert legs["leg h era book diffs"].endswith(": export incomplete → FAIL")
```

In `tests/test_verify_era_map_def.py` (`test_f_fails_when_the_history_changed`), replace:

```python
    assert _failures(result) == [
        f"f15_funding_history.json hashes to {actual}, the S0 pin says {digest}"
        " (only the S5 correction re-pins it)"]
```

with:

```python
    assert _failures(result) == [
        f"f15_funding_history.json hashes to {actual}, the committed pin says {digest}"
        " (only an owner-approved correction re-pins it)"]
```

and (`test_format_report_prints_legs_d_to_f`) replace:

```python
        f"  FAIL f15_funding_history.json hashes to {digest}, the S0 pin says {'0' * 64}"
        " (only the S5 correction re-pins it)",
```

with:

```python
        f"  FAIL f15_funding_history.json hashes to {digest}, the committed pin says {'0' * 64}"
        " (only an owner-approved correction re-pins it)",
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_verify_era_map_gh.py tests/test_verify_era_map.py -q`
Expected: a collection error for `tests/test_verify_era_map_gh.py` (`ImportError: cannot import name
'leg_g_era_minters' from 'govbudget.verify_era_map'`), so pytest stops with `1 error`; run
`tests/test_verify_era_map.py` alone and `test_cli_zero_arguments_runs_every_leg` and
`test_cli_zero_arguments_fails_without_the_export` fail (six leg lines where `LEG_LINES` lists eight); run
`tests/test_verify_era_map_def.py` alone and `test_f_fails_when_the_history_changed` and
`test_format_report_prints_legs_d_to_f` fail (the message still says "the S0 pin says … (only the S5 correction
re-pins it)").

- [ ] **Step 3: Implement legs g and h and wire them in**

In `src/govbudget/verify_era_map.py` (:47-51, the module docstring), replace:

```python
  Leg (f) — F-15 history pin. data/site/json/f15_funding_history.json hashes
    to the sha256 committed at S0 in tests/fixtures/f15/history.sha256 (its
    first token, so `shasum -a 256` output reads); only the S5 correction
    re-pins it.
"""
```

with:

```python
  Leg (f) — F-15 history pin. data/site/json/f15_funding_history.json hashes
    to the sha256 committed in tests/fixtures/f15/history.sha256 (its first
    token, so `shasum -a 256` output reads); only an owner-approved correction
    re-pins it (S5 2026-10-04; the T9 gloss, follow-ups Task 21g).

  Leg (g) — era minters (follow-ups, ROADMAP #206 T11). Every PB2017–PB2023
    P-1 row of the exported budget_lines_decade is a same_program line whose
    program_key has a program page and whose workbook citation carries that
    program_key, or an F-15 roster line (ERA_MEMBERS x ERA_PROGRAM_CODES)
    whose citation carries none; the era P-1 workbook citations are exactly
    those rows. This is the p1_era_line_map scope's "Only a same_program line
    whose code has a program page, or an F-15 family-history line, has those
    rows and citations".

  Leg (h) — era book diffs (ROADMAP #206 T11). Every program sidecar
    book_diff from PB2023 or earlier resolves, through the derived citations'
    inputs, to budget_lines_decade leaves none of which is P-1 or P-1R:
    /methodology/'s "book diffs for the era editions cover RDT&E only".
"""
```

In `src/govbudget/verify_era_map.py` (`leg_f_history_pin`'s failure line, :479-480 at HEAD), replace:

```python
        f"{history.name} hashes to {actual}, the S0 pin says {pin}"
        " (only the S5 correction re-pins it)"]
```

with:

```python
        f"{history.name} hashes to {actual}, the committed pin says {pin}"
        " (only an owner-approved correction re-pins it)"]
```

In `src/govbudget/verify_era_map.py` (:54-56), replace:

```python
import csv
import hashlib
import re
```

with:

```python
import csv
import hashlib
import json
import re
```

In `src/govbudget/verify_era_map.py` (:63-67), replace:

```python
LEGS = ("a", "b", "c", "d", "e", "f")
LEG_NAMES = {
    "a": "workbooks", "b": "decisions", "c": "f15",
    "d": "fact ids", "e": "published map", "f": "f15 history pin",
}
```

with:

```python
LEGS = ("a", "b", "c", "d", "e", "f", "g", "h")
LEG_NAMES = {
    "a": "workbooks", "b": "decisions", "c": "f15",
    "d": "fact ids", "e": "published map", "f": "f15 history pin",
    "g": "era minters", "h": "era book diffs",
}
```

In `src/govbudget/verify_era_map.py` (:484-486: legs g and h go in front of `run_verify_era_map`, whose default becomes "abcdefgh"), replace:

```python


def run_verify_era_map(
    *, site_dir: Path, duckdb_path: Path, seed_path: Path, legs: str = "abcdef",
) -> dict:
```

with:

```python


# --- Legs g–h (follow-ups Task 11, ROADMAP #206 T11): two published claims --
#
# The p1_era_line_map scope says "Only a same_program line whose code has a
# program page, or an F-15 family-history line, has those rows and
# citations"; /methodology/ says "book diffs for the era editions cover RDT&E
# only". Both held on the S5 export with only string pins guarding them (the
# home trust anchor went stale exactly that way, final review T1).


def _program_pages(site_dir: Path) -> tuple[set[str], dict[tuple, str]]:
    """The program pages the export ships (one per json/program_details/<slug>.json)
    and, for the split codes, the (pe_bli, account, org) -> slug map that
    json/programs.json carries ('20', '0300D', 'DCSA') -> '20-DCSA'."""
    json_dir = Path(site_dir) / "json"
    pages = {p.stem for p in (json_dir / "program_details").glob("*.json")}
    slugs: dict[tuple, str] = {}
    for row in json.loads((json_dir / "programs.json").read_text(encoding="utf-8")):
        if row.get("slug") and row["slug"] != row.get("pe_bli"):
            slugs[(row["pe_bli"], row.get("account"), row.get("org"))] = row["slug"]
    return pages, slugs


def leg_g_era_minters(*, site_dir: Path, workbooks: Mapping[int, str]) -> dict:
    """Leg (g): who minted each era row of the exported budget_lines_decade.

    Every PB2017–PB2023 P-1 row carrying an era key is either (1) a
    same_program line of the published map whose program_key has a page —
    the split page json/programs.json names for a pinned collision code —
    and whose workbook citation carries program_key as pe_bli (program_key,
    not line_item_code: 0390D's O&M line is cited under 0390DOM), or (2) an
    F-15 roster line (ERA_MEMBERS x ERA_PROGRAM_CODES) whose citation carries
    no pe_bli (the family-history builder's rows). Each row cites its
    edition's pinned era P-1 workbook, and the workbook citations under those
    shas are exactly the era rows' fact ids."""
    import duckdb

    from govbudget.f15_funding_history import ERA_MEMBERS, ERA_PROGRAM_CODES
    from govbudget.jbooks.era_keys import is_era_procurement_key

    site_dir = Path(site_dir)
    decade = site_dir / "data" / "budget_lines_decade.parquet"
    era_map = site_dir / "data" / "p1_era_line_map.parquet"
    cites = site_dir / "citations" / "citations.parquet"
    needed = (decade, era_map, cites, site_dir / "json" / "programs.json",
              site_dir / "json" / "program_details")
    missing = [f"missing {p}" for p in needed if not p.exists()]
    if missing:
        return _leg(False, "export incomplete", missing)
    pages, slugs = _program_pages(site_dir)
    roster = {(edition, f"3010F-AF-L{line}", ERA_PROGRAM_CODES[edition][line])
              for edition, members in ERA_MEMBERS.items() for line, _ba, _title in members}
    con = duckdb.connect()
    try:
        rows = con.execute(
            "select b.fact_id, b.fiscal_year, b.pe_bli, b.document_sha256,"
            " m.line_item_code, m.decision, m.program_key, m.program_account, m.program_org,"
            " c.kind, c.sha256, c.pe_bli"
            " from read_parquet(?) b"
            " left join read_parquet(?) m on m.edition = b.fiscal_year and m.era_key = b.pe_bli"
            " left join read_parquet(?) c on c.fact_id = b.fact_id"
            " where b.exhibit = 'P-1' and b.fiscal_year <= ?",
            [str(decade), str(era_map), str(cites), _ERA_P1_LAST_EDITION]).fetchall()
        cited = {r[0] for r in con.execute(
            "select fact_id from read_parquet(?)"
            " where kind = 'workbook' and list_contains(?, sha256)",
            [str(cites), sorted(set(workbooks.values()))]).fetchall()}
    finally:
        con.close()
    failures: list[str] = []
    counts: Counter = Counter()
    era_fids: set[str] = set()
    for (fid, edition, pe_bli, doc_sha, code, decision, program_key, p_account, p_org,
         kind, cite_sha, cite_pe) in rows:
        if not is_era_procurement_key(pe_bli):
            continue  # leg d fails an era-edition P-1 row that lost its era key
        era_fids.add(fid)
        where = f"{fid} ({edition}/{pe_bli})"
        if decision is None:
            failures.append(f"{where}: no p1_era_line_map row")
            continue
        pinned = workbooks.get(edition)
        if kind != "workbook" or cite_sha != pinned or doc_sha != pinned:
            failures.append(f"{where}: citation is {kind}/{(cite_sha or '')[:12]}, not the"
                            f" PB{edition} era P-1 workbook")
        if decision == "same_program":
            counts["same_program"] += 1
            slug = slugs.get((program_key, p_account, p_org)) if (p_account or p_org) else program_key
            if slug not in pages:
                failures.append(f"{where}: same_program line {code} has no program page"
                                f" ({program_key}, {p_account}, {p_org})")
            if cite_pe != program_key:
                failures.append(f"{where}: citation pe_bli {cite_pe!r} != program_key {program_key!r}")
        elif (edition, pe_bli, code) in roster:
            counts["f15_roster"] += 1
            if cite_pe is not None:
                failures.append(f"{where}: F-15 roster line {code} ({decision}) cites pe_bli {cite_pe!r}")
        else:
            failures.append(f"{where}: a {decision} line ({code}) that is neither same_program"
                            " nor on the F-15 roster minted a decade row")
    for fid in sorted(cited - era_fids):
        failures.append(f"{fid}: an era P-1 workbook citation with no era budget_lines_decade row")
    for fid in sorted(era_fids - cited):
        failures.append(f"{fid}: an era budget_lines_decade row with no era P-1 workbook citation")
    if not era_fids:
        failures.append("no era P-1 row in budget_lines_decade: the leg would pass vacuously")
    return _leg(not failures,
                f"era_rows={len(era_fids)} same_program={counts['same_program']}"
                f" f15_roster={counts['f15_roster']} era_workbook_citations={len(cited)}"
                f" failures={len(failures)}", failures)


def leg_h_era_book_diffs(*, site_dir: Path) -> dict:
    """Leg (h): no book diff from an era edition sums procurement rows.

    Every json/program_details/*.json book_diff whose from_edition is PB2023 or
    earlier is resolved, through the derived citations' inputs (recursively),
    to its budget_lines_decade leaves; none may be a P-1 or P-1R row, and each
    must resolve to at least one leaf. At least one era diff must exist."""
    import duckdb

    site_dir = Path(site_dir)
    decade = site_dir / "data" / "budget_lines_decade.parquet"
    cites = site_dir / "citations" / "citations.parquet"
    details = site_dir / "json" / "program_details"
    missing = [f"missing {p}" for p in (decade, cites, details) if not p.exists()]
    if missing:
        return _leg(False, "export incomplete", missing)
    con = duckdb.connect()
    try:
        exhibit = dict(con.execute("select fact_id, exhibit from read_parquet(?)",
                                   [str(decade)]).fetchall())
        inputs = dict(con.execute("select fact_id, inputs from read_parquet(?)"
                                  " where inputs is not null", [str(cites)]).fetchall())
    finally:
        con.close()

    def leaves(fid: str, seen: set[str]) -> set[str]:
        if fid in exhibit:
            return {fid}
        if fid in seen or fid not in inputs:
            return set()
        seen.add(fid)
        out: set[str] = set()
        for child in json.loads(inputs[fid]):
            out |= leaves(child, seen)
        return out

    failures: list[str] = []
    era = 0
    by_exhibit: Counter = Counter()
    for path in sorted(details.glob("*.json")):
        diffs = json.loads(path.read_text(encoding="utf-8")).get("book_diff")
        for diff in ([diffs] if isinstance(diffs, dict) else diffs or []):
            from_edition = diff.get("from_edition")
            if not isinstance(from_edition, int) or from_edition > _ERA_P1_LAST_EDITION:
                continue
            era += 1
            found = leaves(diff["fid"], set())
            if not found:
                failures.append(f"{path.stem}: book_diff {diff['fid']} (from PB{from_edition})"
                                " resolves to no budget_lines_decade row")
            kinds = {exhibit[f] for f in found}
            by_exhibit.update(kinds)
            procurement = sorted(kinds & {"P-1", "P-1R"})
            if procurement:
                failures.append(f"{path.stem}: book_diff {diff['fid']} from PB{from_edition} sums"
                                f" {'/'.join(procurement)} rows (era book diffs are RDT&E only)")
    if not era:
        failures.append("no book_diff from an era edition: the leg would pass vacuously")
    return _leg(not failures,
                f"era_diffs={era} r1={by_exhibit['R-1']}"
                f" procurement={by_exhibit['P-1'] + by_exhibit['P-1R']} failures={len(failures)}",
                failures)


def run_verify_era_map(
    *, site_dir: Path, duckdb_path: Path, seed_path: Path, legs: str = "abcdefgh",
) -> dict:
```

In `src/govbudget/verify_era_map.py` (the dispatch in `run_verify_era_map`), replace:

```python
        else:  # f
            results[leg] = leg_f_history_pin(site_dir=Path(site_dir))
```

with:

```python
        elif leg == "f":
            results[leg] = leg_f_history_pin(site_dir=Path(site_dir))
        elif leg == "g":
            results[leg] = leg_g_era_minters(site_dir=Path(site_dir),
                                             workbooks=ERA_P1_WORKBOOK_SHA256)
        else:  # h
            results[leg] = leg_h_era_book_diffs(site_dir=Path(site_dir))
```

In `src/govbudget/cli.py` (:3343-3351), replace:

```python
        help="families piece 1 release gate: era P-1 map vs the shipped"
             " workbooks, owner decisions, F-15 roster (legs a-f)",
    )
    vera.add_argument(
        "--legs", default="abcdef",
        help="legs to run, letters from abcdef (default: all six)",
    )
```

with:

```python
        help="families piece 1 release gate: era P-1 map vs the shipped"
             " workbooks, owner decisions, F-15 roster, era minters and era"
             " book diffs (legs a-h)",
    )
    vera.add_argument(
        "--legs", default="abcdefgh",
        help="legs to run, letters from abcdefgh (default: all eight)",
    )
```

In `src/govbudget/verify_phase5.py` (:35-40), replace:

```python
     build-dependent phase gates) PLUS verify-era-map (families piece 1,
     legs a–f: the era P-1 workbooks re-read against the map, no undecided
     or stale decision, F-15's era rows, every budget_lines_decade fact ID
     recomputed from its own row, the published map equal to the
     warehouse's, the F-15 history sha pinned; legs d–f audit the export,
     so a missing artifact FAILs). Parses each full output with the verdict
```

with:

```python
     build-dependent phase gates) PLUS verify-era-map (families piece 1,
     legs a–h: the era P-1 workbooks re-read against the map, no undecided
     or stale decision, F-15's era rows, every budget_lines_decade fact ID
     recomputed from its own row, the published map equal to the
     warehouse's, the F-15 history sha pinned, every era decade row minted
     by a same_program line with a page or by the F-15 roster, no era book
     diff over procurement rows; legs d–h audit the export,
     so a missing artifact FAILs). Parses each full output with the verdict
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_verify_era_map_gh.py tests/test_verify_era_map.py tests/test_verify_era_map_def.py tests/test_verify_phase5.py -q`
Expected: no failures (scratch overlay, first three files: `76 passed`, of which 17 are the new file's).

- [ ] **Step 5: Run the two legs on today's export, read-only**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
uv run --project . python -m govbudget verify-era-map --legs gh; echo "exit $?"
```
Expected (measured 2026-10-13 against the live `data/site`, built 2026-10-04):

```
leg g era minters: era_rows=17502 same_program=17481 f15_roster=21 era_workbook_citations=17502 failures=0 → PASS
leg h era book diffs: era_diffs=1044 r1=1044 procurement=0 failures=0 → PASS
verify-era-map: PASS
exit 0
```
A FAIL here is a real breach of a published claim on the deployed export: stop and report it, do not edit the leg.

- [ ] **Step 6: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/verify_era_map.py GovBudget/src/govbudget/cli.py GovBudget/src/govbudget/verify_phase5.py GovBudget/tests/test_verify_era_map_gh.py GovBudget/tests/test_verify_era_map.py GovBudget/tests/test_verify_era_map_def.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(verify-era-map): legs g (era minters) and h (era book diffs) back two published claims (#206 T11)" -m "Leg g: every era budget_lines_decade row is a same_program line with a page whose citation carries program_key, or an F-15 roster line citing no pe_bli; era workbook citations = era rows (17,502 = 17,481 + 21 live). Leg h: no era book_diff resolves to a P-1/P-1R leaf (1,044 R-1 diffs live). Default legs abcdefgh. Leg f names an owner-approved correction, not only S5, as what re-pins the F-15 history (the T9 gloss re-pins it in Task 21g)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
