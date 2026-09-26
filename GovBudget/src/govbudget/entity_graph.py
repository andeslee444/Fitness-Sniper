"""Build the UEI -> canonical-family crosswalk parquet from the award lake.

Family preference: parent_name (name-first, not parent_uei-first) because
cross-parent-UEI merges need the NAME level — two parent UEIs whose names
normalize identically (e.g. Boeing's 'THE BOEING COMPANY' vs 'BOEING COMPANY,
THE (INC)') must resolve to the same canonical family key. family_key() in
entities.py remains the generic helper (prefers parent UEI); this module uses
name-first preference deliberately and records the distinction here.

Two properties this module exists to hold, both learned the hard way
(PM Sprint 3 Task 5b, 2026-08-05):

1. THE PARENT IS A PAIR, NOT TWO COLUMNS.  A recipient's parent changes over a
   decade — reorganisations, divestitures, sloppy registrations.  Aggregating
   recipient_parent_uei and recipient_parent_name with INDEPENDENT max() takes
   the uei from one transaction and the name from another and emits a pair that
   exists on no transaction anywhere.  Over FY2017-2026 that invented 6,342
   chimeric parents and moved $210B of Lockheed Martin into a family named
   'SIKORSKY SUPPORT SERVICES' and $88B of Electric Boat into one named 'WICO'.
   The pair is therefore chosen WHOLE, by the obligation dollars behind it.

2. THE AWARD UNIVERSE IS THE ONE THE SITE CITES.  award_glob covers contracts
   AND assistance because every consumer (fct_family_obligations_by_year,
   fct_agency_concentration) and every minted entity citation reads
   fct_award_transactions, which is their union.  A crosswalk built over a
   narrower universe makes dim_entities.total_obligation unreproducible from
   the query the page publishes beside it.

Both selections are fully ordered (dollars, then transaction count, then the
strings themselves) so the build is deterministic and reproducible.
"""
import csv
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb

from govbudget.entities import normalize_name

# ── Curated parent-pair exclusions (ROADMAP #135) ────────────────────────────
#
# The whole-pair pick below is the right rule for almost every recipient, and
# one curated exception is on file. SPARTON DELEON SPRINGS, LLC (UEI
# H7KFX5RH75K3) filed five parent registrations over FY2017-FY2026; the
# dollar-dominant one, parent UEI EGAVSJTA2D81 registered as ROCKWELL COLLINS
# AUSTRALIA PTY LIMITED ($207.3M across FY2024-FY2025, measured read-only
# 2026-09-25), put it in that family key — which the curated RTX family
# (data-seeds/entity_family_events.csv) merges on NAME-INFERRED evidence
# about Rockwell Collins Australia, evidence that says nothing about Sparton.
# Ruling #135 (owner-delegated to the controller, 2026-09-25): split Sparton
# out of that key; the name-inferred merge keeps only RC Australia's own
# members, and Sparton's family follows its OWN other registry filings.
#
# A row here removes exactly one (recipient UEI, parent UEI) pair from that
# recipient's parent pick. Nothing else moves: the recipient keeps every
# dollar (totals and the recipient-name pick read all its transactions), and
# the next pair by the same dollars-first order decides its family. The build
# prints what each row moved and the runner-up, so a near tie is visible in
# the chain log instead of being discovered on a page.
#
# Loud failures only. A row that matches no transaction, names a different
# recipient, or finds the parent UEI registered under another name raises:
# each of those would leave the defect in place without a word, or apply a
# review to a registration nobody reviewed.
DEFAULT_PARENT_EXCLUSIONS = (
    Path(__file__).resolve().parents[2] / "data-seeds" / "entity_parent_exclusions.csv"
)
PARENT_EXCLUSION_COLUMNS = (
    "recipient_uei",
    "recipient_name",
    "excluded_parent_uei",
    "excluded_parent_name",
    "decided",
    "roadmap",
    "note",
)
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ParentExclusionError(ValueError):
    """A curated parent-pair exclusion is malformed, stale, or mis-aimed."""


@dataclass(frozen=True)
class ParentExclusion:
    recipient_uei: str
    #: The recipient the row was written for, as the award data names it.
    recipient_name: str
    excluded_parent_uei: str
    #: The registration name the curator reviewed for that parent UEI.
    excluded_parent_name: str
    decided: str
    roadmap: str
    note: str


