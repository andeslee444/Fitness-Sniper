"""p1_era_line_map and its dbt tests, run on a hand-built lake (families
piece 1, spec §4.4, V3).

Each test renders the COMMITTED model / singular-test SQL (tests/dbt_render.py)
and runs it on a throwaway in-memory DuckDB holding the relations it reads:
stg_budget_lines (with migration 021's line_item_code), the lake's
budget_lines source (for source_cells), jbook_documents, and the seed
p1_era_code_decisions. Every singular test is shown to pass on the clean
fixture AND to fail on the defect it exists for.

The fixture lake (PB2019 + PB2020 era P-1, one PB2019 R-1 row, PB2024/PB2026
P-1 rows for the collision anchors and the JLTV successor):

  era key            ed    BA  code        title                 seed decision
  3010F-AF-L25       2019  05  F01500      F-15                  F01500|3010F||2019-2020 same_program
  3010F-AF-L79       2019  07  F01500      F-15                  (same row: an AP-style pair, two BAs)
  3010F-AF-L25       2020  05  F01500      F-15                  (same row)
  0300D-DSS-L21      2019  01  20          Major Equipment, DSS  20|0300D|DSS|2019-2019 same_program -> DCSA
  0300D-DTRA-L23     2019  01  20          Major Equipment, DTRA 20|0300D|DTRA|2019-2019 same_program -> DTRA
  2035A-ARMY-L5      2019  03  5600D15603  JLTV                  none -> undecided
"""
import duckdb
import pytest
from dbt_render import render_dbt_sql

from govbudget.jbooks.era_map import SEED_COLUMNS, keys_sha256

MODEL = "dbt/models/marts/p1_era_line_map.sql"
TESTS = "dbt/tests/{}.sql"

SHA_2019 = "a" * 64
SHA_2020 = "b" * 64

# (exhibit, fiscal_year, account, organization, ba, pe_bli, title, amount_type,
#  amount, source_document_id, line_item_code, source_cells)
LAKE = [
    ("P-1", 2019, "3010F", "AF", "05", "3010F-AF-L25", "F-15", "fy_2019_total", 100.0, "271", "F01500", "AO40"),
    ("P-1", 2019, "3010F", "AF", "05", "3010F-AF-L25", "F-15", "fy_2017_base_oco", 90.0, "271", "F01500", "O40"),
    ("P-1", 2019, "3010F", "AF", "07", "3010F-AF-L79", "F-15", "fy_2019_total", 50.0, "271", "F01500", "AO98,AO99"),
    ("P-1", 2020, "3010F", "AF", "05", "3010F-AF-L25", "F-15", "fy_2020_total_base_oco", 120.0, "282", "F01500", "AE41"),
    ("P-1", 2019, "0300D", "DSS", "01", "0300D-DSS-L21", "Major Equipment, DSS", "fy_2019_total", 7.0, "271", "20", "AO700"),
    ("P-1", 2019, "0300D", "DTRA", "01", "0300D-DTRA-L23", "Major Equipment, DTRA", "fy_2019_total", 5.0, "271", "20", "AO702"),
    ("P-1", 2019, "2035A", "ARMY", "03", "2035A-ARMY-L5", "JLTV", "fy_2019_total", 900.0, "271", "5600D15603", "AO300"),
    ("P-1R", 2019, "3010F", "AF", "05", "F01500", "F-15", "fy_2019_total", 10.0, "272", "F01500", "AO10"),
    ("R-1", 2019, "3600F", "AF", "07", "0207134F", "F-15E Squadrons", "fy_2019_total", 70.0, "270", None, "P9"),
    ("P-1", 2026, "0300D", "DCSA", "01", "20", "Major Equipment, DCSA", "fy_2026_total", 3.0, "1", "20", "Q5"),
    ("P-1", 2026, "0300D", "DTRA", "01", "20", "Major Equipment, DTRA", "fy_2026_total", 4.0, "1", "20", "Q6"),
    ("P-1", 2024, "2035A", "A", "01", "5731D15610", "Joint Light Tactical Vehicle", "fy_2024_request", 800.0, "76", "5731D15610", "S9"),
]


def _key(edition, era_key, ba, title):
    return (edition, era_key, ba, title)


