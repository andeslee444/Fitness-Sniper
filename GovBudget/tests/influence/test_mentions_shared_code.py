"""RULING R-DEC-176b (2026-09-26) — `influence rematch` is a measurement, so it
must give the same rows on every run.

Until this fix `build_program_terms` kept ONE title per code: it walked the
(pe_bli, title) rows and ended each code with `result[pe_bli] = compiled`, so
for the 13 codes two or three dim_programs rows share, whichever member's row
came LAST decided which title words could match. `cmd_influence_rematch` read
those rows with no ORDER BY, so the same corpus gave different mention counts
from run to run: the stage-1 checker measured 12,509 and 12,487 rows on two
as-is runs of the same code, 12,571 sorted and 12,432 reverse-sorted
(2026-09-25, read-only on the lake). A figure that moves with row order is not
a measurement.

The rule these tests pin: a shared code is matched against EVERY member's
title, each title on its own. A `multi_token` row needs two distinct title
words from ONE member's title (a pair split across two members' titles —
"Major" from "Major Equipment", "Vehicles" from "Vehicles" — names neither
program, so it is not evidence), and the row is attributed to the CODE, never
to a member: RULING R-INT-9 already withholds every shared-code row from every
member's program page, and /filing/ labels it with both members' names beside
the shared-code note. The result no longer depends on the order of the input
rows, and the chain command also reads them sorted.

Titles are exactly as dim_programs carries them (read 2026-09-25); the filing
snippets are quoted from data/parquet/influence/lda_activities.parquet (the
comment names the filing_uuid prefix).
"""
from __future__ import annotations

import random

import duckdb
import pytest

from govbudget.influence.mentions import build_program_terms, find_mentions

# Every shared code in dim_programs on 2026-09-25, every member's title, plus
# single-title programs so the shuffles interleave both shapes.
PROGRAMS = [
    ("0145", "F/A-18E/F (Fighter) Hornet"),
    ("0145", "General Purpose Bombs"),
    ("1350", "Infantry Weapons Ammunition"),
    ("1350", "Missile Industrial Facilities"),
    ("20", "Major Equipment"),
    ("20", "Vehicles"),
    ("2101", "Tomahawk"),
    ("2101", "Tomahawk"),
    ("2210", "Joint Advance Tactical Missile (JATM)"),
    ("2210", "Submarine Acoustic Warfare System"),
    ("2292", "Naval Strike Missile (NSM)"),
    ("2292", "Naval Strike Missile (NSM)"),
    ("30", "Major Equipment"),
    ("30", "Major Equipment, OSD"),
    ("30", "Other Major Equipment"),
    ("3010", "LPD Flight II"),
    ("3010", "Shipboard Tactical Communications"),
    ("3050", "Medium Landing Ship"),
    ("3050", "Ship Communications Automation"),
    ("3215", "MK-54 Torpedo Mods"),
    ("3215", "Satellite Communications Systems"),
    ("3302", "ASW Range Support"),
    ("3302", "Joint Communications Support Element (JCSE)"),
    ("4217", "Advanced Arresting Gear (AAG)"),
    ("4217", "Gun Mount Mods"),
    ("500", "Major Equipment"),
    ("500", "Personnel Administration"),
    ("1045", "COLUMBIA Class Submarine"),
    ("MD08", "Ground Based Midcourse"),
    ("0604122D8Z", "JADC2 Development and Experimentation Activities"),
]

ACTIVITIES = [
    # fedcb26c — Missile / Industrial, both from "Missile Industrial Facilities"
    {"filing_uuid": "fedcb26c", "description":
        "Issues relating to industrial base resilience, missiles, missile"
        " defense, counter-unmanned aerial system"},
    # 96ae87f5 — Weapons / Ammunition from "Infantry Weapons Ammunition",
    # Missile alone from the other member
    {"filing_uuid": "96ae87f5", "description":
        "Procurement Ammunition Navy & Marine Corps; Missile Procurement- Army,"
        " Air Force, & Navy; Procurement Weapons & Tracked Combat Vehicles"
        " (WTCV); Other"},
    # e93637ae — Submarine / Warfare from "Submarine Acoustic Warfare System"
    {"filing_uuid": "e93637ae", "description":
        "radar and sensor systems, submarine warfare funding provisions,"
        " military space"},
    # ad7050ea — Satellite / Communications from "Satellite Communications
    # Systems"
    {"filing_uuid": "ad7050ea", "description":
        "weapons, missile defense, and military satellite & space programs."
        " Communications science and technology. Manufacturing"},
    # 5b4c65cb — General / Purpose from "General Purpose Bombs"
    {"filing_uuid": "5b4c65cb", "description":
        "Artificial Intelligence (AI), general purpose AI and foundation"
        " models, open source AI"},
    # df9bdc06 — Columbia / Class / Submarine from "COLUMBIA Class Submarine" (a
    # single-title code riding along), Flight alone from "LPD Flight II"
    {"filing_uuid": "df9bdc06", "description":
        "Procurement DDG(X) DDG 1002 LHA and LPD Flight II Columbia Class"
        " Submarine Procurement"},
    # constructed: one word from EACH of 1350's members and nothing else
    {"filing_uuid": "split-1350", "description":
        "Weapons funding and industrial policy."},
    # constructed: "Major" from 20's first member, "Vehicles" from its second
    {"filing_uuid": "split-20", "description":
        "Major investments in tactical vehicles."},
    # constructed: BOTH of 1350's members qualify in one filing
    {"filing_uuid": "both-1350", "description":
        "Infantry weapons and ammunition; missile industrial facilities."},
]


