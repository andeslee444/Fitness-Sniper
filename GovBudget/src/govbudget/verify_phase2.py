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
    registration that is no longer this family's dominant registration
    (`max(coalesce(parent_uei, recipient_uei)) filter (rk = 1)`). NOT "the one
    its own heading is built from": `display_name` keeps rn = 1, so on an exact
    obligation tie the heading can name a different tied member — the identity
    the Group C polish withdrew from every surface that states this pick. This
    leg never reads display_name. The re-derivation deliberately shares
    `dominant_parent_ueis()` with the extract — this is a STALENESS check, not
    an independent reimplementation of the pick rule.

    SCOPE IS THE CURRENT TOP-N, AND ONLY THAT. The published set moves with
    every lake refresh, so a family fetched while it was rank 180 can be rank
    201 today: its registration is still correct, `--refresh` (which only
    touches the current top-N) could never "fix" it, and counting it would
    both fail the gate forever and push `with_registration` above `published`
    in the printed N/200. Those rows are reported as `out_of_scope_count` and
    grade nothing.

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

    in_scope = [r for r in rows if r[0] in expected]
    out_of_scope = len(rows) - len(in_scope)
    mismatched = [fk for fk, uei, _ in in_scope if expected[fk] != uei]
    nameless = [fk for fk, _, name in in_scope if not name]
    note = None
    if not has_columns:
        note = (
            "dim_entities carries no sam_* columns — this warehouse predates"
            " ROADMAP #10's dbt source; re-run `govbudget build`. Nothing was"
            " checked."
        )
    elif not in_scope:
        why = (
            f" all {out_of_scope} stored registration(s) belong to families"
            f" outside the current top {top_n}."
            if out_of_scope else
            " `govbudget sam extract` has not run against this warehouse (it is"
            " blocked on an owner-minted SAM.gov Personal API key, and fetches"
            " 10 registrations/day without a SAM.gov role)."
        )
        note = (
            "no SAM.gov registration rows in dim_entities for the published"
            f" top {top_n}:{why} This leg passes vacuously and checks nothing"
            " until the extract lands rows — and rows only become visible to"
            " dim_entities after the next `govbudget build`."
        )
    return {
        "published": len(expected),
        "with_registration": len(in_scope),
        "out_of_scope_count": out_of_scope,
        "mismatched": mismatched[:5],
        "mismatched_count": len(mismatched),
        "nameless_count": len(nameless),
        "note": note,
        "ok": not mismatched and not nameless,
    }