F15_KEYS = [
    _key(2019, "3010F-AF-L25", "05", "F-15"),
    _key(2019, "3010F-AF-L79", "07", "F-15"),
    _key(2020, "3010F-AF-L25", "05", "F-15"),
]


def _seed_row(**values):
    row = {c: None for c in SEED_COLUMNS}
    row.update(decided_on="2026-10-02", decided_by="owner")
    row.update(values)
    return row


def _seed():
    return [
        _seed_row(decision_id="F01500|3010F||2019-2020", line_item_code="F01500", account="3010F",
                  first_edition="2019", last_edition="2020", decision="same_program",
                  n_keys="3", keys_sha256=keys_sha256(F15_KEYS), ruling="R-DEC-ERA-SAME"),
        _seed_row(decision_id="20|0300D|DSS|2019-2019", line_item_code="20", account="0300D",
                  organization="DSS", first_edition="2019", last_edition="2019",
                  decision="same_program", program_org="DCSA", n_keys="1",
                  keys_sha256=keys_sha256([_key(2019, "0300D-DSS-L21", "01", "Major Equipment, DSS")]),
                  ruling="R-DEC-ERA-B1"),
        _seed_row(decision_id="20|0300D|DTRA|2019-2019", line_item_code="20", account="0300D",
                  organization="DTRA", first_edition="2019", last_edition="2019",
                  decision="same_program", program_org="DTRA", n_keys="1",
                  keys_sha256=keys_sha256([_key(2019, "0300D-DTRA-L23", "01", "Major Equipment, DTRA")]),
                  ruling="R-DEC-ERA-SAME"),
    ]


DOCS = [
    ("271", SHA_2019, "fy2019/dod/p1_display.xlsx", "2019"),
    ("282", SHA_2020, "fy2020/dod/p1_display.xlsx", "2020"),
    ("272", "c" * 64, "fy2019/dod/p1r_display.xlsx", "2019"),
    ("270", "d" * 64, "fy2019/dod/r1_display.xlsx", "2019"),
    ("1", "e" * 64, "fy2026/dod/p1_display.xlsx", "2026"),
    ("76", "f" * 64, "fy2024/dod/p1_display.xlsx", "2024"),
    ("152", "9" * 64, "fy2025/dod/p1_display.xlsx", "2025"),
]


def _lake(lake=None, seed=None, docs=None) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(
        "create table stg_budget_lines (exhibit varchar, fiscal_year integer,"
        " account varchar, account_title varchar, organization varchar,"
        " budget_activity varchar, budget_activity_title varchar, pe_bli varchar,"
        " title varchar, amount_type varchar, amount_thousands double,"
        " source_document_id varchar, line_item_code varchar)"
    )
    con.execute(
        "create table lake__jbook_budget_lines (exhibit varchar, fiscal_year varchar,"
        " pe_bli varchar, amount_type varchar, source_cells varchar)"
    )
    for (ex, fy, acct, org, ba, pe, title, at, amt, doc, code, cells) in (LAKE if lake is None else lake):
        con.execute(
            "insert into stg_budget_lines values (?, ?, ?, null, ?, ?, null, ?, ?, ?, ?, ?, ?)",
            [ex, fy, acct, org, ba, pe, title, at, amt, doc, code],
        )
        con.execute(
            "insert into lake__jbook_budget_lines values (?, ?, ?, ?, ?)",
            [ex, str(fy), pe, at, cells],
        )
    con.execute(
        "create table lake__jbook_documents (id varchar, sha256 varchar, rel_path varchar,"
        " fiscal_year varchar)"
    )
    con.executemany("insert into lake__jbook_documents values (?, ?, ?, ?)", DOCS if docs is None else docs)
    con.execute(
        "create table p1_era_code_decisions ("
        + ", ".join(f"{c} varchar" for c in SEED_COLUMNS) + ")"
    )
    for row in (_seed() if seed is None else seed):
        con.execute(
            f"insert into p1_era_code_decisions values ({', '.join('?' * len(SEED_COLUMNS))})",
            [row[c] for c in SEED_COLUMNS],
        )
    con.execute("create table p1_era_line_map as " + render_dbt_sql(MODEL))
    return con


def _map(con) -> dict[tuple, dict]:
    cur = con.execute("select * from p1_era_line_map")
    cols = [d[0] for d in cur.description]
    return {(r[0], r[4]): dict(zip(cols, r)) for r in cur.fetchall()}


