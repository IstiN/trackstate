# TS-703

Validates that hosted workspace onboarding supports both authenticated
repository discovery and manual `owner/repo` fallback entry with a free-text
branch field.

The automation:
1. seeds an existing active hosted workspace with a stored GitHub token
2. opens the Add workspace flow and switches to `Hosted repository`
3. verifies the accessible repository list and manual fallback helper text are
   visible for an authenticated session
4. selects a visible repository suggestion and verifies the repository plus
   `Branch: ...` identity details are shown to the user
5. overwrites the form with manual `owner/repo` and custom branch values,
   submits `Open`, and verifies the production workspace state uses those exact
   details

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-703/test_ts_703.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: authenticated users see accessible repository suggestions and the manual
owner/repo fallback, the branch field accepts free-text input, and opening the
workspace uses the exact manual repository and branch values.

Fail: the accessible repository list is missing for an authenticated session,
manual owner/repo fallback is unavailable, the branch field does not retain a
custom value, or the saved workspace does not use the entered repository and
branch.
```
