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
    request_k: Decimal | None = None   # fct_decade_series FY(N) request (BudgetYearOne)


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
        FY(y-1) actuals, y = 2017..2023 (ERA_EDITIONS only — y anchors every
        check to an era edition, so a check always has an era-side amount on
        at least one of its two legs), on the ident's era sum + modern grain.
        A check with y = 2024 or 2025 would compare two PB2024-26 editions
        against each other with no era-side value at all; that is not
        evidence the era line continues into the modern program, so those
        checks are excluded from both passed and total (spec §5.3: a chain
        with zero checks here has NO continuity evidence, not vacuous proof).
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
        for y in range(ERA_EDITIONS[0], ERA_EDITIONS[-1] + 1):
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
                    total > 0 and passed * 3 >= total * 2):
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
    A2      it exists, best title Jaccard ≥ 0.5, and it has at least one
            era-anchored continuity check (y = 2017..2023) of which ≥2/3
            pass — zero checks is NOT evidence of continuity, so it does not
            qualify;
    R1      it exists (title drift beyond A2, or A2's jaccard/continuity bar
            not met at all);
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


# ---------------------------------------------------------------------------
# Stated successors (§5.4)
# ---------------------------------------------------------------------------

# Continuation wording only — a mention of both codes is not enough.
SUCCESSOR_RE = re.compile(
    r"continuation of|continues under|previously (?:funded|reflected) (?:under|in)",
    re.IGNORECASE,
)
# Code-shaped tokens: 5+ uppercase alphanumerics with at least one letter and
# one digit. Digits-only codes ('1045') are never matched: in prose they are
# indistinguishable from years, quantities and line numbers.
_CODE_TOKEN_RE = re.compile(r"\b(?=[A-Z0-9]*[A-Z])(?=[A-Z0-9]*[0-9])[A-Z0-9]{5,}\b")
_ACCOUNT_PREFIX_RE = re.compile(r"^[0-9]{4}(?=[A-Z])")
SUCCESSOR_EDITION_DIRS = ("fy2026", "fy2025", "fy2024")


def code_forms(code: str) -> list[tuple[str, str]]:
    """[(token, form)]: the literal code, then — for a code printed with a
    4-digit account prefix ('5600D15603') — the code without it ('D15603'),
    which is how the Army books print it."""
    forms = [(code, "literal")]
    short = _ACCOUNT_PREFIX_RE.sub("", code)
    if short != code and len(short) >= 5:
        forms.append((short, "short"))
    return forms


def is_successor_searchable(code: str) -> bool:
    """True when at least one of code_forms(code) is a token _CODE_TOKEN_RE
    could ever match in prose (a letter, a digit, 5+ chars) — i.e. the code
    is a candidate search_successors could in principle find. False for a
    digits-only code ('1045'): indistinguishable from years, quantities and
    line numbers, so search_successors never looks for it. Distinguishes a
    chain that was searched-but-not-found from one that was never a search
    target at all."""
    return any(_CODE_TOKEN_RE.fullmatch(tok) for tok, _form in code_forms(code))


def successor_xml_files(raw_docs_dir: Path) -> list[Path]:
    """PB2026, then PB2025, then PB2024 XML; inside an edition, a volume's own
    justification book before any master book ('_MJB_' bundles every volume),
    then by path."""
    out: list[Path] = []
    for edition_dir in SUCCESSOR_EDITION_DIRS:
        base = Path(raw_docs_dir) / edition_dir
        if not base.is_dir():
            continue
        out.extend(sorted(
            base.rglob("*.xml"),
            key=lambda p: ("_MJB_" in p.name, p.relative_to(base).as_posix()),
        ))
    return out


def _sentence_bounds(text: str, start: int, end: int) -> tuple[int, int]:
    """The sentence around text[start:end]: bounded by a newline, an XML tag
    edge, or a period followed by a space."""
    lows = [text.rfind("\n", 0, start), text.rfind(">", 0, start)]
    dot = text.rfind(". ", 0, start)
    if dot >= 0:
        lows.append(dot + 1)
    lo = max(lows) + 1
    highs = [p for p in (text.find("\n", end), text.find("<", end)) if p >= 0]
    dot = text.find(". ", end)
    if dot >= 0:
        highs.append(dot + 1)
    hi = min(highs) if highs else len(text)
    return lo, hi


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _pdf_page(pdf: Path, quote: str) -> int | None:
    """1-based page of the PDF whose text contains the quote (whitespace
    ignored), or None."""
    from pypdf import PdfReader

    needle = "".join(quote.split())
    for i, page in enumerate(PdfReader(str(pdf)).pages, start=1):
        if needle in "".join((page.extract_text() or "").split()):
            return i
    return None


def search_successors(
    chains: Sequence[Chain], *, raw_docs_dir: Path, modern: Sequence[ModernLine],
) -> dict[str, dict]:
    """{chain_id: successor} for era-only chains (classes == {'H'}) whose code
    a PB2024–26 J-book XML sentence states continues under one PB2024–26 P-1
    code. Each successor dict has successor_code, successor_account,
    successor_evidence, matched_form, xml, line, quote.

    A sentence qualifies only when it carries continuation wording
    (SUCCESSOR_RE), one of the era code's forms, and exactly one other
    PB2024–26 code (preferring the era chain's own account when the sentence
    names several). The first qualifying sentence in successor_xml_files
    order wins."""
    raw_docs_dir = Path(raw_docs_dir)
    targets = {c.chain_id: c for c in chains if c.classes == frozenset({"H"})}
    if not targets:
        return {}
    era_forms: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for cid, ch in targets.items():
        for token, form in code_forms(ch.line_item_code):
            era_forms[token].append((cid, form))
    modern_by_token: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for m in modern:
        for token, _form in code_forms(m.code):
            modern_by_token[token].add((m.code, m.account))
    found: dict[str, dict] = {}
    for xml in successor_xml_files(raw_docs_dir):
        if len(found) == len(targets):
            break
        text = xml.read_bytes().decode("utf-8", errors="replace")
        for hit in SUCCESSOR_RE.finditer(text):
            lo, hi = _sentence_bounds(text, hit.start(), hit.end())
            sentence = text[lo:hi]
            tokens = set(_CODE_TOKEN_RE.findall(sentence))
            for token in sorted(tokens):
                for cid, form in era_forms.get(token, ()):
                    if cid in found:
                        continue
                    ch = targets[cid]
                    own = {t for t, _f in code_forms(ch.line_item_code)}
                    cands: set[tuple[str, str]] = set()
                    for other in tokens - own:
                        cands |= modern_by_token.get(other, set())
                    same = {c for c in cands if c[1] == ch.account}
                    pick = same or cands
                    if len(pick) != 1:
                        continue
                    code, account = next(iter(pick))
                    rel = xml.relative_to(raw_docs_dir).as_posix()
                    line = text.count("\n", 0, hit.start()) + 1
                    quote = " ".join(sentence.split())
                    parts = [f"xml={rel}:{line}", f"xml_sha256={_sha256_file(xml)}"]
                    if xml.parent.name.endswith("__xml"):
                        pdf = xml.parent.parent / (xml.parent.name[: -len("__xml")] + ".pdf")
                        if pdf.is_file():
                            page = _pdf_page(pdf, quote)
                            parts += [f"pdf={pdf.relative_to(raw_docs_dir).as_posix()}",
                                      f"pdf_sha256={_sha256_file(pdf)}",
                                      f"pdf_page={page if page is not None else ''}"]
                    parts += [f"form={form}", f'quote="{quote}"']
                    found[cid] = {
                        "successor_code": code,
                        "successor_account": account,
                        "successor_evidence": "; ".join(parts),
                        "matched_form": form,
                        "xml": rel,
                        "line": line,
                        "quote": quote,
                    }
    return found


