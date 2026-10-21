"""R-DEC-LINK-2026-10-21 (owner, 2026-10-21): explicit per-pair line rulings.

"approved, would process with recommendation to approve all" — the owner
withdrew the 7 verified wrong evidence-graded links (production or long-lead
contracts on aircraft-modification lines, and one O&M support task order on
two modification lines) and the 34 `fpds-ap` production-on-modification-line
links, and allowed the legitimate subsystem buys a modification line makes
itself. The rulings live in dbt/seeds/link_line_rulings.csv, one row per
(award_piid, pe_bli); audit_link_grading reads them:

  * a `withdraw` ruling grades the link 'low' (not published) whatever any
    other rule would say, and binds every row of the pair (every edition,
    every method) — the ruling is about the PAIR;
  * its demotion_reason is 'precision_sample_refuted' when a held-out
    precision sample refuted the pair (R-DEC-110b/110c: the export's tally
    keys on exactly that value and keeps the link in the tier it was
    tallied in, so the withdrawal never flatters the figure that caught it),
    otherwise the new 'line_activity_mismatch';
  * an `allow` ruling changes nothing: it records that a person read a pair
    the recurrence gate (assert_no_production_award_on_modification_line)
    flags and ruled it correct;
  * a grade an adjudication already set to low or reject keeps that grade
    and no reason (the adjudication is the reason), as before.

Also here: the SQL of the three build-stopping tests the rulings come with
(the conflict test, the recurrence gate, the refuted-sibling gate) run
against a throwaway DuckDB, and the seed's own well-formedness test.
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import duckdb

from test_dbt_link_grading import (
    ANN,
    AWARD_COLS,
    REVIEW_COLS,
    RULING_COLS,
    _grade,
    _grade_rows,
    _grading_sql,
    rev,
    sample,
    survivor,
)

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "dbt" / "seeds" / "link_line_rulings.csv"
FPDS = "fpds-ap"
LINE = "line_activity_mismatch"
SAMPLE = "precision_sample_refuted"


# ── the grading ──────────────────────────────────────────────────────────────

def test_a_withdraw_ruling_grades_the_link_low_with_line_activity_mismatch():
    """An announcement link its pipeline upholds (it would publish high) and
    an fpds-ap medium link, both ruled withdrawn and never sampled: neither
    publishes, and the reason is the ruling's."""
    g = _grade(
        awards=[("ANN_HIGH", "0592", ANN, "high"),
                ("FPDS_MED", "F03500", FPDS, "medium"),
                ("CONTROL", "0592", ANN, "high")],
        reviews=[survivor("ANN_HIGH", pe="0592"), survivor("CONTROL", pe="0592")],
        rulings=[("ANN_HIGH", "0592", "withdraw"),
                 ("FPDS_MED", "F03500", "withdraw")],
    )
    assert g["ANN_HIGH"] == ("low", "high", LINE)
    assert g["FPDS_MED"] == ("low", "medium", LINE)
    assert g["CONTROL"] == ("high", "high", None)


def test_a_withdrawn_pair_its_precision_sample_refuted_keeps_that_reason():
    """The export's precision tally keeps a link whose reason is exactly
    'precision_sample_refuted' in the tier it was tallied in, whether or not
    it still publishes (R-DEC-110b/110c). A withdrawal under any other reason
    would drop the study's 'refuted' verdict and flatter the figure: 57/61
    would read 57/60. So the sample's reason wins whenever the pair carries a
    refutation — even where the pipeline's own records would name another
    reason for a demotion to medium."""
    g = _grade(
        awards=[("ANN_REFUTED", "0593", ANN, "high"),
                ("ANN_MEDIUM_REFUTED", "C04000", ANN, "high"),
                ("ANN_PIPELINE_TOO", "0603", ANN, "high"),
                ("FPDS_REFUTED", "0505", FPDS, "medium")],
        reviews=[
            survivor("ANN_REFUTED", pe="0593"), sample("ANN_REFUTED", pe="0593"),
            survivor("ANN_MEDIUM_REFUTED", pe="C04000"),
            sample("ANN_MEDIUM_REFUTED", pe="C04000"),
            # the pipeline refuted the cited article too: as a medium
            # demotion its reason would be 'announcement_review_refuted'
            rev("ANN_PIPELINE_TOO", "link", "refuted"),
            sample("ANN_PIPELINE_TOO"),
            # drawn from another tier, attached to the fpds-ap row of the pair
            sample("FPDS_REFUTED", pe="0505", drawn="fpds-ap+account"),
        ],
        rulings=[("ANN_REFUTED", "0593", "withdraw"),
                 ("ANN_MEDIUM_REFUTED", "C04000", "withdraw"),
                 ("ANN_PIPELINE_TOO", "0603", "withdraw"),
                 ("FPDS_REFUTED", "0505", "withdraw")],
    )
    assert g["ANN_REFUTED"] == ("low", "high", SAMPLE)
    assert g["ANN_MEDIUM_REFUTED"] == ("low", "high", SAMPLE)
    assert g["ANN_PIPELINE_TOO"] == ("low", "high", SAMPLE)
    assert g["FPDS_REFUTED"] == ("low", "medium", SAMPLE)


