"""`govbudget platform-families …` (families piece 2; spec §8.3, §9.2, Review Focus 5).

Task 7a: `check`. Task 7b: `propose` and the `--seed-shipped` wrapper. Tasks 7c–7d
append render, answer, ratify and preview.
The lake is stubbed through module attributes (reg.open_lake, reg.check_lake,
reg.measure_member).
"""
from __future__ import annotations

import csv
import dataclasses
import datetime
import io
import json
from types import SimpleNamespace

import duckdb
import pytest

from govbudget import cli, config
from govbudget import f15_funding_history as f15
from govbudget import platform_families as reg
import govbudget.platform_family_review as review
import govbudget.verify_families as vf
from platform_families_helpers import (ATA000, DRAFT_F35, F35_PREFILL, F35_RULING_ID, JSM000, MEASURES, MSAR,
                                       FakeLake, add_family, add_source, f15_registry, ratified_f35,
                                       write_prefill)

LOCK = 'IO Error: Could not set lock on file "/x/govbudget.duckdb": Conflicting lock is held in /usr/bin/python3 (PID 1)'


def _exit(argv) -> int:
    with pytest.raises(SystemExit) as exit_:
        cli.main(argv)
    return exit_.value.code


@pytest.fixture
def cli_env(tmp_path, monkeypatch):
    paths = f15_registry(tmp_path)
    add_family(paths, DRAFT_F35, sources=[MSAR])
    env = SimpleNamespace(paths=paths, tmp_path=tmp_path, report=reg.LakeReport([], [], []), lakes=[])
    monkeypatch.setattr(reg, "DEFAULT_PATHS", paths)
    monkeypatch.setattr(reg, "REVIEW_ROOT", tmp_path / "research")

    def open_lake(path):
        env.lakes.append(FakeLake())
        return env.lakes[-1]

    monkeypatch.setattr(reg, "open_lake", open_lake)
    monkeypatch.setattr(reg, "check_lake", lambda registry, **kw: env.report)
    # Without it, a run at :15-:20 against the default --duckdb would trip the SAM guard.
    monkeypatch.setattr(vf, "_now", lambda: datetime.datetime(2026, 10, 21, 1, 30))
    return env


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------


def test_check_prints_failures_undecided_and_stale(cli_env, capsys):
    cli_env.report = reg.LakeReport(failures=[], undecided=["f-35: 2026/JSM000 matches the review guard"],
                                    stale=["f-15|P-1:3010F:AF:F01500|2017-2026: drift_sha256 moved"])
    code = _exit(["platform-families", "check"])
    out = capsys.readouterr().out.splitlines()
    assert code == 0
    assert "  undecided f-35: 2026/JSM000 matches the review guard" in out
    assert "  stale f-15|P-1:3010F:AF:F01500|2017-2026: drift_sha256 moved" in out
    assert out[-1] == "platform-families check: families=2 failures=0 undecided=1 stale=1"
    assert [lake.closed for lake in cli_env.lakes] == [True]


@pytest.mark.parametrize("which", ["undecided", "stale"])
def test_check_strict_exits_1_on_undecided_or_stale(cli_env, capsys, which):
    cli_env.report = reg.LakeReport(failures=[], undecided=[], stale=[])
    getattr(cli_env.report, which).append("f-35: 2026/JSM000 matches the review guard")
    assert _exit(["platform-families", "check"]) == 0
    assert _exit(["platform-families", "check", "--strict"]) == 1
    assert capsys.readouterr().out.splitlines()[-1].startswith("platform-families check: families=2 failures=0")


def test_check_exits_1_on_a_lake_failure(cli_env, capsys):
    cli_env.report = reg.LakeReport(failures=["f-15: P-1 2026/F01500 title 'F-15X' differs from titles_seen 'F-15'"],
                                    undecided=[], stale=[])
    assert _exit(["platform-families", "check"]) == 1
    out = capsys.readouterr().out.splitlines()
    assert "  FAIL f-15: P-1 2026/F01500 title 'F-15X' differs from titles_seen 'F-15'" in out
    assert out[-1] == "platform-families check: families=2 failures=1 undecided=0 stale=0"


