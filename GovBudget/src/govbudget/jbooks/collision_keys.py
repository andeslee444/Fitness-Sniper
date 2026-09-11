"""Which program a link or a page on a SHARED BLI code belongs to (ROADMAP #70,
one rule for every consumer under ROADMAP #83).

Some pe_bli values in the PB2026 corpus are published by dim_programs more
than once because two genuinely different programs share one numeric code.
They split on one of two axes:

  ACCOUNT   ten keys — same organization, different appropriation account.
            '3010' is LPD Flight II in Shipbuilding & Conversion, Navy
            (1611N) AND Shipboard Tactical Communications in Other
            Procurement, Navy (1810N). Sprint E Task E3 gives each member its
            own page (`3010-SCN` / `3010-OPN`) and turns the bare
            `/program/3010/` into a disambiguation stub; ROADMAP #70 lets an
            award link name the ONE member its account evidence identifies.

  ORGANIZATION  three keys ('20', '30', '500') — one account (0300D),
            different organizations (DCSA/DTRA, OSD/DTRA/DMACT, DLA/DHRA).
            Each member has its own page (`20-DCSA` / `20-DTRA`) and no award
            links: their members share an account, so no account evidence
            tells them apart.

ROADMAP #83: the exporter (export_site._ProgramIdentity) and the two link
loaders (scripts/derive_ap_links.py, scripts/load_announcement_links.py)
used to carry their own copy of "is this key account-split". They agreed on
every key the warehouse has shipped and disagreed on two shapes it has not
— three rows over two accounts (one account naming two programs) and a row
with no account. classify_shared_keys is now the ONE rule, and the answer
for both shapes is the strict one the loaders already used: an axis
resolves a key only when it names EXACTLY ONE of the key's rows.

  ACCOUNT       every row's account is present and no two rows share one.
  ORGANIZATION  not ACCOUNT, and every row's organization is present and no
                two rows share one.
  UNRESOLVED    neither. No page slug and no link rule exists for such a
                key: the loaders exclude it from link targets, and the
                exporter refuses to run (require_resolved) rather than file
                two programs under one identity.

ACCOUNT wins when both axes would resolve, because every account-split
member page is addressed `{pe_bli}-{ACCOUNT_CODE}` (Task E3) and every award
link on a shared key carries the member ACCOUNT (#70, migration 014) — the
organization is never part of that contract.

Every function here is pure — the callers own the SQL.
"""
from __future__ import annotations

import enum
from collections.abc import Iterable, Mapping


class SplitAxis(enum.Enum):
    """The single axis that names exactly one of a shared key's rows."""

    ACCOUNT = "account"
    ORGANIZATION = "organization"
    UNRESOLVED = "unresolved"


class UnresolvedSharedKeyError(RuntimeError):
    """dim_programs publishes a pe_bli more than once and neither account nor
    organization alone names exactly one of its rows. Raised by
    require_resolved instead of letting a consumer guess an identity."""


def _names_exactly_one_row(values: list[str | None]) -> bool:
    """True iff every value is present and no two rows share one — the axis
    is a key over the rows, not merely 'varies somewhere'."""
    return all(values) and len(set(values)) == len(values)


def classify_shared_keys(
    rows: Iterable[tuple[str, str | None, str | None]],
) -> dict[str, SplitAxis]:
    """{pe_bli: axis} for every pe_bli that appears in `rows` more than once.

    `rows` are dim_programs' (pe_bli, account, organization) triples — one
    per published program row. Keys that appear once are absent from the
    result: they were never ambiguous. See the module docstring for the
    three axes and why ACCOUNT takes precedence.
    """
    by_pe: dict[str, list[tuple[str | None, str | None]]] = {}
    for pe_bli, account, organization in rows:
        by_pe.setdefault(pe_bli, []).append((account, organization))

    axes: dict[str, SplitAxis] = {}
    for pe_bli, members in by_pe.items():
        if len(members) < 2:
            continue
        if _names_exactly_one_row([account for account, _org in members]):
            axes[pe_bli] = SplitAxis.ACCOUNT
        elif _names_exactly_one_row([org for _account, org in members]):
            axes[pe_bli] = SplitAxis.ORGANIZATION
        else:
            axes[pe_bli] = SplitAxis.UNRESOLVED
    return axes


