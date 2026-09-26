"""The FPDS deriver's recipient is one deterministic pick (R-DEC-RECIPIENT,
fix-round-5 ruling 2026-09-26).

THE DEFECT. scripts/derive_ap_links.ap_awards took each (AP code, PIID)
group's recipient with any_value(recipient_name) and any_value(recipient_uei)
— two independent picks DuckDB resolves by scan order, so a name could come
from one UEI's rows and the UEI from another's, and the pick could change run
to run. Measured read-only 2026-09-26 over the 25,081 (AP code, PIID) groups
the deriver reads: 667 carry more than one recipient UEI, and 27 of them tie
for the largest total.

THE RULE (the ruling's (1) then (3); an FPDS link cites no announcement, so
the loader's step (2) has nothing to read here): the UEI whose rows carry the
largest exact total obligation in the group (move rule applied); ties go to
the lowest UEI. The name comes from that UEI's own rows (the name carrying the
most dollars, ties to the lower name) and is never borrowed. The basis —
'obligation' or 'uei_tiebreak' — is stored with the link
(budget_line_awards.recipient_basis, migration 019).

Every test here failed on the pre-fix deriver except
test_bases_is_optional_and_the_row_shape_is_unchanged, which pins what did not
change (ap_awards' row shape for its other callers).
"""
from pathlib import Path

import duckdb
import psycopg
import pytest

COLS = ("contract_transaction_unique_key, award_id_piid, recipient_uei,"
        " recipient_name, federal_action_obligation,"
        " federal_accounts_funding_this_award, dod_acquisition_program_code,"
        " action_date, last_modified_date")
MODIFIED = "2026-08-02 00:00:00+00"


def row(key, piid, uei, name, obligation, *, ap="123", action_date="2025-10-02",
        modified=MODIFIED, accounts="097-0400"):
    return (key, piid, uei, name, obligation, accounts, ap, action_date, modified)


def write(root: Path, fy: int, rows, part="part") -> str:
    d = root / "contracts" / f"fy={fy}"
    d.mkdir(parents=True, exist_ok=True)
    values = ", ".join(
        "(" + ", ".join("'" + str(v).replace("'", "''") + "'" for v in r) + ")"
        for r in rows)
    duckdb.sql(f"copy (select * from (values {values}) t({COLS}))"
               f" to '{d}/{part}.parquet' (format parquet)")
    return str(root / "contracts" / "fy=*" / "*.parquet")


def awards(codes, glob):
    from derive_ap_links import ap_awards

    bases: dict = {}
    rows, _moves = ap_awards(codes, contracts_glob=glob, bases=bases)
    return {(r[0], r[1]): r[2:] for r in rows}, bases


def test_the_largest_total_obligation_wins_not_the_largest_row(tmp_path):
    glob = write(tmp_path, 2026, [
        row("K1", "TWO", "UEIBBBBBBBB2", "BRAVO LLC", "250"),
        row("K2", "TWO", "UEIAAAAAAAA1", "ALPHA CORP", "100"),
        row("K3", "TWO", "UEIAAAAAAAA1", "ALPHA CORPORATION", "200"),
    ])
    got, bases = awards(["123"], glob)
    assert got[("123", "TWO")] == (
        "ALPHA CORPORATION", "UEIAAAAAAAA1", "097-0400", 550.0)
    assert bases == {("123", "TWO"): "obligation"}


def test_an_all_zero_tie_goes_to_the_lowest_uei_with_its_own_name(tmp_path):
    # the higher UEI is scanned first and carries the name that sorts first:
    # neither scan order nor min(name) gives the answer
    glob = write(tmp_path, 2026, [
        row("Z1", "IDV", "UEIZZZZZZZZ9", "AARDVARK INC", "0"),
        row("Z2", "IDV", "UEIAAAAAAAA1", "ZEBRA LLC", "0"),
        row("Z3", "IDV", "UEIAAAAAAAA1", "ZEBRA LLC", "0"),
    ])
    got, bases = awards(["123"], glob)
    assert got[("123", "IDV")][:2] == ("ZEBRA LLC", "UEIAAAAAAAA1")
    assert bases[("123", "IDV")] == "uei_tiebreak"


