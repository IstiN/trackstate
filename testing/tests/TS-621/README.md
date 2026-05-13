# TS-621

Validates that the shared transition mutation flow rejects an illegal
`To Do -> Done` transition when `config/workflows.json` only allows
`To Do -> In Progress`.

The automation covers the production-visible flow by:
1. seeding a clean Local Git-backed repository with `TRACK-621` in `To Do`
2. configuring `config/workflows.json` with `To Do -> In Progress` and
   `In Progress -> Done`, but no direct `To Do -> Done` transition
3. calling the shared testing transition-mutation port with
   `transitionIssue(issueKey: "TRACK-621", status: "done")`
4. verifying the returned mutation result is a typed validation failure and the
   issue still appears as `To Do` after a repository reload and search

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-621/test_ts_621.dart -r expanded
```

## Required configuration

This test creates its own temporary Local Git-backed repository fixture, so no
external credentials, environment variables, or additional config are required.
