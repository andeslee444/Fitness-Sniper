"""R-DEC-SHAREDTITLE (controller ruling, 2026-09-26, under the owner's
2026-09-25 delegation): fct_program_lobbying's program_title for a budget-line
code two or more programs share names EVERY member, never min(title).

fct_program_lobbying is keyed on the bare pe_bli (a lobbying mention carries a
code, and the link it renders opens /program/{pe_bli}/ — the disambiguation
stub on a shared code). Until this ruling the mart deduped dim_programs to one
row per code with min(title), so a mention on '1350' read "Infantry Weapons
Ammunition" even when the words that matched came from "Missile Industrial
Facilities", and /company/{slug}/ plus the /data/ fct_program_lobbying.parquet
copied that one member's name. The label now mirrors
export_site.shared_code_program_label, which /filing/ already renders: the
members' distinct non-empty titles in (account, organization) order, joined
" / ". A code that names one program keeps its title byte for byte.

dbt/tests/assert_program_lobbying_shared_title_names_every_member.sql fails
the build on a label that omits a member or names anything else.

The unit tests run the committed SQL against a throwaway DuckDB; the last one
builds the fixture lake with dbt.
"""
import os
import subprocess
from pathlib import Path

import duckdb

from test_dbt_build import make_lake

ROOT = Path(__file__).resolve().parents[1]

MENTION_COLS = "filing_uuid, pe_bli, matched_term, evidence_kind, description_snippet"
FILING_COLS = (
    "filing_uuid, url, client_name, family_key_guess, match_method, filing_year"
)

# (pe_bli, account, org, title) — the live shapes, 2026-09-26
PROGRAMS = [
    ("SOLO", "0400", "DARPA", "Defense Research Sciences"),
    # account-split, and account order is NOT title order: min(title) picked
    # the 1508N member on every '1350' mention (the live code)
    ("1350", "1508N", "N", "Infantry Weapons Ammunition"),
    ("1350", "1507N", "N", "Missile Industrial Facilities"),
    ("0145", "1506N", "N", "F/A-18E/F (Fighter) Hornet"),
    ("0145", "1508N", "N", "General Purpose Bombs"),
    # organization-split: one account, three organizations — and one member's
    # title is a prefix of both others' (the live '30')
    ("30", "0300D", "OSD", "Major Equipment, OSD"),
    ("30", "0300D", "DTRA", "Other Major Equipment"),
    ("30", "0300D", "DMACT", "Major Equipment"),
    # one program name in two appropriations (the live '2292'): one name
    ("2292", "1507N", "N", "Naval Strike Missile (NSM)"),
    ("2292", "1109N", "N", "Naval Strike Missile (NSM)"),
    # a member with no title never blanks its sibling
    ("GAP", "0100", "A", ""),
    ("GAP", "0200", "A", "Named Member"),
]

EXPECTED = {
    "SOLO": "Defense Research Sciences",
    "1350": "Missile Industrial Facilities / Infantry Weapons Ammunition",
    "0145": "F/A-18E/F (Fighter) Hornet / General Purpose Bombs",
    "30": "Major Equipment / Other Major Equipment / Major Equipment, OSD",
    "2292": "Naval Strike Missile (NSM)",
    "GAP": "Named Member",
    # a mention on a code dim_programs does not carry names nothing
    "NOPROG": None,
}


def _model_sql() -> str:
    """dbt/models/marts/fct_program_lobbying.sql with its source()/ref()
    macros replaced by plain tables — the SQL dbt builds, not a restatement."""
    sql = (ROOT / "dbt" / "models" / "marts" / "fct_program_lobbying.sql").read_text()
    for macro, table in {
        "{{ source('influence', 'lda_program_mentions') }}": "mentions",
        "{{ source('influence', 'lda_filings') }}": "filings",
        "{{ ref('dim_programs') }}": "progs",
    }.items():
        sql = sql.replace(macro, table)
    assert "{{" not in sql, "unsubstituted macro left in fct_program_lobbying.sql"
    return sql


def _test_sql() -> str:
    path = ROOT / "dbt" / "tests" / "assert_program_lobbying_shared_title_names_every_member.sql"
    sql = path.read_text()
    for macro, table in {
        "{{ ref('fct_program_lobbying') }}": "lobbying",
        "{{ ref('dim_programs') }}": "progs",
    }.items():
        sql = sql.replace(macro, table)
    assert "{{" not in sql, f"unsubstituted macro left in {path.name}"
    return sql


def _con(programs):
    con = duckdb.connect()
    con.execute("create table progs (pe_bli varchar, account varchar, org varchar, title varchar)")
    con.executemany("insert into progs values (?, ?, ?, ?)", programs)
    return con


def _lobbying(programs, codes):
    """One mention per code on one filing; returns {pe_bli: program_title}
    and the full row list."""
    con = _con(programs)
    con.execute(f"create table mentions ({', '.join(c.strip() + ' varchar' for c in MENTION_COLS.split(','))})")
    con.execute(f"create table filings ({', '.join(c.strip() + ' varchar' for c in FILING_COLS.split(','))})")
    con.execute("insert into filings values ('F1', 'https://lda.test/F1', 'CLIENT',"
                " 'FAMILY', 'exact_family', '2025')")
    con.executemany(
        "insert into mentions values ('F1', ?, ?, 'pe_literal', 'snippet')",
        [(code, code) for code in codes],
    )
    rows = con.execute(
        "select pe_bli, program_title, matched_term, family_key, filing_url"
        " from (" + _model_sql() + ") order by pe_bli"
    ).fetchall()
    con.close()
    return {r[0]: r[1] for r in rows}, rows


