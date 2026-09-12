"""Phase 2 acceptance gates (phase-gates doc): entity resolution, golden
family merges, geography coverage. Runs against the DuckDB mart file."""
from pathlib import Path

import duckdb


def entity_gate(duckdb_path: Path, *, top_n: int = 1000) -> dict:
    con = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        resolved, total = con.execute(
            f"""
            with top as (
              select * from entity_xwalk
              order by total_obligation desc nulls last limit {int(top_n)}
            )
            select count(*) filter (where method in ('parent_name','parent_uei','recipient_name')
                                    and family_key is not null and family_key <> recipient_uei),
                   count(*)
            from top
            """
        ).fetchone()
    finally:
        con.close()
    return {
        "top_n": total,
        "resolved": resolved,
        "resolved_pct": round(100.0 * resolved / total, 1) if total else 0.0,
    }


def golden_gate(duckdb_path: Path) -> dict:
    con = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        boeing = con.execute(
            "select count(distinct recipient_uei), count(distinct family_key)"
            " from entity_xwalk where parent_name ilike '%boeing%'"
            " and parent_name not ilike '%bell boeing%'"
        ).fetchone()
        hii = con.execute(
            "select count(distinct family_key) from entity_xwalk"
            " where parent_name ilike 'huntington ingalls%'"
        ).fetchone()
    finally:
        con.close()
    return {
        "boeing_ueis": boeing[0],
        "boeing_one_family": boeing[1] == 1,
        "hii_one_family": hii[0] == 1,
    }


def geography_gate(duckdb_path: Path) -> dict:
    con = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        with_state, with_district = con.execute(
            """
            select count(*) filter (where pop_state is not null and pop_state <> ''),
                   count(*) filter (where pop_state is not null and pop_state <> ''
                                    and pop_district is not null and pop_district <> '')
            from fct_award_transactions
            """
        ).fetchone()
    finally:
        con.close()
    return {
        "with_state": with_state,
        "with_district": with_district,
        "resolved_pct": round(100.0 * with_district / with_state, 1) if with_state else 0.0,
    }


def sam_gate(duckdb_path: Path, *, top_n: int = 200) -> dict:
    """ROADMAP #10 leg e4: the SAM registration a company page publishes must
    be THIS family's dominant registration, and it must carry a legal name.

    What it catches, and it is the real failure mode: a SAM parquet built
    before a lake refresh moved a family's dominant member, so the page cites a
    registration that is no longer the one its own heading is built from. The
    re-derivation deliberately shares `dominant_parent_ueis()` with the extract
    — this is a STALENESS check, not an independent reimplementation of the
    pick rule.

    ZERO ROWS IS A PASS, BUT NEVER A SILENT ONE. An un-run extract is the
    normal state (the key is the owner's to mint, and the no-role quota is 10
    requests/day), so the gate returns ok=True — and always returns a `note`
    saying which of the two vacuous states it is in, which the CLI prints. A
    leg that can pass by checking nothing has to say so out loud, or the next
    reader takes its green for evidence.
    """
    from govbudget.sam_entities import dominant_parent_ueis

    expected = dict(dominant_parent_ueis(duckdb_path, top_n=top_n))
    con = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        try:
            rows = con.execute(
                "select family_key, sam_uei, sam_legal_business_name"
                " from dim_entities where sam_uei is not null and sam_uei <> ''"
            ).fetchall()
            has_columns = True
        except duckdb.Error:
            # A mart built before #10 (or a fixture DB) has no sam_* columns.
            rows, has_columns = [], False
    finally:
        con.close()

    mismatched = [fk for fk, uei, _ in rows if expected.get(fk) != uei]
    nameless = [fk for fk, _, name in rows if not name]
    note = None
    if not has_columns:
        note = (
            "dim_entities carries no sam_* columns — this warehouse predates"
            " ROADMAP #10's dbt source; re-run `govbudget build`. Nothing was"
            " checked."
        )
    elif not rows:
        note = (
            "no SAM.gov registration rows in dim_entities:"
            " `govbudget sam extract` has not run against this warehouse (it is"
            " blocked on an owner-minted SAM.gov Personal API key, and fetches"
            " 10 registrations/day without a SAM.gov role). This leg passes"
            " vacuously and checks nothing until the extract lands rows."
        )
    return {
        "published": len(expected),
        "with_registration": len(rows),
        "mismatched": mismatched[:5],
        "mismatched_count": len(mismatched),
        "nameless_count": len(nameless),
        "note": note,
        "ok": not mismatched and not nameless,
    }