def test_totals_are_compared_exactly(tmp_path):
    glob = write(tmp_path, 2026, [
        row("E1", "CENTS", "UEIBBBBBBBB2", "BRAVO LLC", "0.10"),
        row("E2", "CENTS", "UEIBBBBBBBB2", "BRAVO LLC", "0.20"),
        row("E3", "CENTS", "UEIAAAAAAAA1", "ALPHA CORP", "0.30"),
    ])
    got, bases = awards(["123"], glob)
    assert got[("123", "CENTS")][:2] == ("ALPHA CORP", "UEIAAAAAAAA1")
    assert bases[("123", "CENTS")] == "uei_tiebreak"


def test_each_ap_code_picks_from_its_own_rows(tmp_path):
    # one PIID tagged with two programs: each group's obligation AND
    # recipient come from that group's rows
    glob = write(tmp_path, 2026, [
        row("A1", "SHARED", "UEIAAAAAAAA1", "ALPHA CORP", "900", ap="111"),
        row("A2", "SHARED", "UEIBBBBBBBB2", "BRAVO LLC", "10", ap="111"),
        row("A3", "SHARED", "UEIBBBBBBBB2", "BRAVO LLC", "80", ap="222"),
        row("A4", "SHARED", "UEIAAAAAAAA1", "ALPHA CORP", "5", ap="222"),
    ])
    got, bases = awards(["111", "222"], glob)
    assert got[("111", "SHARED")][:2] == ("ALPHA CORP", "UEIAAAAAAAA1")
    assert got[("222", "SHARED")][:2] == ("BRAVO LLC", "UEIBBBBBBBB2")
    assert bases == {("111", "SHARED"): "obligation", ("222", "SHARED"): "obligation"}


def test_a_retired_copy_does_not_count_toward_a_recipient(tmp_path):
    write(tmp_path, 2025, [
        row("MOVED001", "MOVE", "UEIAAAAAAAA1", "ALPHA CORP", "1000",
            action_date="2025-03-01", modified="2025-04-01 00:00:00+00"),
    ])
    glob = write(tmp_path, 2026, [
        row("MOVED001", "MOVE", "UEIAAAAAAAA1", "ALPHA CORP", "10"),
        row("STAYS001", "MOVE", "UEIBBBBBBBB2", "BRAVO LLC", "50"),
    ])
    got, bases = awards(["123"], glob)
    assert got[("123", "MOVE")] == ("BRAVO LLC", "UEIBBBBBBBB2", "097-0400", 60.0)
    assert bases[("123", "MOVE")] == "obligation"


def test_rows_with_no_uei_never_outrank_a_uei_and_names_are_never_borrowed(tmp_path):
    glob = write(tmp_path, 2026, [
        row("U1", "MIXED", "", "NO UEI CO", "900"),
        row("U2", "MIXED", "UEICCCCCCCC3", "CHARLIE LLC", "1"),
        row("W1", "NONAME", "UEIAAAAAAAA1", "", "100"),
        row("W2", "NONAME", "UEIBBBBBBBB2", "BRAVO LLC", "50"),
    ])
    got, _ = awards(["123"], glob)
    assert got[("123", "MIXED")][:2] == ("CHARLIE LLC", "UEICCCCCCCC3")
    # the picked UEI's rows name no one: None, never BRAVO's name
    assert got[("123", "NONAME")][:2] == (None, "UEIAAAAAAAA1")


def test_the_pick_does_not_depend_on_row_or_file_order(tmp_path):
    rows = [
        row("R1", "ORDER", "UEIZZZZZZZZ9", "ZULU INC", "0"),
        row("R2", "ORDER", "UEIAAAAAAAA1", "ALPHA CORP", "0"),
        row("R3", "ORDER", "UEIMMMMMMMM5", "MIKE LLC", "0"),
    ]
    forward = write(tmp_path / "a", 2026, rows)
    write(tmp_path / "b", 2026, rows[2:], part="part-1")
    backward = write(tmp_path / "b", 2026, list(reversed(rows[:2])), part="part-2")
    assert awards(["123"], forward) == awards(["123"], backward)