def test_check_exits_1_on_a_stage_1_error_naming_the_file(cli_env, capsys):
    doc = json.loads(cli_env.paths.json.read_text(encoding="utf-8"))
    doc["schema_version"] = 2
    cli_env.paths.json.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    assert _exit(["platform-families", "check"]) == 1
    out = capsys.readouterr().out.splitlines()
    n = len(out) - 1
    assert n >= 1
    assert all(line.startswith("platform-families: ") and "platform_families.json" in line for line in out[:-1])
    assert out[-1] == f"platform-families check: stage 1 failed ({n} error(s))"
    assert cli_env.lakes == []


def test_check_reports_a_duckdb_lock_as_exit_2(cli_env, monkeypatch, capsys):   # Review Focus 5
    def locked(path):
        raise duckdb.IOException(LOCK)
    monkeypatch.setattr(reg, "open_lake", locked)
    assert _exit(["platform-families", "check"]) == 2
    out, err = capsys.readouterr()
    assert err.strip() == f"platform-families check: ERROR — {LOCK}"
    assert "platform-families check: families=" not in out


def test_check_refuses_the_live_lake_across_the_sam_window(cli_env, monkeypatch, capsys):
    live = cli_env.tmp_path / "govbudget.duckdb"
    live.touch()
    monkeypatch.setattr(config, "DUCKDB_PATH", live)
    monkeypatch.setattr(vf, "_now", lambda: datetime.datetime(2026, 10, 21, 1, 17))
    assert _exit(["platform-families", "check"]) == 2
    out, err = capsys.readouterr()
    assert "SAM window" in err
    assert "platform-families check: families=" not in out
    assert cli_env.lakes == []


# ---------------------------------------------------------------------------
# propose (Task 7b; spec §8.3, §7.2, §7.4, §7.6; Review Focus 4 and 5)
# ---------------------------------------------------------------------------

_SEED_REPLY = "approved, would process with recommendation to approve all\n"
_B1_RULING = {"ruling_id": F35_RULING_ID, "kind": "batch", "platform_family": "f-35", "decided_by": "owner",
              "decided_on": "2026-10-22", "owner_reply": "approved", "spec": "docs/x.md#b1",
              "text": "Ratifies the f-35 rows.", "seed_basis": False}


