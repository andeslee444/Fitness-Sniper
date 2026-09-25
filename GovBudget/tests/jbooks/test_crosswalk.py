import inspect
from decimal import Decimal
from pathlib import Path

import duckdb
import psycopg
import pytest

from govbudget import config
from govbudget.jbooks import crosswalk as crosswalk_module
from govbudget.jbooks.crosswalk import (
    CrosswalkResult,
    crosswalk_org,
    plan_crosswalk_org,
)

AWARD_COLS = (
    "contract_transaction_unique_key, award_id_piid, federal_action_obligation,"
    " federal_accounts_funding_this_award, transaction_description,"
    " prime_award_base_transaction_description, recipient_name, recipient_uei,"
    " awarding_sub_agency_name, action_date"
)


# Fixture action_dates sit in federal FY2026 (Oct 2025 - Sep 2026) because
# every seed_* helper below stamps its budget line at PB edition 2026 and,
# since #78, the default window is the line's own edition FY. The `fy=2024`
# directory name in these helpers is not a hive partition and is never read.
def make_award_parquet(tmp_path: Path) -> Path:
    out = tmp_path / "contracts" / "fy=2024"
    out.mkdir(parents=True)
    duckdb.sql(
        f"""
        copy (select * from (values
          ('K1','HR001124C0001','5000000','097-0400','DEFENSE RESEARCH SCIENCES MATHEMATICS PROGRAM',
           'BASIC MATHEMATICS SCIENCES INITIATIVE','ACME RESEARCH LLC','UEIDARPA1',
           'Defense Advanced Research Projects Agency','2026-03-01'),
          ('K2','HR001124C0002','100','021-2040','UNRELATED ARMY THING',
           'TANK PARTS','TANKCO','UEITANK','Dept of the Army','2026-04-01'),
          ('K3','HR001124C0003','750000','021-1319;097-0400','RESEARCH SUPPORT SERVICES',
           'SOMETHING ELSE ENTIRELY','BETA LABS','UEIBETA',
           'Defense Advanced Research Projects Agency','2026-05-01')
        ) t({AWARD_COLS})) to '{out}/part.parquet' (format parquet)
        """
    )
    return tmp_path


def make_award_parquet_with_dates(tmp_path: Path, rows: list[tuple]) -> str:
    """Award parquet fixture with caller-supplied rows (full AWARD_COLS tuples,
    in AWARD_COLS order) so a test can control action_date precisely — needed
    for federal-fiscal-year boundary tests. Unlike make_award_parquet, this
    returns the ready-to-use glob string rather than the bare tmp_path.
    """
    out = tmp_path / "contracts" / "fy=2024"
    out.mkdir(parents=True, exist_ok=True)
    values_sql = ", ".join(
        "(" + ", ".join("'" + str(v).replace("'", "''") + "'" for v in row) + ")"
        for row in rows
    )
    duckdb.sql(
        f"""
        copy (select * from (values {values_sql}) t({AWARD_COLS}))
        to '{out}/part.parquet' (format parquet)
        """
    )
    return str(tmp_path / "contracts" / "*" / "*.parquet")


def make_award_parquet_nullable_dates(tmp_path: Path, rows: list[tuple]) -> str:
    """Like make_award_parquet_with_dates, but a Python None in any column is
    written as a SQL NULL — the other helper would write the string 'None'.
    The NULL is cast to varchar so a column that is NULL in every row still
    lands as VARCHAR in the parquet (DuckDB types a bare NULL literal as
    INTEGER, which would change the action_date column type)."""
    out = tmp_path / "contracts" / "fy=2024"
    out.mkdir(parents=True, exist_ok=True)

    def lit(v):
        if v is None:
            return "cast(NULL as varchar)"
        return "'" + str(v).replace("'", "''") + "'"

    values_sql = ", ".join(
        "(" + ", ".join(lit(v) for v in row) + ")" for row in rows
    )
    duckdb.sql(
        f"""
        copy (select * from (values {values_sql}) t({AWARD_COLS}))
        to '{out}/part.parquet' (format parquet)
        """
    )
    return str(tmp_path / "contracts" / "*" / "*.parquet")


def make_navy_award_parquet(tmp_path: Path) -> Path:
    """Navy parquet: one award under 017-1319, one under 097-1319 only."""
    out = tmp_path / "contracts" / "fy=2024"
    out.mkdir(parents=True, exist_ok=True)
    duckdb.sql(
        f"""
        copy (select * from (values
          ('N1','N0001824C0001','2000000','017-1319','NAVAL RESEARCH SCIENCES PROGRAM',
           'OCEAN RESEARCH INITIATIVE','NAVY LABS LLC','UEINAV1',
           'Department of the Navy','2026-06-01'),
          ('N2','N0001824C0002','500000','097-1319','DEFENSE WIDE SCIENCES THING',
           'SOME DEFENSE PROGRAM','DEFENSE CO','UEIDEF1',
           'Under Secretary of Defense','2026-07-01')
        ) t({AWARD_COLS})) to '{out}/part.parquet' (format parquet)
        """
    )
    return tmp_path


def seed_budget(pg_dsn):
    with psycopg.connect(pg_dsn) as con:
        con.execute(
            "insert into jbook_documents (org, exhibit_family, fiscal_year, title, source_url)"
            " values ('DARPA','rdte',2026,'seed.pdf','https://example.test/seed.pdf')"
        )
        doc_id = con.execute("select max(id) from jbook_documents").fetchone()[0]
        con.execute(
            "insert into budget_lines (exhibit, fiscal_year, account, organization,"
            " pe_bli, title, amount_type, amount_thousands, source_document_id) values"
            " ('R-1',2026,'0400','DARPA','0601101E','DEFENSE RESEARCH SCIENCES',"
            " 'fy_2024_actuals',%s,%s)",
            (Decimal("280494"), doc_id),
        )


def seed_budget_with_detail(pg_dsn):
    """Seed DARPA budget line with a detail row for project title tokens."""
    with psycopg.connect(pg_dsn) as con:
        # Insert jbook_documents row first (minimal, no real file) — the
        # budget line needs its id for provenance (migration 005)
        con.execute(
            "insert into jbook_documents (org, exhibit_family, fiscal_year, title, source_url)"
            " values ('DARPA','rdte',2026,'darpa_test.pdf','https://example.test/darpa.pdf')"
        )
        doc_id = con.execute("select id from jbook_documents").fetchone()[0]
        con.execute(
            "insert into budget_lines (exhibit, fiscal_year, account, organization,"
            " pe_bli, title, amount_type, amount_thousands, source_document_id) values"
            " ('R-1',2026,'0400','DARPA','0601101E','DEFENSE RESEARCH SCIENCES',"
            " 'fy_2024_actuals',%s,%s)",
            (Decimal("280494"), doc_id),
        )
        # Insert extraction_runs row
        con.execute(
            "insert into extraction_runs (document_id, tier, tool_versions, status)"
            " values (%s,1,'{}','success')",
            (doc_id,),
        )
        run_id = con.execute("select id from extraction_runs").fetchone()[0]
        # Insert budget_line_details row with project_title
        con.execute(
            "insert into budget_line_details"
            " (pe_bli, project_number, project_title, scenario, amount_millions,"
            "  xml_path, extraction_run_id, document_id, superseded)"
            " values ('0601101E','CCS-02','MATHEMATICS AND COMPUTER SCIENCES',"
            "         'PriorYear',1,'ProgramElement[0]',%s,%s,false)",
            (run_id, doc_id),
        )


def seed_navy_budget(pg_dsn):
    """Seed Navy budget line with account '1319N' (service-letter N -> 017)."""
    with psycopg.connect(pg_dsn) as con:
        con.execute(
            "insert into jbook_documents (org, exhibit_family, fiscal_year, title, source_url)"
            " values ('NAVY','rdte',2026,'navy.pdf','https://example.test/navy.pdf')"
        )
        doc_id = con.execute("select max(id) from jbook_documents").fetchone()[0]
        con.execute(
            "insert into budget_lines (exhibit, fiscal_year, account, organization,"
            " pe_bli, title, amount_type, amount_thousands, source_document_id) values"
            " ('R-1',2026,'1319N','NAVY','0601152N','NAVY RESEARCH SCIENCES',"
            " 'fy_2024_actuals',%s,%s)",
            (Decimal("50000"), doc_id),
        )


