"""`govbudget platform-families …` (families piece 2; spec §8.3, §9.2, Review Focus 5).

Task 7a: `check`. Task 7b: `propose` and the `--seed-shipped` wrapper. Task 7c:
`preview`, `compare_reference` and `render`. Task 7d appends answer and ratify.
The lake is stubbed through module attributes (reg.open_lake, reg.check_lake,
reg.measure_member) and the history export through hist.export_family_histories.
"""
from __future__ import annotations

import csv
import dataclasses
import datetime
import hashlib
import html
import io
import json
import shutil
from decimal import Decimal
from types import SimpleNamespace

import duckdb
import pytest

from govbudget import cli, config
from govbudget import f15_funding_history as f15
from govbudget import platform_families as reg
import govbudget.platform_family_history as hist
import govbudget.platform_family_review as review
import govbudget.verify_families as vf
from platform_families_helpers import (ATA000, B1_MART, B1_POINTS, B1_REF, DRAFT_F35, EMD, F15_ORDER, F35_PREFILL,
                                       F35_RULING_ID, JSM000, MEASURES, MSAR, FakeLake, add_family, add_source,
                                       f15_registry, fake_export, ratified_f35, site_tree, write_prefill)

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


@pytest.mark.parametrize("tool", ["propose", "ratify"])
def test_propose_and_ratify_write_nothing_on_a_lock(proposing, request, monkeypatch, capsys, tool):   # Review Focus 5
    fj, rc, db, paths, rr, _before = _unpack(proposing)
    if tool == "ratify":
        # Ratify reaches the lake only at step 6, after it has read the answer, the
        # manifest and both review files: build that state first (answering renders B1
        # on the proposing this test holds), then lock the lake.
        a = request.getfixturevalue("answering")
        review.answer(platform_family="f-35", batch="B1", answers_path=a.ans, review_root=rr, out_root=a.out_root)
        baseline = _snap(paths, rr)
        argv = ["platform-families", "ratify", "--family", "f-35", "--batch", "B1", "--decided-on", "2026-10-22",
                "--duckdb", str(db), "--site-dir", str(a.site)]
    else:
        baseline = _registry_bytes(paths)
        argv = ["platform-families", "propose", "--family", "f-35", "--family-json", str(fj), "--rows", str(rc),
                "--duckdb", str(db)]

    def locked(path):
        raise duckdb.IOException(LOCK)

    monkeypatch.setattr(reg, "open_lake", locked)
    assert _exit(argv) == 2
    err = capsys.readouterr().err
    assert err.startswith(f"platform-families {tool}: ERROR — ")
    assert "Could not set lock on file" in err
    if tool == "ratify":
        assert "answer B1 first" not in err
        _assert_unchanged(baseline, paths, rr)
    else:
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


# ---------------------------------------------------------------------------
# preview, compare_reference and render (Task 7c; spec §8.2, §8.3; Review Focus 3)
# ---------------------------------------------------------------------------


@pytest.fixture
def rendering(proposing, monkeypatch):
    """proposing, plus one propose run, B1_REF as reference-b1.json, a snapshot site
    tree, the D10 preview scratch path, the history export stubbed with B1_POINTS and
    the lake with B1_MART."""
    p = proposing
    review.propose(platform_family="f-35", family_json=p.fj, rows_csv=p.rc, duckdb_path=p.db, paths=p.paths,
                   review_root=p.rr)
    (p.rr / "f-35" / "reference-b1.json").write_text(json.dumps(B1_REF, indent=2) + "\n", encoding="utf-8")
    site = site_tree(p.tmp_path)
    scratch = p.tmp_path / "fam2-preview-f-35-B1"
    monkeypatch.setattr(hist, "export_family_histories", fake_export(B1_POINTS))
    monkeypatch.setattr(reg, "open_lake", lambda path: FakeLake(B1_MART))
    return SimpleNamespace(**vars(p), site=site, scratch=scratch)


def _rendered(r):
    return r.site, r.db, r.scratch, r.paths, r.rr


def test_preview_refuses_a_draft_without_the_draft_flag(rendering):
    site, db, scratch, paths, rr = _rendered(rendering)
    with pytest.raises(reg.RegistryError, match="--draft"):
        review.preview(platform_family="f-35", draft=False, site_dir=site, duckdb_path=db, out=scratch, paths=paths, review_root=rr)
    assert not scratch.exists()


