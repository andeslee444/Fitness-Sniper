"""Route-safe page keys for printed budget line codes a web address cannot
carry, and the P-1 lines that restate R-1 program elements (#194).

Families piece-1 follow-ups design §4.2–§4.3 (owner decisions 2026-10-04:
Q1 (a), Q2, Q8). A program page is a static route, so its key must survive a
URL path segment: no '&', '#', '/', '?', '%' or whitespace
(export_site.is_route_safe_pe applies the same rule to the page universe).
Two real PB2024–PB2026 P-1 lines of account 0390D (Chemical Agents and
Munitions Destruction, Defense) print exactly such codes:

  * 'O&M' ("Chem Demilitarization - O&M") loads under the owner-approved page
    key in dbt/seeds/p1_route_safe_codes.csv (0390DOM). budget_lines.pe_bli
    is the page key; budget_lines.line_item_code keeps the printed code.
  * 'RDT&E' ("Chem Demilitarization - RDT&E") equals R-1 program elements
    0708081D + 0708083D in every column of every edition, so loading it would
    count those dollars twice. P1_R1_RESTATEMENTS records it; the loader
    skips it only after checking it still equals that R-1 sum
    (p1_loader.verify_r1_restatements), and never gives it a page.

Any other route-unsafe code raises UnsafeBudgetLineCode: it is never skipped
silently again (the 2026-07-05 guard treated these two real lines as junk).

The seed is read here for Python (the loader, era_map, the exporter and the
receipt matcher) and by dbt as the seed table p1_route_safe_codes
(p1_era_line_map, assert_route_safe_codes_valid).
"""
from __future__ import annotations

import csv
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

SEED_COLUMNS = (
    "account", "line_item_code", "page_key", "exhibit_family",
    "decided_on", "decided_by", "note",
)
PAGE_KEY_RE = re.compile(r"[A-Z0-9]+")
# The exporter's route-safety character set (export_site.is_route_safe_pe).
ROUTE_UNSAFE_CHARS = frozenset("&#/?%")


class UnsafeBudgetLineCode(ValueError):
    """A workbook row prints a budget line code (or era line number) that a
    web address cannot carry, and neither the route-safe seed nor
    P1_R1_RESTATEMENTS names it. The loader refuses rather than skip a real
    line in silence."""


class P1RestatementMismatch(ValueError):
    """A P-1 line P1_R1_RESTATEMENTS names no longer equals the R-1 program
    elements it restates (or that R-1 is not loaded), so skipping it could
    drop real money. The loader refuses; re-measure the line before changing
    the rule."""


@dataclass(frozen=True)
class RouteSafeCode:
    """One owner-approved page key for a printed code under one account."""

    account: str
    line_item_code: str
    page_key: str
    exhibit_family: str
    decided_on: date
    decided_by: str
    note: str


@dataclass(frozen=True)
class R1Restatement:
    """A P-1 line that prints the same dollars as these R-1 program elements."""

    title: str
    program_elements: tuple[str, ...]


# (account, printed code) -> what the P-1 line restates. Measured 2026-10-04
# and re-measured 2026-10-13 (read-only, data/raw_docs/fy202{4,5,6}/dod/
# p1_display.xlsx rows 1138 / 1191 / 304 against the loaded R-1): every
# column of every PB2024–PB2026 edition matches to the thousand
# (PB2026: 1,002,560 / 754,762 / 210,039 / 210,039).
P1_R1_RESTATEMENTS: dict[tuple[str, str], R1Restatement] = {
    ("0390D", "RDT&E"): R1Restatement(
        title="Chem Demilitarization - RDT&E",
        program_elements=("0708081D", "0708083D"),
    ),
}

# A P-1 amount column whose R-1 twin is slugged differently. PB2025's P-1
# prints 'FY 2024 PB Request with CR Adjustments' where its R-1 prints
# 'FY 2024 PB Request with CR Amounts'.
R1_AMOUNT_TYPE_EQUIVALENTS: dict[str, str] = {
    "fy_2024_pb_request_with_cr_adjustments": "fy_2024_pb_request_with_cr_amounts",
}