def test_bases_is_optional_and_the_row_shape_is_unchanged(tmp_path):
    from derive_ap_links import ap_awards

    glob = write(tmp_path, 2026, [row("S1", "SOLO", "UEISSSSSSSS1", "SOLO INC", "3")])
    rows, _ = ap_awards(["123"], contracts_glob=glob)
    assert rows == [("123", "SOLO", "SOLO INC", "UEISSSSSSSS1", "097-0400", 3.0)]


# ── the rows carry the basis; the upsert stores it ─────────────────────────

LINE_META = {("0601101E", None): {"fed_accounts": {"097-0400"}, "org": "DARPA",
                                  "exhibit": "R-1"}}


def _rows(basis):
    from derive_ap_links import link_rows_for_award

    return link_rows_for_award(
        ap_code="123", piid="IDV", recipient_name="ZEBRA LLC",
        recipient_uei="UEIAAAAAAAA1", award_accounts={"097-0400"},
        obligation=0.0,
        candidates=[{"pe_bli": "0601101E", "match_kind": "title-exact"}],
        line_meta=LINE_META, account_split={}, recipient_basis=basis)


def test_a_link_row_carries_its_recipient_basis_last():
    from derive_ap_links import BLA_ROW_WIDTH, incoming_member_claims

    (r,) = _rows("uei_tiebreak")
    assert len(r) == BLA_ROW_WIDTH == 14
    assert (r[5], r[6], r[12], r[13]) == (
        "ZEBRA LLC", "UEIAAAAAAAA1", None, "uei_tiebreak")
    assert incoming_member_claims([r]) == [(("0601101E", "R-1", 2026, "IDV"), None)]


ORG = "derive-recipient-test"


@pytest.fixture()
def con(pg_dsn):
    with psycopg.connect(pg_dsn) as c:
        yield c
        c.rollback()


def _row(piid, name, uei, basis, method="fpds-ap"):
    return ("RC0601101E", "R-1", 2026, ORG, piid, name, uei, 0.0, method,
            "medium", 1, "FPDS acquisition program 123", None, basis)


def _stored(con, piid):
    return con.execute(
        "select method, recipient_name, recipient_uei, recipient_basis"
        " from budget_line_awards where organization = %s and award_piid = %s",
        (ORG, piid)).fetchone()


def test_the_deriver_stores_the_basis(con):
    from derive_ap_links import UPSERT_SQL

    con.cursor().execute(UPSERT_SQL, _row("NEW", "ZEBRA LLC", "UEIAAAAAAAA1",
                                          "uei_tiebreak"))
    assert _stored(con, "NEW") == ("fpds-ap", "ZEBRA LLC", "UEIAAAAAAAA1",
                                   "uei_tiebreak")


def test_an_fpds_row_that_takes_a_mechanical_key_takes_its_own_recipient(con):
    """The upsert updated method/confidence on an account* key and left the
    crosswalk's recipient behind, so the fpds-ap link published a recipient
    its own rule did not pick, with no basis."""
    from derive_ap_links import UPSERT_SQL

    con.execute(
        "insert into budget_line_awards (pe_bli, exhibit, fiscal_year,"
        " organization, award_piid, recipient_name, recipient_uei, method,"
        " confidence, rationale) values ('RC0601101E', 'R-1', 2026, %s, 'ACCT',"
        " 'AARDVARK INC', 'UEIZZZZZZZZ9', 'account+subagency', 'medium',"
        " 'account route')", (ORG,))
    con.cursor().execute(UPSERT_SQL, _row("ACCT", "ZEBRA LLC", "UEIAAAAAAAA1",
                                          "uei_tiebreak"))
    assert _stored(con, "ACCT") == ("fpds-ap", "ZEBRA LLC", "UEIAAAAAAAA1",
                                    "uei_tiebreak")


def test_an_evidence_graded_link_keeps_its_recipient_and_basis(con):
    from derive_ap_links import UPSERT_SQL

    con.execute(
        "insert into budget_line_awards (pe_bli, exhibit, fiscal_year,"
        " organization, award_piid, recipient_name, recipient_uei, method,"
        " confidence, rationale, recipient_basis) values ('RC0601101E', 'R-1',"
        " 2026, %s, 'ANN', 'VIASAT INC', 'L9Z1ASN3B8E7', 'announcement+lexicon',"
        " 'high', 'defense.gov article 1275111', 'announcement_named')", (ORG,))
    con.cursor().execute(UPSERT_SQL, _row("ANN", "L3 TECHNOLOGIES, INC.",
                                          "FRJQGQHDX4J3", "uei_tiebreak"))
    assert _stored(con, "ANN") == ("announcement+lexicon", "VIASAT INC",
                                   "L9Z1ASN3B8E7", "announcement_named")