def test_an_allow_ruling_changes_nothing():
    g = _grade(
        awards=[("ALLOW_HIGH", "0515", ANN, "high"),
                ("ALLOW_FPDS", "0505", FPDS, "medium"),
                ("ALLOW_REFUTED", "0603", ANN, "high")],
        reviews=[survivor("ALLOW_HIGH", pe="0515"),
                 survivor("ALLOW_REFUTED"), sample("ALLOW_REFUTED")],
        rulings=[("ALLOW_HIGH", "0515", "allow"),
                 ("ALLOW_FPDS", "0505", "allow"),
                 ("ALLOW_REFUTED", "0603", "allow")],
    )
    assert g["ALLOW_HIGH"] == ("high", "high", None)
    assert g["ALLOW_FPDS"] == ("medium", "medium", None)
    # an allow is not an uphold: the sample still demotes the pair
    assert g["ALLOW_REFUTED"] == ("medium", "high", SAMPLE)


def test_a_ruling_binds_its_pair_and_nothing_else():
    """The same award on another line, and another award on the same line,
    are other pairs: a ruling names one (award_piid, pe_bli)."""
    rows = _grade_rows(
        awards=[("AWD", "0592", ANN, "high"), ("AWD", "ATA000", ANN, "high"),
                ("OTHER", "0592", ANN, "high")],
        reviews=[survivor("AWD", pe="0592"), survivor("AWD", pe="ATA000"),
                 survivor("OTHER", pe="0592")],
        rulings=[("AWD", "0592", "withdraw")],
    )
    assert rows == {
        ("AWD", "0592"): ("low", "high", LINE),
        ("AWD", "ATA000"): ("high", "high", None),
        ("OTHER", "0592"): ("high", "high", None),
    }, rows


def test_a_withdraw_ruling_binds_every_edition_and_method_of_the_pair():
    """budget_line_awards is keyed (pe_bli, exhibit, fiscal_year, award_piid):
    a pair can carry several rows. The ruling is about the pair, so no row of
    it publishes — and a pair ruled twice still grades one row per link."""
    con = duckdb.connect()
    for table, cols in (("awards", AWARD_COLS), ("reviews", REVIEW_COLS),
                        ("rulings", RULING_COLS)):
        defs = ", ".join(f"{c.strip()} varchar" for c in cols.split(","))
        con.execute(f"create table {table} ({defs})")
    con.execute(
        "create table adjudications (award_piid varchar, pe_bli varchar,"
        " adjudicated_confidence varchar, award_verdict varchar,"
        " pair_reason varchar, basis varchar, evidence varchar,"
        " refuter_lenses_passed varchar, method varchar, adjudicated_at varchar)")
    for fy, method, conf in (("2026", ANN, "high"), ("2025", FPDS, "medium")):
        con.execute(
            "insert into awards values ('F03500', 'P-1', ?, 'F', 'AWD', 'X', 'U',"
            " '1', ?, ?, '1', 'r', '3010F')", [fy, method, conf])
    for ruling in ("withdraw", "allow"):
        con.execute(
            "insert into rulings values ('AWD', 'F03500', ?, 's', null, 'e',"
            " '2026-10-21', 'owner', 'R-DEC-LINK-2026-10-21')", [ruling])
    rows = con.execute(
        "select fiscal_year, method, confidence, demotion_reason from ("
        + _grading_sql() + ") order by fiscal_year").fetchall()
    con.close()
    assert rows == [(2025, FPDS, "low", LINE), (2026, ANN, "low", LINE)], rows


