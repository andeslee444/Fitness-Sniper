"""TDD tests for govbudget.sam_entities (ROADMAP #10, SAM-extract half).

No live network. Requests go through httpx.MockTransport; response shapes
come from tests/fixtures/sam/*.json.

FIXTURE PROVENANCE: entity_lockheed.json is TYPED FROM THE PUBLISHED API
DOCUMENTATION (https://open.gsa.gov/api/entity-api/), not recorded from a
live call — nobody on this project has held a SAM.gov key. `sam preflight`
writes the first real response's key names to
data/research/sam_entities/preflight.json; whoever runs it first must
replace this fixture with the real body (minus the api_key) and re-run this
file. The parser raises SamShapeError rather than emitting nulls precisely
so that a shape surprise is loud instead of silent.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import httpx
import pytest

from govbudget.manifest import ManifestRecord, append_record
from govbudget.sam_entities import (
    DEFAULT_SAM_ENTITY_API_URL,
    DEFAULT_SAM_PUBLIC_ENTITY_URL,
    SamAuthError,
    SamRateLimitError,
    SamShapeError,
    extract_entities,
    parse_entity,
    plan_extract,
    preflight,
    reparse,
    require_api_key,
    require_preflight,
    write_entities_parquet,
)

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "sam"
LOCKHEED = json.loads((FIXTURE_DIR / "entity_lockheed.json").read_text())


def test_require_api_key_without_a_key_raises_with_the_owner_action(monkeypatch):
    monkeypatch.delenv("SAM_API_KEY", raising=False)
    with pytest.raises(SamAuthError) as exc:
        require_api_key()
    msg = str(exc.value)
    assert "SAM_API_KEY" in msg
    assert "login.gov" in msg
    assert "api.data.gov" in msg  # names the key that does NOT work
    assert "10 requests/day" in msg


def test_parse_entity_reads_every_published_field():
    rec = parse_entity(LOCKHEED, source_url="https://api.sam.gov/x?ueiSAM=ZFN2JJXBLZT3")
    assert rec["sam_uei"] == "ZFN2JJXBLZT3"
    assert rec["legal_business_name"] == "LOCKHEED MARTIN CORPORATION"
    assert rec["cage_code"] == "98897"
    assert rec["registration_status"] == "Active"
    assert rec["registration_expiration_date"] == "2026-05-14"
    assert rec["primary_naics"] == "336411"
    # business types render as one reader-legible varchar, order preserved.
    assert rec["business_types"] == "For Profit Organization; Manufacturer of Goods"
    assert rec["public_url"] == "https://sam.gov/entity/ZFN2JJXBLZT3"


def test_parse_entity_raises_naming_the_missing_path_rather_than_nulling():
    broken = {"totalRecords": 1, "entityData": [{"coreData": {}}]}
    with pytest.raises(SamShapeError) as exc:
        parse_entity(broken, source_url="https://api.sam.gov/x")
    assert "entityData[0].entityRegistration" in str(exc.value)


def test_parse_entity_raises_when_the_legal_name_is_missing():
    """The legal business name is the field the whole enrichment exists for.
    A silent None would publish 'SAM.gov registration: <uei>.' and nothing."""
    payload = json.loads(json.dumps(LOCKHEED))
    del payload["entityData"][0]["entityRegistration"]["legalBusinessName"]
    with pytest.raises(SamShapeError) as exc:
        parse_entity(payload, source_url="https://api.sam.gov/x")
    assert "legalBusinessName" in str(exc.value)


def test_parse_entity_tolerates_a_public_key_view_missing_assertions():
    """A no-role key may not be served the assertions section. Absent is
    absent — never invented, never a crash."""
    payload = json.loads(json.dumps(LOCKHEED))
    del payload["entityData"][0]["assertions"]
    rec = parse_entity(payload, source_url="https://api.sam.gov/x")
    assert rec["primary_naics"] is None
    assert rec["registration_status"] == "Active"


def test_require_preflight_refuses_an_unverified_reader_url(tmp_path):
    """Assumption 4: no citation links to a page nobody has opened."""
    report = tmp_path / "preflight.json"
    with pytest.raises(SamShapeError):
        require_preflight(report)
    report.write_text(json.dumps({"endpoint": "https://x", "status": 200,
                                  "public_url": DEFAULT_SAM_PUBLIC_ENTITY_URL,
                                  "public_url_status": 404}))
    with pytest.raises(SamShapeError) as exc:
        require_preflight(report)
    assert "public_url_status" in str(exc.value)
    report.write_text(json.dumps({"endpoint": "https://x", "status": 200,
                                  "public_url": DEFAULT_SAM_PUBLIC_ENTITY_URL,
                                  "public_url_status": 200}))
    assert require_preflight(report)["public_url_status"] == 200


def test_extract_stops_dead_on_a_rate_limit_body(tmp_path, monkeypatch):
    monkeypatch.setattr("govbudget.sam_entities._REQUEST_FLOOR_S", 0)
    body = json.loads((FIXTURE_DIR / "entity_over_rate_limit.json").read_text())
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(429, json=body)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(SamRateLimitError):
            extract_entities(
                [("LOCKHEED MARTIN", "ZFN2JJXBLZT3"), ("BOEING", "NU2UC8MX6NK1")],
                api_key="k",
                out_dir=tmp_path / "parquet",
                raw_dir=tmp_path / "raw",
                client=client,
                max_requests=10,
            )
    assert calls["n"] == 1, "a 429 must stop the run, not retry into tomorrow"


def test_a_stopped_run_still_leaves_a_rebuilt_parquet(tmp_path, monkeypatch):
    """The quota is 10/day. A run that dies on request 2 must not throw away
    the body it already paid for."""
    monkeypatch.setattr("govbudget.sam_entities._REQUEST_FLOOR_S", 0)
    seen = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["n"] += 1
        if seen["n"] > 1:
            return httpx.Response(429, json={"error": {"code": "OVER_RATE_LIMIT"}})
        return httpx.Response(200, json=LOCKHEED)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(SamRateLimitError):
            extract_entities(
                [("F1", "ZFN2JJXBLZT3"), ("F2", "NU2UC8MX6NK1")],
                api_key="k", out_dir=tmp_path / "p", raw_dir=tmp_path / "r",
                client=client, max_requests=10,
            )
    out = tmp_path / "p" / "entities.parquet"
    assert out.exists()
    con = duckdb.connect()
    n = con.execute(f"select count(*) from read_parquet('{out}')").fetchone()[0]
    con.close()
    assert n == 1


def test_extract_never_writes_the_api_key_anywhere(tmp_path, monkeypatch):
    monkeypatch.setattr("govbudget.sam_entities._REQUEST_FLOOR_S", 0)
    secret = "SUPERSECRETKEY123"

    def handler(request: httpx.Request) -> httpx.Response:
        assert secret in str(request.url), "the key must be sent"
        return httpx.Response(200, json=LOCKHEED)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        out = extract_entities(
            [("LOCKHEED MARTIN", "ZFN2JJXBLZT3")],
            api_key=secret,
            out_dir=tmp_path / "parquet",
            raw_dir=tmp_path / "raw",
            client=client,
            max_requests=10,
        )
    written = [out, tmp_path / "parquet" / "manifest.jsonl",
               tmp_path / "raw" / "ZFN2JJXBLZT3.json"]
    for p in written:
        assert p.exists(), p
        assert secret not in p.read_bytes().decode("utf-8", "replace"), p
    con = duckdb.connect()
    rows = con.execute(f"select * from read_parquet('{out}')").fetchall()
    con.close()
    assert len(rows) == 1
    assert not any(secret in str(v) for v in rows[0])


def test_extract_resumes_and_respects_the_daily_cap(tmp_path, monkeypatch):
    monkeypatch.setattr("govbudget.sam_entities._REQUEST_FLOOR_S", 0)
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json=LOCKHEED)

    fams = [("F1", "UEI0000000A"), ("F2", "UEI0000000B"), ("F3", "UEI0000000C")]
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        extract_entities(fams, api_key="k", out_dir=tmp_path / "p",
                         raw_dir=tmp_path / "r", client=client, max_requests=2)
    assert len(seen) == 2, "the run cap is a hard stop"
    # Second run skips what the first already fetched.
    seen.clear()
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        extract_entities(fams, api_key="k", out_dir=tmp_path / "p",
                         raw_dir=tmp_path / "r", client=client, max_requests=2)
    assert len(seen) == 1, "resume must fetch only what is missing"


def test_schema_only_write_produces_a_typed_zero_row_parquet(tmp_path):
    out = write_entities_parquet([], tmp_path / "p")
    con = duckdb.connect()
    cols = [r[0] for r in con.execute(
        f"describe select * from read_parquet('{out}')").fetchall()]
    n = con.execute(f"select count(*) from read_parquet('{out}')").fetchone()[0]
    con.close()
    assert n == 0
    assert cols == [
        "sam_uei", "legal_business_name", "cage_code", "registration_status",
        "registration_expiration_date", "business_types", "primary_naics",
        "public_url", "source_url", "retrieved_at", "response_sha256",
    ]


# ---------------------------------------------------------------------------
# retrieved_at is the FETCH day, never this run's clock (fix round 1, R-19-1).
# ---------------------------------------------------------------------------


def _body_for(uei: str) -> dict:
    body = json.loads(json.dumps(LOCKHEED))
    body["entityData"][0]["entityRegistration"]["ueiSAM"] = uei
    return body


def _retrieved_at(parquet_path) -> dict[str, str]:
    con = duckdb.connect()
    try:
        return dict(con.execute(
            f"select sam_uei, retrieved_at from read_parquet('{parquet_path}')"
        ).fetchall())
    finally:
        con.close()


def test_reparse_takes_retrieved_at_from_the_manifest_not_from_now(tmp_path):
    """Two bodies fetched on different days keep their own days.

    `extract_entities` re-parses every stored body in its finally block on
    EVERY run, so a now() stamp would re-date day 1's row to day 20 of the
    bounded extract — and the published claim is "this is what SAM said on
    that day".
    """
    raw, out = tmp_path / "r", tmp_path / "p"
    raw.mkdir()
    out.mkdir()
    for uei, day in (("ZFN2JJXBLZT3", "2026-09-01T10:00:00+00:00"),
                     ("NU2UC8MX6NK1", "2026-09-20T11:30:00+00:00")):
        (raw / f"{uei}.json").write_text(json.dumps(_body_for(uei)))
        append_record(out / "manifest.jsonl", ManifestRecord(
            dataset="sam_entities", fiscal_year=None, file_name=f"{uei}.json",
            source_url=f"https://api.sam.gov/entity-information/v4/entities?ueiSAM={uei}",
            sha256="x", bytes=1, downloaded_at=day,
        ))
    got = _retrieved_at(reparse(raw_dir=raw, out_dir=out))
    assert got["ZFN2JJXBLZT3"] == "2026-09-01T10:00:00+00:00"
    assert got["NU2UC8MX6NK1"] == "2026-09-20T11:30:00+00:00"


def test_reparse_falls_back_to_the_raw_file_mtime_when_the_manifest_is_silent(
    tmp_path,
):
    """A hand-dropped body (or a lost manifest) is still dated by its FETCH,
    not by the reparse — the file's own mtime, never now()."""
    import os

    raw, out = tmp_path / "r", tmp_path / "p"
    raw.mkdir()
    out.mkdir()
    p = raw / "ZFN2JJXBLZT3.json"
    p.write_text(json.dumps(LOCKHEED))
    when = datetime(2026, 3, 4, 5, 6, 7, tzinfo=timezone.utc)
    os.utime(p, (when.timestamp(), when.timestamp()))
    got = _retrieved_at(reparse(raw_dir=raw, out_dir=out))
    assert got["ZFN2JJXBLZT3"] == "2026-03-04T05:06:07+00:00"


