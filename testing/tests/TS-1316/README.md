# TS-1316

Verifies that an archived issue disappears from the active JQL search path and
remains visible only through the archived JQL path.

The test uses a temporary Local Git-backed repository fixture, opens the
production TrackState widget shell, archives `TRACK-231` through the shared
mutation harness, and checks both JQL paths from the user view.

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-1316/test_ts_1316.dart --reporter expanded
```

## Required configuration

No external credentials or environment variables are required. The test creates
its own temporary repository fixture.

## Expected result when the test passes

```text
00:00 +1: All tests passed!
```