def seed_mda_budget(pg_dsn):
    """Seed an MDA budget line whose account carries no service-letter suffix
    (agency comes straight from the caller-supplied treasury_agency)."""
    with psycopg.connect(pg_dsn) as con:
        con.execute(
            "insert into jbook_documents (org, exhibit_family, fiscal_year, title, source_url)"
            " values ('MDA','rdte',2026,'mda.pdf','https://example.test/mda.pdf')"
        )
        doc_id = con.execute("select max(id) from jbook_documents").fetchone()[0]
        con.execute(
            "insert into budget_lines (exhibit, fiscal_year, account, organization,"
            " pe_bli, title, amount_type, amount_thousands, source_document_id) values"
            " ('R-1',2026,'0603870','MDA','0603870C','BALLISTIC MISSILE DEFENSE MIDCOURSE',"
            " 'fy_2024_actuals',%s,%s)",
            (Decimal("10000"), doc_id),
        )


def seed_budget_with_quoted_account(pg_dsn):
    """A budget line whose account carries a single quote. budget_lines.account
    is `text not null` with no check constraint (migration 001 — verified live:
    the only constraints are the pkey, the 7-column unique and the FK), so the
    row inserts; the crosswalk turns it into fed_account "097-04'00"."""
    with psycopg.connect(pg_dsn) as con:
        con.execute(
            "insert into jbook_documents (org, exhibit_family, fiscal_year, title, source_url)"
            " values ('DARPA','rdte',2026,'quote.pdf','https://example.test/quote.pdf')"
        )
        doc_id = con.execute("select max(id) from jbook_documents").fetchone()[0]
        con.execute(
            "insert into budget_lines (exhibit, fiscal_year, account, organization,"
            " pe_bli, title, amount_type, amount_thousands, source_document_id) values"
            " ('R-1',2026,%s,'DARPA','0601QUOT','QUOTED ACCOUNT LINE',"
            " 'fy_2024_actuals',%s,%s)",
            ("04'00", Decimal("1"), doc_id),
        )


def test_crosswalk_matches_by_account_and_scores_confidence(pg_dsn, tmp_path):
    seed_budget_with_detail(pg_dsn)
    lake = make_award_parquet(tmp_path)
    n = crosswalk_org(
        pg_dsn, organization="DARPA", treasury_agency="097",
        award_glob=str(lake / "contracts" / "*" / "*.parquet"),
    )
    assert n == CrosswalkResult(written=2, skipped=0)  # K1 and K3 (097-0400 in accounts); K2 excluded
    with psycopg.connect(pg_dsn) as con:
        rows = {
            r[0]: r for r in con.execute(
                "select award_piid, confidence, recipient_name, matched_obligation"
                " from budget_line_awards where pe_bli='0601101E'"
            )
        }
    assert rows["HR001124C0001"][1] == "high"   # account + >=2 title-token overlap
    assert rows["HR001124C0003"][1] == "medium"  # account + DARPA sub-agency only
    assert rows["HR001124C0001"][3] == Decimal("5000000")


def test_crosswalk_is_idempotent(pg_dsn, tmp_path):
    seed_budget_with_detail(pg_dsn)
    lake = make_award_parquet(tmp_path)
    kwargs = dict(organization="DARPA", treasury_agency="097",
                  award_glob=str(lake / "contracts" / "*" / "*.parquet"))
    first = crosswalk_org(pg_dsn, **kwargs)
    second = crosswalk_org(pg_dsn, **kwargs)
    with psycopg.connect(pg_dsn) as con:
        n = con.execute("select count(*) from budget_line_awards").fetchone()[0]
    assert n == 2
    # Both runs WRITE both rows: the second is an update of two mechanical
    # rows, which the method guard allows, so nothing is skipped (#86).
    assert first == second == CrosswalkResult(written=2, skipped=0)


def test_crosswalk_navy_service_letter_maps_to_017(pg_dsn, tmp_path):
    """Fix C2: account '1319N' must resolve to agency 017, matching 017-1319 awards.

    The award under 097-1319 only must NOT match.
    """
    seed_navy_budget(pg_dsn)
    lake = make_navy_award_parquet(tmp_path)
    n = crosswalk_org(
        pg_dsn, organization="NAVY", treasury_agency="097",
        award_glob=str(lake / "contracts" / "*" / "*.parquet"),
    )
    # Only N1 (017-1319) should match; N2 (097-1319) must not
    assert n == CrosswalkResult(written=1, skipped=0)
    with psycopg.connect(pg_dsn) as con:
        rows = con.execute(
            "select award_piid from budget_line_awards where pe_bli='0601152N'"
        ).fetchall()
    piids = [r[0] for r in rows]
    assert "N0001824C0001" in piids    # 017-1319 award matched
    assert "N0001824C0002" not in piids  # 097-1319 award NOT matched


def test_crosswalk_small_token_not_high_confidence(pg_dsn, tmp_path):
    """Fix I1: 'small' is a stopword; generic-token coincidences must not reach 'high'.

    An award for 'SMALL DIAMETER BOMB INCREMENT II' vs a line titled
    'SMALL BUSINESS INNOVATION RESEARCH' should NOT be high confidence.
    """
    with psycopg.connect(pg_dsn) as con:
        con.execute(
            "insert into jbook_documents (org, exhibit_family, fiscal_year, title, source_url)"
            " values ('DARPA','rdte',2026,'sbir.pdf','https://example.test/sbir.pdf')"
        )
        doc_id = con.execute("select max(id) from jbook_documents").fetchone()[0]
        con.execute(
            "insert into budget_lines (exhibit, fiscal_year, account, organization,"
            " pe_bli, title, amount_type, amount_thousands, source_document_id) values"
            " ('R-1',2026,'0400','DARPA','0601SBIR','SMALL BUSINESS INNOVATION RESEARCH',"
            " 'fy_2024_actuals',%s,%s)",
            (Decimal("10000"), doc_id),
        )
    out = tmp_path / "contracts" / "fy=2024"
    out.mkdir(parents=True)
    duckdb.sql(
        f"""
        copy (select * from (values
          ('SB1','FA860124C0099','999999','097-0400',
           'SMALL DIAMETER BOMB INCREMENT II',
           'SMALL DIAMETER BOMB INCREMENT II','BOMB CO','UEIBOMB',
           'Defense Advanced Research Projects Agency','2026-08-01')
        ) t({AWARD_COLS})) to '{out}/part.parquet' (format parquet)
        """
    )
    crosswalk_org(
        pg_dsn, organization="DARPA", treasury_agency="097",
        award_glob=str(tmp_path / "contracts" / "*" / "*.parquet"),
    )
    with psycopg.connect(pg_dsn) as con:
        rows = con.execute(
            "select award_piid, confidence from budget_line_awards where pe_bli='0601SBIR'"
        ).fetchall()
    # The award may or may not match (sub-agency gives medium) but must not be high
    for piid, conf in rows:
        assert conf != "high", f"Expected not-high for stopword-only match, got {conf} for {piid}"


