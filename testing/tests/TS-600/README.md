# TS-600

Validates that `IssueMutationService.updateFields` normalizes provider-backed
filesystem failures into a typed `provider-failure` result instead of leaking raw
implementation exceptions.

The automation:
1. seeds a clean Local Git-backed repository with active issue `TRACK-122`
2. inserts a filesystem blocker that makes the generated
   `TRACK/.trackstate/index/issues.json` write fail inside the real local provider
3. calls `IssueMutationService.updateFields` for that issue
4. verifies the returned `IssueMutationResult` stays failed with the
   machine-readable `providerFailure` category and a safe, user-visible message
5. re-reads the repository snapshot to confirm callers still see the last
   committed issue state instead of a partial save

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-600/test_ts_600.dart --reporter expanded
```

## Required environment / config

- Flutter SDK available on `PATH`
- No external credentials or environment variables are required
- The test creates and disposes its own temporary Local Git-backed repository

## Expected result

```text
Pass: updateFields returns a failed typed result with category provider-failure,
the message remains safe for callers, and repository readers still see the last
committed issue state.

Fail: updateFields throws instead of returning a typed result, reports the wrong
category, leaks raw filesystem exception details, or leaves callers observing the
partially edited issue as the committed state.
```
