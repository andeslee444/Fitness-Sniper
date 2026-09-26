"""A link's recipient is one deterministic pick (fix round 5, 2026-09-26).

Until this fix, scripts/load_announcement_links.lake_evidence took a link's
recipient with any_value(recipient_name) and any_value(recipient_uei), two
independent picks that DuckDB resolves by scan order. Measured read-only on
2026-09-26: 33 of the loader's 1,224 lake PIIDs carry more than one recipient
UEI, and six identical dry runs returned a different recipient for 18 of them.
The published HHI moved with the draw (356120: 5,627.5 in one chain run,
5,192.1 in the next). A figure that moves with row order is not a measurement
(R-DEC-176b's principle).

THE RULE: the recipient UEI whose transactions carry the largest total
obligation on the award (the same rows the loader sums, read through the
fiscal-year move rule, govbudget.award_moves), summed exactly; ties go to the
lower UEI. The name comes from that UEI's own rows: the name carrying the
largest total obligation among them, ties to the lower name. Rows with no UEI
form a group only when the award has no UEI at all.

Each fixture puts the row a scan-order pick would return FIRST, so the
pre-fix code fails every test here.
"""
from pathlib import Path

import duckdb
import psycopg
import pytest

COLS = ("contract_transaction_unique_key, award_id_piid, recipient_uei,"
        " recipient_name, federal_action_obligation,"
        " federal_accounts_funding_this_award, action_date, last_modified_date")
MODIFIED = "2026-08-02 00:00:00+00"


def row(key, piid, uei, name, obligation, *, action_date="2025-10-02",
        modified=MODIFIED, accounts="097-0400"):
    """One raw contracts row in COLS order."""
    return (key, piid, uei, name, obligation, accounts, action_date, modified)


def write(root: Path, fy: int, rows, part="part") -> str:
    """Write rows to <root>/contracts/fy=<fy>/<part>.parquet, in the order
    given; returns the loader's glob over <root>."""
    d = root / "contracts" / f"fy={fy}"
    d.mkdir(parents=True, exist_ok=True)
    values = ", ".join(
        "(" + ", ".join("'" + str(v).replace("'", "''") + "'" for v in r) + ")"
        for r in rows)
    duckdb.sql(f"copy (select * from (values {values}) t({COLS}))"
               f" to '{d}/{part}.parquet' (format parquet)")
    return str(root / "contracts" / "fy=*" / "*.parquet")


def evidence(piids, glob):
    from load_announcement_links import lake_evidence

    ev, _moves = lake_evidence(piids, contracts_glob=glob)
    return ev


# The fixture: two recipients on one award, and a tie.
TWO = [
    # BRAVO holds the largest single transaction, and is scanned first
    row("K1", "TWO", "UEIBBBBBBBB2", "BRAVO LLC", "250"),
    row("K2", "TWO", "UEIAAAAAAAA1", "ALPHA CORP", "100"),
    row("K3", "TWO", "UEIAAAAAAAA1", "ALPHA CORPORATION", "200"),
]
TIE = [
    # equal totals; the higher UEI is scanned first and carries the name
    # that sorts first, so neither scan order nor min(name) gives the answer
    row("T1", "TIE", "UEIZZZZZZZZ9", "AARDVARK INC", "100"),
    row("T2", "TIE", "UEIAAAAAAAA1", "ZEBRA LLC", "60"),
    row("T3", "TIE", "UEIAAAAAAAA1", "ZEBRA LLC", "40"),
]


def test_the_recipient_is_the_uei_with_the_largest_total_obligation(tmp_path):
    ev = evidence(["TWO"], write(tmp_path, 2026, TWO))
    # ALPHA's 100 + 200 = 300 beats BRAVO's single 250; the name is the one
    # ALPHA's own rows carry the most dollars under
    assert ev["TWO"] == ("ALPHA CORPORATION", "UEIAAAAAAAA1", 550.0, "097-0400")


def test_a_tie_goes_to_the_lower_uei_and_the_name_comes_from_its_rows(tmp_path):
    ev = evidence(["TIE"], write(tmp_path, 2026, TIE))
    assert ev["TIE"] == ("ZEBRA LLC", "UEIAAAAAAAA1", 200.0, "097-0400")


