"""SAM.gov Entity Management extract for the published company families.

ROADMAP #10, SAM-extract half.

WHAT THIS IS NOT. It is not an entity-resolution fix and it promotes no
confidence tier. `recipient_parent_name` in USAspending IS the SAM
registration name, so SAM is the ORIGIN of the label defect the curated
display-name seed (spike Option A) corrected, not its cure — see
docs/superpowers/reviews/10-entity-resolution-spike.md §4.

WHAT THIS IS. A bounded enrichment: for each of the 200 published families,
the SAM registration record of the family's DOMINANT member — the one
`dim_entities.dominant_registration_uei` names, i.e. the largest by
obligations with ties broken to the highest registration UEI (the max() runs
over coalesce(parent_uei, recipient_uei), not over the tied member's own
recipient_uei) — giving registration status,
CAGE, UEI, legal business name, business types, primary NAICS and expiration.
`display_name` is taken from rn = 1 and so can name a DIFFERENT tied member;
nothing published may claim the two are the same row (see
`dominant_parent_ueis` below and dbt/models/marts/dim_entities.sql's header).

CREDENTIAL. The Entity Management API takes a SAM.gov *Personal API key*
minted inside a SAM.gov (login.gov) account — NOT an api.data.gov key. Limits
published at https://open.gsa.gov/api/entity-api/ : 10 requests/day for a
non-federal user with no role, 1,000/day with a role. 200 families = 200
requests = ~20 resumable days on the low limit. Account creation is the
owner's action; this module refuses to run without the key rather than
degrade. The key is read from the environment (config loads the gitignored
.env at import); `DATA_GOV_API_KEY` is NEVER consulted, because the Entity
Management API does not accept it — probed 2026-09-05.

SHAPE IS UNVERIFIED AND THE FAILURE IS LOUD. No one on this project has held
a key, and an unauthenticated probe of /entity-information/v3/entities
returned an empty 404. So: the endpoint is overridable (SAM_ENTITY_API_URL,
read at call time — see `sam_entity_api_url`), `preflight` reports which candidate answers and writes the first response's
key names to data/research/sam_entities/preflight.json, and `parse_entity`
raises SamShapeError naming the missing JSON path instead of writing nulls.
Raw bodies are kept under data/raw/sam/ so `sam reparse` can fix a field map
without spending a day's quota.

THE READER LINK IS OURS (ROADMAP #191, 2026-10-01). SAM.gov shows entity
registrations only to signed-in users: sam.gov/entity/<UEI> renders its 404
page and /entities/view/<UEI> redirects to "401 You must be signed in". The
preflight that "verified" the first route recorded 200 from the app shell,
which answers 200 for every path — the LDA lesson again (influence/lda.py:
197-214: an "official_url" nobody opened). So `public_url` is SAM_RECEIPT_URL:
the receipt `export_site` publishes of the fields read from SAM's answer,
which the site gates and the live-asset check open, and preflight probes the
API alone.

ZERO RECORDS IS AN ANSWER, NOT A SHAPE ERROR (chain G step 11, 2026-09-26).
A 200 with exactly `{"entityData": [], "totalRecords": 0}` (`is_no_record`)
is stored, recorded in the manifest, never re-fetched, and yields no row; the
extract carries on to the next family and `reparse` rebuilds the parquet from
every other stored body. It says SAM returned no record for that UEI, not why.

POLITENESS. One request per UEI, >=1s floor between requests, no retry storm:
a 429 or an OVER_RATE_LIMIT/API_KEY_INVALID body stops the run immediately.

DRY RUN. `plan_extract` (and `extract_entities(..., dry_run=True)`) answers
"what would this run do" from stored state alone — no key, no network, no
write. It is the only mode that is runnable on a machine with no credential,
and it is what `govbudget sam extract --dry-run` prints.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import httpx

from govbudget.manifest import ManifestRecord, append_record, load_records

#: Neither version is verified. `preflight` decides and records which answers.
#: These are DEFAULTS only: the environment is read at call time by
#: `sam_entity_api_url` (ROADMAP #10 pre-live seam).
DEFAULT_SAM_ENTITY_API_URL = "https://api.sam.gov/entity-information/v4/entities"
_DOCUMENTED_ENTITY_URLS = (
    "https://api.sam.gov/entity-information/v4/entities",
    "https://api.sam.gov/entity-information/v3/entities",
)
#: The page a READER opens: Fiscal Receipts' receipt of SAM's answer for one
#: UEI, written by export_site to data/site/json/sam/ and served by the site
#: (SAM.gov has no public entity page; module note). Absolute, because the
#: citation panel and copied footnotes link only http(s) inputs.
SAM_RECEIPT_URL = "https://fiscalreceipts.com/json/sam/{uei}.json"
#: The UEI `preflight` probes with (Lockheed Martin's parent registration).
_PROBE_UEI = "ZFN2JJXBLZT3"
_REQUEST_FLOOR_S = 1.0
_USER_AGENT = "fiscalreceipts/1.0 (research; contact: andes.lee444@gmail.com)"
#: Non-federal, no-role daily limit. Overridable; never silently exceeded.
DEFAULT_MAX_REQUESTS = 10
#: Beside manifest.jsonl in the extract's out_dir: one line per `preflight`
#: API request, so `sam_daily` can charge the probes to the day's quota from
#: the shared lake (the report itself is per checkout and tracked in git).
PREFLIGHT_PROBES = "preflight_probes.jsonl"

_PARQUET_COLUMNS = (
    "sam_uei", "legal_business_name", "cage_code", "registration_status",
    "registration_expiration_date", "business_types", "primary_naics",
    "public_url", "source_url", "retrieved_at", "response_sha256",
)

_OWNER_ACTION = (
    "SAM_API_KEY is not set. The SAM.gov Entity Management API does NOT accept "
    "an api.data.gov key (DATA_GOV_API_KEY will not work here). It needs a "
    "SAM.gov *Personal API key*, which only an account holder can mint:\n"
    "  1. sign in at login.gov\n"
    "  2. go to SAM.gov -> Account Details\n"
    "  3. copy the Public/Personal API key\n"
    "  4. paste it into the gitignored GovBudget/.env as SAM_API_KEY=...\n"
    "Limits (https://open.gsa.gov/api/entity-api/): 10 requests/day with no "
    "role, 1,000/day with one. The bounded extract is 200 requests.\n"
    "Nothing was fetched and nothing was written. To see what the run WOULD "
    "do without a key, add --dry-run."
)


def _utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def _now_iso() -> str:
    """This instant, UTC. The ONLY caller is a live fetch — `reparse` reads the
    fetch record instead, so re-parsing never re-dates a stored registration."""
    return _utc_iso(datetime.now(timezone.utc))


class SamAuthError(RuntimeError):
    """No usable credential. Never downgraded to a warning."""


class SamRateLimitError(RuntimeError):
    """The daily quota is spent. Stop; resume tomorrow with the same command."""


class SamShapeError(ValueError):
    """The response (or the preflight report) lacked an expected value."""


class SamUnavailableError(SamShapeError):
    """SAM gave no answer: a timeout, a dropped connection or a 5xx.

    Says nothing about the endpoint version or the response shape — re-run
    later. A SamShapeError subclass so every existing `except SamShapeError`
    (cmd_sam's BLOCKED line among them) still catches it; `sam_daily` catches
    it before SamShapeError and retries it within the day. `uei` names the
    registration the failed request asked for.
    """

    def __init__(self, message: str, *, uei: str | None = None):
        super().__init__(message)
        self.uei = uei


class SamOfflineError(SamUnavailableError):
    """The request never left this machine (DNS or connection failure), so
    it spent none of the day's quota."""


def sam_entity_api_url() -> str:
    """`SAM_ENTITY_API_URL` as the environment says NOW, else the v4 default.

    READ AT CALL TIME (ROADMAP #10 pre-live seam, closed 2026-09-25). It used
    to be bound when this module was imported, so a value set afterwards — a
    wrapper loading .env late, a REPL, a test harness — was silently ignored
    and the run requested the v4 guess. An empty value counts as unset.
    """
    return os.environ.get("SAM_ENTITY_API_URL") or DEFAULT_SAM_ENTITY_API_URL


def candidate_urls() -> tuple[str, ...]:
    """The entity endpoints `preflight` probes, in order, deduplicated: the
    configured one first, then the two versions the API documentation names.
    Two by default; three when SAM_ENTITY_API_URL names a third."""
    return tuple(dict.fromkeys((sam_entity_api_url(), *_DOCUMENTED_ENTITY_URLS)))


def require_api_key(api_key: str | None = None) -> str:
    """The credential, or a refusal that tells the owner exactly what to do.

    Offline and free — this is what `sam extract` calls, NOT `preflight`.
    Calling preflight on every extract run would spend 2 of a 10/day quota
    before the first family was fetched.
    """
    key = api_key or os.environ.get("SAM_API_KEY")
    if not key:
        raise SamAuthError(_OWNER_ACTION)
    return key


def _strip_key(url: str) -> str:
    """The request URL with api_key removed. NOTHING that keeps a key is ever
    written to disk (assumption 2)."""
    parts = urllib.parse.urlsplit(url)
    q = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
         if k.lower() != "api_key"]
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(q)))


