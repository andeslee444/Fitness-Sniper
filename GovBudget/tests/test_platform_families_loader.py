"""platform_families loader (families piece 2; spec §7, §9)."""
from __future__ import annotations

import copy
import hashlib
import json

import pytest

from govbudget.jbooks import era_map
from govbudget.platform_families import (
    CAVEAT_IDS, CONTRACT_LINK_POLICIES, DEFAULT_PATHS, EDITIONS, ERA_LINE_COLUMNS, EXCLUSION_KINDS,
    EXHIBITS, FAMILY_KEYS, F15_SEED_RULING_ID, HISTORY_DATASET_RE, LINK_BASES, MEMBER_COLUMNS,
    MEMBER_ID_RE, PAYING_ORGS, PLATFORM_FAMILY_RE, PREFILL_COLUMNS, PURPOSES, REVIEW_COLUMNS,
    REVIEW_ROOT, ROLES, RULING_ID_RE, SEED_BASIS_ALLOWED, SERVICES, SHORT_NAME_RE, SOURCE_ID_RE,
    SOURCE_TIERS, STATUSES, TOP_KEYS, VARIANT_SCOPES, VERDICTS, EraLine, Headline, RegistryError,
    ReviewGuard, family_hash, load_registry, parse_ref, registry_texts, split_refs, write_registry)
from platform_family_fixtures import (DOC_SHA, ERA_XA, RULING_X1, World, XA, XC, XR, ruling, tmp_paths,
                                      write_world)

J, M, E = "platform_families.json", "platform_family_members.csv", "platform_family_era_lines.csv"
XA_ID = "x-1|P-1:3010F:AF:XA0001|2023-2026"
XR_ID = "x-1|R-1:3600F:AF:XR0001|2025-2026"
XC_ID = "x-1|P-1:3010F:AF:XC0001|2024-2026"
ERA_ID = "x-1|2023|3010F-AF-L7"


def refused(errors, file, row, fragment) -> bool:
    head = f"platform-families: {file}:{row}: " if row else f"platform-families: {file}: "
    return any(line.startswith(head) and fragment in line for line in errors)


def assert_refused(fn, file, row, fragment):
    with pytest.raises(RegistryError) as exc:
        fn()
    assert refused(exc.value.errors, file, row, fragment), "\n".join(exc.value.errors)


def test_constants_are_the_spec_values():
    assert len(MEMBER_COLUMNS) == 49 and len(set(MEMBER_COLUMNS)) == 49
    assert MEMBER_COLUMNS[:3] == ("member_row_id", "platform_family", "member_id")
    assert MEMBER_COLUMNS[44:] == ("allocation_years", "decided_by", "ruling_id", "decided_on", "note")
    assert ERA_LINE_COLUMNS == ("platform_family", "member_id", "edition", "era_key",
                                "budget_activity", "filed_title", "decision_id")
    assert REVIEW_COLUMNS == MEMBER_COLUMNS + ("reason", "headline_actuals_k")
    assert len(PREFILL_COLUMNS) == 43 and PREFILL_COLUMNS[-1] == "reason"
    assert not {"member_row_id", "titles_seen", "budget_activities", "drift_sha256", "decided_by",
                "ruling_id", "decided_on"} & set(PREFILL_COLUMNS)
    assert (ROLES, VERDICTS, EXHIBITS, STATUSES, SOURCE_TIERS) == (
        ("counted", "context", "project_slice", "excluded"), ("approved", "deferred", "rejected"),
        ("P-1", "R-1", "P-1R"), ("draft", "ratified", "published"), ("G", "PG", "C", "X"))
    assert (PURPOSES, VARIANT_SCOPES, LINK_BASES) == (
        ("buy", "upgrade", "develop", "support"), ("variant", "shared"),
        ("book_stated", "era_map", "inferred"))
    assert CONTRACT_LINK_POLICIES == ("production+AP", "modifications_only", "development", "none")
    assert SERVICES == ("USAF", "USN", "USMC", "USA", "USSF", "SOCOM", "DW")
    assert PAYING_ORGS == ("AF", "NAVY", "USMC", "ARMY", "USSF", "SOCOM", "DW")
    assert CAVEAT_IDS == ("classified", "construction", "operating_and_support", "spares",
                          "foreign", "cr_years", "nominal_dollars")
    assert EXCLUSION_KINDS == ("outside_scope", "not_a_budget_line", "shared_line")
    assert list(EDITIONS) == list(range(2017, 2027))
    assert SEED_BASIS_ALLOWED == frozenset({"R-DEC-FAM-F15-SEED"}) and F15_SEED_RULING_ID == "R-DEC-FAM-F15-SEED"
    assert [r.pattern for r in (PLATFORM_FAMILY_RE, SHORT_NAME_RE, HISTORY_DATASET_RE, RULING_ID_RE,
                                SOURCE_ID_RE, MEMBER_ID_RE)] == [
        r"^[a-z0-9]+(-[a-z0-9]+)*$", r"^[A-Za-z0-9][A-Za-z0-9 /-]*$", r"^[a-z0-9]+_funding_history$",
        r"^R-DEC-FAM-[A-Z0-9]+(-[A-Z0-9]+)+$", r"^[a-z0-9][a-z0-9-]*$",
        r"^(P-1|R-1|P-1R):[0-9]{4}[A-Z]+:[A-Z0-9]+:[A-Z0-9]+$"]
    assert TOP_KEYS == ("schema_version", "rulings", "sources", "families")
    assert FAMILY_KEYS[:3] == ("platform_family", "status", "published_ruling_id") and len(FAMILY_KEYS) == 20
    assert DEFAULT_PATHS.json.parts[-2:] == ("data-seeds", "platform_families.json")
    assert DEFAULT_PATHS.members.name == M and DEFAULT_PATHS.era_lines.name == E
    assert REVIEW_ROOT.parts[-3:] == ("data", "research", "platform_families")