def _seed(tmp_path_factory):
    # An empty alias seed: these tests exercise the title-token tier only.
    seed = tmp_path_factory.mktemp("seed") / "program_aliases.csv"
    seed.write_text("pe_bli,alias,note\n")
    return seed


@pytest.fixture(scope="module")
def seed(tmp_path_factory):
    return _seed(tmp_path_factory)


def _shape(terms):
    """Everything find_mentions reads, in order, as plain data."""
    return [
        (
            pe,
            [(t, p.pattern, p.flags, k) for t, p, k in entries],
            sorted(sorted(g) for g in entries.title_groups),
        )
        for pe, entries in terms.items()
    ]


def _rows(programs, seed, activities=ACTIVITIES):
    return find_mentions(activities, build_program_terms(programs, seed_path=seed))


def _by_pair(rows):
    return {(r["filing_uuid"], r["pe_bli"]): r for r in rows}


# ── the determinism the ruling asks for ─────────────────────────────────────

@pytest.mark.parametrize("rng_seed", [1, 2, 3, 4, 5, 6, 7, 8])
def test_shuffled_program_rows_build_identical_terms(seed, rng_seed):
    shuffled = list(PROGRAMS)
    random.Random(rng_seed).shuffle(shuffled)
    assert _shape(build_program_terms(shuffled, seed_path=seed)) == _shape(
        build_program_terms(PROGRAMS, seed_path=seed)
    )


def test_two_runs_with_shuffled_program_rows_give_identical_rows(seed):
    """The ruling's test: two runs, the input rows in different orders, the
    same rows out — values AND order."""
    first = list(PROGRAMS)
    second = list(PROGRAMS)
    random.Random(176).shuffle(first)
    second.reverse()
    assert first != second
    a = _rows(first, seed)
    b = _rows(second, seed)
    assert a == b
    assert a, "the fixture must produce rows for the comparison to mean anything"


def test_rows_do_not_depend_on_which_member_row_comes_last(seed):
    """The exact defect: 1350's rows were decided by the LAST member row."""
    infantry_last = [p for p in PROGRAMS if p[0] != "1350"] + [
        ("1350", "Missile Industrial Facilities"),
        ("1350", "Infantry Weapons Ammunition"),
    ]
    missile_last = [p for p in PROGRAMS if p[0] != "1350"] + [
        ("1350", "Infantry Weapons Ammunition"),
        ("1350", "Missile Industrial Facilities"),
    ]
    assert _rows(infantry_last, seed) == _rows(missile_last, seed)


# ── which titles a shared code matches ──────────────────────────────────────

def test_a_shared_code_matches_either_members_title(seed):
    got = _by_pair(_rows(PROGRAMS, seed))
    # Each member's own words qualify the code, whatever the row order.
    assert got[("fedcb26c", "1350")]["matched_term"] == "Missile|Industrial"
    assert got[("96ae87f5", "1350")]["matched_term"] == "Weapons|Ammunition"
    assert got[("e93637ae", "2210")]["matched_term"] == "Submarine|Warfare"
    assert got[("ad7050ea", "3215")]["matched_term"] == "Satellite|Communications"
    assert got[("5b4c65cb", "0145")]["matched_term"] == "General|Purpose"
    for key in [("fedcb26c", "1350"), ("96ae87f5", "1350"), ("e93637ae", "2210"),
                ("ad7050ea", "3215"), ("5b4c65cb", "0145")]:
        assert got[key]["evidence_kind"] == "multi_token"
        # One row per (filing, code): the row is the code's, not a member's.
        assert got[key]["pe_bli"] == key[1]


def test_a_pair_split_across_two_members_titles_is_not_evidence(seed):
    """Two words that no single member's title holds together name neither
    program — the #52 rule (two words of the program's own title) applies per
    member, never to the pooled vocabulary of a code."""
    got = _by_pair(_rows(PROGRAMS, seed))
    # "Weapons" (Infantry Weapons Ammunition) + "Industrial" (Missile
    # Industrial Facilities)
    assert ("split-1350", "1350") not in got
    # "Major" (Major Equipment) + "Vehicles" (Vehicles)
    assert ("split-20", "20") not in got
    # 96ae87f5 also carries "Missile", but alone it is one word of the other
    # member's title: it is not part of the evidence and not in matched_term.
    assert "Missile" not in got[("96ae87f5", "1350")]["matched_term"]