def _dig(payload: dict, path: str):
    """payload['a'][0]['b'] for path 'a[0].b'; raises SamShapeError by path."""
    cur = payload
    for token in path.replace("]", "").split("."):
        key, _, idx = token.partition("[")
        try:
            cur = cur[key]
            if idx != "":
                cur = cur[int(idx)]
        except (KeyError, IndexError, TypeError) as e:
            raise SamShapeError(
                f"SAM response has no {path} (stopped at {token!r}): {e}. "
                "The raw body is kept under data/raw/sam/ — fix the path map "
                "in sam_entities.py and re-run `govbudget sam reparse`; do "
                "not re-fetch, the quota is 10/day."
            ) from e
    return cur


def _opt(payload: dict, path: str):
    try:
        return _dig(payload, path)
    except SamShapeError:
        return None


def _canonical_sha256(payload) -> str:
    """sha256 of the CANONICALISED body (sorted keys, compact separators),
    not of the raw bytes: it must be stable across `sam reparse`, which
    re-reads a pretty-printed copy of the same document."""
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def is_no_record(payload) -> bool:
    """True for SAM's answer to a UEI it returns no record for, and ONLY that.

    Chain G step 11 (2026-09-26): RTX's dominant registration UEI
    PPLZG8J3N9D4 came back 200 with exactly `{"entityData": [],
    "totalRecords": 0}`. That is an ANSWER — the Entity API returns no record
    for this UEI to this key — not a shape the path map got wrong, and it
    must neither stop the extract nor block `sam reparse` of every other
    stored body. What it does NOT establish is why: a registration the
    default query does not return (an expired one, or one withheld from
    public view) is indistinguishable here, so nothing may publish it as
    "this company has no SAM registration".

    Strict on purpose, so a shape surprise stays loud: `entityData` must be
    an empty LIST and `totalRecords` the INTEGER 0 (not "0", not False).
    Anything else — a count with no records, records with no count — falls
    through to `parse_entity`, which raises SamShapeError naming the path.
    """
    if not isinstance(payload, dict):
        return False
    total = payload.get("totalRecords")
    # `== []` is True only for an empty list (a {} or () is not equal to it).
    return payload.get("entityData") == [] and type(total) is int and total == 0


