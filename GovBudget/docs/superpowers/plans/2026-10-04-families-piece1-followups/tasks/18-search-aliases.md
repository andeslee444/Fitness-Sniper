<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; the approved design is ../../../specs/2026-10-04-families-piece1-followups-design.md. -->

### Task 18: search aliases JASSM and C-130J route as #55 did; a cross-seed membership test (#197)

**Spec:** design §5.8 (#197: `data-seeds/search_aliases.csv` line 3 JASSM → `/program/0207325F/`, ref
`jbook:0207325F:ProgramElement[182]/Project[0]`; line 11 C-130J → `/program/0401132F/`, ref
`jbook:0401132F:ProgramElement[252]`; both carry the #55 note (2026-08-27); a new test beside
`tests/test_dossiers_research.py:546-583`: a search term whose alphanumeric key matches a `program_aliases` alias
targets a `pe_bli` in that alias's target set — membership, not equality, because 10 aliases have several targets —
failing today on exactly JASSM and C-130J; two URLs change in `search_quick.json`); §2.2 Q23 (owner: no check of
`site/src/lib/aliases.ts`; the families registry, piece 2, becomes the single source); §7 W1.

**Files:**
- Modify: `data-seeds/search_aliases.csv` (line 3, line 11)
- Modify: `tests/test_dossiers_research.py` (a constant after `ALIASES_CSV` :46; a test in `TestSearchAliasesCsv`
  before `test_jbook_source_refs_resolve` :576)

Line numbers are hints measured at `532205c9` (anchor on the quoted text).