def test_a_name_tie_inside_the_picked_uei_goes_to_the_lower_name(tmp_path):
    glob = write(tmp_path, 2026, [
        row("N1", "NAMES", "UEIOOOOOOOO1", "OMEGA INCORPORATED", "50"),
        row("N2", "NAMES", "UEIOOOOOOOO1", "OMEGA INC", "50"),
    ])
    rname, ruei, _ob, _acc = evidence(["NAMES"], glob)["NAMES"]
    assert (rname, ruei) == ("OMEGA INC", "UEIOOOOOOOO1")


def test_the_totals_are_compared_exactly(tmp_path):
    # 0.10 + 0.20 is 0.30000000000000004 in floating point, which would beat
    # 0.30; summed exactly they tie, and the tie goes to the lower UEI
    glob = write(tmp_path, 2026, [
        row("E1", "CENTS", "UEIBBBBBBBB2", "BRAVO LLC", "0.10"),
        row("E2", "CENTS", "UEIBBBBBBBB2", "BRAVO LLC", "0.20"),
        row("E3", "CENTS", "UEIAAAAAAAA1", "ALPHA CORP", "0.30"),
    ])
    rname, ruei, _ob, _acc = evidence(["CENTS"], glob)["CENTS"]
    assert (rname, ruei) == ("ALPHA CORP", "UEIAAAAAAAA1")


def test_a_retired_copy_does_not_count_toward_a_recipient(tmp_path):
    # ALPHA's transaction MOVED001 was moved from fy=2025 (1,000) to fy=2026
    # (10). The warehouse keeps the fy=2026 copy only, so ALPHA holds 10 and
    # BRAVO's 50 wins; a raw read would give ALPHA 1,010.
    write(tmp_path, 2025, [
        row("MOVED001", "MOVE", "UEIAAAAAAAA1", "ALPHA CORP", "1000",
            action_date="2025-03-01", modified="2025-04-01 00:00:00+00"),
    ])
    glob = write(tmp_path, 2026, [
        row("MOVED001", "MOVE", "UEIAAAAAAAA1", "ALPHA CORP", "10"),
        row("STAYS001", "MOVE", "UEIBBBBBBBB2", "BRAVO LLC", "50"),
    ])
    assert evidence(["MOVE"], glob)["MOVE"] == (
        "BRAVO LLC", "UEIBBBBBBBB2", 60.0, "097-0400")


def test_rows_with_no_uei_never_outrank_a_uei(tmp_path):
    glob = write(tmp_path, 2026, [
        row("U1", "MIXED", "", "NO UEI CO", "900"),
        row("U2", "MIXED", "UEICCCCCCCC3", "CHARLIE LLC", "1"),
    ])
    rname, ruei, _ob, _acc = evidence(["MIXED"], glob)["MIXED"]
    assert (rname, ruei) == ("CHARLIE LLC", "UEICCCCCCCC3")


def test_an_award_with_no_uei_at_all_names_its_largest_recipient(tmp_path):
    # no UEI is stored as NULL, never as '' (which the concentration mart
    # would pool into one family across unrelated awards)
    glob = write(tmp_path, 2026, [
        row("V1", "NOUEI", "", "GAMMA LLC", "5"),
        row("V2", "NOUEI", "", "DELTA LLC", "7"),
    ])
    rname, ruei, ob, _acc = evidence(["NOUEI"], glob)["NOUEI"]
    assert (rname, ruei, ob) == ("DELTA LLC", None, 12.0)


def test_a_picked_uei_whose_rows_name_no_one_gets_no_name(tmp_path):
    # the name is never borrowed from another UEI's rows; the loader then
    # skips the link and counts it (main: no recipient name)
    glob = write(tmp_path, 2026, [
        row("W1", "NONAME", "UEIAAAAAAAA1", "", "100"),
        row("W2", "NONAME", "UEIBBBBBBBB2", "BRAVO LLC", "50"),
    ])
    rname, ruei, _ob, _acc = evidence(["NONAME"], glob)["NONAME"]
    assert (rname, ruei) == (None, "UEIAAAAAAAA1")