def parse_response(payload: dict, *, source_url: str,
                   retrieved_at: str | None = None) -> dict | None:
    """The parquet row one stored response yields, or None when SAM returned
    no record for the UEI (`is_no_record`). The front door `extract_entities`
    and `reparse` both use; everything that is not the exact zero-record
    answer goes to `parse_entity` and its SamShapeError."""
    if is_no_record(payload):
        return None
    return parse_entity(payload, source_url=source_url, retrieved_at=retrieved_at)


def parse_entity(payload: dict, *, source_url: str,
                 retrieved_at: str | None = None) -> dict:
    """One parquet row from one response body. No network, no key.

    `retrieved_at` defaults to now() because the default caller IS the fetch.
    `reparse` always passes the stored fetch time instead — see its docstring.
    A body with no record raises here like any other missing path: it is not
    a row. `parse_response` is the caller-facing door that tells the two
    apart.
    """
    reg = _dig(payload, "entityData[0].entityRegistration")
    uei = reg.get("ueiSAM")
    if not uei:
        raise SamShapeError("entityData[0].entityRegistration.ueiSAM is empty")
    legal = reg.get("legalBusinessName")
    if not legal:
        raise SamShapeError(
            "entityData[0].entityRegistration.legalBusinessName is empty — "
            "that field IS this enrichment; publishing a UEI with no name "
            "would be a line that says nothing. The raw body is kept under "
            "data/raw/sam/; fix the path map and `govbudget sam reparse`."
        )
    types = _opt(payload, "entityData[0].coreData.businessTypes.businessTypeList") or []
    return {
        "sam_uei": uei,
        "legal_business_name": legal,
        "cage_code": reg.get("cageCode") or None,
        "registration_status": reg.get("registrationStatus") or None,
        "registration_expiration_date": reg.get("registrationExpirationDate") or None,
        "business_types": "; ".join(
            t.get("businessTypeDesc", "") for t in types if t.get("businessTypeDesc")
        ) or None,
        "primary_naics": _opt(payload, "entityData[0].assertions.goodsAndServices.primaryNaics"),
        "public_url": SAM_RECEIPT_URL.format(uei=uei),
        "source_url": _strip_key(source_url),
        "retrieved_at": retrieved_at or _now_iso(),
        "response_sha256": _canonical_sha256(payload),
    }


