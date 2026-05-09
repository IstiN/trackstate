# TS-207

Validates that the Local Git `Create issue` form resets its visible field state
after a successful save so no values leak into the next create flow.

The automation:
1. creates a clean Local Git repository fixture whose project config declares the
   `Solution` and `Acceptance Criteria` custom fields
2. launches the real `TrackStateApp` in Local Git mode
3. opens `Create issue` from `JQL Search` and verifies the visible custom fields
   are present
4. enters `Summary = Issue 1` and `Solution = Static analysis fix`, then submits
   the form
5. verifies the save completes as a clean Local Git create operation by checking
   the new search result, saved `main.md`, new HEAD commit, expected commit
   subject, expected changed file set, and clean worktree
6. reopens `Create issue` from the same entry point and requires the visible
   `Summary`, `Description`, `Solution`, and `Acceptance Criteria` fields to be
   empty

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-207/test_ts_207.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: the Local Git Create issue form saves successfully from JQL Search,
creates exactly one dedicated git commit for DEMO-2, leaves the worktree clean,
and reopens with empty Summary, Description, Solution, and Acceptance Criteria
fields.

Fail: a required field is missing, save surfaces an error, the new issue is not
visible, git-side effects do not match a clean create operation, or reopening
the form shows stale values from the prior save.
```