def test_a_row_with_no_name_never_outranks_a_name(tmp_path):
    glob = write(tmp_path, 2026, [
        row("X1", "BLANK", "UEIAAAAAAAA1", "", "500"),
        row("X2", "BLANK", "UEIAAAAAAAA1", "ALPHA CORP", "10"),
    ])
    rname, ruei, _ob, _acc = evidence(["BLANK"], glob)["BLANK"]
    assert (rname, ruei) == ("ALPHA CORP", "UEIAAAAAAAA1")


def test_the_pick_does_not_depend_on_row_or_file_order(tmp_path):
    forward = write(tmp_path / "a", 2026, TWO + TIE)
    write(tmp_path / "b", 2026, list(reversed(TIE)), part="part-1")
    backward = write(tmp_path / "b", 2026, list(reversed(TWO)), part="part-2")
    first = evidence(["TWO", "TIE"], forward)
    assert first == evidence(["TWO", "TIE"], backward)
    assert first == evidence(["TWO", "TIE"], forward)


def test_the_dry_run_counts_the_awards_with_more_than_one_uei(tmp_path):
    from load_announcement_links import lake_evidence

    glob = write(tmp_path, 2026, TWO + TIE + [
        row("S1", "SOLO", "UEISSSSSSSS1", "SOLO INC", "3"),
    ])
    stats: dict = {}
    lake_evidence(["TWO", "TIE", "SOLO"], contracts_glob=glob, stats=stats)
    assert stats == {"piids": 3, "multi_uei": 2, "multi_uei_piids": ["TIE", "TWO"]}


# ── R-DEC-RECIPIENT (fix-round-5 ruling, 2026-09-26) ───────────────────────
#
# "A link's recipient: (1) the UEI with the largest total obligation on the
# award (move rule applied); (2) among ties — including all-$0 — the recipient
# the link's cited announcement names (normalized-name match); (3) only then
# the lowest UEI. The loader records the basis ('obligation' /
# 'announcement_named' / 'uei_tiebreak')."
#
# The defect the ruling answers: fix round 5's tie-break was the alphabet
# alone. 10 of the 29 multi-UEI PIIDs with published links tie at $0.00 (IDVs
# whose money sits on their orders), so the pick there was the lower UEI, not
# evidence. N0003915D0008 (0604280N, a high announcement link) carries 2 L3
# rows (FRJQGQHDX4J3) and 21 ViaSat rows (L9Z1ASN3B8E7), both $0.00; the
# article its card cites (1275111, 2017-08-10, wave2_chunks/chunk_006.json)
# names "ViaSat Inc.", and every pre-fix production run carried ViaSat. 'FRJQ'
# sorts first, so the alphabet published L3 Technologies.
#
# Every test in this block failed on the fix-round-5 code except
# test_lake_evidence_keeps_the_announcement_free_pick, which pins what did not
# change (lake_evidence's own per-award pick).

ANN = "announcement+lexicon"
SUB = "subaward+lexicon"

N0003915D0008 = [
    # the L3 rows sort first by UEI and are scanned first; both UEIs net $0
    row("V01", "N0003915D0008", "FRJQGQHDX4J3", "L3 TECHNOLOGIES, INC.", "0"),
    row("V02", "N0003915D0008", "FRJQGQHDX4J3", "L3 TECHNOLOGIES, INC.", "0"),
    row("V03", "N0003915D0008", "L9Z1ASN3B8E7", "VIASAT INC", "0"),
    row("V04", "N0003915D0008", "L9Z1ASN3B8E7", "VIASAT INC", "1250.00"),
    row("V05", "N0003915D0008", "L9Z1ASN3B8E7", "VIASAT INC", "-1250.00"),
]
#: the packet its card cites (wave2_chunks/chunk_006.json, trimmed)
VIASAT_PACKET = {"piid": "N0003915D0008", "pe_bli": "0604280N",
                 "article_id": "1275111", "date": "2017-08-10",
                 "contractor": "ViaSat Inc.", "match_basis": "exact-name"}


def candidates(piids, glob):
    from load_announcement_links import lake_evidence

    cands: dict = {}
    lake_evidence(piids, contracts_glob=glob, candidates=cands)
    return cands


def pick(piid, rows, packet, method=ANN, *, tmp_path):
    from load_announcement_links import link_recipient

    return link_recipient(candidates([piid], write(tmp_path, 2026, rows))[piid],
                          packet, method)


