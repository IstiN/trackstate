# TS-748

Automates the JQL Search regression coverage for selected-row highlight styling
before and after a matching workspace sync refresh.

The test covers the production widget flow end to end:

1. launch the real `TrackStateApp`
2. open **JQL Search**, submit `status = Open`, and select `TRACK-742-B`
3. inspect the selected and unselected result rows for production-visible
   selection styling tokens
4. apply a background sync update that changes only Issue-B's description
5. trigger the production app-resume workspace sync refresh path
6. verify the same selection styling remains applied after refresh while the
   refreshed issue detail stays open

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-748/test_ts_748.dart -r expanded
```

## Required configuration

No external credentials are required. The test reuses the in-memory repository
fixture from `testing/tests/TS-742/support/`.
