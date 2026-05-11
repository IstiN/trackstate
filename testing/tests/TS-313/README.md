# TS-313

Validates that JQL Search treats canonical field names and quoted multi-word
values as exact comparisons from the user's perspective.

The automation:
1. launches the real `TrackStateApp` with a ticket-scoped repository fixture
2. opens `JQL Search` and runs `status = "In Progress" AND issueType = "Sub-task"`
3. verifies only the visible issue row whose stable key maps to the canonical
   `In Progress` status ID and `Sub-task` issue-type ID is returned
4. runs `status != Done AND project = TRACK`
5. verifies only the non-done `TRACK` issues remain visible and done or
   cross-project issues stay hidden

## Run this test

```bash
flutter test testing/tests/TS-313/test_ts_313.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required
- The test uses the local widget fixture provided by this repository

## Expected result

```text
Pass: quoted multi-word values for status and issueType are parsed as single
values, canonical field names are accepted, and the visible issue rows are
filtered by the configured IDs behind those labels.

Fail: quoted values are split incorrectly, canonical field names are rejected,
or the visible issue rows do not match the expected stable issue keys.
```
