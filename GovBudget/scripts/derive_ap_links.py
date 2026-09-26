"""Leg 1 derivation: turn verified (acquisition program -> J-book line) mappings
into award-level links, narrowed per award by funding account.

Tiers (deterministic, conservative):
  medium  the award's funding accounts select >=1 verified line of its
          program (program identity from FPDS AP code, mapping verified by
          two adversarial lenses, money color confirmed) — the award is
          program-pinned, but which specific line (production vs
          modification vs research) paid is not provable from account data
          alone: sibling lines often share one appropriation account. A
          held-out study measured the earlier "unique matched line" high
          tier at 34/60 = 56.7% (17 of 26 refutations were exactly this
          sibling-line ambiguity), and that tier was withdrawn 2026-09-04.
  low     accounts select none of the program's lines (e.g. O&M money on an
          MDAP) — NOT published; retained for audit

Only lines present in dim_programs (the site's display universe) may publish.
Inserts into budget_line_awards with method 'fpds-ap' (medium/low); the
adjudication overlay does not apply to these rows (they are evidence-graded
at creation).

Recipient (R-DEC-RECIPIENT, fix-round-5 ruling 2026-09-26): each (AP code,
PIID) group names the UEI with the largest total obligation on its rows, a tie
going to the lowest UEI; the basis ('obligation' / 'uei_tiebreak') is stored
in budget_line_awards.recipient_basis (migration 019). See ap_awards and
pick_recipient, which load_announcement_links.py shares. The fpds-ap rows an
earlier run stored keep their recipients until this deriver runs again, with
recipient_basis 'pre_rule' (migration 019's backfill, R-DEC-DERIVE 2026-09-26:
it is not run in chain G).

Usage: uv run python scripts/derive_ap_links.py [--dry-run]
"""
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import duckdb
import psycopg

from govbudget import config
from govbudget.award_moves import AwardMoves, register_award_rows
from govbudget.jbooks.collision_keys import (
    member_for_award,
    partition_split_keys,
    raise_on_contradictory_accounts,
)

# Catch-all budget lines ("Items Less Than $5 Million", "Ordnance Items <$5M",
# "Other Support Aircraft") are aggregates, not programs: a link asserting an
# award executes "Items Less Than $5 Million" is content-free, and the $ in
# the title trips the site's currency-in-prose sweep. Never link targets.
CATCHALL_TITLE = re.compile(r"(less than|under|<)\s*\$|^other\b|^miscellaneous", re.I)

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "data" / "research"
# The database the exporter reads: config.PG_DSN honours GOVBUDGET_PG_DSN
# and the gitignored .env (tests/test_loader_dsn.py).
DSN = config.PG_DSN
AGENCY_BY_LETTER = {"D": "097", "N": "017", "A": "021", "F": "057", "M": "017"}
#: The raw contracts archive, one directory per fiscal year (fy=YYYY).
CONTRACTS_GLOB = f"{ROOT}/data/parquet/contracts/fy=*/*.parquet"


def fed_accounts_from_codes(accounts) -> set[str]:
    """Map raw budget_lines.account codes (e.g. '1319N') to lake-style
    federal account keys ('097-1319') via AGENCY_BY_LETTER.

    Shared with load_announcement_links.py so both the FPDS-account path and
    the announcement money-color guard derive "which appropriation funds
    this line" the same way.
    """
    fed = set()
    for account in accounts:
        if account and account[-1:].isalpha():
            num, letter = account[:-1], account[-1].upper()
            pref = AGENCY_BY_LETTER.get(letter)
            if pref:
                fed.add(f"{pref}-{num}")
    return fed


# ---------------------------------------------------------------------------
# The member-attribution guard both loaders run before they write (ROADMAP #70
# fix round 1). Shared here rather than in govbudget/jbooks/collision_keys.py, which owns the
# pure resolution rule and no SQL — the same reason fed_accounts_from_codes
# lives here and is imported by load_announcement_links.
# ---------------------------------------------------------------------------


