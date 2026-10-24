"""The generic platform-family history builder and the export post-pass
(families piece 2; spec §10, §11, §12, §13, §16).

F35 is a synthetic F-35-shaped family built from the F-15 entry without stage 1:
the builder is pure, so it needs only the Family fields it reads. The post-pass
tests run on a mini export built from the V5 fixture (_v5_export)."""
import functools
import gzip
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import duckdb
import pytest

from govbudget import config, platform_family_history
from govbudget.export_site import fact_id_derived
from govbudget.platform_families import EraLine, Headline, LakeReport, RegistryError, ReviewGuard, load_registry
from govbudget.platform_family_history import (ANNUAL_FORMULA, CELL_FORMULA, CUMULATIVE_FORMULA, INDEX_PATH,
                                               _json_bytes, build_history, build_program_matrix, check_headline,
                                               expected_members, export_family_histories, member_row,
                                               program_entries, reuse_formulas)

F15 = load_registry()["f-15"]


def _member(member_id, title, *, family="f-35", valid=(2017, 2026), titles=None, order=None, role="counted",
            page_slug=None):
    first, last = valid
    exhibit, account, organization, code = member_id.split(":")
    return replace(
        F15.counted[0],
        member_row_id=f"{family}|{member_id}|{first}-{last}", platform_family=family, member_id=member_id,
        exhibit=exhibit, account=account, organization=organization, code=code, role=role, verdict="approved",
        # A tuple, never a generator: F35 is shared by every test and title_for reads it on every call.
        titles_seen=tuple((e, title) for e in (titles if titles is not None else range(first, last + 1))),
        display_title=title,
        page_slug=page_slug if page_slug is not None else (code if role == "counted" else ""),
        valid_from_edition=first, valid_to_edition=last,
        coverage_expected_from_edition=first if role == "counted" else None,
        member_order=order, era_decision_ids=(), evidence=())


F35 = replace(
    F15, platform_family="f-35", short_name="F-35", history_dataset="f35_funding_history",
    on_partial_corpus="raise",
    review_guard=ReviewGuard(exhibits=("P-1", "R-1"),
                             title_substrings=("F-35", "F35", "JSF", "JOINT STRIKE", "F135", "LIGHTNING")),
    headline=Headline("cumulative_actuals", 2015, 2024), program_notes={},
    scope_note="Synthetic F-35-shaped scope note.", coverage_notes=("Synthetic coverage note.",),
    members=(
        _member("P-1:3010F:AF:ATA000", "F-35", titles=range(2024, 2027), order=1),
        _member("P-1:1506N:NAVY:0152", "JSF STOVL", titles=range(2024, 2027), order=2),
        _member("R-1:3600F:AF:0207142F", "F-35 Squadrons", order=3),
        # Synthetic range, so a PB2026 row is in range.
        _member("R-1:1319N:NAVY:0604800M", "JSF EMD", order=4),
        _member("R-1:1319N:NAVY:0604810N", "JSF Follow-On Modernization", valid=(2017, 2020), order=5),
        _member("P-1:3020F:AF:JSM000", "Joint Strike Missile", titles=(), role="context"),
    ),
    era_lines=(EraLine("f-35", "P-1:3010F:AF:ATA000", 2020, "3010F-AF-L1", "01", "F-35", "ATA000|3010F||2017-2023"),),
)


def _row(pe, edition, *, exhibit, account, organization, title, amount_type="fy_2024_actuals", value=10,
         budget_activity="01", cells="J20"):
    """The shape of tests/test_f15_funding_history.py::source."""
    return dict(pe_bli=pe, edition=edition, exhibit=exhibit, account=account, account_title="Synthetic account",
                organization=organization, budget_activity=budget_activity,
                budget_activity_title="Synthetic activity", title=title, amount_type=amount_type,
                amount_thousands=value, sha256="a" * 64, sheet=f"Exhibit {exhibit}", cells=cells,
                official_url="https://comptroller.war.gov/synthetic.xlsx", retrieved_at="2026-10-21")