def test_fy_filter_uses_federal_fiscal_year(pg_dsn, tmp_path):
    """Fix #75a: the FY filter must use the FEDERAL fiscal year (Oct-Dec belong
    to the NEXT FY), not the calendar year of action_date.

    action_date 2023-11-15 is federal FY2024: a 2024..2024 window must include
    it, a 2023..2023 window must not.
    """
    seed_budget(pg_dsn)
    glob = make_award_parquet_with_dates(
        tmp_path,
        [(
            "K9", "HR001124C0009", "1", "097-0400", "X", "Y", "Z", "U",
            "Defense Advanced Research Projects Agency", "2023-11-15",
        )],
    )
    n_2024 = crosswalk_org(
        pg_dsn, organization="DARPA", treasury_agency="097", award_glob=glob,
        fy_start=2024, fy_end=2024,
    )
    n_2023 = crosswalk_org(
        pg_dsn, organization="DARPA", treasury_agency="097", award_glob=glob,
        fy_start=2023, fy_end=2023,
    )
    assert n_2024 == CrosswalkResult(1, 0) and n_2023 == CrosswalkResult(0, 0)


def test_fy_filter_september_stays_in_same_fy(pg_dsn, tmp_path):
    """Boundary check the other side of the Oct-Dec rollover: a September
    action_date belongs to the SAME calendar-year FY, not the next one."""
    seed_budget(pg_dsn)
    glob = make_award_parquet_with_dates(
        tmp_path,
        [(
            "K10", "HR001124C0010", "1", "097-0400", "X", "Y", "Z", "U",
            "Defense Advanced Research Projects Agency", "2024-09-15",
        )],
    )
    n_2024 = crosswalk_org(
        pg_dsn, organization="DARPA", treasury_agency="097", award_glob=glob,
        fy_start=2024, fy_end=2024,
    )
    n_2025 = crosswalk_org(
        pg_dsn, organization="DARPA", treasury_agency="097", award_glob=glob,
        fy_start=2025, fy_end=2025,
    )
    assert n_2024 == CrosswalkResult(1, 0) and n_2025 == CrosswalkResult(0, 0)


def test_multi_account_award_has_no_matched_obligation(pg_dsn, tmp_path):
    """Fix #75b: an award funded from more than one federal account has no
    single 'the' obligation for this account — matched_obligation must be
    NULL rather than the (wrong) sum across every account on the award."""
    seed_budget_with_detail(pg_dsn)
    lake = make_award_parquet(tmp_path)   # K3 is funded from '021-1319;097-0400'
    crosswalk_org(
        pg_dsn, organization="DARPA", treasury_agency="097",
        award_glob=str(lake / "contracts" / "*" / "*.parquet"),
    )
    with psycopg.connect(pg_dsn) as pg:
        ob = pg.execute(
            "select matched_obligation from budget_line_awards"
            " where award_piid='HR001124C0003'"
        ).fetchone()[0]
    assert ob is None


def test_single_account_award_still_has_matched_obligation(pg_dsn, tmp_path):
    """Companion to the multi-account fix: a single-account award must keep
    its (real) obligation — the fix must not null out everything."""
    seed_budget_with_detail(pg_dsn)
    lake = make_award_parquet(tmp_path)   # K1 is funded from '097-0400' only
    crosswalk_org(
        pg_dsn, organization="DARPA", treasury_agency="097",
        award_glob=str(lake / "contracts" / "*" / "*.parquet"),
    )
    with psycopg.connect(pg_dsn) as pg:
        ob = pg.execute(
            "select matched_obligation from budget_line_awards"
            " where award_piid='HR001124C0001'"
        ).fetchone()[0]
    assert ob == Decimal("5000000")


def test_subagency_aliases_come_from_seed(pg_dsn, tmp_path):
    """Fix #75c: sub-agency matching must come from data-seeds/
    org_subagency_aliases.csv, not a hardcoded DARPA clause. An MDA budget
    line matched against an award whose awarding_sub_agency_name is 'Missile
    Defense Agency' should reach medium confidence ONLY because the seed maps
    MDA -> 'missile defense agency' (the bare organization string 'mda' is
    not a substring of 'missile defense agency', so the old
    organization.lower()-in-sub_agency check alone would miss it)."""
    seed_mda_budget(pg_dsn)
    out = tmp_path / "contracts" / "fy=2024"
    out.mkdir(parents=True)
    duckdb.sql(
        f"""
        copy (select * from (values
          ('M1','MDA0024C0001','2000000','097-0603870',
           'UNRELATED DESCRIPTION ONE','UNRELATED DESCRIPTION TWO',
           'INTERCEPT SYSTEMS LLC','UEIMDA1',
           'Missile Defense Agency','2026-02-01')
        ) t({AWARD_COLS})) to '{out}/part.parquet' (format parquet)
        """
    )
    crosswalk_org(
        pg_dsn, organization="MDA", treasury_agency="097",
        award_glob=str(tmp_path / "contracts" / "*" / "*.parquet"),
    )
    with psycopg.connect(pg_dsn) as con:
        row = con.execute(
            "select method, confidence from budget_line_awards"
            " where pe_bli='0603870C' and award_piid='MDA0024C0001'"
        ).fetchone()
    assert row is not None, "expected the MDA award to be linked via sub-agency alias"
    assert row == ("account+subagency", "medium")


def test_crosswalk_does_not_overwrite_non_mechanical_methods(pg_dsn, tmp_path):
    """Addendum ruling 1: fpds-ap, announcement+lexicon and subaward+lexicon
    links share the upsert key space with the mechanical crosswalk. A re-run
    must never clobber one of those rows even when the mechanical pass would
    also produce that exact (pe_bli, award) pair."""
    seed_budget_with_detail(pg_dsn)
    lake = make_award_parquet(tmp_path)
    with psycopg.connect(pg_dsn) as con:
        con.execute(
            "insert into budget_line_awards"
            " (pe_bli, exhibit, fiscal_year, organization, award_piid,"
            "  recipient_name, recipient_uei, matched_obligation, method,"
            "  confidence, score, rationale)"
            " values ('0601101E','R-1',2026,'DARPA','HR001124C0001',"
            "  'ACME RESEARCH LLC','UEIDARPA1',5000000,'announcement+lexicon',"
            "  'high',null,'defense.gov contract announcement 123456')"
        )
    # The mechanical crosswalk would also produce this pair as
    # account+tokens/high (same as test_crosswalk_matches_by_account_and_scores_confidence);
    # the guard must leave the pre-existing non-mechanical row untouched.
    crosswalk_org(
        pg_dsn, organization="DARPA", treasury_agency="097",
        award_glob=str(lake / "contracts" / "*" / "*.parquet"),
    )
    with psycopg.connect(pg_dsn) as con:
        method, confidence = con.execute(
            "select method, confidence from budget_line_awards"
            " where pe_bli='0601101E' and award_piid='HR001124C0001'"
        ).fetchone()
    assert (method, confidence) == ("announcement+lexicon", "high")


def test_subagency_seed_rejects_empty_alias(tmp_path, monkeypatch):
    """Fix round 1, finding 5: an empty alias in the seed CSV must raise, not
    load silently. `"" in sub_agency` is True for every award (empty string
    is a substring of anything in Python), so an unvalidated empty alias
    would silently promote the whole organization's matches to medium."""
    bad_csv = tmp_path / "org_subagency_aliases.csv"
    bad_csv.write_text("organization,alias\nDARPA,advanced research projects\nMDA,\n")
    monkeypatch.setattr(crosswalk_module, "_ALIASES_CSV", bad_csv)
    with pytest.raises(ValueError, match="MDA"):
        crosswalk_module._load_subagency_aliases()


def test_subagency_seed_rejects_empty_organization(tmp_path, monkeypatch):
    """Companion: an empty organization is equally unusable — it can never
    be looked up by crosswalk_org's own `organization` argument, so it must
    also raise rather than load as a silent no-op alias."""
    bad_csv = tmp_path / "org_subagency_aliases.csv"
    bad_csv.write_text("organization,alias\n,missile defense agency\n")
    monkeypatch.setattr(crosswalk_module, "_ALIASES_CSV", bad_csv)
    with pytest.raises(ValueError, match="empty organization"):
        crosswalk_module._load_subagency_aliases()


# --------------------------------------------------------------------------
# #78 — default award-FY window (each line's own PB edition FY), --all-years,
# loud lone bounds. Every seed_* helper above stamps its budget line at PB
# edition 2026, so under the #78 default only an FY2026 award may link.
# --------------------------------------------------------------------------

