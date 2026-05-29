# TS-190

Validates that Local Git issue creation preserves YAML-sensitive custom-field
values in the generated `main.md` frontmatter.

The automation:
1. creates a clean Local Git repository fixture whose project config declares the
   `Solution` and `Answer` fields
2. launches the real `TrackStateApp` in Local Git mode
3. opens the production-visible `Create issue` flow and verifies those fields are
   visible to the user
4. enters a Summary plus YAML-sensitive custom-field values, then submits the form
5. verifies the create form closes without a visible save failure
6. verifies the new issue is visible from the user-facing search/detail flow
7. inspects `DEMO/DEMO-2/main.md` and requires the frontmatter custom-fields
   payload to remain decodable and to preserve the entered values exactly

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-190/test_ts_190.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: the Local Git Create issue form exposes Solution and Answer, accepts the
entered YAML-sensitive values, creates the issue successfully, and persists both
values exactly in DEMO/DEMO-2/main.md without corrupting the frontmatter payload.

Fail: one of the custom fields is not visible, submission surfaces an error, the
new issue is not visible in the UI, or the saved frontmatter cannot be decoded
back to the exact entered values.
```