def stored_member_claims(cur) -> dict[tuple, str | None]:
    """Every published link's unique key → the member account it names.

    Read INSIDE the load transaction and AFTER this loader deleted its own
    rows, so what remains is the other evidence route's standing claims. The
    unique key's fiscal_year is an int column; normalize so a loader carrying
    it as text compares equal instead of silently never matching (a guard that
    can never fire is worse than no guard).
    """
    cur.execute(
        "select pe_bli, exhibit, fiscal_year, award_piid, account"
        " from budget_line_awards where account is not null"
    )
    return {
        (pe_bli, exhibit, int(fiscal_year), award_piid): account
        for pe_bli, exhibit, fiscal_year, award_piid, account in cur.fetchall()
    }


#: Column count of the budget_line_awards tuple both loaders build:
#: pe_bli, exhibit, fiscal_year, organization, award_piid, recipient_name,
#: recipient_uei, matched_obligation, method, confidence, score, rationale,
#: account, recipient_basis (R-DEC-RECIPIENT, migration 019 — appended last so
#: the positions incoming_member_claims reads did not move).
BLA_ROW_WIDTH = 14


def incoming_member_claims(rows) -> list[tuple[tuple, str | None]]:
    """The same shape for the rows about to be written. Both loaders build the
    14-column budget_line_awards tuple: pe_bli, exhibit, fiscal_year,
    organization, award_piid, …, account, recipient_basis.

    The subscripts below are POSITIONAL across two files (final review M3): if
    either loader ever inserts or reorders a column, `r[4]` silently starts
    reading recipient_name as the PIID and `r[12]` reads past the end or picks
    up the wrong field — and the member-attribution guard that runs on this
    output would compare nonsense while still looking like it fired. Assert the
    width so the shape change is a loud error at the loader, not a wrong
    account on a shared-key page.

    Both loaders call this on the exact rows they are about to upsert, so it
    also checks each row's recipient_basis (r[13]) is one the rule produces
    (RECIPIENT_BASES). Migration 019's CHECK admits PRE_RULE_BASIS too, for
    its backfill of rows written before R-DEC-RECIPIENT (R-DEC-DERIVE); a row
    a loader writes now is a fresh pick, so 'pre_rule' — or no basis — from a
    loader is a bug, refused here where the database would store it.
    """
    for r in rows:
        if len(r) != BLA_ROW_WIDTH:
            raise ValueError(
                f"budget_line_awards row has {len(r)} column(s), expected"
                f" {BLA_ROW_WIDTH}. incoming_member_claims reads pe_bli/exhibit/"
                f"fiscal_year/award_piid/account POSITIONALLY (r[0], r[1], r[2],"
                f" r[4], r[12]) and is shared by derive_ap_links.py and"
                f" load_announcement_links.py — update both loaders and"
                f" BLA_ROW_WIDTH together. Offending row: {r!r}"
            )
        if r[13] not in RECIPIENT_BASES:
            raise ValueError(
                f"budget_line_awards row carries recipient_basis {r[13]!r};"
                f" a loader writes only a basis R-DEC-RECIPIENT's pick"
                f" produces, one of {RECIPIENT_BASES} ({PRE_RULE_BASIS!r} is"
                f" migration 019's backfill value for rows written before the"
                f" rule, never a loader's). Offending row: {r!r}"
            )
    return [((r[0], r[1], int(r[2]), r[4]), r[12]) for r in rows]


#: The loader's own upsert, hoisted so tests can run the REAL statement
#: (tests/test_derive_ap_links_run_order.py) instead of restating it.
#:
#: The `where` clause is a RUN-ORDER guard (final review I3) — see the comment
#: at the executemany call site for the failure it prevents. Evidence-graded
#: methods outrank this mechanical derivation regardless of who ran last.
EVIDENCE_GRADED_METHODS = ("announcement+lexicon", "subaward+lexicon")

