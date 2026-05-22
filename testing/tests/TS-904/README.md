# TS-904

Automates the JQL Search regression where a background sync removes a
non-selected issue while the currently selected issue still remains valid.

The test covers the production widget flow end to end:

1. launch the real `TrackStateApp`
2. open **JQL Search**, submit `status = Open`, and select `TRACK-904-A`
3. apply a background sync update that removes `TRACK-904-B`
4. trigger the production app-resume workspace sync refresh path
5. verify `TRACK-904-A` stays selected with its detail panel visible,
   `TRACK-904-B` disappears from the results, and no
   `no longer available` notification is shown

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-904/test_ts_904.dart --reporter expanded
```

## Required configuration

No external credentials are required. The test uses an in-memory repository
fixture inside `testing/tests/TS-904/support/`.