def test_preview_refuses_out_inside_the_site_dir(rendering, monkeypatch):
    site, db, _scratch, paths, rr = _rendered(rendering)
    tmp_path = rendering.tmp_path
    monkeypatch.setattr(config, "SITE_DIR", tmp_path / "live-site")
    with pytest.raises(reg.RegistryError, match="inside config.SITE_DIR"):
        review.preview(platform_family="f-35", draft=True, site_dir=site, duckdb_path=db,
                       out=tmp_path / "live-site" / "preview", paths=paths, review_root=rr)
    assert not (tmp_path / "live-site").exists()


def test_preview_builds_the_draft_into_a_scratch_clone(rendering):
    site, db, scratch, paths, rr = _rendered(rendering)
    before = sorted(p.relative_to(site) for p in site.rglob("*"))
    result = review.preview(platform_family="f-35", draft=True, site_dir=site, duckdb_path=db, out=scratch, paths=paths, review_root=rr)
    assert result.years[0] == {"fy": 2015, "kind": "actuals", "edition": 2017, "total_thousands": Decimal("4611600.000")}
    assert result.cumulative_thousands == Decimal("4611600.000")
    assert result.member_years[("P-1:3010F:AF:ATA000", 2015, "actuals")] == Decimal("4044700.000")
    assert (scratch / review.PREVIEW_MARKER).is_file() and sorted(p.relative_to(site) for p in site.rglob("*")) == before
    (call,) = hist.export_family_histories.calls
    assert call["families"] == ["f-35"] and call["preview"] is True and call["out_dir"] == scratch
    assert call["registry"]["f-35"].status == "ratified"
    assert [m.member_id for m in call["registry"]["f-35"].counted] == ["P-1:3010F:AF:ATA000", "R-1:3600F:AF:0604800F"]


def test_preview_replaces_only_its_own_scratch(rendering):
    site, db, scratch, paths, rr = _rendered(rendering)
    kw = dict(platform_family="f-35", draft=True, site_dir=site, duckdb_path=db, out=scratch, paths=paths, review_root=rr)
    scratch.mkdir(); (scratch / "keep.txt").write_text("x")
    with pytest.raises(reg.RegistryError, match="not a preview scratch"):
        review.preview(**kw)
    assert (scratch / "keep.txt").read_text() == "x"
    shutil.rmtree(scratch); review.preview(**kw); review.preview(**kw)  # second run replaces


def test_preview_compares_at_b1_precision(tmp_path):            # Review Focus 3
    ata = "P-1:3010F:AF:ATA000"
    ref = {"lines": {"ATA000": {"2015": 4044.7, "2025": 4972.5, "2026": 4086.7}},
           "totals": {"2015": 4044.7, "2025": 4972.5, "2026": 4086.7}, "cumulative": 4044.7,
           "fy2025_enacted": 4972.5, "fy2026_request": 4086.7}
    def result(k2015):
        years = [(2015, "actuals", 2017, k2015), (2025, "enacted", 2026, "4972500"), (2026, "request", 2026, "4086700")]
        return review.PreviewResult(years=[{"fy": f, "kind": k, "edition": e, "total_thousands": Decimal(t)} for f, k, e, t in years],
                                    cumulative_thousands=Decimal(k2015),
                                    member_years={(ata, f, k): Decimal(t) for f, k, e, t in years}, out_dir=tmp_path)
    lake = FakeLake({"ATA000": {(2015, "actuals"): Decimal("4044700"), (2025, "enacted"): Decimal("4972500"), (2026, "request"): Decimal("4086700")}})
    assert review.compare_reference(result("4044650"), ref, lake=lake) == []       # 4044.65 → 4044.7 only under ROUND_HALF_UP
    diffs = review.compare_reference(result("4044649.999"), ref, lake=lake)
    assert {"fy": 2015, "kind": "actuals", "member_id": ata, "preview_k": Decimal("4044649.999"),
            "reference_m": Decimal("4044.7"), "cause": "proposal row", "blocks": True} in diffs
    assert len(diffs) == 3 and all(d["blocks"] for d in diffs)   # the member, the FY2015 total, the cumulative