def _point(row, *, fy=2024, kind="actuals", n=1, amount=None):
    """The shape of tests/test_f15_funding_history.py::point."""
    return dict(pe_bli=row["pe_bli"], edition=row["edition"], fy=fy, kind=kind, amount_type=row["amount_type"],
                n_source_rows=n, amount=row["amount_thousands"] if amount is None else amount)


def _previews(leaves, family):
    """tests/test_f15_funding_history.py::matrix's previews; an era leaf's code comes from family.era_lines."""
    codes = {m.member_id: m.code for m in family.members}
    era = {(line.edition, line.era_key): codes[line.member_id] for line in family.era_lines}
    previews = {}
    for fid, row in leaves.items():
        code = era.get((row["edition"], row["pe_bli"]), row["pe_bli"])
        refs = row["cells"].split(",")
        col = refs[0].rstrip("0123456789")
        previews[fid] = dict(sheet=row["sheet"], col=col, units="USD thousands", total=row["amount_thousands"],
                             rows=[dict(r=int(ref[len(col):]), code=code, cited=True) for ref in refs])
    return previews


def test_templates_are_the_spec_section_11_text():
    assert ANNUAL_FORMULA == ("sum(budget_lines.amount_thousands) for reviewed {short_name} members, PB{edition}, "
                              "FY{fy} {kind}; one selected scenario column per workbook line")
    assert CUMULATIVE_FORMULA == ("sum(budget_lines.amount_thousands) via annual reviewed {short_name} actuals totals, "
                                  "FY{a}–FY{b}; each fiscal year once, nominal USD thousands; excludes "
                                  "enacted/current-year figures and requests")
    assert CELL_FORMULA == ("sum(budget_lines.amount_thousands) for workbook program {member_id}, PB{edition}, "
                            "FY{fy} {kind}; each selected workbook input once")


def test_reuse_formulas_lists_own_then_edition_then_bare():
    own = ("sum(budget_lines.amount_thousands) for workbook program P-1:3010F:AF:F01500, PB2018, FY2016 actuals; "
           "each selected workbook input once")
    assert reuse_formulas("P-1:3010F:AF:F01500", 2018, 2016, "actuals", "fy_2016_base_oco") == [
        own, "sum(budget_lines.amount_thousands where amount_type=fy_2016_base_oco and edition=2018)",
        "sum(budget_lines.amount_thousands where amount_type=fy_2016_base_oco)"]
    assert reuse_formulas("P-1:3010F:AF:F01500", 2018, 2016, "actuals", None) == [own]


def test_four_accounts_sum_once_into_one_annual_point():
    rows = [_row("ATA000", 2026, exhibit="P-1", account="3010F", organization="F", title="F-35", value=100, cells="J10"),
            _row("0152", 2026, exhibit="P-1", account="1506N", organization="N", title="JSF STOVL", value=20, cells="J11"),
            _row("0207142F", 2026, exhibit="R-1", account="3600F", organization="F", title="F-35 Squadrons", value=3, cells="J12"),
            _row("0604800M", 2026, exhibit="R-1", account="1319N", organization="N", title="JSF EMD", value=4, cells="J13")]
    payload, citations, leaves, _ = build_history(F35, rows, [_point(r) for r in rows], retrieved_at="2026-10-21")
    (point,) = payload["points"]
    assert point["amount_thousands"] == 127 and len(leaves) == 4
    assert {c["program_slug"] for c in point["components"]} == {"ATA000", "0152", "0207142F", "0604800M"}
    assert point["fact_id"] == fact_id_derived("family_history", "f-35|2026|2024", "actuals")
    assert citations[point["fact_id"]]["formula"] == ("sum(budget_lines.amount_thousands) for reviewed F-35 members, "
                                                      "PB2026, FY2024 actuals; one selected scenario column per workbook line")
    assert point["missing_programs"] == [] and point["coverage"] == "covered-records"
    assert payload["family_id"] == "f-35" and payload["scope_note"] == "Synthetic F-35-shaped scope note."
    assert payload["cumulative"]["fact_id"] == fact_id_derived("family_history", "f-35|2024|2024", "cumulative-actuals")


