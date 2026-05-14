# TS-733

Automates the JQL Search regression where a background sync refresh removes the
currently selected issue from the active query results.

The test covers the production widget flow end to end:

1. launch the real `TrackStateApp`
2. open **JQL Search**, submit `status = Open`, and select Issue-B
3. apply a background sync update that changes Issue-B to **Closed**
4. trigger the production app-resume workspace sync refresh path
5. verify the visible query is still `status = Open`, Issue-B disappears from
   the visible results, Issue-A remains visible, and no issue detail stays
   selected

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-733/test_ts_733.dart -r expanded
```

## Required configuration

No external credentials are required. The test uses an in-memory repository
fixture inside `testing/tests/TS-733/support/`.
