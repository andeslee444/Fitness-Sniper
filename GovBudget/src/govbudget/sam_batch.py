"""Batched, three-query SAM answers (ROADMAP #10) — what `sam daily` fetches.

WHY. A plain `?ueiSAM=<one UEI>` request (what `sam extract` sends) spends one
of the key's 10 daily requests on one family and sees one kind of entity.
https://open.gsa.gov/api/entity-api/ (read 2026-09-27): the API "by default,
will return only the entities that are registered"; `samRegistered=No`
returns "entities that are not registered/ID Assigned"; a Personal key reads
Public data, "publicly available entities"; and `ueiSAM` "Allows a single
12-character value or up to 100 values" (`ueiSAM=[A~B]`). Three of the first
eight single answers were empty (RTX, Humana, BAE). So:

  * one request carries up to BATCH_SIZE UEIs. A page holds at most 10
    records ("Size Cannot Exceed 10 Records"), so 10 per request.
  * three queries, asked in order until one finds the UEI:
      registered   the default population, plus integrityInformation, which
                   the docs show bringing an entity that opted out of public
                   display back as a masked record (Example 6), not nothing;
      id_assigned  samRegistered=No: a UEI issued without a registration;
      expired      registrationStatus=E, in case this key's default leaves
                   expired registrations out (documented neither way).
    A UEI absent from all three is `not_public`: no record this key can see.
    Absent means absent from a COMPLETE page (totalRecords == the records
    returned); a UEI missing from an incomplete page is asked again, alone.
    An absence from a `registered` request sent WITHOUT integrityInformation
    (any `sam extract` body, or a mode without it) is `registered_plain`: it
    cannot tell an opted-out entity from none, so while the mode in force can
    ask with integrityInformation, the UEI is asked again that way.
  * every request's whole body is stored under raw/sam/batches/ with its
    key-free URL, and gets ONE manifest line — one line per request, which is
    exactly what `sam_daily`'s quota ledger counts.

MODES. Neither the bracket syntax nor includeSections=integrityInformation is
documented for a Personal key (every example that shows them uses a FOUO or
Public system key), so the request shape is a ladder, most capable first
(MODES). A batch mode is proven by CONTROL_UEI, a known public registration
that rides in its first request: an answer without it means SAM did not
honour the batch, the next mode is tried, and — because the control is
recorded in the stored body — `resolve_answers` never trusts that request's
absences. The last rung is the plain single-UEI request the first live day
proved (2026-09-26).
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import duckdb
import httpx

from govbudget import sam_entities as sam
from govbudget.manifest import ManifestRecord, append_record, load_records

BATCH_SIZE = 10
STAGES = ("registered", "id_assigned", "expired")
MODES = ("batch+integrity", "batch", "single+integrity", "single")
#: Lockheed Martin's parent registration: registered, public, answered on
#: 2026-09-26. It rides in every request that tries to prove a batch mode.
CONTROL_UEI = "ZFN2JJXBLZT3"
#: Boeing's (2026-09-26, same): the second UEI of a proof with nothing else
#: to ask, so a proof is always a real bracketed request, never one UEI.
CONTROL_PAIR = "NU2UC8MX6NK1"
BATCH_DIR = "batches"

_SECTIONS = {
    "registered": "entityRegistration,coreData,assertions,integrityInformation",
    "id_assigned": "entityRegistration,coreData,integrityInformation",
    "expired": "entityRegistration,coreData,assertions,integrityInformation",
}
_STAGE_PARAM = {"registered": "", "id_assigned": "&samRegistered=No",
                "expired": "&registrationStatus=E"}
_UEI_RE = re.compile(r"^[A-Z0-9]{12}$")
_KIND_RANK = {"registered": 0, "id_assigned": 1, "opted_out": 2}

_ANSWER_COLUMNS = (
    "sam_uei", "kind", "legal_business_name", "registration_status",
    "stages_absent", "source_url", "retrieved_at", "response_sha256",
)


class SamQueryRejectedError(sam.SamShapeError):
    """HTTP 400: SAM refused the request's shape (a mode it does not honour
    for this key, or a malformed query)."""


class SamStoredBodyError(sam.SamShapeError):
    """A 200 answer that was stored (and has its manifest line — the request
    is already on the quota ledger) but does not read. Names the file; the
    fix is the owner's, then `govbudget sam reparse`."""

    def __init__(self, message: str, *, file: str):
        super().__init__(f"{file}: {message}")
        self.file = file


