# TS-151

Validates that Local Git issue creation succeeds when the visible custom-field
inputs are left empty and that the generated `main.md` persists only the core
Summary and Description data without literal `null` or `undefined`
placeholders.

The automation:
1. creates a clean Local Git repository fixture whose project config declares
   the `Solution`, `Acceptance Criteria`, and `Diagrams` fields
2. launches the real `TrackStateApp` in Local Git mode
3. opens the production-visible `Create issue` flow and verifies those custom
   fields are visible to the user
4. enters only Summary and Description, leaving all custom-field inputs blank
5. submits the form and requires the create flow to close without a visible
   save failure
6. verifies the new issue is visible from the user-facing search/detail flow
7. inspects `DEMO/DEMO-2/main.md` in the repository and requires it to contain
   the entered Summary and Description without persisting `null` or
   `undefined`

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-151/test_ts_151.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: the Local Git Create issue form exposes Solution, Acceptance Criteria,
and Diagrams, allows them to remain empty, creates the issue successfully, and
persists the entered Summary and Description in DEMO/DEMO-2/main.md without
literal null/undefined placeholders.

Fail: any required create-form field is not visible, submission surfaces an
error, the new issue is not visible in the UI, or main.md omits core data or
contains literal null/undefined placeholders.
```
