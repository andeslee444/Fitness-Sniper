"""Tests for govbudget.sam_batch — batched, three-query SAM answers.

Every request goes through httpx.MockTransport to tests/sam_fake.FakeSam,
which answers the documented shapes; bodies land in tmp dirs.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import duckdb
import httpx
import pytest

from govbudget import sam_batch
from govbudget.sam_batch import (
    SamQueryRejectedError, build_url, classify_record, fetch_batch,
    rebuild, resolve_answers,
)
from govbudget.sam_entities import DEFAULT_SAM_ENTITY_API_URL as EP, SamShapeError
from sam_fake import FakeSam, id_only, masked, registration

KEY = "sekret-key-0123456789"
T = datetime(2026, 9, 28, 13, 29, tzinfo=timezone.utc)
U = [f"UEI{i:09d}" for i in range(30)]


@pytest.fixture(autouse=True)
def _no_floor(monkeypatch):
    monkeypatch.setattr("govbudget.sam_entities._REQUEST_FLOOR_S", 0)


def fetch(tmp_path, fake, ueis, *, stage="registered", mode="batch+integrity",
          control=None):
    with httpx.Client(transport=httpx.MockTransport(fake)) as client:
        return fetch_batch(client, api_key=KEY, endpoint=EP, ueis=ueis,
                           stage=stage, mode=mode, raw_dir=tmp_path / "raw",
                           out_dir=tmp_path / "out", control=control,
                           clock=lambda: T)


def test_build_url_writes_the_documented_brackets_and_commas_literally():
    url = build_url(EP, U[:3], stage="id_assigned", mode="batch+integrity")
    assert url == (f"{EP}?ueiSAM=[{U[0]}~{U[1]}~{U[2]}]&samRegistered=No"
                   "&includeSections=entityRegistration,coreData,integrityInformation")
    assert build_url(EP, U[:1], stage="expired", mode="single") == (
        f"{EP}?ueiSAM={U[0]}&registrationStatus=E")
    for bad in (["abc"], [f"{U[0][:11]}&"], [], U * 4):
        with pytest.raises(ValueError):
            build_url(EP, bad, stage="registered", mode="batch")
    with pytest.raises(ValueError):
        build_url(EP, U[:2], stage="registered", mode="single")


def test_classify_never_takes_an_id_only_active_as_a_registration():
    """Docs Example 2: samRegistered "No" with registrationStatus "Active"."""
    assert classify_record(id_only(U[0]))[:2] == (U[0], "id_assigned")
    assert classify_record(registration(U[1]))[:2] == (U[1], "registered")
    uei, kind, fields = classify_record(masked(U[2]))
    assert (uei, kind, fields["legal_business_name"]) == (U[2], "opted_out",
                                                          f"HIDDEN {U[2]}")
    with pytest.raises(SamShapeError):
        classify_record({"entityRegistration": 7})


def test_a_batch_is_stored_whole_with_one_manifest_line_and_no_key(tmp_path):
    fake = FakeSam({U[1]: "none"})
    r = fetch(tmp_path, fake, U[:3], control=U[0])
    assert r.honoured is True and sorted(r.found) == [U[0], U[2]]
    assert r.absent == [U[1]] and r.unresolved == []
    files = list((tmp_path / "raw" / "batches").glob("*.json"))
    assert len(files) == 1
    stored = json.loads(files[0].read_text())
    assert stored["asked"] == U[:3] and stored["stage"] == "registered"
    assert stored["request_url"].startswith(f"{EP}?ueiSAM=[") and "api_key" not in stored["request_url"]
    lines = (tmp_path / "out" / "manifest.jsonl").read_text().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["downloaded_at"] == T.isoformat()
    assert KEY not in files[0].read_text() + lines[0]
    assert fake.requests[0]["api_key"] == KEY


def test_a_batch_without_its_control_proves_nothing_absent(tmp_path):
    """SAM that ignores the brackets answers the literal string: nothing."""
    fake = FakeSam(honour_batches=False)
    r = fetch(tmp_path, fake, U[1:4], control=U[0])
    assert r.honoured is False and r.absent == [] and r.unresolved == []
    answers = resolve_answers(tmp_path / "raw", tmp_path / "out")
    assert all(a["kind"] == "pending" and a["stages_absent"] == []
               for a in answers.values())


def test_an_incomplete_page_leaves_the_rest_unresolved_not_absent(tmp_path):
    fake = FakeSam({u: "dup" for u in U[:6]})           # 12 records, 10 fit
    r = fetch(tmp_path, fake, U[:10])
    assert r.absent == [] and set(r.unresolved) == set(U[5:10])
    answers = resolve_answers(tmp_path / "raw", tmp_path / "out")
    assert answers[U[9]]["kind"] == "pending" and answers[U[9]]["unresolved"] == 1


def test_duplicates_resolve_to_the_latest_expiring_active_registration(tmp_path):
    fetch(tmp_path, FakeSam({U[0]: "dup"}), U[:1], mode="single+integrity")
    a = resolve_answers(tmp_path / "raw", tmp_path / "out")[U[0]]
    assert a["record"]["entityRegistration"]["registrationExpirationDate"] == "2027-06-30"


def test_the_three_queries_classify_every_kind_and_publish_only_registrations(tmp_path):
    kinds = {U[0]: "opted_out", U[1]: "id_only", U[2]: "inactive", U[3]: "none"}
    fake = FakeSam(kinds, default_hides_expired=True)
    fetch(tmp_path, fake, U[:5])
    fetch(tmp_path, fake, U[1:4], stage="id_assigned")
    fetch(tmp_path, fake, [U[2], U[3]], stage="expired")
    rebuild(tmp_path / "raw", tmp_path / "out")
    got = {r[0]: r[1] for r in duckdb.sql(
        f"select sam_uei, kind from '{tmp_path}/out/answers.parquet'").fetchall()}
    assert got == {U[0]: "opted_out", U[1]: "id_assigned", U[2]: "registered",
                   U[3]: "not_public", U[4]: "registered"}
    rows = duckdb.sql(f"select sam_uei, registration_status from "
                      f"'{tmp_path}/out/entities.parquet' order by 1").fetchall()
    assert rows == [(U[2], "Inactive"), (U[4], "Active")]


def test_a_plain_absence_is_asked_again_with_integrity_but_counts_without(tmp_path):
    """A `sam extract` empty body (RTX, Humana, BAE) cannot tell an opted-out
    entity from none: re-asked while the mode can ask with integrity."""
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / f"{U[0]}.json").write_text(json.dumps({"entityData": [], "totalRecords": 0}))
    with_integrity = resolve_answers(raw, tmp_path / "out", integrity=True)[U[0]]
    plain = resolve_answers(raw, tmp_path / "out", integrity=False)[U[0]]
    assert (with_integrity["kind"], with_integrity["next_stage"]) == ("pending", "registered")
    assert (plain["kind"], plain["next_stage"]) == ("pending", "id_assigned")


def test_http_errors_map_to_the_errors_the_driver_acts_on(tmp_path):
    from govbudget.sam_entities import (SamAuthError, SamOfflineError,
                                        SamRateLimitError, SamUnavailableError)
    cases = [
        (httpx.Response(400, text="bad"), SamQueryRejectedError),
        (httpx.Response(429, text="slow"), SamRateLimitError),
        (httpx.Response(403, text="API_KEY_INVALID"), SamAuthError),
        (httpx.Response(503, text="down"), SamUnavailableError),
        (httpx.ReadTimeout("t"), SamUnavailableError),
        (httpx.ConnectError("x"), SamOfflineError),
    ]
    for response, exc in cases:
        fake = FakeSam(fail=lambda n, q, r=response: r)
        with pytest.raises(exc) as e:
            fetch(tmp_path, fake, U[:2])
        assert KEY not in str(e.value)
    with pytest.raises(SamUnavailableError) as e:
        fetch(tmp_path, FakeSam(fail=lambda n, q: httpx.ReadTimeout("t")), U[:1],
              mode="single")
    assert e.value.uei == U[0]
    assert not (tmp_path / "raw" / "batches").exists()      # nothing paid for is lost, nothing unpaid stored


def test_two_identical_answers_in_one_second_never_overwrite(tmp_path):
    fake = FakeSam({U[0]: "none"})
    fetch(tmp_path, fake, U[:1], mode="single")
    fetch(tmp_path, fake, U[:1], mode="single")
    assert len(list((tmp_path / "raw" / "batches").glob("*.json"))) == 2


def test_rebuild_keeps_what_hand_runs_and_batches_each_stored(tmp_path):
    """`sam_entities.reparse` is `rebuild`: a hand-run `sam extract` body and
    a batch body both yield rows, and reparse's legacy lines still print."""
    from govbudget.sam_entities import reparse
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / f"{U[0]}.json").write_text(json.dumps(
        {"entityData": [registration(U[0])], "totalRecords": 1}))
    fetch(tmp_path, FakeSam(), U[1:3])
    reparse(raw_dir=raw, out_dir=tmp_path / "out")
    n = duckdb.sql(f"select count(*) from '{tmp_path}/out/entities.parquet'").fetchone()[0]
    assert n == 3
    assert sam_batch.pending([("A", U[0]), ("B", U[5])],
                             resolve_answers(raw, tmp_path / "out")) == [("B", U[5])]


