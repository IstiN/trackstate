# TS-380

Verifies that `trackstate read fields` returns a flat JSON array of Jira-style
field objects for a seeded local repository.

The automation:

1. compiles a temporary `trackstate` executable from this checkout
2. seeds a temporary local repository with a project, issue type, statuses, and
   field definitions
3. runs the exact ticket command from that repository: `trackstate read fields`
4. checks that the stdout starts with a JSON array and that the parsed payload
   exposes Jira-style `summary` and custom field schema metadata without leaking
   TrackState-only config markers

## Install dependencies

No extra Python packages are required. Run the test from the repository root
with:

```bash
python3 -m unittest discover -s testing/tests/TS-380 -p 'test_*.py' -v
```

## Environment

- Python 3 standard library
- Dart SDK available on `PATH` or via `TRACKSTATE_DART_BIN`
- git CLI available on `PATH`

## Expected output

```text
test_read_fields_returns_flat_jira_style_field_objects (...) ... ok

----------------------------------------------------------------------
Ran 1 test in <time>s

OK
```