def test_preview_keeps_real_zero_distinct_from_absent(tmp_path):  # Review Focus 3
    f40, n10 = "R-1:3600F:AF:0604840F", "R-1:1319N:NAVY:0604810N"
    ref = {"lines": {"0604840F": {"2018": 0.0, "2019": 0.0, "2026": 1182.1}, "0604810N": {"2019": None, "2020": None, "2026": None}},
           "totals": {"2018": 0.0, "2019": 0.0, "2026": 1182.1}, "cumulative": 0.0, "fy2025_enacted": None, "fy2026_request": 1182.1}
    member_years = {(f40, 2019, "actuals"): Decimal("0"), (f40, 2026, "request"): Decimal("1182100"), (n10, 2019, "actuals"): Decimal("0")}
    result = review.PreviewResult(   # years and cumulative agree with ref; 0604840F FY2018 is absent from the preview
        years=[{"fy": 2018, "kind": "actuals", "edition": 2020, "total_thousands": Decimal("0")},
               {"fy": 2019, "kind": "actuals", "edition": 2021, "total_thousands": Decimal("0")},
               {"fy": 2026, "kind": "request", "edition": 2026, "total_thousands": Decimal("1182100")}],
        cumulative_thousands=Decimal("0"), member_years=member_years, out_dir=tmp_path)
    lake = FakeLake({"0604840F": {(2018, "actuals"): Decimal("0"), (2019, "actuals"): Decimal("0"), (2026, "request"): Decimal("1182100")}})
    diffs = {(d["fy"], d["member_id"]): d for d in review.compare_reference(result, ref, lake=lake) if d["member_id"]}
    assert set(diffs) == {(2018, f40), (2019, n10)}
    assert (diffs[(2018, f40)]["preview_k"], diffs[(2018, f40)]["reference_m"]) == (None, Decimal("0.0"))
    assert (diffs[(2019, n10)]["preview_k"], diffs[(2019, n10)]["reference_m"]) == (Decimal("0"), None)
    assert all(d["cause"] == "proposal row" for d in diffs.values())


def test_render_blocks_a_proposal_row_difference_and_shows_lake_drift(rendering, monkeypatch):  # Review Focus 3
    site, db, scratch, _paths, rr = _rendered(rendering)
    out_root = rendering.out_root
    wrong = [(2015, "actuals", 2017, "4611549.999", {"P-1:3010F:AF:ATA000": "4044649.999", "R-1:3600F:AF:0604800F": "566900.000"}), *B1_POINTS[1:]]  # 4044.6 ≠ 4044.7
    monkeypatch.setattr(hist, "export_family_histories", fake_export(wrong))
    with pytest.raises(reg.RegistryError, match="proposal row"):
        review.render(platform_family="f-35", batch="B1", duckdb_path=db, site_dir=site, review_root=rr, out_root=out_root, preview_out=scratch)
    assert not (out_root / "f-35" / "B1.html").exists() and not (out_root / "f-35" / "B1.json").exists()
    drift = [(2015, "actuals", 2017, "4616900.000", {"P-1:3010F:AF:ATA000": "4050000.000", "R-1:3600F:AF:0604800F": "566900.000"}), *B1_POINTS[1:]]
    monkeypatch.setattr(hist, "export_family_histories", fake_export(drift))
    monkeypatch.setattr(reg, "open_lake", lambda p: FakeLake(B1_MART | {"ATA000": B1_MART["ATA000"] | {(2015, "actuals"): Decimal("4050000")}}))
    out = review.render(platform_family="f-35", batch="B1", duckdb_path=db, site_dir=site, review_root=rr, out_root=out_root, preview_out=scratch)
    assert out["differences"] == 3
    assert "lake since 2026-10-19" in out["page"].read_text()
    member = [d for d in json.loads(out["manifest"].read_text())["preview"]["differences"] if d["member_id"]]
    assert member == [{"fy": 2015, "kind": "actuals", "member_id": "P-1:3010F:AF:ATA000", "preview_k": "4050000.000",
                       "reference_m": "4044.7", "cause": "lake since 2026-10-19", "blocks": False}]