@dataclass
class BatchResult:
    stage: str
    mode: str
    asked: list[str]
    found: dict[str, dict] = field(default_factory=dict)
    absent: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
    control: str | None = None
    #: True: SAM honoured the batch (it answered with an asked UEI); False: a
    #: complete page held none of them; None: no proof was attempted, or the
    #: page was too full to tell.
    honoured: bool | None = None
    file_name: str = ""


def build_url(endpoint: str, ueis, *, stage: str, mode: str) -> str:
    """The request URL WITHOUT the key, literal brackets and commas as the
    docs write them (httpx `params=` would percent-encode both, which the
    docs never show SAM accepting)."""
    ueis = list(ueis)
    if not ueis or len(ueis) > 100:
        raise ValueError(f"a SAM request takes 1-100 UEIs, not {len(ueis)}")
    for u in ueis:
        if not _UEI_RE.match(u or ""):
            raise ValueError(f"not a 12-character UEI: {u!r}")
    if mode.startswith("single") and len(ueis) != 1:
        raise ValueError(f"mode {mode} sends one UEI per request")
    uei_param = ueis[0] if len(ueis) == 1 else "[" + "~".join(ueis) + "]"
    query = f"ueiSAM={uei_param}{_STAGE_PARAM[stage]}"
    if mode.endswith("+integrity"):
        query += f"&includeSections={_SECTIONS[stage]}"
    return f"{endpoint}?{query}"


def classify_record(rec: dict) -> tuple[str | None, str, dict]:
    """(uei, kind, fields) for one entityData element. Never raises on the
    three documented shapes: a registration, an ID-only entity
    (samRegistered "No" — its registrationStatus may still read "Active",
    docs Example 2, so it is never taken as one), and the masked record of
    an entity that opted out of public display (entityRegistration is the
    sentence itself, docs Example 6; name and UEI from entitySummary)."""
    if not isinstance(rec, dict):
        raise sam.SamShapeError(f"entityData holds a {type(rec).__name__}, "
                                "not a record")
    reg = rec.get("entityRegistration")
    integrity = rec.get("integrityInformation")
    summary = (integrity.get("entitySummary")
               if isinstance(integrity, dict) else None)
    summary = summary if isinstance(summary, dict) else {}
    if isinstance(reg, str):
        return (summary.get("ueiSAM"), "opted_out",
                {"legal_business_name": summary.get("legalBusinessName"),
                 "registration_status": None})
    if not isinstance(reg, dict):
        raise sam.SamShapeError("entityData[].entityRegistration is neither a "
                                "record nor the opted-out sentence")
    kind = ("id_assigned" if str(reg.get("samRegistered", "")).strip().lower()
            == "no" else "registered")
    return (reg.get("ueiSAM"), kind,
            {"legal_business_name": reg.get("legalBusinessName"),
             "registration_status": reg.get("registrationStatus")})


def _best(items: list[tuple[str, dict, dict]]) -> tuple[str, dict, dict]:
    """One answer per UEI when SAM returns duplicates ("A UEI can return
    multiple (duplicate) registration records"): a registration over an
    ID-only or masked record, an Active one over any other, then the latest
    expiration date."""
    def rank(item):
        return (_KIND_RANK[item[0]], item[1].get("registration_status") != "Active")

    def expires(item):
        reg = item[2].get("entityRegistration")
        return (reg.get("registrationExpirationDate") or "") if isinstance(reg, dict) else ""
    top = min(rank(i) for i in items)
    return max((i for i in items if rank(i) == top), key=expires)


def _read_batch(payload: dict, asked: list[str], control: str | None):
    """found / absent / unresolved from one stored response. Raises
    SamShapeError on a body that is not the documented envelope."""
    data, total = payload.get("entityData"), payload.get("totalRecords")
    if not isinstance(data, list) or type(total) is not int:
        raise sam.SamShapeError("SAM response lacks an entityData list and an "
                                "integer totalRecords")
    grouped: dict[str, list] = {}
    unreadable_uei = False
    for rec in data:
        uei, kind, fields = classify_record(rec)
        if uei:
            grouped.setdefault(uei, []).append((kind, fields, rec))
        else:
            unreadable_uei = True
    found = {u: dict(zip(("kind", "fields", "record"), _best(v)))
             for u, v in grouped.items()}
    # A record whose UEI does not read might be the answer to any asked UEI:
    # such a page proves no absence.
    complete = total == len(data) and not unreadable_uei
    batch = len(asked) > 1
    # A batch was honoured if SAM answered with ANY asked UEI — the control or
    # a family. Only a COMPLETE page with none of them says it was not; a
    # full page (duplicates) says nothing either way.
    hit = any(u in found for u in asked)
    honoured = (True if hit else False if complete else None) if control else None
    trusted = not batch or hit or control is None
    missing = [u for u in asked if u not in found]
    absent = missing if (complete and trusted and (hit or not control)) else []
    unresolved = missing if (not complete and trusted) else []
    return found, absent, unresolved, honoured


