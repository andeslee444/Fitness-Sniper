"""RULING R-DEC-135b (2026-09-26) — every recomputation of the parent pick
applies the same curated exclusions the build does.

ROADMAP #135 added data-seeds/entity_parent_exclusions.csv: a (recipient UEI,
parent UEI) pair listed there is never the recipient's parent pick in
entity_graph (the pick behind entity_xwalk, dim_entities and every family
label). Two other places re-derive that pick to measure how close each
published family's label came to losing it:

  * site/scripts/gates/familylabel-recompute.py — gate 24 leg l's margins,
    recomputed from the award lake;
  * src/govbudget/entity_label_review.py — the near-tie count the exporter
    writes to site_meta (the /methodology/ census).

Both ranked every registration of the dominant member, the excluded pair
included. Measured 2026-09-25 no published family's dominant member carries
an exclusion, so their numbers did not move — but the first exclusion on a
dominant member would have made the gate and the census disagree with the
label the build published. These tests build one lake where the dominant
member's dollar-top registration is excluded, and require the build, the gate
helper and the census to agree on what won and by how much.
"""
from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

import duckdb
import pytest

from govbudget import entity_graph
from govbudget.entity_label_review import build_entity_label_review

REPO = Path(__file__).resolve().parents[1]
GATE_SCRIPT = REPO / "site" / "scripts" / "gates" / "familylabel-recompute.py"

# One published family whose dominant member u1 filed three registrations.
# The dollar-top one (P_EX, $300) is excluded; of the rest ALPHA ($200) beats
# BRAVO ($190) by 5% — inside the 15% near-tie threshold. Without the
# exclusion the label won by 33% (300 vs 200): not a near tie.
TX = [
    # recipient_uei, recipient_name, parent_uei, parent_name, obligation
    ("u1", "DOMINANT MEMBER LLC", "P_EX", "EXCLUDED PARENT", 300.0),
    ("u1", "DOMINANT MEMBER LLC", "P_A", "ALPHA PARENT", 200.0),
    ("u1", "DOMINANT MEMBER LLC", "P_B", "BRAVO PARENT", 190.0),
    ("u2", "SMALL MEMBER INC", "P_A", "ALPHA PARENT", 50.0),
    ("u2", "SMALL MEMBER INC", "P_B", "BRAVO PARENT", 40.0),
    ("v1", "OTHER FAMILY CO", "P_V", "VICTOR PARENT", 400.0),
]


def _seed(path: Path, rows) -> Path:
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(entity_graph.PARENT_EXCLUSION_COLUMNS)
        for r in rows:
            w.writerow(r)
    return path


@pytest.fixture()
def seed(tmp_path):
    return _seed(tmp_path / "entity_parent_exclusions.csv", [(
        "u1", "DOMINANT MEMBER LLC", "P_EX", "EXCLUDED PARENT", "2026-09-26",
        "#135", "test row",
    )])


@pytest.fixture()
def empty_seed(tmp_path):
    return _seed(tmp_path / "empty_exclusions.csv", [])


@pytest.fixture()
def lake(tmp_path):
    d = tmp_path / "contracts" / "fy=2025"
    d.mkdir(parents=True)
    con = duckdb.connect()
    con.execute(
        "create table t (recipient_uei varchar, recipient_name varchar,"
        " recipient_parent_uei varchar, recipient_parent_name varchar,"
        " federal_action_obligation varchar)"
    )
    con.executemany(
        "insert into t values (?, ?, ?, ?, ?)",
        [(u, n, pu, pn, str(o)) for u, n, pu, pn, o in TX],
    )
    con.execute(f"copy t to '{d / 'part.parquet'}' (format parquet)")
    con.close()
    return [str(tmp_path / "contracts" / "fy=*" / "*.parquet")]