def test_minimal_published_family_loads():
    w = World()
    reg = w.parse()
    assert reg.schema_version == 1 and reg.doc == w.doc and reg.doc is not w.doc
    assert [f.platform_family for f in reg.families] == ["x-1", "y-1"]
    assert [f.platform_family for f in reg.published()] == ["x-1"]
    x = reg["x-1"]
    assert [m.member_id for m in x.counted] == [XA, XR]
    assert [m.code for m in x.code_keyed] == ["XA0001", "XR0001"]
    assert [m.member_id for m in x.context] == [XC]
    assert (x.route, x.history_path) == ("/families/x-1/", "json/x1_funding_history.json")
    assert x.headline == Headline("cumulative_actuals", 2015, 2024)
    assert x.review_guard == ReviewGuard(("P-1", "R-1"), ("X-1",))
    assert x.era_lines == (EraLine("x-1", XA, 2023, "3010F-AF-L7", "05", "X-1", ERA_XA),)
    assert reg.rulings[RULING_X1].seed_basis is False and reg.sources["x-book"].tier == "G"
    xa = x.counted[0]
    assert (xa.valid_from_edition, xa.valid_to_edition, xa.member_order) == (2023, 2026, 1)
    assert xa.titles_seen == ((2024, "X-1"), (2025, "X-1"), (2026, "X-1"))
    assert xa.evidence == (f"era:{ERA_XA}", "src:x-book#p3")
    assert x.counted[1].evidence == (f"doc:{DOC_SHA}#p1;q=X-1 development",)
    assert x.counted[1].variant_ids == ("A", "B") and xa.quantity_bearing is None
    with pytest.raises(KeyError):
        reg["z-9"]


def test_draft_family_with_zero_rows_loads():
    y = World().parse()["y-1"]
    assert (y.status, y.published_ruling_id, y.members, y.era_lines, y.counted) == (
        "draft", None, (), (), ())


def test_member_and_era_line_as_row_round_trip():
    w = World()
    x = w.parse()["x-1"]
    assert sorted((m.as_row() for m in x.members), key=lambda r: r["member_row_id"]) == sorted(
        w.members, key=lambda r: r["member_row_id"])
    assert [e.as_row() for e in x.era_lines] == w.era_rows


def test_title_for_reads_titles_seen():
    xa = World().parse()["x-1"].counted[0]
    assert (xa.title_for(2025), xa.title_for(2023)) == ("X-1", None)


def _set(target, **kv):
    return lambda w: target(w).update(kv)


FAM = lambda w: w.family()
YFAM = lambda w: w.family("y-1")
RUL = lambda w: w.doc["rulings"][0]
SRC = lambda w: w.doc["sources"][0]
MXA = lambda w: w.member("XA0001")
MXR = lambda w: w.member("XR0001")
MXC = lambda w: w.member("XC0001")