def load_parent_exclusions(csv_path: Path) -> list[ParentExclusion]:
    """Parse + validate the curated seed; raises ParentExclusionError on any defect."""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise ParentExclusionError(
            f"curated parent-exclusion seed missing: {csv_path} — ROADMAP #135's "
            f"split would silently revert"
        )
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        header = tuple(reader.fieldnames or ())
        if header != PARENT_EXCLUSION_COLUMNS:
            raise ParentExclusionError(
                f"{csv_path.name}: columns {header} != required {PARENT_EXCLUSION_COLUMNS}"
            )
        rows: list[ParentExclusion] = []
        seen: set[tuple[str, str]] = set()
        for i, raw in enumerate(reader, start=2):
            vals = {c: (raw.get(c) or "").strip() for c in PARENT_EXCLUSION_COLUMNS}
            for col, value in vals.items():
                if not value:
                    raise ParentExclusionError(f"{csv_path.name}:{i}: empty {col}")
            if not _ISO_DATE.match(vals["decided"]):
                raise ParentExclusionError(
                    f"{csv_path.name}:{i}: decided {vals['decided']!r} is not YYYY-MM-DD"
                )
            try:
                date.fromisoformat(vals["decided"])
            except ValueError as exc:
                raise ParentExclusionError(f"{csv_path.name}:{i}: decided: {exc}") from exc
            key = (vals["recipient_uei"], vals["excluded_parent_uei"])
            if key in seen:
                raise ParentExclusionError(
                    f"{csv_path.name}:{i}: pair {key} excluded twice"
                )
            seen.add(key)
            rows.append(ParentExclusion(**vals))
    return rows


def _check_exclusions(con, exclusions: Sequence[ParentExclusion]) -> None:
    """Every row must bite on the lake it is applied to (see the block comment)."""
    for ex in exclusions:
        names = {
            r[0]
            for r in con.execute(
                "select distinct recipient_name from tx where recipient_uei = ?",
                [ex.recipient_uei],
            ).fetchall()
            if r[0]
        }
        pair_names = con.execute(
            "select distinct parent_name from tx"
            " where recipient_uei = ? and parent_uei = ?",
            [ex.recipient_uei, ex.excluded_parent_uei],
        ).fetchall()
        if not pair_names:
            raise ParentExclusionError(
                f"{ex.roadmap}: no transaction of recipient {ex.recipient_uei} under "
                f"parent {ex.excluded_parent_uei} in this lake — the exclusion is "
                f"stale or mistyped and would change nothing"
            )
        want = normalize_name(ex.recipient_name)
        if want not in {normalize_name(n) for n in names}:
            raise ParentExclusionError(
                f"{ex.roadmap}: recipient {ex.recipient_uei} is filed as "
                f"{sorted(names)}, not {ex.recipient_name!r} — the row was written "
                f"for a different recipient"
            )
        reviewed = normalize_name(ex.excluded_parent_name)
        other = sorted(
            n for (n,) in pair_names if normalize_name(n or "") != reviewed
        )
        if other:
            raise ParentExclusionError(
                f"{ex.roadmap}: parent {ex.excluded_parent_uei} of {ex.recipient_uei} "
                f"now also carries the registration name(s) {other}, not only the "
                f"reviewed {ex.excluded_parent_name!r} — re-review before excluding"
            )


def _report_exclusions(con, exclusions: Sequence[ParentExclusion]) -> None:
    """One chain-log line per row: what it removed, where the recipient went,
    and the runner-up pair (a near tie is the thing to watch)."""
    for ex in exclusions:
        pairs = con.execute(
            "select parent_uei, parent_name, sum(obligation), count(*) from tx"
            " where recipient_uei = ? and (parent_uei is not null or parent_name is not null)"
            " group by 1, 2 order by 3 desc nulls last, 4 desc, 2 nulls last, 1 nulls last",
            [ex.recipient_uei],
        ).fetchall()
        dropped = [p for p in pairs if p[0] == ex.excluded_parent_uei]
        kept = [p for p in pairs if p[0] != ex.excluded_parent_uei]

        def fmt(p) -> str:
            return f"{p[0]} {p[1]} (${(p[2] or 0) / 1e6:,.1f}M, {p[3]} tx)"

        went = (
            f"family {normalize_name(kept[0][1]) or kept[0][0]} via {fmt(kept[0])}"
            if kept else "no other parent filing — recipient-name family"
        )
        runner = f"; runner-up {fmt(kept[1])}" if len(kept) > 1 else ""
        print(
            f"entity-graph: parent exclusion {ex.roadmap} {ex.recipient_uei} "
            f"{ex.recipient_name}: removed {', '.join(fmt(p) for p in dropped)}; "
            f"{went}{runner}"
        )

# Whole-pair parent selection + dollar-dominant recipient name.  Ranked by
# obligation dollars, then transaction count, then the strings — a total order,
# so two runs over the same lake produce byte-identical output.
_TX_SQL = """
create temp table tx as
    select recipient_uei,
           nullif(recipient_name, '')        as recipient_name,
           nullif(recipient_parent_uei, '')  as parent_uei,
           nullif(recipient_parent_name, '') as parent_name,
           try_cast(federal_action_obligation as double) as obligation
    from read_parquet({globs}, union_by_name=true)
    where recipient_uei is not null and recipient_uei <> ''
"""