def _failures(con, test_name: str) -> list[tuple]:
    return con.execute(render_dbt_sql(TESTS.format(test_name))).fetchall()


def test_one_row_per_era_key_with_the_spec_columns():
    con = _lake()
    cols = [d[0] for d in con.execute("select * from p1_era_line_map limit 0").description]
    assert cols == [
        "edition", "account", "organization", "budget_activity", "era_key",
        "line_item_code", "filed_title", "program_key", "program_account", "program_org",
        "decision", "decision_id", "ruling", "keys_sha_ok", "successor_code",
        "source_document_sha256", "source_cells",
    ]
    assert sorted(_map(con)) == [
        (2019, "0300D-DSS-L21"), (2019, "0300D-DTRA-L23"), (2019, "2035A-ARMY-L5"),
        (2019, "3010F-AF-L25"), (2019, "3010F-AF-L79"), (2020, "3010F-AF-L25"),
    ]


def test_a_decision_binds_its_code_account_and_edition_range():
    m = _map(_lake())
    l25 = m[(2019, "3010F-AF-L25")]
    assert (l25["line_item_code"], l25["filed_title"], l25["program_key"]) == ("F01500", "F-15", "F01500")
    assert (l25["decision"], l25["decision_id"], l25["ruling"]) == (
        "same_program", "F01500|3010F||2019-2020", "R-DEC-ERA-SAME")
    assert l25["keys_sha_ok"] is True
    assert (l25["program_account"], l25["program_org"]) == (None, None)
    # a two-budget-activity pair and the next edition bind the same decision
    assert m[(2019, "3010F-AF-L79")]["decision_id"] == "F01500|3010F||2019-2020"
    assert m[(2020, "3010F-AF-L25")]["decision_id"] == "F01500|3010F||2019-2020"


def test_provenance_is_the_workbook_sha_and_the_column_i_cells():
    m = _map(_lake())
    l25 = m[(2019, "3010F-AF-L25")]
    assert l25["source_document_sha256"] == SHA_2019
    # two amount cells on row 40 -> one code cell
    assert l25["source_cells"] == "I40"
    # a key summed from two workbook rows lists both, in row order
    assert m[(2019, "3010F-AF-L79")]["source_cells"] == "I98,I99"
    assert m[(2020, "3010F-AF-L25")]["source_document_sha256"] == SHA_2020


def test_organization_narrows_a_decision_and_pins_ride_along():
    m = _map(_lake())
    dss, dtra = m[(2019, "0300D-DSS-L21")], m[(2019, "0300D-DTRA-L23")]
    assert (dss["decision_id"], dss["program_key"], dss["program_org"]) == (
        "20|0300D|DSS|2019-2019", "20", "DCSA")
    assert (dtra["decision_id"], dtra["program_org"]) == ("20|0300D|DTRA|2019-2019", "DTRA")


def test_a_key_no_decision_covers_is_undecided_and_carries_nothing():
    jltv = _map(_lake())[(2019, "2035A-ARMY-L5")]
    assert (jltv["decision"], jltv["decision_id"], jltv["program_key"], jltv["keys_sha_ok"]) == (
        "undecided", None, None, None)


def test_an_edition_outside_the_range_is_not_covered():
    seed = _seed()
    seed[0].update(decision_id="F01500|3010F||2019-2019", last_edition="2019", n_keys="2",
                   keys_sha256=keys_sha256(F15_KEYS[:2]))
    m = _map(_lake(seed=seed))
    assert m[(2019, "3010F-AF-L25")]["keys_sha_ok"] is True
    assert m[(2020, "3010F-AF-L25")]["decision"] == "undecided"


def test_exclusions_carry_no_program_key():
    seed = _seed()
    seed[0].update(decision="exclude_reused_code")
    assert _map(_lake(seed=seed))[(2019, "3010F-AF-L25")]["program_key"] is None


