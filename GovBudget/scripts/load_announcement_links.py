"""Load wave-verified announcement-derived (award, PE) links into budget_line_awards.

Evidence chain per link: an official defense.gov daily Contracts announcement
names BOTH the contract number and the program; the program name is one the
PE's own J-book narrative owns (lexicon 'own' entry with verbatim quote);
the pair survived agent triage AND an adversarial refute pass. Published at
'high' with method 'announcement+lexicon'; rationale carries the article
provenance (id/date/url) so the citation panel can point at the source.

Money color guard (2026-09-04): a held-out study measured
'announcement+lexicon' at 54/60 = 90.0%; 3 of 6 refutations were O&M-only
awards attached to RDT&E/procurement lines. Announcement links now
additionally require the award's funding accounts
(federal_accounts_funding_this_award, lake-side) to intersect the target
line's appropriation accounts (budget_lines.account, mapped the same way
derive_ap_links.py does via fed_accounts_from_codes) — see money_color_ok().
A mismatch is skipped, not published, and counted under
skipped['money_color_mismatch']. Subaward links (method 'subaward+lexicon')
are one hop removed (a sub's description, not the award's own funding
account) and keep their existing medium-tier behavior unchanged.

Exclusions mirror derive_ap_links.py: display-universe only, no
organization-split or unresolved collision keys (account-split keys are
admitted with the member their lexicon document names — ROADMAP #70, one
classification rule under #83), no synthetic -L rollup keys.

Source rows (2026-09-04, ROADMAP #71): alongside each published link the
loader writes its evidence STRUCTURALLY to award_link_sources — article_id +
article URL + the archived copy's Wayback URL/timestamp/sha256 + the packet's
match_basis for announcement links, subaward_number for subaward links — so
export_site can mint a first-class kind='announcement' citation instead of
pointing the reader at a generic derived crosswalk row. The rationale prose
is unchanged; this is the same evidence in a shape a citation panel can
render. match_basis is carried through to the card because "the announcement
names this program" is true only for the exact-name basis: for
designator-normalized / llm-alias / llm-designator-variant / llm-description
the announcement did NOT name the program as written, and the card must say
so instead of collapsing every basis into the strongest sentence.

Superseded routes (2026-09-25, ROADMAP #140, decided under the owner's
delegation): the upsert still takes a key another route holds (fpds-ap, a
mechanical account* row) — announcement evidence is the stronger evidence of
THIS program — but the replaced row's method and confidence are recorded in
budget_line_awards.superseded_method / superseded_confidence / superseded_at
(migration 019) and carried across this loader's own rebuild; see write_links.
The 60 moves the 2026-09-19 run made before that existed are recorded by
migration 020 from the evidence it cites in superseded_evidence (R-DEC-140),
and the rebuild carries that column too.

Chain order (R-DEC-LOADER, 2026-09-26): migrate -> THIS ->
scripts/backfill_announcement_link_reviews.py -> jbooks export-facts -> build.
The write refuses while any migration file is unapplied (require_migrations):
020's evidence is the created_at this loader's rebuild erases. export-facts
refuses a review table recorded before this loader's last run.

Usage: uv run python scripts/load_announcement_links.py <wave_result.json>... [--dry-run]

Pass EVERY wave result file on EVERY run. This loader owns every
'announcement+lexicon' and 'subaward+lexicon' row in budget_line_awards (and
every 'announcement'/'subaward' row in award_link_sources): it deletes that
whole partition and rebuilds it from the files on the command line, so a run
given only wave 3 silently unpublishes waves 1 and 2 (ROADMAP #87).
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import psycopg

from govbudget import config
from govbudget.jbooks.collision_keys import (
    member_for_document,
    partition_split_keys,
    raise_on_contradictory_accounts,
)
from derive_ap_links import (
    EVIDENCE_GRADED_METHODS,
    fed_accounts_from_codes,
    incoming_member_claims,
    stored_member_claims,
)

# The methods this loader OWNS — every row carrying one of them is deleted
# and rewritten on each run. It is the same tuple derive_ap_links uses as its
# upsert guard (the deriver refuses to touch exactly what this loader owns);
# tests/test_derive_ap_links_run_order.py pins the two together (ROADMAP #87).
OWNED_METHODS = EVIDENCE_GRADED_METHODS

_OWNED_SQL_LIST = ", ".join(f"'{m}'" for m in OWNED_METHODS)

#: The link upsert, hoisted so tests run the REAL statement
#: (tests/test_load_announcement_links_supersede.py). The insert column list
#: is the 13-column shape derive_ap_links.UPSERT_SQL shares
#: (tests/test_derive_ap_links_run_order.py compares the two).
#:
#: #140 (decided 2026-09-25 under the owner's delegation): the override is
#: KEPT — an announcement link that lands on a key another route holds takes
#: the key — but the replaced row's method and confidence are recorded in
#: superseded_method / superseded_confidence / superseded_at (migration 019)
#: instead of vanishing. A conflict with a row this loader itself wrote earlier
#: in the same run (a pair two waves both produced) is not a move from another
#: route, so an owned row keeps whatever record it already carries.
UPSERT_SQL = f"""insert into budget_line_awards
               (pe_bli, exhibit, fiscal_year, organization, award_piid, recipient_name,
                recipient_uei, matched_obligation, method, confidence, score, rationale,
                account)
               values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               on conflict (pe_bli, exhibit, fiscal_year, award_piid) do update set
                 confidence=excluded.confidence, method=excluded.method,
                 score=excluded.score, rationale=excluded.rationale,
                 matched_obligation=excluded.matched_obligation,
                 account=excluded.account,
                 superseded_method=case
                   when budget_line_awards.method in ({_OWNED_SQL_LIST})
                   then budget_line_awards.superseded_method
                   else budget_line_awards.method end,
                 superseded_confidence=case
                   when budget_line_awards.method in ({_OWNED_SQL_LIST})
                   then budget_line_awards.superseded_confidence
                   else budget_line_awards.confidence end,
                 superseded_at=case
                   when budget_line_awards.method in ({_OWNED_SQL_LIST})
                   then budget_line_awards.superseded_at
                   else now() end"""

SOURCE_UPSERT_SQL = """insert into award_link_sources
               (award_piid, pe_bli, source_kind, source_id, source_url,
                archive_url, archived_at, sha256, match_basis)
               values (%s,%s,%s,%s,%s,%s,%s,%s,%s)
               on conflict (award_piid, pe_bli, source_kind, source_id) do update set
                 source_url=excluded.source_url, archive_url=excluded.archive_url,
                 archived_at=excluded.archived_at, sha256=excluded.sha256,
                 match_basis=excluded.match_basis"""


def _key(row) -> tuple:
    """budget_line_awards' unique key of a 13-column loader row."""
    return (row[0], row[1], int(row[2]), row[4])