def test_reparse_prints_how_many_rows_the_manifest_dated(tmp_path, capsys):
    """The silent case made loud: a reparse pointed at the wrong out_dir.

    `manifest.jsonl` lives under out_dir, so the wrong one finds no records
    and dates every row by mtime — a stamp a copy or a restore can move —
    while the run prints a path and looks like any other. The split is the
    only thing that tells the two apart.
    """
    raw, out = tmp_path / "r", tmp_path / "p"
    raw.mkdir()
    out.mkdir()
    for uei in ("ZFN2JJXBLZT3", "NU2UC8MX6NK1"):
        (raw / f"{uei}.json").write_text(json.dumps(_body_for(uei)))
    append_record(out / "manifest.jsonl", ManifestRecord(
        dataset="sam_entities", fiscal_year=None, file_name="ZFN2JJXBLZT3.json",
        source_url="https://api.sam.gov/entity-information/v4/entities?ueiSAM=ZFN2JJXBLZT3",
        sha256="x", bytes=1, downloaded_at="2026-09-01T10:00:00+00:00",
    ))

    reparse(raw_dir=raw, out_dir=out)
    assert (
        "sam reparse: 1 row(s) dated from manifest.jsonl, 1 from file mtime"
        in capsys.readouterr().out
    )

    # The wrong out_dir: nothing is dated by the record, and it says so.
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    reparse(raw_dir=raw, out_dir=elsewhere)
    assert (
        "sam reparse: 0 row(s) dated from manifest.jsonl, 2 from file mtime"
        in capsys.readouterr().out
    )


