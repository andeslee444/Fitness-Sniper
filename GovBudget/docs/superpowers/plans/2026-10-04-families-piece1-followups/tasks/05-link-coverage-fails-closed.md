<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G4 (2026-10-13). -->

### Task 5: link-coverage fails closed (#200)

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §6.5: fail when the baseline recorded `receipts_match_citations` True and the report has None; with `--baseline` and `--write-baseline`, compare first and refuse one path for both; a summary card with a value and neither a fid nor an `xml_path` counts as (d), live 0; the 440 cards with an `xml_path` are reported as their own count (Q20); `json.loads` TypeError and ValueError count as (d). §6 (one CLI convention: a tool error prints `link-coverage: ERROR — <message>` and exits 2; a failed check exits 1). §7 W6 runs this tool against the committed baseline.

**Files:**
- Modify: `src/govbudget/link_coverage.py` — `_page_figures` (anchor on `    for card in (detail.get("summary") or {}).get("cards") or []:`), a new `_xml_path_cards` after it, `_Classifier._derived` (anchor on `except ValueError:\n            return "d"`), `compute_link_coverage` (the sidecar loop and `site.update`), `compare_to_baseline` (anchor on `    violations.extend(absolute_violations(report))`)
- Modify: `src/govbudget/cli.py` — `cmd_link_coverage` (whole function, about lines 2545–2587)
- Test: `tests/test_link_coverage.py` (append at the end)

**Interfaces:**
Consumes: Task 1's workspace.
Produces (Task 21 and Task 22 run W6 with it):
- `compute_link_coverage(site_dir)["site"]["summary_cards_cited_by_xml_path"]: int` — summary cards with no fid, a value and an `xml_path` (J-book detail cards; outside V9, Q20).
- A summary card with a value and neither a fid nor an `xml_path` is a figure keyed `nofid:<slug>:summary_cards:<index>` of class (d).
- `compare_to_baseline(report, baseline)` adds the violation `"receipt audit missing: the baseline recorded receipts_match_citations true, but json/budget_pdf_receipts_audit.json is absent from this site (re-run export-budget-pdf-receipts)"`.
- `govbudget link-coverage`: exit 0 PASS, 1 FAIL, 2 tool error (`link-coverage: ERROR — <message>`, no traceback). With both `--baseline` and `--write-baseline`, the two must be different files; the report is compared first, and the new baseline is written only when there are 0 violations (`link-coverage: baseline NOT written to <path> (the report has violations)` otherwise). A second stdout line reports `link-coverage: <n> summary card(s) cited by XML path only, outside V9 (Q20)`.

Measured for this task (2026-10-13, read-only on the live `data/site`, built 2026-10-04): `uv run --project . python -m govbudget link-coverage --site-dir "$GOVBUDGET_DATA/site" --baseline data/research/link_coverage/baseline.json` → `link-coverage: 61,645 budget figures on 2,562 program pages: a 60,983 · b 662 · c 0 · d 0; source-linked 100.00%, PDF-highlighted 98.93%; 2,415 of 2,562 pages fully PDF-highlighted`, `compared against data/research/link_coverage/baseline.json (44,747 baseline (a) figures)`, `0 violation(s)`, `PASS` (2.2 s). The committed baseline's `site.receipts_match_citations` is `true`. Across the 2,562 sidecars' 10,248 summary cards: 440 have no fid, a value and an `xml_path` (306 pages; e.g. `0305234N.json`, `{"fid": null, "value": 0.0, "xml_path": "ProgramElement[241]", "basis": "jbook-detail", …}`); 0 have a value with neither. `tests/test_link_coverage.py`: 10 passed.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_link_coverage.py`:

```python


# ---------------------------------------------------------------------------
# ROADMAP #200 (follow-ups spec 2026-10-04 §6.5): fail closed
# ---------------------------------------------------------------------------

def test_a_baseline_that_recorded_the_receipt_audit_fails_when_the_audit_is_missing(tmp_path):
    s0 = compute_link_coverage(write_site(tmp_path / "s0", citations=CITATIONS, receipts=RECEIPTS,
                                          pages={"AAA": page(lines=[fid(1)])}))
    baseline = baseline_from_report(s0)
    assert baseline["site"]["receipts_match_citations"] is True
    unaudited = compute_link_coverage(write_site(tmp_path / "s4", citations=CITATIONS,
                                                 receipts=RECEIPTS,
                                                 pages={"AAA": page(lines=[fid(1)])},
                                                 audit_sha=None))
    assert compare_to_baseline(unaudited, baseline) == [
        "receipt audit missing: the baseline recorded receipts_match_citations true, but"
        " json/budget_pdf_receipts_audit.json is absent from this site"
        " (re-run export-budget-pdf-receipts)"
    ]


