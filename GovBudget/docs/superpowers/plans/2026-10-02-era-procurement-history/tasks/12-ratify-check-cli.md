<!-- Part of the families piece-1 plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; ../notes.md has background. -->

### Task 12: ratify / check / seed config / CLI

**Spec:** §4.3 (the seed is all-varchar in `dbt_project.yml`, as `program_aliases` is; a row exists
only once decided), §5.3 (batches ratified with `decided_by=owner`, `decided_on`,
`ruling=R-DEC-ERA-B<n>`; `check` lists undecided chains and stale `keys_sha256`), §7 (keys or titles
changed after review ⇒ `keys_sha256` mismatch fails `era-map check`; collision chains must be
pinned; "Code spanning organizations" — decided per organization, and with CONTRACT ISSUE 9b no
two organizations' same_program keys on one page in one edition), §4.7 CLI (as
`govbudget era-map {propose,ratify,check}` per the contract). CONTRACT ISSUE 9a: a batch decides
whole chains.

**Files:**
- Modify: `src/govbudget/jbooks/era_map.py` (append after Task 11's last line `    return counts`)
- Modify: `dbt/dbt_project.yml:20-24` (add the seed's column types after `program_aliases`)
- Modify: `src/govbudget/cli.py` (insert `cmd_era_map` before `def cmd_refresh` at `:2921`; insert the
  parser after `ev.set_defaults(func=cmd_evals)` at `:3257`; line numbers at the branch base,
  Tasks 3/5 may shift them, the text anchors are unique)
- Test: `tests/jbooks/test_era_map_ratify.py`

**Interfaces:** Consumes: everything Tasks 10–11 produce; the committed seed (Task 11);
`config.DUCKDB_PATH`, `config.RAW_DOCS_DIR`, `config.RESEARCH_DIR`, `config.ROOT`
(`src/govbudget/config.py`). / Produces: `default_seed_path() -> Path`
(`config.ROOT/dbt/seeds/p1_era_code_decisions.csv`), `default_out_dir() -> Path`
(`config.RESEARCH_DIR/era_map`), private `_page_grain(row, collision_codes)` and
`_row_editions(row, keys_by_chain)` (CONTRACT ISSUE 9b), `ratify(*, review_csv, seed_path, batch,
decided_on, duckdb_path) -> int` (refuses part-decided chains and a second organization on one
page, CONTRACT ISSUE 9), `check(*, duckdb_path, seed_path) -> {"undecided": [{"chain_id", "editions", "n_keys"}],
"stale": [{"decision_id", "seed_n_keys", "lake_n_keys", "seed_sha256", "lake_sha256"}]}`;
`cli.cmd_era_map(args)`; CLI `govbudget era-map propose [--decided-on DATE]`,
`govbudget era-map ratify --batch B<n> --decided-on DATE [--review FILE]` (exit 1 and `REFUSED` on
any validation error, nothing written), `govbudget era-map check [--strict]` (exit 1 on any stale
decision; `--strict` also on any undecided key; last line
`era-map check: <n> undecided chain(s), <m> stale decision(s)`); the dbt seed config
`seeds: govbudget: p1_era_code_decisions: +column_types` (22 varchar columns).

- [ ] **Step 1: Write the failing tests**

Create `tests/jbooks/test_era_map_ratify.py`:

```python
"""era_map ratify / check, the dbt seed config and the `era-map` CLI (plan
Task 12; spec §4.3, §5.3, §7) on the miniature lake in era_map_fixtures."""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import pytest
import yaml

from govbudget.jbooks import era_map
from jbooks.era_map_fixtures import make_lake, make_raw_docs

ROOT = Path(__file__).resolve().parents[2]
ON = date(2026, 10, 2)
DECIDED = date(2026, 10, 5)


@pytest.fixture(autouse=True)
def _mini_org_split(monkeypatch):
    monkeypatch.setattr(era_map, "ORG_SPLIT_CODES", frozenset({"20"}))


@pytest.fixture()
def world(tmp_path):
    db = make_lake(tmp_path / "lake")
    raw = make_raw_docs(tmp_path)
    out = tmp_path / "research" / "era_map"
    seed = tmp_path / "seeds" / "p1_era_code_decisions.csv"
    era_map.propose(duckdb_path=db, raw_docs_dir=raw, out_dir=out,
                    seed_path=seed, decided_on=ON)
    return {"db": db, "out": out, "seed": seed, "review": out / "review.csv"}


def read(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def write_review(path, rows):
    era_map.write_csv(path, era_map.REVIEW_COLUMNS, rows)


def decide(world, edits, extra=()):
    """Apply {chain_id: {field: value}} to review.csv; append extra rows
    (copies of an existing chain's row with overrides, for range splits)."""
    rows = read(world["review"])
    by_id = {r["chain_id"]: r for r in rows}
    for cid, fields in edits.items():
        by_id[cid].update(fields)
    for cid, fields in extra:
        rows.append({**by_id[cid], **fields})
    write_review(world["review"], rows)


def ratify(world, batch="B1", decided_on=DECIDED):
    return era_map.ratify(review_csv=world["review"], seed_path=world["seed"],
                          batch=batch, decided_on=decided_on,
                          duckdb_path=world["db"])


GOOD = {
    "1045|1612N|": {"decision": "same_program", "note": "OHIO Replacement = COLUMBIA"},
    "20|0300D|DSS": {"decision": "same_program"},   # pre-filled 0300D/DCSA
    "50|0300D|": {"decision": "exclude_reused_code", "last_edition": "2022"},
    "20|0300D|DHRA": {"decision": "history_only"},  # pre-filled 0300D/DHRA
}
SPLIT = [("50|0300D|", {"decision": "history_only", "first_edition": "2023",
                        "last_edition": "2023"})]


# ---------------------------------------------------------------------------
# ratify
# ---------------------------------------------------------------------------

def test_ratify_merges_a_batch_with_a_range_split(world):
    decide(world, GOOD, SPLIT)
    assert ratify(world) == 5
    seed = {r["decision_id"]: r for r in read(world["seed"])}
    b1 = {k: r for k, r in seed.items() if r["ruling"] == "R-DEC-ERA-B1"}
    assert set(b1) == {"1045|1612N||2022-2022", "20|0300D|DSS|2022-2022",
                       "50|0300D||2022-2022", "50|0300D||2023-2023",
                       "20|0300D|DHRA|2023-2023"}
    assert (b1["20|0300D|DHRA|2023-2023"]["program_account"],
            b1["20|0300D|DHRA|2023-2023"]["program_org"]) == ("0300D", "DHRA")
    dss = b1["20|0300D|DSS|2022-2022"]
    assert (dss["decision"], dss["program_account"], dss["program_org"]) == (
        "same_program", "0300D", "DCSA")
    assert {r["decided_by"] for r in b1.values()} == {"owner"}
    assert {r["decided_on"] for r in b1.values()} == {"2026-10-05"}
    assert b1["1045|1612N||2022-2022"]["note"] == "OHIO Replacement = COLUMBIA"
    assert b1["50|0300D||2022-2022"]["n_keys"] == "1"
    assert b1["50|0300D||2023-2023"]["titles_seen"] == "2023: DTRA Cyber Activities"
    assert len(seed) == 7 + 5
    assert era_map.check(duckdb_path=world["db"], seed_path=world["seed"]) == {
        "undecided": [], "stale": []}


@pytest.mark.parametrize("edits, extra, message", [
    ({"1045|1612N|": {"decision": "same"}}, [], "not in"),
    ({"1045|1612N|": {"decision": "same_program", "keys_sha256": "0" * 64}}, [],
     "changed since review"),
    ({"20|0300D|DSS": {"decision": "same_program", "program_org": ""}}, [],
     "program_account and program_org are required"),
    ({"20|0300D|DSS": {"decision": "same_program", "program_org": "DSS"}}, [],
     "is not a PB2026 page"),
    ({"20|0300D|DHRA": {"decision": "same_program"}}, [], "is not a PB2026 page"),
    ({"20|0300D|DHRA": {"decision": "history_only", "program_org": "XYZ"}}, [],
     "is not a PB2024-26 P-1 line"),
    ({"1045|1612N|": {"decision": "same_program", "program_account": "1611N"}}, [],
     "only set for"),
    ({"50|0300D|": {"decision": "history_only", "successor_code": "5731D15610"}}, [],
     "is not the book-stated successor"),
    ({"50|0300D|": {"decision": "history_only", "first_edition": "2017"}}, [],
     "outside the chain"),
    ({"50|0300D|": {"decision": "history_only"}},
     [("50|0300D|", {"decision": "exclude_reused_code", "first_edition": "2023"})],
     "overlaps"),
    # half a range split: PB2023 would never return to review.csv
    ({"50|0300D|": {"decision": "exclude_reused_code", "last_edition": "2022"}}, [],
     "editions 2023 left undecided"),
])
def test_ratify_refuses_and_writes_nothing(world, edits, extra, message):
    decide(world, edits, extra)
    before = world["seed"].read_bytes()
    with pytest.raises(ValueError, match=message):
        ratify(world)
    assert world["seed"].read_bytes() == before


def test_ratify_refuses_bad_batch_labels_and_reuse(world):
    decide(world, GOOD, SPLIT)
    with pytest.raises(ValueError, match="is not B<n>"):
        ratify(world, batch="b1")
    assert ratify(world) == 5
    with pytest.raises(ValueError, match="already in"):
        ratify(world)
    with pytest.raises(ValueError, match="overlaps"):
        ratify(world, batch="B2")


def test_propose_after_ratify_drops_the_ratified_chains(world):
    decide(world, GOOD, SPLIT)
    ratify(world)
    era_map.propose(duckdb_path=world["db"], raw_docs_dir=world["db"].parents[2] / "raw_docs",
                    out_dir=world["out"], seed_path=world["seed"], decided_on=ON)
    assert read(world["review"]) == []
    assert sum(r["ruling"] == "R-DEC-ERA-B1" for r in read(world["seed"])) == 5


def test_ratify_refuses_an_undecided_file(world):
    with pytest.raises(ValueError, match="no row has a decision"):
        ratify(world)


def test_ratify_accepts_the_book_stated_successor(world, tmp_path):
    # a review row for the JLTV chain (class-ruled in this world) re-proposed
    # after an owner override: drop its class-ruled seed row first
    seed = [r for r in read(world["seed"]) if r["line_item_code"] != "5600D15603"]
    era_map.write_seed(world["seed"], seed)
    chains = {r["chain_id"]: r for r in read(world["out"] / "chains.csv")}
    jltv = chains["5600D15603|2035A|"]
    row = {c: "" for c in era_map.REVIEW_COLUMNS}
    row.update({"chain_id": jltv["chain_id"], "first_edition": "2022",
                "last_edition": "2023", "keys_sha256": jltv["keys_sha256"],
                "decision": "history_only", "successor_code": "5731D15610"})
    write_review(world["review"], [row])
    assert ratify(world) == 1
    got = next(r for r in read(world["seed"]) if r["line_item_code"] == "5600D15603")
    assert (got["successor_code"], got["successor_account"]) == ("5731D15610", "2035A")
    assert got["successor_evidence"] == jltv["successor_evidence"]


# ---------------------------------------------------------------------------
# one organization per page grain and edition
# ---------------------------------------------------------------------------

@pytest.fixture()
def clash_world(tmp_path, monkeypatch):
    # PB2022 prints `10` for TJS (page 10 is TJS's; class-ruled SAME) and DPAA,
    # and `20` for DTRA (page 20-DTRA; class-ruled SAME) and DLA.
    monkeypatch.setattr(era_map, "ORG_SPLIT_CODES", frozenset({"10", "20"}))
    db = make_lake(tmp_path / "lake", org_clash=True)
    out = tmp_path / "research" / "era_map"
    seed = tmp_path / "seeds" / "p1_era_code_decisions.csv"
    era_map.propose(duckdb_path=db, raw_docs_dir=make_raw_docs(tmp_path), out_dir=out,
                    seed_path=seed, decided_on=ON)
    return {"db": db, "out": out, "seed": seed, "review": out / "review.csv"}


@pytest.mark.parametrize("edits", [
    {"10|0300D|DPAA": {"decision": "same_program"}},
    {"20|0300D|DLA": {"decision": "same_program", "program_account": "0300D",
                      "program_org": "DTRA"}},
])
def test_ratify_refuses_a_second_organization_on_one_page(clash_world, edits):
    decide(clash_world, edits)
    before = clash_world["seed"].read_bytes()
    with pytest.raises(ValueError, match="same_program collides with .* in PB2022"):
        ratify(clash_world)
    assert clash_world["seed"].read_bytes() == before


def test_ratify_accepts_the_pre_filled_history_only(clash_world):
    decide(clash_world, {"10|0300D|DPAA": {"decision": "history_only"},
                         "20|0300D|DLA": {"decision": "history_only"}})
    assert ratify(clash_world) == 2
    got = {r["decision_id"]: (r["decision"], r["program_account"], r["program_org"])
           for r in read(clash_world["seed"]) if r["ruling"] == "R-DEC-ERA-B1"}
    assert got == {"10|0300D|DPAA|2022-2022": ("history_only", "", ""),
                   # the chain's own identity: no PB2024-26 line prints 20 for DLA
                   "20|0300D|DLA|2022-2022": ("history_only", "0300D", "DLA")}


def test_ratify_refuses_two_organizations_on_one_page_in_one_batch(clash_world):
    # TJS's chain re-reviewed (its class-ruled row dropped) beside DPAA's
    era_map.write_seed(clash_world["seed"], [
        r for r in read(clash_world["seed"]) if r["line_item_code"] != "10"])
    tjs = {r["chain_id"]: r for r in read(clash_world["out"] / "chains.csv")}[
        "10|0300D|TJS"]
    rows = read(clash_world["review"])
    rows.append({**{c: "" for c in era_map.REVIEW_COLUMNS},
                 "chain_id": tjs["chain_id"], "first_edition": "2022",
                 "last_edition": "2023", "keys_sha256": tjs["keys_sha256"],
                 "decision": "same_program"})
    dpaa = next(r for r in rows if r["chain_id"] == "10|0300D|DPAA")
    dpaa["decision"] = "same_program"
    write_review(clash_world["review"], rows)
    with pytest.raises(ValueError, match="same_program collides with"):
        ratify(clash_world)
    dpaa["decision"] = "history_only"
    write_review(clash_world["review"], rows)
    assert ratify(clash_world) == 2


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------

def test_check_lists_undecided_chains(world):
    res = era_map.check(duckdb_path=world["db"], seed_path=world["seed"])
    assert res["stale"] == []
    assert res["undecided"] == [
        {"chain_id": "1045|1612N|", "editions": [2022], "n_keys": 1},
        {"chain_id": "20|0300D|DHRA", "editions": [2023], "n_keys": 1},
        {"chain_id": "20|0300D|DSS", "editions": [2022], "n_keys": 1},
        {"chain_id": "50|0300D|", "editions": [2022, 2023], "n_keys": 2},
    ]


def test_check_flags_a_stale_and_a_vanished_decision(world):
    rows = read(world["seed"])
    target = next(r for r in rows if r["line_item_code"] == "ATA000")
    target["keys_sha256"] = "f" * 64
    ghost = {**target, "decision_id": "GHOST1|3010F||2022-2022",
             "line_item_code": "GHOST1", "first_edition": "2022",
             "last_edition": "2022"}
    era_map.write_seed(world["seed"], rows + [ghost])
    stale = {s["decision_id"]: s for s in era_map.check(
        duckdb_path=world["db"], seed_path=world["seed"])["stale"]}
    assert set(stale) == {"ATA000|3010F||2022-2023", "GHOST1|3010F||2022-2022"}
    assert stale["ATA000|3010F||2022-2023"]["lake_n_keys"] == 2
    assert stale["GHOST1|3010F||2022-2022"]["lake_n_keys"] == 0


# ---------------------------------------------------------------------------
# dbt seed config
# ---------------------------------------------------------------------------

def test_dbt_seed_config_is_all_varchar():
    project = yaml.safe_load((ROOT / "dbt" / "dbt_project.yml").read_text())
    cfg = project["seeds"]["govbudget"]["p1_era_code_decisions"]["+column_types"]
    assert cfg == {c: "varchar" for c in era_map.SEED_COLUMNS}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@pytest.fixture()
def cli_world(tmp_path, monkeypatch):
    from govbudget import config

    db = make_lake(tmp_path / "data")
    raw = make_raw_docs(tmp_path / "data")
    monkeypatch.setattr(config, "DUCKDB_PATH", db)
    monkeypatch.setattr(config, "RAW_DOCS_DIR", raw)
    monkeypatch.setattr(config, "RESEARCH_DIR", tmp_path / "repo" / "data" / "research")
    monkeypatch.setattr(config, "ROOT", tmp_path / "repo")
    return tmp_path / "repo"


def test_cli_propose_check_ratify(cli_world, capsys):
    from govbudget.cli import main

    main(["era-map", "propose"])
    out = capsys.readouterr().out
    assert out.startswith("era-map propose: 15 era keys, 11 chains; rulings"
                          " SAME=3 EXCLUDE=2 HISTORY=2; 4 chain(s) for review")
    seed = cli_world / "dbt" / "seeds" / "p1_era_code_decisions.csv"
    assert {r["decided_on"] for r in read(seed)} == {"2026-10-02"}
    assert (cli_world / "data" / "research" / "era_map" / "counts.json").is_file()

    main(["era-map", "check"])
    assert capsys.readouterr().out.splitlines()[-1] == (
        "era-map check: 4 undecided chain(s), 0 stale decision(s)")
    with pytest.raises(SystemExit) as exc:
        main(["era-map", "check", "--strict"])
    assert exc.value.code == 1

    with pytest.raises(SystemExit) as exc:
        main(["era-map", "ratify", "--batch", "B1", "--decided-on", "2026-10-05"])
    assert exc.value.code == 1
    assert "REFUSED" in capsys.readouterr().err


@pytest.mark.parametrize("argv", [["era-map", "--help"], ["era-map", "propose", "--help"],
                                  ["era-map", "ratify", "--help"],
                                  ["era-map", "check", "--help"]])
def test_cli_help_renders(argv, capsys):
    from govbudget.cli import main

    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 0
    assert "usage: govbudget era-map" in capsys.readouterr().out
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `uv run --project . pytest tests/jbooks/test_era_map_ratify.py -q`

Expected: `28 failed` (AttributeError `module 'govbudget.jbooks.era_map' has no attribute 'ratify'` /
`'check'`, `KeyError: 'p1_era_code_decisions'` for the dbt config, and argparse
`invalid choice: 'era-map'` exits for the five CLI tests).

- [ ] **Step 3: Append ratify and check**

Append to the end of `src/govbudget/jbooks/era_map.py`, leaving two blank lines after
`    return counts`:

```python
# ---------------------------------------------------------------------------
# ratify / check (§5.3, §7)
# ---------------------------------------------------------------------------


def default_seed_path() -> Path:
    from govbudget import config

    return config.ROOT / "dbt" / "seeds" / "p1_era_code_decisions.csv"


def default_out_dir() -> Path:
    from govbudget import config

    return config.RESEARCH_DIR / "era_map"


def _page_grain(row: Mapping[str, str],
                collision_codes: frozenset[str]) -> tuple[str, str, str]:
    """The fct_program_decade_series page grain a same_program row's keys
    join (spec §4.5): the bare code, plus the pins on a PB2026 collision
    code."""
    code = row["line_item_code"]
    if code in collision_codes:
        return (code, row["program_account"], row["program_org"])
    return (code, "", "")


def _row_editions(row: Mapping[str, str],
                  keys_by_chain: Mapping[str, Sequence[EraKey]]) -> set[int]:
    """The editions inside the row's range in which its chain holds keys."""
    cid = chain_id(row["line_item_code"], row["account"], row["organization"])
    first, last = int(row["first_edition"]), int(row["last_edition"])
    return {k.edition for k in keys_by_chain.get(cid, ()) if first <= k.edition <= last}


def ratify(
    *, review_csv: Path, seed_path: Path, batch: str, decided_on: date,
    duckdb_path: Path,
) -> int:
    """Merge the owner-decided rows of review_csv (non-blank `decision`) into
    the seed as ruling R-DEC-ERA-<batch>, decided_by owner. Validates, and
    writes nothing unless every row passes:

      * batch matches B<n> and has not been ratified before;
      * decision is in DECISIONS;
      * the chain still exists and its keys_sha256 equals the review-time
        value (otherwise the chain changed after review: re-run propose);
      * first_edition..last_edition lies inside the chain and holds keys;
      * collision code + same_program/history_only: program_account and
        program_org both set, naming a PB2026 page (same_program), or a
        PB2024–26 P-1 line identity or the chain's own account/organization
        (history_only); every other row leaves them blank;
      * successor_code only on history_only, and only the book-stated
        successor propose recorded in chains.csv beside review_csv;
      * no range overlaps an existing seed row or another row of the batch;
      * one organization per page grain and edition: an org-split chain's
        same_program row may not share a page grain (_page_grain) and an
        edition holding keys with another organization's same_program row,
        already in the seed or in this batch (codes '10' and '15' are not
        PB2026 collision codes, so two organizations' same_program keys
        would sum into one page);
      * every chain the batch touches is decided in full: its seed rows and
        batch rows together cover every edition in which it holds keys.
        propose re-proposes only chains with no owner row, so a part-decided
        chain would never return to review.csv; split the whole chain into
        ranges, or leave its decision blank (defer it) until it is.
    Returns the number of rows added."""
    if not BATCH_RE.match(batch):
        raise ValueError(f"batch {batch!r} is not B<n> (e.g. B1)")
    ruling = f"R-DEC-ERA-{batch}"
    review_csv = Path(review_csv)
    rows = read_csv(review_csv)
    missing = set(REVIEW_COLUMNS) - set(rows[0].keys() if rows else REVIEW_COLUMNS)
    if missing:
        raise ValueError(f"{review_csv}: missing columns {sorted(missing)}")
    decided = [r for r in rows if (r.get("decision") or "").strip()]
    if not decided:
        raise ValueError(f"{review_csv}: no row has a decision — nothing to ratify")
    existing = read_seed(Path(seed_path))
    if any(r["ruling"] == ruling for r in existing):
        raise ValueError(f"{ruling} is already in {seed_path}; use a new batch number")
    stated = {r["chain_id"]: r for r in read_csv(review_csv.parent / "chains.csv")}

    inputs = load_inputs(Path(duckdb_path))
    ctx = _Context(inputs.era, inputs.modern)
    classes = {(k.edition, k.era_key): ctx.classify(k, inputs.collision_codes)
               for k in ctx.era}
    by_id = {c.chain_id: c for c in build_chains(inputs.era, classes)}
    keys_by_chain = group_keys(inputs.era)
    line_idents = {(m.code, m.account, m.organization) for m in inputs.modern}

    errors: list[str] = []
    new: list[dict] = []
    for r in decided:
        cid = r["chain_id"]
        decision = r["decision"].strip()
        ch = by_id.get(cid)
        if ch is None:
            errors.append(f"{cid}: no such chain in the lake")
            continue
        if r["keys_sha256"] != ch.keys_sha256:
            errors.append(f"{cid}: keys_sha256 changed since review"
                          f" ({r['keys_sha256'][:12]} -> {ch.keys_sha256[:12]});"
                          " re-run propose and re-review")
            continue
        if decision not in DECISIONS:
            errors.append(f"{cid}: decision {decision!r} not in {DECISIONS}")
            continue
        try:
            first, last = int(r["first_edition"]), int(r["last_edition"])
        except ValueError:
            errors.append(f"{cid}: first/last edition must be integers")
            continue
        if not (ch.first_edition <= first <= last <= ch.last_edition):
            errors.append(f"{cid}: range {first}-{last} outside the chain"
                          f" ({ch.first_edition}-{ch.last_edition})")
            continue
        n_keys, sha = range_sha(keys_by_chain[cid], first, last)
        if n_keys == 0:
            errors.append(f"{cid}: range {first}-{last} holds no era key")
            continue
        pa, po = r["program_account"].strip(), r["program_org"].strip()
        pinned = (ch.line_item_code in inputs.collision_codes
                  and decision in ("same_program", "history_only"))
        if pinned:
            ident = (ch.line_item_code, pa, po)
            if not pa or not po:
                errors.append(f"{cid}: collision code — program_account and"
                              " program_org are required")
                continue
            if decision == "same_program" and ident not in inputs.modern_pages:
                errors.append(f"{cid}: {ident} is not a PB2026 page")
                continue
            own = {(k.account, _modern_org(k.organization))
                   for k in keys_by_chain[cid]}
            if (decision == "history_only" and ident not in line_idents
                    and (pa, po) not in own):
                errors.append(f"{cid}: {ident} is not a PB2024-26 P-1 line or"
                              f" the chain's own identity {sorted(own)}")
                continue
        elif pa or po:
            errors.append(f"{cid}: program_account/program_org are only set for"
                          " collision-code same_program/history_only rows")
            continue
        successor: dict[str, str] = {}
        succ = r["successor_code"].strip()
        if succ:
            book = stated.get(cid, {})
            if decision != "history_only":
                errors.append(f"{cid}: successor_code only on history_only rows")
                continue
            if book.get("successor_code") != succ:
                errors.append(f"{cid}: successor {succ!r} is not the book-stated"
                              f" successor {book.get('successor_code') or '(none)'!r}")
                continue
            successor = {f: book[f] for f in
                         ("successor_code", "successor_account", "successor_evidence")}
        new.append(seed_row(
            ch, first=first, last=last, n_keys=n_keys, keys_sha=sha,
            decision=decision, ruling=ruling, decided_on=decided_on,
            program_account=pa, program_org=po, successor=successor,
            modern_title=r["modern_title"],
            evidence=(f"continuity={r['continuity']}; actuals_k={r['actuals_k']};"
                      f" proposed={r['proposed_decision'] or '(none)'}:"
                      f" {r['reason']}"),
            note=r["note"],
        ))
    cc = inputs.collision_codes
    for i, a in enumerate(new):
        for b in existing + new[:i]:
            if _ranges_overlap(a, b):
                errors.append(f"{a['decision_id']} overlaps {b['decision_id']}")
            if (a["decision"] == b["decision"] == "same_program"
                    and a["organization"] and b["organization"]
                    and a["organization"] != b["organization"]
                    and _page_grain(a, cc) == _page_grain(b, cc)):
                shared = sorted(_row_editions(a, keys_by_chain)
                                & _row_editions(b, keys_by_chain))
                if shared:
                    code, pin_a, pin_o = _page_grain(a, cc)
                    page = f"{code} ({pin_a}/{pin_o})" if pin_o else code
                    errors.append(
                        f"{a['decision_id']}: same_program collides with"
                        f" {b['decision_id']} — page {page} would"
                        f" sum {a['organization']} and {b['organization']} in"
                        f" {', '.join(f'PB{e}' for e in shared)}; decide"
                        " history_only for the organization whose page it is not")
    touched = sorted({chain_id(a["line_item_code"], a["account"], a["organization"])
                      for a in new})
    for cid in touched:
        covered: set[int] = set()
        for r in existing + new:
            if chain_id(r["line_item_code"], r["account"], r["organization"]) == cid:
                covered.update(range(int(r["first_edition"]),
                                     int(r["last_edition"]) + 1))
        open_eds = sorted({k.edition for k in keys_by_chain[cid]} - covered)
        if open_eds:
            errors.append(f"{cid}: editions {', '.join(map(str, open_eds))} left"
                          " undecided — split the whole chain or defer it")
    if errors:
        raise ValueError("era-map ratify refused; nothing written:\n  "
                         + "\n  ".join(errors))
    write_seed(Path(seed_path), existing + new)
    return len(new)


def check(*, duckdb_path: Path, seed_path: Path) -> dict:
    """{"undecided": [{"chain_id", "editions", "n_keys"}],
        "stale": [{"decision_id", "seed_n_keys", "lake_n_keys",
                   "seed_sha256", "lake_sha256"}]}

    undecided: era keys no seed row covers (chain + edition range).
    stale: seed rows whose keys in the current lake no longer hash to the
    reviewed keys_sha256 (or whose chain is gone)."""
    era = load_era_keys(Path(duckdb_path), with_amounts=False)
    keys_by_chain = group_keys(era)
    seed = read_seed(Path(seed_path))
    stale, covered = [], set()
    for r in seed:
        cid = chain_id(r["line_item_code"], r["account"], r["organization"])
        first, last = int(r["first_edition"]), int(r["last_edition"])
        keys = keys_by_chain.get(cid, [])
        n_keys, sha = range_sha(keys, first, last)
        if sha != r["keys_sha256"] or n_keys != int(r["n_keys"]):
            stale.append({"decision_id": r["decision_id"],
                          "seed_n_keys": int(r["n_keys"]), "lake_n_keys": n_keys,
                          "seed_sha256": r["keys_sha256"], "lake_sha256": sha})
        covered.update((cid, k.edition, k.era_key) for k in keys
                       if first <= k.edition <= last)
    undecided = []
    for cid, keys in sorted(keys_by_chain.items()):
        open_keys = [k for k in keys if (cid, k.edition, k.era_key) not in covered]
        if open_keys:
            undecided.append({"chain_id": cid,
                              "editions": sorted({k.edition for k in open_keys}),
                              "n_keys": len(open_keys)})
    return {"undecided": undecided, "stale": stale}
```

- [ ] **Step 4: Run the tests: the module tests pass, config and CLI still fail**

Run: `uv run --project . pytest tests/jbooks/test_era_map_ratify.py -q`

Expected: `6 failed, 22 passed`. The failures are `test_dbt_seed_config_is_all_varchar`,
`test_cli_propose_check_ratify` and the four `test_cli_help_renders` cases.

- [ ] **Step 5: Declare the seed all-varchar**

In `dbt/dbt_project.yml`, after the `program_aliases` block (`:20-24`, the end of the file):

Before:
```yaml
    program_aliases:
      +column_types:
        alias: varchar
        pe_bli: varchar
        notes: varchar
```
After:
```yaml
    program_aliases:
      +column_types:
        alias: varchar
        pe_bli: varchar
        notes: varchar
    p1_era_code_decisions:
      +column_types:
        decision_id: varchar
        line_item_code: varchar
        account: varchar
        organization: varchar
        first_edition: varchar
        last_edition: varchar
        decision: varchar
        program_account: varchar
        program_org: varchar
        successor_code: varchar
        successor_account: varchar
        successor_evidence: varchar
        n_keys: varchar
        keys_sha256: varchar
        titles_seen: varchar
        modern_title: varchar
        proposed_rule: varchar
        evidence: varchar
        decided_on: varchar
        decided_by: varchar
        ruling: varchar
        note: varchar
```

- [ ] **Step 6: Add the CLI command function**

In `src/govbudget/cli.py`, insert the function between `cmd_evals` and `cmd_refresh`.

Before (`:2916-2922` at the branch base):
```python
    else:
        print(f"unknown evals action: {args.evals_action}", file=sys.stderr)
        sys.exit(2)


def cmd_refresh(args) -> None:
    """ROADMAP #8 — unattended end-to-end refresh."""
```
After:
```python
    else:
        print(f"unknown evals action: {args.evals_action}", file=sys.stderr)
        sys.exit(2)


def cmd_era_map(args) -> None:
    """Families piece 1 (spec §5): era P-1 line → program decisions.

    propose  classify + chain + class rulings + successor search; writes
             data/research/era_map/ and the class-ruled seed rows.
    ratify   merge one owner-approved review batch into the seed.
    check    list undecided era keys and stale decisions (exit 1 on stale;
             --strict also exits 1 on undecided)."""
    from datetime import date

    from govbudget.jbooks import era_map

    seed_path = era_map.default_seed_path()
    out_dir = era_map.default_out_dir()
    if args.era_map_action == "propose":
        counts = era_map.propose(
            duckdb_path=config.DUCKDB_PATH, raw_docs_dir=config.RAW_DOCS_DIR,
            out_dir=out_dir, seed_path=seed_path,
            decided_on=date.fromisoformat(args.decided_on),
        )
        print(f"era-map propose: {counts['era_keys']} era keys,"
              f" {counts['chains']} chains; rulings"
              f" SAME={counts['rulings'][era_map.RULING_SAME]}"
              f" EXCLUDE={counts['rulings'][era_map.RULING_EXCLUDE]}"
              f" HISTORY={counts['rulings'][era_map.RULING_HISTORY]};"
              f" {counts['review_rows']} chain(s) for review -> {out_dir}")
    elif args.era_map_action == "ratify":
        try:
            n = era_map.ratify(
                review_csv=Path(args.review) if args.review else out_dir / "review.csv",
                seed_path=seed_path, batch=args.batch,
                decided_on=date.fromisoformat(args.decided_on),
                duckdb_path=config.DUCKDB_PATH,
            )
        except (ValueError, FileNotFoundError, RuntimeError) as e:
            print(f"era-map ratify: REFUSED — {e}", file=sys.stderr)
            sys.exit(1)
        print(f"era-map ratify: {n} decision row(s) added as R-DEC-ERA-{args.batch}"
              f" -> {seed_path}")
    elif args.era_map_action == "check":
        res = era_map.check(duckdb_path=config.DUCKDB_PATH, seed_path=seed_path)
        for u in res["undecided"]:
            print(f"  undecided {u['chain_id']} editions"
                  f" {','.join(map(str, u['editions']))} ({u['n_keys']} key(s))")
        for s in res["stale"]:
            print(f"  stale {s['decision_id']}: {s['seed_n_keys']} key(s)"
                  f" {s['seed_sha256'][:12]} reviewed, lake has {s['lake_n_keys']}"
                  f" {s['lake_sha256'][:12]}")
        print(f"era-map check: {len(res['undecided'])} undecided chain(s),"
              f" {len(res['stale'])} stale decision(s)")
        if res["stale"] or (args.strict and res["undecided"]):
            sys.exit(1)


def cmd_refresh(args) -> None:
    """ROADMAP #8 — unattended end-to-end refresh."""
```
(`cli.py` already imports `sys`, `Path` and `config` at `:1-8`.)

- [ ] **Step 7: Register the `era-map` parser**

In `src/govbudget/cli.py` `main()`, after the `evals` parser.

Before (`:3253-3259` at the branch base):
```python
    ev = sub.add_parser("evals", help="phase 5B-4 eval refresh/check pipeline")
    ev_sub = ev.add_subparsers(dest="evals_action", required=True)
    ev_sub.add_parser("refresh", help="re-run answer_sql, update expected_answer in-place")
    ev_sub.add_parser("check", help="check expected_answer freshness; exit 1 if stale")
    ev.set_defaults(func=cmd_evals)

    dos = sub.add_parser("dossiers", help="phase 5B-3 dossier research pipeline")
```
After:
```python
    ev = sub.add_parser("evals", help="phase 5B-4 eval refresh/check pipeline")
    ev_sub = ev.add_subparsers(dest="evals_action", required=True)
    ev_sub.add_parser("refresh", help="re-run answer_sql, update expected_answer in-place")
    ev_sub.add_parser("check", help="check expected_answer freshness; exit 1 if stale")
    ev.set_defaults(func=cmd_evals)

    em = sub.add_parser(
        "era-map",
        help="families piece 1: era P-1 line -> program decisions (propose/ratify/check)",
    )
    em_sub = em.add_subparsers(dest="era_map_action", required=True)
    em_prop = em_sub.add_parser(
        "propose",
        help="classify era keys, apply the class rulings, search successors;"
             " writes data/research/era_map/ and the class-ruled seed rows",
    )
    em_prop.add_argument(
        "--decided-on", dest="decided_on", default="2026-10-02",
        help="decided_on for class-ruled rows (default: the rulings' approval"
             " date, 2026-10-02)",
    )
    em_rat = em_sub.add_parser(
        "ratify", help="merge one owner-approved review batch into the seed")
    em_rat.add_argument("--batch", required=True, help="batch label, e.g. B1")
    em_rat.add_argument("--decided-on", dest="decided_on", required=True,
                        help="ISO date the owner approved the batch")
    em_rat.add_argument("--review", default=None,
                        help="review CSV (default data/research/era_map/review.csv)")
    em_chk = em_sub.add_parser(
        "check", help="list undecided era keys and stale decisions; exit 1 on stale")
    em_chk.add_argument("--strict", action="store_true",
                        help="also exit 1 when any era key is undecided")
    em.set_defaults(func=cmd_era_map)

    dos = sub.add_parser("dossiers", help="phase 5B-3 dossier research pipeline")
```
(No help string contains `%`, which argparse would try to format; `test_cli_help_renders` checks this.)

- [ ] **Step 8: Run the tests and watch them pass**

Run: `uv run --project . pytest tests/jbooks/test_era_map_ratify.py -q`

Expected: `28 passed`.

Run: `uv run --project . pytest tests/jbooks/test_era_map.py tests/jbooks/test_era_map_propose.py tests/jbooks/test_era_map_ratify.py tests/jbooks/test_era_keys.py tests/test_collision_keys.py tests/test_shrink_guard.py -q`

Expected: `138 passed, 2 skipped` (0 failed). The 2 skips are the pre-existing warehouse checks
in `tests/test_collision_keys.py`, which need `GOVBUDGET_DATA`; with
`GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data` set (they open DuckDB
`read_only=True`) the result is `140 passed`.

- [ ] **Step 9: Load the committed seed into a scratch DuckDB with dbt**

This writes only a temporary DuckDB file and the gitignored `dbt/target`, `dbt/logs`. Never point
it at the real warehouse.
```bash
SEEDCHECK="$(mktemp -d)/seedcheck.duckdb" && GOVBUDGET_DUCKDB="$SEEDCHECK" uv run --project . dbt seed --project-dir dbt --profiles-dir dbt --select p1_era_code_decisions && uv run --project . python -c "import duckdb,sys; c=duckdb.connect(sys.argv[1], read_only=True); print(c.execute('select count(*), count(distinct decision_id), count(program_account), count(successor_code) from p1_era_code_decisions').fetchone(), sorted({r[1] for r in c.execute('describe p1_era_code_decisions').fetchall()}))" "$SEEDCHECK"
```
Expected: dbt ends `Done. PASS=1 WARN=0 ERROR=0 SKIP=0 ...`, then
```
(1128, 1128, 22, 1) ['VARCHAR']
```
(1,128 class-ruled rows with unique `decision_id`s; 22 pinned collision chains, all with both
`program_account` and `program_org`; 1 successor; blanks load as NULL).

- [ ] **Step 10: Exercise the CLI on the live lake (read-only)**

```bash
OUT="$(mktemp)"; GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data uv run --project . python -m govbudget era-map check > "$OUT"; echo "exit=$?"; tail -1 "$OUT"; grep -c '^  undecided ' "$OUT"; grep '30|0300D|DODEA' "$OUT"
```
Expected:
```
exit=0
era-map check: 125 undecided chain(s), 0 stale decision(s)
125
  undecided 30|0300D|DODEA editions 2017,2018,2019,2020,2021,2022,2023 (7 key(s))
```
```bash
GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data uv run --project . python -m govbudget era-map check --strict > /dev/null; echo "exit=$?"
```
Expected: `exit=1` (125 chains await the Task 15 review batches).
```bash
GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data uv run --project . python -m govbudget era-map propose && git status --short dbt/seeds data/research/era_map
```
Expected: one line
`era-map propose: 6927 era keys, 1253 chains; rulings SAME=810 EXCLUDE=47 HISTORY=271; 125 chain(s) for review -> /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/data/research/era_map`
and no `git status` output (the CLI default `--decided-on 2026-10-02` reproduces Task 11's files byte
for byte).

- [ ] **Step 11: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/src/govbudget/jbooks/era_map.py GovBudget/src/govbudget/cli.py GovBudget/dbt/dbt_project.yml GovBudget/tests/jbooks/test_era_map_ratify.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(era-map): ratify/check, all-varchar seed config, govbudget era-map CLI (spec §4.3, §5.3, §7)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