def other_routes_on_keys(cur, keys) -> dict[tuple, tuple[str, str]]:
    """key -> (method, confidence) of every row ANOTHER route holds on one of
    `keys` — the rows an incoming link would replace (#140). Read-only; the
    dry run prints it before anything is written."""
    if not keys:
        return {}
    ordered = sorted(keys)
    cur.execute(
        "select b.pe_bli, b.exhibit, b.fiscal_year, b.award_piid,"
        "       b.method, b.confidence"
        "  from budget_line_awards b"
        "  join unnest(%s::text[], %s::text[], %s::int[], %s::text[])"
        "       as t(pe, ex, fy, piid)"
        "    on b.pe_bli = t.pe and b.exhibit = t.ex"
        "   and b.fiscal_year = t.fy and b.award_piid = t.piid"
        " where b.method <> all(%s)",
        ([k[0] for k in ordered], [k[1] for k in ordered],
         [k[2] for k in ordered], [k[3] for k in ordered],
         list(OWNED_METHODS)),
    )
    return {(pe, ex, int(fy), piid): (m, c)
            for pe, ex, fy, piid, m, c in cur.fetchall()}


def write_links(cur, rows: list[tuple], src_rows: list[tuple]) -> dict:
    """Replace this loader's partition with `rows` / `src_rows`, recording
    every route an incoming link replaces (#140). Runs inside the caller's
    transaction and never commits: a raise anywhere rolls the delete back.

    Order matters and is the point:
      1. snapshot the supersession records the owned rows already carry —
         the delete in step 2 would otherwise erase them, and the rows they
         describe no longer exist to conflict with;
      2. delete the owned partition (ROADMAP #87);
      3. the #70 member-attribution guard;
      4. list the other routes' rows the incoming links will replace, then
         upsert (UPSERT_SQL records each one);
      5. put each carried record back on its re-inserted link.

    A carried record whose link is NOT re-inserted is dropped with its row and
    returned in `superseded_dropped_keys`: the replaced route is not restored
    by this loader (re-running derive_ap_links re-derives an fpds-ap row).
    """
    incoming_keys = {_key(r) for r in rows}
    cur.execute(
        "select pe_bli, exhibit, fiscal_year, award_piid, superseded_method,"
        " superseded_confidence, superseded_at, superseded_evidence"
        " from budget_line_awards"
        " where method = any(%s) and superseded_method is not null",
        (list(OWNED_METHODS),),
    )
    # superseded_evidence rides along: a historical record (migration 020,
    # R-DEC-140) must stay a CITED record, not turn into one that looks
    # recorded at the move.
    carried = {(pe, ex, int(fy), piid): (m, c, at, ev)
               for pe, ex, fy, piid, m, c, at, ev in cur.fetchall()}
    cur.execute("select count(*) from budget_line_awards where method = any(%s)",
                (list(OWNED_METHODS),))
    n_stored = cur.fetchone()[0]
    cur.execute("delete from budget_line_awards where method = any(%s)",
                (list(OWNED_METHODS),))
    # ROADMAP #70 fix round 1: same guard as derive_ap_links — a link the
    # FPDS route already attributed to one member of a shared code must not
    # be moved to the other by whichever loader runs last. The raise aborts
    # this transaction, so the delete above is rolled back with it.
    raise_on_contradictory_accounts(
        stored_member_claims(cur),
        incoming_member_claims(rows),
        loader="load_announcement_links",
    )
    replaced = other_routes_on_keys(cur, incoming_keys)
    cur.executemany(UPSERT_SQL, rows)
    n_carried = 0
    dropped = []
    for key, (m, c, at, ev) in sorted(carried.items(), key=lambda kv: kv[0]):
        if key not in incoming_keys:
            dropped.append((key, m, c))
            continue
        cur.execute(
            "update budget_line_awards set superseded_method=%s,"
            " superseded_confidence=%s, superseded_at=%s, superseded_evidence=%s"
            " where pe_bli=%s and exhibit=%s and fiscal_year=%s and award_piid=%s"
            " and method = any(%s) and superseded_method is null",
            (m, c, at, ev, *key, list(OWNED_METHODS)),
        )
        n_carried += cur.rowcount
    # Same delete-then-upsert shape as the links above, scoped to the two
    # kinds this loader owns: a link that stops being published must not
    # leave its source row behind for the citation tier to mint from.
    cur.execute("delete from award_link_sources"
                " where source_kind in ('announcement','subaward')")
    cur.executemany(SOURCE_UPSERT_SQL, src_rows)
    by_route: dict[tuple[str, str], int] = {}
    for m, c in replaced.values():
        by_route[(m, c)] = by_route.get((m, c), 0) + 1
    return {
        "stored": n_stored,
        "links": len(incoming_keys),
        "superseded_new": len(replaced),
        "superseded_new_by_route": dict(sorted(by_route.items())),
        "superseded_carried": n_carried,
        "superseded_dropped": len(dropped),
        "superseded_dropped_keys": dropped,
    }