def fetch_batch(client: httpx.Client, *, api_key: str, endpoint: str,
                ueis, stage: str, mode: str, raw_dir: Path, out_dir: Path,
                control: str | None = None,
                clock: Callable[[], datetime] | None = None) -> BatchResult:
    """ONE request: send it, store the whole body (key scrubbed) and its
    manifest line, then read it. The body is stored before it is read, so a
    request that was paid for is never lost to a parser surprise."""
    clock = clock or (lambda: datetime.now(timezone.utc))
    asked = list(ueis) + ([control] if control and control not in ueis else [])
    if control and len(asked) < 2:
        asked.insert(0, CONTROL_PAIR if control != CONTROL_PAIR else CONTROL_UEI)
    url = build_url(endpoint, asked, stage=stage, mode=mode)
    one = asked[0] if len(asked) == 1 else None
    time.sleep(sam._REQUEST_FLOOR_S)
    try:
        r = client.get(url.replace("?", f"?api_key={api_key}&", 1))
    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        raise sam.SamOfflineError(
            f"could not connect to SAM ({type(e).__name__}); the {stage} "
            f"request for {len(asked)} UEI(s) was never sent", uei=one) from None
    except httpx.TransportError as e:
        raise sam.SamUnavailableError(
            f"SAM did not answer the {stage} request for {len(asked)} UEI(s) "
            f"({type(e).__name__})", uei=one) from None
    body = r.text
    if r.status_code == 429 or "OVER_RATE_LIMIT" in body:
        raise sam.SamRateLimitError(
            f"SAM returned a rate-limit response ({r.status_code}) — the day's "
            "quota is spent")
    if r.status_code in (401, 403) or "API_KEY_INVALID" in body:
        raise sam.SamAuthError(f"SAM rejected the key ({r.status_code}).")
    if r.status_code >= 500:
        raise sam.SamUnavailableError(
            f"SAM answered {r.status_code} to the {stage} request for "
            f"{len(asked)} UEI(s): SAM is down", uei=one)
    if r.status_code == 400:
        raise SamQueryRejectedError(
            f"SAM refused the {mode} {stage} request (400): "
            f"{body.replace(api_key, '…')[:300]}")
    if r.status_code != 200:
        raise sam.SamShapeError(f"SAM answered {r.status_code} to the {stage} "
                                "request")
    retrieved = sam._utc_iso(clock())
    try:
        payload = r.json()
    except ValueError:
        payload = None
    sha = sam._canonical_sha256(payload if payload is not None else body)
    batch_dir = Path(raw_dir) / BATCH_DIR
    batch_dir.mkdir(parents=True, exist_ok=True)
    # Named by time, stage and the REQUEST (two empty answers share a body
    # sha); a clash within the second gets a suffix, never an overwrite.
    stem = (f"{retrieved.replace(':', '').replace('+0000', 'Z')}-{stage}-"
            f"{sam._canonical_sha256(url)[:10]}")
    name, n = f"{stem}.json", 1
    while (batch_dir / name).exists():
        n += 1
        name = f"{stem}-{n}.json"
    record = {"request_url": url, "stage": stage, "mode": mode,
              "integrity": mode.endswith("+integrity"),
              "asked": asked, "control": control, "retrieved_at": retrieved,
              "http_status": r.status_code, "response": payload}
    if payload is None:                 # paid for: kept even when it is not JSON
        record["response_text"] = body
    (batch_dir / name).write_text(
        json.dumps(record, indent=2, sort_keys=True).replace(api_key, "…"))
    append_record(Path(out_dir) / "manifest.jsonl", ManifestRecord(
        dataset="sam_entities", fiscal_year=None,
        file_name=f"{BATCH_DIR}/{name}", source_url=url, sha256=sha,
        bytes=len(body.encode()), downloaded_at=retrieved))
    try:
        if payload is None:
            raise sam.SamShapeError("SAM answered 200 with a body that is not JSON")
        found, absent, unresolved, honoured = _read_batch(payload, asked, control)
    except sam.SamShapeError as e:
        raise SamStoredBodyError(str(e), file=f"{BATCH_DIR}/{name}") from None
    return BatchResult(stage=stage, mode=mode, asked=asked, found=found,
                       absent=absent, unresolved=unresolved, control=control,
                       honoured=honoured, file_name=name)


