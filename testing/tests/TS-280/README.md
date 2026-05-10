# TS-280

Validates that `IssueMutationService.transitionIssue` automatically applies the
only configured resolution when an issue moves to `Done` without an explicit
`resolutionId`.

The automation reproduces the live service behavior against a temporary local
Git-backed repository by:
1. seeding `config/workflows.json` with an allowed `in-progress -> done`
   transition
2. seeding `config/resolutions.json` with exactly one resolution, `Fixed`
3. invoking `transitionIssue(issueKey: ..., status: 'done')` without a
   resolution
4. verifying the returned issue, persisted `main.md`, and reloaded repository
   snapshot all expose `status: done` and `resolution: fixed`

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-280/test_ts_280.dart -r expanded
```

## Required configuration

This test seeds its own temporary local Git-backed repository fixture, so no
external credentials or environment variables are required.