STAGE1_ROW_RULES = [
    # (case id, mutation, file, row id, fragment)
    ("r1-schema-version", lambda w: w.doc.update(schema_version=2), J, None, "schema_version"),
    ("r1-schema-version-bool", lambda w: w.doc.update(schema_version=True), J, None, "schema_version"),
    ("r1-top-unknown", lambda w: w.doc.update(notes="x"), J, None, "notes"),
    ("r1-family-missing", lambda w: w.family().pop("headline"), J, "x-1", "headline"),
    ("r1-family-unknown", _set(FAM, colour="red"), J, "x-1", "colour"),
    ("r1-ruling-unknown", _set(RUL, extra=1), J, RULING_X1, "extra"),
    ("r1-source-unknown", _set(SRC, extra=1), J, "x-book", "extra"),
    ("r1-nested-unknown", lambda w: w.family()["headline"].update(window=1), J, "x-1", "window"),
    ("r1-type", _set(FAM, coverage_notes="one note"), J, "x-1", "coverage_notes"),
    ("r1-caveat", _set(FAM, caveat_ids=["weather"]), J, "x-1", "weather"),
    ("r1-exclusion-kind", lambda w: w.family()["exclusions"][0].update(kind="guess"), J, "x-1", "guess"),
    ("r1-exclusion-duplicate", lambda w: w.family()["exclusions"].append(
        copy.deepcopy(w.family()["exclusions"][0])), J, "x-1", "exclusion_id"),
    ("r1-on-partial-corpus", _set(FAM, on_partial_corpus="ignore"), J, "x-1", "on_partial_corpus"),
    ("r1-art-generated", _set(FAM, art={"src": "a.png", "alt": "a", "caption": "An X-1",
                                        "generated": True}), J, "x-1", "AI-generated"),
    ("r1-contract-basis", _set(FAM, contract_routes={"program_codes": ["999"],
        "description_pattern": "X-1", "description_exclusions": [], "basis": "vibes"}),
     J, "x-1", "basis"),
    ("r2-regex", _set(FAM, platform_family="X_1"), J, "X_1", "platform_family"),
    ("r2-duplicate", lambda w: w.doc["families"].append(copy.deepcopy(w.family("y-1"))),
     J, "y-1", "duplicate"),
    ("r3-regex", _set(FAM, short_name="X_1"), J, "x-1", "short_name"),
    ("r3-leading-hyphen", _set(FAM, short_name="-X1"), J, "x-1", "short_name"),
    ("r3-duplicate", _set(YFAM, short_name="X-1"), J, "y-1", "short_name"),
    ("r4-regex", _set(FAM, history_dataset="x1_history"), J, "x-1", "history_dataset"),
    ("r4-duplicate", _set(YFAM, history_dataset="x1_funding_history"), J, "y-1", "history_dataset"),
    ("r5-status", _set(FAM, status="public"), J, "x-1", "status"),
    ("r6-decided-by", _set(RUL, decided_by="controller"), J, RULING_X1, "decided_by"),
    ("r6-blank-reply", _set(RUL, owner_reply="  "), J, RULING_X1, "owner_reply"),
    ("r6-bad-date", _set(RUL, decided_on="2026-13-01"), J, RULING_X1, "decided_on"),
    ("r6-non-iso-date", _set(RUL, decided_on="21 Oct 2026"), J, RULING_X1, "decided_on"),
    ("r6-ruling-id", _set(RUL, ruling_id="R-DEC-X1"), J, "R-DEC-X1", "ruling_id"),
    ("r6-duplicate", lambda w: w.doc["rulings"].append(copy.deepcopy(w.doc["rulings"][0])),
     J, RULING_X1, "duplicate"),
    ("r6-kind", _set(RUL, kind="decree"), J, RULING_X1, "kind"),
    ("r6-seed-basis", _set(RUL, seed_basis=True), J, RULING_X1, "seed_basis"),
    ("r7-tier", _set(SRC, tier="Z"), J, "x-book", "tier"),
    ("r7-sha256", _set(SRC, sha256="abc"), J, "x-book", "sha256"),
    ("r7-archive-path", lambda w: w.doc["sources"][0].pop("archive_path"), J, "x-book", "archive_path"),
    ("r7-source-id", _set(SRC, source_id="X Book"), J, "X Book", "source_id"),
    ("r7-as-of", _set(SRC, as_of="April 2026"), J, "x-book", "as_of"),
    ("r7-duplicate", lambda w: w.doc["sources"].append(copy.deepcopy(w.doc["sources"][0])),
     J, "x-book", "duplicate"),
    ("r8-row-keys", lambda w: w.members[0].pop("note"), M, XA_ID, "columns"),
    ("r9-formula", _set(MXA, member_row_id="x-1|XA0001|2023-2026"), M, "x-1|XA0001|2023-2026",
     "member_row_id"),
    ("r9-duplicate", lambda w: w.members.append(dict(w.member("XC0001"))), M, XC_ID, "duplicate"),
    ("r10-regex", _set(MXA, member_id="P-2:3010F:AF:XA0001"), M, XA_ID, "member_id"),
    ("r10-disagrees", _set(MXA, code="XA0002"), M, XA_ID, "code"),
    ("r10-modern-org", _set(MXA, member_id="P-1:3010F:F:XA0001", organization="F",
                            member_row_id="x-1|P-1:3010F:F:XA0001|2023-2026"),
     M, "x-1|P-1:3010F:F:XA0001|2023-2026", "era spelling"),
    ("r11-role", _set(MXA, role="member"), M, XA_ID, "role"),
    ("r11-verdict", _set(MXA, verdict="maybe"), M, XA_ID, "verdict"),
    ("r11-appropriation", _set(MXA, appropriation="procure"), M, XA_ID, "appropriation"),
    ("r11-purpose", _set(MXA, purpose="make"), M, XA_ID, "purpose"),
    ("r11-purpose-blank-with-page", _set(MXA, purpose=""), M, XA_ID, "purpose"),
    ("r11-variant-scope", _set(MXA, variant_scope="both"), M, XA_ID, "variant_scope"),
    ("r11-link-basis", _set(MXA, link_basis="guess"), M, XA_ID, "link_basis"),
    ("r11-contract-link-policy", _set(MXA, contract_link_policy="all"), M, XA_ID,
     "contract_link_policy"),
    ("r11-boolean", _set(MXA, quantity_bearing="yes"), M, XA_ID, "quantity_bearing"),
    ("r11-service", _set(MXA, services_using="USAF;ARMY"), M, XA_ID, "ARMY"),
    ("r11-paying-org", _set(MXA, paying_org="USN"), M, XA_ID, "paying_org"),
    ("r11-p1r-not-context", _set(MXA, exhibit="P-1R", member_id="P-1R:3010F:AF:XA0001",
                                 member_row_id="x-1|P-1R:3010F:AF:XA0001|2023-2026"),
     M, "x-1|P-1R:3010F:AF:XA0001|2023-2026", "P-1R"),
    ("r11-empty-list-item", _set(MXR, variant_ids="A;;B"), M, XR_ID, "variant_ids"),
    ("r11-drift-format", _set(MXA, drift_sha256="XYZ"), M, XA_ID, "drift_sha256"),
    ("r12-before-2017", _set(MXA, valid_from_edition="2016"), M, XA_ID, "valid_from_edition"),
    ("r12-after-2026", _set(MXA, valid_to_edition="2027"), M, XA_ID, "valid_to_edition"),
    ("r12-not-integer", _set(MXA, valid_to_edition="20x6"), M, XA_ID, "valid_to_edition"),
    ("r12-from-after-to", _set(MXA, valid_from_edition="2026", valid_to_edition="2024",
                               member_row_id="x-1|P-1:3010F:AF:XA0001|2026-2024"),
     M, "x-1|P-1:3010F:AF:XA0001|2026-2024", "valid_from_edition"),
    ("r12-coverage-outside", _set(MXA, coverage_expected_from_edition="2022"), M, XA_ID,
     "coverage_expected_from_edition"),
    ("r12-expected-next", _set(MXA, expected_next_edition="2026"), M, XA_ID, "expected_next_edition"),
    ("r12-titles-outside", _set(MXA, titles_seen="2022: X-1; 2024: X-1"), M, XA_ID, "titles_seen"),
    ("r12-titles-order", _set(MXA, titles_seen="2025: X-1; 2024: X-1"), M, XA_ID, "titles_seen"),
    ("r12-titles-format", _set(MXA, titles_seen="X-1"), M, XA_ID, "titles_seen"),
    ("r17-slice-no-project", _set(MXC, role="project_slice", verdict="deferred"), M, XC_ID,
     "project_number"),
    ("r17-project-on-counted", _set(MXA, project_number="675365"), M, XA_ID, "project_number"),
    ("r17-shared-no-scope", _set(MXR, scope_note=""), M, XR_ID, "scope_note"),
    ("r17-context-no-scope", _set(MXC, scope_note=""), M, XC_ID, "scope_note"),
    ("r17-context-coverage", _set(MXC, coverage_expected_from_edition="2024"), M, XC_ID,
     "coverage_expected_from_edition"),
    ("r17-context-order", _set(MXC, member_order="3"), M, XC_ID, "member_order"),
    ("r17-allocation-off-context", _set(MXA, allocation_years="2024"), M, XA_ID, "allocation_years"),
    ("r17-quantity-off-counted", _set(MXC, quantity_bearing="true"), M, XC_ID, "quantity_bearing"),
    ("r18-variant", _set(MXA, variant_ids="C"), M, XA_ID, "variant_ids"),
    ("r18-program-tag", _set(MXA, program_tag="X-2"), M, XA_ID, "program_tag"),
    ("r18-purpose-tag", _set(MXA, purpose_tag="sdd"), M, XA_ID, "purpose_tag"),
    ("r26-empty", lambda w: w.family()["review_guard"].update(title_substrings=[]), J, "x-1",
     "title_substrings"),
    ("r26-lower-case", lambda w: w.family()["review_guard"].update(title_substrings=["x-1"]),
     J, "x-1", "title_substrings"),
    ("r26-exhibits", lambda w: w.family()["review_guard"].update(exhibits=["P-1R"]), J, "x-1",
     "exhibits"),
    ("r27-window", lambda w: w.family()["headline"].update(first_fy=2025), J, "x-1", "headline"),
    ("r27-measure", lambda w: w.family()["headline"].update(measure="total"), J, "x-1", "measure"),
]


