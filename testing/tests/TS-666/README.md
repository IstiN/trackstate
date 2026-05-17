# TS-666

Validates that workspace profile creation rejects duplicates by target +
default branch, even when the requested `writeBranch` differs.

The automation:
1. seeds the production `SharedPreferencesWorkspaceProfileService` with an
   existing local workspace for `/user/projects/ts` on `main`
2. attempts to create `/user/projects/ts` on `main` with `writeBranch:
   feature-x`
3. verifies the duplicate attempt is rejected and does not add a second saved
   workspace for `main`
4. creates `/user/projects/ts` on `develop` and verifies the distinct default
   branch is still accepted

## Run this test

```bash
flutter test testing/tests/TS-666/test_ts_666.dart --reporter expanded
```