def test_n0003915d0008_takes_the_recipient_its_cited_announcement_names(tmp_path):
    assert pick("N0003915D0008", N0003915D0008, VIASAT_PACKET,
                tmp_path=tmp_path) == ("VIASAT INC", "L9Z1ASN3B8E7",
                                       "announcement_named")


def test_the_real_packet_n0003915d0008_cites_names_viasat():
    """The evidence the tie-break reads is the packet the card cites — the
    packet choice (R-DEC-PACKET) over the real wave files, not any packet."""
    from load_announcement_links import ROOT, provenance_packets, recipient_name_key

    ann = ROOT / "data/research/announcements"
    prov = provenance_packets(ann, [ann / f"wave{n}_result.json" for n in (1, 2, 3, 4)])
    packet = prov[("N0003915D0008", "0604280N")]
    assert packet["article_id"] == "1275111"
    assert recipient_name_key(packet["contractor"]) == recipient_name_key("VIASAT INC")


def test_an_all_zero_tie_no_announcement_names_goes_to_the_lowest_uei(tmp_path):
    # N0003910D0032's shape: its article (605988) names "Data Link
    # Solutions", which is neither recipient on the award
    rows = [r[:1] + ("N0003910D0032",) + r[2:] for r in N0003915D0008]
    packet = dict(VIASAT_PACKET, piid="N0003910D0032", article_id="605988",
                  contractor="Data Link Solutions")
    assert pick("N0003910D0032", rows, packet, tmp_path=tmp_path) == (
        "L3 TECHNOLOGIES, INC.", "FRJQGQHDX4J3", "uei_tiebreak")


def test_a_name_match_beats_uei_order(tmp_path):
    # W909MY17D0002's shape (article 1161148 names "PD Systems Inc."), and a
    # tie that is not at $0: the rule is "among ties", not "at $0"
    rows = [
        row("P1", "W909MY17D0002", "GRRQGPH7QS29", "PD POWER SYSTEMS, LLC", "75.50"),
        row("P2", "W909MY17D0002", "MBF6MBLZLMC3", "PD SYSTEMS INC.", "75.50"),
    ]
    packet = {"article_id": "1161148", "contractor": "PD Systems Inc."}
    assert pick("W909MY17D0002", rows, packet, tmp_path=tmp_path) == (
        "PD SYSTEMS INC.", "MBF6MBLZLMC3", "announcement_named")


def test_the_largest_obligation_comes_before_the_announcement(tmp_path):
    # M6785415F4444's shape: the announcement names iGov, whose rows net
    # negative; MA Federal carries the largest total, so dollars decide
    rows = [
        row("G1", "M6785415F4444", "JKJ7JTLJJHR6", "IGOV TECHNOLOGIES, INC.", "-317545.70"),
        row("G2", "M6785415F4444", "L7MZK1KZZ162", "MA FEDERAL, INC.", "1359425.60"),
    ]
    packet = {"article_id": "1", "contractor": "iGov Technologies Inc."}
    assert pick("M6785415F4444", rows, packet, tmp_path=tmp_path) == (
        "MA FEDERAL, INC.", "L7MZK1KZZ162", "obligation")


def test_the_announcement_breaks_only_a_tie_for_the_largest_total(tmp_path):
    # the named recipient ties with another UEI, but BELOW the largest total
    rows = [
        row("L1", "LOWTIE", "UEIAAAAAAAA1", "ALPHA CORP", "10"),
        row("L2", "LOWTIE", "UEIBBBBBBBB2", "BRAVO LLC", "10"),
        row("L3", "LOWTIE", "UEICCCCCCCC3", "CHARLIE INC", "20"),
    ]
    packet = {"article_id": "1", "contractor": "Bravo LLC"}
    assert pick("LOWTIE", rows, packet, tmp_path=tmp_path) == (
        "CHARLIE INC", "UEICCCCCCCC3", "obligation")