@pytest.mark.parametrize("mutate,file,row,fragment",
                         [c[1:] for c in STAGE1_ROW_RULES], ids=[c[0] for c in STAGE1_ROW_RULES])
def test_stage_one_red_case(mutate, file, row, fragment):
    w = World()
    mutate(w)
    assert_refused(w.parse, file, row, fragment)


def test_stage_one_lists_every_error_at_once():
    w = World()
    w.family().update(short_name="X_1")
    w.member("XC0001").update(role="member")
    with pytest.raises(RegistryError) as exc:
        w.parse()
    assert refused(exc.value.errors, J, "x-1", "short_name")
    assert refused(exc.value.errors, M, XC_ID, "role")
    assert str(exc.value) == "\n".join(exc.value.errors)


@pytest.mark.parametrize("fault,fragment", [
    (lambda b: b"\xef\xbb\xbf" + b, "BOM"),
    (lambda b: b.replace(b"\n", b"\r\n"), "carriage return"),
    (lambda b: b + b"\n", "trailing blank line"),
], ids=["bom", "crlf", "trailing-blank-line"])
@pytest.mark.parametrize("which", ["json", "members", "era_lines"])
def test_bom_crlf_and_trailing_blank_line_are_refused_naming_the_file(tmp_path, fault, fragment, which):
    paths, seed = write_world(tmp_path, World())
    target = getattr(paths, which)
    target.write_bytes(fault(target.read_bytes()))
    assert_refused(lambda: load_registry(paths, era_decisions_path=seed), target.name, None, fragment)