def test_navy_rows_accept_the_era_and_modern_spellings_only():
    row = _row("0604800M", 2026, exhibit="R-1", account="1319N", organization="N", title="JSF EMD")
    assert member_row(F35, row) and member_row(F35, {**row, "organization": "NAVY"})
    with pytest.raises(ValueError, match=r"^F-35 modern member identity drift: 2026/0604800M$"):
        member_row(F35, {**row, "organization": "F"})


def test_a_member_ending_at_pb2020_is_not_missing_afterwards():
    a = _row("0207142F", 2020, exhibit="R-1", account="3600F", organization="F", title="F-35 Squadrons", amount_type="fy_2018_actuals")
    b = _row("0207142F", 2021, exhibit="R-1", account="3600F", organization="F", title="F-35 Squadrons", amount_type="fy_2019_actuals")
    payload, *_ = build_history(F35, [a, b], [_point(a, fy=2018), _point(b, fy=2019)], retrieved_at="2026-10-21")
    missing = {p["edition"]: p["missing_programs"] for p in payload["points"]}
    assert missing == {2020: ["0152", "0604800M", "0604810N", "ATA000"], 2021: ["0152", "0604800M", "ATA000"]}


def test_era_roster_attribution_counts_as_present():
    era = _row("3010F-AF-L1", 2020, exhibit="P-1", account="3010F", organization="AF", title="F-35", amount_type="fy_2018_actuals")
    payload, *_ = build_history(F35, [era], [_point(era, fy=2018)], retrieved_at="2026-10-21")
    (point,) = payload["points"]
    assert point["missing_programs"] == ["0152", "0207142F", "0604800M", "0604810N"]
    assert point["components"][0]["program_slug"] is None and point["components"][0]["dataset"] == "budget_lines_decade"


def test_a_context_row_is_never_summed_and_silences_the_guard():
    ata = _row("ATA000", 2026, exhibit="P-1", account="3010F", organization="F", title="F-35", cells="J10")
    jsm = _row("JSM000", 2026, exhibit="P-1", account="3020F", organization="F", title="Joint Strike Missile", cells="J11")
    assert member_row(F35, jsm) is False
    payload, _, leaves, _ = build_history(F35, [ata, jsm], [_point(ata), _point(jsm)], retrieved_at="2026-10-21")
    assert [c["pe_bli"] for c in payload["points"][0]["components"]] == ["ATA000"] and len(leaves) == 1


def test_an_unreviewed_joint_strike_row_raises():
    row = _row("JSF999", 2026, exhibit="P-1", account="3010F", organization="F", title="JOINT STRIKE SPARES")
    with pytest.raises(ValueError, match=r"^Unreviewed F-35 workbook identity: 2026/JSF999$"):
        member_row(F35, row)


def test_a_code_keyed_row_outside_titles_seen_is_identity_drift():
    row = _row("0604810N", 2021, exhibit="R-1", account="1319N", organization="N", title="JSF Follow-On Modernization")
    with pytest.raises(ValueError, match=r"^F-35 modern member identity drift: 2021/0604810N$"):
        member_row(F35, row)


