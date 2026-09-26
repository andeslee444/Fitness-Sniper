#!/usr/bin/env python3
"""familylabel-recompute.py — gate 24 leg (l) helper (ROADMAP #10, option A).

Answers, on stdout as JSON, the one question the gate cannot answer in Node:
**by how much did each published family's label win the argmax that chose it?**

`dim_entities.display_name` is `max(coalesce(parent_name, recipient_name))
filter (rn = 1)` — the registered parent name of the family member holding the
most money. That member picked its own `(parent_uei, parent_name)` pair by an
argmax over obligations (`entity_graph._PICK_SQL parent_pick`), and the argmax
has no notion of "close" and no notion of "current". Measured at the time this
leg was written (2026-09-01): 15 of the 200 published families ($255.2B, 9.7%
of published family dollars) carried a label that beat its runner-up by under
15%, and `ROCKWELL COLLINS AUSTRALIA` — then a family 97.3% RAYTHEON COMPANY —
won by 3.1% with a registration RTX reverted in FY2026. The live count is
gate 24 leg l's note.

MARGIN = (d1 - d2) / d1 over the DOMINANT MEMBER's distinct
`(recipient_parent_uei, recipient_parent_name)` pairs in the award lake, ranked
the way `parent_pick` ranks them. A family whose dominant member has exactly one
registration has margin 1.0 — nothing was decided by a coin flip.

Recomputed INDEPENDENTLY from the warehouse and the lake. It never reads
data-seeds/entity_display_aliases.csv, entities_top.json or the built HTML —
those are the artifacts under test, and reading one here would make the leg
tautological.

It DOES read data-seeds/entity_parent_exclusions.csv (RULING R-DEC-135b,
2026-09-26), because that seed is an INPUT to the pick it mirrors, not an
output under test: a (recipient UEI, parent UEI) pair listed there is never
the recipient's parent pick in entity_graph (ROADMAP #135), so it is neither
a winner nor a runner-up here either. Without it this helper ranked a
registration the build had refused and reported the label, and the margin, of
a pick nobody published. A missing or malformed seed is an error, exactly as
it is in entity_graph — never "no exclusions". The parse is repeated here
rather than imported, for the reason districtyear-recompute.py gives: the
helper must not depend on the govbudget package; tests/
test_label_margin_exclusions.py holds the two parses to the same pairs.

Output:
{
  "families": [
    {"family_key": "...", "display_name": "...", "total_obligation": 1.9e10,
     "margin": 0.031, "won": "ROCKWELL COLLINS AUSTRALIA PTY LIMITED",
     "won_dollars": 6.58e9, "runner_up": "RAYTHEON COMPANY",
     "runner_up_dollars": 6.38e9, "dominant_uei": "XSV6AZJ6SDJ7",
     "dominant_name": "RAYTHEON COMPANY"},
    ...
  ],
  "published": 200,
  "published_dollars": 2.63e12,
  "unmeasured": [{"family_key": "...", "reason": "no parent registration"}]
}

`unmeasured` names every published family the loop below skipped (Task 29
fix round 1): leg l fails unless `families` covers all `published`, and the
names make that failure say which family and why.
"""

import csv
import json
import sys
from pathlib import Path

import duckdb

REPO = Path(__file__).resolve().parents[3]
DUCKDB = REPO / "data" / "duckdb" / "govbudget.duckdb"
LAKE = [
    "data/parquet/contracts/fy=*/*.parquet",
    "data/parquet/assistance/fy=*/*.parquet",
]
#: entity_graph.DEFAULT_PARENT_EXCLUSIONS — the seed the build applies.
EXCLUSIONS_SEED = REPO / "data-seeds" / "entity_parent_exclusions.csv"
#: entity_graph.PARENT_EXCLUSION_COLUMNS, in order.
EXCLUSION_COLUMNS = (
    "recipient_uei",
    "recipient_name",
    "excluded_parent_uei",
    "excluded_parent_name",
    "decided",
    "roadmap",
    "note",
)

#: The published set — the same ordering and limit export_site.py uses.
PUBLISHED_LIMIT = 200


class SeedError(ValueError):
    """The parent-exclusion seed is missing or malformed."""


def load_exclusions(path: Path) -> list[tuple[str, str]]:
    """(recipient_uei, excluded_parent_uei) pairs, in seed order.

    Refuses what entity_graph.load_parent_exclusions refuses on shape: a
    missing file, other columns, an empty field. (The build also checks that
    each row bites on the lake; a row that did not could not change a pick,
    so it cannot change a margin either.)
    """
    path = Path(path)
    if not path.exists():
        raise SeedError(f"parent-exclusion seed missing: {path}")
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        header = tuple(reader.fieldnames or ())
        if header != EXCLUSION_COLUMNS:
            raise SeedError(
                f"{path.name}: columns {header} != required {EXCLUSION_COLUMNS}"
            )
        pairs: list[tuple[str, str]] = []
        for i, raw in enumerate(reader, start=2):
            vals = {c: (raw.get(c) or "").strip() for c in EXCLUSION_COLUMNS}
            for col, value in vals.items():
                if not value:
                    raise SeedError(f"{path.name}:{i}: empty {col}")
            pairs.append((vals["recipient_uei"], vals["excluded_parent_uei"]))
    return pairs