DARPA_SUB = "Defense Advanced Research Projects Agency"

# Two awards under 097-0400: one in federal FY2026 (Oct 2025 - Sep 2026), one
# in federal FY2024. AWARD_COLS order.
TWO_FY_ROWS = [
    ("K26", "HR001126C0001", "1", "097-0400", "X", "Y", "Z", "U", DARPA_SUB, "2026-03-01"),
    ("K24", "HR001124C0001", "1", "097-0400", "X", "Y", "Z", "U", DARPA_SUB, "2024-03-01"),
]


def seed_budget_editions(pg_dsn, years):
    """One DARPA R-1 line for pe_bli 0601101E in EACH given PB edition year,
    all pointing at one jbook_documents row (budget_lines.source_document_id
    is NOT NULL since migration 005)."""
    with psycopg.connect(pg_dsn) as con:
        con.execute(
            "insert into jbook_documents (org, exhibit_family, fiscal_year, title, source_url)"
            " values ('DARPA','rdte',2026,'editions.pdf','https://example.test/editions.pdf')"
        )
        doc_id = con.execute("select max(id) from jbook_documents").fetchone()[0]
        for fy in years:
            con.execute(
                "insert into budget_lines (exhibit, fiscal_year, account, organization,"
                " pe_bli, title, amount_type, amount_thousands, source_document_id) values"
                " ('R-1',%s,'0400','DARPA','0601101E','DEFENSE RESEARCH SCIENCES',"
                " 'fy_2024_actuals',%s,%s)",
                (fy, Decimal("1"), doc_id),
            )


def _links(pg_dsn):
    with psycopg.connect(pg_dsn) as con:
        return con.execute(
            "select fiscal_year, award_piid, rationale from budget_line_awards"
            " order by fiscal_year, award_piid"
        ).fetchall()


def test_default_window_is_the_lines_own_edition_fy(pg_dsn, tmp_path):
    """#78: with no fy_start/fy_end and no all_years, a PB2026 line matches
    ONLY awards whose federal FY is 2026 — the FY2024 award is excluded."""
    seed_budget(pg_dsn)                       # edition fiscal_year = 2026
    glob = make_award_parquet_with_dates(tmp_path, TWO_FY_ROWS)
    n = crosswalk_org(pg_dsn, organization="DARPA", treasury_agency="097", award_glob=glob)
    assert n == CrosswalkResult(written=1, skipped=0)
    rows = _links(pg_dsn)
    assert [(fy, piid) for fy, piid, _r in rows] == [(2026, "HR001126C0001")]
    assert rows[0][2].endswith("; award FY2026")


def test_default_window_is_per_line_edition_not_per_run(pg_dsn, tmp_path):
    """#78: the window is resolved PER LINE inside the loop. Two editions of
    the same PE (PB2024 and PB2026) each link only their own FY's award —
    never the cross pairs (2024-line x 2026-award, 2026-line x 2024-award)
    that the unbounded run produced."""
    seed_budget_editions(pg_dsn, [2024, 2026])
    glob = make_award_parquet_with_dates(tmp_path, TWO_FY_ROWS)
    n = crosswalk_org(pg_dsn, organization="DARPA", treasury_agency="097", award_glob=glob)
    assert n == CrosswalkResult(written=2, skipped=0)
    assert [(fy, piid) for fy, piid, _r in _links(pg_dsn)] == [
        (2024, "HR001124C0001"), (2026, "HR001126C0001"),
    ]


def test_all_years_matches_every_loaded_award_year(pg_dsn, tmp_path):
    """all_years=True is the explicit opt-in to the pre-#78 behaviour, and it
    says so in rationale with the SAME wording the 124,502 mechanical DARPA
    rows already in budget_line_awards carry."""
    seed_budget(pg_dsn)
    glob = make_award_parquet_with_dates(tmp_path, TWO_FY_ROWS)
    n = crosswalk_org(
        pg_dsn, organization="DARPA", treasury_agency="097", award_glob=glob,
        all_years=True,
    )
    assert n == CrosswalkResult(written=2, skipped=0)
    rows = _links(pg_dsn)
    assert [piid for _fy, piid, _r in rows] == ["HR001124C0001", "HR001126C0001"]
    assert all(r.endswith("; all loaded award years") for _fy, _p, r in rows)


def test_explicit_window_overrides_the_per_line_default(pg_dsn, tmp_path):
    """An explicit fy_start/fy_end pins ONE window for every line (a PB2026
    line can be pointed at FY2024 awards on purpose) and names it."""
    seed_budget(pg_dsn)
    glob = make_award_parquet_with_dates(tmp_path, TWO_FY_ROWS)
    n = crosswalk_org(
        pg_dsn, organization="DARPA", treasury_agency="097", award_glob=glob,
        fy_start=2024, fy_end=2024,
    )
    assert n == CrosswalkResult(written=1, skipped=0)
    rows = _links(pg_dsn)
    assert [(fy, piid) for fy, piid, _r in rows] == [(2026, "HR001124C0001")]
    assert rows[0][2].endswith("; award FY2024")


def test_lone_fy_bound_raises_instead_of_silently_ignoring(pg_dsn, tmp_path):
    """Pre-#78, fy_start without fy_end was silently dropped and the run went
    unbounded. Loud failure instead — and nothing is written. all_years on top
    of an explicit window is refused the same way."""
    seed_budget(pg_dsn)
    glob = make_award_parquet_with_dates(tmp_path, TWO_FY_ROWS)
    with pytest.raises(ValueError, match="together"):
        crosswalk_org(
            pg_dsn, organization="DARPA", treasury_agency="097", award_glob=glob,
            fy_start=2024,
        )
    with pytest.raises(ValueError, match="all_years"):
        crosswalk_org(
            pg_dsn, organization="DARPA", treasury_agency="097", award_glob=glob,
            fy_start=2024, fy_end=2024, all_years=True,
        )
    assert _links(pg_dsn) == []


@pytest.mark.parametrize(
    ("kwargs", "per_edition"),
    [
        (dict(), [(2024, 1), (2026, 1)]),
        (dict(all_years=True), [(2024, 2), (2026, 2)]),
        (dict(fy_start=2024, fy_end=2024), [(2024, 1), (2026, 1)]),
    ],
    ids=["default", "all-years", "explicit-fy2024"],
)
def test_plan_matches_what_the_run_writes_and_writes_nothing_itself(
    pg_dsn, tmp_path, kwargs, per_edition,
):
    """#78 dry-run primitive: plan_crosswalk_org returns one LinePlan per
    budget line carrying the number of (line, award) pairs crosswalk_org
    would upsert under the SAME window, and touches Postgres only to read
    budget_lines. The last line is the anti-drift check — the planned total
    is exactly the number of upserts the run then issues."""
    seed_budget_editions(pg_dsn, [2024, 2026])
    glob = make_award_parquet_with_dates(tmp_path, TWO_FY_ROWS)
    kw = dict(organization="DARPA", treasury_agency="097", award_glob=glob, **kwargs)
    plan = plan_crosswalk_org(pg_dsn, **kw)
    assert len(plan) == 2
    assert sorted((p.fiscal_year, p.candidates) for p in plan) == per_edition
    assert {p.fed_account for p in plan} == {"097-0400"}
    assert _links(pg_dsn) == []                      # planning wrote nothing
    # Anti-drift: the planned pair count is exactly what the run ATTEMPTS to
    # upsert. On a clean table the method guard refuses nothing, so every
    # planned pair is a written link and skipped is 0 (#86).
    result = crosswalk_org(pg_dsn, **kw)
    assert result.written + result.skipped == sum(p.candidates for p in plan)
    assert result == CrosswalkResult(
        written=sum(p.candidates for p in plan), skipped=0)


# --------------------------------------------------------------------------
# #78 — `govbudget jbooks crosswalk` dispatch: --dry-run / --all-years / --yes
# --------------------------------------------------------------------------

