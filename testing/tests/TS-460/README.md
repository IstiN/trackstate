# TS-460

Validates that the CLI can update multiple ticket fields in one canonical
mutation request against a disposable Local Git repository.

The automation:

1. seeds `TS/TS-1/main.md` with an original summary, priority, assignee, and
   label,
2. runs the live `trackstate jira_update_ticket --target local --issueKey TS-1
   --json '{"fields":{...}}'` command through the repository checkout,
3. verifies the returned JSON success envelope reports one `update-fields`
   operation and the updated issue metadata,
4. checks `TS/TS-1/main.md` visibly shows the new summary, priority, assignee,
   and labels, and
5. confirms the repository history advanced by exactly one commit with a clean
   worktree.

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-460 -p 'test_*.py' -v
```

## Required configuration

No Python packages are required beyond the standard library. The repository
under test must have a Dart SDK available on `PATH`, or `TRACKSTATE_DART_BIN`
must point to the Dart executable used to run `dart run trackstate`.