def test_duplicate_json_keys_are_refused(tmp_path):
    paths, seed = write_world(tmp_path, World())
    text = paths.json.read_text(encoding="utf-8")
    paths.json.write_text(text.replace('"short_name": "X-1",', '"short_name": "X-1",\n      "short_name": "X-1",', 1),
                          encoding="utf-8")
    assert_refused(lambda: load_registry(paths, era_decisions_path=seed), J, None, "duplicate key 'short_name'")


def test_field_whitespace_is_not_stripped(tmp_path):
    w = World()
    w.member("XA0001").update(role=" counted")
    paths, seed = write_world(tmp_path, w)
    assert_refused(lambda: load_registry(paths, era_decisions_path=seed), M, XA_ID, "' counted'")


def test_unquoted_comma_shifts_columns_and_fails_the_header_count(tmp_path):
    paths, seed = write_world(tmp_path, World())
    text = paths.members.read_text(encoding="utf-8")
    paths.members.write_text(text.replace("A shared spares line; never summed.",
                                          "A shared spares line, never summed."), encoding="utf-8")
    assert_refused(lambda: load_registry(paths, era_decisions_path=seed), M, XC_ID,
                   "50 fields, the header has 49")


@pytest.mark.parametrize("which,columns", [("members", MEMBER_COLUMNS), ("era_lines", ERA_LINE_COLUMNS)])
def test_header_other_than_the_frozen_tuple_is_refused(tmp_path, which, columns):
    paths, seed = write_world(tmp_path, World())
    target = getattr(paths, which)
    lines = target.read_text(encoding="utf-8").split("\n")
    lines[0] = ",".join(reversed(columns))
    target.write_text("\n".join(lines), encoding="utf-8")
    assert_refused(lambda: load_registry(paths, era_decisions_path=seed), target.name, None, "header")


def test_missing_file_and_non_json_are_refused(tmp_path):
    paths, seed = write_world(tmp_path, World())
    paths.era_lines.unlink()
    assert_refused(lambda: load_registry(paths, era_decisions_path=seed), E, None, "missing")
    paths, seed = write_world(tmp_path / "b", World())
    paths.json.write_text("{\n", encoding="utf-8")
    assert_refused(lambda: load_registry(paths, era_decisions_path=seed), J, None, "JSON")


def test_write_registry_serializes_per_d11(tmp_path):
    w = World()
    w.doc["families"][0] = dict(reversed(list(w.family().items())))
    w.family().update(scope_note="X-1 – scope")
    paths = tmp_paths(tmp_path)
    write_registry(paths, doc=w.doc, members=list(reversed(w.members)), era_lines=w.era_rows)
    text = paths.json.read_text(encoding="utf-8")
    doc = json.loads(text)
    assert list(doc) == list(TOP_KEYS)
    assert list(doc["families"][0]) == [k for k in FAMILY_KEYS if k in w.family()]
    assert text.startswith('{\n  "schema_version": 1,\n') and "X-1 – scope" in text
    assert text.endswith("}\n") and not text.endswith("\n\n")
    members = paths.members.read_text(encoding="utf-8").split("\n")
    assert members[0] == ",".join(MEMBER_COLUMNS) and members[-1] == ""
    assert [line.split(",", 1)[0] for line in members[1:-1]] == [XA_ID, XC_ID, XR_ID]
    assert b"\r" not in paths.members.read_bytes() + paths.era_lines.read_bytes()


def test_registry_texts_are_what_write_registry_writes(tmp_path):
    w = World()
    paths = tmp_paths(tmp_path)
    texts = registry_texts(paths, doc=w.doc, members=w.members, era_lines=w.era_rows)
    write_registry(paths, doc=w.doc, members=w.members, era_lines=w.era_rows)
    assert set(texts) == {paths.json, paths.members, paths.era_lines}
    assert all(p.read_text(encoding="utf-8") == t for p, t in texts.items())


def test_write_registry_round_trips_byte_for_byte(tmp_path):
    paths, seed = write_world(tmp_path, World())
    reg = load_registry(paths, era_decisions_path=seed)
    again = tmp_paths(tmp_path / "again")
    write_registry(again, doc=reg.doc, members=[m.as_row() for f in reg.families for m in f.members],
                   era_lines=[e.as_row() for f in reg.families for e in f.era_lines])
    for name in ("json", "members", "era_lines"):
        assert getattr(again, name).read_bytes() == getattr(paths, name).read_bytes()