@pytest.mark.parametrize("lines", [
    # 'L1' sorts AFTER 'L10' as text ('|' > '0'): the hash sorts LINES, not tuples
    [(2019, "3010F-AF-L1", "05", "a"), (2019, "3010F-AF-L10", "05", "b")],
    # NULL budget activity and NULL title render as empty strings
    [(2019, "3010F-AF-L2", None, None), (2019, "3010F-AF-L3", "05", "F-15")],
    # non-ASCII, a pipe inside a title, mixed case
    [(2019, "3010F-AF-L4", "05", "Café | Équipement"), (2019, "3010F-AF-L5", "05", "a"),
     (2019, "3010F-AF-L6", "05", "B")],
])
def test_keys_sha_sql_agrees_with_era_map_keys_sha256(lines):
    lake = [("P-1", ed, "3010F", "AF", ba, key, title, "fy_2019_total", 1.0, "271", "CODE1", "AO7")
            for ed, key, ba, title in lines]
    seed = [_seed_row(decision_id="CODE1|3010F||2019-2019", line_item_code="CODE1", account="3010F",
                      first_edition="2019", last_edition="2019", decision="history_only",
                      n_keys=str(len(lines)), keys_sha256=keys_sha256(lines), ruling="R-DEC-ERA-HISTORY")]
    m = _map(_lake(lake=lake, seed=seed))
    assert {row["keys_sha_ok"] for row in m.values()} == {True}


def test_keys_sha_ok_turns_false_when_a_reviewed_title_changes():
    lake = [row if row[5] != "3010F-AF-L79" else row[:6] + ("F-15 (retitled)",) + row[7:] for row in LAKE]
    m = _map(_lake(lake=lake))
    assert {m[k]["keys_sha_ok"] for k in [(2019, "3010F-AF-L25"), (2019, "3010F-AF-L79"),
                                          (2020, "3010F-AF-L25")]} == {False}
    assert m[(2019, "0300D-DSS-L21")]["keys_sha_ok"] is True


# --- the singular tests: clean on the fixture -------------------------------

ALL_TESTS = [
    "assert_p1_era_map_grain_unique",
    "assert_p1_era_map_complete",
    "assert_p1_era_map_one_code",
    "assert_p1_era_map_decisions_no_overlap",
    "assert_p1_era_map_org_split",
    "assert_p1_era_map_collision_pinned",
    "assert_p1_era_map_successor_resolves",
    "assert_p1_era_map_p1r_crosscheck",
]


@pytest.mark.parametrize("test_name", ALL_TESTS)
def test_singular_test_passes_on_the_clean_fixture(test_name):
    assert _failures(_lake(), test_name) == []


def test_no_undecided_lists_undecided_and_stale_keys():
    # Not in ALL_TESTS: the clean fixture keeps one undecided key on purpose.
    con = _lake()
    rows = _failures(con, "assert_p1_era_map_no_undecided")
    assert [(r[0], r[1], r[6]) for r in rows] == [(2019, "2035A-ARMY-L5", "undecided")]
    con.execute("update p1_era_line_map set keys_sha_ok = false where era_key = '0300D-DSS-L21'")
    assert len(_failures(con, "assert_p1_era_map_no_undecided")) == 2


# --- the singular tests: each fails on its defect ---------------------------

def test_grain_unique_fails_on_a_duplicate_key():
    con = _lake()
    con.execute("insert into p1_era_line_map select * from p1_era_line_map where era_key = '3010F-AF-L79'")
    assert _failures(con, "assert_p1_era_map_grain_unique") == [(2019, "3010F-AF-L79", 2)]


def test_complete_fails_on_a_dropped_key():
    con = _lake()
    con.execute("delete from p1_era_line_map where era_key = '2035A-ARMY-L5'")
    assert [r[:2] for r in _failures(con, "assert_p1_era_map_complete")] == [
        ("lake era key missing from the map", "2019/2035A-ARMY-L5")]


def test_complete_pins_the_corpus_counts_once_all_seven_workbooks_are_registered():
    docs = DOCS + [(str(900 + ed), str(ed) * 16, f"fy{ed}/dod/p1_display.xlsx", str(ed))
                   for ed in (2017, 2018, 2021, 2022, 2023)]
    rows = _failures(_lake(docs=docs), "assert_p1_era_map_complete")
    assert ("edition key count differs from the full corpus", "2019", "989", "5") in rows
    assert len([r for r in rows if r[0] == "edition key count differs from the full corpus"]) == 7