# ── review round 3 (2026-09-27) ─────────────────────────────────────────────

def test_a_proof_with_nothing_else_to_ask_is_still_a_bracketed_pair(tmp_path):
    fake = FakeSam()
    r = fetch(tmp_path, fake, [], control=sam_batch.CONTROL_UEI)
    assert r.asked == [sam_batch.CONTROL_PAIR, sam_batch.CONTROL_UEI]
    assert fake.requests[0]["ueiSAM"].startswith("[") and r.honoured is True


def test_a_full_page_that_cut_the_control_is_inconclusive_not_a_refusal(tmp_path):
    """Duplicates fill the page before the control: SAM answered with asked
    UEIs, so it DID honour the batch."""
    fake = FakeSam({u: "dup" for u in U[:6]})
    r = fetch(tmp_path, fake, U[:9], control=sam_batch.CONTROL_UEI)
    assert r.honoured is True and r.absent == []


def test_a_record_whose_uei_does_not_read_proves_no_absence(tmp_path):
    def fail(n, q):
        return httpx.Response(200, json={"totalRecords": 1, "entityData": [
            {"entityRegistration": {"legalBusinessName": "NO UEI"}}]})
    r = fetch(tmp_path, FakeSam(fail=fail), U[:3])
    assert r.absent == [] and set(r.unresolved) == set(U[:3])