def _wire_crosswalk_cli(monkeypatch, pg_dsn, tmp_path):
    """Point the CLI at the scratch DB and the fixture lake, and no-op the
    migrate() call cmd_jbooks makes first (cli.py:718-720) — the same pattern
    as tests/jbooks/test_cli_service.py::_wire_service_backfill."""
    import govbudget.jbooks.db
    from govbudget import config

    monkeypatch.setattr(govbudget.jbooks.db, "migrate", lambda *a, **kw: [])
    monkeypatch.setattr(config, "PG_DSN", pg_dsn)
    # cmd_jbooks builds the glob as config.PARQUET_DIR / "contracts" / "*" /
    # "*.parquet" — exactly where make_award_parquet_with_dates writes.
    monkeypatch.setattr(config, "PARQUET_DIR", tmp_path)


def _link_count(pg_dsn) -> int:
    with psycopg.connect(pg_dsn) as con:
        return con.execute("select count(*) from budget_line_awards").fetchone()[0]


def test_cli_default_window_writes_only_the_edition_fy(monkeypatch, pg_dsn, tmp_path, capsys):
    from govbudget import cli

    _wire_crosswalk_cli(monkeypatch, pg_dsn, tmp_path)
    seed_budget(pg_dsn)
    make_award_parquet_with_dates(tmp_path, TWO_FY_ROWS)
    cli.main(["jbooks", "crosswalk", "--org", "DARPA"])
    out = capsys.readouterr().out
    assert ("crosswalk DARPA: 1 links written, 0 skipped (evidence-graded rows"
            " kept); window=each line's own edition FY") in out
    assert "crosswalk total: 1 written, 0 skipped" in out
    assert _link_count(pg_dsn) == 1


def test_cli_dry_run_prints_the_plan_per_edition_and_writes_nothing(
    monkeypatch, pg_dsn, tmp_path, capsys,
):
    from govbudget import cli

    _wire_crosswalk_cli(monkeypatch, pg_dsn, tmp_path)
    seed_budget_editions(pg_dsn, [2024, 2026])
    make_award_parquet_with_dates(tmp_path, TWO_FY_ROWS)
    cli.main(["jbooks", "crosswalk", "--org", "DARPA", "--dry-run"])
    out = capsys.readouterr().out
    assert ("crosswalk DARPA: 2 line(s), projected 2 (line, award) pair(s);"
            " window=each line's own edition FY") in out
    assert "  edition FY2024: 1 line(s) -> 1 pair(s)" in out
    assert "  edition FY2026: 1 line(s) -> 1 pair(s)" in out
    assert "crosswalk projected total: 2 pair(s)" in out
    assert "crosswalk dry-run: nothing written" in out
    assert _link_count(pg_dsn) == 0


def test_cli_all_years_dry_run_shows_the_cross_join(monkeypatch, pg_dsn, tmp_path, capsys):
    """The plan is what makes the explosion visible BEFORE a write:
    2 line-editions x 2 awards = 4 under --all-years, 2 under the default."""
    from govbudget import cli

    _wire_crosswalk_cli(monkeypatch, pg_dsn, tmp_path)
    seed_budget_editions(pg_dsn, [2024, 2026])
    make_award_parquet_with_dates(tmp_path, TWO_FY_ROWS)
    cli.main(["jbooks", "crosswalk", "--org", "DARPA", "--all-years", "--dry-run"])
    out = capsys.readouterr().out
    assert ("crosswalk DARPA: 2 line(s), projected 4 (line, award) pair(s);"
            " window=all loaded award years") in out
    assert "crosswalk dry-run: nothing written" in out
    assert _link_count(pg_dsn) == 0


def test_cli_all_years_aborts_above_threshold_without_yes(monkeypatch, pg_dsn, tmp_path, capsys):
    from govbudget import cli

    _wire_crosswalk_cli(monkeypatch, pg_dsn, tmp_path)
    monkeypatch.setattr(crosswalk_module, "ALL_YEARS_ABORT_ROWS", 1)
    seed_budget(pg_dsn)
    make_award_parquet_with_dates(tmp_path, TWO_FY_ROWS)
    with pytest.raises(SystemExit) as e:
        cli.main(["jbooks", "crosswalk", "--org", "DARPA", "--all-years"])
    assert e.value.code == 2
    out = capsys.readouterr().out
    assert "crosswalk projected total: 2 pair(s)" in out
    assert "above the 1 abort threshold; nothing written" in out
    assert "--yes" in out
    assert _link_count(pg_dsn) == 0


def test_cli_all_years_with_yes_writes_past_threshold(monkeypatch, pg_dsn, tmp_path, capsys):
    from govbudget import cli

    _wire_crosswalk_cli(monkeypatch, pg_dsn, tmp_path)
    monkeypatch.setattr(crosswalk_module, "ALL_YEARS_ABORT_ROWS", 1)
    seed_budget(pg_dsn)
    make_award_parquet_with_dates(tmp_path, TWO_FY_ROWS)
    cli.main(["jbooks", "crosswalk", "--org", "DARPA", "--all-years", "--yes"])
    out = capsys.readouterr().out
    assert "crosswalk projected total: 2 pair(s)" in out
    assert ("crosswalk DARPA: 2 links written, 0 skipped (evidence-graded rows"
            " kept); window=all loaded award years") in out
    assert _link_count(pg_dsn) == 2


def test_cli_all_years_under_threshold_writes_without_yes(monkeypatch, pg_dsn, tmp_path):
    """The abort is a threshold, not a blanket refusal: a small --all-years
    plan writes without --yes."""
    from govbudget import cli

    _wire_crosswalk_cli(monkeypatch, pg_dsn, tmp_path)
    assert crosswalk_module.ALL_YEARS_ABORT_ROWS >= 2   # the real constant
    seed_budget(pg_dsn)
    make_award_parquet_with_dates(tmp_path, TWO_FY_ROWS)
    cli.main(["jbooks", "crosswalk", "--org", "DARPA", "--all-years"])
    assert _link_count(pg_dsn) == 2


def test_cli_default_window_aborts_above_threshold_without_yes(
    monkeypatch, pg_dsn, tmp_path, capsys,
):
    """Controller ruling 2026-09-11: the projected-row abort covers the
    DEFAULT per-line window too, not only --all-years. DARPA's default run
    plans 761,029 pairs — above the 500,000 threshold — so an unguarded
    default would be the same six-figure surprise --all-years is guarded
    against. Every mode plans first; every mode is refused above the
    threshold without --yes."""
    from govbudget import cli

    _wire_crosswalk_cli(monkeypatch, pg_dsn, tmp_path)
    monkeypatch.setattr(crosswalk_module, "ALL_YEARS_ABORT_ROWS", 0)
    seed_budget(pg_dsn)
    make_award_parquet_with_dates(tmp_path, TWO_FY_ROWS)
    with pytest.raises(SystemExit) as e:
        cli.main(["jbooks", "crosswalk", "--org", "DARPA"])
    assert e.value.code == 2
    out = capsys.readouterr().out
    assert "crosswalk projected total: 1 pair(s); window=each line's own edition FY" in out
    assert "above the 0 abort threshold; nothing written" in out
    assert "--yes" in out
    assert _link_count(pg_dsn) == 0
    # ...and the same plan writes when the operator says --yes.
    cli.main(["jbooks", "crosswalk", "--org", "DARPA", "--yes"])
    assert _link_count(pg_dsn) == 1


