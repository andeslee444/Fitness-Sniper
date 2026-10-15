"""scripts/fu/s195_narratives.py — the #195 write, its pre-image and its
revert (families piece-1 follow-ups, Task 23c), on the synthetic book set."""
import json

import psycopg
import pytest

from fu.s195_narratives import main, state_digest  # scripts/ is on sys.path via conftest
from jbooks.narrative_volumes import seed_book_set, seed_pre_195_rows

STATE = ("select id, pe_bli, page_number, x0, resolution, candidate_pages,"
         " printed_document_sha256, built_at from provenance_pages order by id")


def _state(dsn):
    with psycopg.connect(dsn) as con:
        return con.execute(STATE).fetchall()


def _digest(dsn):
    with psycopg.connect(dsn) as con:
        return state_digest(con)


@pytest.fixture()
def book(pg_dsn, tmp_path):
    seeded = seed_book_set(pg_dsn, tmp_path)
    seed_pre_195_rows(pg_dsn, seeded)
    return seeded


def test_check_reads_only_and_reports_the_plan(pg_dsn, book, tmp_path, capsys):
    before, digest = _state(pg_dsn), _digest(pg_dsn)
    plan_json = tmp_path / "plan.json"
    assert main(["--check", "--plan-json", str(plan_json), "--dsn", pg_dsn]) == 0
    out = capsys.readouterr().out
    assert "rows 6: kept 1, located 1, relocated 1, opening_only 1, unresolved 2" in out
    assert f"cites superseded {book['sha']['BA2']}     1 row(s)  Book BA2" in out
    assert f"state digest: {digest}" in out
    plan = json.loads(plan_json.read_text())
    assert plan["state_digest"] == digest and len(plan["changes"]) == 2
    assert _state(pg_dsn) == before


def test_apply_writes_the_pre_image_then_moves_only_the_planned_rows(pg_dsn, book, tmp_path, capsys):
    pre, before = _digest(pg_dsn), _state(pg_dsn)
    image = tmp_path / "pre.json"
    assert main(["--apply", "--pre-image", str(image), "--expect-pre-digest", pre,
                 "--dsn", pg_dsn]) == 0
    out = capsys.readouterr().out
    doc = json.loads(image.read_text())
    assert doc["pre_digest"] == pre and len(doc["rows"]) == 6
    after = {r[1]: r for r in _state(pg_dsn)}
    assert (after["0605001TST"][2], after["0605001TST"][6]) == (2, book["sha"]["BA2"])
    assert (after["0605002TST"][2], after["0605002TST"][6]) == (1, book["sha"]["BA3"])
    assert sum(1 for r in before if after[r[1]] != r) == 2
    post = _digest(pg_dsn)
    assert post != pre and f"post-write digest: {post}" in out and "committed" in out


def test_apply_refuses_another_pre_state_and_writes_nothing(pg_dsn, book, tmp_path, capsys):
    before, image = _state(pg_dsn), tmp_path / "pre.json"
    assert main(["--apply", "--pre-image", str(image), "--expect-pre-digest", "0" * 32,
                 "--dsn", pg_dsn]) == 1
    assert "nothing written" in capsys.readouterr().err
    assert not image.exists() and _state(pg_dsn) == before


def test_apply_never_overwrites_a_pre_image(pg_dsn, book, tmp_path):
    before, image = _state(pg_dsn), tmp_path / "pre.json"
    image.write_text("{}")
    assert main(["--apply", "--pre-image", str(image), "--dsn", pg_dsn]) == 1
    assert image.read_text() == "{}" and _state(pg_dsn) == before


def test_dry_run_checks_then_rolls_back(pg_dsn, book, tmp_path, capsys):
    before = _state(pg_dsn)
    assert main(["--apply", "--dry-run", "--pre-image", str(tmp_path / "pre.json"),
                 "--dsn", pg_dsn]) == 0
    assert "dry run: rolled back" in capsys.readouterr().out
    assert _state(pg_dsn) == before


def test_revert_restores_every_row_and_the_pre_digest(pg_dsn, book, tmp_path, capsys):
    pre, before, image = _digest(pg_dsn), _state(pg_dsn), tmp_path / "pre.json"
    assert main(["--apply", "--pre-image", str(image), "--dsn", pg_dsn]) == 0
    assert _state(pg_dsn) != before
    assert main(["--revert", "--pre-image", str(image), "--dsn", pg_dsn]) == 0
    assert "reverted 2 row(s)" in capsys.readouterr().out
    assert _state(pg_dsn) == before and _digest(pg_dsn) == pre
    assert main(["--revert", "--pre-image", str(image), "--dsn", pg_dsn]) == 0
    assert "reverted 0 row(s)" in capsys.readouterr().out


def test_the_digest_ignores_file_paths_and_build_times(pg_dsn, book):
    digest = _digest(pg_dsn)
    with psycopg.connect(pg_dsn, autocommit=True) as con:
        con.execute("update jbook_documents set file_path = '/elsewhere/' || id || '.pdf'")
        con.execute("update provenance_pages set built_at = now() - interval '1 day'")
    assert _digest(pg_dsn) == digest
    with psycopg.connect(pg_dsn, autocommit=True) as con:
        con.execute("update provenance_pages set candidate_pages = candidate_pages + 1"
                    " where pe_bli = '0605004TST'")
    assert _digest(pg_dsn) != digest