def test_an_adjudicated_unpublished_grade_is_not_relabelled_by_a_ruling():
    """A grade an adjudication set to low or reject is already out of
    publication and its reason is the adjudication; a ruling does not
    relabel it. An adjudicated grade that would publish is withdrawn like any
    other (the conflict test stops the build on a pinned-here pair)."""
    g = _grade(
        awards=[("REJ", "0603", ANN, "high"), ("LOW", "0603", "account", "medium"),
                ("ADJ_MED", "0603", "account+tokens", "high")],
        adjudications=[
            ("REJ", "0603", "reject", "contradicted", "contradicted", None),
            ("LOW", "0603", "low", "not_darpa", "account-only", None),
            ("ADJ_MED", "0603", "medium", "darpa_unpinned", "unpinned-pool", None),
        ],
        rulings=[("REJ", "0603", "withdraw"), ("LOW", "0603", "withdraw"),
                 ("ADJ_MED", "0603", "withdraw")],
    )
    assert g["REJ"] == ("reject", "high", None)
    assert g["LOW"] == ("low", "medium", None)
    assert g["ADJ_MED"] == ("low", "high", LINE)


# ── the seed itself ──────────────────────────────────────────────────────────

def _seed_rows() -> list[dict]:
    with SEED.open(newline="") as f:
        return list(csv.DictReader(f))


#: verify.md §1.1 — the 7 verified wrong evidence-graded links.
VERIFIED_WRONG = {
    ("N0001917C0001", "0592"), ("N0001925C0070", "0592"),
    ("N0001925C0070", "0593"), ("N0001917C0001", "0593"),
    ("N6134020C0007", "0549"), ("FA813423FB001", "C03200"),
    ("FA813423FB001", "C04000"),
}
#: verify.md §1.2 — the three "unclear" links stay as they are (owner review).
UNCLEAR = {("FA813423DB004", "C03200"), ("FA813423DB004", "C04000"),
           ("W58RGZ24C0021", "0756AA6601")}


def test_the_seed_carries_the_owners_rulings():
    rows = _seed_rows()
    assert list(rows[0]) == [c.strip() for c in RULING_COLS.split(",")]
    withdraw = {(r["award_piid"], r["pe_bli"]) for r in rows
                if r["ruling"] == "withdraw"}
    assert len(withdraw) == 41
    assert VERIFIED_WRONG <= withdraw
    by_species = Counter(r["species"] for r in rows if r["ruling"] == "withdraw")
    assert by_species == {"production_on_modification_line": 39,
                          "om_task_order_on_mod_line": 2}, by_species
    assert {r["species"] for r in rows if r["award_piid"] == "FA813423FB001"} == {
        "om_task_order_on_mod_line"}
    # sweep.md §2 A2: 34 fpds-ap rows on seven modification lines
    a2 = Counter(r["pe_bli"] for r in rows if r["ruling"] == "withdraw"
                 and (r["award_piid"], r["pe_bli"]) not in VERIFIED_WRONG)
    assert a2 == {"F03500": 16, "0505": 5, "0590": 4, "0596": 4,
                  "3264AA0252": 2, "0962C50700": 2, "6552C67500": 1}, a2
    assert not UNCLEAR & {(r["award_piid"], r["pe_bli"]) for r in rows}
    assert all(r["ruled_by"] == "owner" and r["ruled_on"] == "2026-10-21"
               and r["ruling_id"] == "R-DEC-LINK-2026-10-21" for r in rows)
    pairs = [(r["award_piid"], r["pe_bli"]) for r in rows]
    assert len(pairs) == len(set(pairs))


# ── the build-stopping tests, run against a throwaway DuckDB ────────────────

