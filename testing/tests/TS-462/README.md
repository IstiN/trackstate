# TS-462

Reproduces the live CLI comment-creation flow against a disposable Local Git
repository and verifies that repeating the exact same comment command:

1. creates two separate markdown files under `TS/TS-1/comments/`,
2. returns the created comment metadata for each call, and
3. exposes a non-empty repository revision in each success envelope.

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-462 -p 'test_*.py' -v
```

## Required configuration

No Python packages are required beyond the standard library. The repository
under test must have a Dart SDK available on `PATH`, or `TRACKSTATE_DART_BIN`
must point to the Dart executable used to run `dart run trackstate`.

## Expected passing output

```text
test_duplicate_comment_posts_create_two_files_and_report_revisions (test_ts_462.TrackStateCliCommentCreationTest.test_duplicate_comment_posts_create_two_files_and_report_revisions) ... ok

----------------------------------------------------------------------
Ran 1 test in <time>

OK
```