def test_render_writes_no_page_when_the_preview_fails(rendering, monkeypatch):
    site, db, scratch, _paths, rr = _rendered(rendering)

    def failing(**kwargs):
        raise ValueError("Unreviewed F-35 workbook identity: 2026/0604999F")

    monkeypatch.setattr(hist, "export_family_histories", failing)
    with pytest.raises(ValueError, match="Unreviewed F-35 workbook identity: 2026/0604999F"):
        review.render(platform_family="f-35", batch="B1", duckdb_path=db, site_dir=site, review_root=rr,
                      out_root=rendering.out_root, preview_out=scratch)
    assert list((rendering.out_root / "f-35").glob("B1.*")) == []


def test_render_orders_the_page_and_records_the_manifest(rendering):
    site, db, scratch, paths, rr = _rendered(rendering)
    out = review.render(platform_family="f-35", batch="B1", duckdb_path=db, site_dir=site, review_root=rr,
                        out_root=rendering.out_root, preview_out=scratch)
    assert (out["rows"], out["differences"]) == (4, 0)
    page = out["page"].read_text(encoding="utf-8")
    text = html.unescape(page)
    assert (page.index("P-1:3010F:AF:ATA000") < page.index("R-1:3600F:AF:0604800F") < page.index("not counted")
            < page.index("P-1:3020F:AF:JSM000") < page.index("R-1:3600F:AF:0207268F") < page.index("Exclusions"))
    assert "53,368.3" in text and "1,939.5" in text
    quote = ("yes this is good, except we should break out the sub contractors because it doesn't end with lockheed "
             "and pratt & W")
    assert quote == review.PRIOR_APPROVALS["f-35"][1] and quote in text
    assert "piece 7" in text
    assert "src:msar-pb2027#p25 (G)" in text and "era:ATA000|3010F||2017-2023 (era decision)" in text
    manifest = json.loads(out["manifest"].read_text(encoding="utf-8"))
    assert set(manifest) == {"schema_version", "platform_family", "batch", "rows", "review_sha256",
                             "review_era_lines_sha256", "family_sha256", "preview"}
    assert set(manifest["preview"]) == {"years", "cumulative_thousands", "differences"}
    assert [r["member_row_id"] for r in manifest["rows"]] == [
        "f-35|P-1:3010F:AF:ATA000|2017-2026", "f-35|R-1:3600F:AF:0604800F|2017-2023",
        "f-35|P-1:3020F:AF:JSM000|2022-2026", "f-35|R-1:3600F:AF:0207268F|2017-2026"]
    assert manifest["review_sha256"] == hashlib.sha256((rr / "f-35" / "review.csv").read_bytes()).hexdigest()
    assert manifest["review_era_lines_sha256"] == hashlib.sha256(
        (rr / "f-35" / "review_era_lines.csv").read_bytes()).hexdigest()
    assert manifest["family_sha256"] == reg.family_hash(json.loads(paths.json.read_text(encoding="utf-8")), "f-35")
    assert manifest["preview"]["years"][0] == {"fy": 2015, "kind": "actuals", "edition": 2017,
                                               "total_thousands": "4611600.000"}
    assert manifest["preview"]["differences"] == []


def test_compare_reference_refuses_a_reference_whose_named_years_disagree(tmp_path):
    result = review.PreviewResult(years=[], cumulative_thousands=Decimal("0"), member_years={}, out_dir=tmp_path)
    with pytest.raises(ValueError, match=r"fy2025_enacted 1.0 differs from totals\[2025\] 4972.5"):
        review.compare_reference(result, B1_REF | {"fy2025_enacted": 1.0}, lake=FakeLake(B1_MART))


@pytest.mark.parametrize("argv", [
    ["platform-families", "render", "--family", "f-35", "--batch", "B1"],
    ["platform-families", "preview", "--family", "f-35", "--draft", "--out", "x"],
], ids=["render", "preview"])
def test_cli_render_and_preview_require_duckdb_and_site_dir(argv):
    assert _exit(argv) == 2


# ---------------------------------------------------------------------------
# answer and ratify (Task 7d; spec §8.2, §8.3, §9.1 rules 16, 22, 23, 25; Review Focus 1 and 5)
# ---------------------------------------------------------------------------

