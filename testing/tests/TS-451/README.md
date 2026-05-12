# TS-451

Verifies that the JQL Search surface stays visible during initial hydration and
shows bootstrap-backed rows instead of replacing the section with a blocking
loader.

The automation:
1. opens the JQL Search section while the repository snapshot is already loaded
   but the initial async search page is still pending
2. confirms the search shell, query field, and bootstrap-backed rows remain
   visible during hydration
3. edits the visible Search issues field during hydration to prove the surface
   stays interactive without restarting the pending bootstrap hydration
4. proves no full-screen blocking search loader replaces the search surface
5. waits for hydration to complete and confirms the visible rows stay in place
   while the summary/load-more controls appear in place

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-451/test_ts_451.dart -r expanded
```

## Required configuration

This test uses an in-memory delayed repository fixture, so no external
credentials or services are required.

## Expected passing output

```text
00:00 +1: All tests passed!
```