def test_both_members_qualifying_record_both_in_canonical_order(seed):
    """When each member's own title qualifies, matched_term records every
    qualifying word: member titles in sorted order, each title's words in
    title order — the same string whatever order the rows arrived in."""
    got = _by_pair(_rows(PROGRAMS, seed))
    assert got[("both-1350", "1350")]["matched_term"] == (
        "Infantry|Weapons|Ammunition|Missile|Industrial|Facilities"
    )


def test_identical_member_titles_collapse_to_one_group(seed):
    terms = build_program_terms(PROGRAMS, seed_path=seed)
    assert len(terms["2292"].title_groups) == 1
    assert [t for t, _p, _k in terms["2292"]].count("Naval") == 1
    rows = find_mentions(
        [{"filing_uuid": "nsm", "description": "Naval Strike Missile procurement"}],
        terms,
    )
    assert [(r["pe_bli"], r["matched_term"]) for r in rows] == [
        # "Strike" is a GENERIC_WORDS entry; the two words left are the
        # evidence.
        ("2292", "Naval|Missile")
    ]


def test_single_title_codes_are_unchanged(seed):
    """The ~1,909 one-title codes keep exactly the pre-fix term list: title
    words in title order, then the code, then aliases."""
    terms = build_program_terms([("1045", "COLUMBIA Class Submarine")], seed_path=seed)
    assert [(t, k) for t, _p, k in terms["1045"]] == [
        ("COLUMBIA", "title_token"), ("Class", "title_token"),
        ("Submarine", "title_token"), ("1045", "pe_code"),
    ]
    assert terms["1045"].title_groups == (
        frozenset({"COLUMBIA", "CLASS", "SUBMARINE"}),
    )
    got = _by_pair(_rows(PROGRAMS, seed))
    assert got[("df9bdc06", "1045")]["matched_term"] == "COLUMBIA|Class|Submarine"


def test_hand_built_term_lists_keep_the_old_single_group_rule():
    """A caller that builds its own list of (term, pattern, kind) tuples (no
    title_groups) is read as one title — the rule before R-DEC-176b."""
    import re

    def wb(t):
        return re.compile(r"(?<![A-Za-z0-9])" + re.escape(t) + r"(?![A-Za-z0-9])", re.I)

    terms = {"X1": [("Alpha", wb("Alpha"), "title_token"),
                    ("Bravo", wb("Bravo"), "title_token")]}
    rows = find_mentions([{"filing_uuid": "u", "description": "alpha bravo"}], terms)
    assert [(r["pe_bli"], r["matched_term"]) for r in rows] == [("X1", "Alpha|Bravo")]


# ── the chain command reads the rows sorted ─────────────────────────────────

def _lake(tmp_path, name, program_rows):
    """A tiny lake: dim_programs in the given PHYSICAL order, one activities
    parquet."""
    root = tmp_path / name
    (root / "parquet" / "influence").mkdir(parents=True)
    (root / "duckdb").mkdir()
    db = root / "duckdb" / "govbudget.duckdb"
    con = duckdb.connect(str(db))
    con.execute("create table dim_programs (pe_bli varchar, title varchar)")
    con.executemany("insert into dim_programs values (?, ?)", program_rows)
    con.close()
    acon = duckdb.connect()
    acon.execute("create table a (filing_uuid varchar, description varchar)")
    acon.executemany(
        "insert into a values (?, ?)",
        [(a["filing_uuid"], a["description"]) for a in ACTIVITIES],
    )
    acon.execute(
        f"copy a to '{root / 'parquet' / 'influence' / 'lda_activities.parquet'}'"
        " (format parquet)"
    )
    acon.close()
    return root, db


def _run_rematch(monkeypatch, root, db):
    from govbudget import cli, config

    monkeypatch.setattr(config, "PARQUET_DIR", root / "parquet")
    monkeypatch.setattr(config, "DUCKDB_PATH", db)
    cli.cmd_influence_rematch(None)
    con = duckdb.connect()
    try:
        return con.execute(
            "select * from read_parquet(?)",
            [str(root / "parquet" / "influence" / "lda_program_mentions.parquet")],
        ).fetchall()
    finally:
        con.close()


def test_rematch_twice_with_dim_programs_in_different_orders_writes_identical_rows(
    tmp_path, monkeypatch
):
    forward = list(PROGRAMS)
    backward = list(reversed(PROGRAMS))
    a = _run_rematch(monkeypatch, *_lake(tmp_path, "a", forward))
    b = _run_rematch(monkeypatch, *_lake(tmp_path, "b", backward))
    assert a == b
    assert a


def test_rematch_reads_dim_programs_sorted(tmp_path, monkeypatch):
    """The command itself hands build_program_terms the rows in (pe_bli,
    title) order, so nothing downstream can depend on the table's physical
    order either."""
    from govbudget.influence import mentions

    seen: list = []
    real = mentions.build_program_terms

    def spy(programs, **kw):
        seen.append(list(programs))
        return real(programs, **kw)

    monkeypatch.setattr(mentions, "build_program_terms", spy)
    _run_rematch(monkeypatch, *_lake(tmp_path, "c", list(reversed(PROGRAMS))))
    assert seen and seen[0] == sorted(PROGRAMS)