def _gate():
    spec = importlib.util.spec_from_file_location("familylabel_recompute", GATE_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _warehouse(tmp_path, lake, seed_path) -> duckdb.DuckDBPyConnection:
    """The warehouse the exporter reads, built from the lake the way the chain
    builds it: entity_xwalk from entity_graph (with the seed), dim_entities
    from the xwalk, fct_award_transactions from the lake."""
    xw = entity_graph.build_entity_xwalk(
        award_glob=lake, out_path=tmp_path / "entity_xwalk.parquet",
        parent_exclusions=seed_path,
    )
    con = duckdb.connect()
    con.execute(f"create table entity_xwalk as select * from read_parquet('{xw}')")
    con.execute(
        "create table dim_entities as select family_key,"
        " max(family_key) as display_name, sum(total_obligation) as total_obligation"
        " from entity_xwalk group by family_key"
    )
    con.execute(
        "create table fct_award_transactions as select recipient_uei,"
        " recipient_parent_uei, recipient_parent_name,"
        " try_cast(federal_action_obligation as double) as obligation"
        f" from read_parquet({lake!r}, union_by_name=true)"
    )
    return con


def _dominant_pick(con, family_key):
    return con.execute(
        "select parent_uei, parent_name from entity_xwalk where family_key = ?"
        " order by total_obligation desc limit 1", [family_key]
    ).fetchone()


# ── the build, the gate helper and the census agree ──────────────────────────

def test_gate_helper_ranks_the_same_registrations_the_build_picked(tmp_path, lake, seed):
    con = _warehouse(tmp_path, lake, seed)
    # The build: u1's excluded top registration is never its pick.
    assert _dominant_pick(con, "ALPHA PARENT") == ("P_A", "ALPHA PARENT")
    gate = _gate()
    out = gate.recompute(con, lake, gate.load_exclusions(seed))
    fam = {f["family_key"]: f for f in out["families"]}["ALPHA PARENT"]
    assert fam["won"] == "ALPHA PARENT"            # what the build published
    assert fam["runner_up"] == "BRAVO PARENT"
    assert fam["won_dollars"] == 200.0 and fam["runner_up_dollars"] == 190.0
    assert fam["margin"] == pytest.approx(0.05)


def test_without_the_exclusion_the_gate_helper_would_disagree_with_the_build(
    tmp_path, lake, seed
):
    """The defect this ruling closes: the helper ranked the excluded pair and
    reported a label the build never published, by a margin (33%) that hides
    the real near tie (5%)."""
    con = _warehouse(tmp_path, lake, seed)
    gate = _gate()
    fam = {f["family_key"]: f for f in gate.recompute(con, lake, [])["families"]}[
        "ALPHA PARENT"
    ]
    assert fam["won"] == "EXCLUDED PARENT"
    assert fam["margin"] == pytest.approx(1 / 3)


def test_the_census_counts_the_near_tie_the_build_created(tmp_path, lake, seed):
    con = _warehouse(tmp_path, lake, seed)
    assert build_entity_label_review(con, parent_exclusions=seed) == {
        "near_ties": 1, "families": 2, "threshold_pct": 15,
    }


def test_the_census_without_the_exclusion_misses_it(tmp_path, lake, seed, empty_seed):
    con = _warehouse(tmp_path, lake, seed)
    assert build_entity_label_review(con, parent_exclusions=empty_seed)["near_ties"] == 0
    assert build_entity_label_review(con, parent_exclusions=())["near_ties"] == 0


def test_an_exclusion_on_a_non_dominant_member_moves_no_margin(tmp_path, lake, seed):
    """The margin is the DOMINANT member's (the one dim_entities takes its
    label from). u2 is ALPHA's smaller member: excluding one of its pairs
    leaves it in ALPHA (its other pair still wins) and moves no margin."""
    both = _seed(tmp_path / "both.csv", [
        ("u1", "DOMINANT MEMBER LLC", "P_EX", "EXCLUDED PARENT", "2026-09-26", "#135", "t"),
        ("u2", "SMALL MEMBER INC", "P_B", "BRAVO PARENT", "2026-09-26", "#135", "t"),
    ])
    con = _warehouse(tmp_path, lake, both)
    assert con.execute(
        "select family_key from entity_xwalk where recipient_uei = 'u2'"
    ).fetchone()[0] == "ALPHA PARENT"
    gate = _gate()
    margins = lambda ex: {  # noqa: E731
        f["family_key"]: f["margin"] for f in gate.recompute(con, lake, ex)["families"]
    }
    assert margins(gate.load_exclusions(both)) == margins(gate.load_exclusions(seed))
    assert build_entity_label_review(con, parent_exclusions=both) == (
        build_entity_label_review(con, parent_exclusions=seed)
    )


# ── one seed, read the same way everywhere ───────────────────────────────────

def test_every_recomputation_reads_the_build_seed_by_default():
    gate = _gate()
    assert gate.EXCLUSIONS_SEED.resolve() == entity_graph.DEFAULT_PARENT_EXCLUSIONS.resolve()
    assert gate.load_exclusions(gate.EXCLUSIONS_SEED) == [
        (e.recipient_uei, e.excluded_parent_uei)
        for e in entity_graph.load_parent_exclusions(entity_graph.DEFAULT_PARENT_EXCLUSIONS)
    ]
    # #135's row is the one on file today.
    assert ("H7KFX5RH75K3", "EGAVSJTA2D81") in gate.load_exclusions(gate.EXCLUSIONS_SEED)


def test_the_census_applies_the_build_seed_when_the_exporter_calls_it(
    tmp_path, lake, seed, monkeypatch
):
    """export_site calls build_entity_label_review(con) with no seed argument;
    the default must be the build's own seed."""
    con = _warehouse(tmp_path, lake, seed)
    monkeypatch.setattr(entity_graph, "DEFAULT_PARENT_EXCLUSIONS", seed)
    assert build_entity_label_review(con)["near_ties"] == 1


def test_gate_helper_refuses_a_missing_or_malformed_seed(tmp_path):
    gate = _gate()
    with pytest.raises(gate.SeedError, match="missing"):
        gate.load_exclusions(tmp_path / "nope.csv")
    bad = tmp_path / "bad.csv"
    bad.write_text("recipient_uei,parent_uei\nu1,P_EX\n")
    with pytest.raises(gate.SeedError, match="columns"):
        gate.load_exclusions(bad)
    blank = _seed(tmp_path / "blank.csv", [("u1", "X", "", "Y", "2026-09-26", "#1", "n")])
    with pytest.raises(gate.SeedError, match="empty"):
        gate.load_exclusions(blank)


def test_the_census_refuses_a_missing_seed(tmp_path, lake, seed):
    con = _warehouse(tmp_path, lake, seed)
    with pytest.raises(entity_graph.ParentExclusionError, match="missing"):
        build_entity_label_review(con, parent_exclusions=tmp_path / "nope.csv")