# ---------------------------------------------------------------------------
# Lake inputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LakeInputs:
    era: list[EraKey]
    modern: list[ModernLine]
    collision_codes: frozenset[str]
    modern_pages: frozenset[tuple[str, str, str]]


def jbooks_parquet(duckdb_path: Path, name: str) -> Path:
    """data/parquet/jbooks/<name> beside the DuckDB file — the layouts
    export_site._stage_parquet_path probes: {duckdb_dir}/parquet/jbooks/
    (test fixtures), then {duckdb_dir}/../parquet/jbooks/ (data/duckdb +
    data/parquet)."""
    base = Path(duckdb_path).parent
    for cand in (base / "parquet" / "jbooks" / name,
                 base.parent / "parquet" / "jbooks" / name):
        if cand.is_file():
            return cand
    raise FileNotFoundError(
        f"era-map: {name} not found beside {duckdb_path}"
        f" (looked in {base / 'parquet' / 'jbooks'} and"
        f" {base.parent / 'parquet' / 'jbooks'})"
    )


def _sql_path(p: Path) -> str:
    return str(p).replace("'", "''")


def _dec(v) -> Decimal | None:
    return None if v is None else Decimal(str(v))


def _cell_sort_key(cell: str) -> tuple[int, str]:
    m = re.match(r"^([A-Z]+)([0-9]+)$", cell)
    return (int(m.group(2)), m.group(1)) if m else (0, cell)


def _connect(duckdb_path: Path):
    import duckdb

    return duckdb.connect(str(duckdb_path), read_only=True)


def _read_budget_lines(con, duckdb_path: Path) -> list[tuple]:
    bl = jbooks_parquet(duckdb_path, "budget_lines.parquet")
    cols = {r[0] for r in con.execute(
        f"describe select * from read_parquet('{_sql_path(bl)}')").fetchall()}
    if "line_item_code" not in cols:
        raise RuntimeError(
            f"era-map: {bl} has no line_item_code column. The era map reads the"
            " printed budget line code from the lake: apply migration 021 and"
            " run the S1 reload (scripts/era/s1_reload_era_p1.py --apply) and"
            " `govbudget jbooks export-facts` first (plan Tasks 7-8)."
        )
    return con.execute(
        "select cast(fiscal_year as integer), account, organization,"
        " budget_activity, pe_bli, title, line_item_code, source_document_id,"
        " coalesce(source_cells, '')"
        f" from read_parquet('{_sql_path(bl)}')"
        " where exhibit = 'P-1' and cast(fiscal_year as integer) between 2017 and 2026"
    ).fetchall()


def load_era_keys(duckdb_path: Path, *, with_amounts: bool = True) -> list[EraKey]:
    """Every era P-1 key (PB2017–23, pe_bli an era procurement key) with its
    printed code, title, budget activity, workbook sha and cells; amounts
    from fct_decade_series when with_amounts. Raises EraKeyConflict if a key
    prints more than one code, title, budget activity or source document."""
    con = _connect(duckdb_path)
    try:
        rows = _read_budget_lines(con, duckdb_path)
        docs = dict(con.execute(
            "select id, sha256 from read_parquet("
            f"'{_sql_path(jbooks_parquet(duckdb_path, 'documents.parquet'))}')"
        ).fetchall())
        amounts: dict[tuple[str, int, str], Decimal] = {}
        if with_amounts:
            for pe, ed, kind, amt in con.execute(
                "select pe_bli, edition_year, amount_type_kind, amount"
                " from fct_decade_series where edition_year <= 2023"
                " and amount_type_kind in ('actuals', 'enacted', 'request')"
            ).fetchall():
                amounts[(pe, int(ed), kind)] = _dec(amt)
    finally:
        con.close()
    acc: dict[tuple[int, str], dict] = {}
    for ed, account, org, ba, pe, title, code, doc_id, cells in rows:
        if ed > 2023 or not is_era_procurement_key(pe):
            continue
        a = acc.setdefault((ed, pe), {"account": set(), "org": set(), "ba": set(),
                                       "title": set(), "code": set(), "doc": set(),
                                       "cells": set()})
        a["account"].add(account)
        a["org"].add(org)
        a["ba"].add(ba)
        a["title"].add(title)
        a["code"].add((code or "").strip())
        a["doc"].add(doc_id)
        a["cells"].update(c for c in cells.split(",") if c)
    era = []
    for (ed, pe), a in sorted(acc.items()):
        for what in ("account", "org", "ba", "title", "code", "doc"):
            if len(a[what]) != 1:
                raise EraKeyConflict(
                    f"era key {pe} (PB{ed}) has {len(a[what])} distinct {what}"
                    f" values: {sorted(map(str, a[what]))}")
        code = next(iter(a["code"]))
        if not code:
            raise RuntimeError(
                f"era-map: era key {pe} (PB{ed}) has a blank line_item_code —"
                " the S1 reload did not fill every era row (plan Task 8)")
        doc = next(iter(a["doc"]))
        if doc not in docs:
            raise RuntimeError(f"era-map: source document {doc} of {pe} (PB{ed})"
                               " is missing from documents.parquet")
        era.append(EraKey(
            edition=ed, account=next(iter(a["account"])),
            organization=next(iter(a["org"])), budget_activity=next(iter(a["ba"])),
            era_key=pe, line_item_code=code, filed_title=next(iter(a["title"])),
            actuals_k=amounts.get((pe, ed, "actuals")),
            source_document_sha256=docs[doc],
            source_cells=tuple(sorted(a["cells"], key=_cell_sort_key)),
            enacted_k=amounts.get((pe, ed, "enacted")),
            request_k=amounts.get((pe, ed, "request")),
        ))
    return era