def _test_sql(name: str, tables: dict[str, str]) -> str:
    sql = (ROOT / "dbt" / "tests" / f"{name}.sql").read_text()
    for src, table in tables.items():
        sql = sql.replace(src, table)
    assert "{{" not in sql, f"unsubstituted macro left in {name}.sql"
    return sql


def _rulings_table(con, rulings):
    defs = ", ".join(f"{c.strip()} varchar" for c in RULING_COLS.split(","))
    con.execute(f"create table rulings ({defs})")
    for row in rulings:
        con.execute("insert into rulings values (?, ?, ?, ?, ?, ?, ?, ?, ?)", list(row))


def _ruling(piid, pe, ruling="withdraw", **kw):
    row = {"award_piid": piid, "pe_bli": pe, "ruling": ruling,
           "species": "production_on_modification_line", "correct_line": None,
           "evidence": "verify.md 1.1", "ruled_on": "2026-10-21",
           "ruled_by": "owner", "ruling_id": "R-DEC-LINK-2026-10-21"}
    row.update(kw)
    return tuple(row[c.strip()] for c in RULING_COLS.split(","))


def test_a_withdraw_ruling_on_a_pair_pinned_here_stops_the_build():
    """A two-lens adjudication pinned THIS pair; a line ruling withdrawing it
    is a conflict between two recorded judgments a person must settle — the
    build stops rather than silently letting either win."""
    con = duckdb.connect()
    con.execute(
        "create table adjudications (award_piid varchar, pe_bli varchar,"
        " adjudicated_confidence varchar, award_verdict varchar,"
        " pair_reason varchar, refuter_lenses_passed varchar)")
    con.executemany("insert into adjudications values (?, ?, ?, ?, ?, ?)", [
        ("PINNED", "0592", "high", "pinned", "pinned-here", "2"),
        ("PINNED_ONE_LENS", "0592", "high", "pinned", "pinned-here", "1"),
        ("POOL", "0592", "medium", "darpa_unpinned", "unpinned-pool", None),
        ("PINNED_ALLOWED", "0592", "high", "pinned", "pinned-here", "2"),
        ("PINNED_ELSEWHERE", "0592", "low", "pinned", "pinned-elsewhere:0593", None),
    ])
    _rulings_table(con, [
        _ruling("PINNED", "0592"), _ruling("PINNED_ONE_LENS", "0592"),
        _ruling("POOL", "0592"), _ruling("PINNED_ALLOWED", "0592", "allow"),
        _ruling("PINNED_ELSEWHERE", "0592"),
        # the pin is of another PE's pair
        _ruling("PINNED", "0593"),
    ])
    failures = sorted(con.execute("select award_piid, pe_bli from (" + _test_sql(
        "assert_link_line_withdraw_not_on_pinned_pair",
        {"{{ ref('link_line_rulings') }}": "rulings",
         "{{ source('lake', 'jbook_award_adjudications') }}": "adjudications"},
    ) + ")").fetchall())
    con.close()
    assert failures == [("PINNED", "0592"), ("PINNED_ONE_LENS", "0592")], failures


def test_a_malformed_or_duplicated_ruling_stops_the_build():
    con = duckdb.connect()
    _rulings_table(con, [
        _ruling("GOOD", "0592"), _ruling("GOOD_ALLOW", "0515", "allow"),
        _ruling("BAD_RULING", "0592", "withhold"),
        _ruling("NO_SPECIES", "0592", species=" "),
        _ruling("NO_EVIDENCE", "0592", evidence=None),
        _ruling("BAD_DATE", "0592", ruled_on="21 Oct 2026"),
        _ruling("NOT_OWNER", "0592", ruled_by="controller"),
        _ruling("NO_ID", "0592", ruling_id=""),
        _ruling(None, "0592"),
        _ruling("DUP", "0592"), _ruling("DUP", "0592", "allow"),
    ])
    failures = sorted(r[0] or "" for r in con.execute(
        "select award_piid from (" + _test_sql(
            "assert_link_line_rulings_well_formed",
            {"{{ ref('link_line_rulings') }}": "rulings"}) + ")").fetchall())
    con.close()
    assert failures == ["", "BAD_DATE", "BAD_RULING", "DUP", "DUP", "NOT_OWNER",
                        "NO_EVIDENCE", "NO_ID", "NO_SPECIES"], failures