def test_cli_lone_fy_bound_exits_2(monkeypatch, pg_dsn, tmp_path, capsys):
    """--fy-start without --fy-end, and --all-years stacked on an explicit
    window, exit 2 with a message before any Postgres connection is opened."""
    from govbudget import cli

    _wire_crosswalk_cli(monkeypatch, pg_dsn, tmp_path)
    seed_budget(pg_dsn)
    make_award_parquet_with_dates(tmp_path, TWO_FY_ROWS)
    with pytest.raises(SystemExit) as e:
        cli.main(["jbooks", "crosswalk", "--org", "DARPA", "--fy-start", "2024"])
    assert e.value.code == 2
    assert "--fy-start and --fy-end must be given together" in capsys.readouterr().out
    with pytest.raises(SystemExit) as e2:
        cli.main(["jbooks", "crosswalk", "--org", "DARPA",
                  "--fy-start", "2024", "--fy-end", "2024", "--all-years"])
    assert e2.value.code == 2
    assert "--all-years cannot be combined with --fy-start/--fy-end" in capsys.readouterr().out
    assert _link_count(pg_dsn) == 0


# --------------------------------------------------------------------------
# Edition selector and window validation (merged 2026-09-25 from the
# award-refresh branch's bounded crosswalk, adapted to this implementation).
# --------------------------------------------------------------------------


@pytest.mark.parametrize("kwargs", [
    {"fy_start": 2026}, {"fy_end": 2026},
    {"fy_start": 2026, "fy_end": 2025},          # reversed: matched nothing, silently
    {"fy_start": 0, "fy_end": 2026}, {"fiscal_year": 2201},
    {"fy_start": True, "fy_end": 2026}, {"fiscal_year": "2026"},
])
def test_invalid_window_fails_before_any_database_is_opened(kwargs, monkeypatch):
    def forbidden(*args, **kw):
        pytest.fail("an invalid window reached the database")
    monkeypatch.setattr(crosswalk_module.psycopg, "connect", forbidden)
    with pytest.raises(ValueError):
        crosswalk_org("unused", organization="DARPA", treasury_agency="097",
                      award_glob="unused", **kwargs)
    with pytest.raises(ValueError):
        plan_crosswalk_org("unused", organization="DARPA", treasury_agency="097",
                           award_glob="unused", **kwargs)


def test_edition_selector_plans_and_writes_only_that_edition(pg_dsn, tmp_path):
    """fiscal_year narrows WHICH lines run — the PB2024 line is not touched —
    and never widens a line's award window: the PB2026 line still sees only
    its own FY2026 award."""
    seed_budget_editions(pg_dsn, [2024, 2026])
    glob = make_award_parquet_with_dates(tmp_path, TWO_FY_ROWS)
    kw = dict(organization="DARPA", treasury_agency="097", award_glob=glob)
    plan = plan_crosswalk_org(pg_dsn, **kw, fiscal_year=2024)
    assert [(p.fiscal_year, p.candidates) for p in plan] == [(2024, 1)]
    assert _links(pg_dsn) == []
    n = crosswalk_org(pg_dsn, **kw, fiscal_year=2026)
    assert n == CrosswalkResult(written=1, skipped=0)
    assert [(fy, piid) for fy, piid, _r in _links(pg_dsn)] == [
        (2026, "HR001126C0001"),
    ]
    # An edition with no lines plans nothing and never reads the lake.
    assert plan_crosswalk_org(
        pg_dsn, organization="DARPA", treasury_agency="097",
        award_glob="not-a-path", fiscal_year=2025,
    ) == []


def test_cli_edition_selector_dry_run_never_migrates(
    monkeypatch, pg_dsn, tmp_path, capsys,
):
    """--fiscal-year is the shared jbooks flag; for crosswalk it selects the
    PB edition. A crosswalk run performs no schema writes of its own (migrate
    is the explicit `govbudget migrate` step), so a dry run touches nothing."""
    import govbudget.jbooks.db
    from govbudget import cli

    _wire_crosswalk_cli(monkeypatch, pg_dsn, tmp_path)
    monkeypatch.setattr(govbudget.jbooks.db, "migrate",
                        lambda *a, **kw: pytest.fail("crosswalk migrated the schema"))
    seed_budget_editions(pg_dsn, [2024, 2026])
    make_award_parquet_with_dates(tmp_path, TWO_FY_ROWS)
    cli.main(["jbooks", "crosswalk", "--dry-run", "--fiscal-year", "2026"])
    out = capsys.readouterr().out
    assert ("crosswalk DARPA: 1 line(s), projected 1 (line, award) pair(s);"
            " window=each line's own edition FY; edition FY2026 only") in out
    assert "edition FY2024" not in out
    assert "crosswalk dry-run: nothing written" in out
    assert _link_count(pg_dsn) == 0


def test_cli_reversed_window_exits_2(monkeypatch, pg_dsn, tmp_path, capsys):
    from govbudget import cli

    _wire_crosswalk_cli(monkeypatch, pg_dsn, tmp_path)
    with pytest.raises(SystemExit) as e:
        cli.main(["jbooks", "crosswalk", "--org", "DARPA",
                  "--fy-start", "2026", "--fy-end", "2025"])
    assert e.value.code == 2
    assert "is after fy_end" in capsys.readouterr().out


# --------------------------------------------------------------------------
# #85: determinism — one canonical title per (pe_bli, exhibit, fiscal_year,
# account) key; an award is graded from ALL of its transactions in the
# window, never from whichever one any_value() happened to scan first.
# --------------------------------------------------------------------------

DARPA_KW = dict(organization="DARPA", treasury_agency="097")


def seed_key_with_titles(pg_dsn, *, pe_bli, titles, fiscal_year=2024,
                         account="0400", org="DARPA", detail_title=None):
    """One jbook_documents row and one budget_lines row per (budget_activity,
    title) in `titles`, all on the SAME (pe_bli, R-1, fiscal_year, account)
    key. Distinct budget_activity keeps the budget_lines unique key happy and
    is the shape of two of the three live multi-title keys (HCMC00 on 3010F:
    BA 05 'HC/MC-130 Modifications' and BA 07 'HC/MC-130 Post Prod' in one
    P-1 workbook). fiscal_year=2024 so the awards below (federal FY2024
    action_dates) fall inside Task 5's default per-edition window.
    detail_title, when given, adds one non-superseded budget_line_details row
    whose project_title tokens join the line's title tokens."""
    with psycopg.connect(pg_dsn) as con:
        con.execute(
            "insert into jbook_documents (org, exhibit_family, fiscal_year, title, source_url)"
            " values (%s,'rdte',%s,%s,%s)",
            (org, fiscal_year, f"{pe_bli}_{fiscal_year}.pdf",
             f"https://example.test/{org}/{pe_bli}_{fiscal_year}.pdf"),
        )
        doc_id = con.execute("select max(id) from jbook_documents").fetchone()[0]
        for budget_activity, title in titles:
            con.execute(
                "insert into budget_lines (exhibit, fiscal_year, account, organization,"
                " budget_activity, pe_bli, title, amount_type, amount_thousands,"
                " source_document_id)"
                " values ('R-1',%s,%s,%s,%s,%s,%s,'fy_2024_actuals',1,%s)",
                (fiscal_year, account, org, budget_activity, pe_bli, title, doc_id),
            )
        if detail_title is not None:
            con.execute(
                "insert into extraction_runs (document_id, tier, tool_versions, status)"
                " values (%s,1,'{}','success')",
                (doc_id,),
            )
            run_id = con.execute("select max(id) from extraction_runs").fetchone()[0]
            con.execute(
                "insert into budget_line_details"
                " (pe_bli, project_number, project_title, scenario, amount_millions,"
                "  xml_path, extraction_run_id, document_id, superseded)"
                " values (%s,'P-01',%s,'PriorYear',1,'ProgramElement[0]',%s,%s,false)",
                (pe_bli, detail_title, run_id, doc_id),
            )