def test_digest_mode_prints_the_state_digest(pg_dsn, book, capsys):
    assert main(["--digest", "--dsn", pg_dsn]) == 0
    assert capsys.readouterr().out == f"state digest: {_digest(pg_dsn)}\n"


def test_usage_errors_exit_2(pg_dsn):
    with pytest.raises(SystemExit) as exc:
        main(["--apply", "--dsn", pg_dsn])
    assert exc.value.code == 2


# The s194 lessons (controller notes for Task 23c): the DSN, the first line,
# the pre-image's shape and the table's columns.

def test_an_empty_dsn_is_refused_before_any_connection(monkeypatch, capsys):
    import fu.s195_narratives as s195

    def no_connection(*args, **kwargs):
        raise AssertionError("connected")

    monkeypatch.setattr(s195.psycopg, "connect", no_connection)
    for mode in (["--digest"], ["--check"], ["--revert", "--pre-image", "x.json"]):
        assert main([*mode, "--dsn", " "]) == 2
        assert "s195: --dsn is empty; nothing connected" in capsys.readouterr().err
    monkeypatch.setattr(s195.config, "PG_DSN", "")
    assert main(["--digest"]) == 2
    assert "s195: GOVBUDGET_PG_DSN is empty; nothing connected" in capsys.readouterr().err


@pytest.mark.parametrize("argv", [
    ["--revert", "--dry-run", "--pre-image", "x.json"],
    ["--check", "--expect-pre-digest", "0" * 32],
    ["--apply", "--pre-image", "x.json", "--expect-pre-digest", ""],
    ["--apply", "--pre-image", "x.json", "--expect-pre-digest", "XYZ"],
    ["--digest", "--plan-json", "plan.json"],
])
def test_flags_of_another_mode_and_a_malformed_digest_are_usage_errors(argv):
    with pytest.raises(SystemExit) as exc:
        main([*argv, "--dsn", "postgresql://127.0.0.1:1/nowhere"])
    assert exc.value.code == 2


def test_every_mode_names_its_database_first(pg_dsn, book, tmp_path, capsys):
    image = tmp_path / "pre.json"
    for label, mode in (("--digest", ["--digest"]), ("--check", ["--check"]),
                        ("--apply --dry-run", ["--apply", "--dry-run", "--pre-image", str(image)]),
                        ("--revert", ["--revert", "--pre-image", str(image)])):
        assert main([*mode, "--dsn", pg_dsn]) == 0
        err = capsys.readouterr().err
        assert err.splitlines()[0].startswith(
            f"s195 {label}: database 'govbudget_test' on host "), err


@pytest.mark.parametrize("text, why", [
    ("{", "not JSON"),
    ("[]", "a JSON list, not an object"),
    ('{"schema": 1}', "no pre_digest, taken_at, columns, rows"),
    ('{"schema": 2, "pre_digest": "", "taken_at": "", "columns": [], "rows": []}', "schema 2"),
])
def test_a_malformed_pre_image_is_refused_without_a_traceback(pg_dsn, book, tmp_path, capsys,
                                                             text, why):
    before, image = _state(pg_dsn), tmp_path / "pre.json"
    image.write_text(text)
    assert main(["--revert", "--pre-image", str(image), "--dsn", pg_dsn]) == 2
    err = capsys.readouterr().err
    assert f"is not a schema-1 s195 pre-image ({why}" in err and "Traceback" not in err
    assert _state(pg_dsn) == before


def test_a_pre_image_whose_rows_were_edited_is_refused(pg_dsn, book, tmp_path, capsys):
    image = tmp_path / "pre.json"
    assert main(["--apply", "--pre-image", str(image), "--dsn", pg_dsn]) == 0
    after = _state(pg_dsn)
    doc = json.loads(image.read_text())
    doc["rows"][0] = doc["rows"][0][:-1]
    image.write_text(json.dumps(doc))
    assert main(["--revert", "--pre-image", str(image), "--dsn", pg_dsn]) == 2
    assert "rows" in capsys.readouterr().err and _state(pg_dsn) == after
    image.unlink()
    assert main(["--revert", "--pre-image", str(image), "--dsn", pg_dsn]) == 2
    assert "does not exist" in capsys.readouterr().err


def test_apply_and_revert_refuse_a_table_whose_columns_moved(pg_dsn, book, tmp_path, capsys,
                                                             monkeypatch):
    import fu.s195_narratives as s195

    before, image = _state(pg_dsn), tmp_path / "pre.json"
    monkeypatch.setattr(s195, "PAGE_COLUMNS", s195.PAGE_COLUMNS[:-1])
    assert main(["--apply", "--pre-image", str(image), "--dsn", pg_dsn]) == 2
    assert "provenance_pages columns" in capsys.readouterr().err
    assert not image.exists() and _state(pg_dsn) == before
    monkeypatch.undo()
    assert main(["--apply", "--pre-image", str(image), "--dsn", pg_dsn]) == 0
    after = _state(pg_dsn)
    capsys.readouterr()
    monkeypatch.setattr(s195, "PAGE_COLUMNS", (*s195.PAGE_COLUMNS, "extra"))
    assert main(["--revert", "--pre-image", str(image), "--dsn", pg_dsn]) == 2
    assert "provenance_pages columns" in capsys.readouterr().err
    assert _state(pg_dsn) == after