def test_two_named_tied_ueis_go_to_the_lower_of_those_two(tmp_path):
    # the announcement narrows the tie to the UEIs it names; the lowest UEI
    # overall (unnamed) is not a candidate any more, and the UEI order decides
    # between the two it names
    rows = [
        row("A1", "THREE", "UEIAAAAAAAA1", "NORTHROP GRUMMAN SYSTEMS CORP", "0"),
        row("A2", "THREE", "UEICCCCCCCC3", "ALLIANT TECHSYSTEMS OPERATIONS LLC", "0"),
        row("A3", "THREE", "UEIBBBBBBBB2", "ALLIANT TECHSYSTEMS OPERATIONS LLC", "0"),
    ]
    packet = {"article_id": "1", "contractor": "Alliant Techsystems Operations LLC"}
    assert pick("THREE", rows, packet, tmp_path=tmp_path) == (
        "ALLIANT TECHSYSTEMS OPERATIONS LLC", "UEIBBBBBBBB2", "uei_tiebreak")


def test_a_related_company_is_not_named_by_the_announcement(tmp_path):
    # N0003917D0004's names with the UEIs swapped so the match decides: the
    # article names "Raytheon Technical Services Co.", a different recipient
    # from RAYTHEON COMPANY, so neither tied UEI is named and the lower wins
    rows = [
        row("R1", "RTSC", "UEIZZZZZZZZ9", "RAYTHEON COMPANY", "0"),
        row("R2", "RTSC", "UEIAAAAAAAA1", "VERTEX MODERNIZATION AND SUSTAINMENT LLC", "0"),
    ]
    packet = {"article_id": "1", "contractor": "Raytheon Technical Services Co."}
    assert pick("RTSC", rows, packet, tmp_path=tmp_path) == (
        "VERTEX MODERNIZATION AND SUSTAINMENT LLC", "UEIAAAAAAAA1", "uei_tiebreak")


def test_any_name_on_a_ueis_own_rows_can_be_the_named_one(tmp_path):
    # the UEI's rows carry two spellings; the announcement names the one that
    # carries fewer dollars, and the published name is still the UEI's
    # largest-dollar spelling (never the announcement's text)
    rows = [
        row("S1", "SPELL", "UEIAAAAAAAA1", "ALPHA CORP", "0"),
        row("S2", "SPELL", "UEIZZZZZZZZ9", "ZULU HOLDINGS INC", "5"),
        row("S3", "SPELL", "UEIZZZZZZZZ9", "ZULU SYSTEMS INC", "-5"),
    ]
    packet = {"article_id": "1", "contractor": "Zulu Systems Inc."}
    assert pick("SPELL", rows, packet, tmp_path=tmp_path) == (
        "ZULU HOLDINGS INC", "UEIZZZZZZZZ9", "announcement_named")


def test_a_subaward_link_cites_no_announcement_to_name_anyone(tmp_path):
    # a subaward+lexicon link cites an FSRS record, not an announcement: its
    # packet's contractor is the string 'None' (wave 3), and even a real
    # string there is not an announcement naming a recipient
    packet = {"article_id": "None", "contractor": "ViaSat Inc.",
              "match_basis": "subaward-description-exact"}
    assert pick("N0003915D0008", N0003915D0008, packet, SUB,
                tmp_path=tmp_path) == ("L3 TECHNOLOGIES, INC.", "FRJQGQHDX4J3",
                                       "uei_tiebreak")
    none_packet = dict(packet, contractor="None")
    assert pick("N0003915D0008", N0003915D0008, none_packet, SUB,
                tmp_path=tmp_path / "b")[2] == "uei_tiebreak"


def test_a_packet_naming_no_contractor_falls_to_the_uei(tmp_path):
    assert pick("N0003915D0008", N0003915D0008, {"article_id": "1"},
                tmp_path=tmp_path) == ("L3 TECHNOLOGIES, INC.", "FRJQGQHDX4J3",
                                       "uei_tiebreak")


def test_one_recipient_is_decided_by_obligation(tmp_path):
    rows = [row("O1", "ONE", "UEIOOOOOOOO1", "OSCAR LLC", "0"),
            row("O2", "NONE", "", "NOBODY LLC", "4")]
    glob = write(tmp_path, 2026, rows)
    from load_announcement_links import link_recipient

    cands = candidates(["ONE", "NONE"], glob)
    assert link_recipient(cands["ONE"], {"contractor": "Someone Else"}, ANN) == (
        "OSCAR LLC", "UEIOOOOOOOO1", "obligation")
    assert link_recipient(cands["NONE"], {}, ANN) == ("NOBODY LLC", None, "obligation")