def supersession_census(cur, incoming_keys, *, owner: str | None = None) -> dict:
    """What this run's rebuild would do to the supersession records the
    owned rows carry (#140, R-DEC-140): how many are stored, how many of those
    are historical (superseded_evidence set — migration 020), and how many the
    rebuild re-inserts (carried) or drops with their link. Read-only; the dry
    run prints it. `owner` narrows to one organization (tests)."""
    sql = ("select pe_bli, exhibit, fiscal_year, award_piid,"
           " superseded_evidence is not null from budget_line_awards"
           " where method = any(%s) and superseded_method is not null")
    args: list = [list(OWNED_METHODS)]
    if owner is not None:
        sql += " and organization = %s"
        args.append(owner)
    cur.execute(sql, args)
    stored = {(pe, ex, int(fy), piid): hist for pe, ex, fy, piid, hist in cur.fetchall()}
    dropped = sorted(k for k in stored if k not in incoming_keys)
    return {"stored": len(stored), "historical": sum(stored.values()),
            "carried": len(stored) - len(dropped), "dropped": len(dropped),
            "dropped_keys": dropped}


def require_migrations(cur, migrations_dir: Path | None = None) -> None:
    """Refuse to write until every migration file is applied (R-DEC-LOADER:
    migrate -> loader -> backfill -> export-facts -> dbt). Migration 019 adds
    the columns this loader writes, and 020 records the 60 moves of
    2026-09-19 from the created_at this loader's rebuild erases — run after
    the loader, it would find no evidence left."""
    folder = Path(migrations_dir) if migrations_dir else ROOT / "migrations"
    cur.execute("select to_regclass('schema_migrations') is not null")
    applied: set[str] = set()
    if cur.fetchone()[0]:
        cur.execute("select name from schema_migrations")
        applied = {r[0] for r in cur.fetchall()}
    missing = sorted(p.name for p in folder.glob("*.sql") if p.name not in applied)
    if missing:
        raise SystemExit(
            f"load_announcement_links: {len(missing)} migration(s) not applied:"
            f" {missing}. Run `python -m govbudget migrate` first (chain order:"
            " migrate -> load_announcement_links -> backfill_announcement_link_reviews"
            " -> jbooks export-facts -> build); nothing written")


