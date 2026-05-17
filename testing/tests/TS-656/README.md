# TS-656

Validates that a mixed `links.json` payload is rejected atomically when one
record is valid and another record is a non-canonical standardized link with
`{"type":"blocks","direction":"inward"}`.

The automation covers the production-visible storage flow by:
1. seeding a clean Local Git-backed repository with source issue `DEMO-2` and
   target issue `DEMO-10`
2. preparing a mixed payload with one canonical outward `blocks` record and one
   non-canonical inward `blocks` record
3. calling the live Local Git provider write API directly for
   `DEMO/DEMO-1/DEMO-2/links.json`
4. verifying the storage response is a validation rejection and that no part of
   the mixed payload is persisted to repository state

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-656/test_ts_656.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed repository fixture, so no
external credentials or environment variables are required.

## Expected passing output

```text
00:00 +1: All tests passed!
```
