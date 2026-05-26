# TS-420

Validates the section-level readiness contract for the Flutter app shell when
project metadata and issue summaries are ready but issue details remain
partially loaded.

The automation:
1. launches the app with a ticket-scoped repository whose readiness contract
   reports `projectMeta = ready`, `issueSummaries = ready`, and
   `issueDetails = partial`
2. verifies the bootstrap readiness snapshot marks `Dashboard` and `Settings`
   as ready and `JQL Search` as partial
3. verifies the visible navigation controls for `Dashboard`, `Settings`, and
   `JQL Search` stay interactive through the shared app component abstraction
4. opens `Settings`, `Dashboard`, and `JQL Search` to confirm each surface shows
   the expected production-visible content
5. opens the deferred issue row from `JQL Search` and verifies the detail panel
   stays in the visible partial/loading state

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-420/test_ts_420.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: Dashboard and Settings remain interactive and reachable while JQL Search
stays reachable with a visible partial/loading detail panel for the deferred
issue.

Fail: The readiness contract marks the wrong section state, Dashboard or
Settings become unavailable, or JQL Search no longer exposes the visible
partial/loading detail state for the deferred issue.
```
