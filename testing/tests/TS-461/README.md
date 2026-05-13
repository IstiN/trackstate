# TS-461

Verifies that the CLI keeps permanent delete and archive as distinct lifecycle
operations for local TrackState repositories.

The automation:
1. seeds a disposable repository containing `TS-10` and `TS-11`
2. runs the exact ticket commands `trackstate jira_delete_ticket TS-10` and
   `trackstate archive TS-11` through a compiled repository-local CLI binary
3. checks the repository-visible filesystem state after each command
4. checks the terminal-visible JSON output to confirm delete creates tombstones
   while archive keeps the issue in place with `archived: true`

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-461 -p 'test_ts_461.py' -v
```

## Required configuration

No Python packages are required beyond the standard library. The repository
under test must have a Dart SDK available on `PATH`, or `TRACKSTATE_DART_BIN`
must point to the Dart executable used to compile the temporary TrackState CLI.

## Expected result

```text
Pass: `jira_delete_ticket` hard-deletes TS-10, writes tombstone artifacts, and
`archive` leaves TS-11 at `TS/TS-11/main.md` with `archived: true`.

Fail: the live CLI does not expose one or both requested lifecycle commands or
their repository-visible behavior differs from the ticket.
```
