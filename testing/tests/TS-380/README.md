# TS-380 — TrackState CLI Read Fields Jira Schema

Functional test verifying that the `trackstate read fields` command returns a flat array of field objects with the Jira-standard schema.

## What is tested

1. A temporary TrackState repository is initialized.
2. The `trackstate read fields` command is executed.
3. The command exits with code 0 and returns valid JSON.
4. The JSON payload is a flat array of field objects.
5. Each field object contains the Jira-standard schema keys: `id`, `name`, `custom`, `orderable`, `navigable`, `searchable`, `clauseNames`, `schema`.
6. The `schema` sub-object contains `type` and `system` keys.

## Run this test

```bash
python testing/tests/TS-380/test_ts_380.py
```

## Required environment

- Dart SDK available on `PATH` (or set `TRACKSTATE_DART_BIN` to the dart executable).
- TrackState CLI source code in the repository root.

## Expected pass / fail behavior

- **Pass:** the command returns a valid JSON array of field objects matching the Jira schema.
- **Fail:** the command exits non-zero, returns non-JSON output, or the payload does not match the expected schema.