def resolve_answers(raw_dir: Path, out_dir: Path, *,
                    integrity: bool = True) -> dict[str, dict]:
    """Every UEI's answer so far, rebuilt from stored bodies alone.

    {uei: {"kind": registered | id_assigned | opted_out | not_public |
    pending, "next_stage", "unresolved", "stages_absent", and for a found
    answer "record", "fields", "source_url", "retrieved_at",
    "response_sha256", "dated_by"}}. `integrity` is whether the mode in
    force asks with integrityInformation: if it does, a `registered_plain`
    absence does not settle the `registered` stage (see the module note).
    """
    raw_dir, out_dir = Path(raw_dir), Path(out_dir)
    dated = {r.file_name: r for r in load_records(out_dir / "manifest.jsonl")}
    found: dict[str, list] = {}
    absent: dict[str, set] = {}
    unresolved: dict[str, int] = {}
    unreadable: dict[str, str] = {}      # uei -> "file: why"

    for p in sorted(raw_dir.glob("*.json")):
        try:
            payload = json.loads(p.read_text())
            f, a, _u, _c = _read_batch(payload, [p.stem], None)
        except (ValueError, sam.SamShapeError) as e:
            unreadable[p.stem] = f"{p.name}: {e}"
            continue
        rec = dated.get(p.name)
        when = rec.downloaded_at if rec else sam._utc_iso(
            datetime.fromtimestamp(p.stat().st_mtime, timezone.utc))
        src = (rec.source_url if rec
               else f"{sam.sam_entity_api_url()}?ueiSAM={p.stem}")
        for uei, ans in f.items():
            found.setdefault(uei, []).append(
                {**ans, "source_url": src, "retrieved_at": when,
                 "response_sha256": sam._canonical_sha256(payload),
                 "dated_by": "manifest" if rec else "mtime"})
        for uei in a:
            absent.setdefault(uei, set()).add("registered_plain")
    batch_dir = raw_dir / BATCH_DIR
    for p in sorted(batch_dir.glob("*.json")) if batch_dir.is_dir() else []:
        stored = None
        try:
            stored = json.loads(p.read_text())
            payload = stored["response"]
            if payload is None:
                raise sam.SamShapeError("the stored answer is not JSON")
            f, a, u, _c = _read_batch(payload, stored["asked"],
                                      stored.get("control"))
        except (ValueError, KeyError, TypeError, AttributeError,
                sam.SamShapeError) as e:
            asked = stored.get("asked") if isinstance(stored, dict) else None
            for uei in asked if isinstance(asked, list) else []:
                unreadable[uei] = f"{BATCH_DIR}/{p.name}: {e}"
            continue
        for uei, ans in f.items():
            found.setdefault(uei, []).append(
                {**ans, "source_url": stored["request_url"],
                 "retrieved_at": stored["retrieved_at"],
                 "response_sha256": sam._canonical_sha256(payload),
                 "dated_by": "manifest"})
        stage = stored["stage"]
        if stage == "registered" and not stored.get("integrity"):
            stage = "registered_plain"
        for uei in a:
            absent.setdefault(uei, set()).add(stage)
        for uei in u:
            unresolved[uei] = unresolved.get(uei, 0) + 1

    order = ("registered_plain",) + STAGES
    answers: dict[str, dict] = {}
    for uei, why in unreadable.items():
        if uei not in found:
            # Not re-asked (the body is paid for and kept) and not absent: the
            # owner fixes the reader, then `sam reparse` settles it.
            answers[uei] = {"kind": "unreadable", "why": why, "next_stage": None,
                            "stages_absent": [], "unresolved": 0}
    for uei in (set(found) | set(absent) | set(unresolved)) - (set(unreadable) - set(found)):
        seen = absent.get(uei, set())
        stages_absent = sorted(seen, key=order.index)
        settled = set(seen)
        if not integrity and "registered_plain" in seen:
            settled.add("registered")
        if uei in found:
            latest = max(found[uei], key=lambda a: a["retrieved_at"])
            answers[uei] = {**latest, "stages_absent": stages_absent,
                            "next_stage": None,
                            "unresolved": unresolved.get(uei, 0)}
            continue
        todo = [s for s in STAGES if s not in settled]
        answers[uei] = {"kind": "not_public" if not todo else "pending",
                        "next_stage": todo[0] if todo else None,
                        "stages_absent": stages_absent,
                        "unresolved": unresolved.get(uei, 0)}
    return answers


