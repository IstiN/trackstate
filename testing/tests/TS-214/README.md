# TS-214

Validates that creating a new issue through the repository service leaves the
legacy `.trackstate/index/deleted.json` compatibility file untouched.

The automation covers the ticket in two repository-backed layers:
1. create a new issue in a temporary local Git repository, verify the new
   issue artifact and commit metadata, and compare the legacy
   `.trackstate/index/deleted.json` contents before vs after creation
2. reload the repository snapshot and search results the way an integrated
   client would, verifying the created issue is visible while the legacy
   deleted key remains hidden from active search

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-214/test_ts_214.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed TrackState repository
fixture, so no external credentials or environment variables are required.