def load_inputs(duckdb_path: Path) -> LakeInputs:
    """The era keys, the PB2024–26 P-1 lines, the PB2026 collision codes and
    the PB2026 page identities, all read-only."""
    era = load_era_keys(duckdb_path)
    con = _connect(duckdb_path)
    try:
        rows = _read_budget_lines(con, duckdb_path)
        grains = con.execute(
            "select pe_bli, account, organization, edition_year, amount_type_kind,"
            " amount from fct_decade_series where edition_year >= 2024"
            " and amount_type_kind in ('actuals', 'enacted')"
        ).fetchall()
        programs = con.execute(
            "select pe_bli, account, org from dim_programs").fetchall()
    finally:
        con.close()
    acct_split = {r[0] for r in grains if r[1] is not None}
    org_split = {r[0] for r in grains if r[2] is not None}
    amounts = {(pe, acct, org, int(ed), kind): _dec(amt)
               for pe, acct, org, ed, kind, amt in grains}
    modern: set[ModernLine] = set()
    for ed, account, org, _ba, pe, title, _code, _doc, _cells in rows:
        if ed < 2024 or pe == "9999999999" or not is_route_safe_code(pe):
            continue
        gk = (pe, account if pe in acct_split else None,
              org if pe in org_split else None, ed)
        modern.add(ModernLine(
            edition=ed, code=pe, account=account, organization=org, title=title,
            actuals_k=amounts.get(gk + ("actuals",)),
            enacted_k=amounts.get(gk + ("enacted",)),
        ))
    axes = require_resolved(programs, caller="era_map.load_inputs")
    return LakeInputs(
        era=era,
        modern=sorted(modern, key=lambda m: (m.edition, m.code, m.account,
                                             m.organization, m.title or "")),
        collision_codes=frozenset(axes),
        modern_pages=frozenset((pe, acct or "", org or "") for pe, acct, org in programs),
    )


# ---------------------------------------------------------------------------
# Seed / CSV I/O
# ---------------------------------------------------------------------------


def read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as fh:
        return [dict(r) for r in csv.DictReader(fh)]


def write_csv(path: Path, columns: Sequence[str], rows: Iterable[Mapping]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(columns), lineterminator="\n",
                           extrasaction="raise")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in columns})


def read_seed(seed_path: Path) -> list[dict[str, str]]:
    if not Path(seed_path).is_file():
        return []
    rows = read_csv(seed_path)
    if rows and tuple(rows[0].keys()) != SEED_COLUMNS:
        raise ValueError(f"{seed_path}: header {tuple(rows[0].keys())} != SEED_COLUMNS")
    return rows


def write_seed(seed_path: Path, rows: Iterable[Mapping]) -> None:
    write_csv(Path(seed_path), SEED_COLUMNS, sorted(rows, key=lambda r: r["decision_id"]))


def _ranges_overlap(a: Mapping, b: Mapping) -> bool:
    return (a["line_item_code"], a["account"], a["organization"]) == (
        b["line_item_code"], b["account"], b["organization"]) and not (
        int(a["last_edition"]) < int(b["first_edition"])
        or int(b["last_edition"]) < int(a["first_edition"]))


# ---------------------------------------------------------------------------
# propose (§4.6, §5.2, §5.4)
# ---------------------------------------------------------------------------


def _chain_group(ch: Chain) -> str:
    """The research-pass bucket a chain falls in (mutually exclusive)."""
    if "CR" in ch.classes:
        return "cr"
    if "UNSAFE" in ch.classes:
        return "unsafe"
    if ch.classes == frozenset({"A1"}):
        return "a1_only"
    if ch.classes == frozenset({"H"}):
        return "h_drift_free" if title_drift_free(ch) else "h_drifting"
    if ch.classes & {"R1", "R2", "R3"}:
        return "r_containing"
    if "A2" in ch.classes:
        return "a2_without_r"
    return "other"


def _chain_context(ch: Chain, keys: Sequence[EraKey], ctx: _Context) -> dict:
    ident = ctx.ident(keys[0])
    mi = ctx.idx.get(ident)
    # Fix round 2 (review finding): a chain whose class contains R2 or R3 is
    # an account/organization move — `ident` (the chain's OWN account[/org])
    # is exactly the identity that move left, so looking the title up there
    # finds nothing. Show every PB2024-26 destination for the code instead.
    # A non-move chain keeps today's single-title format.
    is_move = bool(ch.classes & {"R2", "R3"})
    destinations = _modern_destinations(ch.line_item_code, ctx) if is_move else []
    if is_move:
        modern_title = _format_destinations(destinations)
    elif mi is not None and mi.latest_title is not None:
        modern_title = mi.latest_title[1]
    else:
        modern_title = ""
    jac = [j for j in (ctx.best_jaccard(k) for k in keys) if j is not None]
    passed, total = ctx.continuity(ident)
    return {
        "modern_title": modern_title,
        "title_jaccard": f"{min(jac):.2f}" if jac else "",
        "continuity": f"{passed}/{total}",
        "continuity_total": total,
        "continuity_ok": total > 0 and passed * 3 >= total * 2,
        "modern_accounts": sorted(ctx.modern_accounts.get(ch.line_item_code, ())),
        "modern_destinations": destinations,
        # Fix round 3: a chain with no non-zero request in any edition is
        # typical of a Congress-added line (the President never asked for
        # it) — the year-to-year continuity check has no request-side
        # anchor for such a line, so a failing ratio is not evidence either
        # way, just an artifact of the amount being absent.
        "has_request": any((k.request_k or Decimal(0)) != 0 for k in keys),
    }


def _pick_page_by_title(ch: Chain, keys: Sequence[EraKey], ctx: _Context,
                        modern_pages: frozenset[tuple[str, str, str]]) -> tuple[str, str]:
    """For a collision-code chain left to review: the one page of its code
    whose modern title matches the chain's latest filed title, else blanks."""
    latest = normalize_title(keys[-1].filed_title)
    hits = set()
    for code, account, org in modern_pages:
        if code != ch.line_item_code:
            continue
        mi = ctx.idx.get((code, account, org if code in ctx.split else ""))
        if mi is not None and latest in mi.norm_titles:
            hits.add((account, org))
    return next(iter(hits)) if len(hits) == 1 else ("", "")