def test_a_later_run_never_restamps_an_earlier_run_s_rows(tmp_path, monkeypatch):
    """The reviewer's exact scenario: a 20-day bounded extract must not date
    every registration to the last day it happened to run."""
    monkeypatch.setattr("govbudget.sam_entities._REQUEST_FLOOR_S", 0)
    clock = {"now": "2026-09-01T00:00:00+00:00"}
    monkeypatch.setattr("govbudget.sam_entities._now_iso", lambda: clock["now"])
    fams = [("F1", "UEI0000000A"), ("F2", "UEI0000000B")]

    def handler(request: httpx.Request) -> httpx.Response:
        uei = dict(request.url.params)["ueiSAM"]
        return httpx.Response(200, json=_body_for(uei))

    for day in ("2026-09-01T00:00:00+00:00", "2026-09-20T00:00:00+00:00"):
        clock["now"] = day
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            out = extract_entities(fams, api_key="k", out_dir=tmp_path / "p",
                                   raw_dir=tmp_path / "r", client=client,
                                   max_requests=1)
    got = _retrieved_at(out)
    assert got["UEI0000000A"] == "2026-09-01T00:00:00+00:00", \
        "day 1's row must keep day 1 after day 20's run re-parsed it"
    assert got["UEI0000000B"] == "2026-09-20T00:00:00+00:00"


# ---------------------------------------------------------------------------
# --dry-run: the only mode that runs on a machine with no credential.
# ---------------------------------------------------------------------------


def test_plan_extract_counts_stored_missing_and_this_run(tmp_path):
    raw = tmp_path / "r"
    raw.mkdir()
    (raw / "UEI0000000A.json").write_text("{}")
    fams = [("F1", "UEI0000000A"), ("F2", "UEI0000000B"), ("F3", "UEI0000000C")]
    plan = plan_extract(fams, raw_dir=raw, max_requests=1)
    assert plan["families"] == 3
    assert plan["already_stored"] == 1
    assert plan["missing"] == 2
    assert plan["would_fetch"] == 1
    assert plan["runs_remaining"] == 2, "2 missing at 1/run is two more runs"
    assert plan["next_ueis"] == ["UEI0000000B"]