def test_a_multi_input_cell_mints_the_family_dataset_and_cell_formula():
    first = _row("ATA000", 2026, exhibit="P-1", account="3010F", organization="F", title="F-35", value=100, cells="J10")
    second = {**first, "budget_activity": "05", "amount_thousands": 20, "cells": "J20"}
    payload, _, leaves, _ = build_history(F35, [first, second], [_point(first, n=2, amount=120)], retrieved_at="2026-10-21")
    enriched, additions, _ = build_program_matrix(F35, payload, _previews(leaves, F35), existing_citations={}, retrieved_at="2026-10-21")
    (cell,) = enriched["points"][0]["program_cells"]
    assert cell["dataset"] == "f35_funding_history" and cell["amount_thousands"] == 120
    assert cell["fact_id"] == fact_id_derived("family_program_history", "P-1:3010F:AF:ATA000|2026|2024", "actuals")
    assert additions[cell["fact_id"]]["formula"] == ("sum(budget_lines.amount_thousands) for workbook program "
                                                     "P-1:3010F:AF:ATA000, PB2026, FY2024 actuals; each selected workbook input once")
    assert enriched["programs"] == program_entries(F35)
    assert [p["id"] for p in enriched["programs"]] == [m.member_id for m in F35.counted]


def test_expected_members_reproduces_the_88538c6a_f15_rule():
    for edition in range(2017, 2027):
        today = {"0207134F", "0207171F"} | ({"0207146F"} if edition >= 2021 else set()) \
            | ({"F01500", "F015EX", "F15EWS"} if edition >= 2024 else set())
        assert expected_members(F15, edition) == frozenset(today), edition


def test_check_headline_refuses_a_window_unlike_the_registry():
    assert check_headline(F35, {"cumulative": {"start_fy": 2015, "end_fy": 2024}}) is None
    with pytest.raises(ValueError, match=r"^F-35 cumulative window FY2016–FY2024 differs from the registry headline FY2015–FY2024$"):
        check_headline(F35, {"cumulative": {"start_fy": 2016, "end_fy": 2024}})


def test_the_f15_facade_delegates_to_the_generic_builder():
    from govbudget import f15_funding_history as facade
    row = _row("0207130F", 2026, exhibit="R-1", account="3600F", organization="F", title="F-15 Squadrons")
    with pytest.raises(ValueError, match=r"^Unreviewed F-15 workbook identity: 2026/0207130F$"):
        facade.member_row(row)
    assert facade.PROGRAMS == program_entries(facade.F15) and facade.F15 == F15
    assert facade._json_bytes is _json_bytes


# ---------------------------------------------------------------------------
# The export post-pass (spec §10.1, §12, §16): a mini export from the V5 fixture
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "f15"
PIN = (FIXTURES / "history.sha256").read_text().strip()
NARRATIVE = dict(kind="jbook_narrative", page_number=71, pe_bli="F015EX",
                 sha256="528d14414585406684021e04e74632cccf4b40f8ba039f89f8af1ddebc7bc01e")
FACT_REFS = ("0026c924483c6624", "d9982379a24ebac6", "b30fae1fd23999e4", "c9e5c28dfebc879e", "b3dbc6ed30814fdf")
# The live export's column types (export_site._write_typed_parquet and the decade tier).
CITATION_COLUMNS = (
    ("fact_id", "varchar"), ("kind", "varchar"), ("units", "varchar"), ("amount_text", "varchar"),
    ("page_number", "integer"), ("x0", "double"), ("x1", "double"), ("top_pt", "double"), ("bottom_pt", "double"),
    ("page_width", "double"), ("page_height", "double"), ("resolution", "varchar"), ("sheet", "varchar"),
    ("cells", "varchar"), ("amount_thousands", "double"), ("sha256", "varchar"), ("hosted_pdf_url", "varchar"),
    ("official_url", "varchar"), ("xml_path", "varchar"), ("retrieved_at", "varchar"), ("formula", "varchar"),
    ("inputs", "varchar"), ("query_body", "varchar"), ("recorded_value", "varchar"), ("pe_bli", "varchar"),
    ("scenario", "varchar"), ("amount_type", "varchar"))
