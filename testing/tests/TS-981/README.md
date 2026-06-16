# TS-981

Verifies that retrying a saved `Local Unavailable` workspace reuses already
granted browser directory access instead of prompting again, then restores that
workspace as the active `Local Git` session.

The automation:
1. seeds a hosted active workspace plus a saved local workspace marked
   unavailable
2. launches the production tracker in the supported Flutter widget runtime at
   the ticket viewport of 1440x900
3. exposes the unavailable local row in the workspace switcher and confirms the
   row offers a retry-style action
4. taps the retry action while a browser-local repository loader is already able
   to reopen the saved folder
5. verifies the workspace becomes active as `Local Git` without calling the
   directory picker again

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-981/test_ts_981.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- Linux widget-test environment

## Expected result

```text
Pass: tapping Retry (or Re-authenticate) on the saved unavailable local
workspace restores that workspace immediately as the active Local Git session.
The browser directory picker is not called again because access is already
available for the saved directory.
```