def is_route_safe_code(code: str) -> bool:
    """True when a code can be a page key: no '&#/?%' and no whitespace."""
    return not (set(code) & ROUTE_UNSAFE_CHARS or any(c.isspace() for c in code))


def default_seed_path() -> Path:
    from govbudget import config

    return config.ROOT / "dbt" / "seeds" / "p1_route_safe_codes.csv"


def read_route_safe_codes(path: Path) -> dict[tuple[str, str], RouteSafeCode]:
    """{(account, printed code): RouteSafeCode} from a seed file, validated.

    Raises ValueError on a header other than SEED_COLUMNS, a page key that is
    not [A-Z0-9]+ or repeats, a printed code that is already route-safe, a
    repeated (account, code), a pair P1_R1_RESTATEMENTS also names, a blank
    exhibit_family, a decided_on that is not an ISO date, or decided_by other
    than 'owner'."""
    path = Path(path)
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != SEED_COLUMNS:
            raise ValueError(f"{path}: header {reader.fieldnames} != {list(SEED_COLUMNS)}")
        rows = list(reader)
    out: dict[tuple[str, str], RouteSafeCode] = {}
    keys: set[str] = set()
    for n, r in enumerate(rows, start=2):
        where = f"{path.name} line {n}"
        pair = (r["account"], r["line_item_code"])
        if not PAGE_KEY_RE.fullmatch(r["page_key"]):
            raise ValueError(f"{where}: page_key {r['page_key']!r} is not [A-Z0-9]+")
        if r["page_key"] in keys:
            raise ValueError(f"{where}: page_key {r['page_key']!r} repeats")
        if is_route_safe_code(r["line_item_code"]):
            raise ValueError(f"{where}: {r['line_item_code']!r} is already route-safe;"
                             " only a code a web address cannot carry gets a page key")
        if pair in out:
            raise ValueError(f"{where}: {pair} repeats")
        if pair in P1_R1_RESTATEMENTS:
            raise ValueError(f"{where}: {pair} is an R-1 restatement and gets no page")
        if not r["exhibit_family"].strip():
            raise ValueError(f"{where}: exhibit_family is blank")
        try:
            decided_on = date.fromisoformat(r["decided_on"])
        except ValueError as exc:
            raise ValueError(f"{where}: decided_on {r['decided_on']!r} is not an ISO date") from exc
        if r["decided_by"] != "owner":
            raise ValueError(f"{where}: decided_by {r['decided_by']!r} is not 'owner'")
        keys.add(r["page_key"])
        out[pair] = RouteSafeCode(
            account=r["account"], line_item_code=r["line_item_code"],
            page_key=r["page_key"], exhibit_family=r["exhibit_family"],
            decided_on=decided_on, decided_by=r["decided_by"], note=r["note"],
        )
    return out


@lru_cache(maxsize=1)
def load_route_safe_codes() -> dict[tuple[str, str], RouteSafeCode]:
    """The committed seed, read once per process."""
    return read_route_safe_codes(default_seed_path())


def page_key(account: str, code: str,
             codes: Mapping[tuple[str, str], RouteSafeCode] | None = None) -> str | None:
    """The page key the seed gives (account, printed code), or None."""
    hit = (load_route_safe_codes() if codes is None else codes).get((account, code))
    return hit.page_key if hit else None


def by_page_key(codes: Mapping[tuple[str, str], RouteSafeCode] | None = None,
                ) -> dict[str, RouteSafeCode]:
    """{page_key: RouteSafeCode}."""
    return {c.page_key: c for c in (load_route_safe_codes() if codes is None else codes).values()}


def restated_lines(account: str) -> list[dict]:
    """The P1_R1_RESTATEMENTS entries of one account, in code order, as the
    exporter publishes them on that account's alias page."""
    return [
        {"line_item_code": code, "title": rule.title,
         "program_elements": list(rule.program_elements)}
        for (acct, code), rule in sorted(P1_R1_RESTATEMENTS.items())
        if acct == account
    ]