def pending(families, answers: dict) -> list[tuple[str, str]]:
    """The families whose answer is still owed, in the order given."""
    return [f for f in families
            if answers.get(f[1], {"kind": "pending"})["kind"] == "pending"]


def next_stage(uei: str, answers: dict) -> str:
    return (answers.get(uei) or {}).get("next_stage") or STAGES[0]


def rebuild(raw_dir: Path, out_dir: Path, *, integrity: bool | None = None) -> Path:
    """entities.parquet (registrations only — the published rows, schema
    unchanged) and answers.parquet (every answer, every kind), from stored
    bodies. No network, no quota. `sam_entities.reparse` is this function;
    the first two lines it prints are the ones reparse always printed."""
    raw_dir, out_dir = Path(raw_dir), Path(out_dir)
    if integrity is None:
        integrity = mode_in_force(out_dir).endswith("+integrity")
    answers = resolve_answers(raw_dir, out_dir, integrity=integrity)
    rows, counts, by_mtime = [], {}, 0
    for uei, ans in sorted(answers.items()):
        counts[ans["kind"]] = counts.get(ans["kind"], 0) + 1
        if ans["kind"] != "registered":
            continue
        rows.append(sam.parse_entity(
            {"entityData": [ans["record"]]}, source_url=ans["source_url"],
            retrieved_at=ans["retrieved_at"])
            # The request as it was sent (key-free), not re-encoded.
            | {"response_sha256": ans["response_sha256"],
               "source_url": ans["source_url"]})
        by_mtime += ans.get("dated_by") == "mtime"
    print(f"sam reparse: {len(rows) - by_mtime} row(s) dated from "
          f"manifest.jsonl, {by_mtime} from file mtime")
    empty = sorted(u for u, a in answers.items() if a["kind"] != "registered"
                   and a["stages_absent"] == ["registered_plain"])
    if empty:
        print(f"sam reparse: {len(empty)} stored answer(s) where SAM returned"
              " no record for the UEI (200, totalRecords 0; no row written): "
              + ", ".join(empty))
    print("sam reparse: answers by kind — " + ", ".join(
        f"{k} {n}" for k, n in sorted(counts.items())))
    _write_answers_parquet(answers, out_dir)
    return sam.write_entities_parquet(rows, out_dir)


def mode_in_force(out_dir: Path) -> str:
    """The request mode `sam daily` last recorded (its state beside the
    manifest), so every reader settles answers the way the driver does."""
    try:
        state = json.loads((Path(out_dir) / "daily" / "state.json").read_text())
        return state.get("mode") or MODES[0]
    except (OSError, ValueError, AttributeError):
        return MODES[0]


def question_settled(answer: dict | None) -> bool:
    """True once a plain `?ueiSAM=` request (what `sam extract` sends) could
    tell us nothing new about this UEI: it was found, or the registered
    query — with or without integrityInformation — already came back empty."""
    if not answer:
        return False
    return answer["kind"] != "pending" or bool(
        {"registered", "registered_plain"} & set(answer.get("stages_absent") or []))


def _write_answers_parquet(answers: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "answers.parquet"
    rows = []
    for uei, a in sorted(answers.items()):
        fields = a.get("fields") or {}
        rows.append((uei, a["kind"], fields.get("legal_business_name"),
                     fields.get("registration_status"),
                     ",".join(a.get("stages_absent") or []) or None,
                     a.get("source_url"), a.get("retrieved_at"),
                     a.get("response_sha256")))
    con = duckdb.connect()
    try:
        cols = ", ".join(f"{c} varchar" for c in _ANSWER_COLUMNS)
        con.execute(f"create table _a ({cols})")
        if rows:
            con.executemany(
                f"insert into _a values ({','.join('?' for _ in _ANSWER_COLUMNS)})",
                rows)
        con.execute(f"copy _a to '{path}' (format parquet, compression zstd)")
    finally:
        con.close()
    return path
