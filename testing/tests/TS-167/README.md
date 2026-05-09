# TS-167

Validates that archiving `TRACK-555` preserves existing YAML frontmatter
metadata instead of overwriting `priority`, `components`, or `fixVersions`.

The automation uses the shared local Git-backed archive fixture and checks the
scenario in three observable ways:
1. verify `TRACK-555` starts with the expected priority, components, and
   fixVersions in both parsed repository data and physical frontmatter
2. invoke `archiveIssue` through `LocalTrackStateRepository`
3. verify `archived: true` is added while the original metadata remains
   unchanged in the issue model, standard repository search results, and raw
   YAML frontmatter

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-167/test_ts_167.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed TrackState repository
fixture, so no external credentials or environment variables are required.

## Expected passing output

```text
00:00 +1: All tests passed!
```
