# /years/ split fixtures (ROADMAP #193)

Each directory holds one `_emit_years_matrix` fixture payload from
`tests/test_export_years_matrix.py` (`payload.json`, indented for reading) and
the three files `split_years_matrix` makes of it, byte for byte as the exporter
writes them (compact, so their bytes and sha256 match the core's manifest):

- `basic/` (`_split_fixture_payload`): native and era decade grains, project
  rows and a family badge; `fy2019r` is the one lazy decade column.
- `split_keys/` (`_emit_split_keys`): the organization-split code `20`
  (rows `20-DCSA`, `20-DTRA`) and the account-split code `0145`.

Three tests read them:

- `tests/test_export_years_matrix.py::TestCrossLanguageFixture` fails when the
  files no longer match the Python split;
- `site/src/__tests__/years-matrix-shards.test.ts` checks that the JS merge
  (`mergeYearsMatrix`, which the /years/ island runs) turns them back into
  `payload.json`;
- `site/scripts/gates/__tests__/years-matrix-gate.test.mjs` loads them through
  the yearsmatrix gate's loader.

After a deliberate change to the split, regenerate both directories from
`GovBudget/`:

```bash
uv run --project . python - <<'PY'
import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, "tests")
import test_export_years_matrix as t
from govbudget.export_site import _canonical_json_bytes, split_years_matrix
for name, build in t.SPLIT_FIXTURES.items():
    out = t.SPLIT_FIXTURE_DIR / name
    (out / "years_matrix").mkdir(parents=True, exist_ok=True)
    payload = build(Path(tempfile.mkdtemp()))
    (out / "payload.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    for rel, obj in split_years_matrix(payload).items():
        (out / rel).write_bytes(_canonical_json_bytes(obj))
PY
```
