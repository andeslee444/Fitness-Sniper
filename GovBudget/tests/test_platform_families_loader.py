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
    ReviewGuard, family_hash, load_registry, registry_texts, write_registry)
from platform_family_fixtures import (DOC_SHA, ERA_XA, RULING_X1, World, XA, XC, XR, tmp_paths,
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