def _modern_destinations(code: str, ctx: _Context) -> list[tuple[str, str, str]]:
    """Every (account, organization, title) the code prints in PB2024-26, one
    row per distinct modern identity (organization blank unless code is an
    org-split code), sorted by (account, organization). Fix round 2 (review
    finding): a chain's own (code, account[, org]) identity is only ONE of
    these — an account/organization move (classes containing R2 or R3) needs
    to see every destination, not just the one, if any, that happens to
    share the chain's own account."""
    idents = sorted({(a, o if code in ctx.split else "")
                     for c, a, o in ctx.line_idents if c == code})
    out: list[tuple[str, str, str]] = []
    for account, org in idents:
        mi = ctx.idx.get((code, account, org))
        if mi is not None and mi.latest_title is not None:
            out.append((account, org, mi.latest_title[1]))
    return out


def _format_destinations(destinations: Sequence[tuple[str, str, str]]) -> str:
    """'<account>[/<org>]: <title>' per destination, joined by '; ' (Fix
    round 2 ruling 1) — shared by modern_title and the ambiguous-move reason
    so the two stay consistent."""
    return "; ".join(f"{a}{'/' + o if o else ''}: {t}" for a, o, t in destinations)


def _org_editions(
    era: Iterable[EraKey], split: frozenset[str],
) -> dict[str, dict[tuple[str, str], set[int]]]:
    """{code: {(account, era organization): editions holding keys}} for the
    org-split codes."""
    out: dict[str, dict[tuple[str, str], set[int]]] = {}
    for k in era:
        if k.line_item_code in split:
            out.setdefault(k.line_item_code, {}).setdefault(
                (k.account, k.organization), set()).add(k.edition)
    return out


def _org_clash(
    ch: Chain, ctx: _Context, collision_codes: frozenset[str],
    page: tuple[str, str],
    org_editions: Mapping[str, Mapping[tuple[str, str], set[int]]],
) -> tuple[str, dict[str, list[int]]] | None:
    """(page organization, {other era organization: [shared editions]}) when
    an org-split chain's code points at ANOTHER organization's page and that
    organization prints the code in an edition this chain also holds keys
    in. Deciding both same_program would sum two organizations' lines into
    one page grain (fct_program_decade_series keeps organization only for
    the PB2026 collision codes), i.e. put this chain's dollars on the other
    organization's page. None otherwise.

    The page: for a PB2026 collision code, `page` (the (account, org) the
    pre-fill picked; a blank org means no page was picked); for any other
    code, the code's one page, owned by the organizations that print it in
    PB2024-26 (a chain of one of them is the page's own and never clashes).
    Codes '10' and '15' are the live non-collision cases (PB2018 `10`:
    TJS's page, DPAA's line; PB2021-23 `15`: DISA's page, TJS's line)."""
    if not ch.organization:
        return None
    code, own = ch.line_item_code, _modern_org(ch.organization)
    held = {e for e, _key in ch.keys}
    rivals: dict[str, set[int]] = defaultdict(set)
    if code in collision_codes:
        page_account, page_org = page
        if not page_org or page_org == own:
            return None
        for (a, o), eds in org_editions.get(code, {}).items():
            if a == page_account and _modern_org(o) == page_org:
                rivals[o] |= eds
    else:
        owners = sorted({o for c, _a, o in ctx.line_idents if c == code})
        if not owners or own in owners:
            return None
        page_org = "/".join(owners)
        for (_a, o), eds in org_editions.get(code, {}).items():
            if o != ch.organization:
                rivals[o] |= eds
    shared = {o: sorted(eds & held) for o, eds in rivals.items() if eds & held}
    return (page_org, shared) if shared else None