def test_a_shared_code_names_every_member_in_account_then_organization_order():
    titles, rows = _lobbying(PROGRAMS, list(EXPECTED))
    assert titles == EXPECTED, titles
    # the mart's grain is untouched: one row per mention, nothing fanned out
    assert len(rows) == len(EXPECTED)
    assert {r[3] for r in rows} == {"FAMILY"}


def test_the_label_does_not_depend_on_the_order_dim_programs_returns_rows():
    forward, _ = _lobbying(PROGRAMS, list(EXPECTED))
    backward, _ = _lobbying(list(reversed(PROGRAMS)), list(EXPECTED))
    assert forward == backward


def test_the_label_is_the_one_filing_pages_render():
    """export_site.shared_code_program_label is what /filing/ prints for a
    shared-code mention (prog_titles); /company/ reads this mart's label, so
    the two must be the same string for the same member order."""
    from govbudget.export_site import shared_code_program_label

    by_code: dict[str, list] = {}
    for pe_bli, account, org, title in sorted(
        PROGRAMS, key=lambda r: (r[0], r[1], r[2], r[3])
    ):
        by_code.setdefault(pe_bli, []).append(title)
    titles, _ = _lobbying(PROGRAMS, list(by_code))
    assert titles == {code: shared_code_program_label(t) for code, t in by_code.items()}


# ── the dbt test ────────────────────────────────────────────────────────────

def _failures(programs, lobbying_rows):
    con = _con(programs)
    con.execute("create table lobbying (filing_uuid varchar, pe_bli varchar,"
                " program_title varchar)")
    con.executemany("insert into lobbying values (?, ?, ?)", lobbying_rows)
    out = con.execute("select pe_bli, failure from (" + _test_sql() + ") order by 1, 2").fetchall()
    con.close()
    return out


def test_the_dbt_test_passes_on_the_models_own_labels():
    _titles, rows = _lobbying(PROGRAMS, list(EXPECTED))
    assert _failures(PROGRAMS, [("F1", r[0], r[1]) for r in rows]) == []


def test_the_dbt_test_fails_on_a_label_that_omits_a_member():
    # the min(title) labels the mart published before the ruling
    assert _failures(PROGRAMS, [
        ("F1", "1350", "Infantry Weapons Ammunition"),
        ("F1", "30", "Major Equipment"),
        ("F1", "0145", "F/A-18E/F (Fighter) Hornet"),
    ]) == [
        ("0145", "omits a member"),
        ("1350", "omits a member"),
        # 'Major Equipment' is a substring of both siblings' titles: the
        # check matches whole " / "-bounded members, not substrings
        ("30", "omits a member"),
        ("30", "omits a member"),
    ]


def test_the_dbt_test_fails_on_a_missing_label_or_one_naming_a_non_member():
    assert _failures(PROGRAMS, [
        ("F1", "0145", None),
        ("F1", "SOLO", "Defense Research Sciences / Something Else"),
        # one name said twice is not a truer label
        ("F1", "2292", "Naval Strike Missile (NSM) / Naval Strike Missile (NSM)"),
    ]) == [
        ("0145", "omits a member"),
        ("0145", "omits a member"),
        ("2292", "names something that is not a member"),
        ("SOLO", "names something that is not a member"),
    ]


# ── the fixture lake, built with dbt ────────────────────────────────────────

def test_the_fixture_lake_labels_its_shared_code_mention(tmp_path):
    make_lake(tmp_path)
    # add a mention on the fixture's shared '3010' (LPD Flight II in 1611N,
    # Shipboard Tactical Communications in 1810N) beside the two it has
    mentions = tmp_path / "parquet" / "influence" / "lda_program_mentions.parquet"
    duckdb.sql(
        f"copy (select * from read_parquet('{mentions}') union all"
        " select 'uuid-lda-001', '3010', '3010', 'pe_literal',"
        " 'Issues related to budget line 3010.')"
        f" to '{tmp_path}/mentions.parquet' (format parquet)"
    )
    (tmp_path / "mentions.parquet").replace(mentions)
    (tmp_path / "duckdb").mkdir()
    db = tmp_path / "duckdb" / "test.duckdb"
    env = {
        **os.environ,
        "GOVBUDGET_DATA": str(tmp_path),
        "GOVBUDGET_DUCKDB": str(db),
        "DBT_TARGET_PATH": str(tmp_path / "dbt_target"),
        "DBT_LOG_PATH": str(tmp_path / "dbt_logs"),
    }
    result = subprocess.run(
        ["uv", "run", "dbt", "build", "--project-dir", "dbt", "--profiles-dir", "dbt"],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "assert_program_lobbying_shared_title_names_every_member" in result.stdout
    con = duckdb.connect(str(db), read_only=True)
    try:
        assert dict(con.sql(
            "select pe_bli, program_title from fct_program_lobbying"
        ).fetchall())["3010"] == "LPD Flight II / Shipboard Tactical Communications"
    finally:
        con.close()