ATA, F00, JSM, SLICE = ("f-35|P-1:3010F:AF:ATA000|2017-2026", "f-35|R-1:3600F:AF:0604800F|2017-2023",
                        "f-35|P-1:3020F:AF:JSM000|2022-2026", "f-35|R-1:3600F:AF:0207268F|2017-2026")


def _sha(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _answers(path, *, rows, decided_on="2026-10-22", owner_reply="approved", **extra):
    """Write the owner's answers to B1 at `path`: {"batch": "B1", decided_on, owner_reply, rows},
    with any `extra` keys after them. Returns `path`."""
    obj = {"batch": "B1", "decided_on": decided_on, "owner_reply": owner_reply, "rows": rows, **extra}
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _snap(paths, rr) -> dict:
    """The bytes of the three registry files and both review files."""
    return {p: p.read_bytes() for p in (paths.json, paths.members, paths.era_lines, *review.review_files(rr, "f-35"))}


def _assert_unchanged(baseline, paths, rr) -> None:
    assert _snap(paths, rr) == baseline


@pytest.fixture
def answering(rendering, monkeypatch):
    """rendering, plus B1 rendered once (no differences) under out_root (the patched
    review.OUT_ROOT), the owner's answers B1-answers.json (no amendments, decided_on
    2026-10-22, reply "approved"), the lake measures stubbed with MEASURES and stage 2
    with an empty report."""
    r = rendering
    out = review.render(platform_family="f-35", batch="B1", duckdb_path=r.db, site_dir=r.site, review_root=r.rr,
                        out_root=r.out_root, preview_out=r.scratch)
    assert out["differences"] == 0
    ans = _answers(r.tmp_path / "B1-answers.json", rows={})
    monkeypatch.setattr(reg, "measure_member", lambda lake, member, *, headline: MEASURES[member.member_id])
    monkeypatch.setattr(reg, "check_lake", lambda r, **kw: reg.LakeReport([], [], []))
    return SimpleNamespace(**vars(r), ans=ans)


def _answer(a):
    return review.answer(platform_family="f-35", batch="B1", answers_path=a.ans, review_root=a.rr, out_root=a.out_root)


def _ratify(a, decided_on="2026-10-22"):
    return review.ratify(platform_family="f-35", batch="B1", decided_on=decided_on, duckdb_path=a.db, site_dir=a.site,
                         paths=a.paths, review_root=a.rr, out_root=a.out_root)


def test_answer_writes_the_batch_file_with_both_shas(answering):
    a = answering
    path = review.answer(platform_family="f-35", batch="B1", answers_path=a.ans, review_root=a.rr, out_root=a.out_root)
    assert path == a.rr / "f-35" / "batches" / "B1.json"
    got = json.loads(path.read_text())
    assert got == {"batch": "B1", "decided_on": "2026-10-22", "owner_reply": "approved", "rows": {},
                   "review_sha256": _sha(a.rr / "f-35" / "review.csv"),
                   "manifest_sha256": _sha(a.out_root / "f-35" / "B1.json")}
    assert list(got)[-2:] == ["review_sha256", "manifest_sha256"]
    assert path.read_text(encoding="utf-8") == json.dumps(got, indent=2, ensure_ascii=False) + "\n"


@pytest.mark.parametrize("change,needle", [({"extra": 1}, "unknown key"), ({"owner_reply": "  "}, "owner_reply"),
                                           ({"decided_on": "20261022"}, "not an ISO date")])
def test_answer_refuses_unknown_keys_a_blank_reply_or_a_non_iso_date(answering, change, needle):
    a = answering
    _answers(a.ans, rows={}, **change)
    with pytest.raises(reg.RegistryError) as e:
        _answer(a)
    assert needle in str(e.value)
    assert not (a.rr / "f-35" / "batches" / "B1.json").exists()


def test_answer_refuses_a_changed_review_csv(answering):
    a = answering
    review_csv = a.rr / "f-35" / "review.csv"
    text = review_csv.read_text(encoding="utf-8")
    assert text.count("waits for the project-slice pilot") == 1
    review_csv.write_text(text.replace("waits for the project-slice pilot", "waits for the slice pilot"),
                          encoding="utf-8")
    with pytest.raises(reg.RegistryError, match="changed since B1 was rendered"):
        _answer(a)
    assert not (a.rr / "f-35" / "batches" / "B1.json").exists()


@pytest.mark.parametrize("column", ["member_id", "valid_from_edition", "drift_sha256", "titles_seen", "member_order"])
def test_answer_refuses_identity_edition_or_lake_column_amendments(answering, column):   # Review Focus 1
    a = answering
    _answers(a.ans, rows={ATA: {column: "x"}})
    with pytest.raises(reg.RegistryError) as e:
        _answer(a)
    assert f"{ATA}: {column} is not amendable in an answer" in str(e.value) and "re-run propose" in str(e.value)
    assert not (a.rr / "f-35" / "batches" / "B1.json").exists()


def test_answer_refuses_a_row_not_on_the_page(answering):               # Review Focus 1
    a = answering
    _answers(a.ans, rows={"f-35|P-1:3010F:AF:F03500|2017-2026": {"note": "x"}})
    with pytest.raises(reg.RegistryError, match=r"f-35\|P-1:3010F:AF:F03500\|2017-2026 is not on the B1 page"):
        _answer(a)
    assert not (a.rr / "f-35" / "batches" / "B1.json").exists()


def test_ratify_writes_members_era_lines_and_the_batch_ruling(answering):
    a = answering
    _answers(a.ans, rows={JSM: {"note": "context only"}})
    _answer(a)
    out = review.ratify(platform_family="f-35", batch="B1", decided_on="2026-10-22", duckdb_path=a.db, site_dir=a.site,
                        paths=a.paths, review_root=a.rr, out_root=a.out_root)
    assert out == {"members": 4, "era_lines": 1, "ruling_id": "R-DEC-FAM-F35-B1", "status": "ratified"}
    registry = reg.load_registry(a.paths)
    ruling = registry.rulings["R-DEC-FAM-F35-B1"]
    assert (registry["f-35"].status, ruling.kind, ruling.platform_family, ruling.decided_by, ruling.decided_on,
            ruling.owner_reply, ruling.seed_basis) == ("ratified", "batch", "f-35", "owner", "2026-10-22", "approved", False)
    assert ruling.spec == review.BATCH_RULING_SPEC and ruling.spec.endswith("#82-r-dec-fam-f35-b1-one-batch-through-the-batch-page")
    rows = {r["member_row_id"]: r for r in _csv(a.paths.members) if r["platform_family"] == "f-35"}
    assert [rows[i]["member_order"] for i in (ATA, F00, JSM, SLICE)] == ["1", "2", "", ""]
    assert {r["ruling_id"] for r in rows.values()} == {"R-DEC-FAM-F35-B1"} and rows[JSM]["note"] == "context only"
    assert rows[SLICE]["verdict"] == "deferred"
    assert [r["member_id"] for r in _csv(a.paths.era_lines) if r["platform_family"] == "f-35"] == ["P-1:3010F:AF:ATA000"]
    assert [m.member_id for m in registry["f-15"].counted] == F15_ORDER        # F-15 untouched


def test_ratify_renumbers_member_order_after_a_deferral(answering):     # Review Focus 1
    a = answering
    _answers(a.ans, rows={ATA: {"defer": True}})
    _answer(a)
    out = _ratify(a)
    rows = {r["member_row_id"]: r for r in _csv(a.paths.members) if r["platform_family"] == "f-35"}
    assert (rows[ATA]["verdict"], rows[ATA]["member_order"], rows[F00]["member_order"]) == ("deferred", "", "1")
    assert out["era_lines"] == 0


def test_ratify_refuses_a_decided_on_unlike_the_answer(answering):      # Review Focus 1
    a = answering
    _answer(a)
    baseline = _snap(a.paths, a.rr)
    with pytest.raises(reg.RegistryError, match="--decided-on 2026-10-23 differs from the answer's decided_on 2026-10-22"):
        _ratify(a, decided_on="2026-10-23")
    _assert_unchanged(baseline, a.paths, a.rr)


def test_ratify_refuses_a_family_object_changed_since_the_render(answering):
    a = answering
    _answer(a)
    doc = json.loads(a.paths.json.read_text(encoding="utf-8"))
    next(f for f in doc["families"] if f["platform_family"] == "f-35")["scope_note"] = "Edited."
    a.paths.json.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    baseline = _snap(a.paths, a.rr)     # holds the edit
    with pytest.raises(reg.RegistryError, match="family object changed since B1 was rendered"):
        _ratify(a)
    _assert_unchanged(baseline, a.paths, a.rr)


def test_ratify_refuses_a_reused_batch(answering):
    a = answering
    _answer(a)
    _ratify(a)
    baseline = _snap(a.paths, a.rr)
    with pytest.raises(reg.RegistryError, match="R-DEC-FAM-F35-B1 already exists"):
        _ratify(a)
    _assert_unchanged(baseline, a.paths, a.rr)


def test_ratify_refuses_a_lake_hash_unlike_the_review_time_drift(answering, monkeypatch):
    a = answering
    _answer(a)
    monkeypatch.setitem(MEASURES, EMD, dataclasses.replace(MEASURES[EMD], drift_sha256="e" * 64))
    baseline = _snap(a.paths, a.rr)
    with pytest.raises(reg.RegistryError) as e:
        _ratify(a)
    assert f"{F00}: drift_sha256 {'e' * 64} differs from the review-time {'b' * 64}" in str(e.value)
    _assert_unchanged(baseline, a.paths, a.rr)


def test_ratify_lists_every_refusal_at_once_and_writes_nothing(answering, monkeypatch):
    a = answering
    _answer(a)
    monkeypatch.setitem(MEASURES, EMD, dataclasses.replace(MEASURES[EMD], drift_sha256="e" * 64))
    baseline = _snap(a.paths, a.rr)
    with pytest.raises(reg.RegistryError) as e:
        _ratify(a, decided_on="2026-10-23")
    errors = e.value.errors
    assert any("--decided-on 2026-10-23 differs from the answer's decided_on 2026-10-22" in line for line in errors)
    assert any(f"{F00}: drift_sha256 {'e' * 64} differs from the review-time {'b' * 64}" in line for line in errors)
    _assert_unchanged(baseline, a.paths, a.rr)


def test_propose_render_answer_ratify_round_trip(proposing, monkeypatch, capsys):
    p = proposing
    site = site_tree(p.tmp_path)
    monkeypatch.setattr(hist, "export_family_histories", fake_export(B1_POINTS))
    monkeypatch.setattr(reg, "open_lake", lambda path: FakeLake(B1_MART))
    monkeypatch.setattr(reg, "check_lake", lambda r, **kw: reg.LakeReport([], [], []))
    ans = _answers(p.tmp_path / "B1-answers.json", rows={})
    db, s = str(p.db), str(site)

    def run(argv):   # each command exits 0 or returns
        try:
            cli.main(["platform-families", *argv])
        except SystemExit as exit_:
            assert exit_.code == 0, capsys.readouterr().err

    run(["propose", "--family", "f-35", "--family-json", str(p.fj), "--rows", str(p.rc), "--duckdb", db])
    (p.rr / "f-35" / "reference-b1.json").write_text(json.dumps(B1_REF, indent=2) + "\n", encoding="utf-8")
    run(["render", "--family", "f-35", "--batch", "B1", "--duckdb", db, "--site-dir", s,
         "--preview-out", str(p.tmp_path / "fam2-preview-f-35-B1")])
    run(["answer", "--family", "f-35", "--batch", "B1", "--answers", str(ans)])
    run(["ratify", "--family", "f-35", "--batch", "B1", "--decided-on", "2026-10-22", "--duckdb", db, "--site-dir", s])
    run(["check"])
    out = capsys.readouterr().out.splitlines()
    assert (p.out_root / "f-35" / "B1.html").is_file() and (p.out_root / "f-35" / "B1.json").is_file()
    batch_file = p.rr / "f-35" / "batches" / "B1.json"
    assert (f"platform-families answer: f-35 B1 -> {batch_file}; next: platform-families ratify --family f-35"
            " --batch B1 --decided-on 2026-10-22") in out
    assert ("platform-families ratify: f-35 ratified as R-DEC-FAM-F35-B1; 4 member row(s), 1 era line(s)"
            " -> data-seeds/") in out
    assert reg.load_registry(p.paths)["f-35"].status == "ratified"
    assert out[-1] == "platform-families check: families=2 failures=0 undecided=0 stale=0"
