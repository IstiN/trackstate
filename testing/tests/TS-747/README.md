# TS-747

Automates the JQL Search regression where a sync refresh must preserve
selection by stable issue identity even when another visible issue has the
same summary, status, and description.

The test covers the production widget flow end to end:

1. launch the real `TrackStateApp`
2. open **JQL Search**, submit `status = Open`, and verify two identical
   user-facing issue rows are visible
3. select `TRACK-747-A` and confirm its visible selected/highlight state and
   detail panel before refresh
4. trigger the production app-resume workspace sync refresh path after the
   repository recreates the same two issues with new instances in reversed order
5. verify the visible selection/highlight stays strictly on `TRACK-747-A`,
   `TRACK-747-B` stays unselected, and the detail panel remains on
   `TRACK-747-A`

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-747/test_ts_747.dart --reporter expanded
```

## Required configuration

No external credentials are required. The test uses an in-memory repository
fixture inside `testing/tests/TS-747/support/`.