def _gate_a(published, lines, contracts, rulings=()):
    """published: (piid, pe_bli, method, confidence, account); lines:
    (pe_bli, account, fiscal_year, budget_activity_title); contracts:
    (award_id_piid, prime_award_base_transaction_description)."""
    con = duckdb.connect()
    con.execute("create table published (award_piid varchar, pe_bli varchar,"
                " method varchar, confidence varchar, account varchar)")
    con.executemany("insert into published values (?, ?, ?, ?, ?)", published)
    con.execute("create table lines (pe_bli varchar, account varchar,"
                " fiscal_year integer, budget_activity_title varchar)")
    con.executemany("insert into lines values (?, ?, ?, ?)", lines)
    con.execute("create table contracts (award_id_piid varchar,"
                " prime_award_base_transaction_description varchar)")
    con.executemany("insert into contracts values (?, ?)", contracts)
    _rulings_table(con, rulings)
    rows = con.execute("select award_piid, pe_bli from (" + _test_sql(
        "assert_no_production_award_on_modification_line",
        {"{{ ref('fct_budget_to_awards') }}": "published",
         "{{ ref('stg_budget_lines') }}": "lines",
         "{{ source('lake', 'contracts') }}": "contracts",
         "{{ ref('link_line_rulings') }}": "rulings"}) + ")").fetchall()
    con.close()
    return rows


MOD = "Modification of aircraft"


def test_the_gate_flags_an_unruled_production_award_on_a_modification_line():
    """The species (verify.md 1.1, sweep.md 2): a published link of an
    evidence-graded method OR fpds-ap (the owner withdrew that species too) on
    a line whose latest budget activity is a modification activity, whose
    award's FPDS base description is end-item production or long-lead."""
    rows = _gate_a(
        published=[
            ("LOT12", "0592", ANN, "high", None),
            ("ALLOWED", "0515", ANN, "high", None),
            ("FPDS_LRIP", "F03500", FPDS, "medium", None),
            ("SUB_FRP", "0592", "subaward+lexicon", "medium", None),
            # boilerplate: FPDS contract-action text names "this modification"
            ("BOILERPLATE", "F03500", FPDS, "medium", None),
            ("MULTIYEAR", "3264AA0252", FPDS, "medium", None),
            ("PROCURE_N", "0549", ANN, "high", None),
            ("FRP_ACRONYM", "6552C67500", FPDS, "medium", None),
            # not the species
            ("KITS", "0505", FPDS, "medium", None),
            ("RETROFIT", "0592", ANN, "high", None),
            ("PRODUCTION_LINE", "0152", ANN, "high", None),
            ("OTHER_METHOD", "0592", "account+tokens", "medium", None),
            ("SUPPORT", "0592", ANN, "high", None),
            ("NOW_PRODUCTION", "0999", ANN, "high", None),
            ("NOW_MOD", "0998", ANN, "high", None),
        ],
        lines=[
            ("0592", "1506N", 2026, MOD), ("0515", "1506N", 2026, MOD),
            ("F03500", "3010F", 2026, "Modification of inservice aircraft"),
            ("3264AA0252", "2031A", 2026, MOD), ("0549", "1506N", 2026, MOD),
            ("6552C67500", "2032A", 2026, "Modification of missiles"),
            ("0505", "1506N", 2026, MOD), ("0152", "1506N", 2026, "Combat aircraft"),
            # the LATEST edition's activity decides
            ("0999", "1506N", 2024, MOD), ("0999", "1506N", 2026, "Combat aircraft"),
            ("0998", "1506N", 2024, "Combat aircraft"), ("0998", "1506N", 2026, MOD),
        ],
        contracts=[
            ("LOT12", "LRIP LOT 12 ADVANCE ACQUISITION CONTRACT"),
            ("ALLOWED", "IRST LRIP II SYSTEMS"),
            ("FPDS_LRIP", "F-35 LRIP 8 AAC"),
            ("SUB_FRP", "TH-73A FULL RATE PRODUCTION"),
            ("BOILERPLATE", "THE PURPOSE OF THIS MODIFICATION IS TO AWARD F-35A"
             " LRIP 15 USAF  AIRCRAFT* LONG LEAD FUNDING"),
            ("MULTIYEAR", "CH-47F CARGO HELICOPTER MULTIYEAR II.  34 NEW BUILD"
             " HELICOPTERS"),
            ("PROCURE_N", "FIRM-FIXED-PRICE CONTRACT TO PROCURE 32 TH-73A AIRCRAFT"),
            ("FRP_ACRONYM", "FRP 9 UCA REQUIREMENT"),
            ("KITS", "LOT 40 F/A-18E AND EA-18G AIRCRAFT WITH AEA KITS"),
            ("RETROFIT", "LRIP 2 RETROFIT INSTALLATIONS"),
            ("PRODUCTION_LINE", "LRIP LOT 12 ADVANCE ACQUISITION CONTRACT"),
            ("OTHER_METHOD", "LRIP LOT 12 ADVANCE ACQUISITION CONTRACT"),
            ("SUPPORT", "F-35 MODS AND RETROFIT ANNUAL SUPPORT"),
            ("NOW_PRODUCTION", "LRIP 9 AIRCRAFT AAC"),
            ("NOW_MOD", "LRIP 9 AIRCRAFT AAC"),
        ],
        rulings=[_ruling("ALLOWED", "0515", "allow",
                         species="subsystem_production_on_own_mod_line")],
    )
    assert sorted(rows) == [
        ("BOILERPLATE", "F03500"), ("FPDS_LRIP", "F03500"),
        ("FRP_ACRONYM", "6552C67500"), ("LOT12", "0592"),
        ("MULTIYEAR", "3264AA0252"), ("NOW_MOD", "0998"),
        ("PROCURE_N", "0549"), ("SUB_FRP", "0592"),
    ], rows


