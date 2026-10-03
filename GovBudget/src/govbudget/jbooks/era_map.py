"""Era (PB2017–PB2023) P-1 lines → dated program decisions (families piece 1).

Spec: docs/superpowers/specs/2026-10-02-era-procurement-history-design.md
§4.3 (the seed), §4.6 (research outputs), §5 (classes, rulings, review,
successors).

An era P-1 key ('{account}-{org}-L{line}', jbooks/era_keys.py) is ONE display
line inside ONE edition's workbook; line numbers are not identities across
editions. Column I of the same workbook row prints the budget line code
("Line Item"), which the loader keeps as budget_lines.line_item_code
(migration 021). This module never re-keys pe_bli. It records which program,
if any, each era line's PRINTED code belongs to, as decisions the owner made:

  * classify_keys   — one class per era key, first matching rule wins, in
                      CLASS_ORDER (§5.1).
  * build_chains    — keys grouped by (code, account), split by organization
                      for the codes that span organizations within one
                      edition's account (ORG_SPLIT_CODES).
  * apply_class_rulings — the three owner-approved class rulings (§5.2);
                      every other chain goes to individual review (§5.3).
  * search_successors — book-stated continuations for era-only codes (§5.4).
  * propose / ratify / check — the file-level workflow behind the
                      `govbudget era-map` CLI.

Drift guard: every decision row carries keys_sha256 over the sorted lines
'{edition}|{era_key}|{budget_activity}|{filed_title}' (blank for a missing
value), joined with '\\n', no trailing newline, sha256 hex of the UTF-8
bytes. DuckDB mirror for dbt: sha256(string_agg(line, chr(10) order by line)).
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from govbudget.jbooks.collision_keys import require_resolved
from govbudget.jbooks.era_keys import is_era_procurement_key
from govbudget.jbooks.p1_loader import EraKeyConflict

# ---------------------------------------------------------------------------
# Vocabulary (binding: the seed, the dbt map and verify-era-map read these)
# ---------------------------------------------------------------------------

CLASS_ORDER = ("CR", "UNSAFE", "R3", "A1", "A2", "R1", "R2", "H")
ORG_SPLIT_CODES = frozenset({"10", "15", "20", "30", "500"})
RULING_SAME = "R-DEC-ERA-SAME"
RULING_EXCLUDE = "R-DEC-ERA-EXCLUDE"
RULING_HISTORY = "R-DEC-ERA-HISTORY"
CLASS_RULINGS = (RULING_SAME, RULING_EXCLUDE, RULING_HISTORY)
DECISIONS = (
    "same_program", "history_only", "exclude_placeholder",
    "exclude_route_unsafe", "exclude_reused_code",
)
SEED_COLUMNS = (
    "decision_id", "line_item_code", "account", "organization",
    "first_edition", "last_edition", "decision", "program_account",
    "program_org", "successor_code", "successor_account", "successor_evidence",
    "n_keys", "keys_sha256", "titles_seen", "modern_title", "proposed_rule",
    "evidence", "decided_on", "decided_by", "ruling", "note",
)
REVIEW_COLUMNS = (
    "chain_id", "first_edition", "last_edition", "titles_by_edition",
    "modern_title", "accounts", "continuity", "actuals_k",
    "proposed_decision", "reason", "program_account", "program_org",
    "successor_code", "keys_sha256", "decision", "note",
)
CHAIN_COLUMNS = (
    "chain_id", "line_item_code", "account", "organization", "first_edition",
    "last_edition", "classes", "n_keys", "keys_sha256", "actuals_k",
    "titles_by_edition", "modern_title", "title_jaccard", "continuity",
    "ruling", "decision", "left_ruling_reason", "successor_code",
    "successor_account", "successor_evidence",
)
KEY_COLUMNS = (
    "edition", "era_key", "account", "organization", "budget_activity",
    "line_number", "line_item_code", "filed_title", "chain_id", "class",
    "title_jaccard", "continuity", "actuals_k", "enacted_k",
    "source_document_sha256", "source_rows", "source_cells",
)

ERA_EDITIONS = tuple(range(2017, 2024))
MODERN_EDITIONS = (2024, 2025, 2026)
CR_CODES = frozenset({"FY2017CR", "FY2018CR"})
# Era workbooks spell the service organizations out; PB2024+ abbreviates them.
# The Defense-Wide agency codes are printed identically in both eras.
ERA_ORG_TO_MODERN = {"ARMY": "A", "NAVY": "N", "AF": "F"}
JACCARD_MIN = 0.5
# Both sides of a continuity check below $1M (amounts are $K) carry no signal.
CONTINUITY_FLOOR_K = Decimal(1000)
# The approval date of the three class rulings (spec status line, 2026-10-02).
CLASS_RULINGS_DECIDED_ON = date(2026, 10, 2)
BATCH_RE = re.compile(r"^B[1-9][0-9]*$")
CHAIN_TITLE_SEP = " | "

_TITLE_MARKERS = re.compile(r"\((?:myp|mip|space|multiyear|ap|ap-cy)\)")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
# export_site.is_route_safe_pe's character set (a page slug must survive a URL).
_ROUTE_UNSAFE_CHARS = frozenset("&#/?%")


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EraKey:
    """One era P-1 key in one edition: the lake's (edition, era_key) grain."""

    edition: int
    account: str
    organization: str
    budget_activity: str | None
    era_key: str
    line_item_code: str
    filed_title: str | None
    actuals_k: Decimal | None          # fct_decade_series FY(N-2) actuals
    source_document_sha256: str
    source_cells: tuple[str, ...]
    enacted_k: Decimal | None = None   # fct_decade_series FY(N-1) enacted