#: The recipient fields are part of the update (R-DEC-RECIPIENT): a row this
#: deriver takes over from the mechanical crosswalk (account*) publishes the
#: recipient ITS rule picked, with that rule's basis — not the crosswalk's
#: pick left behind with no basis. The `where` keeps an evidence-graded row's
#: recipient along with everything else.
UPSERT_SQL = """insert into budget_line_awards
   (pe_bli, exhibit, fiscal_year, organization, award_piid,
    recipient_name, recipient_uei, matched_obligation, method,
    confidence, score, rationale, account, recipient_basis)
   values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
   on conflict (pe_bli, exhibit, fiscal_year, award_piid)
   do update set confidence=excluded.confidence,
                 method=excluded.method, score=excluded.score,
                 rationale=excluded.rationale,
                 matched_obligation=excluded.matched_obligation,
                 account=excluded.account,
                 recipient_name=excluded.recipient_name,
                 recipient_uei=excluded.recipient_uei,
                 recipient_basis=excluded.recipient_basis
   where budget_line_awards.method not in ('announcement+lexicon', 'subaward+lexicon')"""


# ---------------------------------------------------------------------------
# A link's recipient (R-DEC-RECIPIENT, fix-round-5 ruling 2026-09-26): "(1)
# the UEI with the largest total obligation on the award (move rule applied);
# (2) among ties — including all-$0 — the recipient the link's cited
# announcement names (normalized-name match); (3) only then the lowest UEI."
# The ranking lives here, beside the other rules both loaders share;
# load_announcement_links supplies step (2)'s evidence, this deriver has none
# (an FPDS link cites no announcement).
# ---------------------------------------------------------------------------

#: budget_line_awards.recipient_basis values (migration 019), in rule order:
#: the bases pick_recipient returns, and the only ones a loader writes.
RECIPIENT_BASES = ("obligation", "announcement_named", "uei_tiebreak")

#: The one other value migration 019's CHECK admits (R-DEC-DERIVE, fix-round-6
#: ruling 2026-09-26): 019's backfill writes it onto a stored row of either
#: loader that predates R-DEC-RECIPIENT (the fpds-ap rows this deriver wrote
#: earlier, which chain G does not re-derive). No loader writes it
#: (incoming_member_claims refuses it).
PRE_RULE_BASIS = "pre_rule"


@dataclass(frozen=True)
class RecipientCandidate:
    """One recipient UEI on an award (or on one AP-tagged group of it).

    uei      None only for the rows that carry no UEI.
    dollars  the exact total obligation on this UEI's rows (None when no row
             parses as a number).
    name     the name carrying the most dollars on this UEI's OWN rows, ties
             to the lower name; None when its rows name no one.
    names    every name its rows carry, sorted (what an announcement can name).
    """
    uei: str | None
    dollars: Decimal | None
    name: str | None
    names: tuple[str, ...]


def pick_recipient(cands, named=frozenset()) -> tuple[RecipientCandidate, str]:
    """The recipient R-DEC-RECIPIENT picks among `cands`, and its basis.

    Rows with no UEI count only when the award has no UEI at all. (1) The
    largest exact total wins ('obligation', also the basis of an award with
    one recipient); a total that is unknown ranks below every number. (2) In
    a tie for that total, the tied UEIs in `named` — the ones the link's cited
    announcement names — are the only ones left; exactly one left wins
    ('announcement_named'). (3) Otherwise the lowest UEI of those left, or of
    the whole tie when none is named ('uei_tiebreak').
    """
    pool = [c for c in cands if c.uei is not None] or list(cands)
    if not pool:
        raise ValueError("pick_recipient: no recipient candidates")

    def rank(c: RecipientCandidate) -> tuple[bool, Decimal]:
        return (c.dollars is not None,
                c.dollars if c.dollars is not None else Decimal(0))

    top = max(rank(c) for c in pool)
    tied = sorted((c for c in pool if rank(c) == top), key=lambda c: c.uei or "")
    if len(tied) == 1:
        return tied[0], "obligation"
    hits = [c for c in tied if c.uei in named]
    if len(hits) == 1:
        return hits[0], "announcement_named"
    return (hits or tied)[0], "uei_tiebreak"