def test_the_gate_reports_a_link_once_whatever_fans_it_out():
    """A NULL-account link on a code two accounts share, and a pair two
    editions carry, are one failure row each (select distinct)."""
    rows = _gate_a(
        published=[("LOT12", "0592", ANN, "high", None),
                   ("LOT12", "0592", ANN, "high", None)],
        lines=[("0592", "1506N", 2026, MOD), ("0592", "1507N", 2026, MOD)],
        contracts=[("LOT12", "LRIP LOT 12 ADVANCE ACQUISITION CONTRACT"),
                   ("LOT12", "LRIP LOT 12 ADVANCE ACQUISITION CONTRACT")],
    )
    assert rows == [("LOT12", "0592")], rows


def _gate_b(published, reviews, rulings=()):
    con = duckdb.connect()
    con.execute("create table published (award_piid varchar, pe_bli varchar,"
                " method varchar, confidence varchar)")
    con.executemany("insert into published values (?, ?, ?, ?)", published)
    defs = ", ".join(f"{c.strip()} varchar" for c in REVIEW_COLS.split(","))
    con.execute(f"create table reviews ({defs})")
    for row in reviews:
        con.execute("insert into reviews values (?, ?, ?, ?, ?, ?, ?, ?, ?, null,"
                    " 'f', ?)", list(row))
    _rulings_table(con, rulings)
    rows = con.execute("select award_piid, pe_bli from (" + _test_sql(
        "assert_refuted_pair_siblings_ruled",
        {"{{ ref('fct_budget_to_awards') }}": "published",
         "{{ source('lake', 'jbook_announcement_link_reviews') }}": "reviews",
         "{{ ref('link_line_rulings') }}": "rulings"}) + ")").fetchall()
    con.close()
    return sorted(rows)