@dataclass(frozen=True)
class ModernLine:
    """One PB2024–26 P-1 line identity: (edition, code, account, org, title).

    actuals_k / enacted_k are the decade-series grain of the code's page
    identity in that edition (the code alone, or code+account / code+org for
    the PB2026 collision codes) — the same values a modern page shows."""

    edition: int
    code: str
    account: str
    organization: str
    title: str | None
    actuals_k: Decimal | None = None
    enacted_k: Decimal | None = None


@dataclass(frozen=True)
class Chain:
    chain_id: str                      # '{code}|{account}|{org}' (org '' unless org-split)
    line_item_code: str
    account: str
    organization: str
    keys: tuple[tuple[int, str], ...]  # (edition, era_key), sorted
    classes: frozenset[str]
    titles_by_edition: dict[int, str]  # edition -> its filed titles, ' | '-joined
    actuals_k: Decimal
    n_keys: int
    keys_sha256: str

    @property
    def first_edition(self) -> int:
        return self.keys[0][0]

    @property
    def last_edition(self) -> int:
        return self.keys[-1][0]


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def normalize_title(title: str | None) -> str:
    """Casefold, drop the (MYP)/(MIP)/(SPACE)/(MULTIYEAR)/(AP)/(AP-CY)
    markers, collapse every run of punctuation/whitespace to one space."""
    t = (title or "").casefold()
    t = _TITLE_MARKERS.sub("", t)
    return " ".join(_NON_ALNUM.sub(" ", t).split())


