# TS-818

Verifies that startup hydration keeps the workspace switcher behind a loading
guard while the saved active local workspace is being validated, then restores
that workspace as the visible active `Local Git` selection.

The automation:
1. seeds the production workspace-profile store with an active local workspace
   plus one inactive hosted workspace
2. launches the production tracker in the supported Flutter widget runtime
3. injects a delayed dedicated local-workspace runtime so the hydration window
   is observable on the supported widget surface
4. confirms the initialization guard blocks workspace-switcher interaction and
   hides incorrect transient state text during hydration
5. verifies that, once hydration finishes, the trigger and active row settle to
   the saved local workspace in the `Local Git` state

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-818/test_ts_818.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- Linux widget-test environment

## Expected result

```text
Pass: while the saved local workspace is still being validated, the user sees
the initialization/loading guard instead of an interactive workspace switcher,
and no incorrect transient state such as Hosted / Needs sign-in or Local
Unavailable is exposed. After hydration completes, the trigger and active row
settle to the saved local workspace in the Local Git state.
```