def test_lake_evidence_keeps_the_announcement_free_pick(tmp_path):
    # lake_evidence's own (name, uei) stays rules (1) and (3) — it knows no
    # link; main() takes each link's recipient from link_recipient
    from load_announcement_links import lake_evidence

    glob = write(tmp_path, 2026, N0003915D0008)
    ev, _ = lake_evidence(["N0003915D0008"], contracts_glob=glob)
    assert ev["N0003915D0008"][:2] == ("L3 TECHNOLOGIES, INC.", "FRJQGQHDX4J3")


@pytest.mark.parametrize("announced, recorded", [
    ("ViaSat Inc.", "VIASAT INC"),
    ("The Raytheon Co.", "RAYTHEON COMPANY"),
    ("Trace Systems Inc.", "TRACE SYSTEMS, INC."),
    ("Northrop Grumman Systems Corp. (NGSC)", "NORTHROP GRUMMAN SYSTEMS CORPORATION"),
    ("Alliant Techsystems Operations LLC - ATK Tactical Propulsion and Control",
     "ALLIANT TECHSYSTEMS OPERATIONS LLC"),
    ("BAE Systems Land &amp; Armaments L.P.", "BAE SYSTEMS LAND AND ARMAMENTS LP"),
    ("L-3 Communications Corp.", "L3 COMMUNICATIONS CORPORATION"),
    ("Rolls-Royce Corp.", "ROLLS ROYCE CORPORATION"),
    ("Aret&egrave; Associates Inc.", "ARETE ASSOCIATES INC"),
    ("Lockheed Martin Corp. &ndash; Rotary and Mission Systems",
     "LOCKHEED MARTIN CORPORATION"),
    ("Arrow&rsquo;s Edge LLC", "ARROWS EDGE LLC"),
])
def test_the_name_match_normalizes_form_not_substance(announced, recorded):
    from load_announcement_links import recipient_name_key

    assert recipient_name_key(announced) == recipient_name_key(recorded)


@pytest.mark.parametrize("announced, recorded", [
    ("PD Systems Inc.", "PD POWER SYSTEMS, LLC"),
    ("Engility Corp.", "ENGILITY SERVICES, LLC"),
    ("Raytheon Technical Services Co.", "RAYTHEON COMPANY"),
    ("Data Link Solutions", "VIASAT INC"),
    ("Kollsman Inc.", "ELBITAMERICA, INC."),
])
def test_a_different_legal_name_is_not_a_match(announced, recorded):
    # a subsidiary, a sister company or a joint venture is a different
    # recipient: the announcement did not name THIS one
    from load_announcement_links import recipient_name_key

    assert recipient_name_key(announced) != recipient_name_key(recorded)


@pytest.mark.parametrize("text", [None, "", "None", "  ", "Inc.", "The Co."])
def test_a_blank_or_form_only_name_matches_nothing(text):
    from load_announcement_links import recipient_name_key

    assert recipient_name_key(text) is None


def test_the_candidates_are_each_ueis_exact_total_and_names(tmp_path):
    from decimal import Decimal

    cands = candidates(["TWO"], write(tmp_path, 2026, TWO))["TWO"]
    assert sorted((c.uei, c.dollars, c.name, c.names) for c in cands) == [
        ("UEIAAAAAAAA1", Decimal("300.00"), "ALPHA CORPORATION",
         ("ALPHA CORP", "ALPHA CORPORATION")),
        ("UEIBBBBBBBB2", Decimal("250.00"), "BRAVO LLC", ("BRAVO LLC",)),
    ]


# ── the basis is stored with the link (migration 019) ──────────────────────

ORG = "recipient-basis-test"


@pytest.fixture()
def con(pg_dsn):
    with psycopg.connect(pg_dsn) as c:
        yield c
        c.rollback()


def _link(piid, name, uei, basis, *, method=ANN, confidence="high"):
    """A 14-column loader row (budget_line_awards' insert order)."""
    return ("RB0601101E", "R-1", 2026, ORG, piid, name, uei, 0.0, method,
            confidence, 2, "defense.gov contract announcement 1275111", None,
            basis)


def _stored(con, piid):
    return con.execute(
        "select method, recipient_name, recipient_uei, recipient_basis"
        " from budget_line_awards where organization = %s and award_piid = %s",
        (ORG, piid)).fetchone()