def test_plan_extract_reports_the_endpoint_preflight_recorded_when_there_is_one(
    tmp_path,
):
    """The dry run must not print a URL the real run would not request.

    `sam extract` requests `require_preflight(...)["endpoint"]`, so naming the
    v4 default "endpoint" made the plan the one document that disagrees with
    the run it describes — on the machine that has no key, which is the only
    machine that reads it. With a report it reports the recorded URL; with no
    report the field is called `endpoint_default`, which is what it is.
    """
    raw = tmp_path / "r"
    raw.mkdir()
    fams = [("F1", "UEI0000000A")]

    plan = plan_extract(fams, raw_dir=raw, max_requests=1)
    assert "endpoint" not in plan
    assert plan["endpoint_default"] == DEFAULT_SAM_ENTITY_API_URL

    v3 = "https://api.sam.gov/entity-information/v3/entities"
    report = tmp_path / "preflight.json"
    report.write_text(json.dumps({"endpoint": v3, "public_url_status": 200}))
    plan = plan_extract(fams, raw_dir=raw, max_requests=1, report_path=report)
    assert plan["endpoint"] == v3
    assert "endpoint_default" not in plan

    # A report that never found one is not a recorded endpoint either.
    report.write_text(json.dumps({"endpoint": None, "public_url_status": 200}))
    plan = plan_extract(fams, raw_dir=raw, max_requests=1, report_path=report)
    assert plan["endpoint_default"] == DEFAULT_SAM_ENTITY_API_URL


def test_plan_extract_is_complete_when_every_uei_is_stored(tmp_path):
    raw = tmp_path / "r"
    raw.mkdir()
    (raw / "UEI0000000A.json").write_text("{}")
    plan = plan_extract([("F1", "UEI0000000A")], raw_dir=raw, max_requests=10)
    assert plan["missing"] == 0
    assert plan["would_fetch"] == 0
    assert plan["runs_remaining"] == 0
    assert plan["complete"] is True


def test_dry_run_spends_no_request_and_writes_nothing(tmp_path, monkeypatch):
    """A dry run is the ONLY extract mode that needs no key: it must not
    construct a request, must not need a credential, and must leave the
    output and raw directories exactly as it found them."""
    monkeypatch.delenv("SAM_API_KEY", raising=False)

    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("a dry run must not touch the network")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        plan = extract_entities(
            [("F1", "UEI0000000A"), ("F2", "UEI0000000B")],
            api_key=None,
            out_dir=tmp_path / "p",
            raw_dir=tmp_path / "r",
            client=client,
            max_requests=10,
            dry_run=True,
        )
    assert plan["would_fetch"] == 2
    assert not (tmp_path / "p").exists(), "a dry run writes no parquet"
    assert not (tmp_path / "r").exists(), "a dry run creates no raw dir"


# ---------------------------------------------------------------------------
# preflight discovers the endpoint AND the extract uses it (fix round 1,
# R-19-3). Every path here is MockTransport; no candidate URL is ever dialled.
# ---------------------------------------------------------------------------


def _preflight_client(monkeypatch, status_for):
    """A MockTransport client that answers `status_for(url)` per candidate and
    200 for the reader-facing sam.gov page."""
    monkeypatch.setattr("govbudget.sam_entities._REQUEST_FLOOR_S", 0)
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url).split("?")[0]
        seen.append(url)
        if url.startswith("https://sam.gov/entity/"):
            return httpx.Response(200, text="<html>entity</html>")
        code = status_for(url)
        if code == 200:
            return httpx.Response(200, json=LOCKHEED)
        return httpx.Response(code, json={"error": {"code": "NOT_FOUND"}})

    return httpx.Client(transport=httpx.MockTransport(handler)), seen


def test_preflight_records_the_first_candidate_that_answers(tmp_path, monkeypatch):
    report_path = tmp_path / "preflight.json"
    secret = "SUPERSECRETKEY123"
    client, seen = _preflight_client(monkeypatch, lambda url: 200)
    with client:
        report = preflight(api_key=secret, client=client, report_path=report_path)
    assert report["endpoint"] == "https://api.sam.gov/entity-information/v4/entities"
    assert report["status"] == 200
    assert report["public_url_status"] == 200
    # Key NAMES only — never the body, never the credential.
    assert "entityRegistration" in report["entity_keys"]
    on_disk = json.loads(report_path.read_text())
    assert on_disk == report
    assert secret not in report_path.read_text(), "the report never holds the key"
    assert len([u for u in seen if "api.sam.gov" in u]) == 1, "one candidate, one request"


def test_preflight_skips_a_404_candidate_and_records_the_one_that_answers(
    tmp_path, monkeypatch
):
    v4 = "https://api.sam.gov/entity-information/v4/entities"
    v3 = "https://api.sam.gov/entity-information/v3/entities"
    client, seen = _preflight_client(monkeypatch, lambda url: 404 if url == v4 else 200)
    with client:
        report = preflight(api_key="k", client=client,
                           report_path=tmp_path / "preflight.json")
    assert report["endpoint"] == v3, "a 404 candidate is skipped, not fatal"
    assert [u for u in seen if "api.sam.gov" in u] == [v4, v3]


def test_preflight_raises_shape_error_naming_the_env_var_when_all_404(
    tmp_path, monkeypatch
):
    client, _ = _preflight_client(monkeypatch, lambda url: 404)
    with client:
        with pytest.raises(SamShapeError) as exc:
            preflight(api_key="k", client=client,
                      report_path=tmp_path / "preflight.json")
    assert "SAM_ENTITY_API_URL" in str(exc.value)
    assert not (tmp_path / "preflight.json").exists(), "a failed probe writes no report"


def test_preflight_raises_auth_error_when_every_candidate_rejects_the_key(
    tmp_path, monkeypatch
):
    client, _ = _preflight_client(monkeypatch, lambda url: 403)
    with client:
        with pytest.raises(SamAuthError) as exc:
            preflight(api_key="k", client=client,
                      report_path=tmp_path / "preflight.json")
    msg = str(exc.value)
    assert "401/403" in msg
    assert "login.gov" in msg, "an auth refusal always names the owner's step"


