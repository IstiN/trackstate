# TS-232

Validates that Local Git keeps the `Create issue` entry point inaccessible while
project configuration is still loading, then exposes the configured custom
create-form fields once loading completes.

The automation:
1. creates a clean Local Git repository fixture whose project config declares
   `Solution`, `Acceptance Criteria`, and `Diagrams`
2. preloads the real Local Git repository and wraps it with a deterministic
   initial delay for the first app load
3. pumps the real `TrackStateApp` and verifies the user only sees the loading
   state before configuration finishes
4. confirms no visible `Create issue` entry point or `Summary` form field is
   accessible during that loading window
5. waits for the delayed load to complete and verifies the Local Git runtime UI
   becomes visible
6. opens the production-visible `Create issue` flow and checks the configured
   custom fields are rendered for the user

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-232/test_ts_232.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: while configuration is still loading, the app keeps Create issue
inaccessible and does not render the fallback-only form; after loading
completes, the Local Git Create issue form renders Solution, Acceptance
Criteria, and Diagrams.

Fail: Create issue is accessible before loading completes, a Summary field is
rendered during the loading window, loading never resolves to the Local Git
runtime, or the loaded form omits one or more configured custom fields.
```
