# TS-189

Validates that the Local Git `Create issue` flow opened specifically from the
`JQL Search` top bar renders configured custom fields and persists them to the
generated `main.md` file.

The automation:
1. reuses the TS-141 Local Git fixture so the project field config declares
   `Solution`, `Acceptance Criteria`, and `Diagrams`
2. launches the real `TrackStateApp` in Local Git mode
3. opens `JQL Search` and verifies the top bar exposes a visible `Create issue`
   control
4. opens the create dialog from the `JQL Search` toolbar and verifies the custom
   fields are visibly rendered for the user
5. enters summary, description, and custom-field values, then clicks `Save`
6. verifies the dialog closes without a visible save failure and the new issue
   is reachable from the user-facing `JQL Search` flow
7. inspects `DEMO/DEMO-2/main.md` in the repository and requires it to contain
   all entered core and custom-field values

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-141/test_ts_141.dart testing/tests/TS-189/test_ts_189.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required
- The TS-141 Local Git fixture provides the configured custom fields used by
  this scenario

## Expected result

```text
Pass: the JQL Search top bar exposes a visible Create issue control, opening it
renders Solution, Acceptance Criteria, and Diagrams, saving succeeds, the new
issue is searchable in JQL Search, and DEMO/DEMO-2/main.md contains all entered
core and custom-field values.

Fail: the JQL Search top bar hides or cannot activate Create issue, any required
custom field is missing, saving shows a user-visible failure, the issue is not
searchable from JQL Search, or main.md omits one or more entered values.
```