def test_require_preflight_refuses_a_report_that_never_found_an_endpoint(tmp_path):
    report = tmp_path / "preflight.json"
    report.write_text(json.dumps({"endpoint": None, "status": None,
                                  "public_url_status": 200}))
    with pytest.raises(SamShapeError) as exc:
        require_preflight(report)
    assert "SAM_ENTITY_API_URL" in str(exc.value)


def test_extract_requests_the_endpoint_preflight_recorded(tmp_path, monkeypatch):
    """The whole point of preflight: if it recorded v3, the extract must not
    spend the day's quota on v4."""
    monkeypatch.setattr("govbudget.sam_entities._REQUEST_FLOOR_S", 0)
    v3 = "https://api.sam.gov/entity-information/v3/entities"
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url).split("?")[0])
        return httpx.Response(200, json=LOCKHEED)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        extract_entities([("F1", "ZFN2JJXBLZT3")], api_key="k",
                         out_dir=tmp_path / "p", raw_dir=tmp_path / "r",
                         client=client, max_requests=1, endpoint=v3)
    assert seen == [v3]


def test_an_unexpected_status_is_a_sam_shape_error_not_an_http_status_error(
    tmp_path, monkeypatch
):
    """cmd_sam converts the three Sam* errors into a clean BLOCKED line; an
    httpx.HTTPStatusError would escape as a traceback instead."""
    monkeypatch.setattr("govbudget.sam_entities._REQUEST_FLOOR_S", 0)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": {"code": "NOT_FOUND"}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(SamShapeError) as exc:
            extract_entities([("F1", "ZFN2JJXBLZT3")], api_key="k",
                             out_dir=tmp_path / "p", raw_dir=tmp_path / "r",
                             client=client, max_requests=1)
    assert not isinstance(exc.value, httpx.HTTPStatusError)
    assert "SAM_ENTITY_API_URL" in str(exc.value)


def test_a_5xx_is_diagnosed_as_sam_being_down_not_as_a_wrong_endpoint(
    tmp_path, monkeypatch
):
    """A server-side failure must not send the operator after the version.

    The one message for every non-200 said "re-run preflight; if it records a
    different version, set SAM_ENTITY_API_URL". On a 503 that is a false
    diagnosis of a working endpoint, and acting on it costs 2 of a 10/day
    quota to learn nothing. The advice for a 5xx is to wait.
    """
    monkeypatch.setattr("govbudget.sam_entities._REQUEST_FLOOR_S", 0)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="Service Unavailable")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(SamShapeError) as exc:
            extract_entities([("F1", "ZFN2JJXBLZT3")], api_key="k",
                             out_dir=tmp_path / "p", raw_dir=tmp_path / "r",
                             client=client, max_requests=1)
    msg = str(exc.value)
    assert "503" in msg
    assert "SAM is down" in msg and "later" in msg
    assert "SAM_ENTITY_API_URL" not in msg, (
        "a 5xx says nothing about which endpoint version is right"
    )
    assert "kept" in msg, "stored bodies survive; the resume is the point"


def test_dominant_parent_ueis_breaks_an_obligation_tie_the_way_the_mart_does(
    tmp_path,
):
    """`dim_entities` takes max(uei) over the TIED top members; leg e4
    re-derives the same pick. If the two disagreed on an exact tie the gate
    would report a stale registration that is not stale. 46 families in the
    real lake tie at the top (23 across different UEIs) — none of them in the
    published top 200 today, which is exactly why this has to be pinned now.
    """
    from govbudget.sam_entities import dominant_parent_ueis

    tied = ["('U1','A INC','PB','B PARENT','TIED','parent_name','high',50.0)",
            "('U2','A LLC','PA','A PARENT','TIED','parent_name','high',50.0)"]
    clear = "('U3','C INC','PC','C PARENT','CLEAR','parent_name','high',10.0)"
    picks = []
    # Same family, the tied members inserted in each order: the answer must not
    # depend on which one a plan happens to number 1.
    for order in (tied, list(reversed(tied))):
        db = tmp_path / f"t{len(picks)}.duckdb"
        con = duckdb.connect(str(db))
        con.execute(
            "create table entity_xwalk as select * from (values "
            + ", ".join(order + [clear])
            + ") t(recipient_uei, recipient_name, parent_uei, parent_name,"
            "  family_key, method, confidence, total_obligation)"
        )
        con.execute(
            "create table dim_entities as select family_key,"
            " sum(total_obligation) as total_obligation from entity_xwalk"
            " group by family_key"
        )
        con.close()
        picks.append(dict(dominant_parent_ueis(db, top_n=2)))
    assert picks[0] == picks[1], "an exact tie must not depend on row order"
    assert picks[0]["TIED"] == "PB", "the tie resolves to max(uei), as the mart does"
    assert picks[0]["CLEAR"] == "PC"
    # WHICH UEI, said by the fixture. The two readings of "the one whose UEI
    # sorts highest" disagree here on purpose: the tied member whose own
    # recipient_uei sorts highest is U2, whose registration is PA, and the
    # mart takes max(coalesce(parent_uei, recipient_uei)) = PB, which is U1's.
    # That is why every published sentence about this pick says REGISTRATION
    # UEI — site/src/components/sam-registration.tsx's last sentence, the
    # citation formula in export_site.py, and /methodology/ §4.
    assert max("U1", "U2") == "U2"
    assert picks[0]["TIED"] != "PA", (
        "the tie must break on the registration UEI, not on the tied member's"
        " own recipient_uei"
    )