def money_color_ok(award_accounts: set[str], line_accounts: set[str]) -> bool:
    """True when the award's funding accounts and the target line's
    appropriation accounts share at least one code, i.e. the award's money
    color is consistent with the line it would be linked to.

    Unknown award accounts (empty set, e.g. older PIIDs with NULL
    federal_accounts_funding_this_award) are treated as unknown, not mismatched
    — we do not skip the link. False only when the award's accounts are known
    and disjoint from the line's accounts (the failure mode: O&M-only awards
    attached to RDT&E/procurement lines).

    If the line's accounts are unknown (empty set), we return False because
    we cannot verify the money color match."""
    # Unknown award accounts = don't skip, we don't know if it's wrong
    if not award_accounts:
        return True
    # Known award accounts but unknown line accounts = skip, can't verify
    if not line_accounts:
        return False
    # Both known: match only if they intersect
    return bool(award_accounts & line_accounts)


# Catch-all budget lines ("Items Less Than $5 Million", "Ordnance Items <$5M",
# "Other Support Aircraft") are aggregates, not programs: a link asserting an
# award executes "Items Less Than $5 Million" is content-free, and the $ in
# the title trips the site's currency-in-prose sweep. Never link targets.
CATCHALL_TITLE = re.compile(r"(less than|under|<)\s*\$|^other\b|^miscellaneous", re.I)

ROOT = Path(__file__).resolve().parents[1]
# The database the exporter reads: config.PG_DSN honours GOVBUDGET_PG_DSN
# and the gitignored .env (tests/test_loader_dsn.py).
DSN = config.PG_DSN
ANN_URL = "https://www.defense.gov/News/Contracts/Contract/Article/{id}/"
MANIFEST = ROOT / "data/raw/announcements/manifest.jsonl"
WAYBACK_URL = "https://web.archive.org/web/{ts}/{url}"


def _packet_value(packet: dict, key: str) -> str | None:
    """A packet field, or None when it is absent/blank/the string 'None'.

    The wave-3 (subaward) packets carry the STRING 'None' for the fields that
    only announcement packets have (article_id, date, contractor) — a bare
    .get() would happily build .../Article/None/ out of it.
    """
    v = packet.get(key)
    if v is None:
        return None
    s = str(v).strip()
    return s if s and s != "None" else None


def collision_account_for(
    pe_bli: str, packet: dict, doc_accounts: dict, members: set[str],
) -> str | None:
    """The ONE member of a shared BLI code this packet's evidence identifies.

    ROADMAP #70. An announcement/subaward link's evidence chain runs through a
    lexicon entry quoting a J-book narrative in a specific document, and the
    Navy files one procurement book per appropriation (SCN_Book.pdf,
    OPN_BA1_Book.pdf, …). `doc_accounts` maps (pe_bli, lexicon_doc) to the
    accounts that document's own non-superseded detail rows carry for this
    pe_bli, so the book names the member.

    Returns None — link not published, exactly as every shared key was before
    #70 — when the packet records no lexicon document, when the document is
    unknown, or when it carries BOTH members' lines and so names neither.
    """
    doc = _packet_value(packet, "lexicon_doc")
    if not doc:
        return None
    return member_for_document(doc_accounts.get((pe_bli, str(doc)), set()), members)


_WAVE_RESULT = re.compile(r"^(wave(\d+))_result")


