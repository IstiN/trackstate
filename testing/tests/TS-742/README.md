# TS-742

Automates the JQL Search regression where a workspace sync refresh updates a
selected issue that still matches the active query.

The test covers the production widget flow end to end:

1. launch the real `TrackStateApp`
2. open **JQL Search**, submit `status = Open`, and select `TRACK-742-B`
3. apply a background sync update that changes only Issue-B's description
4. trigger the production app-resume workspace sync refresh path
5. verify the query stays populated, both Open rows remain visible, the detail
   panel refreshes, and the selected result row still exposes a
   production-visible selected/highlight state

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-742/test_ts_742.dart -r expanded
```

## Required configuration

No external credentials are required. The test uses an in-memory repository
fixture inside `testing/tests/TS-742/support/`.