_PICK_SQL = """
with totals as (
    select recipient_uei, sum(obligation) as total_obligation
    from tx group by recipient_uei
),
parent_pairs as (
    -- grouped on the PAIR: only combinations that really occur survive
    select recipient_uei, parent_uei, parent_name,
           sum(obligation) as dollars, count(*) as n
    from tx
    where (parent_uei is not null or parent_name is not null)
      -- ROADMAP #135: a curated (recipient, parent UEI) pair is never picked.
      and not exists (
          select 1 from _excl e
          where e.recipient_uei = tx.recipient_uei and e.parent_uei = tx.parent_uei
      )
    group by recipient_uei, parent_uei, parent_name
),
parent_pick as (
    select recipient_uei, parent_uei, parent_name from (
        select *, row_number() over (
            partition by recipient_uei
            order by dollars desc nulls last, n desc,
                     parent_name nulls last, parent_uei nulls last
        ) as rn
        from parent_pairs
    ) where rn = 1
),
name_counts as (
    select recipient_uei, recipient_name,
           sum(obligation) as dollars, count(*) as n
    from tx where recipient_name is not null
    group by recipient_uei, recipient_name
),
name_pick as (
    select recipient_uei, recipient_name from (
        select *, row_number() over (
            partition by recipient_uei
            order by dollars desc nulls last, n desc, recipient_name
        ) as rn
        from name_counts
    ) where rn = 1
)
select t.recipient_uei,
       n.recipient_name,
       p.parent_uei,
       p.parent_name,
       t.total_obligation
from totals t
left join name_pick   n on n.recipient_uei = t.recipient_uei
left join parent_pick p on p.recipient_uei = t.recipient_uei
order by t.recipient_uei
"""


def build_entity_xwalk(
    *,
    award_glob: str | Sequence[str],
    out_path: Path,
    parent_exclusions: Path | Sequence[ParentExclusion] = DEFAULT_PARENT_EXCLUSIONS,
) -> Path:
    """Write the UEI -> family crosswalk.

    ``parent_exclusions`` defaults to the curated seed (ROADMAP #135); a
    synthetic lake that does not contain the seed's recipients passes ``()``.
    """
    globs = [award_glob] if isinstance(award_glob, str) else list(award_glob)
    if not globs:
        raise ValueError("build_entity_xwalk: award_glob is empty")
    exclusions = (
        load_parent_exclusions(parent_exclusions)
        if isinstance(parent_exclusions, (str, Path))
        else list(parent_exclusions)
    )
    glob_literal = "[" + ", ".join("'" + g.replace("'", "''") + "'" for g in globs) + "]"
    con = duckdb.connect()
    try:
        con.execute(_TX_SQL.format(globs=glob_literal))
        con.execute("create temp table _excl (recipient_uei varchar, parent_uei varchar)")
        if exclusions:
            con.executemany(
                "insert into _excl values (?, ?)",
                [(e.recipient_uei, e.excluded_parent_uei) for e in exclusions],
            )
        _check_exclusions(con, exclusions)
        rows = con.execute(_PICK_SQL).fetchall()
        _report_exclusions(con, exclusions)
        # First pass: assign family + method; confidence starts as 'high' for
        # parent-derived methods, 'medium' for recipient/self methods.
        raw: list[tuple] = []
        for uei, rname, puei, pname, total in rows:
            if pname and normalize_name(pname):
                family, method = normalize_name(pname), "parent_name"
            elif puei:
                family, method = puei, "parent_uei"
            elif rname and normalize_name(rname):
                family, method = normalize_name(rname), "recipient_name"
            else:
                family, method = uei, "self_uei"
            confidence = "high" if method in ("parent_name", "parent_uei") else "medium"
            raw.append((uei, rname, puei, pname, family, method, confidence, total))

        # Second pass: families spanning >1 distinct parent_uei via name-merge
        # are cross-parent merges and must be downgraded to 'medium'.
        from collections import defaultdict
        family_parent_ueis: dict[str, set[str]] = defaultdict(set)
        for uei, rname, puei, pname, family, method, confidence, total in raw:
            if puei:
                family_parent_ueis[family].add(puei)
        cross_parent_families = {
            fam for fam, ueis in family_parent_ueis.items() if len(ueis) > 1
        }

        out: list[tuple] = []
        for uei, rname, puei, pname, family, method, confidence, total in raw:
            if family in cross_parent_families:
                confidence = "medium"
            out.append((uei, rname, puei, pname, family, method, confidence, total))
        con.execute(
            "create table _x (recipient_uei varchar, recipient_name varchar,"
            " parent_uei varchar, parent_name varchar, family_key varchar,"
            " method varchar, confidence varchar, total_obligation double)"
        )
        con.executemany("insert into _x values (?,?,?,?,?,?,?,?)", out)
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        con.execute(f"copy _x to '{out_path}' (format parquet, compression zstd)")
    finally:
        con.close()
    return out_path