def _prefill(ch: Chain, keys: Sequence[EraKey], ctx: _Context, info: dict,
             collision_codes: frozenset[str],
             modern_pages: frozenset[tuple[str, str, str]],
             org_editions: Mapping[str, Mapping[tuple[str, str], set[int]]],
             ) -> tuple[str, str, str, str]:
    """(proposed_decision, reason, program_account, program_org) — Claude's
    pre-fill for the owner; never a decision."""
    rule = _proposed_rule(ch.classes)
    pa = po = ""
    if ch.line_item_code in collision_codes:
        page = collision_page(ch, modern_pages)
        pa, po = page if page is not None else _pick_page_by_title(
            ch, keys, ctx, modern_pages)
    if ch.classes == frozenset({"H"}):
        return ("history_only",
                f"{rule}: era-only code whose titles drift — confirm one program"
                " (history_only) or split the range (exclude_reused_code)", "", "")
    clash = _org_clash(ch, ctx, collision_codes, (pa, po), org_editions)
    if clash is not None:
        # another organization's page: data only. A collision code pins the
        # chain's own identity so its grain stays apart from the page's.
        page_org, shared = clash
        printed = "; ".join(
            f"code also printed by {o} in {', '.join(f'PB{e}' for e in eds)}"
            for o, eds in sorted(shared.items()))
        if ch.line_item_code in collision_codes:
            page = f"{ch.line_item_code}-{page_org} (title match)"
            pa, po = ch.account, _modern_org(ch.organization)
        else:
            page, pa, po = ch.line_item_code, "", ""
        return ("history_only", f"{rule}: {printed}; page {page} is {page_org}'s",
                pa, po)
    if ch.classes == frozenset({"A1"}):
        # only a collision-code chain with no matching PB2026 page gets here:
        # pin it to its own PB2024-26 line identity, data only
        org = _modern_org(ch.organization)
        lines = sorted((a, o) for c, a, o in ctx.line_idents
                       if c == ch.line_item_code and a == ch.account
                       and (not ch.organization or o == org))
        pa, po = lines[0] if len(lines) == 1 else ("", "")
        return ("history_only",
                f"{rule}: collision code with no PB2026 page for"
                f" {ch.account}{'/' + ch.organization if ch.organization else ''}"
                " — history_only (data only), or name the page it joins", pa, po)
    if ch.classes & {"R2", "R3"}:
        # Fix round 2 (review finding): same_program only when the chain's
        # latest filed title actually matches the destination's modern
        # title — moving accounts doesn't prove it is the same program.
        destinations = info["modern_destinations"]
        pin = (pa, po if ch.line_item_code in ctx.split else "") if (pa or po) else None
        own = (ch.account,
               _modern_org(ch.organization) if ch.line_item_code in ctx.split else "")
        if pin is not None:
            target = next((d for d in destinations if (d[0], d[1]) == pin), None)
        elif len(destinations) == 1:
            target = destinations[0]
        else:
            own_hits = [d for d in destinations if (d[0], d[1]) == own]
            target = own_hits[0] if len(own_hits) == 1 else None
        if target is None:
            # Fix round 3: name what's actually wrong — a pin with no title,
            # or no destination at all — instead of always claiming there
            # are "several possible destinations" (neither happens live,
            # but the wording must not lie if the data ever produces one).
            if pin is not None:
                return ("",
                        f"{rule}: the collision pin {pin[0]}"
                        f"{'/' + pin[1] if pin[1] else ''} has no PB2024-26"
                        " title on record — decide which program this line"
                        " belongs to", pa, po)
            if not destinations:
                return ("",
                        f"{rule}: account/organization move, but no"
                        " PB2024-26 line for this code has a title on"
                        " record — decide which program this line belongs"
                        " to", pa, po)
            listed = _format_destinations(destinations)
            return ("",
                    f"{rule}: account/organization move to several possible"
                    f" destinations ({listed}) — decide which, if any, this"
                    " line moved to", pa, po)
        dest_account, dest_org, dest_title = target
        dest_label = f"{dest_account}{'/' + dest_org if dest_org else ''}"
        is_own = (dest_account, dest_org) == own
        # Fix round 3: the destination may print several titles across
        # PB2024-26 (e.g. PB2024 "OHIO Replacement Submarine", PB2026
        # "Columbia Class Submarine" at the SAME account) — a match on any
        # one of them is a match; checking only the latest title missed
        # earlier-edition confirmations like this one.
        dest_mi = ctx.idx.get((ch.line_item_code, dest_account, dest_org))
        jac = (max((title_jaccard(keys[-1].filed_title, t) for t in dest_mi.titles),
                   default=0.0) if dest_mi is not None else 0.0)
        if jac >= JACCARD_MIN:
            if is_own:
                others = sorted({a for a, o, _t in destinations if (a, o) != own})
                return ("same_program",
                        f"{rule}: the code's own account ({dest_label}); also"
                        f" printed by {', '.join(others) or 'no other account'}",
                        pa, po)
            return ("same_program",
                    f"{rule}: account/organization move (modern accounts"
                    f" {', '.join(info['modern_accounts']) or 'none'})", pa, po)
        if is_own:
            others = sorted({a for a, o, _t in destinations if (a, o) != own})
            return ("",
                    f"{rule}: the code's own account ({dest_label}) prints"
                    f" '{dest_title}', not this line's title; also printed"
                    f" by {', '.join(others) or 'no other account'} — confirm"
                    " same_program by hand", pa, po)
        return ("",
                f"{rule}: account/organization move, but the code is"
                f" '{dest_title}' in {dest_label}; decide same_program only"
                " if this line moved there", pa, po)
    if "R1" in ch.classes:
        if info["continuity_total"] == 0:
            # no era-edition-anchored check exists at all: the code could be
            # a genuine rename or an unrelated program reusing the number.
            # Never pre-fill a decision from zero evidence (spec §5.3).
            return ("",
                    f"{rule}: no era-side continuity evidence (title Jaccard"
                    f" {info['title_jaccard'] or 'n/a'}); possible reused"
                    " code — decide same_program, a range split, or"
                    " exclude_reused_code", pa, po)
        if info["continuity_ok"]:
            return ("same_program",
                    f"{rule}: renamed, continuity {info['continuity']} holds"
                    f" (title Jaccard {info['title_jaccard'] or 'n/a'})", pa, po)
        if not info["has_request"]:
            # Fix round 3 (owner-facing finding): a "range split" is the
            # wrong advice when the continuity check failed only because
            # the line never carried a request amount at all (a Congress-
            # added line, e.g. the 0350D National Guard/Reserve
            # "Miscellaneous Equipment" rows) — there is no year-to-year
            # request/actuals pair for the check to confirm either way.
            return ("",
                    f"{rule}: renamed '{keys[-1].filed_title}' →"
                    f" '{info['modern_title'] or 'n/a'}'; no request in any"
                    " edition (a Congress-added line), so the year-to-year"
                    " continuity check cannot confirm it — decide"
                    " same_program if the modern line is the same program",
                    pa, po)
        return ("",
                f"{rule}: renamed and continuity {info['continuity']} fails —"
                " consider a range split (earlier range exclude_reused_code)", pa, po)
    return ("same_program",
            f"{rule}: renamed within A2 (title Jaccard {info['title_jaccard']},"
            f" continuity {info['continuity']})", pa, po)