def partition_split_keys(
    rows: Iterable[tuple[str, str | None, str | None]],
) -> tuple[dict[str, set[str]], set[str], set[str]]:
    """The link loaders' view of classify_shared_keys.

    Returns ({pe_bli: {account, ...}} for the ACCOUNT keys — the members an
    award's or a document's account evidence may pick between —, the set of
    ORGANIZATION keys, and the set of UNRESOLVED keys). Both loaders exclude
    the last two from link targets: no account evidence can name one member
    of either.
    """
    rows = list(rows)
    axes = classify_shared_keys(rows)
    account_split: dict[str, set[str]] = {}
    for pe_bli, account, _organization in rows:
        if axes.get(pe_bli) is SplitAxis.ACCOUNT:
            account_split.setdefault(pe_bli, set()).add(account)
    org_split = {pe for pe, axis in axes.items() if axis is SplitAxis.ORGANIZATION}
    unresolved = {pe for pe, axis in axes.items() if axis is SplitAxis.UNRESOLVED}
    return account_split, org_split, unresolved


def require_resolved(
    rows: Iterable[tuple[str, str | None, str | None]], *, caller: str,
) -> dict[str, SplitAxis]:
    """classify_shared_keys, but it refuses to hand back an UNRESOLVED key.

    The exporter calls this: a shared key with no resolving axis has no page
    identity, and publishing it would file two programs' figures under one
    slug. `caller` names the consumer so the message says who stopped.
    """
    rows = list(rows)
    axes = classify_shared_keys(rows)
    bad = sorted(pe for pe, axis in axes.items() if axis is SplitAxis.UNRESOLVED)
    if not bad:
        return axes
    detail = "\n".join(
        f"  {pe!r}: "
        + ", ".join(
            f"(account={account!r}, organization={org!r})"
            for p, account, org in rows if p == pe
        )
        for pe in bad
    )
    raise UnresolvedSharedKeyError(
        f"{caller}: dim_programs publishes {len(bad)} shared pe_bli key(s)"
        f" that neither account nor organization alone can resolve. A member"
        f" page ({{pe_bli}}-{{ACCOUNT_CODE}} or {{pe_bli}}-{{ORGANIZATION}})"
        f" and an award link on a shared key both need ONE axis naming exactly"
        f" one dim_programs row, and none does here — nothing was published."
        f" Fix the mart (dbt/models/marts/dim_programs.sql) or add a rule in"
        f" govbudget/jbooks/collision_keys.py; do not guess.\n{detail}"
    )


def _exactly_one(hits: set[str]) -> str | None:
    """The single element of `hits`, or None when the evidence named zero or
    more than one. Never picks a winner — an ambiguous link is not published
    (the whole point of #70: a link that could belong to either program is
    not evidence about either one)."""
    return next(iter(hits)) if len(hits) == 1 else None


def member_for_award(
    member_fed_accounts: dict[str, set[str]], award_accounts: set[str],
) -> str | None:
    """The ONE member account whose appropriation funds this award.

    member_fed_accounts maps each member's raw budget_lines account code
    ('1611N') to the lake-style federal account keys it covers ('017-1611' —
    see derive_ap_links.fed_accounts_from_codes); award_accounts is the
    award's own federal_accounts_funding_this_award set. Returns None when
    the award's money names both members (it cannot say which line paid) or
    neither (there is no account evidence at all) — including the common case
    of an award whose funding accounts are unknown.
    """
    return _exactly_one({
        account for account, fed in member_fed_accounts.items()
        if fed & award_accounts
    })


