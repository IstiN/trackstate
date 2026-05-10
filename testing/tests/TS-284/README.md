# TS-284

Validates that creating a link with the inverse label `is blocked by` persists
exactly one canonical `blocks` relationship record in `links.json` and exposes
the same normalized relationship after a repository reload.

The automation covers the ticket from the shared testing-component layer
against a temporary local Git-backed TrackState repository:
1. seed a clean repository containing source issue `DEMO-2` and target issue
   `DEMO-10`
2. open the repository through `LocalGitRepositoryPort`
3. invoke link creation through the reusable `IssueLinkMutationPort`
4. inspect the persisted `DEMO/DEMO-1/DEMO-2/links.json` payload and confirm it
   stores a single canonical `blocks` / `inward` record
5. reload the repository and confirm the refreshed issue model still exposes the
   same normalized relationship to users

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-284/test_ts_284.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed repository fixture, so no
external credentials or environment variables are required.

## Expected output when the test passes

```text
00:00 +1: All tests passed!
```
