# TS-234

Validates that cancelling the top-bar issue creation flow discards draft input
and resets the form in Local Git mode.

The automation:
1. creates a temporary local Git repository fixture
2. launches the real `TrackStateApp` in Local Git mode
3. opens `Dashboard` and activates the top-bar create entry point
4. enters `Discarded Draft` in the visible `Summary` field
5. clicks `Cancel` and verifies the form closes
6. reopens the create flow and verifies `Summary` is empty
7. fails with UI snapshots when the create control, cancel action, or state reset
   behavior is missing

The ticket uses the shared `TrackStateAppComponent` abstraction and keeps all
logic under `testing/`.

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-234/test_ts_234.dart --reporter expanded
```

## Required configuration

This test creates its own temporary local Git-backed TrackState repository
fixture, so no external credentials or environment variables are required.

## Expected result

```text
Pass: clicking Cancel closes create issue and reopening shows an empty Summary
field (draft discarded).

Fail: the create form does not close on Cancel, cannot be reopened, or retains
previous Summary text.
```