def test_a_200_that_does_not_read_is_stored_named_and_never_blocks_the_rest(tmp_path):
    from govbudget.sam_batch import SamStoredBodyError
    bad = FakeSam(fail=lambda n, q: httpx.Response(
        200, json={"totalRecords": 1, "entityData": [{"entityRegistration": None}]}))
    with pytest.raises(SamStoredBodyError) as e:
        fetch(tmp_path, bad, U[:3])
    assert e.value.file.startswith("batches/")
    text = FakeSam(fail=lambda n, q: httpx.Response(200, text="<html>oops"))
    with pytest.raises(SamStoredBodyError):
        fetch(tmp_path, text, U[3:5])
    files = list((tmp_path / "raw" / "batches").glob("*.json"))
    assert len(files) == 2 and any("response_text" in f.read_text() for f in files)
    assert len((tmp_path / "out" / "manifest.jsonl").read_text().splitlines()) == 2
    fetch(tmp_path, FakeSam(), U[5:7])
    answers = resolve_answers(tmp_path / "raw", tmp_path / "out")
    assert {answers[u]["kind"] for u in U[:5]} == {"unreadable"}
    assert answers[U[5]]["kind"] == "registered"
    assert "batches/" in answers[U[0]]["why"]


def test_a_400_body_is_scrubbed_before_it_is_cut(tmp_path):
    body = "x" * 290 + KEY + "y" * 50                  # the key straddles char 300
    fake = FakeSam(fail=lambda n, q: httpx.Response(400, text=body))
    with pytest.raises(SamQueryRejectedError) as e:
        fetch(tmp_path, fake, U[:2])
    assert KEY[:8] not in str(e.value)


