from decimal import Decimal
from pathlib import Path

import duckdb
import psycopg
import pytest

from govbudget.jbooks import crosswalk as crosswalk_module
from govbudget.jbooks.crosswalk import crosswalk_org, plan_crosswalk_org

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


def test_crosswalk_matches_by_account_and_scores_confidence(pg_dsn, tmp_path):
    seed_budget_with_detail(pg_dsn)
    lake = make_award_parquet(tmp_path)
    n = crosswalk_org(
        pg_dsn, organization="DARPA", treasury_agency="097",
        award_glob=str(lake / "contracts" / "*" / "*.parquet"),
    )
    assert n == 2  # K1 and K3 (097-0400 in accounts); K2 excluded
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
    crosswalk_org(pg_dsn, **kwargs)
    crosswalk_org(pg_dsn, **kwargs)
    with psycopg.connect(pg_dsn) as con:
        n = con.execute("select count(*) from budget_line_awards").fetchone()[0]
    assert n == 2


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
    assert n == 1
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
    assert n_2024 == 1 and n_2023 == 0


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
    assert n_2024 == 1 and n_2025 == 0


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
    assert n == 1
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
    assert n == 2
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
    assert n == 2
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
    assert n == 1
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
    assert crosswalk_org(pg_dsn, **kw) == sum(p.candidates for p in plan)


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
    assert "crosswalk DARPA: 1 links; window=each line's own edition FY" in out
    assert "crosswalk total: 1" in out
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
    assert "crosswalk DARPA: 2 links; window=all loaded award years" in out
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