def propose(
    *, duckdb_path: Path, raw_docs_dir: Path, out_dir: Path, seed_path: Path,
    decided_on: date,
) -> dict:
    """Classify, chain, apply the class rulings, search successors, write
    keys.csv / chains.csv / review.csv / counts.json under out_dir and the
    class-ruled rows of the seed. Owner batch rows already in the seed
    (ruling not a class ruling) are kept verbatim and their chains are
    neither class-ruled nor re-proposed. Returns the counts dict."""
    inputs = load_inputs(Path(duckdb_path))
    split = org_split_codes(inputs.era)
    if split != ORG_SPLIT_CODES:
        raise RuntimeError(
            f"era-map: org-split codes changed: lake {sorted(split)} !="
            f" ORG_SPLIT_CODES {sorted(ORG_SPLIT_CODES)} — the chain identity"
            " would move; review the change and update the constant and spec §4.3")
    ctx = _Context(inputs.era, inputs.modern)
    classes = {(k.edition, k.era_key): ctx.classify(k, inputs.collision_codes)
               for k in ctx.era}
    chains = build_chains(inputs.era, classes)
    keys_by_chain = group_keys(inputs.era)
    org_editions = _org_editions(inputs.era, split)

    existing = read_seed(Path(seed_path))
    owner_rows = [r for r in existing if r["ruling"] not in CLASS_RULINGS]
    owner_chains = {chain_id(r["line_item_code"], r["account"], r["organization"])
                    for r in owner_rows}
    review_path = Path(out_dir) / "review.csv"
    if review_path.is_file():
        pending = sorted({r["chain_id"] for r in read_csv(review_path)
                          if (r.get("decision") or "").strip()
                          and r["chain_id"] not in owner_chains})
        if pending:
            raise RuntimeError(
                f"era-map propose: {review_path} holds decisions for"
                f" {len(pending)} chain(s) that are not ratified yet"
                f" ({', '.join(pending[:5])}) — run `govbudget era-map ratify`"
                " first, or blank their decision column; nothing was written")
    open_chains = [c for c in chains if c.chain_id not in owner_chains]
    ruled, left = apply_class_rulings(
        open_chains, modern_pages=inputs.modern_pages,
        collision_codes=inputs.collision_codes, decided_on=decided_on)
    successors = search_successors(chains, raw_docs_dir=Path(raw_docs_dir),
                                   modern=inputs.modern)
    info = {c.chain_id: _chain_context(c, keys_by_chain[c.chain_id], ctx)
            for c in chains}

    prior = {r["decision_id"]: r for r in existing if r["ruling"] in CLASS_RULINGS}
    by_id = {c.chain_id: c for c in chains}
    for row in ruled:
        cid = chain_id(row["line_item_code"], row["account"], row["organization"])
        ch, ci = by_id[cid], info[cid]
        row["modern_title"] = ci["modern_title"]
        row["evidence"] = (f"title_jaccard={ci['title_jaccard'] or 'n/a'};"
                           f" continuity={ci['continuity']};"
                           f" actuals_k={_fmt_k(ch.actuals_k)}")
        if row["decision"] == "history_only" and cid in successors:
            for f in ("successor_code", "successor_account", "successor_evidence"):
                row[f] = successors[cid][f]
        old = prior.get(row["decision_id"])
        if old and all(old[f] == row[f] for f in
                       ("keys_sha256", "decision", "ruling", "program_account",
                        "program_org")):
            row["decided_on"] = old["decided_on"]
    write_seed(Path(seed_path), owner_rows + ruled)

    ruled_ids = {chain_id(r["line_item_code"], r["account"], r["organization"]): r
                 for r in ruled}
    review = []
    left_reason: dict[str, str] = {}
    for ch in left:
        keys = keys_by_chain[ch.chain_id]
        ci = info[ch.chain_id]
        decision, reason, pa, po = _prefill(ch, keys, ctx, ci,
                                            inputs.collision_codes,
                                            inputs.modern_pages, org_editions)
        if ch.classes == frozenset({"A1"}):
            left_reason[ch.chain_id] = "collision code without a matching PB2026 page"
        succ = successors.get(ch.chain_id, {})
        review.append({
            "chain_id": ch.chain_id,
            "first_edition": str(ch.first_edition),
            "last_edition": str(ch.last_edition),
            "titles_by_edition": _titles_seen(ch, ch.first_edition, ch.last_edition),
            "modern_title": ci["modern_title"],
            "accounts": (f"era={ch.account}{'/' + ch.organization if ch.organization else ''};"
                         f" modern={','.join(ci['modern_accounts']) or 'none'}"),
            "continuity": ci["continuity"],
            "actuals_k": _fmt_k(ch.actuals_k),
            "proposed_decision": decision,
            "reason": reason,
            "program_account": pa,
            "program_org": po,
            "successor_code": succ.get("successor_code", ""),
            "keys_sha256": ch.keys_sha256,
            "decision": "",
            "note": "",
        })
    review.sort(key=lambda r: (-Decimal(r["actuals_k"] or "0"), r["chain_id"]))

    out_dir = Path(out_dir)
    write_csv(out_dir / "review.csv", REVIEW_COLUMNS, review)
    chain_rows = []
    for ch in chains:
        ci, succ = info[ch.chain_id], successors.get(ch.chain_id, {})
        ruled_row = ruled_ids.get(ch.chain_id)
        chain_rows.append({
            "chain_id": ch.chain_id, "line_item_code": ch.line_item_code,
            "account": ch.account, "organization": ch.organization,
            "first_edition": str(ch.first_edition), "last_edition": str(ch.last_edition),
            "classes": _proposed_rule(ch.classes), "n_keys": str(ch.n_keys),
            "keys_sha256": ch.keys_sha256, "actuals_k": _fmt_k(ch.actuals_k),
            "titles_by_edition": _titles_seen(ch, ch.first_edition, ch.last_edition),
            "modern_title": ci["modern_title"], "title_jaccard": ci["title_jaccard"],
            "continuity": ci["continuity"],
            "ruling": ruled_row["ruling"] if ruled_row else (
                "owner-batch" if ch.chain_id in owner_chains else ""),
            "decision": ruled_row["decision"] if ruled_row else "",
            "left_ruling_reason": left_reason.get(ch.chain_id, ""),
            "successor_code": succ.get("successor_code", ""),
            "successor_account": succ.get("successor_account", ""),
            "successor_evidence": succ.get("successor_evidence", ""),
        })
    write_csv(out_dir / "chains.csv", CHAIN_COLUMNS, chain_rows)
    key_rows = []
    for ch in chains:
        ci = info[ch.chain_id]
        for k in keys_by_chain[ch.chain_id]:
            jac = ctx.best_jaccard(k)
            key_rows.append({
                "edition": str(k.edition), "era_key": k.era_key,
                "account": k.account, "organization": k.organization,
                "budget_activity": k.budget_activity or "",
                "line_number": k.era_key.rsplit("-L", 1)[1],
                "line_item_code": k.line_item_code, "filed_title": k.filed_title or "",
                "chain_id": ch.chain_id, "class": classes[(k.edition, k.era_key)],
                "title_jaccard": "" if jac is None else f"{jac:.2f}",
                "continuity": ci["continuity"],
                "actuals_k": _fmt_k(k.actuals_k), "enacted_k": _fmt_k(k.enacted_k),
                "source_document_sha256": k.source_document_sha256,
                "source_rows": ",".join(str(r) for r in sorted(
                    {_cell_sort_key(c)[0] for c in k.source_cells})),
                "source_cells": ",".join(k.source_cells),
            })
    key_rows.sort(key=lambda r: (int(r["edition"]), r["era_key"]))
    write_csv(out_dir / "keys.csv", KEY_COLUMNS, key_rows)

    groups: dict[str, int] = defaultdict(int)
    for ch in chains:
        groups[_chain_group(ch)] += 1
    key_classes = {c: 0 for c in CLASS_ORDER}
    key_dollars = {c: Decimal(0) for c in CLASS_ORDER}
    for k in inputs.era:
        cls = classes[(k.edition, k.era_key)]
        key_classes[cls] += 1
        key_dollars[cls] += k.actuals_k or Decimal(0)
    rulings: dict[str, int] = {r: 0 for r in CLASS_RULINGS}
    for r in ruled:
        rulings[r["ruling"]] += 1
    by_edition: dict[str, int] = defaultdict(int)
    for k in inputs.era:
        by_edition[str(k.edition)] += 1
    era_only = [c for c in chains if c.classes == frozenset({"H"})]
    searched = [c for c in era_only if is_successor_searchable(c.line_item_code)]
    not_searchable = [c for c in era_only if not is_successor_searchable(c.line_item_code)]
    successor_coverage = {
        "era_only_chains": len(era_only),
        "era_only_actuals_k": _fmt_k(sum((c.actuals_k for c in era_only), Decimal(0))),
        "searched_chains": len(searched),
        "searched_actuals_k": _fmt_k(sum((c.actuals_k for c in searched), Decimal(0))),
        "not_searchable_chains": len(not_searchable),
        "not_searchable_actuals_k": _fmt_k(
            sum((c.actuals_k for c in not_searchable), Decimal(0))),
        "successors_found": len(successors),
        "successors_found_actuals_k": _fmt_k(sum(
            (by_id[cid].actuals_k for cid in successors), Decimal(0))),
    }
    counts = {
        "era_keys": len(inputs.era),
        "era_keys_by_edition": dict(sorted(by_edition.items())),
        "chains": len(chains),
        "chain_groups": dict(sorted(groups.items())),
        "key_classes": key_classes,
        "key_class_actuals_k": {c: _fmt_k(v) for c, v in key_dollars.items()},
        "era_actuals_k": _fmt_k(sum(key_dollars.values(), Decimal(0))),
        "rulings": rulings,
        "ruled_actuals_k": {
            r: _fmt_k(sum((by_id[chain_id(x["line_item_code"], x["account"],
                                          x["organization"])].actuals_k
                           for x in ruled if x["ruling"] == r), Decimal(0)))
            for r in CLASS_RULINGS},
        "left_ruling": len(left_reason),
        "review_rows": len(review),
        "owner_batch_chains": len(owner_chains),
        "org_split_codes": sorted(split),
        "collision_codes": sorted(inputs.collision_codes),
        "successors": {cid: s["successor_code"] for cid, s in sorted(successors.items())},
        "successor_coverage": successor_coverage,
    }
    (out_dir / "counts.json").write_text(json.dumps(counts, indent=1, sort_keys=True) + "\n")
    return counts


