"""ROADMAP #130 (owner-delegated ruling 2026-09-25): the downloadable
fct_program_concentration LABELS a shared code's row instead of withholding it.

The mart is keyed on the bare pe_bli, so on a budget-line code two or more
programs share (13 today — 10 split by appropriation account, 3 by
organization) its figures are computed over EVERY member's links. Pages and
feed cards keep the link rule (export_site._concentration_owner — unchanged);
the warehouse ships every row and now says which kind it is:

  scope                      'program' — the code names one program;
                             'code'    — two or more programs share the code
                                         and the figures pool every member key
  member_programs            dim_programs rows under the code
  member_keys_with_links     how many of those members' keys carry at least
                             one published link (high or medium — the same
                             count the page rule asks about)
  links_outside_member_keys  published links filed under a key no member
                             carries (an account NULL on an account-split code,
                             an organization no member has)

The key of a member follows govbudget.jbooks.collision_keys: ACCOUNT when
every member has an account and no two share one, otherwise ORGANIZATION.
"""
import duckdb

from test_dbt_build import _model_sql


def _scope(programs, links):
    """programs: (pe_bli, account, org); links: (pe_bli, award_piid, account,
    organization) — every link high-confidence with a $100 award."""
    con = duckdb.connect()
    con.execute("create table progs (pe_bli varchar, account varchar, org varchar)")
    con.executemany("insert into progs values (?, ?, ?)", programs)
    con.execute(
        "create table b2a (pe_bli varchar, award_piid varchar, confidence varchar,"
        " recipient_uei varchar, recipient_name varchar, account varchar,"
        " organization varchar)"
    )
    con.executemany(
        "insert into b2a values (?, ?, 'high', ?, 'R', ?, ?)",
        [(pe, piid, f"U-{piid}", acct, org) for pe, piid, acct, org in links],
    )
    con.execute("create table tx (award_id_piid varchar, obligation double)")
    con.executemany("insert into tx values (?, 100.0)", [(l[1],) for l in links])
    con.execute("create table xwalk (recipient_uei varchar, family_key varchar)")
    rows = con.execute(
        "select pe_bli, scope, member_programs, member_keys_with_links,"
        " links_outside_member_keys, award_count_all from ("
        + _model_sql(
            "fct_program_concentration",
            fct_award_transactions="tx",
            # not "links": the model has a CTE of that name
            fct_budget_to_awards="b2a",
            entity_xwalk="xwalk",
            dim_programs="progs",
        )
        + ") order by pe_bli"
    ).fetchall()
    con.close()
    return {r[0]: r[1:] for r in rows}


PROGRAMS = [
    ("SOLO", "0400", "DARPA"),
    # account-split: same organization, different appropriations
    ("3010", "1611N", "N"), ("3010", "1810N", "N"),
    ("3215", "1507N", "N"), ("3215", "1810N", "N"),
    ("0145", "1506N", "N"), ("0145", "1508N", "N"),
    # organization-split: one account, three organizations
    ("30", "0300D", "OSD"), ("30", "0300D", "DTRA"), ("30", "0300D", "DMACT"),
]


def test_a_code_that_names_one_program_is_labelled_program():
    s = _scope(PROGRAMS, [("SOLO", "S1", None, "DARPA"), ("SOLO", "S2", "0400", "DARPA")])
    assert s["SOLO"] == ("program", 1, 1, 0, 2)


def test_a_shared_code_is_labelled_code_whatever_its_links_are():
    s = _scope(PROGRAMS, [
        # both members carry links: the figure pools two programs' awards
        ("3010", "A", "1611N", "N"), ("3010", "B", "1810N", "N"),
        # one member carries every link: still the code's figure, and the
        # count says only one member contributes
        ("3215", "C", "1507N", "N"), ("3215", "D", "1507N", "N"),
        # a link filed under no member's key (account NULL on an account split)
        ("0145", "E", "1506N", "N"), ("0145", "F", None, "N"),
        # organization split: the link's organization is its member key
        ("30", "G", "0300D", "OSD"), ("30", "H", "0300D", "DTRA"),
        ("30", "I", "0300D", "WHS"),
    ])
    assert s["3010"] == ("code", 2, 2, 0, 2)
    assert s["3215"] == ("code", 2, 1, 0, 2)
    assert s["0145"] == ("code", 2, 1, 1, 2)
    assert s["30"] == ("code", 3, 2, 1, 3)


def test_the_figures_themselves_do_not_move():
    """Labelling is additive: every figure column is identical whether or not
    dim_programs knows the code, only the four label columns differ."""
    links = [("3010", "A", "1611N", "N"), ("3010", "B", "1810N", "N"),
             ("SOLO", "S1", "0400", "DARPA")]
    labelled = _figures(PROGRAMS, links)
    unlabelled = _figures([], links)
    assert labelled == unlabelled
    assert set(labelled) == {"3010", "SOLO"}


def _figures(programs, links):
    con = duckdb.connect()
    con.execute("create table progs (pe_bli varchar, account varchar, org varchar)")
    if programs:
        con.executemany("insert into progs values (?, ?, ?)", programs)
    con.execute(
        "create table b2a (pe_bli varchar, award_piid varchar, confidence varchar,"
        " recipient_uei varchar, recipient_name varchar, account varchar,"
        " organization varchar)"
    )
    con.executemany(
        "insert into b2a values (?, ?, 'high', ?, 'R', ?, ?)",
        [(pe, piid, f"U-{piid}", acct, org) for pe, piid, acct, org in links],
    )
    con.execute("create table tx (award_id_piid varchar, obligation double)")
    con.executemany("insert into tx values (?, ?)",
                    [(l[1], 100.0 * (i + 1)) for i, l in enumerate(links)])
    con.execute("create table xwalk (recipient_uei varchar, family_key varchar)")
    rel = con.sql(
        "select * exclude (scope, member_programs, member_keys_with_links,"
        " links_outside_member_keys) from ("
        + _model_sql("fct_program_concentration", fct_award_transactions="tx",
                     fct_budget_to_awards="b2a", entity_xwalk="xwalk",
                     dim_programs="progs")
        + ") order by pe_bli"
    )
    out = {r[0]: r for r in rel.fetchall()}
    con.close()
    return out
