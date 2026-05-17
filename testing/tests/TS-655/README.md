# TS-655

Validates that the storage layer accepts and persists a canonical
`{"type":"blocks","target":"DEMO-10","direction":"outward"}` link record when
it is written directly through the live Local Git storage API.

The automation covers the production-visible storage flow by:
1. seeding a clean Local Git-backed repository with source issue `DEMO-2` and
   target issue `DEMO-10`
2. calling the live Local Git provider write API directly for
   `DEMO/DEMO-1/DEMO-2/links.json`
3. persisting the canonical payload
   `[{"type":"blocks","target":"DEMO-10","direction":"outward"}]`
4. verifying the file contents, repository HEAD update, and reloaded issue state

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-655/test_ts_655.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed repository fixture, so no
external credentials or environment variables are required.

## Expected passing output

```text
00:00 +1: All tests passed!
```