def test_rebuild_settles_answers_the_way_the_mode_in_force_does(tmp_path):
    """In a plain mode a registered_plain absence settles the first query, so
    answers.parquet agrees with the driver (not_public, not pending)."""
    raw, out = tmp_path / "raw", tmp_path / "out"
    fake = FakeSam({U[0]: "none"})
    fetch(tmp_path, fake, U[:2], mode="batch")
    fetch(tmp_path, fake, U[:1], stage="id_assigned", mode="batch")
    fetch(tmp_path, fake, U[:1], stage="expired", mode="batch")
    (out / "daily").mkdir(parents=True)
    (out / "daily" / "state.json").write_text(json.dumps({"mode": "batch"}))
    rebuild(raw, out)
    kinds = dict(duckdb.sql(f"select sam_uei, kind from '{out}/answers.parquet'").fetchall())
    assert kinds[U[0]] == "not_public"


def test_the_published_source_url_is_the_request_as_sent(tmp_path):
    fetch(tmp_path, FakeSam(), U[:2])
    rebuild(tmp_path / "raw", tmp_path / "out")
    urls = {r[0] for r in duckdb.sql(
        f"select source_url from '{tmp_path}/out/entities.parquet'").fetchall()}
    assert urls == {f"{EP}?ueiSAM=[{U[0]}~{U[1]}]&includeSections="
                    "entityRegistration,coreData,assertions,integrityInformation"}


def test_a_hand_run_never_asks_what_a_batch_already_settled(tmp_path, monkeypatch):
    from govbudget.sam_entities import extract_entities
    fetch(tmp_path, FakeSam({U[0]: "none"}), U[:2])      # U0 empty at `registered`
    monkeypatch.setenv("SAM_API_KEY", KEY)
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(200, json={"entityData": [registration(U[2])],
                                         "totalRecords": 1})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        extract_entities([("A", U[0]), ("B", U[1]), ("C", U[2])], api_key=KEY,
                         out_dir=tmp_path / "out", raw_dir=tmp_path / "raw",
                         client=client, max_requests=10)
    assert len(seen) == 1 and U[2] in seen[0]


def test_the_dry_run_plans_count_what_batches_already_answered(tmp_path):
    from govbudget.sam_entities import plan_extract, plan_first_live_run
    fetch(tmp_path, FakeSam(), U[:3])
    fams = [(f"F{i}", u) for i, u in enumerate(U[:5])]
    plan = plan_extract(fams, raw_dir=tmp_path / "raw", out_dir=tmp_path / "out")
    assert (plan["already_stored"], plan["missing"]) == (3, 2)
    first = plan_first_live_run(fams, raw_dir=tmp_path / "raw",
                                report_path=tmp_path / "none.json",
                                out_dir=tmp_path / "out")
    assert first["extract"]["missing"] == 2


def test_reparse_is_offline_and_needs_no_preflight(tmp_path, monkeypatch, capsys):
    """The link `sam reparse` writes is the fixed receipt URL (#191), so a
    rebuild from stored bodies needs no preflight report at all."""
    from govbudget import cli, config
    with httpx.Client(transport=httpx.MockTransport(FakeSam())) as client:
        fetch_batch(client, api_key=KEY, endpoint=EP, ueis=U[:2],
                    stage="registered", mode="batch+integrity",
                    raw_dir=tmp_path / "raw" / "sam",
                    out_dir=tmp_path / "parquet" / "sam", clock=lambda: T)
    monkeypatch.setattr(config, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(config, "PARQUET_DIR", tmp_path / "parquet")
    monkeypatch.setattr(config, "RESEARCH_DIR", tmp_path / "research")  # no report
    cli.main(["sam", "reparse"])
    urls = {r[0] for r in duckdb.sql(f"select public_url from "
                                     f"'{tmp_path}/parquet/sam/entities.parquet'").fetchall()}
    assert urls == {f"https://fiscalreceipts.com/json/sam/{u}.json" for u in U[:2]}
