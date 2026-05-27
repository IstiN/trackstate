# TS-172

Validates that deleting `TRACK-777` updates only the tombstone-related files
and preserves an unrelated tracked file already present in
`TRACK/.trackstate/index/`.

The automation covers the ticket against a temporary local Git repository
fixture by:
1. seeding `TRACK/.trackstate/index/integrity_check.txt` with a known payload
2. deleting `TRACK-777` through the repository service
3. verifying the tombstone artifact and tombstone index are created
4. inspecting `.trackstate/index/` as a repository user would and confirming
   `integrity_check.txt` is still present with unchanged content

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-172/test_ts_172.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed TrackState repository
fixture, so no external credentials or environment variables are required.
