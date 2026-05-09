# TS-150

Validates that Local Git issue creation dynamically renders a configuration-only
custom field in the production-visible `Create issue` form and persists the
entered value to the generated issue markdown.

The automation:
1. creates a clean Local Git repository fixture whose project config declares a
   unique `Verification Notes` field
2. launches the real `TrackStateApp` in Local Git mode
3. opens the production-visible `Create issue` flow and verifies the
   `Verification Notes` field is visible to the user
4. enters a summary and `Verification Notes` value, then submits the form
5. waits for the observable successful-save state where the create form closes
   without a visible save-failure banner
6. verifies the new issue is visible from the user-facing search/detail flow
7. inspects `DEMO/DEMO-2/main.md` in the repository and requires it to contain
   the entered summary and `Verification Notes` value

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-150/test_ts_150.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: the Local Git Create issue form exposes Verification Notes from
fields.json, accepts the entered value, creates the issue successfully, and
persists the entered content in DEMO/DEMO-2/main.md.

Fail: the Verification Notes field is not visible, submission surfaces a visible
save failure, the form never dismisses after save, the new issue is not visible
in the UI, or main.md omits the entered value.
```
