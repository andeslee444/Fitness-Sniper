<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G2 (2026-10-13). -->

### Task 8: Map alias — `p1_era_line_map.program_key` from the route-safe seed, `era_map` load/classify alias, UNSAFE narrowed to (0390D, RDT&E) (#194)

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §4.5 "Where the alias applies" (`p1_era_line_map.sql`: `program_key = coalesce(alias.page_key, line_item_code)`; `era_map.load_inputs` and `classify`: a code with an alias is route-safe; `UNSAFE` narrows to exactly the unaliased (`0390D`, `RDT&E`) pair and any other unsafe code raises), §6.2 (the UNSAFE bullet: Appendix A and the final numbering give it to this task, not Task 4 — G4 notes contract issue 1), §2.3's cross-review paragraph (the deployed exporter raises when a `same_program` map row's `line_item_code` differs from its `program_key`, `export_site.py:7355-7362`; B must accept the alias), Q4 (the RDT&E chain keeps `exclude_route_unsafe`: the code has no route-safe key, so the reason stays literally true). Q25 (with Task 4a): once the alias exists, `propose` sends the era O&M chain to review instead of re-ruling it; Task 10 ratifies it as B7.

**Files:**
- Modify: `src/govbudget/jbooks/era_map.py` as Task 4a leaves it — the import block's last two lines (`collision_keys` / `era_keys`, about lines 45–46); `_TITLE_MARKERS` … `_ROUTE_UNSAFE_CHARS` (about lines 103–106); `def is_route_safe_code` (about lines 201–202, removed: the name is re-exported from `route_safe_codes`); `_Context.__init__`'s first two lines (about line 257); `_Context.classify`'s UNSAFE test (about line 339); `classify_keys`' signature, docstring line and body (about lines 358–382); the `load_inputs` loop (anchor on `if ed < 2024 or pe == "9999999999" or not is_route_safe_code(pe):`, about line 873)
- Modify: `dbt/models/marts/p1_era_line_map.sql` — the `program_key` header paragraph (about lines 29–34), the `program_key` select line (about line 165), the final `left join key_cells kc` (the end of the file)
- Modify: `dbt/models/marts/fct_program_decade_series.sql` — the header sentence "program_key is ALWAYS the bare printed code" (about lines 10–12)
- Modify: `dbt/models/marts/schema.yml` — `p1_era_line_map.program_key` (about line 440); the `fct_program_decade_series` description's clause "is carried to its bare printed code (program_key), with" (about line 467) and its `program_key` column (about line 471)
- Modify: `src/govbudget/export_site.py` — `_build_decade_citation_rows`' docstring (about lines 7144–7147), the "program_key is the PAGE key" comment (about lines 7305–7306), the map-row check (about lines 7353–7362), the citation comment "program key, i.e. the code printed at the cited cell (column I)." (about line 7557)
- Test: `tests/jbooks/era_map_fixtures.py` (the docstring row for the UNSAFE chain, about line 15; the `ERA` tuple for 0390D, about line 66)
- Test: `tests/jbooks/test_era_map.py` (the `era_map` import block's end; `test_route_unsafe_code_is_unsafe_even_when_modern_prints_it`, about lines 150–153)
- Test: `tests/jbooks/test_era_map_propose.py` (the `jbooks.era_map_fixtures` import; `test_propose_seed_rows`' expected set, about line 393 after Task 4a; new tests before `def test_missing_line_item_code_column_is_a_clear_precondition`)
- Test: `tests/test_p1_era_line_map_sql.py` (`_lake`'s signature and its last two lines; new tests before `def test_exclusions_carry_no_program_key():`; the import block is left alone — Task 9a edits it)
- Test: `tests/test_export_decade_era_map.py` (append at the end)
- Modify: `src/govbudget/cli.py` — the `era-map ratify` "ONE build" line Task 4b added (anchor on `" --profiles-dir dbt --select p1_era_code_decisions p1_era_line_map"`), so the advertised build loads the seed the map now reads (O-3)
- Test: `tests/jbooks/test_era_map_ratify.py` — `test_cli_ratify_names_the_one_build_that_keeps_conservation`'s expected line (Task 4b's pin)

**Interfaces:**
Consumes: Task 4b (the `era-map ratify` ONE-build success line in `cli.py` and its pin in `tests/jbooks/test_era_map_ratify.py`, which this task re-pins: Task 8 depends on 4b); Task 6 (`route_safe_codes.is_route_safe_code`, `load_route_safe_codes`, `page_key`, `P1_R1_RESTATEMENTS`, `UnsafeBudgetLineCode`, `SEED_COLUMNS`; the committed seed and the dbt seed `p1_route_safe_codes`); Task 4a (`era_keys.EraKeyConflict`; `era_map` imports nothing from `p1_loader`, and `route_safe_codes` keeps that true; `_hold_for_review`, which sends a chain whose class result differs from its seeded class row to `review.csv` with proposal `same_program` and the reason `"<rule>: class result … differs from the seeded …"`, and drops the old class row from the seed).
Produces (Tasks 9, 10, 11, 12, 21, 22 rely on these):
- `era_map.UNSAFE_UNALIASED = frozenset(P1_R1_RESTATEMENTS)` (= `{("0390D", "RDT&E")}`); `era_map.is_route_safe_code` is `route_safe_codes.is_route_safe_code`; `_Context(era, modern, route_safe=None)` and `classify_keys(era, modern, *, collision_codes, route_safe=None)`, where `route_safe` is an iterable of seeded `(account, printed code)` pairs, `None` meaning the committed seed; `classify` returns `"UNSAFE"` only for `UNSAFE_UNALIASED`, treats a seeded pair like any route-safe code, and raises `UnsafeBudgetLineCode` on any other route-unsafe code; `load_inputs` reads a PB2024–PB2026 row keyed by a page key (`0390DOM`) as a `ModernLine` with `code` = its printed code (`O&M`), still reads the pre-write stale rows keyed by the printed code `O&M` the same way, skips the restated `RDT&E` rows and raises `UnsafeBudgetLineCode` on any other route-unsafe `pe_bli`.
- `p1_era_line_map.program_key` = `coalesce(p1_route_safe_codes.page_key, line_item_code)` for `same_program`/`history_only`; the model now `ref`s the seed `p1_route_safe_codes`, so every build of the map needs that seed loaded (Tasks 21 and 22 select it, and `era-map ratify`'s success line now names it: `era-map ratify: next, ONE build: uv run --project . dbt build --project-dir dbt --profiles-dir dbt --select p1_route_safe_codes p1_era_code_decisions p1_era_line_map fct_program_decade_series (a map-only build fails assert_program_decade_conservation)`, which Task 10 quotes). The column count and order do not change (Task 9 adds `decided_on`).
- `_build_decade_citation_rows` accepts a map row whose `program_key` is the printed code's page key (`route_safe_codes.page_key(account, code)`) and refuses any other mismatch (`ValueError` naming the expected key); an aliased era grain's citations carry `pe_bli` = the page key (`0390DOM`); its `budget_lines_decade` rows keep the era key.
- Live state after this task: `era-map propose` on the live lake no longer reproduces the seed — the O&M chain (`O&M|0390D|`, 7 keys) classes A1 and goes to review (Task 10). `era-map check` and verify-era-map leg b are unchanged until Task 10 runs `propose`.

Measured for this task (2026-10-13; a scratch tree of HEAD plus Tasks 3, 4a, 4c, 6 and 7, and read-only runs on the live lake outside :12–:22):
- The era chains of account 0390D (`data/research/era_map/keys.csv`): `O&M|0390D|` = `0390D-ARMY-L1` in PB2017–PB2023, title "Chem Demilitarization - O&M", class UNSAFE, 7 keys, `keys_sha256` `523cd96c7d9031b4c4a43c45f4b72731a6fa140873c51c52b9a3700d47d595a2`, 801,553 thousand of era actuals; `RDT&E|0390D|` = `0390D-ARMY-L2`, 7 keys, 5,030,464. The live `p1_era_line_map` gives both `exclude_route_unsafe` (R-DEC-ERA-EXCLUDE) and `program_key` NULL.
- A scratch `era_map.propose` with this task's alias but WITHOUT Task 4a's guard (scratch out dir and seed copy) re-ruled the O&M chain silently to `same_program` R-DEC-ERA-SAME (`title_jaccard=1.00; continuity=7/7; actuals_k=801553`): the overturn Task 4a's guard exists to stop. Its counts: chains 1,253; `chain_groups` `a1_only` 811 → 812 and `unsafe` 2 → 1; `key_classes` A1 5,477 → 5,484 and UNSAFE 14 → 7; `key_class_actuals_k` UNSAFE 5,832,017 → 5,030,464.
- On that scratch tree the test files give: `tests/jbooks/test_era_map.py` 55 (51 + 4), `tests/jbooks/test_era_map_propose.py` 38 (Task 4a's 34 + 4), `tests/test_p1_era_line_map_sql.py` 43 (40 + 3), `tests/test_export_decade_era_map.py` 24 (22 + 2); `tests/jbooks/test_era_map_ratify.py` (28 + Task 4a's), `tests/test_era_review_batch_page.py`, `tests/test_verify_era_map.py` and `tests/test_program_decade_series_sql.py` stay green.

- [ ] **Step 1: Write the failing tests**

In `tests/jbooks/era_map_fixtures.py` (the module docstring's world table, about line 15), replace:

```python
  O&M|0390D|         UNSAFE                    → EXCLUDE route-unsafe
```

with:

```python
  RDT&E|0390D|       UNSAFE (no page key, #194) → EXCLUDE route-unsafe
```

and (the `ERA` list, about line 66: 0390D's `O&M` now has a page key, so the fixture's route-unsafe chain is the unaliased `RDT&E`) replace:

```python
    (2023, "0390D", "CBDP", "2", "O&M", "Operation & Maintenance", "60", None),
```

with:

```python
    (2023, "0390D", "CBDP", "2", "RDT&E", "Chem Demilitarization - RDT&E", "60", None),
```

In `tests/jbooks/test_era_map.py` (the end of the `era_map` import block), replace:

```python
    org_split_codes,
)

D = Decimal
```

with:

```python
    org_split_codes,
)
from govbudget.jbooks.route_safe_codes import UnsafeBudgetLineCode

D = Decimal
```

and (about lines 150–153) replace:

```python
def test_route_unsafe_code_is_unsafe_even_when_modern_prints_it():
    k = ek(2019, "0390D", "CBDP", 2, "O&M", "Operation & Maintenance")
    modern = [ml(2024, "O&M", "0390D", "CBDP", "Operation & Maintenance")]
    assert classes([k], modern) == {(2019, k.era_key): "UNSAFE"}
```

with:

```python
def test_route_unsafe_code_is_unsafe_even_when_modern_prints_it():
    # #194: the one unaliased route-unsafe pair (0390D's RDT&E, an R-1
    # restatement with no page key) stays UNSAFE.
    k = ek(2019, "0390D", "ARMY", 2, "RDT&E", "Chem Demilitarization - RDT&E")
    modern = [ml(2024, "RDT&E", "0390D", "A", "Chem Demilitarization - RDT&E")]
    assert era_map.UNSAFE_UNALIASED == frozenset({("0390D", "RDT&E")})
    assert classes([k], modern) == {(2019, k.era_key): "UNSAFE"}


def test_an_aliased_code_classifies_like_any_code():
    # #194: 0390D's O&M has the page key 0390DOM (dbt/seeds/
    # p1_route_safe_codes.csv), so its chain is A1 when PB2024-26 prints it
    # under the same title — never UNSAFE again.
    k = ek(2019, "0390D", "ARMY", 1, "O&M", "Chem Demilitarization - O&M")
    modern = [ml(2024, "O&M", "0390D", "A", "Chem Demilitarization - O&M")]
    assert classes([k], modern) == {(2019, k.era_key): "A1"}
    assert classes([k], []) == {(2019, k.era_key): "H"}
    # without the seed's pair the same code would raise
    with pytest.raises(UnsafeBudgetLineCode, match="0390D-ARMY-L1"):
        classify_keys([k], modern, collision_codes=NONE, route_safe=frozenset())


@pytest.mark.parametrize("account, code", [("0390D", "PROC&X"), ("2035A", "O&M"),
                                           ("3010F", "A/B")])
def test_any_other_route_unsafe_code_raises(account, code):
    k = ek(2019, account, "ARMY", 7, code, "Some Line")
    with pytest.raises(UnsafeBudgetLineCode, match=f"under {account}"):
        classes([k], [])
```

In `tests/jbooks/test_era_map_propose.py` (the import block; Task 4a changed the lines above it), replace:

```python
from jbooks.era_map_fixtures import (
```

with:

```python
from govbudget.jbooks.route_safe_codes import UnsafeBudgetLineCode
from jbooks.era_map_fixtures import (
```

and (`test_propose_seed_rows`' expected seed rows) replace:

```python
        "FY2017CR|2031A||2022-2022", "O&M|0390D||2023-2023",
```

with:

```python
        "FY2017CR|2031A||2022-2022", "RDT&E|0390D||2023-2023",
```

and (insert before `test_missing_line_item_code_column_is_a_clear_precondition`) replace:

```python
def test_missing_line_item_code_column_is_a_clear_precondition(tmp_path):
```

with:

```python
# #194: PB2024-26 rows of the aliased O&M line, before the Chem Demil write
# (keyed by the printed code) and after it (keyed by the page key 0390DOM),
# and the R-1 restatement RDT&E (no modern identity at all).
ALIAS_ROWS = [
    ("P-1", "2025", "0390D", "Acct", "A", "01", "BA", "O&M", "Chem Demilitarization - O&M",
     "fy_2023_actuals", "84612", "26", "Exhibit P-1", "O1190", "O&M"),
    ("P-1", "2026", "0390D", "Acct", "A", "01", "BA", "0390DOM", "Chem Demilitarization - O&M",
     "fy_2024_actuals", "87404", "26", "Exhibit P-1", "O303", "O&M"),
    ("P-1", "2025", "0390D", "Acct", "A", "02", "BA", "RDT&E", "Chem Demilitarization - RDT&E",
     "fy_2023_actuals", "975206", "26", "Exhibit P-1", "O1191", "RDT&E"),
]
ERA_OM = ("P-1", "2023", "0390D", "Acct", "ARMY", "01", "BA", "0390D-ARMY-L1",
          "Chem Demilitarization - O&M", "fy_2021_actuals", "104501", "23", "Exhibit P-1",
          "O1132", "O&M")


def test_load_inputs_reads_an_aliased_line_under_its_printed_code(tmp_path):
    inputs = era_map.load_inputs(make_lake(tmp_path, extra_era=ALIAS_ROWS))
    chem = sorted((m.edition, m.code) for m in inputs.modern if m.account == "0390D")
    assert chem == [(2025, "O&M"), (2026, "O&M")]


def test_load_inputs_refuses_an_unknown_route_unsafe_line(tmp_path):
    bad = ALIAS_ROWS[0][:7] + ("A/B",) + ALIAS_ROWS[0][8:]
    with pytest.raises(UnsafeBudgetLineCode, match="'A/B' under 0390D"):
        era_map.load_inputs(make_lake(tmp_path, extra_era=[bad]))


def test_propose_rules_an_aliased_chain_like_any_code(tmp_path):
    """No seed row yet: the O&M chain is A1 and R-DEC-ERA-SAME applies, so
    p1_era_line_map gives it program_key 0390DOM through the route-safe seed."""
    db = make_lake(tmp_path / "lake", extra_era=ALIAS_ROWS[1:2] + [ERA_OM])
    seed = tmp_path / "seeds" / "p1_era_code_decisions.csv"
    era_map.propose(duckdb_path=db, raw_docs_dir=make_raw_docs(tmp_path),
                    out_dir=tmp_path / "out", seed_path=seed, decided_on=ON)
    got = {r["decision_id"]: r for r in rows(seed)}
    om = got["O&M|0390D||2023-2023"]
    assert (om["decision"], om["ruling"], om["proposed_rule"]) == (
        "same_program", "R-DEC-ERA-SAME", "A1")
    assert got["RDT&E|0390D||2023-2023"]["decision"] == "exclude_route_unsafe"


def test_propose_sends_a_re_ruled_chain_to_review_not_into_the_seed(tmp_path):
    """Design §4.5 and Q25, through Task 4a's guard: the seed still says
    exclude_route_unsafe for the O&M chain (R-DEC-ERA-EXCLUDE, 2026-10-02);
    with its page key the chain classes A1, so propose sends it to review.csv
    proposed same_program and drops the old class row — never R-DEC-ERA-SAME
    over a seeded ruling in silence. Task 10 ratifies it as owner batch B7."""
    db = make_lake(tmp_path / "lake", extra_era=ALIAS_ROWS[1:2] + [ERA_OM])
    raw = make_raw_docs(tmp_path)
    seed = tmp_path / "seeds" / "p1_era_code_decisions.csv"
    era_map.propose(duckdb_path=db, raw_docs_dir=raw, out_dir=tmp_path / "out",
                    seed_path=seed, decided_on=ON)
    rows_now = rows(seed)
    for r in rows_now:
        if r["decision_id"] == "O&M|0390D||2023-2023":
            r.update(decision="exclude_route_unsafe", ruling="R-DEC-ERA-EXCLUDE",
                     proposed_rule="UNSAFE")
    era_map.write_seed(seed, rows_now)
    era_map.propose(duckdb_path=db, raw_docs_dir=raw, out_dir=tmp_path / "out",
                    seed_path=seed, decided_on=ON)
    held = {r["chain_id"]: r for r in rows(tmp_path / "out" / "review.csv")}["O&M|0390D|"]
    assert held["proposed_decision"] == "same_program"
    assert held["reason"] == (
        "A1: class result same_program (R-DEC-ERA-SAME) differs from the seeded"
        " exclude_route_unsafe (R-DEC-ERA-EXCLUDE, 2026-10-02) — confirm or keep the"
        " seeded decision; no silent overturn")
    assert not any(r["decision_id"].startswith("O&M|0390D|") for r in rows(seed))


def test_missing_line_item_code_column_is_a_clear_precondition(tmp_path):
```

In `tests/test_p1_era_line_map_sql.py` (`_lake`'s signature; the import block above is left as it is), replace:

```python
def _lake(lake=None, seed=None, docs=None) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
```

with:

```python
def _route_safe_seed() -> tuple[tuple[str, ...], list[dict]]:
    """(columns, rows) of the committed dbt/seeds/p1_route_safe_codes.csv (#194).
    Imported here, not at the top, so Task 9's import edits stay untouched."""
    import csv

    from govbudget.jbooks.route_safe_codes import SEED_COLUMNS, default_seed_path

    with open(default_seed_path(), newline="", encoding="utf-8") as fh:
        return SEED_COLUMNS, list(csv.DictReader(fh))


def _lake(lake=None, seed=None, docs=None, route_safe=None) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
```

and (`_lake`'s last two lines: the model now joins the seed) replace:

```python
    con.execute("create table p1_era_line_map as " + render_dbt_sql(MODEL))
    return con
```

with:

```python
    cols, committed = _route_safe_seed()
    con.execute("create table p1_route_safe_codes ("
                + ", ".join(f"{c} varchar" for c in cols) + ")")
    for row in (committed if route_safe is None else route_safe):
        con.execute(f"insert into p1_route_safe_codes values ({', '.join('?' * len(cols))})",
                    [row[c] for c in cols])
    con.execute("create table p1_era_line_map as " + render_dbt_sql(MODEL))
    return con
```

and (insert before `test_exclusions_carry_no_program_key`) replace:

```python
def test_exclusions_carry_no_program_key():
```

with:

```python
# #194: 0390D's era O&M chain (owner batch B7) prints 'O&M', which a web
# address cannot carry; its program key is the seeded page key 0390DOM.
OM_KEY = (2019, "0390D-ARMY-L1", "01", "Chem Demilitarization - O&M")
OM_LAKE = [("P-1", 2019, "0390D", "ARMY", "01", "0390D-ARMY-L1",
            "Chem Demilitarization - O&M", "fy_2017_actuals", 119985.0, "271", "O&M", "O1156")]


def _om_seed(decision="same_program"):
    return _seed() + [_seed_row(
        decision_id="O&M|0390D||2019-2019", line_item_code="O&M", account="0390D",
        first_edition="2019", last_edition="2019", decision=decision, n_keys="1",
        keys_sha256=keys_sha256([OM_KEY]), ruling="R-DEC-ERA-B7")]


def test_an_aliased_code_takes_its_route_safe_page_key():
    m = _map(_lake(lake=LAKE + OM_LAKE, seed=_om_seed()))
    om = m[(2019, "0390D-ARMY-L1")]
    assert (om["line_item_code"], om["program_key"], om["decision"], om["keys_sha_ok"]) == (
        "O&M", "0390DOM", "same_program", True)
    # every other code keeps its printed code as program_key
    assert m[(2019, "3010F-AF-L25")]["program_key"] == "F01500"


def test_without_the_seed_row_the_printed_code_would_be_the_key():
    om = _map(_lake(lake=LAKE + OM_LAKE, seed=_om_seed(), route_safe=[]))[(2019, "0390D-ARMY-L1")]
    assert om["program_key"] == "O&M"


def test_an_excluded_aliased_code_carries_no_program_key():
    om = _map(_lake(lake=LAKE + OM_LAKE, seed=_om_seed("exclude_route_unsafe")))[
        (2019, "0390D-ARMY-L1")]
    assert om["program_key"] is None


def test_exclusions_carry_no_program_key():
```

Append at the end of `tests/test_export_decade_era_map.py`:

```python


# ---------------------------------------------------------------------------
# #194 (families piece-1 follow-ups design §4.5): an era chain whose printed
# code a web address cannot carry joins the page of its route-safe key
# (dbt/seeds/p1_route_safe_codes.csv: 0390D 'O&M' -> 0390DOM, owner batch B7).
# ---------------------------------------------------------------------------

OM_LAKE = [("P-1", "2019", "0390D", "Chemical Agents and Munitions Destruction, Defense",
            "ARMY", "01", "Operation and maintenance", "0390D-ARMY-L1",
            "Chem Demilitarization - O&M", "fy_2017_actuals", "119985", "7",
            "Exhibit P-1", "O1156")]
OM_MAP = [(2019, "0390D", "ARMY", "01", "0390D-ARMY-L1", "O&M", "0390DOM", None, None,
           "same_program")]
OM_ACT = wb("ARMY", "01", "0390D-ARMY-L1", "fy_2017_actuals", account="0390D")
OM_GRAIN = ("0390DOM", 2017, 2019, "actuals", 119985.0, "fy_2017_actuals", None, None,
            1, OM_ACT, "era_line_map")


def test_an_aliased_era_chain_publishes_its_page_key(tmp_path):
    db = _make_warehouse(tmp_path, grains=NATIVE_GRAINS + ERA_GRAINS + [OM_GRAIN],
                         extra_lake=OM_LAKE, extra_map=OM_MAP)
    bl_rows, cit_rows, grains, _side, era_fids = _build(db, scope=SCOPE | {"0390DOM"})
    cit = {r[0]: r for r in cit_rows}
    bl = {r[0]: r for r in bl_rows}
    assert cit[OM_ACT][24] == "0390DOM"           # the citation names the page key
    assert bl[OM_ACT][8] == "0390D-ARMY-L1"       # the lake identity stays the era key
    assert OM_ACT in era_fids
    assert ("0390DOM", 2017, 2019) in {(g[0], g[1], g[2]) for g in grains}


def test_a_program_key_that_is_neither_the_code_nor_its_page_key_raises(tmp_path):
    bad = [(2019, "0390D", "ARMY", "01", "0390D-ARMY-L1", "O&M", "0390DOMX", None, None,
            "same_program")]
    db = _make_warehouse(tmp_path, extra_lake=OM_LAKE, extra_map=bad)
    with pytest.raises(ValueError, match="names program_key '0390DOMX'.*here '0390DOM'"):
        _build(db)
```

In `tests/jbooks/test_era_map_ratify.py` (`test_cli_ratify_names_the_one_build_that_keeps_conservation`, Task 4b's pin), replace:

```python
    assert out[1] == (
        "era-map ratify: next, ONE build: uv run --project . dbt build --project-dir dbt"
        " --profiles-dir dbt --select p1_era_code_decisions p1_era_line_map"
        " fct_program_decade_series (a map-only build fails"
        " assert_program_decade_conservation)")
```

with:

```python
    assert out[1] == (
        "era-map ratify: next, ONE build: uv run --project . dbt build --project-dir dbt"
        " --profiles-dir dbt --select p1_route_safe_codes p1_era_code_decisions"
        " p1_era_line_map fct_program_decade_series (a map-only build fails"
        " assert_program_decade_conservation)")
```

- [ ] **Step 2: Run them to see them fail**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_era_map.py tests/jbooks/test_era_map_propose.py tests/test_p1_era_line_map_sql.py tests/test_export_decade_era_map.py -q 2>&1 | grep -E '^(FAILED|ERROR)|passed|failed'
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_era_map_ratify.py -q 2>&1 | grep -E '^(FAILED|ERROR)|passed|failed'
```

Expected: the second command `FAILED tests/jbooks/test_era_map_ratify.py::test_cli_ratify_names_the_one_build_that_keeps_conservation` (`AssertionError`: the CLI still prints the selection without `p1_route_safe_codes`), `1 failed`, every other ratify test passed. The first command: `12 failed` (and every other test passed):
- `test_era_map.py`: `test_route_unsafe_code_is_unsafe_even_when_modern_prints_it` (`AttributeError: module 'govbudget.jbooks.era_map' has no attribute 'UNSAFE_UNALIASED'`), `test_an_aliased_code_classifies_like_any_code` (`{(2019, '0390D-ARMY-L1'): 'UNSAFE'} != {(2019, '0390D-ARMY-L1'): 'A1'}`), and the three `test_any_other_route_unsafe_code_raises` cases (`DID NOT RAISE`);
- `test_era_map_propose.py`: `test_load_inputs_reads_an_aliased_line_under_its_printed_code` (`[(2026, '0390DOM')] == [(2025, 'O&M'), (2026, 'O&M')]`), `test_load_inputs_refuses_an_unknown_route_unsafe_line` (`DID NOT RAISE`), `test_propose_rules_an_aliased_chain_like_any_code` (`('exclude_route_unsafe', 'R-DEC-ERA-EXCLUDE', 'UNSAFE') == ('same_program', 'R-DEC-ERA-SAME', 'A1')`), `test_propose_sends_a_re_ruled_chain_to_review_not_into_the_seed` (`KeyError: 'O&M|0390D|'`: without the alias nothing differs from the seed);
- `test_p1_era_line_map_sql.py`: `test_an_aliased_code_takes_its_route_safe_page_key` (`'O&M' == '0390DOM'`);
- `test_export_decade_era_map.py`: `test_an_aliased_era_chain_publishes_its_page_key` (`ValueError: decade: p1_era_line_map row PB2019 0390D-ARMY-L1 prints 'O&M' but names program_key '0390DOM'; the program key is always the bare printed code …`) and `test_a_program_key_that_is_neither_the_code_nor_its_page_key_raises` (`Regex pattern did not match`).

The fixture change alone (O&M → RDT&E in `era_map_fixtures.py`) keeps every existing propose and ratify test green: `RDT&E` is UNSAFE today too.

- [ ] **Step 3: Teach `era_map` the alias and narrow UNSAFE**

In `src/govbudget/jbooks/era_map.py` (the import block as Task 4a leaves it; `route_safe_codes` imports neither `p1_loader` nor psycopg, so Task 4a's `test_era_map_does_not_import_the_workbook_loader` stays green), replace:

```python
from govbudget.jbooks.collision_keys import require_resolved
from govbudget.jbooks.era_keys import EraKeyConflict, is_era_procurement_key
```

with:

```python
from govbudget.jbooks.collision_keys import require_resolved
from govbudget.jbooks.era_keys import EraKeyConflict, is_era_procurement_key
from govbudget.jbooks.route_safe_codes import (
    P1_R1_RESTATEMENTS,
    UnsafeBudgetLineCode,
    is_route_safe_code,
    load_route_safe_codes,
)
```

and replace:

```python
_TITLE_MARKERS = re.compile(r"\((?:myp|mip|space|multiyear|ap|ap-cy)\)")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
# export_site.is_route_safe_pe's character set (a page slug must survive a URL).
_ROUTE_UNSAFE_CHARS = frozenset("&#/?%")
```

with:

```python
# The one (account, code) pair that stays UNSAFE (#194, owner Q1 (a) and Q4,
# 2026-10-04): 0390D's RDT&E line restates R-1 program elements and gets no
# page key, so its era chain keeps exclude_route_unsafe. A route-unsafe code
# with a seeded page key (dbt/seeds/p1_route_safe_codes.csv: O&M -> 0390DOM)
# classifies like any code; any other route-unsafe code raises
# UnsafeBudgetLineCode. is_route_safe_code is route_safe_codes' (the same
# character set as export_site.is_route_safe_pe).
UNSAFE_UNALIASED = frozenset(P1_R1_RESTATEMENTS)

_TITLE_MARKERS = re.compile(r"\((?:myp|mip|space|multiyear|ap|ap-cy)\)")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
```

and (the local definition goes; the import above provides the name) replace:

```python
def is_route_safe_code(code: str) -> bool:
    return not (set(code) & _ROUTE_UNSAFE_CHARS or any(c.isspace() for c in code))


def org_split_codes(era: Iterable[EraKey]) -> frozenset[str]:
```

with:

```python
def org_split_codes(era: Iterable[EraKey]) -> frozenset[str]:
```

and replace:

```python
    def __init__(self, era: Sequence[EraKey], modern: Sequence[ModernLine]):
        self.era = list(era)
```

with:

```python
    def __init__(self, era: Sequence[EraKey], modern: Sequence[ModernLine],
                 route_safe: Iterable[tuple[str, str]] | None = None):
        self.era = list(era)
        # (account, printed code) pairs with a seeded page key (#194)
        self.route_safe = frozenset(
            load_route_safe_codes() if route_safe is None else route_safe)
```

and replace:

```python
        if code in CR_CODES:
            return "CR"
        if not is_route_safe_code(code):
            return "UNSAFE"
```

with:

```python
        if code in CR_CODES:
            return "CR"
        if not is_route_safe_code(code) and (k.account, code) not in self.route_safe:
            if (k.account, code) in UNSAFE_UNALIASED:
                return "UNSAFE"
            raise UnsafeBudgetLineCode(
                f"era key {k.era_key} (PB{k.edition}) prints {code!r} under"
                f" {k.account}: not route-safe, no page key in"
                " dbt/seeds/p1_route_safe_codes.csv and not UNSAFE_UNALIASED")
```

and replace:

```python
def classify_keys(
    era: Sequence[EraKey], modern: Sequence[ModernLine], *,
    collision_codes: frozenset[str],
) -> dict[tuple[int, str], str]:
    """{(edition, era_key): class} under CLASS_ORDER (§5.1; first match wins):

    CR      code is a FY2017CR/FY2018CR continuing-resolution placeholder;
    UNSAFE  code is not route-safe ('O&M', 'RDT&E' in 0390D);
```

with:

```python
def classify_keys(
    era: Sequence[EraKey], modern: Sequence[ModernLine], *,
    collision_codes: frozenset[str],
    route_safe: Iterable[tuple[str, str]] | None = None,
) -> dict[tuple[int, str], str]:
    """{(edition, era_key): class} under CLASS_ORDER (§5.1; first match wins):

    CR      code is a FY2017CR/FY2018CR continuing-resolution placeholder;
    UNSAFE  code is not route-safe and has no seeded page key: exactly
            UNSAFE_UNALIASED, 0390D's 'RDT&E' (#194; 'O&M' has the page key
            0390DOM and classifies like any code, route_safe defaulting to
            dbt/seeds/p1_route_safe_codes.csv). Any other route-unsafe code
            raises UnsafeBudgetLineCode;
```

and replace:

```python
    ctx = _Context(era, modern)
    return {(k.edition, k.era_key): ctx.classify(k, collision_codes) for k in ctx.era}
```

with:

```python
    ctx = _Context(era, modern, route_safe)
    return {(k.edition, k.era_key): ctx.classify(k, collision_codes) for k in ctx.era}
```

and (in `load_inputs`) replace:

```python
    modern: set[ModernLine] = set()
    for ed, account, org, _ba, pe, title, _code, _doc, _cells in rows:
        if ed < 2024 or pe == "9999999999" or not is_route_safe_code(pe):
            continue
        gk = (pe, account if pe in acct_split else None,
              org if pe in org_split else None, ed)
        modern.add(ModernLine(
            edition=ed, code=pe, account=account, organization=org, title=title,
```

with:

```python
    # #194: a PB2024–26 row keyed by a seeded page key (0390DOM) is the line
    # its printed code names (O&M), the code its era chain prints; before the
    # Chem Demil write the same rows are keyed by the printed code itself.
    # The R-1 restatement (RDT&E) is no modern identity; any other
    # route-unsafe pe_bli in the lake raises.
    route_safe = load_route_safe_codes()
    printed = {(c.account, c.page_key): c.line_item_code for c in route_safe.values()}
    modern: set[ModernLine] = set()
    for ed, account, org, _ba, pe, title, _code, _doc, _cells in rows:
        if ed < 2024 or pe == "9999999999":
            continue
        code = printed.get((account, pe), pe)
        if not is_route_safe_code(code) and (account, code) not in route_safe:
            if (account, code) in UNSAFE_UNALIASED:
                continue
            raise UnsafeBudgetLineCode(
                f"era-map: PB{ed} P-1 row {pe!r} under {account} is not route-safe and"
                " has no page key in dbt/seeds/p1_route_safe_codes.csv")
        gk = (pe, account if pe in acct_split else None,
              org if pe in org_split else None, ed)
        modern.add(ModernLine(
            edition=ed, code=code, account=account, organization=org, title=title,
```

- [ ] **Step 4: The map takes the page key from the seed**

In `dbt/models/marts/p1_era_line_map.sql` (the header, about lines 29–34), replace:

```sql
-- program_key is the bare printed code, set only for the two decisions that
-- carry points (same_program, history_only); NULL for every exclusion and
-- for undecided keys. program_account/program_org are the seed's pins (the
-- PB2026 account/organization whose page the points join); they are set
-- only for chains on one of the 13 PB2026 collision codes
-- (assert_p1_era_map_collision_pinned.sql).
```

with:

```sql
-- program_key is the printed code, set only for the two decisions that
-- carry points (same_program, history_only); NULL for every exclusion and
-- for undecided keys. A printed code a web address cannot carry takes its
-- owner-approved page key from dbt/seeds/p1_route_safe_codes.csv instead
-- (#194: 0390D's 'O&M' -> 0390DOM, the pe_bli its PB2024–PB2026 rows carry);
-- line_item_code keeps the printed code. program_account/program_org are
-- the seed's pins (the PB2026 account/organization whose page the points
-- join); they are set only for chains on one of the 13 PB2026 collision
-- codes (assert_p1_era_map_collision_pinned.sql).
```

and replace:

```sql
    case when b.decision in ('same_program', 'history_only') then b.line_item_code end as program_key,
```

with:

```sql
    case when b.decision in ('same_program', 'history_only')
         then coalesce(rs.page_key, b.line_item_code) end as program_key,
```

and (the end of the file) replace:

```sql
left join key_cells kc
  on kc.edition = b.edition
 and kc.era_key = b.era_key
```

with:

```sql
left join key_cells kc
  on kc.edition = b.edition
 and kc.era_key = b.era_key
left join {{ ref('p1_route_safe_codes') }} rs
  on rs.account = b.account
 and rs.line_item_code = b.line_item_code
```

In `dbt/models/marts/fct_program_decade_series.sql` (the header, about lines 10–12; comment only, the SQL already reads `p1_era_line_map.program_key`), replace:

```sql
-- (assert_program_decade_grain_unique.sql). program_key is ALWAYS the bare
-- printed code; account/organization are non-NULL only for the 13 PB2026
-- collision codes, exactly as in fct_decade_series. No suffixed key exists.
```

with:

```sql
-- (assert_program_decade_grain_unique.sql). program_key is ALWAYS the
-- printed code, or for a code a web address cannot carry its owner-approved
-- page key (p1_era_line_map.program_key; #194: 0390DOM, the pe_bli its
-- PB2024–PB2026 native rows carry); account/organization are non-NULL only
-- for the 13 PB2026 collision codes, exactly as in fct_decade_series. No
-- suffixed key exists.
```

In `dbt/models/marts/schema.yml` (`p1_era_line_map` → `program_key`, about line 440), replace:

```yaml
        description: "The bare printed code (= line_item_code) when decision is same_program or history_only; NULL for every exclusion and for undecided keys. Never suffixed: a collision code's page split comes only from program_account / program_org."
```

with:

```yaml
        description: "The printed code (= line_item_code) when decision is same_program or history_only, except a code a web address cannot carry, which takes its owner-approved page key from dbt/seeds/p1_route_safe_codes.csv (#194: 0390D's 'O&M' -> 0390DOM); NULL for every exclusion and for undecided keys. Never suffixed: a collision code's page split comes only from program_account / program_org."
```

and (the `fct_program_decade_series` description, about line 467; one clause changes) replace:

```yaml
    description: "Families piece 1 (spec §4.5): fct_decade_series at PROGRAM grain — the same CTEs (collision anchors and candidate patterns copied verbatim, the slug pick copied with map_basis added to its partition; tests/test_program_decade_series_sql.py guards the copies) plus one step: a PB2017–PB2023 P-1 era row whose p1_era_line_map decision is same_program or history_only is carried to its bare printed code (program_key), with the map's pinned program_account / program_org on the 13 PB2026 collision codes. Era lines sharing a code and a map_basis in an edition sum exactly as modern lines sharing a code do; a same_program and a history_only chain of one code and edition stay two rows. Excluded and undecided era rows produce no grain. Grain: (program_key, account, organization, fy, edition_year, map_basis), and (program_key, account, organization, fy, edition_year) is unique among the native and era_line_map rows pages read — assert_program_decade_grain_unique.sql. Every map_basis='native' row equals its fct_decade_series row in every edition (assert_program_decade_native_equals_line.sql); era grains conserve the mapped fct_decade_series era grains per edition and slug (assert_program_decade_conservation.sql). fct_decade_series itself is unchanged and keeps feeding F-15's builder, verify-phase5e and fct_book_diff."
```

with:

```yaml
    description: "Families piece 1 (spec §4.5): fct_decade_series at PROGRAM grain — the same CTEs (collision anchors and candidate patterns copied verbatim, the slug pick copied with map_basis added to its partition; tests/test_program_decade_series_sql.py guards the copies) plus one step: a PB2017–PB2023 P-1 era row whose p1_era_line_map decision is same_program or history_only is carried to its program_key (the printed code, or its route-safe page key: 0390DOM for 0390D's 'O&M'), with the map's pinned program_account / program_org on the 13 PB2026 collision codes. Era lines sharing a code and a map_basis in an edition sum exactly as modern lines sharing a code do; a same_program and a history_only chain of one code and edition stay two rows. Excluded and undecided era rows produce no grain. Grain: (program_key, account, organization, fy, edition_year, map_basis), and (program_key, account, organization, fy, edition_year) is unique among the native and era_line_map rows pages read — assert_program_decade_grain_unique.sql. Every map_basis='native' row equals its fct_decade_series row in every edition (assert_program_decade_native_equals_line.sql); era grains conserve the mapped fct_decade_series era grains per edition and slug (assert_program_decade_conservation.sql). fct_decade_series itself is unchanged and keeps feeding F-15's builder, verify-phase5e and fct_book_diff."
```

and (`fct_program_decade_series` → `program_key`, about line 471) replace:

```yaml
        description: "The bare printed budget line code (P-1) or program element (R-1). For native rows it is fct_decade_series.pe_bli; for era rows it is p1_era_line_map.program_key. Never an era key, never suffixed."
```

with:

```yaml
        description: "The printed budget line code (P-1), or its route-safe page key where a web address cannot carry it (0390DOM for 0390D's 'O&M'), or the program element (R-1). For native rows it is fct_decade_series.pe_bli; for era rows it is p1_era_line_map.program_key. Never an era key, never suffixed."
```

In `src/govbudget/cli.py` (`cmd_era_map`'s ratify success line, which Task 4b added), replace:

```python
        print("era-map ratify: next, ONE build: uv run --project . dbt build --project-dir dbt"
              " --profiles-dir dbt --select p1_era_code_decisions p1_era_line_map"
              " fct_program_decade_series (a map-only build fails"
              " assert_program_decade_conservation)")
```

with:

```python
        # Since #194 (follow-ups Task 8) p1_era_line_map reads the seed
        # p1_route_safe_codes, so the one build loads that seed too.
        print("era-map ratify: next, ONE build: uv run --project . dbt build --project-dir dbt"
              " --profiles-dir dbt --select p1_route_safe_codes p1_era_code_decisions"
              " p1_era_line_map fct_program_decade_series (a map-only build fails"
              " assert_program_decade_conservation)")
```

- [ ] **Step 5: The exporter accepts the page key on a map row**

In `src/govbudget/export_site.py` (`_build_decade_citation_rows`' docstring, about lines 7144–7147), replace:

```python
    PB2017-PB2023 P-1 lines summed under their bare printed code through
    same_program decisions; 'era_history_only' rows are data only and never
    become points (R-DEC-FAM-ERAONLY). fct_decade_series present while the
```

with:

```python
    PB2017-PB2023 P-1 lines summed under their program key (the printed
    code, or its route-safe page key, #194) through same_program decisions;
    'era_history_only' rows are data only and never become points
    (R-DEC-FAM-ERAONLY). fct_decade_series present while the
```

and replace:

```python
        # program_key is the PAGE key: exactly fct_decade_series.pe_bli on
        # native rows, the bare printed code on era rows. account /
```

with:

```python
        # program_key is the PAGE key: exactly fct_decade_series.pe_bli on
        # native rows, the printed code on era rows (or its route-safe page
        # key from dbt/seeds/p1_route_safe_codes.csv, #194). account /
```

and (the map-row check, about lines 7353–7362) replace:

```python
            for (m_ed, m_acct, m_org, m_ba, m_key, m_code, m_prog,
                 m_pin_acct, m_pin_org) in map_rows:
                if m_code != m_prog:
                    raise ValueError(
                        f"decade: p1_era_line_map row PB{m_ed} {m_key} prints"
                        f" {m_code!r} but names program_key {m_prog!r}; the"
                        " program key is always the bare printed code (spec"
                        " §4.5), and era citations publish that code as pe_bli"
                    )
```

with:

```python
            from govbudget.jbooks.route_safe_codes import page_key as _page_key

            for (m_ed, m_acct, m_org, m_ba, m_key, m_code, m_prog,
                 m_pin_acct, m_pin_org) in map_rows:
                want_prog = _page_key(m_acct, m_code) or m_code
                if m_prog != want_prog:
                    raise ValueError(
                        f"decade: p1_era_line_map row PB{m_ed} {m_key} prints"
                        f" {m_code!r} but names program_key {m_prog!r}; the"
                        " program key is the printed code, or its page key in"
                        " dbt/seeds/p1_route_safe_codes.csv (#194), here"
                        f" {want_prog!r}, and era citations publish it as pe_bli"
                    )
```

and (about line 7557) replace:

```python
            # never re-minted; the citation's pe_bli below is the grain's
            # program key, i.e. the code printed at the cited cell (column I).
```

with:

```python
            # never re-minted; the citation's pe_bli below is the grain's
            # program key, i.e. the code printed at the cited cell (column I),
            # or that code's route-safe page key (#194: O&M -> 0390DOM).
```

- [ ] **Step 6: Run the tests — they pass**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_era_map.py tests/jbooks/test_era_map_propose.py tests/test_p1_era_line_map_sql.py tests/test_export_decade_era_map.py -q 2>&1 | tail -1
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_era_map_ratify.py tests/test_era_review_batch_page.py tests/test_verify_era_map.py tests/test_program_decade_series_sql.py tests/test_export_era_line_map.py -q 2>&1 | tail -1
uvx --offline ruff check --isolated --select F,E9 src/govbudget/jbooks/era_map.py | tail -1
uv run --project . dbt parse --project-dir dbt --profiles-dir dbt > /dev/null && echo parse-ok
```

Expected: `160 passed` (55 + 38 + 43 + 24; with Tasks 4a's propose tests counted); then `… passed` with no `failed` on the second line (it includes the re-pinned ratify CLI test); `All checks passed!`; `parse-ok`.

- [ ] **Step 7: What `propose` would do on the live lake now (read-only, scratch outputs)**

A scratch `propose` (copies of the seed and of `data/research/era_map`, read-only DuckDB) shows the O&M chain going to review. It writes only under `$GOVBUDGET_PROOFS/fu-t8-propose/`, removed at the end; Task 10 runs the real `propose`.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
S="${GOVBUDGET_PROOFS:?}/fu-t8-propose"; rm -rf "${S:?}" && mkdir -p "$S/out" && cp dbt/seeds/p1_era_code_decisions.csv "$S/seed.csv"
uv run --project . python - "$S" <<'EOF'
import csv, sys
from pathlib import Path
from govbudget import config
from govbudget.jbooks import era_map
S = Path(sys.argv[1])
c = era_map.propose(duckdb_path=config.DUCKDB_PATH, raw_docs_dir=config.RAW_DOCS_DIR,
                    out_dir=S / "out", seed_path=S / "seed.csv",
                    decided_on=era_map.CLASS_RULINGS_DECIDED_ON)
print(c["rulings"], c["review_rows"], c["key_classes"]["UNSAFE"], c["key_classes"]["A1"])
for r in csv.DictReader(open(S / "out" / "review.csv", newline="")):
    print(r["chain_id"], r["proposed_decision"], r["keys_sha256"][:12], r["actuals_k"], "|", r["reason"])
print(sum(1 for r in csv.DictReader(open(S / "seed.csv", newline="")) if r["line_item_code"] == "O&M"))
EOF
rm -rf "${S:?}"
```

Expected (measured 2026-10-13 with this script on a scratch tree of HEAD plus Tasks 3, 4a, 4c, 6, 7 and this task): `{'R-DEC-ERA-SAME': 810, 'R-DEC-ERA-EXCLUDE': 46, 'R-DEC-ERA-HISTORY': 271} 1 7 5484`, then `O&M|0390D| same_program 523cd96c7d90 801553 | A1: class result same_program (R-DEC-ERA-SAME) differs from the seeded exclude_route_unsafe (R-DEC-ERA-EXCLUDE, 2026-10-02) — confirm or keep the seeded decision; no silent overturn`, then `0` (the old class row left the scratch seed). Any other review row, or a `stale` key, means the lake moved since 2026-10-13: stop and report it before Task 10.

- [ ] **Step 8: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/jbooks/era_map.py GovBudget/dbt/models/marts/p1_era_line_map.sql GovBudget/dbt/models/marts/fct_program_decade_series.sql GovBudget/dbt/models/marts/schema.yml GovBudget/src/govbudget/export_site.py GovBudget/src/govbudget/cli.py GovBudget/tests/jbooks/era_map_fixtures.py GovBudget/tests/jbooks/test_era_map.py GovBudget/tests/jbooks/test_era_map_propose.py GovBudget/tests/jbooks/test_era_map_ratify.py GovBudget/tests/test_p1_era_line_map_sql.py GovBudget/tests/test_export_decade_era_map.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(era-map): program_key takes the route-safe page key (0390D O&M -> 0390DOM) in p1_era_line_map, era_map and the decade tier; UNSAFE narrows to 0390D RDT&E, any other unsafe code raises (#194)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `12 files changed` (the twelve paths above, `cli.py` and `tests/jbooks/test_era_map_ratify.py` among them: the O-3 re-pin of Task 4b's ONE-build line). Nothing here touches the live lake: the map is rebuilt with the seed in Tasks 21 (snapshot) and 22 (release).