def provenance_packets(ann_dir: Path, result_paths) -> dict[tuple[str, str], dict]:
    """(piid, pe_bli) → the wave packet a published link's evidence IS.

    A wave<N>_chunks directory holds every packet wave N TRIAGED, not only the
    ones that survived, so the packet has to come from a wave whose
    `surviving` list holds the pair — the earliest such wave, in wave-number
    order, when several do (unchanged from before). Until 2026-09-25 the loader
    kept the first packet of ANY wave, and a pair wave 1 or 2 triaged and
    dropped but wave 4 upheld on another announcement published with the
    dropped packet: its card cited an article the reviewers did not uphold.
    Measured read-only that day, 10 published links took a dropped packet:
    9 of the 1,074 high announcement links (7 from wave-2 packets, 2 from
    wave-1) and 1 subaward+lexicon link built from a wave-3 subaward packet
    for a pair only wave 4 upheld — on the next load it becomes the
    announcement link wave 4 upheld.

    A survivor with no packet in its own wave gets none (the rationale then
    says so and no source row is written, as for any packet-less link) rather
    than a dropped packet from another wave. Each result file is paired with
    the wave<N>_chunks directory of the same N; a result file with no such
    directory is refused.
    """
    waves = []
    for path in result_paths:
        path = Path(path)
        m = _WAVE_RESULT.match(path.name)
        if not m:
            raise SystemExit(
                f"{path.name}: not a wave<N>_result*.json file — cannot find"
                " the packets its surviving pairs were judged on")
        chunks = Path(ann_dir) / f"{m.group(1)}_chunks"
        if not chunks.is_dir():
            raise SystemExit(
                f"{path.name}: no {chunks.name}/ in {ann_dir} — its surviving"
                " pairs would publish with no packet")
        survivors = {(s["piid"], s["pe_bli"])
                     for s in json.loads(path.read_text())["surviving"]}
        waves.append((int(m.group(2)), chunks, survivors))
    prov: dict[tuple[str, str], dict] = {}
    for _, chunks, survivors in sorted(waves, key=lambda w: w[0]):
        for f in sorted(chunks.glob("chunk_*.json")):
            for p in json.loads(f.read_text()):
                key = (p["piid"], p["pe_bli"])
                if key in survivors:
                    prov.setdefault(key, p)
    return prov


def load_snapshot_manifest(path: Path = MANIFEST) -> dict[str, dict]:
    """article_id → {archive_url, archived_at, sha256} for the archived corpus.

    data/raw/announcements/manifest.jsonl is one JSON object per line with keys
    article_id / original_url / snapshot_ts / sha256 / bytes. It records no
    Wayback URL and no timestamp type, so both are derived from snapshot_ts
    (a %Y%m%d%H%M%S Wayback stamp, UTC). Articles with no manifest line are
    simply absent — the caller writes NULL archive fields rather than inventing
    a snapshot that was never taken.
    """
    out: dict[str, dict] = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        m = json.loads(line)
        aid = str(m.get("article_id") or "").strip()
        ts = str(m.get("snapshot_ts") or "").strip()
        url = m.get("original_url")
        if not aid:
            continue
        archived_at = None
        archive_url = None
        if ts and url:
            try:
                archived_at = datetime.strptime(ts, "%Y%m%d%H%M%S").replace(
                    tzinfo=timezone.utc)
            except ValueError:
                archived_at = None
            else:
                archive_url = WAYBACK_URL.format(ts=ts, url=url)
        out[aid] = {
            "archive_url": archive_url,
            "archived_at": archived_at,
            "sha256": m.get("sha256") or None,
        }
    return out


def source_row(piid: str, pe: str, packet: dict, method: str,
               manifest: dict[str, dict]) -> tuple | None:
    """The award_link_sources row for one published link, or None.

    Keyed off the SAME method the link was published with, so source_kind and
    budget_line_awards.method can never disagree. Returns None when the packet
    names no source id (nothing to cite — never a placeholder row), and None
    for any method this loader does not own — the two methods are matched
    explicitly rather than "not subaward, therefore announcement", which would
    have minted a defense.gov article URL for a future third method.

    match_basis records HOW the announcement's program text was matched to the
    PE (exact-name / designator-normalized / llm-alias / …). NULL when the
    packet recorded none — the citation card says "basis not recorded" rather
    than defaulting to the strongest basis.
    """
    basis = _packet_value(packet, "match_basis")
    if method == "subaward+lexicon":
        sub = _packet_value(packet, "subaward_number")
        if not sub:
            return None
        # No canonical public URL for an FSRS subaward record, and no archived
        # copy: the id is the whole citation until one exists.
        return (piid, pe, "subaward", sub, None, None, None, None, basis)
    elif method == "announcement+lexicon":
        aid = _packet_value(packet, "article_id")
        if not aid:
            return None
        snap = manifest.get(aid, {})
        return (piid, pe, "announcement", aid, ANN_URL.format(id=aid),
                snap.get("archive_url"), snap.get("archived_at"),
                snap.get("sha256"), basis)
    return None


