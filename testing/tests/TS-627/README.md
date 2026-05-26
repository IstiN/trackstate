# TS-627

Validates that the storage layer refuses a manually persisted non-canonical link
record when `links.json` tries to store `{"type":"blocks","direction":"inward"}`
directly on the source issue.

The automation covers the production-visible storage flow by:
1. seeding a clean Local Git-backed repository with source issue `DEMO-2` and
   target issue `DEMO-10`
2. calling the live Local Git provider write API directly for
   `DEMO/DEMO-1/DEMO-2/links.json`
3. attempting to persist the non-canonical payload
   `[{"type":"blocks","target":"DEMO-10","direction":"inward"}]`
4. verifying the storage response is a validation rejection and that repository
   readers still show no stored link and no extra commit

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-627/test_ts_627.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed repository fixture, so no
external credentials or environment variables are required.

## Expected passing output

```text
00:00 +1: All tests passed!
```