def test_a_value_card_with_no_source_is_d_and_an_xml_path_card_is_counted_apart(tmp_path):
    detail = page(lines=[fid(1)])
    detail["summary"]["cards"] += [
        {"fid": None, "value": 12.5},                                    # a value, no source
        {"fid": None, "value": 0.0, "xml_path": "ProgramElement[241]"},  # J-book detail (Q20)
        {"fid": None, "value": None},                                    # an absent card
    ]
    report = compute_link_coverage(write_site(tmp_path, citations=CITATIONS, receipts=RECEIPTS,
                                              pages={"AAA": detail}))
    assert report["figures"] == {fid(1): "a", "nofid:AAA:summary_cards:1": "d"}
    assert report["site"]["summary_cards_cited_by_xml_path"] == 1
    assert absolute_violations(report)[0] == (
        "not source-linked: nofid:AAA:summary_cards:1 is (d) on /program/AAA/")


def test_a_derived_figure_whose_input_has_no_citation_is_d(tmp_path):
    citations = dict(CITATIONS, **{fid(20): derived(fid(1), fid(21))})   # fid(21) is cited nowhere
    report = compute_link_coverage(write_site(tmp_path, citations=citations, receipts=RECEIPTS,
                                              pages={"AAA": page(lines=[fid(20)])}))
    assert report["figures"] == {fid(20): "d"}


def test_non_string_derived_inputs_are_d_not_a_crash(tmp_path):
    citations = dict(CITATIONS, **{fid(22): {"kind": "derived", "inputs": [fid(1)],
                                             "formula": "x", "official_url": None}})
    report = compute_link_coverage(write_site(tmp_path, citations=citations, receipts=RECEIPTS,
                                              pages={"AAA": page(lines=[fid(22)])}))
    assert report["figures"] == {fid(22): "d"}


def test_cli_refuses_one_file_as_both_baseline_and_new_baseline(tmp_path, capsys):
    s0 = write_site(tmp_path / "s0", citations=CITATIONS, receipts=RECEIPTS,
                    pages={"AAA": page(lines=[fid(1), fid(2)])})
    target = tmp_path / "baseline.json"
    cli.main(["link-coverage", "--site-dir", str(s0), "--write-baseline", str(target)])
    before = target.read_bytes()
    capsys.readouterr()
    with pytest.raises(SystemExit) as exc:
        cli.main(["link-coverage", "--site-dir", str(s0), "--baseline", str(target),
                  "--write-baseline", str(target)])
    assert exc.value.code == 2
    assert capsys.readouterr().err.startswith(
        "link-coverage: ERROR — --baseline and --write-baseline both name")
    assert target.read_bytes() == before


def test_cli_compares_first_and_never_writes_a_failing_report_as_a_baseline(tmp_path, capsys):
    s0 = write_site(tmp_path / "s0", citations=CITATIONS, receipts=RECEIPTS,
                    pages={"AAA": page(lines=[fid(1), fid(2)])})
    old, new = tmp_path / "old.json", tmp_path / "new.json"
    cli.main(["link-coverage", "--site-dir", str(s0), "--write-baseline", str(old)])
    s4 = write_site(tmp_path / "s4", citations=CITATIONS,
                    receipts=dict(RECEIPTS, **{fid(1): receipt(False)}),
                    pages={"AAA": page(lines=[fid(1), fid(2)])})
    capsys.readouterr()
    with pytest.raises(SystemExit) as exc:
        cli.main(["link-coverage", "--site-dir", str(s4), "--baseline", str(old),
                  "--write-baseline", str(new)])
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert f"  - lost PDF receipt: {fid(1)} was (a) in the baseline, now (b)" in out
    assert f"link-coverage: baseline NOT written to {new} (the report has violations)" in out
    assert not new.exists()


def test_cli_tool_errors_exit_2_without_a_traceback(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["link-coverage", "--site-dir", str(tmp_path)])
    assert exc.value.code == 2
    assert capsys.readouterr().err.startswith(
        "link-coverage: ERROR — no program sidecars under")
    s0 = write_site(tmp_path / "s0", citations=CITATIONS, receipts=RECEIPTS,
                    pages={"AAA": page(lines=[fid(1)])})
    foreign = tmp_path / "foreign.json"
    foreign.write_text('{"schema_version": 9}')
    with pytest.raises(SystemExit) as exc:
        cli.main(["link-coverage", "--site-dir", str(s0), "--baseline", str(foreign)])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "unsupported link-coverage baseline schema: 9" in err and "Traceback" not in err
```

Run:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && uv run --project . pytest tests/test_link_coverage.py -q 2>&1 | tail -3
```