def test_write_registry_writes_nothing_when_a_replace_fails(tmp_path, monkeypatch):
    paths, _seed = write_world(tmp_path, World())
    before = {p.name: p.read_bytes() for p in paths.json.parent.iterdir()}

    def fail(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(era_map.os, "replace", fail)
    w = World()
    w.family().update(scope_note="changed")
    with pytest.raises(OSError, match="disk full"):
        write_registry(paths, doc=w.doc, members=w.members, era_lines=w.era_rows)
    assert {p.name: p.read_bytes() for p in paths.json.parent.iterdir()} == before


def _d10(fam, sources):
    text = json.dumps({"family": fam, "sources": sources}, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_family_hash_is_d10():
    w = World()
    assert family_hash(w.doc, "x-1") == _d10(w.family(), [w.doc["sources"][0]])
    assert family_hash(w.doc, "y-1") == _d10(w.family("y-1"), [])
    shuffled = copy.deepcopy(w.doc)
    shuffled["families"][0] = dict(reversed(list(w.family().items())))
    assert family_hash(shuffled, "x-1") == family_hash(w.doc, "x-1")
    changed = World()
    changed.family()["exclusions"][0]["size_text"] = "X-1 spares: $2.0M in FY2024"
    retiered = World()
    retiered.doc["sources"][0]["tier"] = "PG"
    assert family_hash(changed.doc, "x-1") != family_hash(w.doc, "x-1")
    assert family_hash(retiered.doc, "x-1") != family_hash(w.doc, "x-1")
    uncited = World()
    uncited.doc["sources"].append(dict(w.doc["sources"][0], source_id="uncited"))
    assert family_hash(uncited.doc, "x-1") == family_hash(w.doc, "x-1")


A64 = "a" * 64


def test_parse_ref_reads_every_prefix():
    assert parse_ref("era:F01500|3010F||2017-2023") == ("era", {"decision_id": "F01500|3010F||2017-2023"})
    assert parse_ref("fact:0026c924483c6624") == ("fact", {"fact_id": "0026c924483c6624"})
    assert parse_ref(f"doc:{A64}#p71;q=funded outside this exhibit") == (
        "doc", {"sha256": A64, "page": 71, "quote": "funded outside this exhibit"})
    assert parse_ref(f"doc:{A64}#p3") == ("doc", {"sha256": A64, "page": 3, "quote": None})
    assert parse_ref("src:msar-pb2027#p25") == ("src", {"source_id": "msar-pb2027", "page": 25})
    assert parse_ref("src:msar-pb2027") == ("src", {"source_id": "msar-pb2027", "page": None})
    assert parse_ref("ev:E-17") == ("ev", {"id": "E-17"})


@pytest.mark.parametrize("ref", [
    "", "web:x", "era:F01500", "fact:XYZ", "fact:0026c924483c662", "doc:abc#p1", f"doc:{A64}",
    f"doc:{A64}#p0", f"doc:{A64}#p1;q=", f"doc:{A64}#p1;q=a;b", "src:Msar", "src:msar#p", "ev:"])
def test_parse_ref_refuses_malformed(ref):
    with pytest.raises(ValueError):
        parse_ref(ref)


def test_split_refs_reattaches_quotes():
    assert split_refs(f"era:XA0001|3010F||2023-2023;doc:{A64}#p3;q=Lot 1 aircraft;src:x-book") == (
        "era:XA0001|3010F||2023-2023", f"doc:{A64}#p3;q=Lot 1 aircraft", "src:x-book")
    assert split_refs("") == ()
    with pytest.raises(ValueError):
        split_refs("q=orphan")


def test_doc_ref_quote_with_semicolon_is_refused():
    w = World()
    w.member("XR0001").update(evidence=f"doc:{DOC_SHA}#p1;q=X-1 development; continued")
    assert_refused(w.parse, M, XR_ID, "';'")


def _z1(w, **kv):
    """A ratified family z-1 counting XA0001 in 2024–2026 (the double-count hazard)."""
    w.add_family("z-1", status="ratified")
    return w.add_member("z-1", XA, 2024, 2026, role="counted", member_order="1",
                        titles_seen="2024: X-1; 2025: X-1; 2026: X-1", display_title="X-1",
                        drift_sha256="0" * 64, program_tag="Z-1", evidence="src:x-book#p3", **kv)


def test_one_member_counted_in_two_families_is_refused():
    w = World()
    _z1(w)
    assert_refused(w.parse, M, "z-1|P-1:3010F:AF:XA0001|2024-2026", "x-1")


def test_a_draft_carrying_published_ruling_id_is_refused():
    w = World()
    w.family("y-1")["published_ruling_id"] = RULING_X1
    assert_refused(w.parse, J, "y-1", "published_ruling_id")


def test_load_registry_resolves_era_refs_against_the_committed_era_seed(tmp_path):
    paths, seed = write_world(tmp_path, World())
    assert load_registry(paths, era_decisions_path=seed)["x-1"].counted[0].code == "XA0001"
    assert_refused(lambda: load_registry(paths), M, XA_ID, f"era:{ERA_XA}")   # not in the committed seed


def _c_source(w, **kv):
    entry = dict(w.doc["sources"][0], source_id="c-claim", tier="C", verified_by=[])
    entry.update(kv)
    w.doc["sources"].append(entry)
    w.member("XA0001").update(evidence=f"era:{ERA_XA};src:x-book#p3;src:c-claim")


def _deferred_xa(w):
    w.add_member("x-1", XA, 2026, 2026, role="counted", verdict="deferred")


def _org_split_context(w):
    w.add_member("x-1", "P-1:0300D:DTRA:20", 2024, 2026, role="context", scope_note="Shared.",
                 drift_sha256="0" * 64, evidence="era:20|0300D|DSS|2022-2022")


def _y1_ruling(w) -> str:
    w.doc["rulings"].append(ruling("R-DEC-FAM-Y1-B1", "y-1"))
    return "R-DEC-FAM-Y1-B1"


def _z1_era(w):
    w.add_family("z-1", status="ratified")
    w.add_member("z-1", "P-1:3010F:AF:XZ0001", 2023, 2026, role="counted", member_order="1",
                 display_title="Z", drift_sha256="0" * 64, program_tag="Z-1",
                 era_decision_ids="XZ0001|3010F||2023-2023", evidence="src:x-book#p3")
    w.era_rows.append(dict(w.era_rows[0], platform_family="z-1", member_id="P-1:3010F:AF:XZ0001",
                           decision_id="XZ0001|3010F||2023-2023"))


NOTE = {"note": "A note.", "note_fact_id": "0026c924483c6624",
        "expected_receipt": {"kind": "jbook_narrative", "page_number": 1, "pe_bli": "XA0001", "sha256": A64}}
ERA0 = lambda w: w.era_rows[0]

STAGE1_CROSS_RULES = [
    ("r5-published-no-ruling", lambda w: w.family().pop("published_ruling_id"), J, "x-1",
     "published_ruling_id"),
    ("r5-unknown-ruling", _set(FAM, published_ruling_id="R-DEC-FAM-X1-B9"), J, "x-1", "R-DEC-FAM-X1-B9"),
    ("r5-other-familys-ruling", lambda w: FAM(w).update(published_ruling_id=_y1_ruling(w)), J, "x-1", "y-1"),
    ("r7-x-cited-by-row", _set(SRC, tier="X"), M, XA_ID, "tier X"),
    ("r7-x-cited-by-exclusion", lambda w: (SRC(w).update(tier="X"), MXA(w).update(
        evidence=f"doc:{DOC_SHA}#p1"), MXC(w).update(evidence="")), J, "x-1", "tier X"),
    ("r7-c-unverified", _c_source, M, XA_ID, "verified_by"),
    ("r7-c-verified-by-c", lambda w: _c_source(w, verified_by=["c-claim"]), M, XA_ID, "verified_by"),
    ("r13-overlap", _deferred_xa, M, "x-1|P-1:3010F:AF:XA0001|2026-2026", "overlap"),
    ("r15-shared-code", lambda w: w.add_member(
        "x-1", "R-1:3600F:AF:XA0001", 2025, 2026, role="counted", member_order="3", display_title="X",
        drift_sha256="0" * 64, program_tag="X-1", evidence="src:x-book#p3"),
     M, "x-1|R-1:3600F:AF:XA0001|2025-2026", "code"),
    ("r16-gap", _set(MXR, member_order="3"), M, XR_ID, "member_order"),
    ("r16-on-deferred", lambda w: (_deferred_xa(w), w.members[-1].update(member_order="3")),
     M, "x-1|P-1:3010F:AF:XA0001|2026-2026", "member_order"),
    ("r19-unknown-predecessor", _set(MXR, predecessor_member_id="P-1:3010F:AF:QQ0001",
                                     link_basis="inferred"), M, XR_ID, "predecessor_member_id"),
    ("r19-no-basis", _set(MXR, predecessor_member_id=XA), M, XR_ID, "link_basis"),
    ("r19-book-stated-no-quote", _set(MXR, predecessor_member_id=XA, link_basis="book_stated",
                                      link_evidence="src:x-book#p3"), M, XR_ID, "book_stated"),
    ("r20-malformed", _set(MXA, evidence="web:x"), M, XA_ID, "web:x"),
    ("r20-malformed-exclusion", lambda w: w.family()["exclusions"][0].update(evidence=["web:x"]),
     J, "x-1", "web:x"),
    ("r20-era-unresolved", _set(MXA, evidence="era:XQ0001|3010F||2023-2023;src:x-book#p3"),
     M, XA_ID, "XQ0001"),
    ("r20-era-other-code", _set(MXA, evidence="era:XB0001|3010F||2023-2023;src:x-book#p3"),
     M, XA_ID, "XB0001"),
    ("r20-era-excluded", _set(MXA, evidence="era:XA0001|3010F||2017-2022;src:x-book#p3"),
     M, XA_ID, "exclude_placeholder"),
    ("r20-era-org-split", _org_split_context, M, "x-1|P-1:0300D:DTRA:20|2024-2026", "organization"),
    ("r20-src-unknown", _set(MXA, evidence=f"era:{ERA_XA};src:nope"), M, XA_ID, "nope"),
    ("r20-no-independent-signal", _set(MXA, evidence=f"era:{ERA_XA}"), M, XA_ID, "independent"),
    ("r20-fact-is-not-enough", _set(MXA, evidence=f"era:{ERA_XA};fact:0026c924483c6624"),
     M, XA_ID, "independent"),
    ("r21-unresolved", _set(MXA, era_decision_ids="XQ0001|3010F||2023-2023"), M, XA_ID,
     "era_decision_ids"),
    ("r21-other-code", _set(MXA, era_decision_ids="XB0001|3010F||2023-2023"), M, XA_ID, "XB0001"),
    ("r22-decided-by", _set(MXA, decided_by=""), M, XA_ID, "decided_by"),
    ("r22-unknown-ruling", _set(MXA, ruling_id="R-DEC-FAM-X1-B9"), M, XA_ID, "R-DEC-FAM-X1-B9"),
    ("r22-other-familys-ruling", lambda w: MXA(w).update(ruling_id=_y1_ruling(w)), M, XA_ID, "y-1"),
    ("r22-decided-on", _set(MXA, decided_on="2026-10-20"), M, XA_ID, "decided_on"),
    ("r23-row-without-family", _set(MXC, platform_family="q-1", member_row_id="q-1|P-1:3010F:AF:XC0001|2024-2026"),
     M, "q-1|P-1:3010F:AF:XC0001|2024-2026", "q-1"),
    ("r23-ratified-without-rows", _set(YFAM, status="ratified"), J, "y-1", "no member rows"),
    ("r24-key-not-counted", _set(FAM, program_notes={XC: NOTE}), J, "x-1", "program_notes"),
    ("r24-empty-note", _set(FAM, program_notes={XA: dict(NOTE, note="")}), J, "x-1", "note"),
    ("r24-fact-id", _set(FAM, program_notes={XA: dict(NOTE, note_fact_id="XYZ")}), J, "x-1", "note_fact_id"),
    ("r24-receipt-keys", _set(FAM, program_notes={XA: dict(NOTE, expected_receipt={
        "kind": "jbook_narrative", "page_number": 1, "sha256": A64})}), J, "x-1", "expected_receipt"),
    ("r25-not-counted", _set(ERA0, member_id=XC), E, ERA_ID, "approved counted"),
    ("r25-edition-outside", _set(ERA0, edition="2022"), E, "x-1|2022|3010F-AF-L7", "edition"),
    ("r25-key-regex", _set(ERA0, era_key="3010F-AF-7"), E, "x-1|2023|3010F-AF-7", "era_key"),
    ("r25-key-account", _set(ERA0, era_key="3011F-AF-L7"), E, "x-1|2023|3011F-AF-L7", "account"),
    ("r25-key-org", _set(ERA0, era_key="3010F-NAVY-L7"), E, "x-1|2023|3010F-NAVY-L7", "organization"),
    ("r25-decision", _set(ERA0, decision_id="XB0001|3010F||2023-2023"), E, ERA_ID, "decision_id"),
    ("r25-duplicate", lambda w: w.era_rows.append(dict(w.era_rows[0])), E, ERA_ID, "duplicate"),
    ("r25-two-families", _z1_era, E, "z-1|2023|3010F-AF-L7", "x-1"),
]


@pytest.mark.parametrize("mutate,file,row,fragment",
                         [c[1:] for c in STAGE1_CROSS_RULES], ids=[c[0] for c in STAGE1_CROSS_RULES])
def test_stage_one_cross_red_case(mutate, file, row, fragment):
    w = World()
    mutate(w)
    assert_refused(w.parse, file, row, fragment)


def test_a_c_source_verified_by_a_g_source_may_be_cited():
    w = World()
    _c_source(w, verified_by=["x-book"])
    assert w.parse()["x-1"].counted[0].evidence[-1] == "src:c-claim"


def test_a_seed_basis_ruling_stands_without_an_independent_signal():
    w = World()
    w.doc["rulings"][0].update(ruling_id="R-DEC-FAM-F15-SEED", seed_basis=True)
    w.family()["published_ruling_id"] = "R-DEC-FAM-F15-SEED"
    for row in w.members:
        row["ruling_id"] = "R-DEC-FAM-F15-SEED"
    w.member("XA0001").update(evidence=f"era:{ERA_XA}")
    w.member("XR0001").update(evidence="fact:0026c924483c6624")
    assert [m.code for m in w.parse()["x-1"].counted] == ["XA0001", "XR0001"]