DECADE_COLUMNS = (
    ("fact_id", "varchar"), ("exhibit", "varchar"), ("fiscal_year", "integer"), ("account", "varchar"),
    ("account_title", "varchar"), ("organization", "varchar"), ("budget_activity", "varchar"),
    ("budget_activity_title", "varchar"), ("pe_bli", "varchar"), ("title", "varchar"), ("amount_type", "varchar"),
    ("amount_thousands", "double"), ("units", "varchar"), ("document_sha256", "varchar"), ("source_sheet", "varchar"),
    ("source_cells", "varchar"))
B1 = replace(F15, platform_family="b-1", short_name="B-1", history_dataset="b1_funding_history",
             program_notes={}, review_guard=ReviewGuard(("P-1", "R-1"), ("B-1B",)),
             headline=Headline("cumulative_actuals", 2024, 2024), on_partial_corpus="skip", era_lines=(),
             members=(_member("P-1:3010F:AF:B00100", "B-1B", family="b-1", valid=(2024, 2026), order=1, page_slug=""),))
B1_ROW = dict(exhibit="P-1", edition=2026, account="3010F", account_title="Aircraft Procurement, Air Force",
              organization="F", budget_activity="01", budget_activity_title="Combat Aircraft", pe_bli="B00100",
              title="B-1B", amount_type="fy_2024_actuals", amount_thousands=5.0, sha256="b" * 64,
              sheet="Exhibit P-1", cells="J5",
              official_url="https://comptroller.war.gov/Portals/45/Documents/defbudget/fy2026/p1_display.xlsx",
              retrieved_at="2026-06-10 16:08:15.686145-04:00")
B1_SERIES = dict(pe_bli="B00100", fy=2024, edition=2026, kind="actuals", amount=5.0, amount_type="fy_2024_actuals",
                 n_source_rows=1)


@functools.lru_cache(maxsize=1)
def _inputs() -> dict:
    with gzip.open(FIXTURES / "builder_inputs.json.gz", "rt", encoding="utf-8") as handle:
        return json.load(handle)