# ---------------------------------------------------------------------------
# ratify / check (§5.3, §7)
# ---------------------------------------------------------------------------


def default_seed_path() -> Path:
    from govbudget import config

    return config.ROOT / "dbt" / "seeds" / "p1_era_code_decisions.csv"


def default_out_dir() -> Path:
    from govbudget import config

    return config.RESEARCH_DIR / "era_map"


def _page_grain(row: Mapping[str, str],
                collision_codes: frozenset[str]) -> tuple[str, str, str]:
    """The fct_program_decade_series page grain a same_program row's keys
    join (spec §4.5): the bare code, plus the pins on a PB2026 collision
    code."""
    code = row["line_item_code"]
    if code in collision_codes:
        return (code, row["program_account"], row["program_org"])
    return (code, "", "")


def _row_editions(row: Mapping[str, str],
                  keys_by_chain: Mapping[str, Sequence[EraKey]]) -> set[int]:
    """The editions inside the row's range in which its chain holds keys."""
    cid = chain_id(row["line_item_code"], row["account"], row["organization"])
    first, last = int(row["first_edition"]), int(row["last_edition"])
    return {k.edition for k in keys_by_chain.get(cid, ()) if first <= k.edition <= last}


def ratify(
    *, review_csv: Path, seed_path: Path, batch: str, decided_on: date,
    duckdb_path: Path,
) -> int:
    """Merge the owner-decided rows of review_csv (non-blank `decision`) into
    the seed as ruling R-DEC-ERA-<batch>, decided_by owner. Validates, and
    writes nothing unless every row passes:

      * batch matches B<n> and has not been ratified before;
      * decision is in DECISIONS;
      * the chain still exists and its keys_sha256 equals the review-time
        value (otherwise the chain changed after review: re-run propose);
      * first_edition..last_edition lies inside the chain and holds keys;
      * collision code + same_program/history_only: program_account and
        program_org both set, naming a PB2026 page (same_program), or a
        PB2024–26 P-1 line identity or the chain's own account/organization
        (history_only); every other row leaves them blank;
      * successor_code only on history_only, and only the book-stated
        successor propose recorded in chains.csv beside review_csv;
      * no range overlaps an existing seed row or another row of the batch;
      * one organization per page grain and edition: an org-split chain's
        same_program row may not share a page grain (_page_grain) and an
        edition holding keys with another organization's same_program row,
        already in the seed or in this batch (codes '10' and '15' are not
        PB2026 collision codes, so two organizations' same_program keys
        would sum into one page);
      * every chain the batch touches is decided in full: its seed rows and
        batch rows together cover every edition in which it holds keys.
        propose re-proposes only chains with no owner row, so a part-decided
        chain would never return to review.csv; split the whole chain into
        ranges, or leave its decision blank (defer it) until it is.
    Returns the number of rows added."""
    if not BATCH_RE.fullmatch(batch):  # .match: `$` accepts "B1\n"
        raise ValueError(f"batch {batch!r} is not B<n> (e.g. B1)")
    ruling = f"R-DEC-ERA-{batch}"
    review_csv = Path(review_csv)
    rows = read_csv(review_csv)
    missing = set(REVIEW_COLUMNS) - set(rows[0].keys() if rows else REVIEW_COLUMNS)
    if missing:
        raise ValueError(f"{review_csv}: missing columns {sorted(missing)}")
    decided = [r for r in rows if (r.get("decision") or "").strip()]
    if not decided:
        raise ValueError(f"{review_csv}: no row has a decision — nothing to ratify")
    existing = read_seed(Path(seed_path))
    if any(r["ruling"] == ruling for r in existing):
        raise ValueError(f"{ruling} is already in {seed_path}; use a new batch number")
    stated = {r["chain_id"]: r for r in read_csv(review_csv.parent / "chains.csv")}

    inputs = load_inputs(Path(duckdb_path))
    ctx = _Context(inputs.era, inputs.modern)
    classes = {(k.edition, k.era_key): ctx.classify(k, inputs.collision_codes)
               for k in ctx.era}
    by_id = {c.chain_id: c for c in build_chains(inputs.era, classes)}
    keys_by_chain = group_keys(inputs.era)
    line_idents = {(m.code, m.account, m.organization) for m in inputs.modern}

    errors: list[str] = []
    new: list[dict] = []
    for r in decided:
        cid = r["chain_id"]
        decision = r["decision"].strip()
        ch = by_id.get(cid)
        if ch is None:
            errors.append(f"{cid}: no such chain in the lake")
            continue
        if r["keys_sha256"] != ch.keys_sha256:
            errors.append(f"{cid}: keys_sha256 changed since review"
                          f" ({r['keys_sha256'][:12]} -> {ch.keys_sha256[:12]});"
                          " re-run propose and re-review")
            continue
        if decision not in DECISIONS:
            errors.append(f"{cid}: decision {decision!r} not in {DECISIONS}")
            continue
        try:
            first, last = int(r["first_edition"]), int(r["last_edition"])
        except ValueError:
            errors.append(f"{cid}: first/last edition must be integers")
            continue
        if not (ch.first_edition <= first <= last <= ch.last_edition):
            errors.append(f"{cid}: range {first}-{last} outside the chain"
                          f" ({ch.first_edition}-{ch.last_edition})")
            continue
        n_keys, sha = range_sha(keys_by_chain[cid], first, last)
        if n_keys == 0:
            errors.append(f"{cid}: range {first}-{last} holds no era key")
            continue
        pa, po = r["program_account"].strip(), r["program_org"].strip()
        pinned = (ch.line_item_code in inputs.collision_codes
                  and decision in ("same_program", "history_only"))
        if pinned:
            ident = (ch.line_item_code, pa, po)
            if not pa or not po:
                errors.append(f"{cid}: collision code — program_account and"
                              " program_org are required")
                continue
            if decision == "same_program" and ident not in inputs.modern_pages:
                errors.append(f"{cid}: {ident} is not a PB2026 page")
                continue
            own = {(k.account, _modern_org(k.organization))
                   for k in keys_by_chain[cid]}
            if (decision == "history_only" and ident not in line_idents
                    and (pa, po) not in own):
                errors.append(f"{cid}: {ident} is not a PB2024-26 P-1 line or"
                              f" the chain's own identity {sorted(own)}")
                continue
        elif pa or po:
            errors.append(f"{cid}: program_account/program_org are only set for"
                          " collision-code same_program/history_only rows")
            continue
        successor: dict[str, str] = {}
        succ = r["successor_code"].strip()
        if succ:
            book = stated.get(cid, {})
            if decision != "history_only":
                errors.append(f"{cid}: successor_code only on history_only rows")
                continue
            if book.get("successor_code") != succ:
                errors.append(f"{cid}: successor {succ!r} is not the book-stated"
                              f" successor {book.get('successor_code') or '(none)'!r}")
                continue
            successor = {f: book[f] for f in
                         ("successor_code", "successor_account", "successor_evidence")}
        new.append(seed_row(
            ch, first=first, last=last, n_keys=n_keys, keys_sha=sha,
            decision=decision, ruling=ruling, decided_on=decided_on,
            program_account=pa, program_org=po, successor=successor,
            modern_title=r["modern_title"],
            evidence=(f"continuity={r['continuity']}; actuals_k={r['actuals_k']};"
                      f" proposed={r['proposed_decision'] or '(none)'}:"
                      f" {r['reason']}"),
            note=r["note"],
        ))
    cc = inputs.collision_codes
    for i, a in enumerate(new):
        for b in existing + new[:i]:
            if _ranges_overlap(a, b):
                errors.append(f"{a['decision_id']} overlaps {b['decision_id']}")
            if (a["decision"] == b["decision"] == "same_program"
                    and a["organization"] and b["organization"]
                    and a["organization"] != b["organization"]
                    and _page_grain(a, cc) == _page_grain(b, cc)):
                shared = sorted(_row_editions(a, keys_by_chain)
                                & _row_editions(b, keys_by_chain))
                if shared:
                    code, pin_a, pin_o = _page_grain(a, cc)
                    page = f"{code} ({pin_a}/{pin_o})" if pin_o else code
                    errors.append(
                        f"{a['decision_id']}: same_program collides with"
                        f" {b['decision_id']} — page {page} would"
                        f" sum {a['organization']} and {b['organization']} in"
                        f" {', '.join(f'PB{e}' for e in shared)}; decide"
                        " history_only for the organization whose page it is not")
    touched = sorted({chain_id(a["line_item_code"], a["account"], a["organization"])
                      for a in new})
    for cid in touched:
        covered: set[int] = set()
        for r in existing + new:
            if chain_id(r["line_item_code"], r["account"], r["organization"]) == cid:
                covered.update(range(int(r["first_edition"]),
                                     int(r["last_edition"]) + 1))
        open_eds = sorted({k.edition for k in keys_by_chain[cid]} - covered)
        if open_eds:
            errors.append(f"{cid}: editions {', '.join(map(str, open_eds))} left"
                          " undecided — split the whole chain or defer it")
    if errors:
        raise ValueError("era-map ratify refused; nothing written:\n  "
                         + "\n  ".join(errors))
    write_seed(Path(seed_path), existing + new)
    return len(new)


