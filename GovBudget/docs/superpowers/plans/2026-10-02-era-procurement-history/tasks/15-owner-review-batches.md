<!-- Part of the families piece-1 plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; ../notes.md has background. -->

### Task 15: Owner review batches → ratify → close S2

**Spec:** §5.3 (individual decisions, batches of about 25, largest dollars first, private page, approved or amended in chat, `ratify` writes `decided_by=owner`, `decided_on`, `ruling=R-DEC-ERA-B<n>`), §7 (undecided severity rule: warn while S2 batches are in review, error in the commit that closes S2), §9 S2 ("the closing commit flips `no_undecided` to error"). (§5.2's R-DEC-ERA-EXCLUDE correction was confirmed by the owner at plan review, 2026-10-02; batches do not repeat it.)
**Files:**
- Create: `scripts/era/review_batch_page.py`
- Test: `tests/test_era_review_batch_page.py`
- Create (one per batch): `data/research/era_map/batches/B<n>.json` (the owner's reply verbatim and its structured answers)
- Modify (per batch, only through the tools): `data/research/era_map/review.csv` (`answer`, then `era-map propose`), `data/research/era_map/chains.csv` and `data/research/era_map/counts.json` (`era-map propose`; `keys.csv` is rewritten unchanged), `dbt/seeds/p1_era_code_decisions.csv` (`era-map ratify`)
- Delete: `dbt/tests/warn_p1_era_map_undecided.sql` (Task 13 Step 7)
- Create: `dbt/tests/assert_p1_era_map_no_undecided.sql`
- Modify: `tests/test_p1_era_line_map_sql.py` — Task 13's `test_warn_test_lists_undecided_and_stale_keys` (the function directly after `test_singular_test_passes_on_the_clean_fixture`)
- Modify: `dbt/models/marts/schema.yml` — the last clause of Task 13 Step 10's `p1_era_line_map` description
- Modify: `docs/superpowers/ROADMAP.md` — the "Platform families (2026-10-02)" paragraph under "## Current priorities" (anchor: it ends with `` `wip/other-session-families-layout-2026-09-29`. ``)

Line numbers cited below are hints (anchor on the quoted text; line numbers are approximate). The steps that run `era-map check`/`ratify`/`propose` or read the warehouse (Steps 6, 12, 13, 14, 18, 19) open the live lake and start with the SAM guard: on `WAIT: SAM window …`, wait until :23 and re-run the block.

**Interfaces:**
Consumes: `govbudget.jbooks.era_map.{DECISIONS, REVIEW_COLUMNS, CHAIN_COLUMNS, SEED_COLUMNS, ORG_SPLIT_CODES, chain_id, parse_chain_id, read_csv, read_seed, write_csv, propose, ratify, check}` (Tasks 10–12); CLI `govbudget era-map propose [--decided-on]`, `govbudget era-map ratify --batch B<n> --decided-on DATE`, `govbudget era-map check [--strict]` (Task 12); `data/research/era_map/{review.csv,chains.csv}` (Task 11); test helpers `jbooks.era_map_fixtures.{make_lake,make_raw_docs}` (Task 11); `scripts/era/env.sh` (Task 1); dbt `p1_era_line_map`, `dbt/tests/warn_p1_era_map_undecided.sql`, `tests/test_p1_era_line_map_sql.py` (`_lake`, `_failures`, `ALL_TESTS`), the `p1_era_line_map` entry of `dbt/models/marts/schema.yml` (Task 13).
Produces: `scripts/era/review_batch_page.py` with `BATCH_SIZE = 25`, `ANSWER_FIELDS`, `CHAIN_FIELDS`, `ANSWERS_KEYS`, `ReviewError(ValueError)`, `read_review(path) -> list[dict]`, `read_chains(path) -> dict[str, dict]`, `seed_chain_ids(seed_path) -> set[str]`, `label(row) -> str`, `next_batch(rows, decided, size=25) -> tuple[list[dict], int]`, `fmt_usd_k(Decimal) -> str`, `collision_pins_missing(row, collision_codes) -> list[str]`, `read_collision_codes(path) -> frozenset[str]`, `render_page(batch, rows, remaining, chains, collision_codes=frozenset()) -> str`, `apply_answers(rows, shown, answers) -> tuple[list[dict], dict]`, `main(argv=None) -> int`; CLI `python scripts/era/review_batch_page.py render --batch N [--review F] [--chains F] [--counts F] [--seed F] [--out-dir D]` (reads the PB2026 collision codes from `counts.json` beside review.csv) and `answer --batch N --answers F [--review F] [--out-dir D]`; seed rows ruled `R-DEC-ERA-B1…B<k>`; `dbt/tests/assert_p1_era_map_no_undecided.sql` (default, error severity; same predicate as the warn test); the live `p1_era_code_decisions` and `p1_era_line_map` rebuilt with every decision.

review.csv is Task 11's file and Task 12's ratify input, exactly `era_map.REVIEW_COLUMNS` (`chain_id, first_edition, last_edition, titles_by_edition, modern_title, accounts, continuity, actuals_k, proposed_decision, reason, program_account, program_org, successor_code, keys_sha256, decision, note`), one row per chain. This tool never adds a column. A range split is two or more copies of a chain's row that differ only in `first_edition`/`last_edition` (and the answers), each keeping the chain's `keys_sha256` — ratify compares that with the whole chain in the lake, then hashes each range itself (Task 12 `test_ratify_merges_a_batch_with_a_range_split`). The page reads `n_keys`, `classes`, `successor_account` and `successor_evidence` from chains.csv beside review.csv.

Measured (read-only, on G3's research-pass `propose` output — a scratch copy of the lake carrying the column-I codes S1 loads — after Task 11 Step 9's org-clash pre-fill): review.csv holds 125 chains (108 proposed `same_program`, 12 `history_only`, 5 with no proposal; none carries a successor). One proposal is not ratifiable as it stands: `20|0300D|DCAA` (PB2017–21) is proposed `same_program` with blank pins on a PB2026 collision code (the PB2026 `20` pages are DCSA and DTRA), and ratify requires both `program_account` and `program_org` there, so `render_page` marks it **needs your decision** and says which pins are missing (pre-flight ruling 2026-10-03). Batch B1 is 25 chains with $63.25B of era actuals, 4 of them without a proposal, and leaves 100 undecided. The test file below passes (41 tests) against G3's Task 10–12 `era_map` in a scratch tree, including the end-to-end test that runs `ratify` on what `answer` writes.

- [ ] **Step 1: Write the failing renderer/answer tests**

Create `tests/test_era_review_batch_page.py`:

```python
"""scripts/era/review_batch_page.py — owner review batches (Task 15, spec §5.3)."""
import csv
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from era.review_batch_page import (  # scripts/ is on sys.path via conftest
    BATCH_SIZE,
    ReviewError,
    apply_answers,
    fmt_usd_k,
    main,
    next_batch,
    read_collision_codes,
    render_page,
)
from govbudget.jbooks import era_map
from govbudget.jbooks.era_map import CHAIN_COLUMNS, REVIEW_COLUMNS, SEED_COLUMNS, write_csv
from jbooks.era_map_fixtures import make_lake, make_raw_docs


def cid(i):
    return f"C{i:03d}|3010F|"


def row(i, actuals="1000", **changes):
    """One review.csv row exactly as `era-map propose` writes it (era_map.REVIEW_COLUMNS)."""
    base = dict.fromkeys(REVIEW_COLUMNS, "")
    base.update(
        chain_id=cid(i), first_edition="2017", last_edition="2023",
        titles_by_edition="2017: OLD TITLE; 2018: OLD TITLE | OLD TITLE (AP); 2023: NEW TITLE",
        modern_title="NEW TITLE", accounts="era=3010F; modern=3010F", continuity="3/3",
        actuals_k=actuals, proposed_decision="same_program",
        reason="R1: renamed, continuity 3/3 holds (title Jaccard 0.50)", keys_sha256="ab" * 32,
    )
    base.update(changes)
    return base


def chains_for(rows, **changes):
    return {r["chain_id"]: {"n_keys": "7", "classes": "A1+R1", "successor_account": "",
                            "successor_evidence": "", **changes} for r in rows}


def test_batch_is_the_25_largest_open_chains():
    rows = [row(i, actuals=str(i * 10)) for i in range(30)]
    rows[29]["decision"] = "same_program"          # answered, not yet ratified
    batch, open_count = next_batch(rows, {cid(28)})  # C028 already in the seed
    assert BATCH_SIZE == 25
    assert open_count == 28
    assert [r["chain_id"] for r in batch] == [cid(i) for i in range(27, 2, -1)]


def test_equal_dollars_break_ties_on_chain_id():
    batch, _ = next_batch([row(2, actuals="5"), row(1, actuals="5"), row(3, actuals="9")], set())
    assert [r["chain_id"] for r in batch] == [cid(3), cid(1), cid(2)]


def test_dollars_print_in_the_scale_the_owner_reads():
    assert fmt_usd_k(Decimal("1234567")) == "$1.23B"
    assert fmt_usd_k(Decimal("4500")) == "$4.50M"
    assert fmt_usd_k(Decimal("12")) == "$12.00K"
    assert fmt_usd_k(Decimal("0")) == "$0"


def test_page_escapes_every_source_string():
    hostile = row(1, titles_by_edition='2017: <script>alert(1)</script> & "Co"',
                  reason="<b>bold</b>", modern_title="A&B")
    page = render_page("B1", [hostile], 0, chains_for([hostile], successor_evidence="<i>x</i>"))
    assert "<script>alert" not in page and "<b>bold</b>" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt; &amp; &quot;Co&quot;" in page
    assert "&lt;b&gt;bold&lt;/b&gt;" in page and "A&amp;B" in page


def test_page_is_an_artifact_fragment_numbered_in_batch_order():
    rows = [row(i, actuals=str(100 - i)) for i in range(3)]
    page = render_page("B3", rows, 40, chains_for(rows))
    assert page.startswith("<title>Era map review B3</title>")
    assert "<html" not in page and "<body" not in page and "<!doctype" not in page.lower()
    assert ':root:not([data-theme="light"])' in page and ':root[data-theme="dark"]' in page
    assert "body{background:var(--paper)" in page
    assert page.count('<li class="chain"') == 3
    assert page.index('id="row-1"') < page.index("C000|3010F||2017-2023") < page.index('id="row-2"')
    assert "7 era lines · class A1+R1" in page
    assert "2017: OLD TITLE\n2018: OLD TITLE | OLD TITLE (AP)\n2023: NEW TITLE" in page
    assert "era=3010F; modern=3010F" in page and "3/3" in page
    assert "40 undecided chains will remain after this batch" in page


def test_page_flags_a_chain_with_no_proposal_and_shows_pins_and_the_stated_successor():
    rows = [row(1, proposed_decision="", program_account="1611N", program_org="N",
                successor_code="5731D15610")]
    page = render_page("B1", rows, 0, chains_for(rows, successor_account="2035A",
                                                  successor_evidence="FY 2024 P-1 line 5731D15610"))
    assert '<span class="chip chip-other">needs your decision</span>' in page
    assert "joins account 1611N · joins org N" in page
    assert "<code>5731D15610</code> 2035A" in page and "FY 2024 P-1 line 5731D15610" in page


def test_page_needs_every_chain_in_chains_csv():
    with pytest.raises(ReviewError, match="chains.csv has no row"):
        render_page("B1", [row(1)], 0, {})


def test_page_flags_a_collision_code_proposal_without_both_pins():
    # Task 12 ratify refuses same_program/history_only on a PB2026 collision
    # code unless program_account AND program_org are set (e.g. the live
    # 20|0300D|DCAA, proposed same_program with blank pins): the page says so.
    rows = [row(1, chain_id="20|0300D|DCAA", proposed_decision="same_program"),
            row(2, chain_id="500|0300D|DCMA", proposed_decision="history_only",
                program_account="0300D", program_org="DCMA"),
            row(3, chain_id="3010|1611N|", proposed_decision="history_only", program_account="1611N"),
            row(4, chain_id="C004|3010F|", proposed_decision="same_program")]
    page = render_page("B1", rows, 0, chains_for(rows), collision_codes=frozenset({"20", "500", "3010"}))
    items = page.split('<li class="chain"')[1:]
    assert '<span class="chip chip-other">needs your decision</span>' in items[0]
    assert ("PB2026 collision code 20: same_program needs program_account and program_org" in items[0])
    assert "needs your decision" not in items[1] and "joins account 0300D · joins org DCMA" in items[1]
    assert "PB2026 collision code 3010: history_only needs program_org" in items[2]
    assert "needs your decision" not in items[3] and "chip-same" in items[3]


def test_collision_codes_come_from_counts_json(tmp_path):
    counts = tmp_path / "counts.json"
    counts.write_text(json.dumps({"collision_codes": ["20", "3010"], "chain_groups": {}}))
    assert read_collision_codes(counts) == frozenset({"20", "3010"})
    counts.write_text(json.dumps({"chain_groups": {}}))
    with pytest.raises(ReviewError, match="no collision_codes list"):
        read_collision_codes(counts)
    with pytest.raises(ReviewError, match="is missing"):
        read_collision_codes(tmp_path / "absent.json")


SHOWN = [cid(1), cid(2), cid(3)]


def three():
    return [row(1), row(2, proposed_decision="history_only"), row(3)]


def test_approval_takes_each_proposal_and_an_amendment_overrides_it():
    out, counts = apply_answers(three(), SHOWN, {"rows": {
        cid(3): {"decision": "exclude_reused_code", "note": "owner B1 row 3: a different program in PB2017"}}})
    assert [r["decision"] for r in out] == ["same_program", "history_only", "exclude_reused_code"]
    assert out[2]["note"] == "owner B1 row 3: a different program in PB2017"
    assert [r["keys_sha256"] for r in out] == ["ab" * 32] * 3
    assert counts == {"decided": 3, "split_chains": 0, "split_rows": 0, "deferred": 0}


def test_pins_and_successor_are_written_only_when_answered():
    out, _ = apply_answers(three(), SHOWN, {"rows": {cid(1): {"program_account": "3022F"},
                                                      cid(2): {"successor_code": "5731D15610"}}})
    assert (out[0]["program_account"], out[0]["decision"]) == ("3022F", "same_program")
    assert out[1]["successor_code"] == "5731D15610"
    assert out[2]["program_account"] == "" and out[2]["successor_code"] == ""


def test_a_deferred_chain_stays_open_and_leads_the_next_batch():
    out, counts = apply_answers(three(), SHOWN, {"rows": {cid(2): {"defer": True}}})
    assert out[1]["decision"] == "" and counts["deferred"] == 1
    assert [r["chain_id"] for r in next_batch(out, set())[0]] == [cid(2)]


@pytest.mark.parametrize("answers, message", [
    ({"rows": {cid(9): {"decision": "same_program"}}}, "did not show"),
    ({"rows": {cid(1): {"decision": "maybe"}}}, "is not a decision"),
    ({"rows": {cid(1): {"verdict": "same_program"}}}, "unknown answer field"),
    ({"rows": {cid(1): {"defer": True, "note": "x"}}}, "takes no other answer"),
    ({"rows": {cid(1): {"split": [{"last_edition": 2019, "decision": "history_only"},
                                  {"decision": "same_program"}], "note": "x"}}}, "inside each range"),
    ({"rows": {cid(1): {"successor_code": "5731D15610"}}}, "successor only on history_only"),
    ({"rows": {cid(1): {"decision": "exclude_reused_code", "program_account": "3022F"}}},
     "an exclusion carries no program pin"),
    ({"row": {}}, 'answers need a "rows" object'),
])
def test_unusable_answers_are_refused(answers, message):
    with pytest.raises(ReviewError, match=message):
        apply_answers(three(), SHOWN, answers)


def test_a_proposal_that_is_not_a_decision_needs_the_owners_explicit_answer():
    rows = three()
    rows[0]["proposed_decision"] = ""
    with pytest.raises(ReviewError, match="is not a decision"):
        apply_answers(rows, SHOWN, {"rows": {}})
    out, _ = apply_answers(rows, SHOWN, {"rows": {cid(1): {"decision": "history_only"}}})
    assert out[0]["decision"] == "history_only"


def test_an_answered_chain_cannot_be_answered_twice():
    rows = three()
    rows[1]["decision"] = "history_only"
    with pytest.raises(ReviewError, match="already has a decision"):
        apply_answers(rows, SHOWN, {"rows": {}})


def test_a_shown_chain_must_have_exactly_one_review_row():
    rows = three() + [row(1, first_edition="2020")]
    with pytest.raises(ReviewError, match="2 review.csv row"):
        apply_answers(rows, SHOWN, {"rows": {}})


def test_a_split_duplicates_the_row_and_changes_only_its_edition_range():
    out, counts = apply_answers(three(), SHOWN, {"rows": {cid(1): {"split": [
        {"last_edition": 2019, "decision": "exclude_reused_code", "note": "owner B1 row 1: earlier program"},
        {"decision": "same_program"}]}}})
    first, second = out[0], out[1]
    assert (first["first_edition"], first["last_edition"]) == ("2017", "2019")
    assert (second["first_edition"], second["last_edition"]) == ("2020", "2023")
    assert {first["chain_id"], second["chain_id"]} == {cid(1)}
    assert first["keys_sha256"] == second["keys_sha256"] == "ab" * 32
    unchanged = set(REVIEW_COLUMNS) - {"first_edition", "last_edition", "decision", "note"}
    assert all(first[c] == second[c] == row(1)[c] for c in unchanged)
    assert [r["decision"] for r in out] == ["exclude_reused_code", "same_program", "history_only", "same_program"]
    assert first["note"] == "owner B1 row 1: earlier program" and second["note"] == ""
    assert counts == {"decided": 2, "split_chains": 1, "split_rows": 2, "deferred": 0}


@pytest.mark.parametrize("ranges, message", [
    ([{"decision": "same_program"}], "at least two ranges"),
    ([{"decision": "history_only"}, {"decision": "same_program"}], "names its last_edition"),
    ([{"last_edition": 2019, "decision": "history_only"},
      {"last_edition": 2022, "decision": "same_program"}], "must end at PB2023"),
    ([{"last_edition": 2016, "decision": "history_only"}, {"decision": "same_program"}], "does not fit"),
    ([{"last_edition": 2023, "decision": "history_only"}, {"decision": "same_program"}], "does not fit"),
    ([{"last_edition": 2019, "decision": "history_only"},
      {"last_edition": 2018, "decision": "history_only"}, {"decision": "same_program"}], "does not fit"),
    ([{"last_edition": 2019}, {"decision": "same_program"}], "needs an explicit decision"),
    ([{"first_edition": 2017, "last_edition": 2019, "decision": "history_only"},
      {"decision": "same_program"}], "unknown answer field"),
])
def test_a_split_must_cover_the_chain_in_contiguous_decided_ranges(ranges, message):
    with pytest.raises(ReviewError, match=message):
        apply_answers(three(), SHOWN, {"rows": {cid(1): {"split": ranges}}})


def write_world(tmp_path, rows, collision_codes=()):
    review = tmp_path / "research" / "review.csv"
    write_csv(review, REVIEW_COLUMNS, rows)
    write_csv(review.with_name("chains.csv"), CHAIN_COLUMNS,
              [{"chain_id": r["chain_id"], "n_keys": "7", "classes": "A1+R1"} for r in rows])
    review.with_name("counts.json").write_text(json.dumps({"collision_codes": sorted(collision_codes)}))
    return review


def answers_file(tmp_path, label, rows, **extra):
    path = tmp_path / f"{label}.answers.json"
    path.write_text(json.dumps({"batch": label, "decided_on": "2026-10-05",
                                "owner_reply": "approved, except 3: history_only", "rows": rows, **extra}))
    return path


def test_render_then_answer_round_trip_through_the_cli(tmp_path, capsys):
    review, out = write_world(tmp_path, [row(1, actuals="10"), row(2, actuals="30"), row(3, actuals="20")]), tmp_path / "out"
    assert main(["render", "--batch", "2", "--review", str(review),
                 "--seed", str(tmp_path / "absent.csv"), "--out-dir", str(out)]) == 0
    manifest = json.loads((out / "B2.json").read_text())
    assert manifest["chain_ids"] == [cid(2), cid(3), cid(1)]
    assert manifest["labels"][0] == "C002|3010F||2017-2023"
    assert (out / "B2.html").read_text().startswith("<title>Era map review B2</title>")
    answers = answers_file(tmp_path, "B2", {cid(1): {"decision": "history_only"}},
                           owner_acknowledgements={"R-DEC-ERA-EXCLUDE actuals correction": "noted"})
    capsys.readouterr()
    assert main(["answer", "--batch", "2", "--review", str(review), "--out-dir", str(out),
                 "--answers", str(answers)]) == 0
    assert capsys.readouterr().out.strip().endswith(
        "ratify writes 3 seed row(s): era-map ratify --batch B2 --decided-on 2026-10-05")
    with review.open(newline="") as f:
        reader = csv.DictReader(f)
        assert tuple(reader.fieldnames) == REVIEW_COLUMNS
        decided = {r["chain_id"]: r["decision"] for r in reader}
    assert decided == {cid(1): "history_only", cid(2): "same_program", cid(3): "same_program"}
    assert main(["answer", "--batch", "2", "--review", str(review), "--out-dir", str(out),
                 "--answers", str(answers)]) == 2
    assert "already has a decision" in capsys.readouterr().err


@pytest.mark.parametrize("extra, message", [
    ({"batch": "B3"}, "is batch 'B3', not B2"),
    ({"owner_reply": " "}, "owner_reply"),
    ({"decided_on": "Oct 5"}, "not an ISO date"),
    ({"rws": {}}, "unknown top-level key"),
])
def test_the_cli_refuses_an_unusable_answers_file(tmp_path, capsys, extra, message):
    review, out = write_world(tmp_path, [row(1)]), tmp_path / "out"
    assert main(["render", "--batch", "2", "--review", str(review),
                 "--seed", str(tmp_path / "absent.csv"), "--out-dir", str(out)]) == 0
    before = review.read_bytes()
    answers = answers_file(tmp_path, "B2", {}, **extra)
    assert main(["answer", "--batch", "2", "--review", str(review), "--out-dir", str(out),
                 "--answers", str(answers)]) == 2
    assert message in capsys.readouterr().err
    assert review.read_bytes() == before


def test_the_cli_refuses_a_review_file_with_another_header(tmp_path, capsys):
    review = tmp_path / "review.csv"
    review.write_text("decision_id,decision\nX|3010F||2017-2023,\n")
    assert main(["render", "--batch", "1", "--review", str(review), "--out-dir", str(tmp_path)]) == 2
    assert "is not era_map.REVIEW_COLUMNS" in capsys.readouterr().err


def test_render_reads_the_collision_codes_beside_review_csv(tmp_path):
    review = write_world(tmp_path, [row(1, chain_id="20|0300D|DCAA")], collision_codes={"20"})
    assert main(["render", "--batch", "1", "--review", str(review),
                 "--seed", str(tmp_path / "absent.csv"), "--out-dir", str(tmp_path / "out")]) == 0
    assert "PB2026 collision code 20: same_program needs program_account and program_org" in (
        (tmp_path / "out" / "B1.html").read_text())


def test_render_skips_chains_the_seed_already_covers(tmp_path, capsys):
    review = write_world(tmp_path, [row(1), row(2)])
    seed = tmp_path / "seed.csv"
    write_csv(seed, SEED_COLUMNS, [{"decision_id": "C001|3010F||2017-2023", "line_item_code": "C001",
                                    "account": "3010F", "organization": "", "first_edition": "2017",
                                    "last_edition": "2023"}])
    assert main(["render", "--batch", "1", "--review", str(review), "--seed", str(seed),
                 "--out-dir", str(tmp_path / "out")]) == 0
    assert json.loads((tmp_path / "out" / "B1.json").read_text())["chain_ids"] == [cid(2)]


def test_what_this_tool_writes_is_what_ratify_accepts(tmp_path, monkeypatch):
    """End to end on era_map's miniature lake: propose -> render -> answer
    (one approval with a note, one range split, two approved proposals with
    their pre-filled pins) -> ratify -> check -> propose."""
    monkeypatch.setattr(era_map, "ORG_SPLIT_CODES", frozenset({"20"}))
    db = make_lake(tmp_path / "lake")
    raw = make_raw_docs(tmp_path)
    out = tmp_path / "research" / "era_map"
    seed = tmp_path / "seeds" / "p1_era_code_decisions.csv"
    era_map.propose(duckdb_path=db, raw_docs_dir=raw, out_dir=out, seed_path=seed, decided_on=date(2026, 10, 2))
    review, pages = out / "review.csv", tmp_path / "pages"
    assert main(["render", "--batch", "1", "--review", str(review), "--seed", str(seed),
                 "--out-dir", str(pages)]) == 0
    shown = json.loads((pages / "B1.json").read_text())["chain_ids"]
    assert sorted(shown) == ["1045|1612N|", "20|0300D|DHRA", "20|0300D|DSS", "50|0300D|"]
    answers = answers_file(tmp_path, "B1", {
        "1045|1612N|": {"decision": "same_program", "note": "OHIO Replacement = COLUMBIA"},
        "50|0300D|": {"split": [{"last_edition": 2022, "decision": "exclude_reused_code"},
                                {"decision": "history_only"}]}})
    assert main(["answer", "--batch", "1", "--review", str(review), "--out-dir", str(pages),
                 "--answers", str(answers)]) == 0
    assert era_map.ratify(review_csv=review, seed_path=seed, batch="B1",
                          decided_on=date(2026, 10, 5), duckdb_path=db) == 5
    b1 = {r["decision_id"]: r for r in era_map.read_seed(seed) if r["ruling"] == "R-DEC-ERA-B1"}
    assert set(b1) == {"1045|1612N||2022-2022", "20|0300D|DSS|2022-2022", "50|0300D||2022-2022",
                       "50|0300D||2023-2023", "20|0300D|DHRA|2023-2023"}
    assert b1["1045|1612N||2022-2022"]["note"] == "OHIO Replacement = COLUMBIA"
    assert era_map.check(duckdb_path=db, seed_path=seed) == {"undecided": [], "stale": []}
    era_map.propose(duckdb_path=db, raw_docs_dir=raw, out_dir=out, seed_path=seed, decided_on=date(2026, 10, 2))
    assert era_map.read_csv(review) == []
    assert main(["render", "--batch", "2", "--review", str(review), "--seed", str(seed),
                 "--out-dir", str(pages)]) == 0
    assert not (pages / "B2.json").exists()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_era_review_batch_page.py -q`
Expected: collection error `ModuleNotFoundError: No module named 'era.review_batch_page'`.

- [ ] **Step 3: Implement the renderer and the answer writer**

Create `scripts/era/review_batch_page.py` (`scripts/era/` holds Task 1's `env.sh`; no `__init__.py`):

```python
#!/usr/bin/env python3
"""Owner review batches for the PB2017-23 era map (spec §5.3; R-DEC-FAM-REVIEW).

render  The next BATCH_SIZE open chains of review.csv, largest recorded era
        actuals first, as one self-contained page fragment. The page is
        published as a private Artifact; the owner reads it (on a phone) and
        answers in chat. A JSON manifest beside it records exactly which
        chains it showed, in the order the owner's row numbers refer to.
answer  Writes the owner's answers for exactly those chains into review.csv
        (decision, note, program pins, successor, range splits), ready for
        `govbudget era-map ratify --batch B<n> --decided-on DATE`.

review.csv is `era-map propose`'s file: era_map.REVIEW_COLUMNS, one row per
chain, keyed by chain_id. chains.csv beside it supplies what the page shows
and review.csv lacks (n_keys, classes, the book-stated successor's account
and evidence). A chain is open while its review.csv `decision` is blank and
no seed row covers it; after ratify, `era-map propose` rewrites review.csv
with only the chains still open (deferred ones come back blank).

A range split duplicates the chain's row and changes only first_edition and
last_edition: every range keeps the chain's keys_sha256, which ratify
compares with the whole chain in the lake before it hashes each range
itself. The ranges are contiguous and cover the chain by construction.

Nothing here decides anything: `answer` copies a proposal only when the
owner's reply approves it, refuses a proposal that is not a decision, and
leaves every check against the lake to ratify.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from govbudget.jbooks.era_map import (
    DECISIONS,
    REVIEW_COLUMNS,
    chain_id,
    parse_chain_id,
    read_csv,
    read_seed,
    write_csv,
)

BATCH_SIZE = 25
ANSWER_FIELDS = frozenset({"decision", "note", "program_account", "program_org", "successor_code"})
CHAIN_FIELDS = ("n_keys", "classes", "successor_account", "successor_evidence")
ANSWERS_KEYS = frozenset({"batch", "decided_on", "owner_reply", "owner_acknowledgements", "rows"})
FONTS = ("https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500"
         "&family=IBM+Plex+Sans:wght@400;500;600&display=swap")
PAGE_CSS = """
:root{--paper:#f4f6f9;--sheet:#ffffff;--ink:#16202c;--muted:#556173;--rule:#d3dae3;--accent:#21507f;--same:#1d6a45;--same-bg:#e1f0e7;--hist:#7a520c;--hist-bg:#f5ead3;--excl:#8e2b22;--excl-bg:#f6e0dc;--other:#3b4553;--other-bg:#e6e9ee}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){color-scheme:dark;--paper:#0e131a;--sheet:#151c25;--ink:#e2e7ee;--muted:#9ba7b7;--rule:#2a3441;--accent:#8fb6e4;--same:#8fd2ac;--same-bg:#16321f;--hist:#e5c27f;--hist-bg:#382b11;--excl:#f0a69d;--excl-bg:#3b1b18;--other:#c2cad5;--other-bg:#242c37}}
:root[data-theme="dark"]{color-scheme:dark;--paper:#0e131a;--sheet:#151c25;--ink:#e2e7ee;--muted:#9ba7b7;--rule:#2a3441;--accent:#8fb6e4;--same:#8fd2ac;--same-bg:#16321f;--hist:#e5c27f;--hist-bg:#382b11;--excl:#f0a69d;--excl-bg:#3b1b18;--other:#c2cad5;--other-bg:#242c37}
body{background:var(--paper);color:var(--ink);font:15px/1.55 "IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif}
.page{max-width:880px;margin:0 auto;padding-inline:16px;padding-block:28px 64px}
.eyebrow,.label{margin:0;font:500 12px/1.4 "IBM Plex Mono",ui-monospace,Menlo,monospace;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
h1{margin:6px 0 10px;font-size:26px;line-height:1.2;font-weight:600;text-wrap:balance}
.lede,.how{margin:0 0 10px;max-width:68ch}
.how{color:var(--muted)}.how b{color:var(--ink)}
.legend{display:grid;gap:6px;margin:14px 0 0;padding-block:12px;border-block:1px solid var(--rule)}
.legend div{display:grid;grid-template-columns:minmax(0,max-content) 1fr;gap:10px;align-items:baseline}
.legend dd{margin:0;color:var(--muted)}
.chains{list-style:none;margin:8px 0 0;padding:0}
.chain{padding-block:18px;border-bottom:1px solid var(--rule)}
.chain-head{display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 12px}
.num{font:500 13px/1 "IBM Plex Mono",ui-monospace,Menlo,monospace;color:var(--muted);min-width:2ch}
.chain h2{margin:0;flex:1 1 auto;display:flex;flex-wrap:wrap;gap:4px 10px;align-items:baseline;font-size:18px;line-height:1.3;font-weight:600}
code,.usd,.acct,.org,.cid{font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace}
.acct,.org{font-size:14px;font-weight:400;color:var(--muted)}
.usd{font-size:16px;font-weight:500;font-variant-numeric:tabular-nums}
.span{margin:4px 0 10px;color:var(--muted);font-size:14px}
.cid{font-size:12px;overflow-wrap:anywhere}
dl{margin:0}.chain dl{display:grid;gap:8px}
.chain dl div{display:grid;grid-template-columns:150px minmax(0,1fr);gap:4px 14px}
dt{font-size:13px;color:var(--muted)}
dd{margin:0;min-width:0;overflow-wrap:anywhere}
.pre{display:block;white-space:pre-wrap}
.proposal{display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 10px;margin:12px 0 0;padding:10px 12px;background:var(--sheet);border:1px solid var(--rule);border-radius:4px}
.chip{display:inline-block;padding:2px 8px;border-radius:3px;font:500 13px/1.5 "IBM Plex Mono",ui-monospace,Menlo,monospace}
.chip-same{color:var(--same);background:var(--same-bg)}.chip-hist{color:var(--hist);background:var(--hist-bg)}
.chip-excl{color:var(--excl);background:var(--excl-bg)}.chip-other{color:var(--other);background:var(--other-bg)}
.pins{font-size:14px;color:var(--accent)}
.reason{flex:1 1 100%}
@media (max-width:560px){.chain dl div{grid-template-columns:1fr}h1{font-size:22px}}
""".strip()
_EDITION_BREAK = re.compile(r"; (?=\d{4}: )")


class ReviewError(ValueError):
    """A review input that cannot be applied safely."""


def read_review(path: Path) -> list[dict]:
    """review.csv rows; refuses any header but era_map.REVIEW_COLUMNS."""
    with Path(path).open(newline="", encoding="utf-8") as fh:
        header = next(csv.reader(fh), [])
    if tuple(header) != REVIEW_COLUMNS:
        raise ReviewError(f"{path}: header {header} is not era_map.REVIEW_COLUMNS {list(REVIEW_COLUMNS)}")
    return read_csv(Path(path))


def read_chains(path: Path) -> dict[str, dict]:
    """chains.csv (beside review.csv): chain_id -> the fields the page reads from it."""
    path = Path(path)
    if not path.is_file():
        raise ReviewError(f"{path} is missing (era-map propose writes it beside review.csv)")
    rows = read_csv(path)
    missing = [c for c in ("chain_id",) + CHAIN_FIELDS if rows and c not in rows[0]]
    if missing:
        raise ReviewError(f"{path} lacks column(s): {', '.join(missing)}")
    return {r["chain_id"]: {f: r[f] for f in CHAIN_FIELDS} for r in rows}


def seed_chain_ids(seed_path: Path) -> set[str]:
    """Every chain at least one seed row already covers."""
    return {chain_id(r["line_item_code"], r["account"], r["organization"])
            for r in read_seed(Path(seed_path))}


def label(row: dict) -> str:
    """What the page prints for a row: '{chain_id}|{first}-{last}'."""
    return f"{row['chain_id']}|{row['first_edition']}-{row['last_edition']}"


def actuals_k(row: dict) -> Decimal:
    try:
        return Decimal(row["actuals_k"] or "0")
    except InvalidOperation as exc:
        raise ReviewError(f"{row['chain_id']}: actuals_k {row['actuals_k']!r} is not a number") from exc


def next_batch(rows: list[dict], decided: set[str], size: int = BATCH_SIZE) -> tuple[list[dict], int]:
    """The `size` largest open chains, and how many chains were open."""
    open_rows = [r for r in rows if not r["decision"].strip() and r["chain_id"] not in decided]
    open_rows.sort(key=lambda r: (-actuals_k(r), r["chain_id"]))
    return open_rows[:size], len(open_rows)


def fmt_usd_k(value: Decimal) -> str:
    """USD thousands as a short dollar figure: Decimal('1234567') -> '$1.23B'."""
    dollars = Decimal(value) * 1000
    for suffix, scale in (("B", Decimal(10) ** 9), ("M", Decimal(10) ** 6), ("K", Decimal(10) ** 3)):
        if abs(dollars) >= scale:
            return f"${dollars / scale:,.2f}{suffix}"
    return f"${dollars:,.0f}"


def _e(value) -> str:
    return html.escape(str(value or ""), quote=True)


def _tone(decision: str) -> str:
    if decision == "same_program":
        return "same"
    if decision == "history_only":
        return "hist"
    if decision.startswith("exclude_"):
        return "excl"
    return "other"


def _editions(row: dict) -> str:
    first, last = row["first_edition"], row["last_edition"]
    return f"PB{first}" if first == last else f"PB{first}–PB{last}"


def read_collision_codes(path: Path) -> frozenset[str]:
    """counts.json (beside review.csv): the PB2026 collision codes `propose` found."""
    path = Path(path)
    if not path.is_file():
        raise ReviewError(f"{path} is missing (era-map propose writes it beside review.csv)")
    codes = json.loads(path.read_text(encoding="utf-8")).get("collision_codes")
    if not isinstance(codes, list):
        raise ReviewError(f"{path} has no collision_codes list")
    return frozenset(str(c) for c in codes)


def collision_pins_missing(row: dict, collision_codes: frozenset[str]) -> list[str]:
    """The pins ratify requires that this row's proposal leaves blank.

    On a PB2026 collision code, same_program and history_only need BOTH
    program_account and program_org (Task 12 ratify refuses either blank), so
    approving such a proposal as it stands could not be ratified."""
    code, _account, _org = parse_chain_id(row["chain_id"])
    if code not in collision_codes or row["proposed_decision"] not in ("same_program", "history_only"):
        return []
    return [f for f in ("program_account", "program_org") if not row[f].strip()]


def _row_html(n: int, row: dict, chain: dict, collision_codes: frozenset[str] = frozenset()) -> str:
    code, account, org = parse_chain_id(row["chain_id"])
    org_html = f'<span class="org">org {_e(org)}</span>' if org else ""
    pins = [f"{text} {_e(row[field])}" for field, text in
            (("program_account", "joins account"), ("program_org", "joins org")) if row[field]]
    pin_html = f'<span class="pins">{" · ".join(pins)}</span>' if pins else ""
    successor = ""
    if row["successor_code"]:
        successor = (f'<div><dt>Stated successor</dt><dd><code>{_e(row["successor_code"])}</code> '
                     f'{_e(chain["successor_account"])}<span class="pre">{_e(chain["successor_evidence"])}</span></dd></div>\n')
    missing = collision_pins_missing(row, collision_codes)
    usable = row["proposed_decision"] and not missing
    proposed = row["proposed_decision"] if usable else "needs your decision"
    tone = _tone(row["proposed_decision"]) if usable else "other"
    need_html = ""
    if missing:
        need_html = (f'<span class="pins">PB2026 collision code {_e(code)}: {_e(row["proposed_decision"])} '
                     f'needs {" and ".join(missing)} (ratify refuses it without them); answer the '
                     f"pin(s) or another decision</span>")
    titles = _EDITION_BREAK.sub("\n", row["titles_by_edition"])
    return (
        f'<li class="chain" id="row-{n}">\n'
        f'<div class="chain-head"><span class="num">{n}</span><h2><code>{_e(code)}</code>'
        f'<span class="acct">{_e(account)}</span>{org_html}</h2>'
        f'<span class="usd">{_e(fmt_usd_k(actuals_k(row)))}</span></div>\n'
        f'<p class="span">{_e(_editions(row))} · {_e(chain["n_keys"])} era lines · '
        f'class {_e(chain["classes"]) or "—"}<br><span class="cid">{_e(label(row))}</span></p>\n'
        f"<dl>\n"
        f'<div><dt>Titles by edition</dt><dd class="pre">{_e(titles)}</dd></div>\n'
        f'<div><dt>PB2024–26 title</dt><dd>{_e(row["modern_title"]) or "—"}</dd></div>\n'
        f'<div><dt>Accounts</dt><dd>{_e(row["accounts"])}</dd></div>\n'
        f'<div><dt>Continuity</dt><dd>{_e(row["continuity"]) or "—"}</dd></div>\n'
        f"{successor}</dl>\n"
        f'<p class="proposal"><span class="label">Proposed</span>'
        f'<span class="chip chip-{tone}">{_e(proposed)}</span>{pin_html}{need_html}'
        f'<span class="reason">{_e(row["reason"])}</span></p>\n'
        f"</li>"
    )


def render_page(batch: str, rows: list[dict], remaining: int, chains: dict[str, dict],
                collision_codes: frozenset[str] = frozenset()) -> str:
    """One Artifact page fragment (the publish skeleton adds <html>/<head>/<body>).

    A row is marked "needs your decision" when it has no proposal, or when its
    proposal is same_program/history_only on a PB2026 collision code with a
    blank pin (collision_pins_missing): the page names the missing pin(s)."""
    for row in rows:
        if row["chain_id"] not in chains:
            raise ReviewError(f"chains.csv has no row for {row['chain_id']}")
    total = sum((actuals_k(r) for r in rows), Decimal(0))
    items = "\n".join(_row_html(n, row, chains[row["chain_id"]], collision_codes)
                      for n, row in enumerate(rows, 1))
    plural = "" if remaining == 1 else "s"
    return (
        f"<title>Era map review {_e(batch)}</title>\n"
        f'<link rel="stylesheet" href="{_e(FONTS)}">\n'
        f"<style>\n{PAGE_CSS}\n</style>\n"
        f'<main class="page">\n<header class="intro">\n'
        f'<p class="eyebrow">Fiscal Receipts · procurement history before FY2024</p>\n'
        f"<h1>Era map review, batch {_e(batch)}</h1>\n"
        f'<p class="lede">{len(rows)} budget-line chains from the PB2017–PB2023 P-1 workbooks, '
        f"ordered by their recorded era actuals ({_e(fmt_usd_k(total))} across this batch). "
        f"Each chain needs one decision before its points can join a program page.</p>\n"
        f'<p class="how">Reply in chat with <b>approved</b> to accept every proposal, or give a row '
        f"number and its change, for example “7: history_only”, “12: split at PB2020, earlier "
        f"range exclude_reused_code” or “3: defer”. A row marked <b>needs your decision</b> has no "
        f"usable proposal (none, or a collision-code proposal missing a pin) and needs an explicit "
        f"answer. {remaining} undecided chain{plural} will remain after this batch.</p>\n"
        f'<dl class="legend">\n'
        f'<div><dt><span class="chip chip-same">same_program</span></dt><dd>The era code is the program on '
        f"today’s page; its PB2017–PB2023 points join that page.</dd></div>\n"
        f'<div><dt><span class="chip chip-hist">history_only</span></dt><dd>Kept in the map and the program '
        f"table; no page gains points.</dd></div>\n"
        f'<div><dt><span class="chip chip-excl">exclude_reused_code</span></dt><dd>The code meant a different '
        f"program in these editions; nothing joins.</dd></div>\n"
        f"</dl>\n</header>\n"
        f'<ol class="chains">\n{items}\n</ol>\n</main>\n'
    )


def _checked(lbl: str, new: dict) -> dict:
    """The two rules ratify would refuse that this tool can see without the lake."""
    if new["successor_code"].strip() and new["decision"] != "history_only":
        raise ReviewError(f"{lbl}: successor_code {new['successor_code']!r} is set but the decision is "
                          f"{new['decision']}; ratify takes a successor only on history_only — answer "
                          f'"successor_code": "" or decision history_only')
    if new["decision"].startswith("exclude_") and (new["program_account"] or new["program_org"]):
        raise ReviewError(f'{lbl}: an exclusion carries no program pin — answer "program_account": "" '
                          f'and "program_org": ""')
    return new


def _decide(row: dict, change: dict) -> dict:
    new = dict(row)
    new.update({f: "" if change[f] is None else str(change[f]) for f in ANSWER_FIELDS if f in change})
    decision = change.get("decision", row["proposed_decision"])
    if decision not in DECISIONS:
        raise ReviewError(
            f"{label(new)}: {decision!r} is not a decision ({', '.join(DECISIONS)}); "
            "the owner's answer must name one, or a split")
    new["decision"] = decision
    return _checked(label(new), new)


def _split(row: dict, ranges) -> list[dict]:
    """One copy of the row per edition range; only first/last_edition and the answers change."""
    lbl = label(row)
    if not isinstance(ranges, list) or len(ranges) < 2:
        raise ReviewError(f"{lbl}: a split needs at least two ranges")
    first, last = int(row["first_edition"]), int(row["last_edition"])
    out, start = [], first
    for i, part in enumerate(ranges):
        unknown = set(part) - ANSWER_FIELDS - {"last_edition"}
        if unknown:
            raise ReviewError(f"{lbl}: unknown answer field(s) {sorted(unknown)} in a split range")
        is_last = i == len(ranges) - 1
        if not is_last and "last_edition" not in part:
            raise ReviewError(f"{lbl}: every split range but the last names its last_edition")
        end = int(part.get("last_edition", last))
        if is_last and end != last:
            raise ReviewError(f"{lbl}: the last range must end at PB{last}, the chain's last edition")
        if end < start or (not is_last and end >= last):
            raise ReviewError(f"{lbl}: range PB{start}-PB{end} does not fit inside PB{first}-PB{last}")
        if "decision" not in part:
            raise ReviewError(f"{lbl}: split range PB{start}-PB{end} needs an explicit decision")
        new = _decide({**row, "first_edition": str(start), "last_edition": str(end)}, part)
        out.append(new)
        start = end + 1
    return out


def apply_answers(rows: list[dict], shown: list[str], answers: dict) -> tuple[list[dict], dict]:
    """Apply the owner's answers to exactly the chains one batch page showed.

    answers["rows"] maps chain_id -> amendment. A shown chain absent from it
    takes its proposal (the owner approved the batch); {"defer": true} leaves
    it open for a later batch; {"split": [...]} replaces it with one row per
    edition range. Returns (rows, counts); rows keep their original order.
    """
    amendments = answers.get("rows")
    if not isinstance(amendments, dict):
        raise ReviewError('answers need a "rows" object (empty when the owner approved every proposal)')
    stray = sorted(set(amendments) - set(shown))
    if stray:
        raise ReviewError(f"answers name chain(s) this batch did not show: {', '.join(stray)}")
    by_id: dict[str, list[dict]] = {}
    for r in rows:
        by_id.setdefault(r["chain_id"], []).append(r)
    for cid in shown:
        found = by_id.get(cid, [])
        if len(found) != 1:
            raise ReviewError(f"{cid}: {len(found)} review.csv row(s); want exactly one (re-run era-map propose)")
        if found[0]["decision"].strip():
            raise ReviewError(f"{label(found[0])}: already has a decision")
    replaced: dict[str, list[dict]] = {}
    counts = {"decided": 0, "split_chains": 0, "split_rows": 0, "deferred": 0}
    for cid in shown:
        row, change = by_id[cid][0], amendments.get(cid, {})
        unknown = set(change) - ANSWER_FIELDS - {"defer", "split"}
        if unknown:
            raise ReviewError(f"{label(row)}: unknown answer field(s) {sorted(unknown)}")
        if change.get("defer"):
            if set(change) != {"defer"}:
                raise ReviewError(f"{label(row)}: a deferred chain takes no other answer")
            counts["deferred"] += 1
            continue
        if "split" in change:
            if set(change) != {"split"}:
                raise ReviewError(f"{label(row)}: a split carries its answers inside each range")
            parts = _split(row, change["split"])
            replaced[cid] = parts
            counts["split_chains"] += 1
            counts["split_rows"] += len(parts)
            continue
        replaced[cid] = [_decide(row, change)]
        counts["decided"] += 1
    out: list[dict] = []
    for row in rows:
        out.extend(replaced.get(row["chain_id"], [row]))
    return out, counts


def _load_answers(path: Path, batch: str) -> dict:
    answers = json.loads(Path(path).read_text(encoding="utf-8"))
    unknown = set(answers) - ANSWERS_KEYS
    if unknown:
        raise ReviewError(f"{path}: unknown top-level key(s) {sorted(unknown)}")
    if answers.get("batch") != batch:
        raise ReviewError(f"{path} is batch {answers.get('batch')!r}, not {batch}")
    if not str(answers.get("owner_reply") or "").strip():
        raise ReviewError(f"{path}: owner_reply (the owner's message, verbatim) is empty")
    try:
        date.fromisoformat(str(answers.get("decided_on")))
    except ValueError as exc:
        raise ReviewError(f"{path}: decided_on {answers.get('decided_on')!r} is not an ISO date") from exc
    return answers


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="review_batch_page", description="Era-map owner review batches")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("render", "answer"):
        s = sub.add_parser(name)
        s.add_argument("--batch", type=int, required=True, help="batch number n (label B<n>)")
        s.add_argument("--review", type=Path, default=Path("data/research/era_map/review.csv"))
        s.add_argument("--out-dir", type=Path, default=Path("tmp/era-review"))
    sub.choices["render"].add_argument("--chains", type=Path, default=None,
                                       help="default: chains.csv beside --review")
    sub.choices["render"].add_argument("--counts", type=Path, default=None,
                                       help="default: counts.json beside --review (PB2026 collision codes)")
    sub.choices["render"].add_argument("--seed", type=Path, default=Path("dbt/seeds/p1_era_code_decisions.csv"))
    sub.choices["answer"].add_argument("--answers", type=Path, required=True)
    args = p.parse_args(argv)
    batch = f"B{args.batch}"
    manifest_path = args.out_dir / f"{batch}.json"
    try:
        rows = read_review(args.review)
        if args.cmd == "render":
            chains = read_chains(args.chains or args.review.with_name("chains.csv"))
            collision_codes = read_collision_codes(args.counts or args.review.with_name("counts.json"))
            shown, open_count = next_batch(rows, seed_chain_ids(args.seed))
            if not shown:
                print("no undecided chain left")
                return 0
            args.out_dir.mkdir(parents=True, exist_ok=True)
            page = args.out_dir / f"{batch}.html"
            page.write_text(render_page(batch, shown, open_count - len(shown), chains, collision_codes),
                            encoding="utf-8")
            total = sum((actuals_k(r) for r in shown), Decimal(0))
            manifest_path.write_text(json.dumps({
                "batch": batch, "chain_ids": [r["chain_id"] for r in shown],
                "labels": [label(r) for r in shown], "actuals_k": str(total),
                "undecided_before": open_count,
            }, indent=2) + "\n", encoding="utf-8")
            print(f"{batch}: {len(shown)} chain(s), {fmt_usd_k(total)} of era actuals -> {page} "
                  f"(manifest {manifest_path}); {open_count - len(shown)} undecided after this batch")
            return 0
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("batch") != batch:
            raise ReviewError(f"{manifest_path} is batch {manifest.get('batch')!r}, not {batch}")
        answers = _load_answers(args.answers, batch)
        out, counts = apply_answers(rows, manifest["chain_ids"], answers)
        write_csv(args.review, REVIEW_COLUMNS, out)
        print(f"{batch}: {counts['decided']} decided, {counts['split_chains']} split into "
              f"{counts['split_rows']} ranges, {counts['deferred']} deferred -> {args.review}; "
              f"ratify writes {counts['decided'] + counts['split_rows']} seed row(s): "
              f"era-map ratify --batch {batch} --decided-on {answers['decided_on']}")
        return 0
    except ReviewError as exc:
        print(f"review_batch_page: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_era_review_batch_page.py -q`
Expected: `41 passed` (38 + the collision-pin page test, the counts.json reader test and the render-CLI collision test).

- [ ] **Step 5: Commit the tool**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/scripts/era/review_batch_page.py GovBudget/tests/test_era_review_batch_page.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(era-map): owner review batch page + answer writer on era_map.REVIEW_COLUMNS (spec §5.3)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 6: Record the starting point of the review (read-only)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
ls data/research/era_map/review.csv data/research/era_map/chains.csv dbt/seeds/p1_era_code_decisions.csv dbt/tests/warn_p1_era_map_undecided.sql && uv run --project . python -c "from pathlib import Path; from govbudget.jbooks.era_map import read_csv; print('review rows', len(read_csv(Path('data/research/era_map/review.csv'))))" && mkdir -p tmp/era-review && uv run --project . python -m govbudget era-map check > tmp/era-review/check.log; echo "exit=$?"; tail -1 tmp/era-review/check.log
```
Expected: the four paths; `review rows 125`; `exit=0`; `era-map check: 125 undecided chain(s), 0 stale decision(s)` (Task 12 Step 10's numbers). Write the numbers down: the closing ROADMAP note quotes them. A non-zero stale count (exit 1) means the lake moved after Task 11: stop, re-run `era-map propose` (Task 12 Step 10) and repeat this step before any batch.

- [ ] **Step 7: Render batch n (start with n = 1)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && uv run --project . python scripts/era/review_batch_page.py render --batch 1
```
Expected for B1: `B1: 25 chain(s), $63.25B of era actuals -> tmp/era-review/B1.html (manifest tmp/era-review/B1.json); 100 undecided after this batch` (the research-pass numbers; later batches print their own). Fewer than 25 chains only on the last batch; `no undecided chain left` means the loop is done — go to Step 16. `tmp/` is gitignored (GovBudget/.gitignore `/tmp/`).

- [ ] **Step 8: Publish the batch page as a private Artifact**

Before the first publish of the session, load the `artifact-design` skill (Skill tool, `skill: "artifact-design"`). The page fragment already follows its contract (own `<title>` first, Google-Fonts link with fallbacks, light tokens on `:root`, dark tokens under `@media (prefers-color-scheme: dark)` guarded by `:root:not([data-theme="light"])` and again under `:root[data-theme="dark"]`, explicit `body` background, 16px gutter via `padding-inline`, no scripts). If the skill asks for something the fragment lacks, change `PAGE_CSS` / `render_page` in `scripts/era/review_batch_page.py`, re-run Step 4 and amend the Step 5 commit before publishing.

Call the Artifact tool: `action: "publish"`, `file_path: "/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/tmp/era-review/B1.html"`, `icon: "checklist"`, `description: "Owner review of the next 25 PB2017–PB2023 budget-line chains, largest era actuals first (batch B1)."` Each batch is its own file, so each is its own private artifact (the page the owner approved stays as it was).

- [ ] **Step 9: Ask the owner and wait**

Send the owner the artifact link with: "Era-map batch B<n> (<count> chains, <$total>). Reply 'approved' to accept every proposal, or amend by row number (e.g. '7: history_only', '12: split at PB2020, earlier range exclude_reused_code', '3: defer'). Rows marked 'needs your decision' have no usable proposal and need an explicit answer; for a PB2026 collision code the page names the missing pin." Then stop until the owner replies in chat. For each 'needs your decision' row on a collision code, ask the owner for the pin explicitly, naming the choices: e.g. `20|0300D|DCAA` → `same_program` joined to the PB2026 `20` page of DCSA or of DTRA (`program_account` 0300D, `program_org` DCSA/DTRA), or `history_only` pinned to its own identity (0300D/DCAA). Only the owner's own chat reply counts; if it is ambiguous for any row (or leaves a 'needs your decision' row unanswered), ask about that row before Step 10.

- [ ] **Step 10: Write the owner's answers file**

Print the row-number → chain map the page used:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && uv run --project . python -c "import json; m=json.load(open('tmp/era-review/B1.json')); [print(i, c, l) for i, (c, l) in enumerate(zip(m['chain_ids'], m['labels']), 1)]"
```

Create `data/research/era_map/batches/B1.json` (`mkdir -p data/research/era_map/batches` first). `owner_reply` is the owner's message verbatim; `decided_on` is the ISO date of that reply; `rows` holds only amended rows, keyed by `chain_id` (every other shown row takes its proposal; `{}` when the owner approved everything). Shape, with one example of each kind of amendment (use only what the owner said):

```json
{
  "batch": "B1",
  "decided_on": "2026-10-03",
  "owner_reply": "approved, except 7: history_only; 12: split at PB2020, earlier range exclude_reused_code; 3: defer",
  "rows": {
    "<chain_id of row 7>": {"decision": "history_only", "note": "owner B1 row 7: history_only"},
    "<chain_id of row 12>": {"split": [
      {"last_edition": 2019, "decision": "exclude_reused_code", "note": "owner B1 row 12: earlier range is a different program"},
      {"decision": "same_program", "note": "owner B1 row 12: same program from PB2020"}
    ]},
    "<chain_id of row 3>": {"defer": true}
  }
}
```
Allowed top-level keys: `batch`, `decided_on`, `owner_reply`, `owner_acknowledgements` (optional, for any note the owner adds that is not about a row; the §5.2 correction needs none, since the owner confirmed it at plan review), `rows`. Allowed per-row fields: `decision` (one of `DECISIONS`), `note`, `program_account`, `program_org`, `successor_code`, `defer`, `split` (ranges in edition order; every range but the last names `last_edition`; each range names its `decision` and may carry the other fields). An exclusion takes `"program_account": "", "program_org": ""` when the row was pre-filled with pins; a successor goes only on `history_only`.

- [ ] **Step 11: Apply the answers to review.csv**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && uv run --project . python scripts/era/review_batch_page.py answer --batch 1 --answers data/research/era_map/batches/B1.json; echo "exit=$?"; git diff --stat -- data/research/era_map/review.csv
```
Expected: `B1: <d> decided, <s> split into <r> ranges, <f> deferred -> data/research/era_map/review.csv; ratify writes <d+r> seed row(s): era-map ratify --batch B1 --decided-on <decided_on>`, `exit=0`, with `d + s + f` = the batch size. Exit 2 prints the refused answer (a chain the page did not show, a non-decision, a missing answer for a row with no proposal, a split that does not cover the chain, a successor off `history_only`, a pinned exclusion): fix the answers file and re-run; review.csv is written only on success. Never edit review.csv by hand.

- [ ] **Step 12: Ratify the batch**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
D=$(uv run --project . python -c "import json; print(json.load(open('data/research/era_map/batches/B1.json'))['decided_on'])") && uv run --project . python -m govbudget era-map ratify --batch B1 --decided-on "$D"; echo "exit=$?"; uv run --project . python - <<'PY'
import csv
rows = [r for r in csv.DictReader(open("dbt/seeds/p1_era_code_decisions.csv", newline="")) if r["ruling"] == "R-DEC-ERA-B1"]
print(f"B1 seed rows={len(rows)} decided_by={sorted({r['decided_by'] for r in rows})} decided_on={sorted({r['decided_on'] for r in rows})}")
PY
```
Expected: `era-map ratify: <d+r> decision row(s) added as R-DEC-ERA-B1 -> /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/dbt/seeds/p1_era_code_decisions.csv`, `exit=0`, then `B1 seed rows=<d+r> decided_by=['owner'] decided_on=['<decided_on>']`. On `era-map ratify: REFUSED — era-map ratify refused; nothing written:` (exit 1; the seed is untouched) read each listed reason — typically a collision chain whose `program_account`/`program_org` name no PB2026 page, or `keys_sha256 changed since review` (the lake moved: re-run `era-map propose`, then re-render this batch) — then restore review.csv with `git checkout -- data/research/era_map/review.csv`, fix the answers file (ask the owner if the fix changes a decision) and re-run Steps 11–12.

- [ ] **Step 13: Check the drift guard and the undecided count**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
uv run --project . python -m govbudget era-map check > tmp/era-review/check.log; echo "exit=$?"; tail -1 tmp/era-review/check.log
```
Expected: `exit=0`, then `era-map check: <u> undecided chain(s), 0 stale decision(s)`, where `<u>` = the previous count minus `d + s` from Step 11 (deferred chains stay; for B1 with no deferral, 100). A stale decision exits 1: stop and compare that seed row with `era-map check`'s `stale` line.

- [ ] **Step 14: Rewrite review.csv with only the open chains**

ratify refuses any review.csv row that overlaps a seed row (Task 12 `test_ratify_refuses_bad_batch_labels_and_reuse`), so the next batch needs review.csv without this batch's rows. `propose` keeps every owner-ruled seed row verbatim, re-derives the class-ruled rows unchanged, and lists only chains no seed row covers (deferred chains come back with blank decisions):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
uv run --project . python -m govbudget era-map propose && git status --short -- data/research/era_map dbt/seeds
```
Expected: one line `era-map propose: 6927 era keys, 1253 chains; rulings SAME=810 EXCLUDE=47 HISTORY=271; <u> chain(s) for review -> /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/data/research/era_map` (`<u>` = Step 13's count; the class-ruling counts never move), then ` M data/research/era_map/chains.csv`, ` M data/research/era_map/counts.json`, ` M data/research/era_map/review.csv`, ` M dbt/seeds/p1_era_code_decisions.csv` and `?? data/research/era_map/batches/` (no `keys.csv` line: its rows do not depend on decisions). `propose` refuses (`holds decisions for … chain(s) that are not ratified yet`) if Step 12 did not ratify every decided row: go back to Step 12.

- [ ] **Step 15: Commit the batch, then loop**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/data/research/era_map/review.csv GovBudget/data/research/era_map/chains.csv GovBudget/data/research/era_map/keys.csv GovBudget/data/research/era_map/counts.json GovBudget/dbt/seeds/p1_era_code_decisions.csv GovBudget/data/research/era_map/batches/B1.json && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(era-map): owner batch B1 ratified (R-DEC-ERA-B1)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
Repeat Steps 7–15 with n = 2, 3, … (replace `B1`/`--batch 1` throughout) until Step 13 prints `era-map check: 0 undecided chain(s), 0 stale decision(s)` and Step 14 prints `0 chain(s) for review`. 125 chains make five batches, more if the owner defers.

- [ ] **Step 16: Replace the warn test with the error test**

Delete the warn test:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git rm GovBudget/dbt/tests/warn_p1_era_map_undecided.sql
```
Expected: `rm 'GovBudget/dbt/tests/warn_p1_era_map_undecided.sql'`.

Create `dbt/tests/assert_p1_era_map_no_undecided.sql` (the warn test's predicate and columns, without `config(severity='warn')`):

```sql
/*
  Families piece 1 (spec §7, §8 V3) — ERROR severity from the commit that
  closed S2 (plan Task 15). It replaces warn_p1_era_map_undecided.sql, which
  warned while the owner's review batches R-DEC-ERA-B1..B<n> were open.

  One row per era key that no owner decision covers (decision =
  'undecided'), or whose decision went stale (keys_sha_ok = false: the keys
  or titles it covers changed after review). Every PB2017-PB2023 P-1 era key
  now carries a dated decision in dbt/seeds/p1_era_code_decisions.csv, so a
  key that loses its decision (a new edition row, a seed row removed or
  re-ranged, a retitled key) fails the build instead of printing a warning.
  tests/test_p1_era_line_map_sql.py::test_no_undecided_lists_undecided_and_stale_keys
  proves the predicate returns both kinds.
*/
select
    edition,
    era_key,
    line_item_code,
    account,
    organization,
    filed_title,
    decision,
    decision_id,
    keys_sha_ok
from {{ ref('p1_era_line_map') }}
where decision = 'undecided'
   or keys_sha_ok = false
```

In `tests/test_p1_era_line_map_sql.py` (Task 13 Step 5), replace

```python
def test_warn_test_lists_undecided_and_stale_keys():
    con = _lake()
    rows = _failures(con, "warn_p1_era_map_undecided")
    assert [(r[0], r[1], r[6]) for r in rows] == [(2019, "2035A-ARMY-L5", "undecided")]
    con.execute("update p1_era_line_map set keys_sha_ok = false where era_key = '0300D-DSS-L21'")
    assert len(_failures(con, "warn_p1_era_map_undecided")) == 2
```
with

```python
def test_no_undecided_lists_undecided_and_stale_keys():
    # Not in ALL_TESTS: the clean fixture keeps one undecided key on purpose.
    con = _lake()
    rows = _failures(con, "assert_p1_era_map_no_undecided")
    assert [(r[0], r[1], r[6]) for r in rows] == [(2019, "2035A-ARMY-L5", "undecided")]
    con.execute("update p1_era_line_map set keys_sha_ok = false where era_key = '0300D-DSS-L21'")
    assert len(_failures(con, "assert_p1_era_map_no_undecided")) == 2
```
(`ALL_TESTS` stays as it is.)

In `dbt/models/marts/schema.yml`, in the `p1_era_line_map` description (Task 13 Step 10), replace the closing clause

```
never reaches the program table (warn_p1_era_map_undecided.sql while S2 review batches are open)."
```
with

```
never reaches the program table (assert_p1_era_map_no_undecided.sql)."
```

Then confirm nothing else names the old test:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && grep -rn --exclude-dir=__pycache__ --exclude-dir=target --exclude-dir=logs "warn_p1_era_map_undecided" dbt tests src site/scripts | grep -v "^dbt/tests/assert_p1_era_map_no_undecided.sql:" || echo "no other references"
```
Expected: `no other references` (dbt's `target/` and `logs/` and Python caches still hold the old name until the next run and are skipped; the new test's header comment names the file it replaces and is filtered out; the plan and ROADMAP prose keep the name as history and are not searched). Checked on a copy of Task 13's files (G4 scratch tree) with this step's three edits applied: `tests/test_p1_era_line_map_sql.py` gives `40 passed` and the grep prints `no other references`.

- [ ] **Step 17: Run the map's SQL tests**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_p1_era_line_map_sql.py -q`
Expected: `40 passed` — Task 13 Step 8's count (the renamed test replaces the old one, so the count does not move; if Task 13 ended with a different count, expect that count), 0 failed.

- [ ] **Step 18: Rebuild the seed and the map in the live warehouse (SHARED LAKE WRITE, G4-3)**

This writes only the nodes S2 needs — the `stg_budget_lines` view (Task 7's, with `line_item_code`; rebuilt here as Task 13 Step 12 does, because the review can span days and a main-checkout build in between would drop the column), the `p1_era_code_decisions` seed table and the `p1_era_line_map` table — in the shared DuckDB, and runs their tests (dbt's default eager selection also runs every test that reads them). It never rebuilds other marts (a full `govbudget build` would rebuild every mart from whatever the lake holds at that minute). Make sure no other session holds `data/duckdb/govbudget.duckdb` (an export or a dbt run). Start it only outside the SAM window:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && MIN=$(date +%M) && if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: minute $MIN is in the SAM window (:15-:20, with margin)"; else GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data GOVBUDGET_DUCKDB=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/duckdb/govbudget.duckdb uv run --project . dbt build --project-dir dbt --profiles-dir dbt --select stg_budget_lines p1_era_code_decisions p1_era_line_map > tmp/era-review/build-close.log 2>&1; echo "exit=$?"; grep -E "stg_budget_lines|p1_era_code_decisions|p1_era_line_map |assert_p1_era_map_no_undecided|warn_p1_era_map" tmp/era-review/build-close.log; tail -1 tmp/era-review/build-close.log; fi
```
Expected: `exit=0`; lines `OK created sql view model main.stg_budget_lines`, `OK loaded seed file main.p1_era_code_decisions … [INSERT <1,128 + the batch rows>]`, `OK created sql table model main.p1_era_line_map`, `PASS assert_p1_era_map_no_undecided`, no `warn_p1_era_map_undecided` line; last line `Done. PASS=<n> WARN=0 ERROR=0 SKIP=0 …`. `Could not set lock on file` means another process holds the DuckDB file: wait and re-run. A `Binder Error` on `line_item_code` means the shared lake's `data/parquet/jbooks/budget_lines.parquet` lost the column (a main-checkout `jbooks export-facts`, README lake hazard): re-run `jbooks export-facts` from this branch (outside the SAM window, as Task 23 Step 1's recovery block does), then rebuild with this step.

- [ ] **Step 19: Prove the strict state on the live lake (read-only)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
uv run --project . python -m govbudget era-map check --strict > tmp/era-review/check.log; echo "exit=$?"; tail -1 tmp/era-review/check.log; uv run --project . python -c "import duckdb,os; c=duckdb.connect(os.environ['GOVBUDGET_DUCKDB'], read_only=True); print(c.execute(\"select count(*) filter (where decision = 'undecided' or keys_sha_ok = false), count(*), count(distinct ruling) filter (where ruling like 'R-DEC-ERA-B%') from p1_era_line_map\").fetchone())"
```
Expected: `exit=0`, `era-map check: 0 undecided chain(s), 0 stale decision(s)`, then `(0, 6927, <k>)` where `<k>` is the number of batches that ruled at least one key.

- [ ] **Step 20: Record the batch rulings in the ROADMAP**

Count the rulings:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && uv run --project . python - <<'PY'
import collections, csv
rows = list(csv.DictReader(open("dbt/seeds/p1_era_code_decisions.csv", newline="")))
batch = [r for r in rows if r["ruling"].startswith("R-DEC-ERA-B")]
print("batches:", sorted({r["ruling"] for r in batch}), "dates:", sorted({r["decided_on"] for r in batch}))
print("rows:", len(batch), "by decision:", dict(sorted(collections.Counter(r["decision"] for r in batch).items())))
chains = collections.Counter((r["line_item_code"], r["account"], r["organization"]) for r in batch)
print("chains:", len(chains), "range-split chains:", sum(1 for n in chains.values() if n > 1))
print("all rulings:", dict(sorted(collections.Counter(r["ruling"] for r in rows).items())))
PY
```

In `docs/superpowers/ROADMAP.md`, append one sentence to the end of the "Platform families (2026-10-02)" paragraph, after `` `wip/other-session-families-layout-2026-09-29`. ``, filling each `<…>` from the printout above and from Step 6:

```markdown
**Era-map review closed (<last decided_on>):** the owner ruled the <chains> chains
that needed an individual decision in <k> batches, **R-DEC-ERA-B1**–**R-DEC-ERA-B<k>**
(<first decided_on>–<last decided_on>), as <n same_program> same_program,
<n history_only> history_only and <n exclude_reused_code> exclude_reused_code
(<split chains> chains split by edition range); each row of
`dbt/seeds/p1_era_code_decisions.csv` names its batch, and the owner's replies are
kept verbatim in `data/research/era_map/batches/`. No PB2017–PB2023 era key is undecided:
`assert_p1_era_map_no_undecided` (error severity) replaced the warn test.
```
(Drop a decision from the list if its count is 0; add `exclude_placeholder`/`exclude_route_unsafe` if the owner used them.)

- [ ] **Step 21: Commit the S2 close**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/dbt/tests/assert_p1_era_map_no_undecided.sql GovBudget/tests/test_p1_era_line_map_sql.py GovBudget/dbt/models/marts/schema.yml GovBudget/docs/superpowers/ROADMAP.md && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "test(dbt): close S2 — no era key undecided (error severity); record R-DEC-ERA-B batches" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
(The `git rm` from Step 16 is already staged and lands in this commit.) Expected: `5 files changed` (one deletion, one creation, three modifications).

---