def test_an_unknown_basis_is_refused(con):
    from derive_ap_links import UPSERT_SQL

    with pytest.raises(psycopg.errors.CheckViolation):
        with con.transaction():
            con.cursor().execute(UPSERT_SQL, _row("BAD", "X INC", "UEIX", "alphabet"))


def test_the_pick_rule_itself():
    from decimal import Decimal

    from derive_ap_links import RecipientCandidate as C, pick_recipient

    a = C("UEIAAAAAAAA1", Decimal("0.00"), "ALPHA", ("ALPHA",))
    b = C("UEIBBBBBBBB2", Decimal("0.00"), "BRAVO", ("BRAVO",))
    c = C("UEICCCCCCCC3", Decimal("5.00"), "CHARLIE", ("CHARLIE",))
    nobody = C(None, Decimal("9.00"), "NOBODY", ("NOBODY",))
    assert pick_recipient([b, a]) == (a, "uei_tiebreak")
    assert pick_recipient([b, a], named={"UEIBBBBBBBB2"}) == (b, "announcement_named")
    assert pick_recipient([b, a], named={"UEIAAAAAAAA1", "UEIBBBBBBBB2"}) == (
        a, "uei_tiebreak")
    assert pick_recipient([a, b, c], named={"UEIBBBBBBBB2"}) == (c, "obligation")
    assert pick_recipient([nobody, a]) == (a, "obligation")
    assert pick_recipient([nobody]) == (nobody, "obligation")
    unknown = C("UEIDDDDDDDD4", None, "DELTA", ("DELTA",))
    assert pick_recipient([unknown, a]) == (a, "obligation")
    with pytest.raises(ValueError):
        pick_recipient([])


# ── R-DEC-DERIVE (fix round 7): 'pre_rule' is stored, never written ─────────
#
# Migration 019's CHECK now admits 'pre_rule' (its backfill's value for a row
# whose recipient predates R-DEC-RECIPIENT). Before, the CHECK refused it from
# every writer; the loaders keep refusing it themselves, and a missing basis
# with it, so a fresh pick can never be stored as pre-rule or as no basis.


@pytest.mark.parametrize("basis", ["pre_rule", None, "alphabet"])
def test_a_row_without_a_rule_basis_is_refused_before_the_write(basis):
    from derive_ap_links import incoming_member_claims

    (r,) = _rows(basis)
    with pytest.raises(ValueError, match=r"recipient_basis"):
        incoming_member_claims([r])


@pytest.mark.parametrize("basis", ["obligation", "announcement_named", "uei_tiebreak"])
def test_every_rule_basis_passes_the_write_check(basis):
    from derive_ap_links import incoming_member_claims

    (r,) = _rows(basis)
    assert incoming_member_claims([r]) == [(("0601101E", "R-1", 2026, "IDV"), None)]


def test_the_deriver_checks_its_rows_before_it_upserts_them():
    """derive_ap_links.main runs incoming_member_claims on the exact rows it
    then upserts, inside the transaction that deleted its partition — a raise
    there rolls the delete back."""
    import inspect

    import derive_ap_links

    src = inspect.getsource(derive_ap_links.main)
    check = src.index("incoming_member_claims(out_rows)")
    delete = src.index("delete from budget_line_awards where method like 'fpds-ap%'")
    upsert = src.index("cur.executemany(UPSERT_SQL, out_rows)")
    assert delete < check < upsert


def test_the_database_now_admits_pre_rule_so_the_check_is_the_loaders(con):
    """Pins the reason the loader-side check exists: the upsert itself stores
    'pre_rule' since migration 019 allows it (for its backfill)."""
    from derive_ap_links import UPSERT_SQL

    con.cursor().execute(UPSERT_SQL, _row("PRE", "X INC", "UEIX", "pre_rule"))
    assert _stored(con, "PRE") == ("fpds-ap", "X INC", "UEIX", "pre_rule")