def test_no_pick_rule_surface_reclaims_the_display_name_identity():
    """The withdrawn identity stays withdrawn where the pick rule is TAUGHT.

    Group C polish corrected the rendered surfaces (the /company/ note, the
    citation formula, /methodology/ §4) and the model header, and each of
    those carries its own negative assertion. These two carry none, and they
    are the files the next editor of the pick rule reads: leg e4's docstring,
    which polices the registration, and the mart's dbt description, which is
    published verbatim on /data/'s sibling surfaces. Both said the
    registration is "the one the heading is built from"/"the rn=1 member
    display_name is read from" until fix round 1.

    Phrase-matched on purpose, and narrowly: export_site.py QUOTES the old
    wording inside the comment recording the correction, so a blanket grep for
    the words would red on the fix itself.
    """
    root = Path(__file__).resolve().parents[1]
    withdrawn = re.compile(
        r"no longer the one its own heading is built from"
        r"|rn\s*=\s*1 member .?display_name.? is read from"
        r"|registration that name is read from",
        re.IGNORECASE,
    )
    for rel, must_say in (
        ("src/govbudget/verify_phase2.py", "dominant registration"),
        ("dbt/models/marts/schema.yml", "ties broken"),
    ):
        text = (root / rel).read_text(encoding="utf-8")
        assert not withdrawn.search(text), (
            f"{rel} states the display_name/registration identity again;"
            " dim_entities.sql's header says nothing may"
        )
        assert must_say.lower() in text.lower(), (
            f"{rel} no longer states the rule it replaced the identity with"
        )


# ---------------------------------------------------------------------------
# The CLI surface: the key-absent path must be a clean refusal, not a crash.
# ---------------------------------------------------------------------------