def _table(con, name, columns, rows, path):
    con.execute(f"create or replace table {name} ({', '.join(f'{c} {t}' for c, t in columns)})")
    if rows:
        con.executemany(f"insert into {name} values ({', '.join('?' * len(columns))})", rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    con.execute(f"copy {name} to ? (format parquet)", [str(path)])


def _v5_export(root, *, extra_rows=(), extra_series=(), drop_series=()) -> tuple[Path, Path]:
    """A completed mini export from tests/fixtures/f15/builder_inputs.json.gz:
    (duckdb_path, out_dir). The warehouse holds fct_decade_series and
    dim_programs; the jbooks parquet holds the F-15 member workbook rows."""
    inputs = _inputs()
    lake, out = root / "lake", root / "site"
    lake.mkdir(parents=True)
    duckdb_path = lake / "govbudget.duckdb"
    con = duckdb.connect(str(duckdb_path))
    try:
        con.execute("create table fct_decade_series (pe_bli varchar, fy integer, edition_year integer, "
                    "amount_type_kind varchar, amount double, amount_type varchar, n_source_rows integer)")
        con.executemany("insert into fct_decade_series values (?, ?, ?, ?, ?, ?, ?)", [
            (p["pe_bli"], p["fy"], p["edition"], p["kind"], p["amount"], p["amount_type"], p["n_source_rows"])
            for p in (*inputs["series"], *extra_series) if p["pe_bli"] not in drop_series])
        con.execute("create table dim_programs (pe_bli varchar, org varchar, exhibit_family varchar, account varchar, "
                    "account_title varchar, title varchar)")
        con.executemany("insert into dim_programs values (?, 'F', ?, ?, ?, ?)", [
            (m.code, m.exhibit, m.account, "Synthetic account", m.display_title) for m in F15.code_keyed])
    finally:
        con.close()

    rows = [*inputs["source_rows"], *extra_rows]
    documents: dict[tuple, str] = {}
    for r in rows:
        documents.setdefault((r["sha256"], r["official_url"], r["retrieved_at"]), f"doc-{len(documents):03d}")
    registry = {**inputs["registry"], "e7d5bcfb4a30f458": dict(NARRATIVE),
                **{fid: dict(kind="jbook_narrative") for fid in FACT_REFS}}
    con = duckdb.connect()
    try:
        _table(con, "budget_lines", [("exhibit", "varchar"), ("fiscal_year", "varchar"), ("account", "varchar"),
                                     ("account_title", "varchar"), ("organization", "varchar"),
                                     ("budget_activity", "varchar"), ("budget_activity_title", "varchar"),
                                     ("pe_bli", "varchar"), ("title", "varchar"), ("amount_type", "varchar"),
                                     ("amount_thousands", "double"), ("source_sheet", "varchar"),
                                     ("source_cells", "varchar"), ("source_document_id", "varchar")],
               [(r["exhibit"], str(r["edition"]), r["account"], r["account_title"], r["organization"],
                 r["budget_activity"], r["budget_activity_title"], r["pe_bli"], r["title"], r["amount_type"],
                 r["amount_thousands"], r["sheet"], r["cells"],
                 documents[(r["sha256"], r["official_url"], r["retrieved_at"])]) for r in rows],
               lake / "parquet/jbooks/budget_lines.parquet")
        _table(con, "documents", [("id", "varchar"), ("sha256", "varchar"), ("source_url", "varchar"),
                                  ("downloaded_at", "varchar")],
               [(doc_id, sha, url, at) for (sha, url, at), doc_id in documents.items()],
               lake / "parquet/jbooks/documents.parquet")
        _table(con, "citations", CITATION_COLUMNS,
               [(fid, *(entry.get(c) for c, _ in CITATION_COLUMNS[1:])) for fid, entry in sorted(registry.items())],
               out / "citations/citations.parquet")
        _table(con, "budget_lines_current", [("fact_id", "varchar")],
               [(fid,) for fid in inputs["current_fact_ids"]], out / "data/budget_lines.parquet")
        _table(con, "budget_lines_decade", DECADE_COLUMNS, [], out / "data/budget_lines_decade.parquet")
    finally:
        con.close()

    def write(relative, value):
        (out / relative).parent.mkdir(parents=True, exist_ok=True)
        (out / relative).write_bytes(_json_bytes(value))

    write("manifest.json", {"built_at": inputs["retrieved_at"], "citations": {},
                            "datasets": {"budget_lines_decade": 0}, "json_sidecars": 0, "schema_version": 1})
    write("json/citations.json", registry)
    write("json/site_meta.json", {"counts": {"citations": 0}, "datasets": {"budget_lines_decade": 0}})
    write("json/datasets.json", {"datasets": [{"name": "budget_lines_decade", "row_count": 0, "bytes": 0}]})
    for m in F15.code_keyed:
        write(f"json/program_details/{m.code}.json", {})
    return duckdb_path, out


@pytest.fixture
def stubbed(monkeypatch):
    """The workbook previews, the lake and stage 2, stubbed on platform_family_history."""
    spy = SimpleNamespace(check_lake_calls=[])
    fixture_previews = _inputs()["previews"]

    def build_workbook_previews(*, workbook_dir, citations, missing_workbooks=None):
        previews = {}
        for fid, citation in citations.items():
            if fid in fixture_previews:
                previews[fid] = fixture_previews[fid]
            elif citation["sha256"] == B1_ROW["sha256"]:     # a b-1 leaf: one cited row of code B00100
                col = citation["cells"].rstrip("0123456789")
                previews[fid] = dict(sheet=citation["sheet"], col=col, units="USD thousands",
                                     total=citation["amount_thousands"],
                                     rows=[dict(r=int(citation["cells"][len(col):]), code="B00100", cited=True)])
        return previews

    def check_lake(registry, *, lake, site_dir, families=None):
        spy.check_lake_calls.append((families, site_dir))
        return LakeReport([], [], [])

    monkeypatch.setattr(platform_family_history, "build_workbook_previews", build_workbook_previews)
    monkeypatch.setattr(platform_family_history, "open_lake", lambda duckdb_path: SimpleNamespace(close=lambda: None))
    monkeypatch.setattr(platform_family_history, "check_lake", check_lake)
    return spy


def _tree(root) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path(root).rglob("*")) if p.is_file()}