def recipient_candidates(lake, source: str, keys: tuple[str, ...]
                         ) -> dict[tuple, list[RecipientCandidate]]:
    """Per group of `keys`, every recipient UEI with its exact total and names.

    `source` is a relation with the columns `keys`, uei, name (both already
    NULL for a blank) and ob_exact (the obligation as DECIMAL(38,2): the
    archive carries at most cents, so exact sums make a tie a tie whatever
    the addition order). Ranking happens in pick_recipient, not in SQL, so
    both loaders apply the one rule.
    """
    k = ", ".join(keys)
    n = len(keys)
    groups: dict[tuple, dict] = {}
    for r in lake.execute(
            f"select {k}, uei, sum(ob_exact) from {source} group by {k}, uei"
    ).fetchall():
        groups.setdefault(tuple(r[:n]), {})[r[n]] = [r[n + 1], []]
    for r in lake.execute(
            f"select {k}, uei, name, sum(ob_exact) from {source}"
            f" where name is not null group by {k}, uei, name"
    ).fetchall():
        groups[tuple(r[:n])][r[n]][1].append((r[n + 1], r[n + 2]))

    def best(named: list) -> str | None:
        # the most dollars, then the lower name; unknown dollars rank last
        ranked = sorted(named, key=lambda nd: (nd[1] is None, -(nd[1] or 0), nd[0]))
        return ranked[0][0] if ranked else None

    return {
        key: [RecipientCandidate(uei, dollars, best(named),
                                 tuple(sorted(n for n, _ in named)))
              for uei, (dollars, named) in by_uei.items()]
        for key, by_uei in groups.items()
    }


def ap_awards(ap_codes, contracts_glob: str = CONTRACTS_GLOB, *,
              bases: dict | None = None) -> tuple[list[tuple], AwardMoves]:
    """Every AP-tagged award of the given acquisition programs — (ap code,
    PIID, recipient_name, recipient_uei, funding accounts, total obligation)
    — and the fiscal-year moves applied.

    Read through the fiscal-year move rule (ROADMAP #133; R-DEC-133c,
    fix-round-3 ruling 2026-09-26: "The four remaining raw-archive summers
    (crosswalk.py, load_announcement_links.py, derive_ap_links.py,
    precision_study.py) read through src/govbudget/award_moves.py"): the
    retired copy of a transaction a source correction moved into another
    fiscal year's archive is not summed, as dbt staging drops it. An
    ambiguous duplicate key raises AmbiguousAwardDuplicateError before
    anything is read. With nothing to retire (0 moves on 2026-09-26) the
    rows are exactly the plain archive read this deriver made before.

    THE RECIPIENT (R-DEC-RECIPIENT, 2026-09-26) is picked per (AP code, PIID)
    group over the same rows the obligation is summed from: pick_recipient's
    (1) and (3) — the largest exact total, ties to the lowest UEI — and the
    name from that UEI's own rows, never borrowed (None when they name no
    one; main() skips and counts such an award). Until then the name and the
    UEI were two independent any_value() picks DuckDB resolves by scan order.
    Measured read-only 2026-09-26 over the 25,081 groups main() reads (332
    AP codes): 667 carry more than one UEI and 27 of those tie for the
    largest total; none of the 27 publishes (all low). `bases`, when given,
    is filled with (ap code, PIID) -> the recipient basis.
    """
    codes = ",".join("'" + a.replace("'", "''") + "'" for a in ap_codes)
    where = (f"dod_acquisition_program_code in ({codes})"
             f" and award_id_piid is not null and award_id_piid <> ''")
    lake = duckdb.connect()
    try:
        moves = register_award_rows(lake, [contracts_glob], view="_awards",
                                    require_transaction_keys=True)
        groups = lake.execute(f"""
            select dod_acquisition_program_code ap, award_id_piid,
                   max(federal_accounts_funding_this_award) accts,
                   sum(try_cast(federal_action_obligation as double)) ob
            from _awards
            where {where}
            group by 1, 2
            order by 1, 2
        """).fetchall()
        cands = recipient_candidates(lake, f"""(
            select dod_acquisition_program_code as ap, award_id_piid as piid,
                   nullif(recipient_uei, '') as uei,
                   nullif(recipient_name, '') as name,
                   try_cast(federal_action_obligation as decimal(38, 2)) as ob_exact
            from _awards where {where})""", ("ap", "piid"))
    finally:
        lake.close()
    awards = []
    for ap, piid, accts, ob in groups:
        chosen, basis = pick_recipient(cands[(ap, piid)])
        if bases is not None:
            bases[(ap, piid)] = basis
        awards.append((ap, piid, chosen.name, chosen.uei, accts, ob))
    return awards, moves