def title_jaccard(a: str | None, b: str | None) -> float:
    """Token-set Jaccard of the two normalized titles; 0.0 if either is empty."""
    sa, sb = set(normalize_title(a).split()), set(normalize_title(b).split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def keys_sha256(lines: Iterable[tuple[int, str, str | None, str | None]]) -> str:
    """The drift guard over (edition, era_key, budget_activity, filed_title)."""
    rendered = sorted(
        f"{edition}|{era_key}|{ba or ''}|{title or ''}"
        for edition, era_key, ba, title in lines
    )
    return hashlib.sha256("\n".join(rendered).encode("utf-8")).hexdigest()


def is_route_safe_code(code: str) -> bool:
    return not (set(code) & _ROUTE_UNSAFE_CHARS or any(c.isspace() for c in code))


def org_split_codes(era: Iterable[EraKey]) -> frozenset[str]:
    """Codes printed by more than one organization inside one edition's account."""
    orgs: dict[tuple[int, str, str], set[str]] = defaultdict(set)
    for k in era:
        orgs[(k.edition, k.account, k.line_item_code)].add(k.organization)
    return frozenset(code for (_e, _a, code), o in orgs.items() if len(o) > 1)


def chain_id(code: str, account: str, organization: str) -> str:
    return f"{code}|{account}|{organization}"


def parse_chain_id(cid: str) -> tuple[str, str, str]:
    parts = cid.split("|")
    if len(parts) != 3 or not parts[0] or not parts[1]:
        raise ValueError(f"malformed chain_id {cid!r} (want 'code|account|org')")
    return parts[0], parts[1], parts[2]


def _chain_org(code: str, organization: str, split: frozenset[str]) -> str:
    return organization if code in split else ""


def _modern_org(organization: str) -> str:
    return ERA_ORG_TO_MODERN.get(organization, organization)


def _fmt_k(value: Decimal | None) -> str:
    if value is None:
        return ""
    if value == value.to_integral_value():
        return str(int(value))
    return format(value.normalize(), "f")


# ---------------------------------------------------------------------------
# Classification (§5.1)
# ---------------------------------------------------------------------------


@dataclass
class _ModernIdent:
    titles: set[str] = field(default_factory=set)
    norm_titles: set[str] = field(default_factory=set)
    editions: set[int] = field(default_factory=set)
    amounts: dict[tuple[int, str], Decimal] = field(default_factory=dict)
    latest_title: tuple[int, str] | None = None


class _Context:
    """Everything classification and review context derive from (era, modern)."""

    def __init__(self, era: Sequence[EraKey], modern: Sequence[ModernLine]):
        self.era = list(era)
        self.split = org_split_codes(self.era)
        self.idx: dict[tuple[str, str, str], _ModernIdent] = {}
        self.modern_codes: set[str] = set()
        self.modern_accounts: dict[str, set[str]] = defaultdict(set)
        self.line_idents: set[tuple[str, str, str]] = set()
        for m in sorted(modern, key=lambda m: (m.edition, m.code, m.account,
                                               m.organization, m.title or "")):
            self.modern_codes.add(m.code)
            self.modern_accounts[m.code].add(m.account)
            self.line_idents.add((m.code, m.account, m.organization))
            ident = (m.code, m.account,
                     m.organization if m.code in self.split else "")
            mi = self.idx.setdefault(ident, _ModernIdent())
            mi.editions.add(m.edition)
            if m.title is not None:
                mi.titles.add(m.title)
                mi.norm_titles.add(normalize_title(m.title))
                if mi.latest_title is None or m.edition >= mi.latest_title[0]:
                    mi.latest_title = (m.edition, m.title)
            for kind, value in (("actuals", m.actuals_k), ("enacted", m.enacted_k)):
                if value is not None:
                    mi.amounts.setdefault((m.edition, kind), value)
        self.accounts_in_edition: dict[tuple[int, str], set[str]] = defaultdict(set)
        self.era_by_ident: dict[tuple[str, str, str], list[EraKey]] = defaultdict(list)
        for k in self.era:
            self.accounts_in_edition[(k.edition, k.line_item_code)].add(k.account)
            self.era_by_ident[self.ident(k)].append(k)
        self._continuity: dict[tuple[str, str, str], tuple[int, int]] = {}

    def ident(self, k: EraKey) -> tuple[str, str, str]:
        code = k.line_item_code
        return (code, k.account,
                _modern_org(k.organization) if code in self.split else "")

    def continuity(self, ident: tuple[str, str, str]) -> tuple[int, int]:
        """(passed, total) checks: edition y's FY(y-1) enacted vs edition y+1's
        FY(y-1) actuals, y = 2017..2025, on the ident's era sum + modern grain.
        A check passes when both are under $1M, or they share a sign and the
        smaller is at least half the larger (within 2x)."""
        if ident in self._continuity:
            return self._continuity[ident]
        series: dict[tuple[int, str], Decimal] = {}
        for k in self.era_by_ident.get(ident, ()):
            for kind, value in (("actuals", k.actuals_k), ("enacted", k.enacted_k)):
                if value is not None:
                    series[(k.edition, kind)] = series.get((k.edition, kind), Decimal(0)) + value
        mi = self.idx.get(ident)
        if mi is not None:
            series.update(mi.amounts)
        passed = total = 0
        for y in range(ERA_EDITIONS[0], MODERN_EDITIONS[-1]):
            enacted, actuals = series.get((y, "enacted")), series.get((y + 1, "actuals"))
            if enacted is None or actuals is None:
                continue
            total += 1
            hi = max(abs(enacted), abs(actuals))
            if hi < CONTINUITY_FLOOR_K:
                passed += 1
            elif min(abs(enacted), abs(actuals)) * 2 >= hi and (enacted >= 0) == (actuals >= 0):
                passed += 1
        self._continuity[ident] = (passed, total)
        return passed, total

    def best_jaccard(self, k: EraKey) -> float | None:
        mi = self.idx.get(self.ident(k))
        if mi is None:
            return None
        return max((title_jaccard(k.filed_title, t) for t in mi.titles), default=0.0)

    def classify(self, k: EraKey, collision_codes: frozenset[str]) -> str:
        code = k.line_item_code
        if code in CR_CODES:
            return "CR"
        if not is_route_safe_code(code):
            return "UNSAFE"
        mi = self.idx.get(self.ident(k))
        if mi is not None:
            if (len(self.accounts_in_edition[(k.edition, code)]) > 1
                    and code not in collision_codes):
                return "R3"
            if normalize_title(k.filed_title) in mi.norm_titles:
                return "A1"
            passed, total = self.continuity(self.ident(k))
            if (self.best_jaccard(k) or 0.0) >= JACCARD_MIN and (
                    total == 0 or passed * 3 >= total * 2):
                return "A2"
            return "R1"
        if code in self.modern_codes:
            return "R2"
        return "H"


def classify_keys(
    era: Sequence[EraKey], modern: Sequence[ModernLine], *,
    collision_codes: frozenset[str],
) -> dict[tuple[int, str], str]:
    """{(edition, era_key): class} under CLASS_ORDER (§5.1; first match wins):

    CR      code is a FY2017CR/FY2018CR continuing-resolution placeholder;
    UNSAFE  code is not route-safe ('O&M', 'RDT&E' in 0390D);
    R3      (code, account[, org]) exists in PB2024–26, the code spans accounts
            inside this era edition, and it is not a PB2026 collision code;
    A1      (code, account[, org]) exists in PB2024–26 and the normalized
            title equals one of its normalized modern titles;
    A2      it exists, best title Jaccard ≥ 0.5, and at least 2/3 of the
            continuity checks pass (no checks counts as passing);
    R1      it exists (title drift beyond A2);
    R2      the code exists in PB2024–26 only under another account/org;
    H       the code is absent from PB2024–26.

    [, org] applies to org-split codes only (organization compared after
    ERA_ORG_TO_MODERN)."""
    ctx = _Context(era, modern)
    return {(k.edition, k.era_key): ctx.classify(k, collision_codes) for k in ctx.era}


# ---------------------------------------------------------------------------
# Chains (§5.2)
# ---------------------------------------------------------------------------


def group_keys(era: Sequence[EraKey]) -> dict[str, list[EraKey]]:
    """{chain_id: [EraKey, ...] sorted by (edition, era_key)}."""
    split = org_split_codes(era)
    groups: dict[str, list[EraKey]] = defaultdict(list)
    for k in era:
        groups[chain_id(k.line_item_code, k.account,
                        _chain_org(k.line_item_code, k.organization, split))].append(k)
    for keys in groups.values():
        keys.sort(key=lambda k: (k.edition, k.era_key))
    return dict(groups)


def range_sha(keys: Sequence[EraKey], first: int, last: int) -> tuple[int, str]:
    """(n_keys, keys_sha256) of the keys whose edition is in [first, last]."""
    inside = [k for k in keys if first <= k.edition <= last]
    return len(inside), keys_sha256(
        (k.edition, k.era_key, k.budget_activity, k.filed_title) for k in inside
    )


def build_chains(
    era: Sequence[EraKey], classes: Mapping[tuple[int, str], str],
) -> list[Chain]:
    """One Chain per (code, account[, org]); sorted by chain_id. Raises
    KeyError if a key has no class."""
    chains = []
    for cid, keys in group_keys(era).items():
        code, account, org = parse_chain_id(cid)
        titles: dict[int, set[str]] = defaultdict(set)
        for k in keys:
            titles[k.edition].add(k.filed_title or "")
        n_keys, sha = range_sha(keys, keys[0].edition, keys[-1].edition)
        chains.append(Chain(
            chain_id=cid, line_item_code=code, account=account, organization=org,
            keys=tuple((k.edition, k.era_key) for k in keys),
            classes=frozenset(classes[(k.edition, k.era_key)] for k in keys),
            titles_by_edition={e: CHAIN_TITLE_SEP.join(sorted(t))
                               for e, t in sorted(titles.items())},
            actuals_k=sum((k.actuals_k or Decimal(0) for k in keys), Decimal(0)),
            n_keys=n_keys, keys_sha256=sha,
        ))
    return sorted(chains, key=lambda c: c.chain_id)


def title_drift_free(chain: Chain) -> bool:
    """True when every filed title of the chain normalizes to one string."""
    return len({
        normalize_title(t)
        for v in chain.titles_by_edition.values()
        for t in v.split(CHAIN_TITLE_SEP)
    }) == 1


def collision_page(
    chain: Chain, modern_pages: frozenset[tuple[str, str, str]],
) -> tuple[str, str] | None:
    """The ONE PB2026 page (account, org) a collision-code chain joins: same
    code and account, and — for an org-split chain — the same organization.
    None when no page (or more than one) matches."""
    org = _modern_org(chain.organization)
    hits = sorted(
        (a, o) for (c, a, o) in modern_pages
        if c == chain.line_item_code and a == chain.account
        and (not chain.organization or o == org)
    )
    return hits[0] if len(hits) == 1 else None


def class_ruling(
    chain: Chain, *, modern_pages: frozenset[tuple[str, str, str]],
    collision_codes: frozenset[str],
) -> tuple[str, str, str, str] | None:
    """(ruling, decision, program_account, program_org), or None when the
    chain needs an individual decision. R-DEC-ERA-EXCLUDE takes precedence."""
    if "CR" in chain.classes:
        return (RULING_EXCLUDE, "exclude_placeholder", "", "")
    if "UNSAFE" in chain.classes:
        return (RULING_EXCLUDE, "exclude_route_unsafe", "", "")
    if chain.classes == frozenset({"A1"}):
        if chain.line_item_code in collision_codes:
            page = collision_page(chain, modern_pages)
            if page is None:
                return None
            return (RULING_SAME, "same_program", page[0], page[1])
        return (RULING_SAME, "same_program", "", "")
    if chain.classes == frozenset({"H"}) and title_drift_free(chain):
        return (RULING_HISTORY, "history_only", "", "")
    return None


def _proposed_rule(classes: Iterable[str]) -> str:
    present = set(classes)
    return "+".join(c for c in CLASS_ORDER if c in present)


def _titles_seen(chain: Chain, first: int, last: int) -> str:
    return "; ".join(f"{e}: {t}" for e, t in sorted(chain.titles_by_edition.items())
                     if first <= e <= last)


def seed_row(
    chain: Chain, *, first: int, last: int, n_keys: int, keys_sha: str,
    decision: str, ruling: str, decided_on: date, program_account: str = "",
    program_org: str = "", successor: Mapping[str, str] | None = None,
    modern_title: str = "", evidence: str = "", note: str = "",
) -> dict[str, str]:
    successor = successor or {}
    return {
        "decision_id": f"{chain.chain_id}|{first}-{last}",
        "line_item_code": chain.line_item_code,
        "account": chain.account,
        "organization": chain.organization,
        "first_edition": str(first),
        "last_edition": str(last),
        "decision": decision,
        "program_account": program_account,
        "program_org": program_org,
        "successor_code": successor.get("successor_code", ""),
        "successor_account": successor.get("successor_account", ""),
        "successor_evidence": successor.get("successor_evidence", ""),
        "n_keys": str(n_keys),
        "keys_sha256": keys_sha,
        "titles_seen": _titles_seen(chain, first, last),
        "modern_title": modern_title,
        "proposed_rule": _proposed_rule(chain.classes),
        "evidence": evidence or f"actuals_k={_fmt_k(chain.actuals_k)}",
        "decided_on": decided_on.isoformat(),
        "decided_by": "owner",
        "ruling": ruling,
        "note": note,
    }


def apply_class_rulings(
    chains: Sequence[Chain], *, modern_pages: frozenset[tuple[str, str, str]],
    collision_codes: frozenset[str], decided_on: date,
) -> tuple[list[dict], list[Chain]]:
    """(seed rows for the class-ruled chains, chains left for review)."""
    rows, left = [], []
    for ch in chains:
        rule = class_ruling(ch, modern_pages=modern_pages,
                            collision_codes=collision_codes)
        if rule is None:
            left.append(ch)
            continue
        ruling, decision, pa, po = rule
        rows.append(seed_row(
            ch, first=ch.first_edition, last=ch.last_edition, n_keys=ch.n_keys,
            keys_sha=ch.keys_sha256, decision=decision, ruling=ruling,
            decided_on=decided_on, program_account=pa, program_org=po,
        ))
    return rows, left
