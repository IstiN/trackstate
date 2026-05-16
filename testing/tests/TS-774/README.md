# TS-774

Validates the production-visible hosted workspace sync path for a
`projectMeta`-only refresh.

The scenario reuses the mutable hosted repository fixture from TS-734, but the
TS-774 refresh mutates only `project.json` so the run isolates project metadata
from repository-index and issue-summary domains before asserting the visible
Settings metadata refresh, Dashboard stability, and `load_snapshot_delta`
behavior.

## Run this test

```bash
flutter test testing/tests/TS-774/test_ts_774.dart --reporter expanded
```

## Expected result

```text
Pass: a projectMeta-only sync preserves the visible Dashboard counters for the
unchanged issue data, updates the Settings > Attachments release tag prefix,
and does not increment load_snapshot_delta.

Fail: the isolated projectMeta-only sync does not preserve the visible project
surfaces coherently or still increments the hosted snapshot reload counter.
```