Expected: `6 failed, 11 passed`. The failures: the receipt-audit test (`[] == [...]`), the value-card test (the card is skipped: the figures dict lacks the `nofid:` key), the non-string test (`TypeError: the JSON object must be str, bytes or bytearray, not list`), the same-file test (no `SystemExit`: today the baseline is written, then compared with itself), the compare-first test (`new.json` exists), and the tool-error test (`FileNotFoundError` escapes). `test_a_derived_figure_whose_input_has_no_citation_is_d` passes already: it pins a case #200 found untested.

- [ ] **Step 2: Count an unsourced card as (d) and an XML-path card apart**

In `src/govbudget/link_coverage.py`, replace:

```python
    for card in (detail.get("summary") or {}).get("cards") or []:
        if card.get("fid"):
            out.append(("summary_cards", card["fid"]))
```

with:

```python
    for card in (detail.get("summary") or {}).get("cards") or []:
        if card.get("fid"):
            out.append(("summary_cards", card["fid"]))
        elif card.get("value") is not None and not card.get("xml_path"):
            # ROADMAP #200: a card that shows a value and names no source at
            # all is (d), never skipped. A card cited by XML path only (the
            # J-book detail cards) is counted apart by _xml_path_cards (Q20).
            out.append(("summary_cards", None))
```

Then replace:

```python
def _has_url(citation: dict, *keys: str) -> bool:
```

with:

```python
def _xml_path_cards(detail: dict) -> int:
    """Summary cards cited by an XML path only (no fid, a value, an
    xml_path): J-book detail figures, outside V9 and reported as their own
    count (follow-ups spec Q20; 440 on the 2026-10-04 export)."""
    return sum(
        1 for card in (detail.get("summary") or {}).get("cards") or []
        if not card.get("fid") and card.get("value") is not None and card.get("xml_path")
    )


def _has_url(citation: dict, *keys: str) -> bool:
```

- [ ] **Step 3: A malformed derived input is (d)**

Replace:

```python
        try:
            inputs = json.loads(citation.get("inputs") or "[]")
        except ValueError:
            return "d"
```

with:

```python
        try:
            inputs = json.loads(citation.get("inputs") or "[]")
        except (TypeError, ValueError):  # ROADMAP #200: a non-string `inputs` is (d), not a crash
            return "d"
```

- [ ] **Step 4: Report the XML-path cards**

In `compute_link_coverage`, replace:

```python
    figures: dict[str, str] = {}
    pages: dict[str, dict] = {}
    occurrences = {section: dict.fromkeys(CLASSES, 0) for section in SECTIONS}
    for path in detail_paths:
        slug = path.stem
        page: dict[str, str] = {}
        for index, (section, fid) in enumerate(_page_figures(json.loads(path.read_text()))):
```

with:

```python
    figures: dict[str, str] = {}
    pages: dict[str, dict] = {}
    occurrences = {section: dict.fromkeys(CLASSES, 0) for section in SECTIONS}
    xml_path_cards = 0
    for path in detail_paths:
        slug = path.stem
        page: dict[str, str] = {}
        detail = json.loads(path.read_text())
        xml_path_cards += _xml_path_cards(detail)
        for index, (section, fid) in enumerate(_page_figures(detail)):
```

and replace:

```python
        "workbooks_pinned": len(pinned),
        "export_built_at": built_at,
    })
```

with:

```python
        "workbooks_pinned": len(pinned),
        "export_built_at": built_at,
        "summary_cards_cited_by_xml_path": xml_path_cards,
    })
```

- [ ] **Step 5: Fail when the receipt audit the baseline relied on is gone**

In `compare_to_baseline`, replace:

```python
    violations.extend(absolute_violations(report))
    return violations
```

with:

```python
    if (baseline.get("site", {}).get("receipts_match_citations") is True
            and report["site"].get("receipts_match_citations") is None):
        # ROADMAP #200: absolute_violations reads None as "not audited" and
        # passes; against a baseline that WAS audited, a missing audit fails.
        violations.append(
            "receipt audit missing: the baseline recorded receipts_match_citations true, but"
            " json/budget_pdf_receipts_audit.json is absent from this site"
            " (re-run export-budget-pdf-receipts)"
        )
    violations.extend(absolute_violations(report))
    return violations
```

- [ ] **Step 6: Compare first, refuse one file for both, tool errors exit 2**

In `src/govbudget/cli.py`, replace the whole function `cmd_link_coverage` — from `def cmd_link_coverage(args) -> None:` through `    print("link-coverage: PASS")` (the line before `def cmd_verify_phase5b2(args) -> None:`) — with:

```python
def cmd_link_coverage(args) -> None:
    """Overview §7 / spec V9: link class of every budget figure on the program pages.

    Exit codes (one convention for the follow-ups' tools, ROADMAP #200): 0 PASS,
    1 FAIL (a violation), 2 a tool error — one stderr line `link-coverage:
    ERROR — <message>`, never a traceback (an unreadable site dir or baseline,
    a foreign baseline, or one file named as both --baseline and
    --write-baseline)."""
    try:
        _link_coverage(args)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001 — every tool error exits 2, without a traceback
        print(f"link-coverage: ERROR — {e}", file=sys.stderr)
        sys.exit(2)


def _link_coverage(args) -> None:
    import json

    from govbudget.link_coverage import (
        absolute_violations,
        baseline_from_report,
        compare_to_baseline,
        compute_link_coverage,
    )

    if (args.baseline is not None and args.write_baseline is not None
            and args.baseline.resolve() == args.write_baseline.resolve()):
        raise ValueError(
            f"--baseline and --write-baseline both name {args.baseline}; the comparison"
            " would read the file it just wrote (ROADMAP #200) — write the new baseline"
            " to another path"
        )

    def pct(share):
        return "n/a" if share is None else f"{100 * share:.2f}%"

    report = compute_link_coverage(args.site_dir)
    site = report["site"]
    print(
        f"link-coverage: {site['figures']:,} budget figures on {site['pages']:,} program pages:"
        f" a {site['a']:,} · b {site['b']:,} · c {site['c']:,} · d {site['d']:,};"
        f" source-linked {pct(site['source_linked'])},"
        f" PDF-highlighted {pct(site['pdf_highlighted'])};"
        f" {site['pages_fully_pdf_highlighted']:,} of {site['pages']:,} pages fully PDF-highlighted"
    )
    print(f"link-coverage: {site['summary_cards_cited_by_xml_path']:,} summary card(s) cited by"
          " XML path only, outside V9 (Q20)")
    # Compare FIRST (ROADMAP #200): the old order wrote the new baseline, then
    # read it back as the one to compare against.
    if args.baseline is not None:
        baseline = json.loads(args.baseline.read_text())
        violations = compare_to_baseline(report, baseline)
        print(f"link-coverage: compared against {args.baseline} ({len(baseline['figures']['a']):,} baseline (a) figures)")
    else:
        violations = absolute_violations(report)
    for line in violations[:50]:
        print(f"  - {line}")
    if len(violations) > 50:
        print(f"  ... and {len(violations) - 50:,} more")
    print(f"link-coverage: {len(violations):,} violation(s)")
    if args.write_baseline is not None:
        if violations:
            print(f"link-coverage: baseline NOT written to {args.write_baseline}"
                  " (the report has violations)")
        else:
            args.write_baseline.parent.mkdir(parents=True, exist_ok=True)
            text = json.dumps(baseline_from_report(report), indent=0, sort_keys=True) + "\n"
            args.write_baseline.write_text(text)
            print(f"link-coverage: baseline -> {args.write_baseline} ({len(text.encode()):,} bytes)")
    if violations:
        print("link-coverage: FAIL")
        sys.exit(1)
    print("link-coverage: PASS")
```

- [ ] **Step 7: Run the tests — they pass**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && uv run --project . pytest tests/test_link_coverage.py -q 2>&1 | tail -1
uvx --offline ruff check --isolated --select F,E9 src/govbudget/link_coverage.py | tail -1
uvx --offline ruff check --isolated --select F,E9 src/govbudget/cli.py | grep '^Found'
```

Expected: `17 passed`; `All checks passed!`; `Found 5 errors.` (the `cli.py` HEAD baseline; nothing new).

- [ ] **Step 8: Run it on the live export against the committed baseline (W6 shape)**

Read-only on the live `data/site`.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
uv run --project . python -m govbudget link-coverage --site-dir "$GOVBUDGET_DATA/site" --baseline data/research/link_coverage/baseline.json; echo "exit=$?"
```

Expected (the 2026-10-04 export; a later export changes the counts, never the verdict):

```
link-coverage: 61,645 budget figures on 2,562 program pages: a 60,983 · b 662 · c 0 · d 0; source-linked 100.00%, PDF-highlighted 98.93%; 2,415 of 2,562 pages fully PDF-highlighted
link-coverage: 440 summary card(s) cited by XML path only, outside V9 (Q20)
link-coverage: compared against data/research/link_coverage/baseline.json (44,747 baseline (a) figures)
link-coverage: 0 violation(s)
link-coverage: PASS
exit=0
```

The figure count is unchanged (61,645): no live card has a value with neither a fid nor an `xml_path`.

- [ ] **Step 9: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/link_coverage.py GovBudget/src/govbudget/cli.py GovBudget/tests/test_link_coverage.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "fix(link-coverage): fail closed on a missing receipt audit, unsourced cards and non-string inputs; compare before writing a baseline; tool errors exit 2 (#200)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `3 files changed`.