def _rows(path) -> list[tuple]:
    return duckdb.connect().execute("select * from read_parquet(?) order by fact_id", [str(path)]).fetchall()


def test_post_pass_on_the_v5_fixture_writes_the_pinned_history_and_the_index(tmp_path, stubbed):
    duckdb_path, out = _v5_export(tmp_path)
    result = export_family_histories(duckdb_path=duckdb_path, out_dir=out, registry=load_registry())
    assert hashlib.sha256((out / "json/f15_funding_history.json").read_bytes()).hexdigest() == PIN
    assert hashlib.sha256((out / INDEX_PATH).read_bytes()).hexdigest() == \
        "3657d3bd36fa8f344cf2c299714dacb11fe227100cd1ff0c3d3d22f6734f1945"
    assert result["families"] == {"f-15": {"annual_points": 30, "source_facts": 207, "added_citations": 208,
                                           "cumulative_actuals_thousands": 17043321.0}}
    assert result["citations"] == 177 + 6 + 208
    assert stubbed.check_lake_calls == [(["f-15"], out)]
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["f15_funding_history"] == {"annual_points": 30, "source_facts": 207, "start_fy": 2015, "end_fy": 2026}
    assert result["json_files"] == manifest["json_sidecars"] == len(list((out / "json").rglob("*.json")))


def test_full_pass_differs_from_the_facade_path_only_by_index_and_json_sidecars(tmp_path, stubbed):
    from govbudget import f15_funding_history as facade
    db_a, out_a = _v5_export(tmp_path / "a")
    db_b, out_b = _v5_export(tmp_path / "b")
    flat = facade.export_f15_funding_history(duckdb_path=db_a, out_dir=out_a)
    full = export_family_histories(duckdb_path=db_b, out_dir=out_b, registry=load_registry())
    assert set(flat) == {"annual_points", "source_facts", "added_citations", "citations", "json_files",
                         "cumulative_actuals_thousands"}
    assert full["json_files"] == flat["json_files"] + 1 and full["citations"] == flat["citations"]
    a, b = _tree(out_a), _tree(out_b)
    assert set(b) - set(a) == {INDEX_PATH} and set(a) <= set(b)
    for path in a:
        if path.endswith(".parquet"):
            assert _rows(out_a / path) == _rows(out_b / path), path   # select * … order by fact_id
        elif path != "manifest.json":
            assert a[path] == b[path], path
    ma, mb = (json.loads((o / "manifest.json").read_text()) for o in (out_a, out_b))
    assert mb.pop("json_sidecars") == ma.pop("json_sidecars") + 1 and ma == mb


def test_nothing_is_written_without_a_full_corpus(tmp_path, stubbed):
    duckdb_path, out = _v5_export(tmp_path, drop_series={"0207171F"})
    before = _tree(out)
    assert export_family_histories(duckdb_path=duckdb_path, out_dir=out, registry=load_registry()) is None
    assert _tree(out) == before and not (out / "json/families").exists()


def test_a_published_family_skipped_beside_one_that_builds_raises_and_writes_nothing(tmp_path, stubbed):
    duckdb_path, out = _v5_export(tmp_path, extra_rows=[B1_ROW])          # no B1_SERIES: B-1 skips
    before = _tree(out)
    with pytest.raises(RegistryError, match=r"all published families build or none: built \['f-15'\], skipped \['b-1'\]"):
        export_family_histories(duckdb_path=duckdb_path, out_dir=out, registry=replace(load_registry(), families=(F15, B1)))
    assert _tree(out) == before