def test_complete_fails_when_a_decision_covers_a_different_key_count():
    docs = DOCS + [(str(900 + ed), str(ed) * 16, f"fy{ed}/dod/p1_display.xlsx", str(ed))
                   for ed in (2017, 2018, 2021, 2022, 2023)]
    seed = _seed()
    seed[0]["n_keys"] = "4"
    rows = _failures(_lake(seed=seed, docs=docs), "assert_p1_era_map_complete")
    assert ("decision covers a different number of keys than were reviewed",
            "F01500|3010F||2019-2020", "4", "3") in rows


def test_one_code_fails_when_one_key_prints_two_codes():
    lake = [row if not (row[5] == "3010F-AF-L25" and row[7] == "fy_2017_base_oco")
            else row[:10] + ("F01501",) + row[11:] for row in LAKE]
    rows = _failures(_lake(lake=lake), "assert_p1_era_map_one_code")
    assert [(r[0], r[1], r[2]) for r in rows] == [(2019, "3010F-AF-L25", 2)]


@pytest.mark.parametrize("mutate, failure", [
    (lambda s: s.append(dict(s[0], decision_id="F01500|3010F||2020-2020", first_edition="2020")),
     "ranges overlap"),
    (lambda s: s[0].update(decision="same_programme"), "malformed row"),
    (lambda s: s[0].update(decision_id="F01500|3010F|AF|2019-2020"), "malformed row"),
    (lambda s: s[0].update(first_edition="2016", decision_id="F01500|3010F||2016-2020"), "malformed row"),
    (lambda s: s[0].update(ruling="R-DEC-OTHER"), "malformed row"),
    (lambda s: s[0].update(decided_by="claude"), "malformed row"),
    (lambda s: s[0].update(keys_sha256="ABC"), "malformed row"),
    (lambda s: s.append(dict(s[1])), "duplicate decision_id"),
])
def test_decisions_no_overlap_fails_on_a_bad_seed(mutate, failure):
    seed = _seed()
    mutate(seed)
    con = duckdb.connect()
    con.execute("create table p1_era_code_decisions (" + ", ".join(f"{c} varchar" for c in SEED_COLUMNS) + ")")
    for row in seed:
        con.execute(f"insert into p1_era_code_decisions values ({', '.join('?' * len(SEED_COLUMNS))})",
                    [row[c] for c in SEED_COLUMNS])
    assert failure in {r[0] for r in _failures(con, "assert_p1_era_map_decisions_no_overlap")}


def test_org_split_fails_when_one_decision_spans_two_organizations():
    seed = [row for row in _seed() if row["line_item_code"] != "20"] + [
        _seed_row(decision_id="20|0300D||2019-2019", line_item_code="20", account="0300D",
                  first_edition="2019", last_edition="2019", decision="same_program",
                  program_org="DCSA", n_keys="2", keys_sha256="0" * 64, ruling="R-DEC-ERA-B1")]
    rows = _failures(_lake(seed=seed), "assert_p1_era_map_org_split")
    # '20' is a PB2026 organization-collision code, so only the first leg fires
    assert rows == [("one decision covers several organizations", "20|0300D||2019-2019", 2019, 2,
                     "DSS,DTRA")]


# PB2019 code '15' — no PB2026 collision, so its grain keeps no organization —
# printed by DISA and by TJS (the measured PB2021–PB2023 shape).
FIFTEEN_LAKE = [
    ("P-1", 2019, "0300D", "DISA", "01", "0300D-DISA-L12", "Joint Forces Headquarters - DODIN",
     "fy_2019_total", 40.0, "271", "15", "AO650"),
    ("P-1", 2019, "0300D", "TJS", "01", "0300D-TJS-L50", "Major Equipment - TJS Cyber",
     "fy_2019_total", 9.0, "271", "15", "AO690"),
]


def _fifteen(org, era_key, title, decision, ruling):
    return _seed_row(decision_id=f"15|0300D|{org}|2019-2019", line_item_code="15", account="0300D",
                     organization=org, first_edition="2019", last_edition="2019", decision=decision,
                     n_keys="1", keys_sha256=keys_sha256([_key(2019, era_key, "01", title)]),
                     ruling=ruling)