def tier_for(matched_count: int) -> tuple[str, str]:
    """Confidence tier + method for an FPDS-tagged award given how many of
    its program's verified lines its funding accounts matched.

    The earlier "exactly one match -> high" tier is withdrawn (2026-09-04):
    a held-out precision study measured it at 34/60 = 56.7%, driven mostly
    by sibling lines sharing one appropriation account. Any account match
    now publishes at medium under the single method 'fpds-ap'; zero matches
    stays low (unpublished, audit-only).
    """
    if matched_count >= 1:
        return "medium", "fpds-ap"
    return "low", "fpds-ap"


def link_rows_for_award(
    *, ap_code, piid, recipient_name, recipient_uei, award_accounts,
    obligation, candidates, line_meta, account_split, recipient_basis=None,
) -> list[tuple]:
    """The budget_line_awards rows ONE AP-tagged award produces.

    recipient_basis  how ap_awards picked the recipient (R-DEC-RECIPIENT;
                'obligation' / 'uei_tiebreak'), stored with each row.
    candidates  the verified J-book lines mapped to this award's AP code.
    line_meta   {(pe_bli, account_or_None): {fed_accounts, org, exhibit}} —
                keyed (pe_bli, None) for an ordinary line and
                (pe_bli, account) once per member of an account-split key.
    account_split  {pe_bli: {account, ...}} for the shared keys an account
                can resolve (ROADMAP #70; see collision_keys).

    A line on a shared key is a candidate for THIS award only when the
    award's own funding accounts name exactly one of its members
    (collision_keys.member_for_award); otherwise the line is dropped for this
    award and the remaining candidates are unaffected. Every other line
    behaves exactly as it did before #70 and carries account=None: for a
    pe_bli that names one program, `resolved` is `candidates` element for
    element and the rationale's `matched/candidates` denominator is
    unchanged.
    """
    resolved: list[tuple[dict, str | None]] = []
    for s in candidates:
        pe_bli = s["pe_bli"]
        members = account_split.get(pe_bli)
        if members is None:
            resolved.append((s, None))
            continue
        account = member_for_award(
            {a: line_meta[(pe_bli, a)]["fed_accounts"] for a in members},
            award_accounts,
        )
        # No account evidence, or evidence naming BOTH programs that share
        # this code: the link would be a claim about a program the award may
        # have nothing to do with. Not published, at any tier.
        if account is not None:
            resolved.append((s, account))

    if not resolved:
        return []

    matched = [
        (s, account) for s, account in resolved
        if line_meta[(s["pe_bli"], account)]["fed_accounts"] & award_accounts
    ]
    conf, method = tier_for(len(matched))
    chosen = matched if matched else resolved  # low: audit trail only
    rows = []
    for s, account in chosen:
        m = line_meta[(s["pe_bli"], account)]
        rationale = (f"FPDS acquisition program {ap_code}; mapping {s['match_kind']}"
                     f" (2-lens verified); account narrowing"
                     f" {len(matched)}/{len(resolved)} lines")
        if account:
            rationale += f"; shared BLI code resolved to account {account}"
        rows.append((s["pe_bli"], m["exhibit"], 2026, m["org"], piid,
                     recipient_name, recipient_uei, obligation, method, conf,
                     len(matched), rationale, account, recipient_basis))
    return rows