def main() -> int:
    if not DUCKDB.exists():
        print(json.dumps({"__error__": f"missing {DUCKDB}"}))
        return 1
    globs = [str(REPO / g) for g in LAKE]
    if not any(Path(g).parent.parent.is_dir() for g in globs):
        print(json.dumps({"__error__": "award lake parquet directories missing"}))
        return 1
    try:
        exclusions = load_exclusions(EXCLUSIONS_SEED)
    except SeedError as exc:
        print(json.dumps({"__error__": str(exc)}))
        return 1

    con = duckdb.connect(str(DUCKDB), read_only=True)
    print(json.dumps(recompute(con, globs, exclusions), sort_keys=True))
    return 0


def recompute(con, globs, exclusions) -> dict:
    """The margins, from `con` (dim_entities + entity_xwalk) and the award
    lake at `globs`, with every excluded (recipient, parent UEI) pair out of
    the ranking — as entity_graph's parent_pairs leaves it out."""
    excluded: dict[str, set[str]] = {}
    for recipient_uei, parent_uei in exclusions:
        excluded.setdefault(recipient_uei, set()).add(parent_uei)
    lake_literal = "[" + ",".join(f"'{g}'" for g in globs) + "]"
    # nullif('') mirrors _PICK_SQL exactly: an empty string is not a
    # registration, and treating it as one would invent a runner-up.
    con.execute(
        f"""
        create or replace temp view _tx as
        select recipient_uei,
               nullif(recipient_parent_uei, '')  as parent_uei,
               nullif(recipient_parent_name, '') as parent_name,
               try_cast(federal_action_obligation as double) as obligation
        from read_parquet({lake_literal}, union_by_name=true)
        where recipient_uei is not null and recipient_uei <> ''
        """
    )

    published = con.execute(
        "select family_key, display_name, total_obligation from dim_entities"
        f" order by total_obligation desc limit {PUBLISHED_LIMIT}"
    ).fetchall()

    # The family's dominant member — the rn=1 row dim_entities takes its
    # display_name from.
    dominant = {
        r[0]: (r[1], r[2])
        for r in con.execute(
            """
            select family_key, recipient_uei, recipient_name from (
              select *, row_number() over (
                  partition by family_key order by total_obligation desc nulls last
              ) rn from entity_xwalk
            ) where rn = 1
            """
        ).fetchall()
    }

    out = []
    unmeasured = []
    for family_key, display_name, total in published:
        uei, dom_name = dominant.get(family_key, (None, None))
        if uei is None:
            unmeasured.append({"family_key": family_key, "reason": "no dominant member"})
            continue
        regs = con.execute(
            """
            select parent_name, sum(obligation) d, count(*) n, parent_uei
            from _tx
            where recipient_uei = ?
              and (parent_uei is not null or parent_name is not null)
            group by parent_uei, parent_name
            order by d desc nulls last, n desc, parent_name nulls last,
                     parent_uei nulls last
            """,
            [uei],
        ).fetchall()
        # R-DEC-135b: the pair the build refused is not a candidate. Filtered
        # after the ORDER BY, so the survivors keep the build's ranking; a
        # NULL parent_uei is never excluded (entity_graph's NOT EXISTS
        # matches on equality, which NULL never satisfies).
        regs = [r for r in regs if r[3] is None or r[3] not in excluded.get(uei, ())]
        if not regs:
            unmeasured.append(
                {"family_key": family_key, "reason": "no parent registration"}
            )
            continue
        d1 = regs[0][1]
        d2 = regs[1][1] if len(regs) > 1 else 0.0
        if not d1:
            unmeasured.append(
                {"family_key": family_key, "reason": "top registration sums to zero"}
            )
            continue
        out.append(
            {
                "family_key": family_key,
                "display_name": display_name,
                "total_obligation": float(total or 0.0),
                "margin": float((d1 - d2) / d1),
                "won": regs[0][0],
                "won_dollars": float(d1),
                "runner_up": regs[1][0] if len(regs) > 1 else None,
                "runner_up_dollars": float(d2),
                "dominant_uei": uei,
                "dominant_name": dom_name,
            }
        )

    return {
        "families": out,
        "published": len(published),
        "published_dollars": float(sum(r[2] or 0.0 for r in published)),
        "unmeasured": unmeasured,
    }


if __name__ == "__main__":
    sys.exit(main())