def write_entities_parquet(records, out_dir) -> Path:
    """All-varchar, unique on sam_uei, deterministic order. [] writes a typed
    zero-row file — what a LEFT JOIN from the mart needs (assumption 11)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "entities.parquet"
    by_uei = {r["sam_uei"]: r for r in records}  # last write wins; never fans out
    rows = [tuple(by_uei[k][c] for c in _PARQUET_COLUMNS) for k in sorted(by_uei)]
    con = duckdb.connect()
    try:
        cols = ", ".join(f"{c} varchar" for c in _PARQUET_COLUMNS)
        con.execute(f"create table _s ({cols})")
        if rows:
            ph = ",".join("?" for _ in _PARQUET_COLUMNS)
            con.executemany(f"insert into _s values ({ph})", rows)
        con.execute(f"copy _s to '{path}' (format parquet, compression zstd)")
    finally:
        con.close()
    return path


def require_preflight(report_path) -> dict:
    """The stored preflight report, or a refusal. Reading it costs no quota.

    The report must name the API endpoint that answered; that is all it
    vouches for now. It used to vouch for a reader-facing sam.gov page too,
    and refused the extract unless that page "answered 200" — but SAM.gov's
    app shell answers 200 for every path, and no public entity page exists
    (ROADMAP #191). The reader link is the receipt export_site publishes
    (SAM_RECEIPT_URL), which the site gates and the live check open. A report
    written by the old preflight, `public_url` keys and all, still passes.
    """
    report_path = Path(report_path)
    if not report_path.is_file():
        raise SamShapeError(
            f"no preflight report at {report_path}. Run `govbudget sam "
            "preflight` once (it spends up to "
            f"{len(candidate_urls())} of the day's requests) before "
            "the first extract: it records which API version answers."
        )
    report = json.loads(report_path.read_text())
    if not report.get("endpoint"):
        raise SamShapeError(
            f"preflight recorded endpoint={report.get('endpoint')!r} — it never"
            " saw a SAM entity endpoint answer, so the extract has no version"
            " to request. Re-run `govbudget sam preflight`; if it still finds"
            " none, set SAM_ENTITY_API_URL in GovBudget/.env to the version"
            " https://open.gsa.gov/api/entity-api/ documents today."
        )
    return report


def dominant_parent_ueis(duckdb_path, *, top_n: int = 200) -> list[tuple[str, str]]:
    """[(family_key, uei)] for the published families, in published order.

    The UEI is the DOMINANT member's parent registration — the registration
    dim_entities.dominant_registration_uei is taken from. Measured 2026-09-10:
    200 families, 200 distinct UEIs, 0 null parent_uei. It is NOT necessarily
    the row the page's heading is built from: `display_name` keeps rn = 1, so
    an exact tie can put the name on one member and the registration on
    another, and the /company/ note states the tie-break rather than that
    identity.

    TIES ARE BROKEN THE WAY THE MART BREAKS THEM, not by whichever row a plan
    happens to number 1: `rank()` keeps every tied top member and `max()` picks
    among them, which is exactly `dim_entities`'s
    `max(coalesce(parent_uei, recipient_uei)) filter (where rk = 1)`. Leg e4
    compares the two, so a disagreement would print a stale registration that
    is not stale. 46 families in the lake tie at the top (23 across different
    UEIs) — none in today's published 200, which is why it had to be pinned
    before that changes. `family_key` breaks ties in the top-N cut and in the
    published order for the same reason.
    """
    con = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        return [
            (r[0], r[1])
            for r in con.execute(
                """
                with top as (
                  select family_key, total_obligation from dim_entities
                  order by total_obligation desc nulls last, family_key limit ?
                ),
                ranked as (
                  select x.family_key,
                         coalesce(x.parent_uei, x.recipient_uei) as uei,
                         rank() over (partition by x.family_key
                           order by x.total_obligation desc nulls last) rk
                  from entity_xwalk x join top t using (family_key)
                )
                select r.family_key, max(r.uei)
                from ranked r join top t using (family_key)
                where r.rk = 1
                group by r.family_key, t.total_obligation
                order by t.total_obligation desc, r.family_key
                """,
                [int(top_n)],
            ).fetchall()
            if r[1]
        ]
    finally:
        con.close()


def preflight(*, api_key: str | None = None, client: httpx.Client | None = None,
              probe_uei: str = _PROBE_UEI, report_path=None,
              probes_path=None) -> dict:
    """Refuse early, report exactly what the API answered, and spend at most
    one API request per candidate (`candidate_urls()`: 2 by default, 3 when
    SAM_ENTITY_API_URL names a third).

    Returns (and writes) {"endpoint", "status", "entity_keys", "probed_at",
    "api_requests"}. `probed_at` (when the last probe had its answer) and
    `api_requests` are the evidence; the quota ledger is `probes_path`, which
    gets one line per API request as each is answered or fails — a failed
    preflight included. No reader page is probed: SAM.gov has none (#191).
    Raises SamAuthError when there is no key or every candidate rejects it;
    SamShapeError when every candidate 404s.
    """
    key = require_api_key(api_key)
    candidates = candidate_urls()
    owns_client = client is None
    client = client or httpx.Client(
        headers={"User-Agent": _USER_AGENT}, timeout=60, follow_redirects=True
    )
    report: dict = {"endpoint": None, "status": None, "entity_keys": [],
                    "probed_at": None, "api_requests": 0}
    auth_rejected = False

    def charge(url: str) -> None:
        # Stamped after the request, never before: a quota must err high.
        report["api_requests"] += 1
        report["probed_at"] = _now_iso()
        if probes_path is not None:
            ledger = Path(probes_path)
            ledger.parent.mkdir(parents=True, exist_ok=True)
            with open(ledger, "a") as f:
                f.write(json.dumps({"at": report["probed_at"], "url": url}) + "\n")
    try:
        for url in candidates:
            time.sleep(_REQUEST_FLOOR_S)
            try:
                r = client.get(url, params={"api_key": key, "ueiSAM": probe_uei})
            finally:
                charge(url)
            if r.status_code == 404:
                continue
            if r.status_code in (401, 403) or "API_KEY_INVALID" in r.text:
                auth_rejected = True
                continue
            report["endpoint"] = url
            report["status"] = r.status_code
            try:
                payload = r.json()
                # Key NAMES only — never the body, never the key.
                report["entity_keys"] = sorted(payload["entityData"][0].keys())
            except Exception:
                report["entity_keys"] = []
            break
    finally:
        if owns_client:
            client.close()
    if report["endpoint"] is None:
        if auth_rejected:
            raise SamAuthError(
                "every SAM entity endpoint rejected the key (401/403). A "
                "SAM.gov Personal API key is not an api.data.gov key.\n"
                + _OWNER_ACTION
            )
        raise SamShapeError(
            "every candidate SAM entity endpoint answered 404: "
            f"{candidates}. Set SAM_ENTITY_API_URL to the version "
            "https://open.gsa.gov/api/entity-api/ documents today and re-run."
        )
    if report_path:
        # Atomic: `sam daily` reads this file every hour and must never see
        # it half-written.
        report_path = Path(report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = report_path.with_name(report_path.name + ".tmp")
        tmp.write_text(json.dumps(report, indent=2, sort_keys=True))
        os.replace(tmp, report_path)
    return report


def plan_extract(families, *, raw_dir, max_requests=DEFAULT_MAX_REQUESTS,
                 report_path=None, out_dir=None) -> dict:
    """What the next `sam extract` WOULD do, from stored state alone.

    No key, no network, no write — this is the dry run, and it is the only
    mode that answers a useful question on a machine that has never held a
    SAM.gov credential. `missing` is what the whole extract still owes;
    `would_fetch` is what ONE run at this cap covers; `runs_remaining` is how
    many runs are still needed INCLUDING this one (ceil(missing / cap)), i.e.
    the number of days a 10/day key has left to go.

    THE ENDPOINT IS REPORTED ONLY WHEN IT IS KNOWN. A real run requests
    `require_preflight(...)["endpoint"]`, never `sam_entity_api_url()`, so
    printing the v4 default under the key `endpoint` described a request the
    run would not make. With a stored preflight report (`report_path`, read
    here and nowhere near the network) the plan carries that recorded URL as
    `endpoint`; without one it carries `endpoint_default`, named for what it
    is — a guess nobody has seen answer.
    """
    raw_dir = Path(raw_dir)
    recorded = None
    if report_path is not None and Path(report_path).is_file():
        try:
            recorded = json.loads(Path(report_path).read_text()).get("endpoint")
        except (OSError, ValueError):
            recorded = None
    answered: set[str] = set()
    if out_dir is not None:
        # What `extract_entities` itself skips: any UEI a stored body
        # (single or batched, raw/sam/batches/) already answers.
        from govbudget import sam_batch   # imports this module; import late
        answered = {u for u, a in sam_batch.resolve_answers(
            raw_dir, Path(out_dir), integrity=False).items()
            if sam_batch.question_settled(a)}
    missing = [(fk, uei) for fk, uei in families
               if not (raw_dir / f"{uei}.json").exists() and uei not in answered]
    cap = max(int(max_requests), 0)
    would = min(len(missing), cap)
    return {
        "families": len(families),
        "already_stored": len(families) - len(missing),
        "missing": len(missing),
        "max_requests": cap,
        "would_fetch": would,
        "runs_remaining": (-(-len(missing) // cap)) if cap else None,
        "next_ueis": [uei for _, uei in missing[:would]],
        "next_families": [fk for fk, _ in missing[:would]],
        "complete": not missing,
        "raw_dir": str(raw_dir),
        **({"endpoint": recorded} if recorded
           else {"endpoint_default": sam_entity_api_url()}),
        "has_key": bool(os.environ.get("SAM_API_KEY")),
    }


def plan_first_live_run(families, *, raw_dir, report_path,
                        daily_quota: int = DEFAULT_MAX_REQUESTS,
                        probe_uei: str = _PROBE_UEI, out_dir=None) -> dict:
    """What the FIRST live day will do — preflight, then the bounded extract —
    from stored state alone: no key, no HTTP client, no write.

    The day's quota is shared: preflight spends up to one API request per
    candidate endpoint before the extract fetches anything, so the extract's
    cap is `daily_quota - len(candidate_urls())` (10 - 2 = 8 by default; one
    more is left if the first candidate answers). When a stored report already
    passes `require_preflight` (it names the endpoint that answered),
    preflight is not needed and the extract gets the whole quota. `reason`
    says why preflight IS needed when it is.
    """
    candidates = list(candidate_urls())
    reason = None
    try:
        require_preflight(report_path)
    except SamShapeError as e:
        reason = str(e)
    needed = reason is not None
    pre_max = len(candidates) if needed else 0
    cap = max(int(daily_quota) - pre_max, 0)
    extract = plan_extract(families, raw_dir=raw_dir, max_requests=cap,
                           out_dir=out_dir,
                           report_path=report_path)
    commands = ["uv run python -m govbudget sam preflight"] if needed else []
    commands.append(f"uv run python -m govbudget sam extract --max-requests {cap}")
    return {
        "daily_quota": int(daily_quota),
        "preflight": {
            "needed": needed,
            "reason": reason,
            "candidates": candidates if needed else [],
            "api_requests_max": pre_max,
            "probe_uei": probe_uei if needed else None,
            "report_path": str(report_path),
        },
        "extract": extract,
        "api_requests_max_today": pre_max + extract["would_fetch"],
        "commands": commands,
        "has_key": bool(os.environ.get("SAM_API_KEY")),
    }


def extract_entities(families, *, api_key, out_dir, raw_dir,
                     client=None, max_requests=DEFAULT_MAX_REQUESTS,
                     refresh=False, dry_run=False, endpoint=None):
    """Fetch up to `max_requests` missing registrations; resume-safe.

    `endpoint` is the URL `preflight` RECORDED as answering — cmd_sam passes
    `require_preflight(...)["endpoint"]`, so a probe that found v3 is not
    followed by 10 requests to the v4 guess. It defaults to
    `sam_entity_api_url()` (read now, not at import), and a non-200 raises
    SamShapeError rather than an
    httpx.HTTPStatusError traceback: cmd_sam converts the three Sam* errors
    into a clean BLOCKED line and nothing else. A 4xx names that env var (the
    version may be wrong); a 5xx says SAM is down and to re-run later, because
    a server-side failure is no evidence about the endpoint version.

    families: [(family_key, uei)]. Already-fetched UEIs (a file under
    raw_dir) are skipped unless refresh=True — that is the resume, and it is
    what makes a 10/day quota survivable over 20 days. The parquet is rebuilt
    in a finally block, so a rate-limit or auth stop mid-run still keeps every
    body already paid for. A zero-record answer (`is_no_record`) is stored and
    recorded like any fetch, yields no row, and does not stop the run.

    Returns the parquet Path. With dry_run=True it returns the plan dict from
    `plan_extract` instead, having required no key, made no request and
    written nothing — not even a directory.
    """
    if dry_run:
        return plan_extract(families, raw_dir=raw_dir, max_requests=max_requests,
                            out_dir=out_dir)

    key = require_api_key(api_key)
    endpoint = endpoint or sam_entity_api_url()
    out_dir, raw_dir = Path(out_dir), Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.jsonl"

    owns_client = client is None
    client = client or httpx.Client(
        headers={"User-Agent": _USER_AGENT}, timeout=60, follow_redirects=True
    )
    spent = 0
    result_path: Path | None = None
    from govbudget import sam_batch   # imports this module; import late
    answered = {u for u, a in sam_batch.resolve_answers(
        raw_dir, out_dir, integrity=False).items()
        if sam_batch.question_settled(a)}
    try:
        for family_key, uei in families:
            raw_path = raw_dir / f"{uei}.json"
            if (raw_path.exists() or uei in answered) and not refresh:
                continue
            if spent >= max_requests:
                missing = sum(
                    1 for _, u in families if not (raw_dir / f"{u}.json").exists()
                )
                print(
                    f"sam extract: run cap {max_requests} reached; {missing} "
                    "UEI(s) still missing — re-run the same command tomorrow."
                )
                break
            time.sleep(_REQUEST_FLOOR_S)
            try:
                r = client.get(endpoint, params={"api_key": key, "ueiSAM": uei})
            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                # No connection, so no request reached SAM. Only the
                # exception's CLASS is named, here and below: its text is
                # httpx's, and nothing vouches that it never carries the
                # request URL, which holds the key.
                raise SamOfflineError(
                    f"could not connect to SAM for {uei} at {endpoint} "
                    f"({type(e).__name__}) after {spent} request(s) this run; "
                    "that request was never sent. Re-run the same command "
                    "once online.", uei=uei,
                ) from None
            except httpx.TransportError as e:
                # 2026-09-27: one fetch, then a 60 s ReadTimeout escaped as a
                # traceback.
                raise SamUnavailableError(
                    f"SAM did not answer for {uei} at {endpoint} "
                    f"({type(e).__name__}) after {spent + 1} request(s) this "
                    "run. Re-run the same command later; bodies already "
                    "stored are kept and never re-fetched.", uei=uei,
                ) from None
            spent += 1
            body_text = r.text
            if r.status_code == 429 or "OVER_RATE_LIMIT" in body_text:
                raise SamRateLimitError(
                    f"SAM returned a rate-limit response after {spent} request(s) "
                    f"({r.status_code}). The quota is per DAY (10 without a SAM.gov "
                    "role, 1,000 with one) — stopping rather than retrying. "
                    "Re-run the same command tomorrow; fetched UEIs are skipped."
                )
            if r.status_code in (401, 403) or "API_KEY_INVALID" in body_text:
                raise SamAuthError(
                    f"SAM rejected the key ({r.status_code}). A SAM.gov Personal "
                    "API key is not an api.data.gov key.\n" + _OWNER_ACTION
                )
            if r.status_code >= 500:
                # A server-side failure says nothing about which endpoint
                # version is right, and the advice below would send the
                # operator to spend 2 of a 10/day quota on a preflight that
                # confirms the URL it already had.
                raise SamUnavailableError(
                    f"SAM answered {r.status_code} for {uei} at {endpoint} "
                    f"after {spent} request(s) this run: SAM is down, and this "
                    "is not an endpoint-version problem. Re-run the same "
                    "command later; bodies already stored are kept and never "
                    "re-fetched.", uei=uei,
                )
            if r.status_code != 200:
                raise SamShapeError(
                    f"SAM answered {r.status_code} for {uei} at {endpoint} "
                    f"after {spent} request(s) this run. Re-run `govbudget sam "
                    "preflight`; if it records a different version, set "
                    "SAM_ENTITY_API_URL in GovBudget/.env to that URL. Bodies "
                    "already stored are kept and never re-fetched."
                )
            payload = r.json()
            # Defence in depth: an error body that echoed the key would raise
            # above, so this can only ever be a no-op — but the guarantee is
            # structural rather than circumstantial (assumption 2).
            #
            # If it ever DID fire it would also make `response_sha256`
            # non-reproducible: that hash is taken over the payload as
            # received (parse_entity, canonicalised), while the file on disk
            # would hold the scrubbed text, so `sam reparse` would compute a
            # different digest for the same fetch. Losing a key is the worse
            # outcome, so the scrub stays first — but a sha that will not
            # re-derive is the tell that it fired, and the stored body is then
            # evidence of a leak, not of the response.
            raw_path.write_text(
                json.dumps(payload, indent=2, sort_keys=True).replace(key, "…")
            )
            rec = parse_response(payload, source_url=str(r.request.url))
            # A zero-record answer (`is_no_record`) is recorded exactly like a
            # registration — stored above, so it is never paid for twice, and
            # given a manifest line — but yields no row, and the run carries on
            # to the next family instead of stopping on it (chain G step 11).
            fetched_at = rec["retrieved_at"] if rec else _now_iso()
            append_record(manifest_path, ManifestRecord(
                dataset="sam_entities",
                fiscal_year=None,
                file_name=raw_path.name,
                source_url=(rec["source_url"] if rec
                            else _strip_key(str(r.request.url))),
                sha256=rec["response_sha256"] if rec else _canonical_sha256(payload),
                bytes=len(body_text.encode()),
                downloaded_at=fetched_at,
            ))
            if rec is None:
                print(f"sam extract: {family_key} <- {uei} (SAM returned no "
                      "record for this UEI: 200, totalRecords 0; stored, no row)")
                continue
            print(f"sam extract: {family_key} <- {uei} "
                  f"({rec['registration_status']}, expires "
                  f"{rec['registration_expiration_date']})")
    finally:
        if owns_client:
            client.close()
        try:
            result_path = reparse(raw_dir=raw_dir, out_dir=out_dir)
        except Exception as e:  # never mask the real failure
            print(f"sam extract: parquet rebuild failed after the run: {e}")
    return result_path  # type: ignore[return-value]


def reparse(*, raw_dir, out_dir) -> Path:
    """Rebuild the parquet from stored raw bodies. No network, no quota.

    `retrieved_at` AND `source_url` come from the FETCH RECORD, never from
    this run's clock or today's endpoint constant. `extract_entities` calls
    this in its finally on EVERY run, so a now() stamp would re-date day 1's
    Lockheed row to day 20 of the 20-day bounded extract — and the published
    claim is "this is what SAM said on THAT day" (the exporter's citation
    comment says exactly that). manifest.jsonl is the record; a body with no
    manifest line (hand-dropped, or a manifest lost) falls back to the file's
    own mtime, which is still its fetch and never now().

    THE FALLBACK IS NOT ONLY THE HAND-DROPPED CASE, which is what this
    docstring used to imply. `manifest.jsonl` is read from `out_dir`, so a
    reparse pointed at the wrong output directory finds no records at all and
    dates EVERY row by mtime — a copy or a restore can move those stamps, and
    the run looks exactly like a successful one. So the counts are printed:
    "N row(s) dated from manifest.jsonl, M from file mtime". M above zero on a
    normal rebuild is the symptom, and `sam extract` prints the same line from
    its finally block on every run.

    A stored zero-record answer (`is_no_record`) contributes no row and is
    counted in neither figure; a second line names its UEI(s). Every other
    stored body is still rebuilt — a body that is neither a registration nor
    the exact zero-record answer still raises SamShapeError, as before.

    A stored batch body (raw/sam/batches/, what `sam daily` fetches) counts
    the same way: `sam_batch.rebuild` reads both kinds, so a hand run's
    rebuild never drops what the daily driver stored (and vice versa).
    """
    from govbudget import sam_batch   # imports this module; import late
    return sam_batch.rebuild(Path(raw_dir), Path(out_dir))
