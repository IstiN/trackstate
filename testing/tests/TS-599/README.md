# TS-599

Validates that `IssueMutationService.transitionIssue` blocks a direct
`To Do -> Done` transition when `config/workflows.json` does not define that
workflow path.

The automation covers the production-visible flow by:
1. seeding a clean Local Git-backed repository with `TRACK-599` in `To Do`
2. configuring `config/workflows.json` with `To Do -> In Progress` and
   `In Progress -> Done`, but no direct `To Do -> Done` transition
3. calling the shared testing transition-mutation port with
   `transitionIssue(issueKey: "TRACK-599", status: "done")`
4. verifying the returned mutation result is a typed validation failure and the
   issue remains visibly in `To Do` after a repository reload and search

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-599/test_ts_599.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed repository fixture, so no
external credentials, environment variables, or additional config are required.
