"""The fiscal-year move rule for code that reads the RAW award archives.

ROADMAP #133; owner-delegated ruling 2026-09-25, extended by R-DEC-133b
(2026-09-26): "entity-graph (cli.py / entity_graph.py) and
flowdown-recompute.py read awards through the same retirement rule as dbt
staging (drop the retired copy of a fiscal-year move; ambiguous duplicates
fail), so a fresh sync rebuilds without the manual reconcile end to end."

A USAspending source correction can MOVE a transaction into another fiscal
year's archive: the refreshed archive then carries the key once in its new
year while an older archive still carries the pre-correction copy. dbt staging
settles that at build time (dbt/models/audit/audit_award_duplicate_copies.sql,
dbt/macros/award_fy_moves.sql); anything that sums data/parquet/contracts or
data/parquet/assistance itself must settle it the same way, or it counts a
moved transaction twice while the warehouse counts it once.

THE RULE (the dbt audit model's; its four reason strings verbatim). Per archive (contracts and
assistance are separate: a key present once in each is not a move and is left
to the warehouse's unique test), for every non-NULL transaction key present
more than once:

  * EXACTLY TWO copies, in two DIFFERENT fiscal-year archives, both with a
    parseable last_modified_date and the two dates DIFFERENT → the strictly
    newer copy is kept and the other is retired.
  * anything else is ambiguous: more than two copies / both copies sit in one
    fiscal year / a copy has no parseable last_modified_date / both copies
    carry the same last_modified_date. dbt retires nothing and fails the
    build; here AmbiguousAwardDuplicateError is raised before any reader is
    registered, so nothing downstream can sum a half-applied rule.

Dates are parsed by DuckDB (`try_cast(... as timestamptz)`) as the dbt model
parses them, with the same session defaults (neither sets TimeZone; every
last_modified_date in the lake carries an explicit UTC offset, measured
2026-09-26), so both implementations agree on what is a date and what is the
same instant. The classification itself is written again here in Python
rather than read from the warehouse: entity-graph runs BEFORE `dbt build` in
the chain, when the warehouse's move list still describes the previous lake,
and a site gate that recomputed through dbt's own table could not catch a
defect in it. tests/test_award_moves.py holds this implementation to the dbt
SQL on the same fixture shapes tests/test_dbt_award_fy_moves.py builds.

Self-contained on purpose (stdlib + duckdb only): the gate helpers that read
the award lake (site/scripts/gates/flowdown-, entitytotals- and
familylabel-recompute.py) load this file BY PATH, because a helper must not
depend on the govbudget package being importable from the cwd the gate spawns
it in.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

#: The transaction key each award archive is keyed on — the columns
#: stg_contracts / stg_assistance take `transaction_key` from.
ARCHIVE_KEYS = {
    "contract": "contract_transaction_unique_key",
    "assistance": "assistance_transaction_unique_key",
}

#: The ambiguity reasons, verbatim from audit_award_duplicate_copies.sql, in
#: the order the model tests them.
MORE_THAN_TWO = "more than two copies"
ONE_FISCAL_YEAR = "both copies sit in one fiscal year"
UNDATED = "a copy has no parseable last_modified_date"
SAME_DATE = "both copies carry the same last_modified_date"

#: Columns a keyed archive must carry for the rule to tell a move from a
#: duplicate: the hive partition `fy` and the source revision time.
_RULE_COLUMNS = ("fy", "last_modified_date")

#: How many ambiguous keys the error message spells out (the count is exact).
_SHOWN = 20


class AwardArchiveError(ValueError):
    """An award glob the rule cannot be applied to."""


class AmbiguousAwardDuplicateError(AwardArchiveError):
    """A duplicated transaction key the fiscal-year move rule refuses."""


@dataclass(frozen=True)
class DuplicateCopy:
    """One copy of a key present more than once in one archive — a row of
    audit_award_duplicate_copies."""

    award_type: str
    transaction_key: str
    fiscal_year: int
    last_modified_date: str | None
    source_file: str
    #: 'keep' | 'retire' | 'ambiguous'
    resolution: str
    ambiguity: str | None


@dataclass(frozen=True)
class RetiredCopy:
    """One proven move — a row of audit_award_fy_moves."""

    award_type: str
    transaction_key: str
    kept_fiscal_year: int
    kept_last_modified_date: str
    kept_file: str
    retired_fiscal_year: int
    retired_last_modified_date: str
    retired_file: str


@dataclass(frozen=True)
class AwardMoves:
    #: Every retired copy, ordered by (award_type, transaction_key).
    retired: tuple[RetiredCopy, ...]
    #: Globs with no transaction-key column (synthetic fixtures only; refused
    #: when the caller requires keys). Read whole: with no key there is no
    #: duplicate to find, exactly as dbt never counts a NULL key as one.
    unkeyed: tuple[str, ...] = ()

    def count(self, award_type: str) -> int:
        return sum(1 for r in self.retired if r.award_type == award_type)

    def summary(self) -> str:
        line = (
            "fiscal-year move rule (ROADMAP #133): retired "
            f"{self.count('contract')} contract and "
            f"{self.count('assistance')} assistance copies"
        )
        if self.unkeyed:
            line += (
                "; no transaction key column in "
                + ", ".join(self.unkeyed)
                + " (read whole — no copy there can be identified)"
            )
        return line


def _literal(globs: Sequence[str]) -> str:
    return "[" + ", ".join("'" + str(g).replace("'", "''") + "'" for g in globs) + "]"


def _read(globs: Sequence[str], *, filename: bool = False) -> str:
    """The read dbt/models/sources.yml uses for the award sources."""
    return (
        f"read_parquet({_literal(globs)}, hive_partitioning=true, union_by_name=true"
        + (", filename=true" if filename else "")
        + ")"
    )


def _archives(con, globs: Sequence[str], *, require_transaction_keys: bool):
    """{award_type: [glob, ...]} and the unkeyed globs, each glob classified by
    the transaction-key column it carries."""
    if isinstance(globs, str):
        globs = [globs]
    if not globs:
        raise AwardArchiveError("no award archive glob given")
    by_type: dict[str, list[str]] = defaultdict(list)
    unkeyed: list[str] = []
    for glob in globs:
        cols = {r[0] for r in con.execute(f"describe select * from {_read([glob])}").fetchall()}
        types = [t for t, key in ARCHIVE_KEYS.items() if key in cols]
        if len(types) > 1:
            raise AwardArchiveError(
                f"{glob} carries both {ARCHIVE_KEYS['contract']} and "
                f"{ARCHIVE_KEYS['assistance']}: the rule is decided per archive, "
                f"so pass the contracts and assistance globs separately"
            )
        if not types:
            if require_transaction_keys:
                raise AwardArchiveError(
                    f"{glob} has no transaction key column ({', '.join(ARCHIVE_KEYS.values())}): "
                    f"the fiscal-year move rule (ROADMAP #133) cannot tell a moved "
                    f"transaction from two transactions"
                )
            unkeyed.append(str(glob))
            continue
        missing = [c for c in _RULE_COLUMNS if c not in cols]
        if missing:
            raise AwardArchiveError(
                f"{glob} carries {ARCHIVE_KEYS[types[0]]} but no "
                f"{' / '.join(missing)} column: the fiscal-year move rule (ROADMAP "
                f"#133) needs the fiscal-year partition (fy=…) and last_modified_date"
            )
        by_type[types[0]].append(str(glob))
    return dict(by_type), unkeyed


def _classify(award_type: str, rows: list[tuple]) -> list[DuplicateCopy]:
    """rows: (key, fiscal_year, last_modified_date, modified_us, source_file)
    for every copy of every duplicated key of one archive."""
    groups: dict[str, list[tuple]] = defaultdict(list)
    for row in rows:
        groups[row[0]].append(row)
    out: list[DuplicateCopy] = []
    for key in sorted(groups):
        copies = groups[key]
        dated = [c[3] for c in copies if c[3] is not None]
        if len(copies) != 2:
            ambiguity = MORE_THAN_TWO
        elif len({c[1] for c in copies}) != 2:
            ambiguity = ONE_FISCAL_YEAR
        elif len(dated) != 2:
            ambiguity = UNDATED
        elif len(set(dated)) != 2:
            ambiguity = SAME_DATE
        else:
            ambiguity = None
        newest = max(dated) if ambiguity is None else None
        for k, fy, lmd, modified_us, source_file in copies:
            if ambiguity is not None:
                resolution = "ambiguous"
            else:
                resolution = "keep" if modified_us == newest else "retire"
            out.append(DuplicateCopy(award_type, k, fy, lmd, source_file, resolution, ambiguity))
    return out


def _duplicate_copies(con, by_type: dict[str, list[str]]) -> list[DuplicateCopy]:
    out: list[DuplicateCopy] = []
    for award_type in sorted(by_type):
        key = ARCHIVE_KEYS[award_type]
        # One aggregate over the key column first (~1.7 s over the 41.5M
        # contract keys, measured 2026-09-26); the copies' dates and files
        # are read only when a key repeats — never on a clean lake.
        dup_keys = [
            r[0]
            for r in con.execute(
                f"select {key} from {_read(by_type[award_type])}"
                f" where {key} is not null group by 1 having count(*) > 1"
            ).fetchall()
        ]
        if not dup_keys:
            continue
        rows = con.execute(
            f"""
            select {key} as transaction_key,
                   cast(fy as integer) as fiscal_year,
                   last_modified_date,
                   epoch_us(try_cast(last_modified_date as timestamptz)) as modified_us,
                   filename as source_file
            from {_read(by_type[award_type], filename=True)}
            where {key} in (select unnest(?::varchar[]))
            order by transaction_key, fiscal_year, source_file, last_modified_date
            """,
            [dup_keys],
        ).fetchall()
        out.extend(_classify(award_type, rows))
    return out


def duplicate_copies(
    con, globs: Sequence[str], *, require_transaction_keys: bool = False
) -> list[DuplicateCopy]:
    """Every copy of every key present more than once in one archive, with
    what the rule does with it — audit_award_duplicate_copies, in Python."""
    by_type, _unkeyed = _archives(con, globs, require_transaction_keys=require_transaction_keys)
    return _duplicate_copies(con, by_type)


def _ambiguity_message(ambiguous: list[DuplicateCopy]) -> str:
    keys: dict[tuple[str, str], list[DuplicateCopy]] = defaultdict(list)
    for c in ambiguous:
        keys[(c.award_type, c.transaction_key)].append(c)
    lines = []
    for (award_type, key), copies in list(keys.items())[:_SHOWN]:
        where = "; ".join(
            f"FY{c.fiscal_year} {c.last_modified_date!r} {c.source_file}" for c in copies
        )
        lines.append(f"  {award_type} {key}: {copies[0].ambiguity} [{where}]")
    more = len(keys) - _SHOWN
    if more > 0:
        lines.append(f"  … and {more} more")
    return (
        f"ROADMAP #133: {len(keys)} ambiguous duplicate transaction key(s) in the "
        f"award archives. The fiscal-year move rule retires a copy only when a key "
        f"has exactly two copies, in two different fiscal-year archives, with two "
        f"different parseable last_modified_dates. These keys do not "
        f"have that shape, so no copy was retired and no reader was registered "
        f"(dbt fails unique_fct_award_transactions_transaction_key on the same "
        f"lake):\n" + "\n".join(lines)
    )


def _moves(con, by_type: dict[str, list[str]], unkeyed: list[str]) -> AwardMoves:
    copies = _duplicate_copies(con, by_type)
    ambiguous = [c for c in copies if c.resolution == "ambiguous"]
    if ambiguous:
        raise AmbiguousAwardDuplicateError(_ambiguity_message(ambiguous))
    kept = {(c.award_type, c.transaction_key): c for c in copies if c.resolution == "keep"}
    retired = []
    for c in copies:
        if c.resolution != "retire":
            continue
        k = kept[(c.award_type, c.transaction_key)]
        retired.append(RetiredCopy(
            award_type=c.award_type,
            transaction_key=c.transaction_key,
            kept_fiscal_year=k.fiscal_year,
            kept_last_modified_date=k.last_modified_date,
            kept_file=k.source_file,
            retired_fiscal_year=c.fiscal_year,
            retired_last_modified_date=c.last_modified_date,
            retired_file=c.source_file,
        ))
    retired.sort(key=lambda r: (r.award_type, r.transaction_key))
    return AwardMoves(retired=tuple(retired), unkeyed=tuple(unkeyed))


def find_moves(
    con, globs: Sequence[str], *, require_transaction_keys: bool = False
) -> AwardMoves:
    """The proven moves in these archives; raises AmbiguousAwardDuplicateError
    on any other duplicate (every one is named)."""
    by_type, unkeyed = _archives(con, globs, require_transaction_keys=require_transaction_keys)
    return _moves(con, by_type, unkeyed)


def register_award_rows(
    con,
    globs: Sequence[str],
    *,
    view: str,
    require_transaction_keys: bool = False,
) -> AwardMoves:
    """Create TEMP VIEW `view` over these award archives with the retired copy
    of every proven move left out, and return the moves.

    Raises before creating anything when a duplicate is ambiguous. With
    nothing to retire (every lake the manual reconcile cleaned, and today's)
    the view is the plain union-by-name read of every glob — the same rows the
    callers read before this rule existed. Otherwise the retired copies are
    dropped exactly as dbt's award_fy_move_filter drops them: same key, same
    fiscal-year partition, same last_modified_date.
    """
    if isinstance(globs, str):
        globs = [globs]
    by_type, unkeyed = _archives(con, globs, require_transaction_keys=require_transaction_keys)
    moves = _moves(con, by_type, unkeyed)
    if not moves.retired:
        con.execute(f"create or replace temp view {view} as select * from {_read(list(globs))}")
        return moves

    retired_table = f"{view}__retired"
    con.execute(
        f"create or replace temp table {retired_table} (award_type varchar,"
        " transaction_key varchar, fiscal_year integer, last_modified_date varchar)"
    )
    con.executemany(
        f"insert into {retired_table} values (?, ?, ?, ?)",
        [
            (r.award_type, r.transaction_key, r.retired_fiscal_year, r.retired_last_modified_date)
            for r in moves.retired
        ],
    )
    parts = []
    for award_type in sorted(by_type):
        select = f"select * from {_read(by_type[award_type])} src"
        if moves.count(award_type):
            select += (
                f" where not exists (select 1 from {retired_table} m"
                f" where m.award_type = '{award_type}'"
                f" and m.transaction_key = src.{ARCHIVE_KEYS[award_type]}"
                f" and m.fiscal_year = cast(src.fy as integer)"
                f" and m.last_modified_date = src.last_modified_date)"
            )
        parts.append(select)
    if unkeyed:
        parts.append(f"select * from {_read(unkeyed)}")
    con.execute(
        f"create or replace temp view {view} as " + " union all by name ".join(parts)
    )
    return moves