# AWARD_COLS order: contract_transaction_unique_key, award_id_piid,
# federal_action_obligation, federal_accounts_funding_this_award,
# transaction_description, prime_award_base_transaction_description,
# recipient_name, recipient_uei, awarding_sub_agency_name, action_date
MULTI_TX_AWARDS = [
    # HR001124C0777: three transactions in the window. Only the LAST one in
    # file order carries the DARPA sub-agency, the only description that
    # overlaps the line, and the novated recipient. any_value() on one small
    # parquet returns the FIRST row scanned, so the pre-#85 code graded this
    # award account/low with the stale recipient and a binary-float sum.
    ("T1", "HR001124C0777", "0.10", "097-0400", "ADMINISTRATIVE MODIFICATION",
     "BASE PERIOD OPTION EXERCISE", "ACME RESEARCH LLC", "UEIACME1",
     "Defense Contract Management Agency", "2024-01-10"),
    ("T2", "HR001124C0777", "0.20", "097-0400", "FUNDING ACTION",
     "BASE PERIOD OPTION EXERCISE", "ACME RESEARCH LLC", "UEIACME1",
     "Defense Contract Management Agency", "2024-02-10"),
    ("T3", "HR001124C0777", "0.30", "097-0400", "MATHEMATICS SCIENCES ALGORITHMS",
     "BASE PERIOD OPTION EXERCISE", "ACME RESEARCH LLC NOVATED", "UEIACME2",
     "Defense Advanced Research Projects Agency", "2024-03-10"),
    # HR001124C0778: no token overlap anywhere; the DARPA sub-agency is on the
    # SECOND of two transactions only -> medium under the any-transaction
    # rule, low under any_value()-picks-the-first.
    ("S1", "HR001124C0778", "1", "097-0400", "UNRELATED WORK", "UNRELATED BASE",
     "BETA LABS", "UEIBETA", "Department of the Navy", "2024-01-05"),
    ("S2", "HR001124C0778", "1", "097-0400", "UNRELATED WORK", "UNRELATED BASE",
     "BETA LABS", "UEIBETA", "Defense Advanced Research Projects Agency", "2024-04-05"),
]


def _mechanical_rows(pg_dsn) -> list[tuple]:
    """Every column a reader or an auditor can see, in key order."""
    with psycopg.connect(pg_dsn) as con:
        return con.execute(
            "select pe_bli, exhibit, fiscal_year, award_piid, method, confidence,"
            " score, rationale, recipient_name, recipient_uei, matched_obligation"
            " from budget_line_awards"
            " order by pe_bli, exhibit, fiscal_year, award_piid"
        ).fetchall()


def _delete_links(pg_dsn) -> None:
    # Plain delete mid-test: no table references budget_line_awards by foreign
    # key (migrations 001-014 checked), and the autouse _clean_tables fixture
    # owns TRUNCATE ... RESTART IDENTITY at teardown; here the rows just need
    # to be gone before the second run.
    with psycopg.connect(pg_dsn, autocommit=True) as con:
        con.execute("delete from budget_line_awards")


def test_any_transaction_description_counts_for_token_overlap(pg_dsn, tmp_path):
    """#85 rule: an award's tokens are the union over ALL of its transactions
    in the window. HR001124C0777's only overlapping description
    ('MATHEMATICS SCIENCES ALGORITHMS') is on its third transaction; line
    tokens are {sciences} from the title plus {mathematics, computer,
    sciences} from the detail title -> overlap 2 -> account+tokens/high.
    Recipient is the LATEST transaction's; the obligation is an exact decimal
    (0.10 + 0.20 + 0.30 = 0.60, not 0.6000000000000001)."""
    seed_key_with_titles(pg_dsn, pe_bli="0601101E",
                         titles=[(None, "DEFENSE RESEARCH SCIENCES")],
                         detail_title="MATHEMATICS AND COMPUTER SCIENCES")
    glob = make_award_parquet_with_dates(tmp_path, MULTI_TX_AWARDS)
    n = crosswalk_org(pg_dsn, **DARPA_KW, award_glob=glob)
    assert n == CrosswalkResult(written=2, skipped=0)  # one canonical line x two awards
    r = {row[3]: row for row in _mechanical_rows(pg_dsn)}["HR001124C0777"]
    assert (r[4], r[5], r[6]) == ("account+tokens", "high", 2)
    assert ("token overlap 2 (mathematics, sciences) across 4 distinct"
            " description(s)") in r[7]
    assert (r[8], r[9]) == ("ACME RESEARCH LLC NOVATED", "UEIACME2")
    assert r[10] == Decimal("0.60")


def test_any_transaction_sub_agency_counts_for_medium(pg_dsn, tmp_path):
    """#85 rule (controller ruling): an award carries a sub-agency if ANY of
    its transactions in the window was awarded under it — the pre-existing
    semantics made explicit and order-independent. HR001124C0778 is DARPA on
    1 of 2 transactions and overlaps nothing -> account+subagency/medium,
    and the rationale says which name matched and how often."""
    seed_key_with_titles(pg_dsn, pe_bli="0601101E",
                         titles=[(None, "DEFENSE RESEARCH SCIENCES")])
    glob = make_award_parquet_with_dates(tmp_path, MULTI_TX_AWARDS)
    crosswalk_org(pg_dsn, **DARPA_KW, award_glob=glob)
    r = {row[3]: row for row in _mechanical_rows(pg_dsn)}["HR001124C0778"]
    assert (r[4], r[5], r[6]) == ("account+subagency", "medium", 0)
    assert ("sub-agency Defense Advanced Research Projects Agency on 1 of 2"
            " transaction(s)") in r[7]


def test_one_canonical_title_per_key(pg_dsn, tmp_path):
    """#85: a key with two title variants (two budget activities in one
    workbook — the shape of HCMC00 and JSE000 live) is planned and graded
    ONCE, from the canonical row (lowest budget_activity, then title), not
    once per variant with the last writer winning. The award overlaps only
    the non-canonical 'ZULU POST PRODUCTION SUPPORT' title (post,
    production; 'support' is a stopword), so the canonical grade is the
    sub-agency medium and exactly one upsert is issued for the pair."""
    seed_key_with_titles(pg_dsn, pe_bli="0601999E", titles=[
        ("05", "ALPHA AIRFRAME MODIFICATIONS"),
        ("07", "ZULU POST PRODUCTION SUPPORT"),
    ])
    glob = make_award_parquet_with_dates(tmp_path, [
        ("Z1", "HR001124C0999", "1", "097-0400", "POST PRODUCTION SPARES",
         "POST PRODUCTION SPARES", "ZULU CO", "UEIZULU",
         "Defense Advanced Research Projects Agency", "2024-06-01"),
    ])
    assert len(plan_crosswalk_org(pg_dsn, **DARPA_KW, award_glob=glob)) == 1
    n = crosswalk_org(pg_dsn, **DARPA_KW, award_glob=glob)
    assert n == CrosswalkResult(written=1, skipped=0)
    rows = _mechanical_rows(pg_dsn)
    assert len(rows) == 1
    assert (rows[0][4], rows[0][5], rows[0][6]) == ("account+subagency", "medium", 0)


def test_tags_independent_of_transaction_order_in_lake(pg_dsn, tmp_path):
    """#85 proof-it-can-fail for the any_value() root cause: the same
    transactions written to the lake in reverse order must produce identical
    rows. any_value() returns the first value scanned, so the pre-#85 code
    graded HR001124C0777 low from the forward file and high from the reversed
    one (and HR001124C0778 low vs medium)."""
    seed_key_with_titles(pg_dsn, pe_bli="0601101E",
                         titles=[(None, "DEFENSE RESEARCH SCIENCES")],
                         detail_title="MATHEMATICS AND COMPUTER SCIENCES")
    fwd = make_award_parquet_with_dates(tmp_path / "fwd", MULTI_TX_AWARDS)
    rev = make_award_parquet_with_dates(tmp_path / "rev", list(reversed(MULTI_TX_AWARDS)))
    crosswalk_org(pg_dsn, **DARPA_KW, award_glob=fwd)
    from_fwd = _mechanical_rows(pg_dsn)
    _delete_links(pg_dsn)
    crosswalk_org(pg_dsn, **DARPA_KW, award_glob=rev)
    from_rev = _mechanical_rows(pg_dsn)
    assert from_fwd == from_rev
    assert {r[3]: (r[4], r[5]) for r in from_fwd} == {
        "HR001124C0777": ("account+tokens", "high"),
        "HR001124C0778": ("account+subagency", "medium"),
    }


