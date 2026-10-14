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
