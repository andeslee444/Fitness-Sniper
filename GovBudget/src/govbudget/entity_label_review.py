"""Measure published company-label ambiguity from the current award mart."""

from collections.abc import Sequence
from pathlib import Path

from govbudget import entity_graph

NEAR_TIE_MARGIN = 0.15


def build_entity_label_review(
    con,
    parent_exclusions: Path | Sequence[entity_graph.ParentExclusion] | None = None,
) -> dict | None:
    """Count close parent-registration choices; never infer a review verdict.

    The site gate independently recomputes the same claim from raw Parquet.
    Tiny export fixtures without registration history omit the disclosure.
    A production warehouse missing those inputs fails instead of inventing zero.

    RULING R-DEC-135b (2026-09-26): the ranking leaves out every (recipient,
    parent UEI) pair in the curated exclusion seed, as entity_graph's parent
    pick does (ROADMAP #135) — otherwise this census would measure a pick the
    build refused. `parent_exclusions` defaults to the build's own seed
    (entity_graph.DEFAULT_PARENT_EXCLUSIONS, read when called); a missing or
    malformed seed raises, exactly as it does in entity_graph; `()` means
    none.
    """
    required = {
        "dim_entities": {"family_key", "total_obligation"},
        "entity_xwalk": {"family_key", "recipient_uei", "total_obligation"},
        "fct_award_transactions": {
            "recipient_uei", "recipient_parent_uei", "recipient_parent_name", "obligation",
        },
    }
    available = {
        name: {r[0] for r in con.execute(
            "select column_name from information_schema.columns where table_name=?", [name]
        ).fetchall()}
        for name in required
    }
    if any(not cols.issubset(available[name]) for name, cols in required.items()):
        if available["dim_entities"] and con.execute(
            "select count(*) from dim_entities"
        ).fetchone()[0] >= 1000:
            raise ValueError("Company-label review requires the complete award registration schema")
        return None

    if parent_exclusions is None:
        parent_exclusions = entity_graph.DEFAULT_PARENT_EXCLUSIONS
    exclusions = (
        entity_graph.load_parent_exclusions(parent_exclusions)
        if isinstance(parent_exclusions, (str, Path))
        else list(parent_exclusions)
    )
    rows = con.execute("""
        with excluded as (
            select unnest(?::varchar[]) as recipient_uei,
                   unnest(?::varchar[]) as parent_uei
        ), published as (
            select family_key from dim_entities
            order by total_obligation desc limit 200
        ), dominant as (
            select x.family_key, x.recipient_uei
            from entity_xwalk x join published p using (family_key)
            qualify row_number() over (
                partition by family_key order by total_obligation desc nulls last
            ) = 1
        ), registrations as (
            select d.family_key,
                   nullif(t.recipient_parent_uei, '') as parent_uei,
                   nullif(t.recipient_parent_name, '') as parent_name,
                   sum(t.obligation) as dollars, count(*) as n
            from fct_award_transactions t
            join dominant d using (recipient_uei)
            where (nullif(t.recipient_parent_uei, '') is not null
                   or nullif(t.recipient_parent_name, '') is not null)
              -- R-DEC-135b: a pair the build never picks is not a candidate
              -- (NOT EXISTS on equality, as entity_graph's parent_pairs).
              and not exists (
                  select 1 from excluded e
                  where e.recipient_uei = t.recipient_uei
                    and e.parent_uei = nullif(t.recipient_parent_uei, '')
              )
            group by 1, 2, 3
        ), ranked as (
            select *, row_number() over (
                partition by family_key
                order by dollars desc nulls last, n desc,
                         parent_name nulls last, parent_uei nulls last
            ) as rn from registrations
        )
        select family_key,
               max(dollars) filter (where rn=1) as winner,
               coalesce(max(dollars) filter (where rn=2), 0) as runner_up
        from ranked group by family_key
    """, [
        [e.recipient_uei for e in exclusions],
        [e.excluded_parent_uei for e in exclusions],
    ]).fetchall()
    measurable = [(winner, runner) for _, winner, runner in rows if winner]
    return {
        "near_ties": sum((winner - runner) / winner < NEAR_TIE_MARGIN
                         for winner, runner in measurable),
        "families": len(measurable),
        "threshold_pct": round(NEAR_TIE_MARGIN * 100),
    }