def member_for_document(
    document_accounts: set[str], member_accounts: set[str],
) -> str | None:
    """The ONE member a J-book document identifies.

    An announcement link's evidence is a lexicon entry quoting a narrative in
    a specific J-book PDF, and the Navy files one procurement book per
    appropriation (SCN_Book.pdf, OPN_BA1_Book.pdf, …), so the accounts that
    book's own detail rows carry name the member. Returns None when the book
    carries both members' lines, or none of them.
    """
    return _exactly_one(set(document_accounts) & set(member_accounts))


# ---------------------------------------------------------------------------
# Contradictory member evidence between the two loaders
#
# budget_line_awards is unique on (pe_bli, exhibit, fiscal_year, award_piid) —
# `account` is deliberately NOT part of that key, because exactly-one-member
# admission already keeps one award naming at most one member and widening the
# key would PERMIT a future loader to publish one award against both. The cost
# of that choice is that both loaders' `on conflict … do update set
# account=excluded.account` lets whichever runs last move a published link from
# one member's page to the other's, with nothing said.
#
# Two independent evidence routes disagreeing about which of two programs an
# award belongs to is a finding about the evidence, not a tie to be broken by
# run order. These helpers let each loader see the disagreement BEFORE it
# writes, so it can stop inside its transaction and leave the corpus alone.
# ---------------------------------------------------------------------------


class ContradictoryAccountError(RuntimeError):
    """Two evidence routes attributed ONE link to different members of a
    shared BLI code. Raised instead of letting the upsert pick a winner."""


def contradictory_accounts(
    stored: Mapping[tuple, str | None],
    incoming: Iterable[tuple[tuple, str | None]],
) -> list[tuple[tuple, str | None, str | None]]:
    """Which incoming links contradict a member claim that already stands.

    `stored` maps each already-published link's unique key — (pe_bli, exhibit,
    fiscal_year, award_piid), normalized by the caller — to the member account
    it names (None for the ordinary keys, which name no member). `incoming` is
    the same shape for the rows about to be written.

    Returns [(key, standing_account, incoming_account), …] in incoming order,
    for every key whose standing claim is a REAL member (not None) and whose
    incoming row names a different one — including a row that names none at
    all, which would blank the account and drop the link off both member pages
    just as silently. A key with no standing claim is not a contradiction:
    that is the ordinary case of a loader owning a key outright.

    The scan is also self-consistent: two rows in ONE batch disagreeing about
    the same key are reported too, since insertion order would otherwise
    decide it exactly the way run order would.
    """
    conflicts: list[tuple[tuple, str | None, str | None]] = []
    claim: dict[tuple, str | None] = {}
    for key, account in incoming:
        standing = claim[key] if key in claim else stored.get(key)
        if standing is not None and standing != account:
            conflicts.append((key, standing, account))
        claim[key] = account
    return conflicts


def raise_on_contradictory_accounts(
    stored: Mapping[tuple, str | None],
    incoming: Iterable[tuple[tuple, str | None]],
    *,
    loader: str,
) -> None:
    """contradictory_accounts, but it stops the load. `loader` names the
    caller so the message says which run found the disagreement."""
    conflicts = contradictory_accounts(stored, incoming)
    if not conflicts:
        return
    lines = "\n".join(
        f"  {key[0]} {key[3]} ({key[1]} FY{key[2]}): already published against"
        f" account {standing}, this run attributes it to {account}"
        for key, standing, account in conflicts[:20]
    )
    more = "" if len(conflicts) <= 20 else f"\n  … and {len(conflicts) - 20} more"
    raise ContradictoryAccountError(
        f"{loader}: {len(conflicts)} link(s) contradict a member attribution"
        f" that is already published on a shared BLI code. Two evidence routes"
        f" naming DIFFERENT members of one code is a finding about the"
        f" evidence, not a tie for the last loader to break — nothing was"
        f" written. Investigate the pairs below and fix the losing route.\n"
        f"{lines}{more}"
    )
