# TS-384

Verifies that the allowlisted `jira_execute_request` comment-list path returns a
raw Jira-compatible JSON payload instead of the TrackState success envelope.

The test preserves the legacy ticket command text:

```bash
trackstate jira_execute_request --method GET --path "rest/api/2/issue/TS-22/comment"
```

and executes the current equivalent `--request-path` form from a temporary
repository-local CLI binary against a seeded disposable Local Git repository.

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-384 -p 'test_*.py' -v
```

## Required configuration

No Python packages are required beyond the standard library. The repository
under test must have a Dart SDK available on `PATH`, or `TRACKSTATE_DART_BIN`
must point to the Dart executable used to compile the temporary TrackState CLI.
