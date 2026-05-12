# TS-375 test automation

Verifies that `trackstate read ticket --key TS-20` returns a single raw
Jira-shaped issue object at the JSON root instead of a TrackState success
envelope.

The automation:
1. compiles a temporary repository-local `trackstate` executable from this checkout
2. seeds a disposable Local Git TrackState repository with issue `TS-20`
3. runs the canonical `trackstate read ticket --key TS-20` command
4. checks the parsed JSON root exposes `id`, `key`, and `fields` directly
5. checks terminal-visible output for the seeded issue data and confirms wrapper
   keys such as `ok`, `schemaVersion`, and `data` are absent

## Install dependencies

No additional Python packages are required beyond the standard library.

Ensure these tools are available before running the test:
- Python 3
- git
- Dart SDK on `PATH`, or `TRACKSTATE_DART_BIN` set to the Dart executable

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-375 -p 'test_ts_375.py' -v
```

## Required environment and config

- The repository under test must be this TrackState checkout.
- `TRACKSTATE_DART_BIN` is optional when `dart` is already on `PATH`.

## Expected result

```text
test_read_ticket_returns_a_raw_jira_issue_object ... ok

Pass: the CLI prints a raw Jira issue object rooted at `id`, `key`, and
`fields`, and the output does not contain TrackState envelope keys such as
`ok`, `schemaVersion`, or `data`.

Fail: the CLI wraps the response in a TrackState envelope, omits required Jira
issue fields, or does not preserve the seeded TS-20 issue data.
```