def _csv(path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def _registry_bytes(paths) -> dict[str, bytes]:
    return {"json": paths.json.read_bytes(), "members": paths.members.read_bytes(),
            "era_lines": paths.era_lines.read_bytes()}


def _member_row(prefill: dict[str, str], **kv: str) -> dict[str, str]:
    """A prefill row as a full member row (MEMBER_COLUMNS order): its member_row_id and
    MEASURES' lake columns, then the overrides."""
    row = dict.fromkeys(reg.MEMBER_COLUMNS, "")
    row.update({key: value for key, value in prefill.items() if key != "reason"})
    m = MEASURES[prefill["member_id"]]
    row.update(member_row_id=f"f-35|{prefill['member_id']}|{prefill['valid_from_edition']}-"
                             f"{prefill['valid_to_edition']}",
               titles_seen="; ".join(f"{e}: {t}" for e, t in m.titles_seen),
               budget_activities=";".join(m.budget_activities), drift_sha256=m.drift_sha256)
    for key, value in kv.items():
        if key not in row:
            raise KeyError(key)
        row[key] = value
    return row


@pytest.fixture
def proposing(cli_env, monkeypatch):
    tmp_path, paths = cli_env.tmp_path, cli_env.paths
    family_json, rows_csv = write_prefill(tmp_path, F35_PREFILL)
    monkeypatch.setattr(reg, "open_lake", lambda path: FakeLake())
    monkeypatch.setattr(reg, "measure_member", lambda lake, member, *, headline: MEASURES[member.member_id])
    out_root = tmp_path / "out"
    # The CLI passes out_root=review.OUT_ROOT; without this a render, answer or ratify run
    # through cli.main would use the checkout's own tmp/platform-families/.
    monkeypatch.setattr(review, "OUT_ROOT", out_root)
    return SimpleNamespace(env=cli_env, paths=paths, tmp_path=tmp_path, fj=family_json, rc=rows_csv,
                           db=tmp_path / "fam2.duckdb", rr=reg.REVIEW_ROOT, out_root=out_root,
                           before=_registry_bytes(paths))


def _unpack(p):
    return p.fj, p.rc, p.db, p.paths, p.rr, p.before


def test_propose_writes_a_draft_family_and_the_review_files(proposing):
    fj, rc, db, paths, rr, before = _unpack(proposing)
    out = review.propose(platform_family="f-35", family_json=fj, rows_csv=rc, duckdb_path=db, paths=paths, review_root=rr)
    assert out == {"rows": 4, "era_lines": 1, "held_for_review": 0}
    registry = reg.load_registry(paths)
    assert registry["f-35"].status == "draft" and registry["f-35"].members == ()
    assert registry.sources["msar-pb2027"].tier == "G"
    rows = _csv(rr / "f-35" / "review.csv")
    assert list(rows[0]) == list(reg.REVIEW_COLUMNS)
    assert [r["member_row_id"] for r in rows] == ["f-35|P-1:3010F:AF:ATA000|2017-2026", "f-35|P-1:3020F:AF:JSM000|2022-2026",
                                                 "f-35|R-1:3600F:AF:0207268F|2017-2026", "f-35|R-1:3600F:AF:0604800F|2017-2023"]
    ata = rows[0]
    assert (ata["titles_seen"], ata["drift_sha256"], ata["headline_actuals_k"]) == ("2024: F-35; 2025: F-35; 2026: F-35", "a" * 64, "53368300.000")
    assert (ata["decided_by"], ata["ruling_id"], ata["decided_on"]) == ("", "", "")
    assert rows[2]["headline_actuals_k"] == ""
    assert _csv(rr / "f-35" / "review_era_lines.csv") == [{"platform_family": "f-35", "member_id": "P-1:3010F:AF:ATA000",
        "edition": "2018", "era_key": "3010F-AF-L1", "budget_activity": "01", "filed_title": "F-35", "decision_id": "ATA000|3010F||2017-2023"}]
    assert paths.members.read_bytes() == before["members"] and paths.era_lines.read_bytes() == before["era_lines"]


@pytest.mark.parametrize("status", ["published", "ratified"])
def test_propose_refuses_to_overwrite_a_ratified_or_published_family(proposing, status):
    fj, rc, db, paths, rr, _before = _unpack(proposing)
    if status == "published":
        pf = "f-15"
        family = {k: v for k, v in DRAFT_F35.items() if k != "status"} | {
            "platform_family": "f-15", "short_name": "F-15", "history_dataset": "f15_funding_history"}
        fj = proposing.tmp_path / "f15-family.json"
        fj.write_text(json.dumps({"family": family, "sources": [MSAR]}, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    else:
        pf = "f-35"
        ratified_f35(paths)
    baseline = _registry_bytes(paths)
    with pytest.raises(reg.RegistryError) as e:
        review.propose(platform_family=pf, family_json=fj, rows_csv=rc, duckdb_path=db, paths=paths, review_root=rr)
    assert f"{pf} is {status}" in str(e.value)
    assert _registry_bytes(paths) == baseline
    assert not (rr / pf).exists()


def test_propose_replaces_an_earlier_draft_of_the_same_family(proposing):
    fj, rc, db, paths, rr, _before = _unpack(proposing)
    review.propose(platform_family="f-35", family_json=fj, rows_csv=rc, duckdb_path=db, paths=paths, review_root=rr)
    doc = json.loads(fj.read_text(encoding="utf-8"))
    doc["family"]["scope_note"] = "Second draft."
    fj.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    review.propose(platform_family="f-35", family_json=fj, rows_csv=rc, duckdb_path=db, paths=paths, review_root=rr)
    written = json.loads(paths.json.read_text(encoding="utf-8"))
    assert [f["platform_family"] for f in written["families"]] == ["f-15", "f-35"]
    registry = reg.load_registry(paths)
    assert registry["f-35"].scope_note == "Second draft." and registry["f-35"].status == "draft"
    assert len(_csv(rr / "f-35" / "review.csv")) == 4


def test_propose_never_reproposes_reviewed_excluded_or_rejected_rows(proposing):
    fj, rc, db, paths, rr, _before = _unpack(proposing)
    add_family(paths, DRAFT_F35, members=[_member_row(F35_PREFILL[2], verdict="rejected")])   # JSM000
    baseline = _registry_bytes(paths)
    out = review.propose(platform_family="f-35", family_json=fj, rows_csv=rc, duckdb_path=db, paths=paths, review_root=rr)
    assert out["rows"] == 3
    assert JSM000 not in {r["member_id"] for r in _csv(rr / "f-35" / "review.csv")}
    assert paths.members.read_bytes() == baseline["members"]


def test_propose_holds_a_lake_change_to_a_ratified_row_for_review(proposing):
    fj, rc, db, paths, rr, _before = _unpack(proposing)
    ruled = {"decided_by": "owner", "ruling_id": F35_RULING_ID, "decided_on": "2026-10-22"}
    jsm = _member_row(F35_PREFILL[2], **ruled)
    assert (jsm["titles_seen"], jsm["budget_activities"], jsm["drift_sha256"]) == ("2026: Joint Strike Missile", "01", "c" * 64)
    add_family(paths, DRAFT_F35, rulings=[_B1_RULING],
               members=[_member_row(F35_PREFILL[0], drift_sha256="0" * 64, **ruled), jsm])
    baseline = _registry_bytes(paths)   # after add_family's two member rows
    out = review.propose(platform_family="f-35", family_json=fj, rows_csv=rc, duckdb_path=db, paths=paths, review_root=rr)
    assert out == {"rows": 3, "era_lines": 1, "held_for_review": 1}
    rows = {r["member_id"]: r for r in _csv(rr / "f-35" / "review.csv")}
    assert JSM000 not in rows
    assert rows[ATA000]["reason"] == ("lake result differs from ratified row f-35|P-1:3010F:AF:ATA000|2017-2026 "
                                      "(drift_sha256) — confirm or keep the ratified row; no silent overturn")
    assert rows[ATA000]["drift_sha256"] == "a" * 64
    assert paths.members.read_bytes() == baseline["members"]


def test_propose_lists_every_error_at_once_and_writes_nothing(proposing):
    _fj, _rc, db, paths, rr, before = _unpack(proposing)
    rows = [dict(row) for row in F35_PREFILL]
    rows[1]["member_order"] = "3"     # 0604800F: rule 16 (1..2)
    rows[2]["purpose"] = "fly"        # JSM000: rule 11
    fj, rc = write_prefill(proposing.tmp_path / "bad", rows)
    with pytest.raises(reg.RegistryError) as e:
        review.propose(platform_family="f-35", family_json=fj, rows_csv=rc, duckdb_path=db, paths=paths, review_root=rr)
    assert len(e.value.errors) >= 2
    assert "f-35|R-1:3600F:AF:0604800F|2017-2023" in str(e.value) and "f-35|P-1:3020F:AF:JSM000|2022-2026" in str(e.value)
    assert "review.csv" in str(e.value)
    assert _registry_bytes(paths) == before
    assert not (rr / "f-35").exists()


@pytest.mark.parametrize("fault", ["header", "bom", "crlf"])
def test_propose_refuses_a_prefill_header_bom_or_crlf(proposing, fault):   # Review Focus 4
    fj, rc, db, paths, rr, before = _unpack(proposing)
    text = rc.read_text(encoding="utf-8")
    if fault == "header":
        lines = list(csv.reader(io.StringIO(text, newline="")))
        at = lines[0].index("reason")
        buf = io.StringIO()
        csv.writer(buf, lineterminator="\n").writerows([line[:at] + line[at + 1:] for line in lines])
        text = buf.getvalue()
    elif fault == "bom":
        text = "﻿" + text
    else:
        text = text.replace("\n", "\r\n")
    rc.write_bytes(text.encode("utf-8"))
    with pytest.raises(reg.RegistryError) as e:
        review.propose(platform_family="f-35", family_json=fj, rows_csv=rc, duckdb_path=db, paths=paths, review_root=rr)
    assert "rows.csv" in str(e.value)
    assert _registry_bytes(paths) == before
    assert not (rr / "f-35").exists()


def test_propose_refuses_a_source_id_that_differs_from_the_shared_list(proposing):
    fj, rc, db, paths, rr, _before = _unpack(proposing)
    add_source(paths, MSAR | {"bytes": 1})
    baseline = _registry_bytes(paths)   # after add_source's "bytes": 1
    with pytest.raises(reg.RegistryError) as e:
        review.propose(platform_family="f-35", family_json=fj, rows_csv=rc, duckdb_path=db, paths=paths, review_root=rr)
    assert "msar-pb2027" in str(e.value)
    assert "duplicate" not in str(e.value)
    assert _registry_bytes(paths) == baseline
    assert not (rr / "f-35").exists()


@pytest.mark.parametrize("tool", ["propose"])
def test_propose_and_ratify_write_nothing_on_a_lock(proposing, request, monkeypatch, capsys, tool):   # Review Focus 5
    fj, rc, db, paths, rr, _before = _unpack(proposing)
    baseline = _registry_bytes(paths)

    def locked(path):
        raise duckdb.IOException(LOCK)

    monkeypatch.setattr(reg, "open_lake", locked)
    argv = ["platform-families", "propose", "--family", "f-35", "--family-json", str(fj), "--rows", str(rc),
            "--duckdb", str(db)]
    assert _exit(argv) == 2
    err = capsys.readouterr().err
    assert err.startswith(f"platform-families {tool}: ERROR — ")
    assert "Could not set lock on file" in err
    assert _registry_bytes(paths) == baseline
    assert not (rr / "f-35").exists()


def _seed_argv(tmp_path, reply) -> list[str]:
    return ["platform-families", "propose", "--seed-shipped", "f-15", "--duckdb", str(tmp_path / "fam2.duckdb"),
            "--site-dir", str(tmp_path / "site"), "--decided-on", "2026-10-21", "--owner-reply", str(reply)]


def test_seed_shipped_wrapper_passes_the_facade_constants(cli_env, monkeypatch, capsys):
    calls = []

    def recorder(**kwargs):
        calls.append(kwargs)
        raise reg.RegistryError(["platform-families: platform_families.json: f-15 already in platform_families.json"])

    monkeypatch.setattr(reg, "seed_shipped_f15", recorder)
    reply = cli_env.tmp_path / "owner-reply.txt"
    reply.write_text(_SEED_REPLY, encoding="utf-8")
    assert _exit(_seed_argv(cli_env.tmp_path, reply)) == 2
    (call,) = calls
    constants = call["constants"]
    for field in dataclasses.fields(reg.F15Constants):
        if field.name != "expected_from":
            assert getattr(constants, field.name) is getattr(f15, field.name.upper()), field.name
    assert constants.expected_from == {"0207134F": 2017, "0207171F": 2017, "0207146F": 2021, "F01500": 2024,
                                       "F015EX": 2024, "F15EWS": 2024, "F0150P": None, "F015E0": None}
    assert call["decided_on"] == "2026-10-21"
    assert call["owner_reply"] == _SEED_REPLY
    assert call["paths"] is reg.DEFAULT_PATHS
    assert (call["duckdb_path"], call["site_dir"]) == (cli_env.tmp_path / "fam2.duckdb", cli_env.tmp_path / "site")
    assert "f-15 already in platform_families.json" in capsys.readouterr().err


def test_seed_shipped_wrapper_refuses_once_the_f15_exists(cli_env, monkeypatch, capsys):
    def locked(path):
        raise duckdb.IOException(LOCK)

    monkeypatch.setattr(reg, "open_lake", locked)   # the one-off refusal comes before any lake read
    baseline = _registry_bytes(cli_env.paths)
    reply = cli_env.tmp_path / "owner-reply.txt"
    reply.write_text(_SEED_REPLY, encoding="utf-8")
    assert _exit(_seed_argv(cli_env.tmp_path, reply)) == 2
    err = capsys.readouterr().err
    assert "f-15" in err and "already" in err
    assert "Could not set lock" not in err
    assert _registry_bytes(cli_env.paths) == baseline


@pytest.mark.parametrize("argv, message", [
    (["--seed-shipped", "f-15", "--family", "f-35", "--duckdb", "D", "--site-dir", "S", "--decided-on", "2026-10-21",
      "--owner-reply", "R"], "--seed-shipped takes --duckdb, --site-dir, --decided-on and --owner-reply only"),
    (["--family", "f-35", "--family-json", "FJ"], "propose needs --family, --family-json and --rows"),
], ids=["seed-with-family", "family-without-rows"])
def test_cli_propose_refuses_mixed_seed_and_family_flags(proposing, capsys, argv, message):
    argv = [str(proposing.fj) if arg == "FJ" else arg for arg in argv]
    assert _exit(["platform-families", "propose", *argv]) == 2
    assert capsys.readouterr().err.strip() == f"platform-families propose: ERROR — {message}"
    assert _registry_bytes(proposing.paths) == proposing.before