def main() -> int:
    dry = "--dry-run" in sys.argv
    res = json.load(open(RESEARCH / "adjudication" / "leg1_result.json"))
    surviving = res["surviving"]

    con = duckdb.connect(str(ROOT / "data" / "duckdb" / "govbudget.duckdb"), read_only=True)
    display = {r[0] for r in con.execute("select distinct pe_bli from dim_programs").fetchall()}
    # Shared BLI codes (E1): dim_programs publishes >1 row for these pe_bli —
    # two different programs share the numeric code (e.g. '3010' is Shipboard
    # Tactical Communications in 1810N AND LPD Flight II in 1611N).
    #
    # ROADMAP #70 (2026-09-04): the ACCOUNT-split keys are link targets again.
    # Sprint E Task E3 already publishes one page per member, so the missing
    # piece was never the URL — it was that a link named the bare code, which
    # names both programs. It now carries the ONE account its own evidence
    # identifies (see link_rows_for_award), and an award whose money names
    # both members or neither links nothing, exactly as before.
    #
    # The ORGANIZATION-split keys ('20', '30', '500' — one account 0300D,
    # different organizations) stay excluded: their members share an account,
    # so account narrowing cannot tell them apart at all. So does any shared
    # key NEITHER axis resolves (none today) — export_site refuses to publish
    # those at all. govbudget.jbooks.collision_keys is the one rule all three
    # consumers apply (ROADMAP #83).
    split_rows = con.execute(
        "select pe_bli, account, org from dim_programs"
        " where pe_bli in (select pe_bli from dim_programs"
        "                  group by pe_bli having count(*) > 1)"
    ).fetchall()
    con.close()
    account_split, org_split, unresolved = partition_split_keys(split_rows)
    display -= org_split | unresolved
    print(f"excluded {len(org_split)} organization-split collision keys from"
          f" link targets: {sorted(org_split)}")
    if unresolved:
        print(f"WARNING: excluded {len(unresolved)} shared key(s) neither"
              f" account nor organization resolves — export_site will refuse"
              f" to publish them: {sorted(unresolved)}")
    print(f"admitted {len(account_split)} account-split collision keys as"
          f" account-qualified link targets: {sorted(account_split)}")

    # per-line account codes + org + exhibit from postgres budget_lines,
    # keyed (pe_bli, None) for an ordinary line and (pe_bli, account) once per
    # member of an account-split key — see link_rows_for_award.
    pg = psycopg.connect(DSN)
    line_meta: dict[tuple[str, str | None], dict] = {}
    for pe_bli in {s["pe_bli"] for s in surviving}:
        rows = pg.execute(
            "select distinct account, organization, exhibit from budget_lines"
            " where pe_bli=%s and account is not null", (pe_bli,),
        ).fetchall()
        for key, own in (
            [((pe_bli, None), rows)]
            + [((pe_bli, a), [r for r in rows if r[0] == a])
               for a in sorted(account_split.get(pe_bli, ()))]
        ):
            orgs = {org for _a, org, _e in own}
            exhibits = {exhibit or "" for _a, _o, exhibit in own}
            line_meta[key] = {
                "fed_accounts": fed_accounts_from_codes(a for a, _, _ in own),
                "orgs": orgs,
                "exhibit": sorted(exhibits)[0] if exhibits else "",
                "org": sorted(orgs)[0] if orgs else "",
            }

    titles = pg.execute("select pe_bli, title from budget_lines where title is not null").fetchall()
    catchall = {pe for pe, t in titles if CATCHALL_TITLE.search(t or "")}
    display -= catchall
    print(f"excluded {len(catchall & set(pe for pe, _ in titles))} catch-all titled lines from link targets")

    import re as _re
    synthetic = _re.compile(r"-L\d+$")
    lines_by_ap: dict[str, list] = defaultdict(list)
    for s in surviving:
        # Synthetic page-line rollup keys ({account}-{org}-L{n}) are export
        # artifacts, not budget lines a reader can visit — linking awards to
        # them produced feed cards with no destination page (gate 8, 2026-09-01).
        if synthetic.search(s["pe_bli"]):
            continue
        if s["pe_bli"] in display:
            lines_by_ap[s["ap_code"]].append(s)
    print(f"verified mappings on display-universe lines: "
          f"{sum(len(v) for v in lines_by_ap.values())} across {len(lines_by_ap)} programs")

    # read through the fiscal-year move rule (R-DEC-133c; ap_awards), one
    # recipient per group by R-DEC-RECIPIENT's (1) and (3)
    bases: dict[tuple[str, str], str] = {}
    awards, moves = ap_awards(list(lines_by_ap), bases=bases)
    print(f"award lake: {moves.summary()}")
    print(f"AP-tagged awards in lake for verified programs: {len(awards)}")
    by_basis: dict[str, int] = defaultdict(int)
    for basis in bases.values():
        by_basis[basis] += 1
    print(f"recipient pick (R-DEC-RECIPIENT): {dict(sorted(by_basis.items()))}"
          f" (obligation: the UEI with the largest total obligation;"
          f" uei_tiebreak: the lowest UEI of a tie for it)")

    out_rows = []
    tiers = defaultdict(int)
    gains = defaultdict(int)          # ROADMAP #70: rows per account-split key
    # (award, shared-code line) pairs the account evidence could not attribute
    # to ONE member — the award's money named both programs, or neither.
    unattributable = defaultdict(int)
    no_recipient_name = 0
    for ap, piid, rname, ruei, accts, ob in awards:
        if rname is None:
            # the picked UEI's rows name no recipient; a name is never
            # borrowed from another UEI's rows (0 on 2026-09-26)
            no_recipient_name += 1
            continue
        award_accounts = set((accts or "").split(";"))
        rows = link_rows_for_award(
            ap_code=ap, piid=piid, recipient_name=rname, recipient_uei=ruei,
            award_accounts=award_accounts, obligation=ob,
            candidates=lines_by_ap[ap], line_meta=line_meta,
            account_split=account_split, recipient_basis=bases[(ap, piid)],
        )
        if rows:
            tiers[rows[0][9]] += 1
        for r in rows:
            if r[12]:
                gains[(r[0], r[12])] += 1
        for s in lines_by_ap[ap]:
            if s["pe_bli"] in account_split and not any(
                r[0] == s["pe_bli"] for r in rows
            ):
                unattributable[s["pe_bli"]] += 1
        out_rows.extend(rows)

    print(f"award-level tier distribution: {dict(tiers)}")
    print(f"link rows to upsert: {len(out_rows)}; awards skipped for no"
          f" recipient name on the picked UEI's rows: {no_recipient_name}")
    print(f"account-split key gains (pe_bli, account): "
          f"{dict(sorted(gains.items()))}")
    print(f"account-split (award, line) pairs no account evidence could"
          f" attribute to one member: {dict(sorted(unattributable.items()))}")
    if dry:
        for r in out_rows[:5]:
            print("  sample:", r[0], r[4], r[9], r[11][:70])
        for r in [x for x in out_rows if x[12]][:5]:
            print("  split-key sample:", r[0], r[12], r[4], r[9])
        return 0

    with pg:
        cur = pg.cursor()
        cur.execute("delete from budget_line_awards where method like 'fpds-ap%'")
        # ROADMAP #70 fix round 1: `account` is not part of the unique key, so
        # the upsert below would happily move a link the announcement route
        # already published from one member's page to the other's. Stop first
        # — the raise aborts this transaction, so the delete above is rolled
        # back too and the corpus is left exactly as it was.
        raise_on_contradictory_accounts(
            stored_member_claims(cur),
            incoming_member_claims(out_rows),
            loader="derive_ap_links",
        )
        # The `where` on the DO UPDATE is a RUN-ORDER guard (final review I3).
        # This loader deletes only its own 'fpds-ap%' rows, so an
        # announcement- or subaward-evidenced link on the same
        # (pe_bli, exhibit, fiscal_year, award_piid) survives the delete and
        # is then hit by the upsert. Without the guard, running this AFTER
        # load_announcement_links.py rewrites an 'announcement+lexicon'/high
        # row to 'fpds-ap'/medium and orphans its award_link_sources row: the
        # citation panel silently loses the article, the tier drops, and no
        # gate can tell (every remaining number is still true). Evidence-graded
        # rows outrank a mechanical derivation regardless of who ran last.
        # Mirrors the same guard in jbooks/crosswalk.py, which restricts its
        # own upsert to the account* family.
        cur.executemany(UPSERT_SQL, out_rows)
    # `with pg:` closes the connection on exit (psycopg3) — count on a fresh one
    with psycopg.connect(DSN) as pg2:
        n = pg2.execute("select confidence, count(*) from budget_line_awards"
                        " where method like 'fpds-ap%' group by 1").fetchall()
        split = pg2.execute(
            "select pe_bli, account, confidence, count(*)"
            " from budget_line_awards where method like 'fpds-ap%'"
            " and account is not null group by 1,2,3 order by 1,2,3"
        ).fetchall()
    print("loaded:", n)
    print("loaded on shared BLI codes:", split)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
