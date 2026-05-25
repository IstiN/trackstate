## Bug Fix Summary

### Root Cause
`read account-by-email` was still wired as a live read operation in `lib/cli/trackstate_cli.dart`, so the CLI resolved the target and then attempted repository/provider access before it ever had a chance to return an unsupported-operation contract. In the ticket scenario that surfaced as `REPOSITORY_OPEN_FAILED` with exit code `4`, and the exact positional command would also have missed the parser's `--email` option path instead of returning the documented unsupported response.

### Fix
Added an early `account-by-email` guard in `lib/cli/trackstate_cli.dart` that returns a structured `UNSUPPORTED_ACCOUNT_BY_EMAIL` error with category `unsupported` and exit code `5` before any repository, auth, or provider lookup runs. Updated the read help text to describe the command as a reserved compatibility surface that currently returns an explicit unsupported error, and replaced the stale CLI success tests with unsupported-contract regression coverage in `test/trackstate_cli_test.dart`.

For the `quality_gate_flutter-analyze` follow-up, I also removed a stale optional `usersByEmail` parameter from the `_FakeHostedTrackStateProvider` test helper in `test/trackstate_cli_test.dart`. The ticket refactor no longer instantiates that helper with email fixtures, so the unused optional constructor parameter triggered the analyzer warning that failed the gate.

For the `development_git_operations` follow-up, I merged the latest `origin/main` into this branch and resolved the overlap in `test/trackstate_cli_test.dart` without dropping either side's work. The final merged state keeps the TS-1077 unsupported `account-by-email` coverage, keeps the upstream `ticket get TRACK-1` shorthand coverage, and preserves the newer hosted LFS attachment test helper support (`lfsTrackedPaths`) while still removing the stale unused `usersByEmail` constructor parameter that had caused the analyzer warning.

### Test Coverage
- Reproduction test added: `test/trackstate_cli_test.dart` — `reports account-by-email as unsupported for the exact ticket command`
- Additional regression test: `test/trackstate_cli_test.dart` — `reports account-by-email as unsupported for hosted targets too`
- Linked test: `testing/tests/TS-378/test_ts_378.py` — `test_cli_reports_account_by_email_as_explicitly_unsupported`
- Full test suite: `flutter test` — PASSED (`504 tests passed`)
- `flutter analyze` — PASSED
- Ticket regression rerun: `flutter test test/trackstate_cli_test.dart --plain-name "reports account-by-email as unsupported for the exact ticket command"` — PASSED
- Merge-resolution validation: `flutter test test/trackstate_cli_test.dart` — PASSED (`46 tests passed`)
- Merge-resolution validation: `python -m unittest testing.tests.TS-378.test_ts_378` — PASSED

### Notes
The exact user-facing command `dart run trackstate read account-by-email user@example.com` now returns the expected JSON unsupported envelope with exit code `5` and does not depend on repository HEAD or provider state.