def test_cli_extract_without_a_key_exits_non_zero_naming_the_owner_step(
    tmp_path, monkeypatch, capsys
):
    from govbudget.cli import main

    monkeypatch.delenv("SAM_API_KEY", raising=False)
    monkeypatch.setattr("govbudget.config.PARQUET_DIR", tmp_path / "parquet")
    monkeypatch.setattr("govbudget.config.RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr("govbudget.config.RESEARCH_DIR", tmp_path / "research")
    with pytest.raises(SystemExit) as exc:
        main(["sam", "extract"])
    assert exc.value.code != 0
    msg = str(exc.value)
    assert "SAM_API_KEY" in msg
    assert "login.gov" in msg
    assert "--dry-run" in msg
    # Nothing written: a refusal is not a partial run.
    assert not (tmp_path / "parquet").exists()
    assert not (tmp_path / "raw").exists()


def test_cli_extract_schema_only_needs_no_key(tmp_path, monkeypatch, capsys):
    from govbudget.cli import main

    monkeypatch.delenv("SAM_API_KEY", raising=False)
    monkeypatch.setattr("govbudget.config.PARQUET_DIR", tmp_path / "parquet")
    monkeypatch.setattr("govbudget.config.RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr("govbudget.config.RESEARCH_DIR", tmp_path / "research")
    main(["sam", "extract", "--schema-only"])
    out = tmp_path / "parquet" / "sam" / "entities.parquet"
    assert out.exists()
    assert "0 rows" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# ROADMAP #10 pre-live seams (decisions wave, 2026-09-25): the two URLs are
# read at CALL time, and a stored preflight only vouches for the reader-page
# template it actually opened. Plus the no-network plan of the first live day.
# ---------------------------------------------------------------------------


def test_the_api_url_is_read_at_call_time_not_import_time(tmp_path, monkeypatch):
    """`SAM_ENTITY_API_URL` used to be bound when the module was imported, so
    an operator who set it after import (a test harness, a REPL, a wrapper
    that loads .env late) got the v4 default with no sign anything was
    ignored."""
    from govbudget.sam_entities import candidate_urls, sam_entity_api_url

    monkeypatch.delenv("SAM_ENTITY_API_URL", raising=False)
    assert sam_entity_api_url() == DEFAULT_SAM_ENTITY_API_URL
    assert len(candidate_urls()) == 2, "v4 default + v3, deduplicated"

    custom = "https://api.sam.gov/entity-information/v9/entities"
    monkeypatch.setenv("SAM_ENTITY_API_URL", custom)
    assert sam_entity_api_url() == custom
    assert candidate_urls()[0] == custom, "the override is probed first"
    assert len(candidate_urls()) == 3

    raw = tmp_path / "r"
    raw.mkdir()
    plan = plan_extract([("F1", "UEI0000000A")], raw_dir=raw, max_requests=1)
    assert plan["endpoint_default"] == custom

    # An empty value is unset, not a URL.
    monkeypatch.setenv("SAM_ENTITY_API_URL", "")
    assert sam_entity_api_url() == DEFAULT_SAM_ENTITY_API_URL


def test_extract_with_no_recorded_endpoint_requests_the_call_time_url(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("govbudget.sam_entities._REQUEST_FLOOR_S", 0)
    custom = "https://api.sam.gov/entity-information/v9/entities"
    monkeypatch.setenv("SAM_ENTITY_API_URL", custom)
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url).split("?")[0])
        return httpx.Response(200, json=LOCKHEED)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        extract_entities([("F1", "ZFN2JJXBLZT3")], api_key="k",
                         out_dir=tmp_path / "p", raw_dir=tmp_path / "r",
                         client=client, max_requests=1)
    assert seen == [custom]


def test_the_public_url_template_is_read_at_call_time(monkeypatch):
    monkeypatch.setenv("SAM_PUBLIC_ENTITY_URL", "https://sam.gov/entity/{uei}/coreData")
    rec = parse_entity(LOCKHEED, source_url="https://api.sam.gov/x")
    assert rec["public_url"] == "https://sam.gov/entity/ZFN2JJXBLZT3/coreData"
    monkeypatch.delenv("SAM_PUBLIC_ENTITY_URL")
    rec = parse_entity(LOCKHEED, source_url="https://api.sam.gov/x")
    assert rec["public_url"] == "https://sam.gov/entity/ZFN2JJXBLZT3"


def test_a_public_url_template_without_the_uei_slot_is_refused(monkeypatch):
    """Every family would cite the same page."""
    from govbudget.sam_entities import sam_public_entity_url

    monkeypatch.setenv("SAM_PUBLIC_ENTITY_URL", "https://sam.gov/search")
    with pytest.raises(SamShapeError) as exc:
        sam_public_entity_url()
    assert "{uei}" in str(exc.value)


def test_preflight_records_the_call_time_public_template(tmp_path, monkeypatch):
    template = "https://sam.gov/entity/{uei}/coreData"
    monkeypatch.setenv("SAM_PUBLIC_ENTITY_URL", template)
    client, seen = _preflight_client(monkeypatch, lambda url: 200)
    with client:
        report = preflight(api_key="k", client=client,
                           report_path=tmp_path / "preflight.json")
    assert report["public_url"] == template
    assert "https://sam.gov/entity/ZFN2JJXBLZT3/coreData" in seen


def test_require_preflight_refuses_a_report_for_a_different_public_template(
    tmp_path, monkeypatch
):
    """The 200 preflight recorded was for the template it OPENED. If
    SAM_PUBLIC_ENTITY_URL changed since, every published citation link would
    point at a page nobody has opened — the exact thing the preflight
    requirement exists to prevent."""
    report = tmp_path / "preflight.json"
    report.write_text(json.dumps({
        "endpoint": "https://api.sam.gov/entity-information/v4/entities",
        "status": 200, "public_url": DEFAULT_SAM_PUBLIC_ENTITY_URL,
        "public_url_status": 200,
    }))
    monkeypatch.delenv("SAM_PUBLIC_ENTITY_URL", raising=False)
    assert require_preflight(report)["public_url_status"] == 200

    monkeypatch.setenv("SAM_PUBLIC_ENTITY_URL", "https://sam.gov/entity/{uei}/coreData")
    with pytest.raises(SamShapeError) as exc:
        require_preflight(report)
    msg = str(exc.value)
    assert DEFAULT_SAM_PUBLIC_ENTITY_URL in msg
    assert "https://sam.gov/entity/{uei}/coreData" in msg
    assert "sam preflight" in msg


def test_require_preflight_refuses_a_report_that_names_no_template(tmp_path):
    """A report with no `public_url` cannot vouch for any template."""
    report = tmp_path / "preflight.json"
    report.write_text(json.dumps({"endpoint": "https://x", "status": 200,
                                  "public_url_status": 200}))
    with pytest.raises(SamShapeError) as exc:
        require_preflight(report)
    assert "public_url" in str(exc.value)


def test_first_live_run_plan_spends_nothing_and_budgets_preflight_first(
    tmp_path, monkeypatch
):
    """What day 1 will do, with no key, no client and no network: preflight
    spends up to one API request per candidate, the extract gets the rest of
    the 10/day quota, and the plan names the families it would fetch."""
    from govbudget.sam_entities import plan_first_live_run

    monkeypatch.delenv("SAM_API_KEY", raising=False)
    monkeypatch.delenv("SAM_ENTITY_API_URL", raising=False)
    monkeypatch.delenv("SAM_PUBLIC_ENTITY_URL", raising=False)

    def boom(*_a, **_k):  # pragma: no cover
        raise AssertionError("a plan must not construct an HTTP client")

    monkeypatch.setattr("govbudget.sam_entities.httpx.Client", boom)
    raw = tmp_path / "raw"
    fams = [(f"F{i}", f"UEI{i:09d}") for i in range(12)]
    plan = plan_first_live_run(fams, raw_dir=raw,
                               report_path=tmp_path / "preflight.json")
    pre = plan["preflight"]
    assert pre["needed"] is True
    assert pre["api_requests_max"] == 2
    assert pre["candidates"] == [
        "https://api.sam.gov/entity-information/v4/entities",
        "https://api.sam.gov/entity-information/v3/entities",
    ]
    assert pre["public_page_probe"] == "https://sam.gov/entity/ZFN2JJXBLZT3"
    ex = plan["extract"]
    assert ex["max_requests"] == 8, "10/day minus preflight's worst case"
    assert ex["would_fetch"] == 8
    assert ex["next_families"] == [f"F{i}" for i in range(8)]
    assert plan["api_requests_max_today"] == 10
    assert plan["commands"] == [
        "uv run python -m govbudget sam preflight",
        "uv run python -m govbudget sam extract --max-requests 8",
    ]
    assert not raw.exists(), "a plan creates nothing"
    assert not (tmp_path / "preflight.json").exists()


def test_first_live_run_plan_skips_preflight_when_a_valid_report_exists(
    tmp_path, monkeypatch
):
    from govbudget.sam_entities import plan_first_live_run

    monkeypatch.delenv("SAM_PUBLIC_ENTITY_URL", raising=False)
    report = tmp_path / "preflight.json"
    v3 = "https://api.sam.gov/entity-information/v3/entities"
    report.write_text(json.dumps({"endpoint": v3, "status": 200,
                                  "public_url": DEFAULT_SAM_PUBLIC_ENTITY_URL,
                                  "public_url_status": 200}))
    plan = plan_first_live_run([("F1", "UEI000000001")], raw_dir=tmp_path / "r",
                               report_path=report)
    assert plan["preflight"]["needed"] is False
    assert plan["extract"]["max_requests"] == 10
    assert plan["extract"]["endpoint"] == v3

    # A report for another template does NOT count as a preflight.
    monkeypatch.setenv("SAM_PUBLIC_ENTITY_URL", "https://sam.gov/entity/{uei}/x")
    plan = plan_first_live_run([("F1", "UEI000000001")], raw_dir=tmp_path / "r",
                               report_path=report)
    assert plan["preflight"]["needed"] is True
    assert "https://sam.gov/entity/{uei}/x" in plan["preflight"]["reason"]


def test_cli_preflight_dry_run_needs_no_key_and_touches_no_network(
    tmp_path, monkeypatch, capsys
):
    from govbudget.cli import main

    monkeypatch.delenv("SAM_API_KEY", raising=False)
    monkeypatch.setattr("govbudget.config.PARQUET_DIR", tmp_path / "parquet")
    monkeypatch.setattr("govbudget.config.RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr("govbudget.config.RESEARCH_DIR", tmp_path / "research")
    monkeypatch.setattr(
        "govbudget.sam_entities.dominant_parent_ueis",
        lambda _db, top_n=200: [(f"F{i}", f"UEI{i:09d}") for i in range(top_n)])

    def boom(*_a, **_k):  # pragma: no cover
        raise AssertionError("a dry run must not construct an HTTP client")

    monkeypatch.setattr("govbudget.sam_entities.httpx.Client", boom)
    main(["sam", "preflight", "--dry-run"])
    out = capsys.readouterr().out
    assert "first live run" in out
    assert "up to 2 of the day's 10 API request(s)" in out
    assert "sam extract --max-requests 8" in out
    assert "F0" in out
    assert "Nothing was fetched and nothing was written." in out
    assert not (tmp_path / "research").exists()
    assert not (tmp_path / "raw").exists()


def test_cli_reparse_refuses_bodies_under_an_unverified_template(
    tmp_path, monkeypatch
):
    """`sam reparse` writes `public_url` from the CURRENT template, so once
    bodies exist it answers to the same preflight the extract does."""
    from govbudget.cli import main

    monkeypatch.setattr("govbudget.config.PARQUET_DIR", tmp_path / "parquet")
    monkeypatch.setattr("govbudget.config.RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr("govbudget.config.RESEARCH_DIR", tmp_path / "research")
    raw = tmp_path / "raw" / "sam"
    raw.mkdir(parents=True)
    (raw / "ZFN2JJXBLZT3.json").write_text(json.dumps(LOCKHEED))
    report = tmp_path / "research" / "sam_entities" / "preflight.json"
    report.parent.mkdir(parents=True)
    report.write_text(json.dumps({"endpoint": "https://x", "status": 200,
                                  "public_url": DEFAULT_SAM_PUBLIC_ENTITY_URL,
                                  "public_url_status": 200}))
    monkeypatch.setenv("SAM_PUBLIC_ENTITY_URL", "https://sam.gov/entity/{uei}/x")
    with pytest.raises(SystemExit) as exc:
        main(["sam", "reparse"])
    assert "BLOCKED" in str(exc.value)
    assert not (tmp_path / "parquet" / "sam" / "entities.parquet").exists()

    monkeypatch.delenv("SAM_PUBLIC_ENTITY_URL")
    main(["sam", "reparse"])
    assert (tmp_path / "parquet" / "sam" / "entities.parquet").exists()


def test_the_missing_report_refusal_counts_the_requests_preflight_would_spend(
    tmp_path, monkeypatch
):
    """Decisions fix round 2: the missing-report refusal said preflight
    "spends up to 2 of the day's requests" as a literal. With
    SAM_ENTITY_API_URL naming a third endpoint preflight probes 3 (one per
    candidate_urls() entry), so the operator console must count them the way
    the template-mismatch refusal below it already does."""
    from govbudget.sam_entities import candidate_urls

    report = tmp_path / "preflight.json"
    monkeypatch.delenv("SAM_ENTITY_API_URL", raising=False)
    with pytest.raises(SamShapeError) as exc:
        require_preflight(report)
    assert len(candidate_urls()) == 2
    assert "spends up to 2 of the day's requests" in str(exc.value)

    monkeypatch.setenv(
        "SAM_ENTITY_API_URL", "https://api.sam.gov/entity-information/v9/entities")
    with pytest.raises(SamShapeError) as exc:
        require_preflight(report)
    assert len(candidate_urls()) == 3
    assert "spends up to 3 of the day's requests" in str(exc.value)
    assert "up to 2 of" not in str(exc.value)