def test_two_runs_over_same_fixtures_produce_identical_rows(pg_dsn, tmp_path):
    """Controller-required regression guard: a second run over the same
    fixtures (the upsert path) leaves every mechanical row identical —
    method, confidence, score, rationale, recipient, obligation — and adds
    none. On a one-file fixture this passes before the fix too (DuckDB scans
    a single row group in one order); the order-independence test above is
    the one that proves the root cause. The live proof is the md5 check in
    docs/superpowers/LAUNCH.md."""
    seed_key_with_titles(pg_dsn, pe_bli="0601101E",
                         titles=[(None, "DEFENSE RESEARCH SCIENCES")],
                         detail_title="MATHEMATICS AND COMPUTER SCIENCES")
    glob = make_award_parquet_with_dates(tmp_path, MULTI_TX_AWARDS)
    n1 = crosswalk_org(pg_dsn, **DARPA_KW, award_glob=glob)
    first = _mechanical_rows(pg_dsn)
    n2 = crosswalk_org(pg_dsn, **DARPA_KW, award_glob=glob)
    second = _mechanical_rows(pg_dsn)
    assert n1 == n2 == CrosswalkResult(written=2, skipped=0)
    assert first == second


# --------------------------------------------------------------------------
# #86 — deferred minors: what the run REPORTS, what an undated award means
# under a window, and where the two interpolated values come from.
# --------------------------------------------------------------------------


def test_upsert_count_excludes_rows_the_method_guard_left_alone(pg_dsn, tmp_path):
    """#86: the old count added 1 per candidate row, including the rows the
    upsert's `do update ... where method in (mechanical)` refused to touch, so
    `crosswalk DARPA: N links` overstated what the run wrote. Postgres reports
    the rows inserted OR updated; a conflict the guard rejected reports 0."""
    seed_budget_with_detail(pg_dsn)
    lake = make_award_parquet(tmp_path)
    with psycopg.connect(pg_dsn) as con:
        con.execute(
            "insert into budget_line_awards"
            " (pe_bli, exhibit, fiscal_year, organization, award_piid,"
            "  recipient_name, recipient_uei, matched_obligation, method,"
            "  confidence, score, rationale)"
            " values ('0601101E','R-1',2026,'DARPA','HR001124C0001',"
            "  'ACME RESEARCH LLC','UEIDARPA1',5000000,'announcement+lexicon',"
            "  'high',null,'defense.gov contract announcement 123456')"
        )
    result = crosswalk_org(
        pg_dsn, organization="DARPA", treasury_agency="097",
        award_glob=str(lake / "contracts" / "*" / "*.parquet"),
    )
    # K3 is written (new mechanical row); K1 is skipped (evidence-graded row kept)
    assert result == CrosswalkResult(written=1, skipped=1)
    with psycopg.connect(pg_dsn) as con:
        method = con.execute(
            "select method from budget_line_awards"
            " where pe_bli='0601101E' and award_piid='HR001124C0001'"
        ).fetchone()[0]
    assert method == "announcement+lexicon"


def test_undated_and_malformed_action_dates_are_excluded_under_an_fy_window(
    pg_dsn, tmp_path,
):
    """#86: an award whose action_date is NULL or not a date has no fiscal
    year, so an FY window must exclude it EXPLICITLY. The old substr
    arithmetic excluded NULL/'' only by three-valued-logic accident and read
    '2024' as FY2024 and '2024-13-01' as FY2025 (month 13 >= 10 rolls over),
    so the 2024..2025 window below admitted THREE awards; it must admit one.
    The no-window path (--all-years) is deliberately not pinned here: with no
    bounds there is no fiscal year to have, and #78's own tests own that
    path."""
    seed_budget(pg_dsn)
    sub = "Defense Advanced Research Projects Agency"
    rows = [
        ("K20", "HR001124C0020", "1", "097-0400", "X", "Y", "Z", "U", sub, "2024-03-01"),
        ("K21", "HR001124C0021", "1", "097-0400", "X", "Y", "Z", "U", sub, None),
        ("K22", "HR001124C0022", "1", "097-0400", "X", "Y", "Z", "U", sub, ""),
        ("K23", "HR001124C0023", "1", "097-0400", "X", "Y", "Z", "U", sub, "not-a-date"),
        ("K24", "HR001124C0024", "1", "097-0400", "X", "Y", "Z", "U", sub, "2024"),
        ("K25", "HR001124C0025", "1", "097-0400", "X", "Y", "Z", "U", sub, "2024-13-01"),
    ]
    glob = make_award_parquet_nullable_dates(tmp_path, rows)
    result = crosswalk_org(
        pg_dsn, organization="DARPA", treasury_agency="097", award_glob=glob,
        fy_start=2024, fy_end=2025,
    )
    assert result == CrosswalkResult(written=1, skipped=0)
    with psycopg.connect(pg_dsn) as con:
        piids = {r[0] for r in con.execute(
            "select award_piid from budget_line_awards where pe_bli='0601101E'"
        )}
    assert piids == {"HR001124C0020"}


def test_the_planner_excludes_undated_awards_the_same_way(pg_dsn, tmp_path):
    """Companion to the test above: plan_crosswalk_org and crosswalk_org share
    _candidate_where, so the plan must count the same one award — a planner
    that still read '2024' as a fiscal year would project 3 pairs and the
    abort threshold would be measuring a population the run never writes."""
    seed_budget(pg_dsn)
    sub = "Defense Advanced Research Projects Agency"
    glob = make_award_parquet_nullable_dates(tmp_path, [
        ("K20", "HR001124C0020", "1", "097-0400", "X", "Y", "Z", "U", sub, "2024-03-01"),
        ("K24", "HR001124C0024", "1", "097-0400", "X", "Y", "Z", "U", sub, "2024"),
        ("K25", "HR001124C0025", "1", "097-0400", "X", "Y", "Z", "U", sub, "2024-13-01"),
    ])
    plan = plan_crosswalk_org(
        pg_dsn, organization="DARPA", treasury_agency="097", award_glob=glob,
        fy_start=2024, fy_end=2025,
    )
    assert [p.candidates for p in plan] == [1]


def test_fed_account_is_bound_as_a_query_parameter(pg_dsn, tmp_path):
    """#86: fed_account reached the DuckDB SQL by f-string at two sites (the
    obligation `case when ... = '{fed_account}'` in _fetch_candidates and the
    `like '%{fed_account}%'` filter in _candidate_where). A quote in the
    account code proves the binding: interpolated, DuckDB raises
    ParserException; bound, it is a value that matches nothing. (Live account
    codes are digits plus one optional service letter — this is a mechanism
    pin, not a live defect.)"""
    seed_budget_with_quoted_account(pg_dsn)
    lake = make_award_parquet(tmp_path)
    kw = dict(organization="DARPA", treasury_agency="097",
              award_glob=str(lake / "contracts" / "*" / "*.parquet"))
    # The planner runs the same predicate and must survive the quote too.
    assert [p.candidates for p in plan_crosswalk_org(pg_dsn, **kw)] == [0]
    assert crosswalk_org(pg_dsn, **kw) == CrosswalkResult(written=0, skipped=0)


def test_aliases_csv_is_anchored_to_config_root():
    """#86: the seed path was built from Path(__file__).resolve().parents[3];
    every other seed path in cli.py hangs off config.ROOT.

    Both spellings resolve to the same directory today, so asserting equality
    alone could never fail — the pin is on the SOURCE: one anchor per module,
    and it is config.ROOT.
    """
    src = inspect.getsource(crosswalk_module)
    assert "parents[" not in src, (
        "crosswalk.py derives a path from __file__ depth; use config.ROOT")
    assert crosswalk_module._ALIASES_CSV == (
        config.ROOT / "data-seeds" / "org_subagency_aliases.csv")
    assert crosswalk_module._ALIASES_CSV.is_file()