**Interfaces:**
Consumes: `dbt/seeds/program_aliases.csv` (`alias, pe_bli, notes`; 53 distinct alphanumeric alias keys, 10 with
several targets; JASSM → 0207325F and C-130J → 0401132F since #55); the existing `TestSearchAliasesCsv` checks: every
`source_ref` starts `jbook:` or `lda:`; `test_jbook_source_refs_resolve` finds each `jbook:pe:xml_path` in
`data/site/data/jbook_narratives.parquet`; `test_targets_exist_in_dim_programs` finds each target in the live
`dim_programs` (both read live data through the worktree's `data/` links, hence the SAM guard in Step 4);
`export_site`'s search block, which emits each row as `{"id": "alias:<term>", "kind": "alias", "title": term,
"url": target_url}`.
Produces: `alias:jassm` → `/program/0207325F/` and `alias:c-130j` → `/program/0401132F/` in `json/search_quick.json`
at the release export (Task 21's P2 rule: `json/search_quick.json`, two alias URLs; Task 22's live check);
`load_alias_terms` (dossier matching) maps `jassm` → 0207325F and `c-130j` → 0401132F on its next run.

Verified now (read-only, 2026-10-13): `jbook_narratives.parquet` holds (0207325F, `ProgramElement[182]/Project[0]`),
a `mission` narrative that opens "The Joint Air-to-Surface Standoff Missile (JASSM) family of missiles includes…",
and (0401132F, `ProgramElement[252]`), a `mission` narrative that opens "The C-130J is a medium-sized transport
aircraft…"; `dim_programs` titles them "Joint Air-to-Surface Standoff Missile (JASSM)" and "C-130J Program"; both have
program pages (`json/program_details/0207325F.json`, `0401132F.json`); the live `search_quick.json` routes
`alias:jassm` to `/program/0603000D8Z/` and `alias:c-130j` to `/program/2012C130J/`. Of the 15 search terms, four share
a key with `program_aliases` (JADC2, JASSM, C2BMC, C-130J); JADC2 and C2BMC already agree.

- [ ] **Step 1: Write the failing test**

In `tests/test_dossiers_research.py` (:46), replace:

```python
ALIASES_CSV = REPO_ROOT / "data-seeds" / "search_aliases.csv"
```

with:

```python
ALIASES_CSV = REPO_ROOT / "data-seeds" / "search_aliases.csv"
PROGRAM_ALIASES_CSV = REPO_ROOT / "dbt" / "seeds" / "program_aliases.csv"
```

In `tests/test_dossiers_research.py` (class `TestSearchAliasesCsv`, :576), replace:

```python
    @pytest.mark.skipif(
        not NARRATIVES_PARQUET.exists(), reason="narratives sidecar not present"
    )
    def test_jbook_source_refs_resolve(self):
```

with:

```python
    def test_terms_shared_with_program_aliases_target_one_of_its_programs(self):
        """ROADMAP #197: #55 moved JASSM and C-130J in dbt/seeds/program_aliases.csv
        on 2026-08-27, and nothing tied this seed to that one, so search kept
        routing both to the old pages. A term whose alphanumeric key is also a
        program_aliases alias must target one of that alias's programs
        (membership, not equality: 10 aliases name several programs). The
        families registry (pieces 2-4) is meant to become the one source."""
        def key(text: str) -> str:
            return re.sub(r"[^0-9a-z]", "", text.lower())

        targets: dict[str, set[str]] = {}
        for row in _read_csv(PROGRAM_ALIASES_CSV):
            targets.setdefault(key(row["alias"]), set()).add(row["pe_bli"])
        checked, wrong = [], []
        for row in _read_csv(ALIASES_CSV):
            members = targets.get(key(row["term"]))
            if members is None:
                continue
            pe = re.fullmatch(r"/program/([^/]+)/", row["target_url"]).group(1)
            checked.append(row["term"])
            if pe not in members:
                wrong.append(f"{row['term']} -> {pe}, program_aliases says {sorted(members)}")
        assert checked == ["JADC2", "JASSM", "C2BMC", "C-130J"]
        assert wrong == []

    @pytest.mark.skipif(
        not NARRATIVES_PARQUET.exists(), reason="narratives sidecar not present"
    )
    def test_jbook_source_refs_resolve(self):
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_dossiers_research.py -k "test_terms_shared_with_program_aliases" -q`
Expected: `1 failed` — `assert wrong == []` with `JASSM -> 0603000D8Z, program_aliases says ['0207325F']` and
`C-130J -> 2012C130J, program_aliases says ['0401132F']` (scratch overlay of `532205c9`, 2026-10-13).

- [ ] **Step 3: Route both terms as #55 did**

In `data-seeds/search_aliases.csv` (line 3), replace:

```csv
JASSM,/program/0603000D8Z/,lda:a449d70c-6416-4828-bc38-6e3643aae6b1,"Joint Air-to-Surface Standoff Missile; named in the filing's activity description; PE is Joint Munitions Advanced Technology"
```

with:

```csv
JASSM,/program/0207325F/,jbook:0207325F:ProgramElement[182]/Project[0],"Joint Air-to-Surface Standoff Missile; the AF RDT&E PE carrying the acronym in its own title, whose project mission names the JASSM family (dbt/seeds/program_aliases.csv since #55, 2026-08-27). #197 CORRECTION (families piece-1 follow-ups, approved 2026-10-04): pointed at 0603000D8Z (Joint Munitions Advanced Technology) on an LDA filing's wording"
```

In `data-seeds/search_aliases.csv` (line 11), replace:

```csv
C-130J,/program/2012C130J/,lda:a449d70c-6416-4828-bc38-6e3643aae6b1,"C-130J named in the filing's activity description; SOCOM AC/MC-130J variants page"
```

with:

```csv
C-130J,/program/0401132F/,jbook:0401132F:ProgramElement[252],"Lockheed C-130J Hercules, the baseline airlifter; C-130J Program, the PE mission names the C-130J (dbt/seeds/program_aliases.csv since #55, 2026-08-27). #197 CORRECTION (families piece-1 follow-ups, approved 2026-10-04): pointed at 2012C130J (AC/MC-130J, the SOCOM gunship and special-operations variants)"
```

- [ ] **Step 4: Run the seed tests, including the two that read live data**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_dossiers_research.py -k "TestSearchAliasesCsv" -q
```
Expected: `5 passed` (shape, loader, the new membership test, the targets in the live `dim_programs`, the J-book refs in
`jbook_narratives.parquet`; the overlay without live data skipped the last two).

- [ ] **Step 5: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/data-seeds/search_aliases.csv GovBudget/tests/test_dossiers_research.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "fix(search): route JASSM and C-130J as #55 did; a shared term must target one of its program_aliases programs (#197)" -m "alias:jassm -> /program/0207325F/ (jbook:0207325F:ProgramElement[182]/Project[0]); alias:c-130j -> /program/0401132F/ (jbook:0401132F:ProgramElement[252]). The new test checks membership in the program_aliases target set for every shared term (JADC2, JASSM, C2BMC, C-130J)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