def test_org_split_fails_when_two_organizations_would_sum_into_one_page():
    disa = _fifteen("DISA", "0300D-DISA-L12", "Joint Forces Headquarters - DODIN",
                    "same_program", "R-DEC-ERA-SAME")
    tjs = _fifteen("TJS", "0300D-TJS-L50", "Major Equipment - TJS Cyber", "same_program", "R-DEC-ERA-B1")
    lake = LAKE + FIFTEEN_LAKE
    rows = _failures(_lake(lake=lake, seed=_seed() + [disa, tjs]), "assert_p1_era_map_org_split")
    assert rows == [("two organizations would sum into one page", "15", 2019, 2, "DISA,TJS")]
    # one organization same_program, the other history_only: clean
    tjs.update(decision="history_only")
    assert _failures(_lake(lake=lake, seed=_seed() + [disa, tjs]), "assert_p1_era_map_org_split") == []


def test_collision_pinned_fails_on_a_missing_or_foreign_pin():
    seed = _seed()
    seed[1]["program_org"] = None                       # DSS chain left unpinned
    seed[2]["program_org"] = "DSS"                      # pinned to an org PB2026 does not report
    seed[0]["program_account"] = "3010F"                # pin on a code that never collides
    rows = _failures(_lake(seed=seed), "assert_p1_era_map_collision_pinned")
    assert sorted((r[0], r[2]) for r in rows) == [
        ("organization-collision code without a usable organization pin", "0300D-DSS-L21"),
        ("organization-collision code without a usable organization pin", "0300D-DTRA-L23"),
        ("pin on a code that is not a PB2026 collision code", "3010F-AF-L25"),
        ("pin on a code that is not a PB2026 collision code", "3010F-AF-L25"),
        ("pin on a code that is not a PB2026 collision code", "3010F-AF-L79"),
    ]


def test_collision_pinned_lets_a_history_only_chain_keep_its_own_organization():
    seed = _seed()
    seed[1].update(decision="history_only", program_org="DSS", ruling="R-DEC-ERA-B1")
    assert _failures(_lake(seed=seed), "assert_p1_era_map_collision_pinned") == []


def test_successor_resolves_fails_on_an_unknown_successor():
    seed = _seed() + [_seed_row(
        decision_id="5600D15603|2035A||2019-2019", line_item_code="5600D15603", account="2035A",
        first_edition="2019", last_edition="2019", decision="same_program", n_keys="1",
        keys_sha256=keys_sha256([_key(2019, "2035A-ARMY-L5", "03", "JLTV")]),
        successor_code="5731D15610", successor_account="2035A",
        successor_evidence="PB2026 OPA BA1 P-40 line 5731D15610, PDF p.100", ruling="R-DEC-ERA-B1")]
    assert _failures(_lake(seed=seed), "assert_p1_era_map_successor_resolves") == []
    seed[-1]["successor_account"] = "2033A"
    rows = _failures(_lake(seed=seed), "assert_p1_era_map_successor_resolves")
    assert rows == [("successor absent from PB2024-PB2026 under its account",
                     "5600D15603|2035A||2019-2019", "5731D15610", "2033A")]
    seed[-1]["successor_evidence"] = None
    assert ("successor recorded without its account or evidence"
            in {r[0] for r in _failures(_lake(seed=seed), "assert_p1_era_map_successor_resolves")})


def test_p1r_crosscheck_fails_on_a_code_the_p1_does_not_print():
    lake = LAKE + [("P-1R", 2019, "2035A", "ARMY", "03", "9999X00001", "Ghost", "fy_2019_total",
                    1.0, "272", "9999X00001", "AO11")]
    rows = _failures(_lake(lake=lake), "assert_p1_era_map_p1r_crosscheck")
    assert [r[:4] for r in rows] == [
        ("P-1R triple absent from the era map and not allow-listed", 2019, "2035A", "9999X00001")]


def test_p1r_crosscheck_allow_list_must_stay_exact_on_the_real_corpus():
    docs = DOCS + [("189", "1" * 64, "fy2017/dod/p1_display.xlsx", "2017"),
                   ("190", "2" * 64, "fy2017/dod/p1r_display.xlsx", "2017")]
    rows = _failures(_lake(docs=docs), "assert_p1_era_map_p1r_crosscheck")
    assert sorted(r[3] for r in rows) == [
        "4000M12800", "8190G01506", "8635G15325", "9221F00001", "9693B01001"]
    assert {r[0] for r in rows} == {"allow-listed triple is no longer an exception"}
