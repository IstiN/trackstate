# TS-314

Validates the JQL Search parser and UI handling for nullable-field emptiness
checks from the user's perspective.

The automation:
1. launches the real `TrackStateApp` with a ticket-scoped repository fixture
2. opens `JQL Search` and runs `assignee IS EMPTY AND project = TRACK`
3. verifies only the unassigned issue is visible
4. runs `parent IS NOT EMPTY AND issueType = "Sub-task"` and verifies only the
   sub-task with a parent reference is visible
5. runs `epic IS EMPTY AND issueType = Story` and verifies only stories without
   an epic link are visible
6. runs `status IS EMPTY` and verifies the UI shows an explicit parser error

## Run this test

```bash
flutter test testing/tests/TS-314/test_ts_314.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required
- The test uses the local widget fixture provided by this repository

## Expected result

```text
Pass: nullable-field empty checks return the expected visible issue rows for
assignee, parent, and epic, and unsupported fields such as status surface an
explicit parsing error in the UI.

Fail: any nullable-field query returns the wrong visible rows, valid empty
checks are rejected, or an unsupported field is accepted without an explicit
error message.
```