def main() -> int:
    dry = "--dry-run" in sys.argv
    paths = [a for a in sys.argv[1:] if not a.startswith("--")]
    surviving = []
    for path in paths:
        surviving.extend(json.load(open(path))["surviving"])

    con = duckdb.connect(str(ROOT / "data/duckdb/govbudget.duckdb"), read_only=True)
    display = {r[0] for r in con.execute("select distinct pe_bli from dim_programs").fetchall()}
    # Shared BLI codes: ROADMAP #70 admits the ACCOUNT-split ones (each link
    # carries the one account its lexicon document identifies — see
    # collision_account_for); the ORGANIZATION-split ones ('20','30','500')
    # share one account and stay excluded, as every shared key was before.
    split_rows = con.execute(
        "select pe_bli, account, org from dim_programs"
        " where pe_bli in (select pe_bli from dim_programs"
        "                  group by pe_bli having count(*) > 1)"
    ).fetchall()
    con.close()
    account_split, org_split, unresolved = partition_split_keys(split_rows)
    if unresolved:
        print(f"WARNING: {len(unresolved)} shared key(s) neither account nor"
              f" organization resolves — skipped as collisions; export_site"
              f" will refuse to publish them: {sorted(unresolved)}")
    synthetic = re.compile(r"-L\d+$")
    with psycopg.connect(DSN) as pg0:
        titles = pg0.execute("select pe_bli, title from budget_lines where title is not null").fetchall()
        # (pe_bli, document_id) -> the accounts that document's own
        # non-superseded detail rows carry for this pe_bli. Only the
        # account-split keys need it; superseded rows are excluded because a
        # withdrawn extraction is not evidence about the current book.
        doc_accounts: dict[tuple[str, str], set[str]] = {}
        if account_split:
            for pe, doc_id, account in pg0.execute(
                "select distinct pe_bli, document_id, account"
                " from budget_line_details"
                " where pe_bli = any(%s) and account is not null"
                " and not superseded",
                (sorted(account_split),),
            ).fetchall():
                doc_accounts.setdefault((pe, str(doc_id)), set()).add(account)
    catchall = {pe for pe, t in titles if CATCHALL_TITLE.search(t or "")}
    display -= catchall

    # article provenance per (piid, pe): the packet of the wave the pair
    # SURVIVED in (provenance_packets), never a triaged-and-dropped one
    prov = provenance_packets(ROOT / "data/research/announcements", paths)

    pairs = []
    skipped = {"not_display_or_catchall": 0, "collision": 0, "synthetic": 0,
               "collision_unresolved": 0, "money_color_mismatch": 0}
    for s in surviving:
        pe, piid = s["pe_bli"], s["piid"]
        account = None
        if synthetic.search(pe): skipped["synthetic"] += 1; continue
        if pe in org_split or pe in unresolved: skipped["collision"] += 1; continue
        if pe in account_split:
            account = collision_account_for(
                pe, prov.get((piid, pe), {}), doc_accounts, account_split[pe])
            if account is None:
                skipped["collision_unresolved"] += 1
                continue
        if pe not in display: skipped["not_display_or_catchall"] += 1; continue
        pairs.append((piid, pe, s.get("reason", ""), account))
    print(f"surviving {len(surviving)} -> publishable {len(pairs)}; skipped {skipped}")

    # lake evidence for recipients/obligations/funding accounts
    piids = sorted({p for p, _, _, _ in pairs})
    lake = duckdb.connect()
    lake.execute("create temp table want(piid varchar)")
    lake.executemany("insert into want values (?)", [(p,) for p in piids])
    ev = {r[0]: r[1:] for r in lake.execute(f"""
        select award_id_piid, any_value(recipient_name), any_value(recipient_uei),
               sum(try_cast(federal_action_obligation as double)),
               max(federal_accounts_funding_this_award)
        from read_parquet('{ROOT}/data/parquet/contracts/fy=*/*.parquet', union_by_name=true)
        where award_id_piid in (select piid from want) group by 1""").fetchall()}
    lake.close()

    # Keyed (pe_bli, account) — account is None for every pe_bli that names
    # one program, and the resolved member's own account for a shared BLI
    # code, so the exhibit/organization stamped on the link and the money
    # color it is checked against are that MEMBER's, never the union of two
    # different programs' appropriations (ROADMAP #70).
    pg = psycopg.connect(DSN)
    line_meta = {}
    line_fed_accounts = {}
    for pe, account in {(pe, account) for _, pe, _, account in pairs}:
        where, args = "pe_bli=%s", [pe]
        if account is not None:
            where, args = "pe_bli=%s and account=%s", [pe, account]
        r = pg.execute(
            f"select min(exhibit), min(organization) from budget_lines where {where}",
            args,
        ).fetchone()
        line_meta[(pe, account)] = (r[0] or "", r[1] or "")
        accounts = pg.execute(
            f"select distinct account from budget_lines"
            f" where {where} and account is not null", args,
        ).fetchall()
        line_fed_accounts[(pe, account)] = fed_accounts_from_codes(
            a for (a,) in accounts)

    # Archived-copy provenance for the citation tier (#71): the article the
    # waves actually read, its Wayback snapshot and that copy's sha256.
    manifest = load_snapshot_manifest()

    rows = []
    src_rows = []
    no_source_id = 0
    no_lake_evidence = 0
    for piid, pe, reason, account in pairs:
        rname, ruei, ob, accts = ev.get(piid, (None, None, None, None))
        if rname is None:
            # the lake does not hold this PIID (formatting variant or pre-FY17
            # award): a link the site cannot back with transactions is not
            # published — counted below, never inserted with a null recipient
            no_lake_evidence += 1
            continue
        p = prov.get((piid, pe), {})
        aid = p.get("article_id")
        rationale = (f"defense.gov contract announcement {aid} ({p.get('date')}): "
                     f"program '{p.get('program_name')}' named for this award "
                     f"[match basis: {p.get('match_basis') or 'not recorded'}]; "
                     f"J-book narrative owns it ({p.get('lexicon_doc')}); "
                     f"triage+adversarial refute survived — {reason[:160]}; "
                     f"url={ANN_URL.format(id=aid)}")
        if account:
            rationale += (f"; shared BLI code resolved to account {account}"
                          f" by that document")
        ex, org = line_meta[(pe, account)]
        # Subaward-derived evidence is one hop removed (a sub's description
        # says what the prime is for): publishes at MEDIUM under its own
        # method so the tier states the evidence species. It keeps its
        # existing behavior — no money-color guard (the subaward description
        # is the evidence, not the award's own funding account).
        if (p.get("match_basis") or "") == "subaward-description-exact":
            method, conf = "subaward+lexicon", "medium"
            rationale = rationale.replace("defense.gov contract announcement None (None)",
                                          f"FSRS subaward {p.get('subaward_number')} ({p.get('subawardee')})")
        else:
            # Money color guard: the award's funding accounts must intersect
            # the target line's appropriation accounts. 3 of 6 refutations in
            # the 2026-09-04 held-out study were O&M-only awards attached to
            # RDT&E/procurement lines — a mismatch here is that failure mode.
            award_accounts = {a for a in (accts or "").split(";") if a.strip()}
            if not money_color_ok(
                award_accounts, line_fed_accounts.get((pe, account), set())
            ):
                skipped["money_color_mismatch"] += 1
                continue
            method, conf = "announcement+lexicon", "high"
        rows.append((pe, ex, 2026, org, piid, rname, ruei, ob, method, conf, 2,
                     rationale, account))
        # Structural provenance for the citation tier — same packet, same
        # method decision, so a published link and its source row agree.
        sr = source_row(piid, pe, p, method, manifest)
        if sr is None:
            no_source_id += 1
        else:
            src_rows.append(sr)
    print(f"rows to upsert: {len(rows)}; distinct PEs: {len({r[0] for r in rows})}; "
          f"skipped for no lake evidence: {no_lake_evidence}; "
          f"skipped for money_color_mismatch: {skipped['money_color_mismatch']}")
    # ROADMAP #70: what the shared BLI codes actually gained this run.
    split_gains = {}
    for r in rows:
        if r[12]:
            split_gains[(r[0], r[12], r[8])] = split_gains.get((r[0], r[12], r[8]), 0) + 1
    print(f"account-split key gains (pe_bli, account, method): "
          f"{dict(sorted(split_gains.items()))}")
    n_archived = sum(1 for r in src_rows if r[5])
    print(f"source rows: {len(src_rows)} "
          f"({sum(1 for r in src_rows if r[2] == 'announcement')} announcement, "
          f"{sum(1 for r in src_rows if r[2] == 'subaward')} subaward); "
          f"with archived copy: {n_archived}; links with no source id: {no_source_id}")
    # The citation card states this in words, so the distribution is worth
    # seeing at load time: an announcement matched by 'llm-description' is a
    # weaker claim than one matched by 'exact-name'.
    basis_counts = {}
    for r in src_rows:
        basis_counts[(r[2], r[8])] = basis_counts.get((r[2], r[8]), 0) + 1
    print("match_basis:", sorted(
        ((k[0], k[1] or "(null)", v) for k, v in basis_counts.items()),
        key=lambda t: (t[0], -t[2])))
    if dry:
        for r in rows[:3]: print("  sample:", r[0], r[4], r[5], "|", r[11][:110])
        for r in [x for x in rows if x[12]][:3]:
            print("  split-key sample:", r[0], r[12], r[4], r[8], r[9])
        for r in src_rows[:3]: print("  source:", r[2], r[3], r[4], "|", (r[7] or "")[:16], "|", r[8])
        # #140: the keys another route holds that this run's links would take
        # (recorded in superseded_* on the real run). Keys an earlier run
        # already took are held by this loader's own rows, so they are not
        # counted here; the real run carries their records across.
        would = other_routes_on_keys(pg.cursor(), {_key(r) for r in rows})
        by_route: dict[tuple[str, str], int] = {}
        for m, c in would.values():
            by_route[(m, c)] = by_route.get((m, c), 0) + 1
        print(f"would replace another route's row on {len(would)} key(s):"
              f" {dict(sorted(by_route.items()))}")
        # R-DEC-LOADER / R-DEC-140: the real run refuses until migrate has
        # run; the dry run says what it would find.
        try:
            require_migrations(pg.cursor())
        except SystemExit as exc:
            print(f"WARNING (the real run refuses): {exc}")
            pg.rollback()
        else:
            census = supersession_census(pg.cursor(), {_key(r) for r in rows})
            print(f"supersession records on owned rows: {census['stored']} stored"
                  f" ({census['historical']} historical, migration 020);"
                  f" the rebuild carries {census['carried']}, drops"
                  f" {census['dropped']} {census['dropped_keys'][:10]}")
        pg.rollback()
        return 0
    with pg:
        cur = pg.cursor()
        require_migrations(cur)
        # Scoped to the two methods this loader owns — and because this loader
        # is the ONLY writer of those methods, the delete inside write_links is
        # effectively a truncate of that partition (ROADMAP #87): every stored
        # announcement and subaward link goes, and only the links rebuilt from
        # the wave files on THIS command line come back. A subset of the wave
        # files therefore unpublishes the rest with every gate green —
        # export_site's missing-source check catches an announcement link with
        # no source row, not a link that simply vanished. The stored and
        # incoming counts are printed side by side so an operator sees
        # "replacing 821 with 300" (--dry-run returns above); the transaction
        # commits when this block exits.
        stats = write_links(cur, rows, src_rows)
        print(f"replaced {stats['stored']} stored {'/'.join(OWNED_METHODS)} links"
              f" with {stats['links']} rebuilt from {len(paths)} wave file(s)")
        # #140: every key an incoming link took from another route, by the
        # route it replaced — recorded in budget_line_awards.superseded_*.
        print(f"links that replaced another route's row on their key:"
              f" {stats['superseded_new']} new this run"
              f" {stats['superseded_new_by_route']};"
              f" {stats['superseded_carried']} earlier record(s) carried across"
              f" the rebuild")
        if stats["superseded_dropped"]:
            print(f"WARNING: {stats['superseded_dropped']} link(s) that had"
                  f" replaced another route are no longer published; the"
                  f" replaced route is NOT restored by this loader (re-run"
                  f" derive_ap_links to re-derive an fpds-ap row):"
                  f" {stats['superseded_dropped_keys'][:10]}")
    with psycopg.connect(DSN) as pg2:
        print("loaded:", pg2.execute("select method, confidence, count(*) from budget_line_awards"
                                     " where method in ('announcement+lexicon','subaward+lexicon') group by 1,2").fetchall())
        print("sources:", pg2.execute("select source_kind, count(*),"
                                      " count(archive_url), count(sha256)"
                                      " from award_link_sources group by 1 order by 1").fetchall())
        print("sources by basis:", pg2.execute(
            "select source_kind, coalesce(match_basis, '(null)'), count(*)"
            " from award_link_sources group by 1,2 order by 1, 3 desc").fetchall())
        print("loaded on shared BLI codes:", pg2.execute(
            "select pe_bli, account, method, confidence, count(*)"
            " from budget_line_awards"
            " where method in ('announcement+lexicon','subaward+lexicon')"
            " and account is not null group by 1,2,3,4 order by 1,2,3").fetchall())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
