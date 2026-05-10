# TS-281

Validates that reopening an issue from `done` to `to-do` clears the persisted
resolution in both the mutation result and the stored issue frontmatter.

The automation covers the production-visible flow by:
1. seeding a clean Local Git-backed repository with `TRACK-122` in `done` and
   `resolution: fixed`
2. calling the shared testing transition-mutation port, which drives
   `transitionIssue(issueKey: "TRACK-122", status: "to-do")`
3. verifying the returned typed issue payload reports `statusId: "to-do"` and
   `resolutionId: null`
4. confirming `TRACK/TRACK-122/main.md` and a fresh repository reload both
   persist the reopened status with no resolution value

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-281/test_ts_281.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed repository fixture, so no
external credentials, environment variables, or additional config are required.

## Expected passing output

```text
00:00 +1: All tests passed!
```
