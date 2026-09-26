"""R-DEC-ENTITYTIE (controller ruling, 2026-09-26): dim_entities must read a
family's display_name from the SAME member on every build.

dim_entities takes display_name from the `rn = 1` member, and rn was
`row_number() over (partition by family_key order by total_obligation desc
nulls last)` with nothing after the obligation. Two members tied on
obligation came back in whatever order the window sort emitted them, so the
family's heading could change between rebuilds of an unchanged lake. Measured
2026-09-26 on the live lake: 47 families tie at the top, 22 of them across
different registrations and 13 with differently-named tied members — none in
the published 200, so no published label moves with this fix.

The order is now total: obligation desc (nulls last), then the registration
UEI — coalesce(parent_uei, recipient_uei), the same key dominant_registration
_uei ranks — ascending, then recipient_uei ascending. entity_xwalk is unique
and not-null on recipient_uei (schema.yml), so the last key cannot tie.

These tests run the committed model's own SQL against a throwaway DuckDB with
the tied rows inserted in every order, and require one answer.
"""
from itertools import permutations
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]

XWALK_COLS = (
    "recipient_uei varchar, recipient_name varchar, parent_uei varchar,"
    " parent_name varchar, family_key varchar, method varchar,"
    " confidence varchar, total_obligation double"
)

# The macro's own absent-extract branch (dbt/macros/sam_entities.sql): the
# LEFT JOIN matches nothing, so the test reads display_name alone.
_NO_SAM = (
    "(select null::varchar as sam_uei, null::varchar as legal_business_name,"
    " null::varchar as cage_code, null::varchar as registration_status,"
    " null::varchar as registration_expiration_date,"
    " null::varchar as business_types, null::varchar as primary_naics,"
    " null::varchar as public_url, null::varchar as source_url,"
    " null::varchar as retrieved_at, null::varchar as response_sha256"
    " where false)"
)


def _model_sql() -> str:
    """dbt/models/marts/dim_entities.sql with its ref()/macro replaced by plain
    relations — the SQL dbt builds, not a restatement of it."""
    sql = (ROOT / "dbt" / "models" / "marts" / "dim_entities.sql").read_text()
    for macro, rel in {
        "{{ ref('entity_xwalk') }}": "xwalk",
        "{{ sam_entities_relation() }}": _NO_SAM,
    }.items():
        assert macro in sql, f"{macro} no longer in dim_entities.sql"
        sql = sql.replace(macro, rel)
    assert "{{" not in sql, "unsubstituted macro left in dim_entities.sql"
    return sql


def _family(rows: list[tuple]) -> tuple:
    con = duckdb.connect(config={"threads": 4})
    try:
        con.execute(f"create table xwalk ({XWALK_COLS})")
        con.executemany("insert into xwalk values (?, ?, ?, ?, ?, ?, ?, ?)", rows)
        return con.execute(
            "select display_name, dominant_registration_uei, uei_count,"
            " total_obligation from (" + _model_sql() + ") where family_key = 'FAM'"
        ).fetchone()
    finally:
        con.close()


def _row(recipient_uei, recipient_name, parent_uei, parent_name, total):
    return (recipient_uei, recipient_name, parent_uei, parent_name, "FAM",
            "parent_name", "high", total)


CASES = {
    # Two tied members under different parents. The lower REGISTRATION UEI
    # (PA) wins — not the lower recipient_uei (R1) and not the alphabetically
    # first name (ALPHA), either of which would pick the other member.
    "tie across two parents": (
        [_row("R1", "SUB ONE", "PB", "ALPHA PARENT", 100.0),
         _row("R2", "SUB TWO", "PA", "ZULU PARENT", 100.0)],
        "ZULU PARENT",
    ),
    # No parent on either: the registration is the member's own UEI and the
    # name its own recipient_name.
    "tie, neither parented": (
        [_row("R9", "NINE CORP", None, None, 50.0),
         _row("R3", "THREE CORP", None, None, 50.0)],
        "THREE CORP",
    ),
    # A parented member against an unparented one: coalesce(parent_uei,
    # recipient_uei) is compared, so R5 (its own registration) sorts before
    # ZP, though the parented member's own recipient_uei (R1) is lower.
    "tie, parented vs unparented": (
        [_row("R1", "ONE SUB", "ZP", "Z PARENT", 70.0),
         _row("R5", "FIVE CORP", None, None, 70.0)],
        "FIVE CORP",
    ),
    # One registration, two names (a member whose parent_name is missing falls
    # back to its own recipient_name): the registration ties too, and
    # recipient_uei closes it. No lake family has this shape today; the order
    # must be total anyway.
    "tie on one registration, names differ": (
        [_row("R8", "EIGHT SUB", "PP", "PP HOLDINGS", 30.0),
         _row("R4", "FOUR SUB", "PP", None, 30.0)],
        "FOUR SUB",
    ),
    # Three-way tie, and a smaller member with the lowest UEI of all: the
    # tiebreak only ever orders the TIED top members.
    "three-way tie over a smaller low-UEI member": (
        [_row("R7", "SEVEN", "PC", "CHARLIE PARENT", 10.0),
         _row("R6", "SIX", "PB", "BRAVO PARENT", 10.0),
         _row("R5", "FIVE", "PD", "DELTA PARENT", 10.0),
         _row("R1", "ONE", "PA", "ALPHA PARENT", 9.0)],
        "BRAVO PARENT",
    ),
    # Unchanged preferences: the largest member wins whatever its UEI…
    "largest member wins": (
        [_row("R1", "SMALL", "PA", "SMALL PARENT", 1.0),
         _row("R2", "LARGE", "PZ", "LARGE PARENT", 2.0)],
        "LARGE PARENT",
    ),
    # …and a member with no obligation never outranks one that has it.
    "null obligation sorts last": (
        [_row("R1", "NULLCO", "PA", "NULL PARENT", None),
         _row("R2", "REALCO", "PZ", "REAL PARENT", 5.0)],
        "REAL PARENT",
    ),
}


@pytest.mark.parametrize("case", sorted(CASES))
def test_display_name_is_the_same_whatever_order_the_rows_arrive_in(case):
    rows, expected = CASES[case]
    seen = set()
    for order in permutations(rows):
        for _ in range(3):
            seen.add(_family(list(order))[0])
    assert seen == {expected}, (case, seen)


def test_the_tiebreak_moves_only_the_label():
    """The ruling reorders rn and nothing else: the SAM join key keeps its own
    rule (the HIGHEST registration UEI among the tied top members, rk = 1),
    and the family's count and total are sums over every member."""
    rows, _ = CASES["tie across two parents"]
    for order in permutations(rows):
        assert _family(list(order)) == ("ZULU PARENT", "PB", 2, 200.0)
    rows, _ = CASES["three-way tie over a smaller low-UEI member"]
    for order in permutations(rows):
        assert _family(list(order)) == ("BRAVO PARENT", "PD", 4, 39.0)
