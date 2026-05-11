# TS-309

Validates that audit history for `PROJECT-1` is derived from Git commits and
rendered as normalized business events without requiring an issue-local
`history.md` file.

The automation:
1. creates a disposable Local Git repository whose `PROJECT-1/main.md` history
   contains creation, description edit, and status transition commits
2. confirms `PROJECT/PROJECT-1/history.md` does not exist before any history is
   requested
3. loads history through the production repository API and verifies normalized
   entries expose `commitSha`, `timestamp`, `changeType`, `author`, and
   `summary`
4. verifies the observable payload an integrated client/UI would consume still
   contains the expected creation, description-update, and lifecycle-transition
   business events
5. confirms the repository stays clean and never creates or uses a
   `history.md` sidecar

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-309/test_ts_309.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: PROJECT-1 history is returned from Git-derived normalized events, the
client-visible payload shows creation, description update, and status transition
entries with author/timestamp metadata, and no history.md file exists before or
after inspection.

Fail: audit history is empty or missing one of the expected business events, an
entry omits the required metadata, the client-visible payload is incomplete, or
a history.md file is required/generated.
```
