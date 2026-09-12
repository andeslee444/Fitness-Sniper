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
from pathlib import Path

import duckdb
import httpx
import pytest

from govbudget.sam_entities import (
    SamAuthError,
    SamRateLimitError,
    SamShapeError,
    extract_entities,
    parse_entity,
    plan_extract,
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
                                  "public_url_status": 404}))
    with pytest.raises(SamShapeError) as exc:
        require_preflight(report)
    assert "public_url_status" in str(exc.value)
    report.write_text(json.dumps({"endpoint": "https://x", "status": 200,
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
