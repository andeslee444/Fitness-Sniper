import duckdb
import pytest

from govbudget.entity_label_review import build_entity_label_review


def test_counts_parent_pair_margin_for_dominant_member_only():
    with duckdb.connect() as con:
        con.execute("create table dim_entities(family_key varchar, total_obligation double)")
        # parent_uei: the dominant pick's registration tiebreak (R-DEC-ENTITYTIE-b).
        con.execute("create table entity_xwalk(family_key varchar, recipient_uei varchar, parent_uei varchar, total_obligation double)")
        con.execute("create table fct_award_transactions(recipient_uei varchar, recipient_parent_uei varchar, recipient_parent_name varchar, obligation double)")
        con.execute("insert into dim_entities values ('A', 300), ('B', 190), ('C', 50)")
        con.execute("insert into entity_xwalk values ('A', 'a1', 'p1', 190), ('A', 'a2', 'p3', 110), ('B', 'b1', 'p4', 190), ('C', 'c1', 'p6', 50)")
        con.execute("""insert into fct_award_transactions values
            ('a1', 'p1', 'Parent', 100), ('a1', 'p2', 'Parent', 90),
            ('a2', 'p3', 'Unrelated candidate', 110),
            ('b1', 'p4', 'One', 100), ('b1', 'p5', 'Two', 85),
            ('c1', 'p6', 'Only registration', 50)
        """)
        # Same name under two parent UEIs is still a distinct registration.
        # The 15% boundary is strict; a single registration is not a near tie.
        assert build_entity_label_review(con) == {
            'near_ties': 1, 'families': 3, 'threshold_pct': 15,
        }
        con.execute("update fct_award_transactions set obligation=99 where recipient_parent_uei='p5'")
        assert build_entity_label_review(con)['near_ties'] == 2


def test_missing_fixture_omits_claim_but_real_warehouse_fails():
    with duckdb.connect() as con:
        assert build_entity_label_review(con) is None
        con.execute("create table dim_entities as select range::varchar as family_key, 1.0 as total_obligation from range(1000)")
        with pytest.raises(ValueError, match='registration schema'):
            build_entity_label_review(con)