def test_a_published_sibling_of_a_refuted_pair_needs_a_ruling():
    """D2 (verify.md 5.4 amendment 2): the precision study refuted
    (N0001917C0001, 0593); the twin link (N0001917C0001, 0592) cites the SAME
    announcement and stayed high, because a refutation binds only its own
    pair (R-DEC-110c). Such a sibling must carry a person's ruling — withdraw
    or allow — or the build stops. A record that names the article but whose
    card cites another one, another award, another article, the refuted pair
    itself and a sibling refuted in its own right are not this shape."""
    A1, A2 = "1167080", "1236797"

    def cited(piid, pe, article, cites="True"):
        return (piid, pe, "P-1", "2026", "survivor_list", "link", "upheld",
                article, cites, None)

    def refuted(piid, pe):
        return (piid, pe, "P-1", "2026", "precision_sample", "link", "refuted",
                None, None, "drawn from the announcement+lexicon tier")

    published = [
        ("AWD", "0593", ANN, "medium"),           # the refuted pair itself
        ("AWD", "0592", ANN, "high"),             # its unruled sibling
        ("AWD", "ATA000", ANN, "high"),           # sibling, ruled allow
        ("AWD", "0147", ANN, "high"),             # cites another article
        ("AWD", "0152", ANN, "high"),             # names A1, card cites A2
        ("AWD", "0604840F", ANN, "medium"),       # refuted in its own right
        ("OTHER", "0592", ANN, "high"),           # another award, same article
        ("FB001", "C04000", ANN, "medium"),       # second cluster: refuted
        ("FB001", "C03200", ANN, "high"),         # its unruled sibling
    ]
    reviews = [
        cited("AWD", "0593", A1), refuted("AWD", "0593"),
        cited("AWD", "0592", A1), cited("AWD", "ATA000", A1),
        cited("AWD", "0147", A2), cited("AWD", "0152", A1, cites="False"),
        cited("AWD", "0604840F", A1), refuted("AWD", "0604840F"),
        cited("OTHER", "0592", A1),
        cited("FB001", "C04000", "3348502"), refuted("FB001", "C04000"),
        cited("FB001", "C03200", "3348502"),
    ]
    rulings = [_ruling("AWD", "ATA000", "allow", species="exact_name")]
    assert _gate_b(published, reviews, rulings) == [
        ("AWD", "0592"), ("FB001", "C03200")]
    # ruled (withdraw or allow): the gate passes
    assert _gate_b(published, reviews, rulings + [
        _ruling("AWD", "0592"), _ruling("FB001", "C03200", "allow")]) == []


# ── (c) the pin, on the fixture lake built with dbt ──────────────────────────

#: verify.md 1.1 / sweep.md 4: the four withdrawn pairs a held-out precision
#: sample refuted (link_precision_samples ids 142, 123, 20, 22). They keep
#: 'precision_sample_refuted' so the export's tally keeps their verdicts.
SAMPLE_REFUTED = {("N0001917C0001", "0593"), ("FA813423FB001", "C04000"),
                  ("N0001909C0019", "0505"), ("N0001912C2001", "0590")}
#: the article each verified announcement link's card cites (verify.md 1.1)
CITED_ARTICLE = {
    ("N0001917C0001", "0592"): "1167080", ("N0001917C0001", "0593"): "1167080",
    ("N0001925C0070", "0592"): "3976306", ("N0001925C0070", "0593"): "3976306",
    ("N0001925C0070", "ATA000"): "3976306",
    ("N6134020C0007", "0549"): "2056101",
    ("FA813423FB001", "C03200"): "3348502", ("FA813423FB001", "C04000"): "3348502",
    ("FA813423DB004", "C03200"): "3348502",
    ("N0001915C0016", "0592"): "1001", ("N0001915C0036", "0515"): "1002",
}
#: links that must stay exactly as published (verify.md 1.2 / 1.3)
KEPT = {
    ("N0001915C0016", "0592"): ("announcement+lexicon", "high"),
    ("N0001925C0070", "ATA000"): ("announcement+lexicon", "high"),
    ("N0001915C0036", "0515"): ("announcement+lexicon", "high"),   # allow
    ("FA813423DB004", "C03200"): ("announcement+lexicon", "high"),  # unclear
    ("N0001912C0004", "F03500"): ("fpds-ap", "medium"),            # allow
}