def test_the_loader_stores_the_basis_with_the_recipient(con):
    import load_announcement_links as lal

    lal.write_links(con.cursor(), [
        _link("N0003915D0008", "VIASAT INC", "L9Z1ASN3B8E7", "announcement_named"),
        _link("N0003910D0032", "L3 TECHNOLOGIES, INC.", "FRJQGQHDX4J3", "uei_tiebreak"),
    ], [])
    assert _stored(con, "N0003915D0008") == (
        ANN, "VIASAT INC", "L9Z1ASN3B8E7", "announcement_named")
    assert _stored(con, "N0003910D0032")[3] == "uei_tiebreak"


def test_a_link_that_takes_another_routes_key_takes_its_own_recipient(con):
    """The upsert used to update method/confidence/obligation on a key another
    route held and leave that route's recipient behind: the announcement link
    then published the fpds-ap row's scan-order recipient with no basis."""
    import load_announcement_links as lal

    con.execute(
        "insert into budget_line_awards (pe_bli, exhibit, fiscal_year,"
        " organization, award_piid, recipient_name, recipient_uei, method,"
        " confidence, rationale) values ('RB0601101E', 'R-1', 2026, %s,"
        " 'N0003915D0008', 'L3 TECHNOLOGIES, INC.', 'FRJQGQHDX4J3', 'fpds-ap',"
        " 'medium', 'fpds-ap route')", (ORG,))
    lal.write_links(con.cursor(), [
        _link("N0003915D0008", "VIASAT INC", "L9Z1ASN3B8E7", "announcement_named"),
    ], [])
    assert _stored(con, "N0003915D0008") == (
        ANN, "VIASAT INC", "L9Z1ASN3B8E7", "announcement_named")


def test_an_unknown_basis_is_refused(con):
    """Refused twice over: write_links stops it before any upsert (fix round
    7's loader check, incoming_member_claims), and the database's CHECK
    (migration 019) still refuses the loader's own statement run directly."""
    import load_announcement_links as lal

    with pytest.raises(ValueError, match=r"recipient_basis 'alphabet'"):
        with con.transaction():
            lal.write_links(con.cursor(), [
                _link("PIID-X", "X INC", "UEIXXXXXXXX1", "alphabet")], [])
    with pytest.raises(psycopg.errors.CheckViolation):
        with con.transaction():
            con.cursor().execute(lal.UPSERT_SQL, _link(
                "PIID-X", "X INC", "UEIXXXXXXXX1", "alphabet"))


def test_the_loaders_basis_values_are_the_rulings_three():
    from derive_ap_links import RECIPIENT_BASES

    assert RECIPIENT_BASES == ("obligation", "announcement_named", "uei_tiebreak")


# ── R-DEC-DERIVE (fix round 7): 'pre_rule' is stored, never written ─────────

@pytest.mark.parametrize("basis", ["pre_rule", None])
def test_the_loader_never_writes_a_pre_rule_or_missing_basis(con, basis):
    """Migration 019 admits 'pre_rule' for its backfill of rows whose recipient
    predates R-DEC-RECIPIENT; a link this loader writes is a fresh pick, so
    write_links refuses one that claims otherwise (or claims nothing) — and
    the raise rolls back the partition delete it ran first."""
    import load_announcement_links as lal

    lal.write_links(con.cursor(), [
        _link("KEEP-ME", "VIASAT INC", "L9Z1ASN3B8E7", "obligation")], [])
    with pytest.raises(ValueError, match=r"recipient_basis"):
        with con.transaction():
            lal.write_links(con.cursor(), [
                _link("N0003915D0008", "VIASAT INC", "L9Z1ASN3B8E7", basis)], [])
    assert _stored(con, "KEEP-ME") == (
        ANN, "VIASAT INC", "L9Z1ASN3B8E7", "obligation")
    assert _stored(con, "N0003915D0008") is None


def test_pre_rule_is_not_a_basis_the_rule_produces():
    from derive_ap_links import PRE_RULE_BASIS, RECIPIENT_BASES

    assert PRE_RULE_BASIS == "pre_rule"
    assert PRE_RULE_BASIS not in RECIPIENT_BASES
