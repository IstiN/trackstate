# TS-734

Validates that TrackState's hosted workspace sync refresh matrix updates only the
surfaces affected by each domain:

1. a comments-only sync keeps the Board and Hierarchy stable while refreshing
   only the selected Issue-C comments surface
2. a project metadata sync refreshes Dashboard counters and the Settings
   Attachments release-tag prefix

The test uses a mutable `ProviderBackedTrackStateRepository` fixture so the real
Flutter app can receive hosted sync refresh signals and render the resulting UI
changes through production view models.

## Run this test

```bash
flutter test testing/tests/TS-734/test_ts_734.dart --reporter expanded
```

## Expected result

```text
Pass: the comments-only refresh stays scoped to Issue-C comments without a
hosted snapshot reload, and the project metadata refresh updates Dashboard plus
Settings.

Fail: the comments-only refresh reloads the hosted snapshot, rehydrates
non-comments issue scopes, or the project metadata refresh does not update the
expected visible surfaces.
```
