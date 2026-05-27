# TS-386

Validates that the live TrackState CLI help keeps attachment upload and
download discoverable from the root help output and that the Jira-compatible
upload alias resolves to the same visible option-based help as the canonical
upload command.

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-386 -p 'test_*.py' -v
```

## Required configuration

No Python packages are required beyond the standard library. The repository
under test must have a Dart SDK available on `PATH`, or `TRACKSTATE_DART_BIN`
must point to the Dart executable used to run `dart run trackstate`.

## Expected passing output

```text
test_attachment_help_and_jira_alias_are_discoverable (test_ts_386.TrackStateCliAttachmentDiscoveryTest.test_attachment_help_and_jira_alias_are_discoverable) ... ok

----------------------------------------------------------------------
Ran 1 test in <time>

OK
```