def check(*, duckdb_path: Path, seed_path: Path) -> dict:
    """{"undecided": [{"chain_id", "editions", "n_keys"}],
        "stale": [{"decision_id", "seed_n_keys", "lake_n_keys",
                   "seed_sha256", "lake_sha256"}]}

    undecided: era keys no seed row covers (chain + edition range).
    stale: seed rows whose keys in the current lake no longer hash to the
    reviewed keys_sha256 (or whose chain is gone)."""
    era = load_era_keys(Path(duckdb_path), with_amounts=False)
    keys_by_chain = group_keys(era)
    seed = read_seed(Path(seed_path))
    stale, covered = [], set()
    for r in seed:
        cid = chain_id(r["line_item_code"], r["account"], r["organization"])
        first, last = int(r["first_edition"]), int(r["last_edition"])
        keys = keys_by_chain.get(cid, [])
        n_keys, sha = range_sha(keys, first, last)
        if sha != r["keys_sha256"] or n_keys != int(r["n_keys"]):
            stale.append({"decision_id": r["decision_id"],
                          "seed_n_keys": int(r["n_keys"]), "lake_n_keys": n_keys,
                          "seed_sha256": r["keys_sha256"], "lake_sha256": sha})
        covered.update((cid, k.edition, k.era_key) for k in keys
                       if first <= k.edition <= last)
    undecided = []
    for cid, keys in sorted(keys_by_chain.items()):
        open_keys = [k for k in keys if (cid, k.edition, k.era_key) not in covered]
        if open_keys:
            undecided.append({"chain_id": cid,
                              "editions": sorted({k.edition for k in open_keys}),
                              "n_keys": len(open_keys)})
    return {"undecided": undecided, "stale": stale}