def test_two_families_in_one_pass_share_no_leaf_and_leave_f15_bytes_unchanged(tmp_path, stubbed):
    duckdb_path, out = _v5_export(tmp_path, extra_rows=[B1_ROW], extra_series=[B1_SERIES])
    result = export_family_histories(duckdb_path=duckdb_path, out_dir=out, registry=replace(load_registry(), families=(F15, B1)))
    assert hashlib.sha256((out / "json/f15_funding_history.json").read_bytes()).hexdigest() == PIN
    assert json.loads((out / "json/b1_funding_history.json").read_text())["family_id"] == "b-1"
    assert [f["platform_family"] for f in json.loads((out / INDEX_PATH).read_text())["families"]] == ["f-15", "b-1"]
    assert set(result["families"]) == {"f-15", "b-1"} and result["families"]["b-1"]["source_facts"] == 1
    assert {"f15_funding_history", "b1_funding_history"} <= set(json.loads((out / "manifest.json").read_text()))


def test_a_leaf_in_two_families_stops_the_pass_before_any_write(tmp_path, stubbed):
    shared = next(m for m in F15.counted if m.code == "0207134F")
    dup = replace(B1, headline=Headline("cumulative_actuals", 2015, 2024),
                  members=(replace(shared, platform_family="b-1", member_order=1),))
    duckdb_path, out = _v5_export(tmp_path)
    before = _tree(out)
    with pytest.raises(RegistryError, match=r"is counted by f-15 and b-1"):
        export_family_histories(duckdb_path=duckdb_path, out_dir=out, registry=replace(load_registry(), families=(F15, dup)))
    assert _tree(out) == before


def test_the_index_must_list_exactly_the_built_families(tmp_path, stubbed, monkeypatch):
    monkeypatch.setattr(platform_family_history, "index_projection", lambda registry: {"families": [], "schema_version": 1})
    duckdb_path, out = _v5_export(tmp_path)
    before = _tree(out)
    with pytest.raises(RegistryError, match=r"index.json lists \[\] but the pass built \['f-15'\]"):
        export_family_histories(duckdb_path=duckdb_path, out_dir=out, registry=load_registry())
    assert _tree(out) == before


def test_the_pass_refuses_a_headline_window_unlike_the_registry(tmp_path, stubbed):
    shifted = replace(F15, headline=Headline("cumulative_actuals", 2015, 2023))
    duckdb_path, out = _v5_export(tmp_path)
    with pytest.raises(ValueError, match=r"^F-15 cumulative window FY2015–FY2024 differs from the registry headline FY2015–FY2023$"):
        export_family_histories(duckdb_path=duckdb_path, out_dir=out, registry=replace(load_registry(), families=(shifted,)))


def test_preview_builds_one_unpublished_family_without_an_index_and_refuses_the_site_dir(tmp_path, stubbed, monkeypatch):
    ratified = replace(B1, status="ratified", published_ruling_id=None)
    registry = replace(load_registry(), families=(F15, ratified))
    duckdb_path, out = _v5_export(tmp_path / "x", extra_rows=[B1_ROW], extra_series=[B1_SERIES])
    export_family_histories(duckdb_path=duckdb_path, out_dir=out, registry=registry, families=["b-1"], preview=True)
    assert (out / "json/b1_funding_history.json").is_file()
    assert not (out / INDEX_PATH).exists() and not (out / "json/f15_funding_history.json").exists()
    with pytest.raises(ValueError, match="preview"):
        export_family_histories(duckdb_path=duckdb_path, out_dir=out, registry=registry, families=["b-1"])
    with pytest.raises(ValueError, match="preview"):
        export_family_histories(duckdb_path=duckdb_path, out_dir=out, registry=registry, families=["f-15"], preview=True)
    monkeypatch.setattr(config, "SITE_DIR", tmp_path / "x")
    before = _tree(out)
    with pytest.raises(ValueError, match="site dir"):
        export_family_histories(duckdb_path=duckdb_path, out_dir=out, registry=registry, families=["b-1"], preview=True)
    assert _tree(out) == before
