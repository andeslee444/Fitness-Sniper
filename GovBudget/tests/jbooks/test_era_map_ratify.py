"""era_map ratify / check, the dbt seed config and the `era-map` CLI (plan
Task 12; spec §4.3, §5.3, §7) on the miniature lake in era_map_fixtures."""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import pytest
import yaml

from govbudget.jbooks import era_map
from jbooks.era_map_fixtures import make_lake, make_raw_docs

ROOT = Path(__file__).resolve().parents[2]
ON = date(2026, 10, 2)
DECIDED = date(2026, 10, 5)


@pytest.fixture(autouse=True)
def _mini_org_split(monkeypatch):
    monkeypatch.setattr(era_map, "ORG_SPLIT_CODES", frozenset({"20"}))


@pytest.fixture()
def world(tmp_path):
    db = make_lake(tmp_path / "lake")
    raw = make_raw_docs(tmp_path)
    out = tmp_path / "research" / "era_map"
    seed = tmp_path / "seeds" / "p1_era_code_decisions.csv"
    era_map.propose(duckdb_path=db, raw_docs_dir=raw, out_dir=out,
                    seed_path=seed, decided_on=ON)
    return {"db": db, "out": out, "seed": seed, "review": out / "review.csv"}


def read(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def write_review(path, rows):
    era_map.write_csv(path, era_map.REVIEW_COLUMNS, rows)


def decide(world, edits, extra=()):
    """Apply {chain_id: {field: value}} to review.csv; append extra rows
    (copies of an existing chain's row with overrides, for range splits)."""
    rows = read(world["review"])
    by_id = {r["chain_id"]: r for r in rows}
    for cid, fields in edits.items():
        by_id[cid].update(fields)
    for cid, fields in extra:
        rows.append({**by_id[cid], **fields})
    write_review(world["review"], rows)


def ratify(world, batch="B1", decided_on=DECIDED):
    return era_map.ratify(review_csv=world["review"], seed_path=world["seed"],
                          batch=batch, decided_on=decided_on,
                          duckdb_path=world["db"])


GOOD = {
    "1045|1612N|": {"decision": "same_program", "note": "OHIO Replacement = COLUMBIA"},
    "20|0300D|DSS": {"decision": "same_program"},   # pre-filled 0300D/DCSA
    "50|0300D|": {"decision": "exclude_reused_code", "last_edition": "2022"},
    "20|0300D|DHRA": {"decision": "history_only"},  # pre-filled 0300D/DHRA
}
SPLIT = [("50|0300D|", {"decision": "history_only", "first_edition": "2023",
                        "last_edition": "2023"})]


# ---------------------------------------------------------------------------
# ratify
# ---------------------------------------------------------------------------

def test_ratify_merges_a_batch_with_a_range_split(world):
    decide(world, GOOD, SPLIT)
    assert ratify(world) == 5
    seed = {r["decision_id"]: r for r in read(world["seed"])}
    b1 = {k: r for k, r in seed.items() if r["ruling"] == "R-DEC-ERA-B1"}
    assert set(b1) == {"1045|1612N||2022-2022", "20|0300D|DSS|2022-2022",
                       "50|0300D||2022-2022", "50|0300D||2023-2023",
                       "20|0300D|DHRA|2023-2023"}
    assert (b1["20|0300D|DHRA|2023-2023"]["program_account"],
            b1["20|0300D|DHRA|2023-2023"]["program_org"]) == ("0300D", "DHRA")
    dss = b1["20|0300D|DSS|2022-2022"]
    assert (dss["decision"], dss["program_account"], dss["program_org"]) == (
        "same_program", "0300D", "DCSA")
    assert {r["decided_by"] for r in b1.values()} == {"owner"}
    assert {r["decided_on"] for r in b1.values()} == {"2026-10-05"}
    assert b1["1045|1612N||2022-2022"]["note"] == "OHIO Replacement = COLUMBIA"
    assert b1["50|0300D||2022-2022"]["n_keys"] == "1"
    assert b1["50|0300D||2023-2023"]["titles_seen"] == "2023: Indian Incentive Program"
    assert len(seed) == 7 + 5
    # Fix round 2's MVTRUE|3021F| isn't part of this GOOD/SPLIT batch — it
    # stays undecided (ratify is explicitly allowed to be partial; a later
    # batch would pick it up).
    assert era_map.check(duckdb_path=world["db"], seed_path=world["seed"]) == {
        "undecided": [{"chain_id": "MVTRUE|3021F|", "editions": [2023], "n_keys": 1}],
        "stale": []}


@pytest.mark.parametrize("edits, extra, message", [
    ({"1045|1612N|": {"decision": "same"}}, [], "not in"),
    ({"1045|1612N|": {"decision": "same_program", "keys_sha256": "0" * 64}}, [],
     "changed since review"),
    ({"20|0300D|DSS": {"decision": "same_program", "program_org": ""}}, [],
     "program_account and program_org are required"),
    ({"20|0300D|DSS": {"decision": "same_program", "program_org": "DSS"}}, [],
     "is not a PB2026 page"),
    ({"20|0300D|DHRA": {"decision": "same_program"}}, [], "is not a PB2026 page"),
    ({"20|0300D|DHRA": {"decision": "history_only", "program_org": "XYZ"}}, [],
     "is not a PB2024-26 P-1 line"),
    ({"1045|1612N|": {"decision": "same_program", "program_account": "1611N"}}, [],
     "only set for"),
    ({"50|0300D|": {"decision": "history_only", "successor_code": "5731D15610"}}, [],
     "is not the book-stated successor"),
    ({"50|0300D|": {"decision": "history_only", "first_edition": "2017"}}, [],
     "outside the chain"),
    ({"50|0300D|": {"decision": "history_only"}},
     [("50|0300D|", {"decision": "exclude_reused_code", "first_edition": "2023"})],
     "overlaps"),
    # half a range split: PB2023 would never return to review.csv
    ({"50|0300D|": {"decision": "exclude_reused_code", "last_edition": "2022"}}, [],
     "editions 2023 left undecided"),
])
def test_ratify_refuses_and_writes_nothing(world, edits, extra, message):
    decide(world, edits, extra)
    before = world["seed"].read_bytes()
    with pytest.raises(ValueError, match=message):
        ratify(world)
    assert world["seed"].read_bytes() == before


def test_ratify_refuses_bad_batch_labels_and_reuse(world):
    decide(world, GOOD, SPLIT)
    with pytest.raises(ValueError, match="is not B<n>"):
        ratify(world, batch="b1")
    assert ratify(world) == 5
    with pytest.raises(ValueError, match="already in"):
        ratify(world)
    with pytest.raises(ValueError, match="overlaps"):
        ratify(world, batch="B2")


def test_propose_after_ratify_drops_the_ratified_chains(world):
    decide(world, GOOD, SPLIT)
    ratify(world)
    era_map.propose(duckdb_path=world["db"], raw_docs_dir=world["db"].parents[2] / "raw_docs",
                    out_dir=world["out"], seed_path=world["seed"], decided_on=ON)
    # Fix round 2's MVTRUE|3021F| wasn't in this batch, so it's the only
    # chain re-proposed back to review.csv.
    assert [r["chain_id"] for r in read(world["review"])] == ["MVTRUE|3021F|"]
    assert sum(r["ruling"] == "R-DEC-ERA-B1" for r in read(world["seed"])) == 5


def test_ratify_refuses_an_undecided_file(world):
    with pytest.raises(ValueError, match="no row has a decision"):
        ratify(world)


def test_ratify_accepts_the_book_stated_successor(world, tmp_path):
    # a review row for the JLTV chain (class-ruled in this world) re-proposed
    # after an owner override: drop its class-ruled seed row first
    seed = [r for r in read(world["seed"]) if r["line_item_code"] != "5600D15603"]
    era_map.write_seed(world["seed"], seed)
    chains = {r["chain_id"]: r for r in read(world["out"] / "chains.csv")}
    jltv = chains["5600D15603|2035A|"]
    row = {c: "" for c in era_map.REVIEW_COLUMNS}
    row.update({"chain_id": jltv["chain_id"], "first_edition": "2022",
                "last_edition": "2023", "keys_sha256": jltv["keys_sha256"],
                "decision": "history_only", "successor_code": "5731D15610"})
    write_review(world["review"], [row])
    assert ratify(world) == 1
    got = next(r for r in read(world["seed"]) if r["line_item_code"] == "5600D15603")
    assert (got["successor_code"], got["successor_account"]) == ("5731D15610", "2035A")
    assert got["successor_evidence"] == jltv["successor_evidence"]


# ---------------------------------------------------------------------------
# one organization per page grain and edition
# ---------------------------------------------------------------------------

@pytest.fixture()
def clash_world(tmp_path, monkeypatch):
    # PB2022 prints `10` for TJS (page 10 is TJS's; class-ruled SAME) and DPAA,
    # and `20` for DTRA (page 20-DTRA; class-ruled SAME) and DLA.
    monkeypatch.setattr(era_map, "ORG_SPLIT_CODES", frozenset({"10", "20"}))
    db = make_lake(tmp_path / "lake", org_clash=True)
    out = tmp_path / "research" / "era_map"
    seed = tmp_path / "seeds" / "p1_era_code_decisions.csv"
    era_map.propose(duckdb_path=db, raw_docs_dir=make_raw_docs(tmp_path), out_dir=out,
                    seed_path=seed, decided_on=ON)
    return {"db": db, "out": out, "seed": seed, "review": out / "review.csv"}


@pytest.mark.parametrize("edits", [
    {"10|0300D|DPAA": {"decision": "same_program"}},
    {"20|0300D|DLA": {"decision": "same_program", "program_account": "0300D",
                      "program_org": "DTRA"}},
])
def test_ratify_refuses_a_second_organization_on_one_page(clash_world, edits):
    decide(clash_world, edits)
    before = clash_world["seed"].read_bytes()
    with pytest.raises(ValueError, match="same_program collides with .* in PB2022"):
        ratify(clash_world)
    assert clash_world["seed"].read_bytes() == before


def test_ratify_accepts_the_pre_filled_history_only(clash_world):
    decide(clash_world, {"10|0300D|DPAA": {"decision": "history_only"},
                         "20|0300D|DLA": {"decision": "history_only"}})
    assert ratify(clash_world) == 2
    got = {r["decision_id"]: (r["decision"], r["program_account"], r["program_org"])
           for r in read(clash_world["seed"]) if r["ruling"] == "R-DEC-ERA-B1"}
    assert got == {"10|0300D|DPAA|2022-2022": ("history_only", "", ""),
                   # the chain's own identity: no PB2024-26 line prints 20 for DLA
                   "20|0300D|DLA|2022-2022": ("history_only", "0300D", "DLA")}


def test_ratify_refuses_two_organizations_on_one_page_in_one_batch(clash_world):
    # TJS's chain re-reviewed (its class-ruled row dropped) beside DPAA's
    era_map.write_seed(clash_world["seed"], [
        r for r in read(clash_world["seed"]) if r["line_item_code"] != "10"])
    tjs = {r["chain_id"]: r for r in read(clash_world["out"] / "chains.csv")}[
        "10|0300D|TJS"]
    rows = read(clash_world["review"])
    rows.append({**{c: "" for c in era_map.REVIEW_COLUMNS},
                 "chain_id": tjs["chain_id"], "first_edition": "2022",
                 "last_edition": "2023", "keys_sha256": tjs["keys_sha256"],
                 "decision": "same_program"})
    dpaa = next(r for r in rows if r["chain_id"] == "10|0300D|DPAA")
    dpaa["decision"] = "same_program"
    write_review(clash_world["review"], rows)
    with pytest.raises(ValueError, match="same_program collides with"):
        ratify(clash_world)
    dpaa["decision"] = "history_only"
    write_review(clash_world["review"], rows)
    assert ratify(clash_world) == 2


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------

def test_check_lists_undecided_chains(world):
    res = era_map.check(duckdb_path=world["db"], seed_path=world["seed"])
    assert res["stale"] == []
    # Fix round 2 adds MVTRUE|3021F| (a genuine account move) to the world.
    assert res["undecided"] == [
        {"chain_id": "1045|1612N|", "editions": [2022], "n_keys": 1},
        {"chain_id": "20|0300D|DHRA", "editions": [2023], "n_keys": 1},
        {"chain_id": "20|0300D|DSS", "editions": [2022], "n_keys": 1},
        {"chain_id": "50|0300D|", "editions": [2022, 2023], "n_keys": 2},
        {"chain_id": "MVTRUE|3021F|", "editions": [2023], "n_keys": 1},
    ]


def test_check_flags_a_stale_and_a_vanished_decision(world):
    rows = read(world["seed"])
    target = next(r for r in rows if r["line_item_code"] == "ATA000")
    target["keys_sha256"] = "f" * 64
    ghost = {**target, "decision_id": "GHOST1|3010F||2022-2022",
             "line_item_code": "GHOST1", "first_edition": "2022",
             "last_edition": "2022"}
    era_map.write_seed(world["seed"], rows + [ghost])
    stale = {s["decision_id"]: s for s in era_map.check(
        duckdb_path=world["db"], seed_path=world["seed"])["stale"]}
    assert set(stale) == {"ATA000|3010F||2022-2023", "GHOST1|3010F||2022-2022"}
    assert stale["ATA000|3010F||2022-2023"]["lake_n_keys"] == 2
    assert stale["GHOST1|3010F||2022-2022"]["lake_n_keys"] == 0


# ---------------------------------------------------------------------------
# dbt seed config
# ---------------------------------------------------------------------------

def test_dbt_seed_config_is_all_varchar():
    project = yaml.safe_load((ROOT / "dbt" / "dbt_project.yml").read_text())
    cfg = project["seeds"]["govbudget"]["p1_era_code_decisions"]["+column_types"]
    assert cfg == {c: "varchar" for c in era_map.SEED_COLUMNS}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@pytest.fixture()
def cli_world(tmp_path, monkeypatch):
    from govbudget import config

    db = make_lake(tmp_path / "data")
    raw = make_raw_docs(tmp_path / "data")
    monkeypatch.setattr(config, "DUCKDB_PATH", db)
    monkeypatch.setattr(config, "RAW_DOCS_DIR", raw)
    monkeypatch.setattr(config, "RESEARCH_DIR", tmp_path / "repo" / "data" / "research")
    monkeypatch.setattr(config, "ROOT", tmp_path / "repo")
    return tmp_path / "repo"


def test_cli_propose_check_ratify(cli_world, capsys):
    from govbudget.cli import main

    main(["era-map", "propose"])
    out = capsys.readouterr().out
    # Fix round 2 adds MVTRUE|3021F| (a genuine account move whose
    # destination title matches) to the fixture world.
    assert out.startswith("era-map propose: 16 era keys, 12 chains; rulings"
                          " SAME=3 EXCLUDE=2 HISTORY=2; 5 chain(s) for review")
    seed = cli_world / "dbt" / "seeds" / "p1_era_code_decisions.csv"
    assert {r["decided_on"] for r in read(seed)} == {"2026-10-02"}
    assert (cli_world / "data" / "research" / "era_map" / "counts.json").is_file()

    main(["era-map", "check"])
    assert capsys.readouterr().out.splitlines()[-1] == (
        "era-map check: 5 undecided chain(s), 0 stale decision(s)")
    with pytest.raises(SystemExit) as exc:
        main(["era-map", "check", "--strict"])
    assert exc.value.code == 1

    with pytest.raises(SystemExit) as exc:
        main(["era-map", "ratify", "--batch", "B1", "--decided-on", "2026-10-05"])
    assert exc.value.code == 1
    assert "REFUSED" in capsys.readouterr().err


@pytest.mark.parametrize("argv", [["era-map", "--help"], ["era-map", "propose", "--help"],
                                  ["era-map", "ratify", "--help"],
                                  ["era-map", "check", "--help"]])
def test_cli_help_renders(argv, capsys):
    from govbudget.cli import main

    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 0
    assert "usage: govbudget era-map" in capsys.readouterr().out
