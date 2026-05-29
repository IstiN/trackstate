# TS-42

## Install dependencies

```bash
flutter pub get
```

If the Flutter SDK is not already on your `PATH`, export it first:

```bash
export PATH="<flutter-sdk>/bin:$PATH"
```

## Run this test

```bash
flutter test testing/tests/TS-42/test_ts_42.dart
```

## Environment requirements

- No additional environment variables are required.
- The test uses an in-memory repository snapshot with `TRACK-1`, `TRACK-2`,
  and `TRACK-3`, then starts the real app against that data.

## Expected passing output

The test passes when booting the app with the initial route
`/issues/TRACK-3` renders the primary issue detail surface for `TRACK-3`
after loading completes. It should fail if startup falls back to another issue
or to the default dashboard/search experience instead of honoring the route
issue key.