def _append_lake_rows(data_dir: Path, file: str, rows: list[dict]):
    path = data_dir / "parquet" / "jbooks" / file
    con = duckdb.connect()
    try:
        con.execute(f"create table t as select * from read_parquet('{path}')")
        cols = [c[0] for c in con.execute("describe t").fetchall()]
        for row in rows:
            con.execute(
                f"insert into t ({', '.join(cols)}) values"
                f" ({', '.join('?' for _ in cols)})",
                [row.get(c) for c in cols])
        con.execute(f"copy t to '{path}' (format parquet)")
    finally:
        con.close()


def test_the_fixture_lake_withdraws_every_ruled_pair_and_nothing_else(tmp_path):
    """(c) R-DEC-LINK-2026-10-21 end to end: the 41 withdrawn pairs, as the
    live lake carries them (the 7 verified announcement links graded high by
    the loader and each upheld by its wave survivor record; the 34 fpds-ap
    links at medium), the four precision-sample refutations, and the links
    that must stay. After `dbt build` — every test included, the recurrence
    and refuted-sibling gates among them — no withdrawn pair publishes; the
    four refuted pairs record 'precision_sample_refuted' (graded low, so the
    export's tally keeps their verdicts); the rest record
    'line_activity_mismatch'; and every kept link publishes as before."""
    from test_dbt_build import make_lake
    from test_dbt_link_grading import _build

    make_lake(tmp_path)
    withdraw = [(r["award_piid"], r["pe_bli"]) for r in _seed_rows()
                if r["ruling"] == "withdraw"]
    assert len(withdraw) == 41
    links = {pair: (("announcement+lexicon", "high") if pair in VERIFIED_WRONG
                    else ("fpds-ap", "medium")) for pair in withdraw}
    links.update(KEPT)
    _append_lake_rows(tmp_path, "budget_line_awards.parquet", [
        {"pe_bli": pe, "exhibit": "P-1", "fiscal_year": "2026",
         "organization": "N", "award_piid": piid, "recipient_name": "X",
         "recipient_uei": "U", "matched_obligation": "1", "method": method,
         "confidence": conf, "score": "1", "rationale": "fixture"}
        for (piid, pe), (method, conf) in sorted(links.items())])
    reviews = [
        {"award_piid": piid, "pe_bli": pe, "exhibit": "P-1", "fiscal_year": "2026",
         "record_kind": "survivor_list", "reviewer_verdict": "link",
         "adversarial_verdict": "upheld", "upholds": "True",
         "article_id": article, "cites_reviewed_article": "True",
         "source_file": "data/research/announcements/wave2_result.json"}
        for (piid, pe), article in sorted(CITED_ARTICLE.items())]
    reviews += [
        {"award_piid": piid, "pe_bli": pe, "exhibit": "P-1", "fiscal_year": "2026",
         "record_kind": "precision_sample", "reviewer_verdict": "link",
         "adversarial_verdict": "refuted", "upholds": "False",
         "source_file": "2026-09-04"}
        for piid, pe in sorted(SAMPLE_REFUTED)]
    _append_lake_rows(tmp_path, "announcement_link_reviews.parquet", reviews)

    result, db = _build(tmp_path)
    out = result.stdout + result.stderr
    assert result.returncode == 0, out
    for gate in ("assert_no_production_award_on_modification_line",
                 "assert_refuted_pair_siblings_ruled",
                 "assert_link_line_withdraw_not_on_pinned_pair",
                 "assert_link_line_rulings_well_formed"):
        assert f"PASS {gate}" in result.stdout, gate
    con = duckdb.connect(str(db), read_only=True)
    try:
        published = {(p, b): (m, c) for p, b, m, c in con.sql(
            "select award_piid, pe_bli, method, confidence"
            " from fct_budget_to_awards").fetchall()}
        graded = {(p, b): (c, r) for p, b, c, r in con.sql(
            "select award_piid, pe_bli, confidence, demotion_reason"
            " from audit_link_grading").fetchall()}
    finally:
        con.close()
    assert not set(withdraw) & set(published), sorted(set(withdraw) & set(published))
    assert {pair: graded[pair] for pair in withdraw} == {
        pair: ("low", SAMPLE if pair in SAMPLE_REFUTED else LINE)
        for pair in withdraw}
    assert {pair: published.get(pair) for pair in KEPT} == KEPT
