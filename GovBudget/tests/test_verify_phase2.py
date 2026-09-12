from pathlib import Path

import duckdb

from govbudget.verify_phase2 import (
    entity_gate,
    geography_gate,
    golden_gate,
    sam_gate,
)


def make_marts(tmp_path: Path) -> Path:
    db = tmp_path / "t.duckdb"
    con = duckdb.connect(str(db))
    con.execute(
        """
        create table entity_xwalk as select * from (values
          ('U1','BOEING DEFENSE','P1','THE BOEING COMPANY','BOEING','parent_name','high',100.0),
          ('U2','BOEING AERO','P2','BOEING COMPANY, THE (INC)','BOEING','parent_name','high',50.0),
          ('U3','HII MISSION','P3','HUNTINGTON INGALLS INDUSTRIES, INC','HUNTINGTON INGALLS INDUSTRIES','parent_name','high',75.0),
          ('U4','MYSTERY','','','U4','self_uei','medium',10.0)
        ) t(recipient_uei, recipient_name, parent_uei, parent_name, family_key, method, confidence, total_obligation)
        """
    )
    con.execute(
        """
        create table fct_award_transactions as select * from (values
          ('K1','contract','CA','CA-52', 10.0),
          ('K2','contract','MD','MD-04', 20.0),
          ('K3','contract', null, null, 5.0)
        ) t(transaction_key, award_type, pop_state, pop_district, obligation)
        """
    )
    con.close()
    return db


def test_entity_gate(tmp_path):
    g = entity_gate(make_marts(tmp_path), top_n=4)
    assert g["resolved_pct"] == 75.0  # 3 of 4 via parent evidence
    assert g["top_n"] == 4


def test_golden_gate(tmp_path):
    g = golden_gate(make_marts(tmp_path))
    assert g["boeing_ueis"] == 2 and g["boeing_one_family"] is True
    assert g["hii_one_family"] is True


def test_geography_gate(tmp_path):
    g = geography_gate(make_marts(tmp_path))
    assert g["with_state"] == 2
    assert g["resolved_pct"] == 100.0  # both state-bearing rows have districts


def make_sam_marts(tmp_path: Path, sam_rows: list[tuple], *, sam_columns=True) -> Path:
    """A tmp mart with two families whose dominant members are P1 / P3, plus
    whatever dim_entities.sam_* values the case under test wants."""
    db = tmp_path / "sam.duckdb"
    con = duckdb.connect(str(db))
    con.execute(
        """
        create table entity_xwalk as select * from (values
          ('U1','BOEING DEFENSE','P1','THE BOEING COMPANY','BOEING','parent_name','high',100.0),
          ('U2','BOEING AERO','P2','BOEING COMPANY, THE (INC)','BOEING','parent_name','high',50.0),
          ('U3','HII MISSION','P3','HUNTINGTON INGALLS INDUSTRIES, INC','HII','parent_name','high',75.0)
        ) t(recipient_uei, recipient_name, parent_uei, parent_name, family_key, method, confidence, total_obligation)
        """
    )
    if sam_columns:
        con.execute(
            "create table dim_entities (family_key varchar, total_obligation double,"
            " sam_uei varchar, sam_legal_business_name varchar)"
        )
        con.execute(
            "insert into dim_entities values ('BOEING', 150.0, ?, ?), ('HII', 75.0, ?, ?)",
            [v for row in sam_rows for v in row],
        )
    else:
        # A warehouse built before ROADMAP #10's dbt source landed.
        con.execute(
            "create table dim_entities as select * from (values"
            " ('BOEING', 150.0), ('HII', 75.0)) t(family_key, total_obligation)"
        )
    con.close()
    return db


def test_sam_gate_passes_before_the_extract_has_run(tmp_path):
    g = sam_gate(make_sam_marts(tmp_path, [(None, None), (None, None)]))
    assert g["published"] == 2
    assert g["with_registration"] == 0
    assert g["ok"] is True, "an un-run extract is not a gate failure"
    # …but it may never pass SILENTLY: the note is what the CLI prints so a
    # green leg cannot be mistaken for a checked one.
    assert g["note"] is not None
    assert "sam extract" in g["note"]
    assert "vacuous" in g["note"]


def test_sam_gate_says_so_when_the_mart_predates_the_sam_columns(tmp_path):
    g = sam_gate(make_sam_marts(tmp_path, [], sam_columns=False))
    assert g["ok"] is True
    assert g["with_registration"] == 0
    assert "sam_* columns" in (g["note"] or "")
    assert "govbudget build" in (g["note"] or "")


def test_sam_gate_passes_when_the_registration_is_the_dominant_one(tmp_path):
    g = sam_gate(make_sam_marts(tmp_path, [("P1", "THE BOEING COMPANY"),
                                           ("P3", "HUNTINGTON INGALLS INDUSTRIES, INC")]))
    assert g["with_registration"] == 2
    assert g["mismatched_count"] == 0
    assert g["ok"] is True
    assert g["note"] is None, "a leg that actually checked something is not vacuous"


def test_sam_gate_fails_when_a_lake_refresh_moved_the_dominant_member(tmp_path):
    # P2 is Boeing's SECOND-largest registration: a stale extract.
    g = sam_gate(make_sam_marts(tmp_path, [("P2", "BOEING COMPANY, THE (INC)"),
                                           ("P3", "HUNTINGTON INGALLS INDUSTRIES, INC")]))
    assert g["mismatched_count"] == 1
    assert g["mismatched"] == ["BOEING"]
    assert g["ok"] is False


def test_sam_gate_fails_on_a_registration_with_no_legal_name(tmp_path):
    g = sam_gate(make_sam_marts(tmp_path, [("P1", None),
                                           ("P3", "HUNTINGTON INGALLS INDUSTRIES, INC")]))
    assert g["nameless_count"] == 1
    assert g["ok"] is False
