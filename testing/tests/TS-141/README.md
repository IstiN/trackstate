# TS-141

Validates that Local Git issue creation persists create-form custom fields to the
generated `main.md` file.

The automation:
1. creates a clean Local Git repository fixture whose project config declares the
   `Solution`, `Acceptance Criteria`, and `Diagrams` fields
2. launches the real `TrackStateApp` in Local Git mode
3. opens the production-visible `Create issue` flow and verifies those fields are
   visible to the user
4. enters summary, description, and custom-field values, then submits the form
5. verifies the create form closes without a visible save failure
6. verifies the new issue is visible from the user-facing search/detail flow
7. inspects `DEMO/DEMO-2/main.md` in the repository and requires it to contain
   all entered values

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-141/test_ts_141.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: the Local Git Create issue form exposes Solution, Acceptance Criteria,
and Diagrams, accepts their entered values, creates the issue successfully, and
persists all entered content in DEMO/DEMO-2/main.md.

Fail: any required create-form field is not visible, submission surfaces an
error, the new issue is not visible in the UI, or main.md omits one or more
entered values.
```
