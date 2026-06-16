# TS-1287

Runs the live local CLI comment flow against a disposable Git repository and
verifies that each successful `ticket comment` write returns the exact Git HEAD
revision created by that write.

1. Seeds issue `TS-1`.
2. Posts `Regression test comment 1` and compares the returned `revision` with
   `git rev-parse HEAD`.
3. Posts `Regression test comment 2` and compares the returned `revision` with
   the new `git rev-parse HEAD`.
4. Confirms the visible CLI JSON output and saved markdown comments reflect what
   a user would observe after each command.

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-1287 -p 'test_*.py' -v
```

## Required configuration

No Python packages are required beyond the standard library. The repository
under test must have a Dart SDK available on `PATH`, or `TRACKSTATE_DART_BIN`
must point to the Dart executable used to run `dart run trackstate`.

## Expected passing output

```text
test_ticket_comment_success_envelope_reports_head_revision (test_ts_1287.TrackStateCliCommentRevisionEnvelopeTest.test_ticket_comment_success_envelope_reports_head_revision) ... ok

----------------------------------------------------------------------
Ran 1 test in <time>

OK
```
